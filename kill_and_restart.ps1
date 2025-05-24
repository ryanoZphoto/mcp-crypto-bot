Write-Host "Killing any existing Python processes..." -ForegroundColor Red
$pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | ForEach-Object { 
        Write-Host "Killing process $($_.Id): $($_.ProcessName)" -ForegroundColor Yellow
        Stop-Process -Id $_.Id -Force 
    }
    Start-Sleep -Seconds 2
}

# Also check for processes using ports 8000 and 8001
Write-Host "Checking for processes using ports 8000 and 8001..." -ForegroundColor Yellow
$netstat = netstat -ano | findstr ":8000 :8001"
if ($netstat) {
    foreach ($line in $netstat) {
        if ($line -match "LISTENING\s+(\d+)") {
            $pid = $matches[1]
            Write-Host "Killing process with PID $pid that's using port 8000 or 8001" -ForegroundColor Red
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 2
}

# Verify .env file is valid
Write-Host "Checking .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw -Encoding UTF8
    if (-not $envContent) {
        Write-Host ".env file exists but is empty or corrupted. Creating a new one..." -ForegroundColor Red
        @"
# Binance API Credentials
binanceusdt_api_key=YOUR_BINANCE_API_KEY
binanceusdt_api_secret=YOUR_BINANCE_API_SECRET

# Slack Integration (optional)
# slack_webhook_url=https://hooks.slack.com/services/XXX/XXX/XXX

# Demo mode - set to True to use simulated trading
DEMO_MODE=True

# Log level
LOG_LEVEL=INFO
"@ | Out-File -FilePath ".env" -Encoding UTF8
    }
}

Write-Host "Starting servers..." -ForegroundColor Green
& .\start_all.ps1 