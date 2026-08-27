@echo off
setlocal enabledelayedexpansion

title AURA Privacy Guardian Launcher
echo ============================================================
echo AURA PRIVACY GUARDIAN ? STARTUP LAUNCHER
echo ============================================================
echo Checking local environment and starting background security engine...

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

:: 1. Start Python AURA Agent in Background if not already running
netstat -ano | findstr 127.0.0.1:8787 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Starting AURA Local Security Engine (FastAPI on 127.0.0.1:8787)...
    start /b "" python -m aura.cli.main agent start
    timeout /t 2 /nobreak >nul
) else (
    echo AURA Local Security Engine is already running on 127.0.0.1:8787.
)

:: 2. Launch Native Flutter Desktop Client
set EXE_PATH=%SCRIPT_DIR%aura_desktop\build\windows\x64\runner\Release\aura_desktop.exe
set STAGED_EXE=%SCRIPT_DIR%packaging\dist\aura-agent\desktop\aura_desktop.exe

if exist "%EXE_PATH%" (
    echo Launching AURA Desktop Application...
    start "" "%EXE_PATH%"
) else if exist "%STAGED_EXE%" (
    echo Launching Staged AURA Desktop Application...
    start "" "%STAGED_EXE%"
) else (
    echo Release binary not found. Launching via Flutter CLI...
    cd "%SCRIPT_DIR%aura_desktop"
    start "" flutter run -d windows
)

echo AURA Privacy Guardian is running.
exit /b 0
