<#
.SYNOPSIS
  Seed or rebuild the FairScreen demo database on Windows.

.DESCRIPTION
  The demo seed drops and rebuilds all tables, generates 198 base CVs and 1,980
  variants, scores them with three simulated models, and computes audits.
  If a database already exists this script refuses unless -Force is supplied.
  With -Force it makes a timestamped backup before rebuilding.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\seed.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\seed.ps1 -Force
#>
[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
$DataDir = Join-Path $Root "data"
$DbPath = Join-Path $DataDir "fairscreen.db"

if (-not (Test-Path -LiteralPath $VenvPy)) {
    Write-Host "Python virtual environment not found at $VenvPy" -ForegroundColor Red
    Write-Host "Run setup first (see README Quickstart)." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path -LiteralPath $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir | Out-Null
}

if (Test-Path -LiteralPath $DbPath) {
    if (-not $Force) {
        Write-Host "Database already exists: $DbPath" -ForegroundColor Yellow
        Write-Host "The seed rebuilds every table, so it is not run automatically." -ForegroundColor Yellow
        Write-Host "Re-run with -Force to back it up and rebuild:" -ForegroundColor Yellow
        Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\seed.ps1 -Force"
        exit 0
    }
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backup = Join-Path $DataDir "fairscreen.backup-$timestamp.db"
    Copy-Item -LiteralPath $DbPath -Destination $backup
    Write-Host "Backed up existing database to $backup" -ForegroundColor Cyan
}

Write-Host "Seeding demo database (about 90 seconds)..." -ForegroundColor Cyan
& $VenvPy (Join-Path $Root "api\scripts\seed_demo.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Seeding failed with exit code $LASTEXITCODE." -ForegroundColor Red
    exit 1
}

Write-Host "Seed complete: $DbPath" -ForegroundColor Green
