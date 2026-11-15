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
    Write-Host 'CouchControl setup: checking project files...'
    foreach ($requiredFile in @($Requirements, $BotFile, $WebServerFile)) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            throw "Required CouchControl file is missing: $requiredFile"
        }
    }

    if (-not ((Test-Path -LiteralPath $PythonExe) -and (Test-Path -LiteralPath $PythonwExe))) {
        Write-Host "Preparing private Python $PythonVersion runtime..."
        if (Test-Path -LiteralPath $PythonDir) {
            Remove-Item -LiteralPath $PythonDir -Recurse -Force
        }

        Write-Host 'Downloading the official Python installer...'
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe" -OutFile $PythonInstaller

        if (-not (Test-Path -LiteralPath $PythonInstaller -PathType Leaf)) {
            throw 'Python installer download did not create a file.'
        }
        $download = Get-Item -LiteralPath $PythonInstaller
        Write-Host "Downloaded installer size: $($download.Length) bytes"
        if ($download.Length -lt 10MB) {
            throw "Downloaded Python installer looks incomplete ($($download.Length) bytes)."
        }

        if (Test-Path -LiteralPath $InstallLog) {
            Remove-Item -LiteralPath $InstallLog -Force
        }

        $installerArguments = '/quiet InstallAllUsers=0 PrependPath=0 Include_launcher=0 Include_test=0 Include_pip=1 Shortcuts=0 TargetDir="' + $PythonDir + '" /log "' + $InstallLog + '"'
        Write-Host "Installing private Python into: $PythonDir"
        $pythonProcess = Start-Process -FilePath $PythonInstaller -ArgumentList $installerArguments -Wait -PassThru -WindowStyle Hidden
        if ($null -eq $pythonProcess) {
            throw 'Windows did not return a process result from the Python installer.'
        }

        Write-Host "Python installer exit code: $($pythonProcess.ExitCode)"
        if ($pythonProcess.ExitCode -ne 0) {
            if (Test-Path -LiteralPath $InstallLog) {
                Write-Host 'Last lines from Python installer log:'
                Get-Content -LiteralPath $InstallLog -Tail 80 | ForEach-Object { Write-Host $_ }
            }
            throw "Python installer failed with exit code $($pythonProcess.ExitCode)."
        }
    }

    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        throw "Private Python was not found at: $PythonExe"
    }
    if (-not (Test-Path -LiteralPath $PythonwExe -PathType Leaf)) {
        throw "Private pythonw.exe was not found at: $PythonwExe"
    }

    Write-Host 'Checking private Python...'
    & $PythonExe --version
    $pythonExitCode = $LASTEXITCODE
    if ($pythonExitCode -ne 0) {
        throw "Private Python could not start. Exit code: $pythonExitCode"
    }

    Write-Host 'Creating the private virtual environment...'
    if (Test-Path -LiteralPath $VenvDir) {
        Remove-Item -LiteralPath $VenvDir -Recurse -Force
    }
    & $PythonExe -m venv $VenvDir
    $venvExitCode = $LASTEXITCODE
    if ($venvExitCode -ne 0 -or -not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        throw "Could not create .venv. Exit code: $venvExitCode"
    }
    if (-not (Test-Path -LiteralPath $VenvPythonw -PathType Leaf)) {
        throw 'The virtual environment does not contain pythonw.exe.'
    }

    Write-Host 'Installing Python packages...'
    & $VenvPython -m pip install --disable-pip-version-check --upgrade pip
    $pipExitCode = $LASTEXITCODE
    if ($pipExitCode -ne 0) {
        throw "Could not upgrade pip. Exit code: $pipExitCode"
    }

    & $VenvPython -m pip install --disable-pip-version-check -r $Requirements
    $dependenciesExitCode = $LASTEXITCODE
    if ($dependenciesExitCode -ne 0) {
        throw "Could not install requirements.txt. Exit code: $dependenciesExitCode"
    }

    Write-Host 'Checking CouchControl modules...'
    & $VenvPython -c "import telegram, dotenv, pyautogui, PIL, pyperclip, aiohttp; import web_server; import bot; print('CouchControl modules OK')"
    $moduleExitCode = $LASTEXITCODE
    if ($moduleExitCode -ne 0) {
        throw "CouchControl module check failed. Exit code: $moduleExitCode"
    }

    Write-Host 'CouchControl installation completed successfully.'
    Write-Host "Diagnostic log: $DiagnosticLog"
    exit 0
}
catch {
    Write-Host ''
    Write-Host 'COUCHCONTROL INSTALLATION FAILED:' -ForegroundColor Red
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
