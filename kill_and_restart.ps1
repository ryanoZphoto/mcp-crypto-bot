Write-Host "========== KILLING EXISTING PROCESSES ==========" -ForegroundColor Red

# First try graceful shutdown of servers if they're running
try {
    Write-Host "Attempting graceful shutdown of MCP server..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "http://localhost:8002/shutdown" -Method POST -TimeoutSec 2 -ErrorAction SilentlyContinue | Out-Null
} catch {
    Write-Host "MCP server not responding to graceful shutdown (may not be running)" -ForegroundColor Gray
}

try {
    Write-Host "Attempting graceful shutdown of orchestrator..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "http://localhost:8001/shutdown" -Method POST -TimeoutSec 2 -ErrorAction SilentlyContinue | Out-Null
} catch {
    Write-Host "Orchestrator not responding to graceful shutdown (may not be running)" -ForegroundColor Gray
}

# Wait a moment for graceful shutdown to take effect
Start-Sleep -Seconds 2

# Kill any Python processes that might be running our servers
Write-Host "Killing any existing Python processes..." -ForegroundColor Red
$pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | ForEach-Object { 
        Write-Host "Killing process $($_.Id): $($_.ProcessName)" -ForegroundColor Yellow
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Also check for uvicorn processes specifically
$uvicornProcesses = Get-Process uvicorn* -ErrorAction SilentlyContinue
if ($uvicornProcesses) {
    $uvicornProcesses | ForEach-Object { 
        Write-Host "Killing uvicorn process $($_.Id): $($_.ProcessName)" -ForegroundColor Yellow
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}

# Also check for processes using ports 8000, 8001, and 8002
Write-Host "Checking for processes using ports 8000, 8001, and 8002..." -ForegroundColor Yellow
$netstat = netstat -ano | findstr ":8000 :8001 :8002"
if ($netstat) {
    foreach ($line in $netstat) {
        if ($line -match "LISTENING\s+(\d+)") {
            $procId = $matches[1]
            Write-Host "Killing process with PID $procId that's using one of our ports" -ForegroundColor Red
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 2
}

# Double-check ports again to make sure they're clear
$netstatCheck = netstat -ano | findstr ":8000 :8001 :8002"
if ($netstatCheck) {
    Write-Host "WARNING: Ports 8000, 8001, or 8002 still in use! Trying harder..." -ForegroundColor Red
    # Run the more aggressive kill script
    & .\kill_python_processes.bat
    Start-Sleep -Seconds 3
}

# Verify .env file is valid
Write-Host "`n========== CHECKING ENVIRONMENT ==========" -ForegroundColor Green
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
} else {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
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

# Clear old log files
Write-Host "Clearing old log files..." -ForegroundColor Yellow
Remove-Item -Path "mcp_server.log", "mcp_server_error.log", "orchestrator.log", "orchestrator_error.log" -ErrorAction SilentlyContinue

Write-Host "`n========== STARTING SERVERS ==========" -ForegroundColor Green
& .\start_all.ps1 