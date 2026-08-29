# Kitsune Windows Installer (PowerShell)
# Usage: irm https://raw.githubusercontent.com/dev-eyitayo/kitsune/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host "Installing kitsune (Universal Web App Manager)..." -ForegroundColor Cyan

# Check for Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Error "Python 3 is required but was not found in PATH. Please install Python 3 from https://www.python.org/"
    exit 1
}

$InstallDir = Join-Path $env:APPDATA "kitsune"
$BinDir = Join-Path $InstallDir "bin"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($ScriptDir -and (Test-Path (Join-Path $ScriptDir "bin\kitsune"))) {
    Write-Host "Installing from local repository..." -ForegroundColor Gray
    Copy-Item -Recurse -Force "$ScriptDir\*" "$InstallDir\"
} else {
    Write-Host "Downloading latest kitsune repository from GitHub..." -ForegroundColor Gray
    $TempDir = Join-Path $env:TEMP ("kitsune_" + [System.Guid]::NewGuid().ToString())
    git clone --depth 1 https://github.com/dev-eyitayo/kitsune.git $TempDir
    Copy-Item -Recurse -Force "$TempDir\*" "$InstallDir\"
    Remove-Item -Recurse -Force $TempDir
}

# Create kitsune.cmd launcher in bin directory
$CmdPath = Join-Path $BinDir "kitsune.cmd"
$PythonScript = Join-Path $InstallDir "bin\kitsune"

$CmdContent = @"
@echo off
python "$PythonScript" %*
"@

Set-Content -Path $CmdPath -Value $CmdContent

# Add BinDir to User PATH if not present
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$BinDir", "User")
    $env:Path += ";$BinDir"
    Write-Host "Added $BinDir to User PATH." -ForegroundColor Green
}

Write-Host "`n[OK] kitsune successfully installed!" -ForegroundColor Green
Write-Host "Try running: kitsune create whatsapp or kitsune for interactive wizard.`n"
