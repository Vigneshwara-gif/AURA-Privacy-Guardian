@echo off
setlocal enabledelayedexpansion

title AURA Privacy Guardian Launcher
echo ============================================================
echo AURA PRIVACY GUARDIAN ? STARTUP LAUNCHER
echo ============================================================
echo Checking local security engine...

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

:: 1. Start Background Security Engine if not already running
netstat -ano | findstr 127.0.0.1:8787 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%SCRIPT_DIR%packaging\dist\AURA-Privacy-Guardian\backend\aura-agent.exe" (
        echo Starting Standalone AURA Security Engine...
        start "" "%SCRIPT_DIR%packaging\dist\AURA-Privacy-Guardian\backend\aura-agent.exe"
        timeout /t 2 /nobreak >nul
    ) else if exist "%SCRIPT_DIR%packaging\dist\aura-agent\aura-agent.exe" (
        echo Starting Standalone AURA Security Engine...
        start "" "%SCRIPT_DIR%packaging\dist\aura-agent\aura-agent.exe"
        timeout /t 2 /nobreak >nul
    ) else (
        echo Starting AURA Security Engine via Python...
        start /b "" python -m aura.cli.main agent start
        timeout /t 2 /nobreak >nul
    )
) else (
    echo AURA Security Engine is already running on 127.0.0.1:8787.
)

:: 2. Launch Native Flutter Desktop Client
set DIST_EXE=%SCRIPT_DIR%packaging\dist\AURA-Privacy-Guardian\desktop\aura_desktop.exe
set REL_EXE=%SCRIPT_DIR%aura_desktop\build\windows\x64\runner\Release\aura_desktop.exe

if exist "%DIST_EXE%" (
    echo Launching AURA Desktop Application...
    start "" "%DIST_EXE%"
) else if exist "%REL_EXE%" (
    echo Launching AURA Desktop Application...
    start "" "%REL_EXE%"
) else (
    echo Release binary not found. Launching via Flutter CLI...
    cd "%SCRIPT_DIR%aura_desktop"
    start "" flutter run -d windows
)

echo AURA Privacy Guardian is active.
exit /b 0
