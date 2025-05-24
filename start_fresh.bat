@echo off
echo Killing any Python processes...
taskkill /f /im python.exe
taskkill /f /im pythonw.exe

echo Killing any processes on ports 8000 and 8001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /PID %%a
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do taskkill /f /PID %%a

echo Starting servers...
start "MCP Server" cmd /k "python mcp_server.py"
timeout /t 5 > nul
start "Orchestrator" cmd /k "python -m uvicorn orchestrator.main:app --port 8001"
timeout /t 8 > nul

echo Opening browser...
start "" http://localhost:8001/bot-control
echo.
echo If the dashboard doesn't load, check the server console windows for error messages. 