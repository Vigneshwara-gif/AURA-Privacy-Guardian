# PowerShell launcher for AURA Privacy Guardian
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "AURA PRIVACY GUARDIAN — STARTUP LAUNCHER" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan

 = 
Set-Location 

# 1. Verify / Start Python AURA Agent
 = False
try {
     = Get-NetTCPConnection -LocalPort 8787 -ErrorAction SilentlyContinue
    if () {  = True }
} catch {}

if (-not ) {
    Write-Host "Starting AURA Local Security Engine (FastAPI on 127.0.0.1:8787)..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "-m aura.cli.main agent start" -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "AURA Local Security Engine is already running on 127.0.0.1:8787." -ForegroundColor Green
}

# 2. Launch Native Flutter Desktop Client
 = Join-Path  "aura_desktop\build\windows\x64\runner\Release\aura_desktop.exe"
 = Join-Path  "packaging\dist\aura-agent\desktop\aura_desktop.exe"

if (Test-Path ) {
    Write-Host "Launching AURA Desktop Application..." -ForegroundColor Green
    Start-Process -FilePath 
} elseif (Test-Path ) {
    Write-Host "Launching Staged AURA Desktop Application..." -ForegroundColor Green
    Start-Process -FilePath 
} else {
    Write-Host "Release binary not found. Launching via Flutter CLI..." -ForegroundColor Yellow
    Set-Location (Join-Path  "aura_desktop")
    Start-Process -FilePath "flutter" -ArgumentList "run -d windows"
}

Write-Host "AURA Privacy Guardian launched successfully." -ForegroundColor Cyan
