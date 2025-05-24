Write-Host "Starting MCP server in background..." -ForegroundColor Green
Start-Process python -ArgumentList "mcp_server.py" -NoNewWindow -RedirectStandardOutput "mcp_server.log" -RedirectStandardError "mcp_server_error.log"

Write-Host "Waiting for MCP server to initialize (5 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if MCP server is running
try {
    $mcp_check = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($mcp_check.StatusCode -eq 200) {
        Write-Host "MCP server is running successfully" -ForegroundColor Green
    }
} catch {
    Write-Host "Warning: Could not verify MCP server is running. Continuing anyway..." -ForegroundColor Red
    Write-Host "Check mcp_server.log and mcp_server_error.log for details" -ForegroundColor Red
}

Write-Host "Starting orchestrator in background..." -ForegroundColor Green
Start-Process python -ArgumentList "-m uvicorn orchestrator.main:app --port 8001" -NoNewWindow -RedirectStandardOutput "orchestrator.log" -RedirectStandardError "orchestrator_error.log"

Write-Host "Waiting for orchestrator to initialize (8 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

# Check if orchestrator is running
try {
    $orch_check = Invoke-WebRequest -Uri "http://127.0.0.1:8001/bot-status" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($orch_check.StatusCode -eq 200) {
        Write-Host "Orchestrator is running successfully" -ForegroundColor Green
    }
} catch {
    Write-Host "Warning: Could not verify orchestrator is running. Check logs for errors." -ForegroundColor Red
    Write-Host "Check orchestrator.log and orchestrator_error.log for details" -ForegroundColor Red
}

Write-Host "Opening browser to trading bot dashboard..." -ForegroundColor Green
Start-Process "http://localhost:8001/bot-control"

Write-Host "Setup complete! If the dashboard doesn't load, check the log files for errors." -ForegroundColor Cyan