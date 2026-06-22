param(
    [string]$ComPort = "COM3",
    [int]$Baud = 115200
)

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

Write-Host "SecureVault - Hardware PUF local test mode" -ForegroundColor Cyan
Write-Host "ESP32 must be plugged in on $ComPort and running esp32/main.py MFA server" -ForegroundColor Yellow
Write-Host ""

# Backend .env for hardware (host must run backend - Docker cannot see COM port easily)
$envFile = Join-Path $Backend ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $Root ".env.example") $envFile
}

$content = Get-Content $envFile -Raw
function Set-Line($text, $key, $value) {
    $pattern = "(?m)^$key=.*$"
    $line = "$key=$value"
    if ($text -match $pattern) { return [regex]::Replace($text, $pattern, $line) }
    return ($text.TrimEnd() + "`r`n" + $line + "`r`n")
}

$content = Set-Line $content "PUF_BRIDGE_MODE" "hardware"
$content = Set-Line $content "HARDWARE_PUF_SERIAL_PORT" $ComPort
$content = Set-Line $content "HARDWARE_PUF_BAUD" $Baud
$content | Set-Content $envFile -NoNewline

Write-Host "Starting Backend (hardware PUF on $ComPort)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Backend'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

Start-Sleep -Seconds 2

Write-Host "Starting Frontend (API -> http://127.0.0.1:8001)..." -ForegroundColor Cyan
Set-Location $Frontend
@"
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8001/ws/auth-monitor
"@ | Set-Content ".env.local" -NoNewline

npm run dev
