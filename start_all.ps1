Write-Host "Starting MCP server in background on port 8000..." -ForegroundColor Green

# Get the absolute path to logs
$currentDir = Get-Location
$mcpServerLogPath = Join-Path -Path $currentDir -ChildPath "mcp_server.log"
$mcpServerErrorLogPath = Join-Path -Path $currentDir -ChildPath "mcp_server_error.log"
$orchestratorLogPath = Join-Path -Path $currentDir -ChildPath "orchestrator.log"
$orchestratorErrorLogPath = Join-Path -Path $currentDir -ChildPath "orchestrator_error.log"

# Start MCP server
$mcpProcess = Start-Process python -ArgumentList "mcp_server.py" -NoNewWindow -PassThru -RedirectStandardOutput $mcpServerLogPath -RedirectStandardError $mcpServerErrorLogPath
Write-Host "MCP server process started with PID: $($mcpProcess.Id)" -ForegroundColor Cyan

# Function to check if a port is in use
function Test-PortInUse {
    param (
        [int]$Port
    )
    $connections = netstat -an | Select-String "TCP.*:$Port.*LISTENING"
    return $null -ne $connections
}

# Wait for MCP server to initialize
Write-Host "Waiting for MCP server to initialize (up to 15 seconds)..." -ForegroundColor Yellow
$retryCount = 0
$maxRetries = 15
$success = $false

while (-not $success -and $retryCount -lt $maxRetries) {
    Start-Sleep -Seconds 1
    $retryCount++

    # First check if port 8000 is in use (main MCP service)
    if (Test-PortInUse -Port 8000) {
        # Then check if health API is accessible on port 8002
        try {
            $mcp_check = Invoke-WebRequest -Uri "http://127.0.0.1:8002/health" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($mcp_check.StatusCode -eq 200) {
                Write-Host "✅ MCP server is running successfully on port 8000 (health API on 8002)" -ForegroundColor Green
                $success = $true
            }
        } catch {
            Write-Host "Waiting for MCP server to be fully ready... ($retryCount/$maxRetries)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Waiting for MCP server to bind to port 8000... ($retryCount/$maxRetries)" -ForegroundColor Yellow
    }

    # Check if process is still running
    if ($mcpProcess.HasExited) {
        Write-Host "❌ ERROR: MCP server process exited unexpectedly!" -ForegroundColor Red
        Write-Host "Check logs for details:" -ForegroundColor Red
        Write-Host "  - $mcpServerLogPath" -ForegroundColor Red
        Write-Host "  - $mcpServerErrorLogPath" -ForegroundColor Red
        if (Test-Path $mcpServerErrorLogPath) {
            Write-Host "`nLast few lines of error log:" -ForegroundColor Red
            Get-Content $mcpServerErrorLogPath -Tail 10
        }
        exit 1
    }
}

if (-not $success) {
    Write-Host "❌ WARNING: Could not verify MCP server is running properly. Continuing anyway..." -ForegroundColor Red
    Write-Host "Check logs for details:" -ForegroundColor Red
    Write-Host "  - $mcpServerLogPath" -ForegroundColor Red
    Write-Host "  - $mcpServerErrorLogPath" -ForegroundColor Red
}

# Start orchestrator
Write-Host "`nStarting orchestrator in background on port 8001..." -ForegroundColor Green
$orchestratorProcess = Start-Process python -ArgumentList "-m uvicorn orchestrator.main:app --port 8001" -NoNewWindow -PassThru -RedirectStandardOutput $orchestratorLogPath -RedirectStandardError $orchestratorErrorLogPath
Write-Host "Orchestrator process started with PID: $($orchestratorProcess.Id)" -ForegroundColor Cyan

# Wait for orchestrator to initialize
Write-Host "Waiting for orchestrator to initialize (up to 15 seconds)..." -ForegroundColor Yellow
$retryCount = 0
$maxRetries = 15
$success = $false

while (-not $success -and $retryCount -lt $maxRetries) {
    Start-Sleep -Seconds 1
    $retryCount++

    if (Test-PortInUse -Port 8001) {
        try {
            $orch_check = Invoke-WebRequest -Uri "http://127.0.0.1:8001/bot-status" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($orch_check.StatusCode -eq 200) {
                Write-Host "✅ Orchestrator is running successfully on port 8001" -ForegroundColor Green
                $success = $true
            }
        } catch {
            Write-Host "Waiting for orchestrator to be fully ready... ($retryCount/$maxRetries)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Waiting for orchestrator to bind to port 8001... ($retryCount/$maxRetries)" -ForegroundColor Yellow
    }

    # Check if process is still running
    if ($orchestratorProcess.HasExited) {
        Write-Host "❌ ERROR: Orchestrator process exited unexpectedly!" -ForegroundColor Red
        Write-Host "Check logs for details:" -ForegroundColor Red
        Write-Host "  - $orchestratorLogPath" -ForegroundColor Red
        Write-Host "  - $orchestratorErrorLogPath" -ForegroundColor Red
        if (Test-Path $orchestratorErrorLogPath) {
            Write-Host "`nLast few lines of error log:" -ForegroundColor Red
            Get-Content $orchestratorErrorLogPath -Tail 10
        }
        exit 1
    }
}

if (-not $success) {
    Write-Host "❌ WARNING: Could not verify orchestrator is running properly." -ForegroundColor Red
    Write-Host "Check logs for details:" -ForegroundColor Red
    Write-Host "  - $orchestratorLogPath" -ForegroundColor Red
    Write-Host "  - $orchestratorErrorLogPath" -ForegroundColor Red
} else {
    Write-Host "`nOpening browser to trading bot dashboard..." -ForegroundColor Green
    Start-Process "http://localhost:8001/bot-control"
    
    Write-Host "`n✅ Setup complete! The dashboard should open in your browser." -ForegroundColor Cyan
    Write-Host "  - MCP Server: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "  - Dashboard: http://localhost:8001/bot-control" -ForegroundColor Cyan
    Write-Host "`nTo restart, run: .\kill_and_restart.ps1" -ForegroundColor Yellow
}