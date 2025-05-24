Here’s a comprehensive, in-depth rundown of how your crypto trading bot platform works, what files are involved, and what an AI developer would need to know to seamlessly continue development or debugging.
Crypto Trading Bot Platform: System Overview & Developer Handoff
1. High-Level Architecture
Purpose:
A production-ready, real-time crypto trading bot platform with a FastAPI backend, a web dashboard, Slack integration, and live trading on Binance.
Key Features:
Automated trading using a moving average crossover strategy with a volatility filter.
Web dashboard for control, monitoring, and live charting.
Slack notifications for trades and errors.
Robust logging and error handling.
Clean shutdown and start/stop controls for both the orchestrator and MCP server.
2. Main Components & File Responsibilities
A. Orchestrator (FastAPI App)
File: orchestrator/main.py
FastAPI server for bot control, logs, price feed, and dashboard endpoints.
Handles bot thread management (start/stop), status, and logs.
Provides /shutdown endpoint to stop both orchestrator and MCP server.
Renders dashboard via Jinja2 templates.
B. Trading Bot Logic
File: orchestrator/bots/manager.py
TradingBot class: Implements the moving average crossover strategy with volatility filter.
Runs in a background thread, checks for trade signals every 10 seconds.
Maintains global logs (bot_logs) and last run data (last_bot_run_data) for dashboard and charting.
Responds to a stop_event for clean shutdown.
Sends logs and trade actions to Slack.
C. Exchange Integration
File: orchestrator/exchange/binance.py
BinanceClient class: Handles fetching price data and placing orders on Binance.
D. Strategy Logic
File: orchestrator/strategies/moving_average.py
Implements the moving average crossover logic (should_buy, should_sell).
E. Volatility Calculation
File: orchestrator/data/volatility.py
Function to calculate price volatility for the filter.
F. Slack Integration
File: orchestrator/integrations/slack.py
Sends notifications to a configured Slack webhook.
G. MCP Client
File: orchestrator/mcp_client.py
Fetches live prices from the MCP server for dashboard display.
H. Web Dashboard
File: orchestrator/templates/bot_control.html
Jinja2/HTML template for the dashboard UI.
Uses JavaScript to poll backend endpoints for status, logs, and price feed.
Handles user actions: start/stop bot, refresh logs, shutdown all.
I. MCP Server
File: mcp_server.py
FastAPI server providing price data to orchestrator.
Has a /shutdown endpoint for remote shutdown.
3. Key Endpoints and Their Roles
/bot-control (GET/POST): Dashboard UI and bot start.
/stop-bot (POST): Stops the bot via stop_event.
/bot-status (GET): Returns bot running status.
/bot-logs (GET): Returns recent bot logs.
/price-feed (GET): Returns last run’s price and indicator data for charting.
/shutdown (POST): Shuts down both orchestrator and MCP server.
/frontend-error (POST): Receives and logs frontend JS errors.
4. How the Bot Works (Logic Flow)
Start:
User clicks “Run Bot Now” on dashboard.
Orchestrator starts a background thread running TradingBot.run().
Bot Loop:
Every 10 seconds:
Fetches latest prices from Binance.
Calculates short and long moving averages.
Checks for crossover (buy/sell signal).
Checks if volatility is above threshold.
If both signal and volatility are present, places a trade.
Logs all actions and sends to Slack.
Updates last_bot_run_data for dashboard chart.
Stop:
User clicks “Stop All.”
Orchestrator sets stop_event.
Bot loop detects this and exits cleanly, logging the stop.
Shutdown:
User clicks “Shutdown All.”
Orchestrator calls /shutdown on MCP server, then shuts itself down.
5. What Files to Inform the Next AI About
Critical files to review and understand before making changes:
orchestrator/main.py (API, threading, dashboard endpoints)
orchestrator/bots/manager.py (bot logic, logging, stop event)
orchestrator/templates/bot_control.html (dashboard UI, JS polling)
orchestrator/exchange/binance.py (exchange integration)
orchestrator/strategies/moving_average.py (strategy logic)
orchestrator/data/volatility.py (volatility calculation)
orchestrator/integrations/slack.py (Slack notifications)
orchestrator/mcp_client.py (MCP price fetch)
mcp_server.py (MCP server, price API, shutdown endpoint)
start_all.bat (startup script for both servers and dashboard)
Optional but useful:
requirements.txt (dependencies)
.env (API keys, secrets, Slack webhook, etc.)
6. Special Notes for the Next AI
Threading:
The bot runs in a background thread. Stopping is handled via a threading.Event (stop_event).
Logging:
All bot actions are logged to a global list and sent to Slack.
Polling:
The dashboard polls status/logs/price-feed only when the bot is running.
Error Handling:
Frontend JS errors are POSTed to /frontend-error for backend logging.
Shutdown:
Both orchestrator and MCP server can be shut down remotely via /shutdown.
Production Readiness:
The system is designed for robust, real-time operation with clear logs and error handling.
7. How to Continue Seamlessly
Review the files above to understand the current logic and endpoints.
Check the logs for any issues or errors before making changes.
If extending or debugging:
Make sure to maintain thread safety and clean shutdowns.
Keep the dashboard polling logic in sync with backend state.
Update both backend and frontend as needed for new features or bug fixes

