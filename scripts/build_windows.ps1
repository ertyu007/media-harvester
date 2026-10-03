# ============================================================
#  Media Harvester — Windows Executable Build Script
#  Requires: pip install pyinstaller pillow
# ============================================================

param(
    [switch]$Clean,
    [switch]$Onefile
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$DistDir     = Join-Path $ProjectRoot "dist"
$BuildDir    = Join-Path $ProjectRoot "build"
$SpecFile    = Join-Path $ProjectRoot "harvester.spec"
$EntryPoint  = Join-Path $ProjectRoot "harvester.py"

Write-Host "=== Media Harvester Windows Build ===" -ForegroundColor Cyan

# ----------------------------------------------------------
# 0. Pick interpreter (.venv first — it has all deps)
# ----------------------------------------------------------
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Python = $null
if (Test-Path $VenvPython) {
    $Python = $VenvPython
    Write-Host "[*] Using .venv interpreter..." -ForegroundColor DarkGray
    & $Python -m pip install -q pyinstaller
} else {
    if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
        Write-Host "[!] PyInstaller not found. Installing..." -ForegroundColor Yellow
        pip install pyinstaller
    }
}

# ----------------------------------------------------------
# 1. Clean previous builds if requested
# ----------------------------------------------------------
if ($Clean) {
    Write-Host "[*] Cleaning previous build artifacts..." -ForegroundColor Yellow
    if (Test-Path $DistDir)  { Remove-Item $DistDir  -Recurse -Force }
    if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }
    if (Test-Path $SpecFile) { Remove-Item $SpecFile -Force }
    Write-Host "[+] Clean complete." -ForegroundColor Green
}

# ----------------------------------------------------------
# 2. Build
# ----------------------------------------------------------
$PyArgs = @(
    $EntryPoint
    "--name", "media-harvester"
    "--clean"
    "--noconfirm"
    "--add-data", "core;core"
    "--add-data", "skills;skills"
    "--collect-all", "httpx"
    "--collect-all", "curl_cffi"
    "--collect-all", "bs4"
    "--collect-all", "lxml"
    "--collect-all", "PIL"
    "--collect-all", "rich"
    "--collect-all", "click"
)

if ($Onefile) {
    Write-Host "[*] Building one-file executable..." -ForegroundColor Yellow
    $PyArgs += "--onefile"
} else {
    Write-Host "[*] Building one-directory bundle (faster startup)..." -ForegroundColor Yellow
    $PyArgs += "--onedir"
}

Push-Location $ProjectRoot
if ($Python) { & $Python -m PyInstaller @PyArgs } else { pyinstaller @PyArgs }
Pop-Location

# ----------------------------------------------------------
# 3. Done
# ----------------------------------------------------------
$Exe = if ($Onefile) {
    Join-Path $DistDir "media-harvester.exe"
} else {
    Join-Path $DistDir "media-harvester\media-harvester.exe"
}

if (Test-Path $Exe) {
    $SizeMB = [math]::Round((Get-Item $Exe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "=== Build Successful ===" -ForegroundColor Green
    Write-Host "  Executable : $Exe" -ForegroundColor Cyan
    Write-Host "  Size       : ${SizeMB} MB" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\dist\media-harvester\media-harvester.exe <URL>" -ForegroundColor White
} else {
    Write-Host "[X] Build failed — executable not found." -ForegroundColor Red
    exit 1
}
