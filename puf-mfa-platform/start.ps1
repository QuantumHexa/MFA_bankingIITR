# Start all SecureVault services (Windows PowerShell)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting Virtual PUF bridge..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\puf-bridge'; python virtual_puf_server.py"

Start-Sleep -Seconds 1

Write-Host "Starting Backend API..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\backend'; if (-not (Test-Path .env)) { Copy-Item '$Root\.env.example' .env }; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

Start-Sleep -Seconds 2

Write-Host "Starting Frontend..." -ForegroundColor Cyan
Set-Location "$Root\frontend"
if (-not (Test-Path .env.local)) { Copy-Item "$Root\frontend\.env.local" .env.local -ErrorAction SilentlyContinue }
npm run dev