9. Key Environment Variables and Secrets
.env file should contain:
BINANCE_API_KEY, BINANCE_API_SECRET (for live trading)
SLACK_WEBHOOK_URL (for notifications)
Any other sensitive config (do not hardcode in source files)
10. How to Add a New Strategy
Create a new file in orchestrator/strategies/ (e.g., rsi_strategy.py).
Implement the strategy logic (e.g., should_buy, should_sell).
Update TradingBot in manager.py to use the new strategy (pass as a parameter or via config).
Update dashboard if you want to display new metrics.
11. How to Add a New Exchange
Create a new client in orchestrator/exchange/ (e.g., coinbase.py).
Implement methods for fetching prices and placing orders.
Update TradingBot to allow selecting the exchange (via config or UI).
12. Testing and Debugging
Unit tests can be placed in the tests/ directory.
Use mock data for strategies and exchange clients to avoid real trades during testing.
Check logs in real time via the terminal or log files.
Use the dashboard to trigger and monitor bot actions.
13. Troubleshooting Common Issues
Port in use:
Only one process can use a port at a time. Kill old processes or reboot if you see [winerror 10048].
Bot not stopping:
Ensure stop_event is set and checked in the bot loop.
No trades happening:
Check volatility threshold and strategy logic; market may be too quiet.
Dashboard not updating:
Check JS polling logic and backend endpoints.
14. Security and Production Tips
Never expose API keys or secrets in logs or public repos.
Run servers behind a reverse proxy (e.g., Nginx) for production.
Use HTTPS for all endpoints in production.
Limit trade amounts and use testnet credentials for development.
Monitor logs for errors and suspicious activity.
15. Extending the Dashboard
Add more charts (e.g., volume, RSI, PnL).
Add user authentication for dashboard access.
Add controls for strategy parameters (e.g., change MA windows, volatility threshold).
Add a trade history table.

7. Example Requirements
fastapi
uvicorn
jinja2
requests
python-dotenv
numpy
ccxt (for exchange integration)
slack_sdk (if using advanced Slack features)
18. Handoff Checklist
[x] All code and config files are present.
[x] .env file is filled out with correct secrets.
[x] Both servers start and stop cleanly.
[x] Dashboard is reachable and functional.
[x] Bot can be started, stopped, and logs are visible.
[x] Slack notifications are working.
[x] All endpoints are documented and tested.
With this, any AI or developer can pick up the project, understand the architecture, and continue building or debugging with confidence.


+-------------------+         +-------------------+         +-------------------+
|                   |  HTTP   |                   |  HTTP   |                   |
|   Web Dashboard   +-------->+   Orchestrator    +-------->+    MCP Server     |
| (bot_control.html)|         |  (FastAPI, main.py)|        |   (mcp_server.py) |
+-------------------+         +-------------------+         +-------------------+
        ^                           |   ^   |                        ^
        |                           |   |   |                        |
        |   Polls status, logs,     |   |   |   Fetches prices       |
        |   price-feed, controls    |   |   |   from MCP, sends      |
        |   bot via endpoints       |   |   |   Slack notifications  |
        +---------------------------+   |   +------------------------+
                                        |
                                        v
                                +-------------------+
                                |                   |
                                |   Binance API     |
                                |                   |
                                +-------------------+