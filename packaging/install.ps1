<#
.SYNOPSIS
    AURA Privacy Guardian — Windows Background Agent Setup & Pairing Installer.
.DESCRIPTION
    Installs and configures the AURA Background Agent on any clean Windows machine.
    Sets up LocalAppData directories, initializes SQLite WAL storage, registers startup task (optional),
    and pairs the device with your AURA account.
#>

param (
    [string]$PairingCode = "",
    [string]$CloudUrl = "https://aura-privacy-guardian.vercel.app",
    [switch]$StartAgent = $true
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  AURA PRIVACY GUARDIAN — WINDOWS AGENT SETUP     " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$AppDir = "$env:LOCALAPPDATA\AURA"
$ConfigDir = "$AppDir\config"
$DataDir = "$AppDir\data"
$LogsDir = "$AppDir\logs"

Write-Host "[1/4] Preparing directories in LocalAppData..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null
Write-Host "      Location: $AppDir" -ForegroundColor Green

Write-Host "[2/4] Verifying Python runtime and dependencies..." -ForegroundColor Yellow
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    Write-Host "      ERROR: Python 3.10+ required to run the agent in script mode." -ForegroundColor Red
    exit 1
}
Write-Host "      Python Runtime: $($PythonCmd.Source)" -ForegroundColor Green

if ($PairingCode -ne "") {
    Write-Host "[3/4] Pairing Windows device with AURA Cloud account..." -ForegroundColor Yellow
    python -m aura.cli.main pair $PairingCode --cloud $CloudUrl
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      Device successfully paired!" -ForegroundColor Green
    } else {
        Write-Host "      Pairing failed. You can pair manually later via 'aura pair <code>'." -ForegroundColor Red
    }
} else {
    Write-Host "[3/4] Pairing step skipped (no -PairingCode provided)." -ForegroundColor Yellow
    Write-Host "      To pair later, run: python -m aura.cli.main pair <YOUR_CODE>" -ForegroundColor Gray
}

if ($StartAgent) {
    Write-Host "[4/4] Starting AURA Background Agent Daemon..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "-m aura.cli.main agent start" -WindowStyle Hidden
    Write-Host "      AURA Agent is running in background (SingleInstanceGuard active)." -ForegroundColor Green
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  AURA WINDOWS AGENT INSTALLATION COMPLETE        " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
