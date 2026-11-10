<#
.SYNOPSIS
  One-command FairScreen demo launcher for Windows.

.DESCRIPTION
  Starts the FastAPI backend and the Next.js dashboard, seeds the demo database
  if it is missing, waits until both are responding, and opens the browser.
  Reuses servers that are already running so it is safe to run twice.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\dev.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\dev.ps1 -NoBrowser -SkipSeed
#>
[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
$ApiPort = 8000
$WebPort = 3000
$ApiUrl = "http://127.0.0.1:$ApiPort"
$WebUrl = "http://localhost:$WebPort"
$LogDir = Join-Path $Root "data\logs"

function Test-PortInUse {
    param([int]$Port)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(500)) { return $false }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Wait-Http {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 90,
        [string]$Label = "service"
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
            # Not ready yet.
        }
        Start-Sleep -Milliseconds 750
    }
    throw "$Label did not respond at $Url within $TimeoutSeconds seconds."
}

function Show-LogTail {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Write-Host "--- $Path (last 15 lines) ---" -ForegroundColor DarkGray
        Get-Content -LiteralPath $Path -Tail 15 -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "  $_" -ForegroundColor DarkGray
        }
    }
}

function Stop-ProcessTree {
    param([int]$ProcessId)
    if (-not $ProcessId) { return }
    try {
        & taskkill.exe /PID $ProcessId /T /F 2>$null | Out-Null
    } catch {
        # Already gone.
    }
}

if (-not (Test-Path -LiteralPath $VenvPy)) {
    Write-Host "Python virtual environment not found at $VenvPy" -ForegroundColor Red
    Write-Host "Run setup first:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt"
    Write-Host "  npm --prefix web install"
    exit 1
}

$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) { $npm = Get-Command npm -ErrorAction SilentlyContinue }
if (-not $npm) {
    Write-Host "npm was not found on PATH. Install Node.js, then run 'npm --prefix web install'." -ForegroundColor Red
    exit 1
}
$NpmPath = $npm.Source

if (-not (Test-Path -LiteralPath $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}
$ApiOut = Join-Path $LogDir "api.out.log"
$ApiErr = Join-Path $LogDir "api.err.log"
$WebOut = Join-Path $LogDir "web.out.log"
$WebErr = Join-Path $LogDir "web.err.log"

$DbPath = Join-Path $Root "data\fairscreen.db"
if (-not $SkipSeed -and -not (Test-Path -LiteralPath $DbPath)) {
    Write-Host "No demo database found. Seeding (this takes about 90 seconds)..." -ForegroundColor Cyan
    & $VenvPy (Join-Path $Root "api\scripts\seed_demo.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Seeding failed with exit code $LASTEXITCODE." -ForegroundColor Red
        exit 1
    }
}

$startedApi = $false
$startedWeb = $false
$api = $null
$web = $null

if (Test-PortInUse $ApiPort) {
    Write-Host "API already listening on port $ApiPort."
} else {
    Write-Host "Starting API on $ApiUrl ..." -ForegroundColor Cyan
    $apiArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort")
    $api = Start-Process -FilePath $VenvPy -ArgumentList $apiArgs `
        -WorkingDirectory (Join-Path $Root "api") -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $ApiOut -RedirectStandardError $ApiErr
    $startedApi = $true
}

if (Test-PortInUse $WebPort) {
    Write-Host "Web dashboard already listening on port $WebPort."
} else {
    Write-Host "Starting web dashboard on $WebUrl ..." -ForegroundColor Cyan
    $web = Start-Process -FilePath $NpmPath -ArgumentList @("--prefix", "web", "run", "dev") `
        -WorkingDirectory $Root -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $WebOut -RedirectStandardError $WebErr
    $startedWeb = $true
}

try {
    Wait-Http -Url "$ApiUrl/health" -TimeoutSeconds 90 -Label "API"
    Write-Host "API is healthy: $ApiUrl/health" -ForegroundColor Green
    Write-Host "API docs: $ApiUrl/docs" -ForegroundColor Green

    Wait-Http -Url $WebUrl -TimeoutSeconds 120 -Label "Web dashboard"
    Write-Host "Dashboard is ready: $WebUrl" -ForegroundColor Green

    if (-not $NoBrowser) {
        Start-Process $WebUrl | Out-Null
    }

    if (-not $startedApi -and -not $startedWeb) {
        Write-Host "Both servers were already running. Nothing to stop." -ForegroundColor Green
        exit 0
    }

    Write-Host ""
    Write-Host "Demo is live. Press Ctrl+C to stop the servers started by this script." -ForegroundColor Yellow
    while ($true) {
        Start-Sleep -Seconds 1
        if ($startedApi -and $api.HasExited) {
            Write-Host "API process exited (code $($api.ExitCode))." -ForegroundColor Red
            Show-LogTail $ApiErr
            break
        }
        if ($startedWeb -and $web.HasExited) {
            Write-Host "Web process exited (code $($web.ExitCode))." -ForegroundColor Red
            Show-LogTail $WebErr
            break
        }
    }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($startedApi) { Show-LogTail $ApiErr }
    if ($startedWeb) { Show-LogTail $WebErr }
    exit 1
} finally {
    if ($startedWeb) { Stop-ProcessTree -ProcessId $web.Id }
    if ($startedApi) { Stop-ProcessTree -ProcessId $api.Id }
}
