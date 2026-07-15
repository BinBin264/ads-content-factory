param(
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path $PSScriptRoot).Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Path $logs -Force | Out-Null

function Stop-WorkspacePort {
    param([int]$Port)

    $listeners = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
        $isWorkspaceProcess = $process -and (
            $process.CommandLine -like "*$root*" -or
            ($Port -eq 8000 -and $process.CommandLine -match "uvicorn\s+app\.main:app") -or
            ($Port -eq 5173 -and $process.CommandLine -match "vite")
        )
        if ($isWorkspaceProcess) {
            Stop-Process -Id $listener.OwningProcess -Force
        }
    }
}

if (-not $NoRestart) {
    Stop-WorkspacePort -Port 8000
    Stop-WorkspacePort -Port 5173
    Start-Sleep -Milliseconds 500
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$python = Join-Path $backend ".venv\Scripts\python.exe"
$venvReady = $false
if (Test-Path -LiteralPath $python) {
    $previousErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $python -c "import fastapi, PIL, uvicorn" *> $null
    $venvReady = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $previousErrorPreference
}
if (-not $venvReady) {
    $python = "python"
}

$backendOut = Join-Path $logs "backend-$stamp.stdout.log"
$backendErr = Join-Path $logs "backend-$stamp.stderr.log"
$frontendOut = Join-Path $logs "frontend-$stamp.stdout.log"
$frontendErr = Join-Path $logs "frontend-$stamp.stderr.log"

Start-Process `
    -FilePath $python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $backend `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -WindowStyle Hidden

Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $frontend `
    -RedirectStandardOutput $frontendOut `
    -RedirectStandardError $frontendErr `
    -WindowStyle Hidden

Start-Sleep -Seconds 2

$backendReady = [bool](Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue)
$frontendReady = [bool](Get-NetTCPConnection -State Listen -LocalPort 5173 -ErrorAction SilentlyContinue)

Write-Host "Backend:  http://127.0.0.1:8000 (ready: $backendReady)"
Write-Host "Frontend: http://127.0.0.1:5173 (ready: $frontendReady)"
Write-Host "Logs:     $logs"
