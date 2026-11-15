$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonVersion = '3.12.10'
$PythonInstaller = Join-Path $env:TEMP "CouchControl-Python-$PythonVersion-amd64.exe"
$PythonDir = Join-Path $ProjectPath 'Python312'
$PythonExe = Join-Path $PythonDir 'python.exe'
$PythonwExe = Join-Path $PythonDir 'pythonw.exe'
$VenvDir = Join-Path $ProjectPath '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$VenvPythonw = Join-Path $VenvDir 'Scripts\pythonw.exe'
$Requirements = Join-Path $ProjectPath 'requirements.txt'
$BotFile = Join-Path $ProjectPath 'bot.py'
$WebServerFile = Join-Path $ProjectPath 'web_server.py'
$InstallLog = Join-Path $env:TEMP 'CouchControl-Python-install.log'
$DiagnosticLog = Join-Path $env:TEMP 'CouchControl-install-diagnostic.log'

try { Start-Transcript -Path $DiagnosticLog -Force | Out-Null } catch {}

try {
    foreach ($requiredFile in @($Requirements, $BotFile, $WebServerFile)) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            throw "Required CouchControl file is missing: $requiredFile"
        }
    }

    # Reuse the private Python runtime only if both Windows executables are present.
    if (-not ((Test-Path -LiteralPath $PythonExe) -and (Test-Path -LiteralPath $PythonwExe))) {
        Write-Host "Preparing private Python $PythonVersion runtime..."
        if (Test-Path -LiteralPath $PythonDir) {
            Remove-Item -LiteralPath $PythonDir -Recurse -Force
        }

        Write-Host "Downloading official Python $PythonVersion installer from python.org..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe" -OutFile $PythonInstaller

        if (-not (Test-Path -LiteralPath $PythonInstaller)) {
            throw 'Python installer download did not create a file.'
        }
        $download = Get-Item -LiteralPath $PythonInstaller
        if ($download.Length -lt 10MB) {
            throw "Downloaded Python installer looks incomplete ($($download.Length) bytes)."
        }

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
        & $PythonInstaller @installerArgs
        $installerExitCode = $LASTEXITCODE
        Write-Host "Python installer exit code: $installerExitCode"

        if ($installerExitCode -ne 0) {
            throw "Python installer failed with exit code $installerExitCode. See $InstallLog"
        }
    }

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "Python installation did not create python.exe at $PythonExe. See $InstallLog"
    }
    if (-not (Test-Path -LiteralPath $PythonwExe)) {
        throw "Python installation did not create pythonw.exe at $PythonwExe. See $InstallLog"
    }

    Write-Host 'Verifying private Python runtime...'
    & $PythonExe --version
    if ($LASTEXITCODE -ne 0) {
        throw 'Python was found but could not be started.'
    }

    Write-Host 'Creating virtual environment...'
    if (Test-Path -LiteralPath $VenvDir) {
        Remove-Item -LiteralPath $VenvDir -Recurse -Force
    }
    & $PythonExe -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $VenvPython)) {
        throw 'Python could not create the virtual environment (.venv).'
    }
    if (-not (Test-Path -LiteralPath $VenvPythonw)) {
        throw 'The virtual environment was created without pythonw.exe.'
    }

    Write-Host 'Upgrading pip...'
    & $VenvPython -m pip install --disable-pip-version-check --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not upgrade pip.'
    }

    Write-Host 'Installing CouchControl dependencies...'
    & $VenvPython -m pip install --disable-pip-version-check -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not install dependencies from requirements.txt.'
    }

    Write-Host 'Verifying CouchControl modules...'
    & $VenvPython -c "import telegram, dotenv, pyautogui, PIL, pyperclip, aiohttp; import web_server; import bot; print('CouchControl modules OK')"
    if ($LASTEXITCODE -ne 0) {
        throw 'CouchControl module verification failed.'
    }

    Write-Host 'CouchControl installation completed successfully.'
    Write-Host "Diagnostic log: $DiagnosticLog"
    exit 0
}
catch {
    Write-Host ''
    Write-Host 'INSTALLATION FAILED:' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "Diagnostic log: $DiagnosticLog" -ForegroundColor Yellow
    if (Test-Path -LiteralPath $InstallLog) {
        Write-Host "Python installer log: $InstallLog" -ForegroundColor Yellow
    }
    exit 1
}
finally {
    try { Stop-Transcript | Out-Null } catch {}
}
