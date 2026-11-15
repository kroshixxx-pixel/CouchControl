$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonVersion = '3.12.10'
$PythonInstaller = Join-Path $env:TEMP "CouchControl-Python-$PythonVersion-amd64.exe"
$PythonDir = Join-Path $ProjectPath 'Python312'
$PythonExe = Join-Path $PythonDir 'python.exe'
$VenvDir = Join-Path $ProjectPath '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$Requirements = Join-Path $ProjectPath 'requirements.txt'
$InstallLog = Join-Path $env:TEMP 'CouchControl-Python-install.log'
$DiagnosticLog = Join-Path $env:TEMP 'CouchControl-install-diagnostic.log'

try { Start-Transcript -Path $DiagnosticLog -Force | Out-Null } catch {}

try {
    Write-Host "Downloading official Python $PythonVersion installer from python.org..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe" -OutFile $PythonInstaller

    if (-not (Test-Path -LiteralPath $PythonInstaller)) { throw 'Python installer download did not create a file.' }
    $download = Get-Item -LiteralPath $PythonInstaller
    if ($download.Length -lt 10MB) { throw "Downloaded Python installer looks incomplete ($($download.Length) bytes)." }

    # Calling the executable directly with an argument array preserves paths containing spaces.
    $installerArgs = @(
        '/quiet',
        'InstallAllUsers=0',
        'PrependPath=0',
        'Include_launcher=0',
        'Include_test=0',
        'Include_pip=1',
        'Shortcuts=0',
        "TargetDir=$PythonDir",
        "/log=$InstallLog"
    )

    Write-Host "Installing Python into: $PythonDir"
    $global:LASTEXITCODE = 0
    & $PythonInstaller @installerArgs
    $installerExitCode = $LASTEXITCODE
    Write-Host "Python installer exit code: $installerExitCode"

    if ($installerExitCode -ne 0) {
        throw "Python installer failed with exit code $installerExitCode. See $InstallLog"
    }

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        $candidates = @(
            (Join-Path $PythonDir 'python.exe'),
            (Join-Path $PythonDir 'Scripts\python.exe'),
            (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe")
        )
        $foundPath = $null
        foreach ($candidate in $candidates) {
            if (Test-Path -LiteralPath $candidate) { $foundPath = $candidate; break }
        }
        if (-not $foundPath) {
            Write-Host 'Python target directory contents:'
            if (Test-Path -LiteralPath $PythonDir) {
                Get-ChildItem -LiteralPath $PythonDir -Force | Format-Table -AutoSize | Out-String | Write-Host
            }
            if (Test-Path -LiteralPath $InstallLog) {
                Write-Host '--- Python installer log (last 80 lines) ---'
                Get-Content -LiteralPath $InstallLog -Tail 80 | ForEach-Object { Write-Host $_ }
            }
            throw "Python installer returned success, but python.exe was not found. Installer log: $InstallLog"
        }
        $PythonExe = $foundPath
        Write-Host "Found Python at: $PythonExe"
    }

    Write-Host 'Verifying Python runtime...'
    & $PythonExe --version
    if ($LASTEXITCODE -ne 0) { throw 'Python was found but could not be started.' }

    Write-Host 'Creating virtual environment...'
    if (Test-Path -LiteralPath $VenvDir) { Remove-Item -LiteralPath $VenvDir -Recurse -Force }
    & $PythonExe -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $VenvPython)) {
        throw 'Python could not create the virtual environment (.venv).'
    }

    Write-Host 'Upgrading pip...'
    & $VenvPython -m pip install --disable-pip-version-check --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'Could not upgrade pip.' }

    Write-Host 'Installing CouchControl dependencies...'
    & $VenvPython -m pip install --disable-pip-version-check -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw 'Could not install dependencies from requirements.txt.' }

    # Validate that the bot imports and its required dependencies are available.
    & $VenvPython -c "import telegram, dotenv, pyautogui, PIL, pyperclip; print('Dependencies OK')"
    if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }

    Write-Host 'CouchControl installation completed successfully.'
    Write-Host "Diagnostic log: $DiagnosticLog"
    exit 0
}
catch {
    Write-Host ''
    Write-Host 'INSTALLATION FAILED:' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "Diagnostic log: $DiagnosticLog" -ForegroundColor Yellow
    if (Test-Path -LiteralPath $InstallLog) { Write-Host "Python installer log: $InstallLog" -ForegroundColor Yellow }
    exit 1
}
finally {
    try { Stop-Transcript | Out-Null } catch {}
}
