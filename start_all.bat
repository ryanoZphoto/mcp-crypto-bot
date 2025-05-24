@echo off
start "MCP Server" cmd /k "python mcp_server.py"
timeout /t 2 > nul
start "Orchestrator" cmd /k "python -m uvicorn orchestrator.main:app --port 8001"
timeout /t 2 > nul
start "" http://localhost:8001/bot-control