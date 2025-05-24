# MCP Crypto Trading Bot Platform

## Overview
A modular, production-ready crypto trading bot platform with:
- Real-time trading on Binance (Binance US)
- Slack integration for alerts and logs
- Web dashboard for bot control and monitoring
- Proprietary volatility index and moving average strategy
- Easily extensible for new exchanges, strategies, and integrations

---

## Project Structure

```
mcp/
│
├── orchestrator/
│   ├── main.py                # FastAPI app entrypoint, web UI, API
│   ├── bots/
│   │   └── manager.py         # TradingBot logic, logging, Slack alerts
│   ├── exchange/
│   │   └── binance.py         # Binance connector (ccxt)
│   ├── integrations/
│   │   └── slack.py           # Slack webhook integration
│   ├── data/
│   │   └── volatility.py      # Proprietary volatility index
│   ├── strategies/
│   │   └── moving_average.py  # Example strategy
│   ├── templates/
│   │   └── bot_control.html   # Dashboard UI (Jinja2)
│   └── ...
├── .env                       # Environment variables (see below)
├── requirements.txt           # Python dependencies
├── start_all.ps1              # Windows script to launch everything
└── README.md                  # This file
```

---

## Environment Variables (`.env`)
Copy `.env.example` to `.env` and fill in your credentials:

```
binanceusdt_api_key=YOUR_BINANCE_API_KEY
binanceusdt_api_secret=YOUR_BINANCE_API_SECRET

# Slack Integration
slack_webhook_url=https://hooks.slack.com/services/XXX/XXX/XXX
# (Optional: for advanced Slack features)
slack_bot_token=...
slack_signing_secret=...
slack_app_id=...
slack_client_id=...
slack_client_secret=...
slack_verification_token=...
slack_app_token=...
```

- **binanceusdt_api_key / binanceusdt_api_secret**: Your Binance US API credentials.
- **slack_webhook_url**: Your Slack Incoming Webhook URL for alerts/logs.

---

## Connections & Integrations

- **Binance (orchestrator/exchange/binance.py):**
  - Uses [ccxt](https://github.com/ccxt/ccxt) to connect to Binance US for trading, price, and balance.
  - Credentials loaded from `.env`.
- **Slack (orchestrator/integrations/slack.py):**
  - Sends all bot actions, errors, and alerts to your Slack channel via webhook.
  - Webhook URL loaded from `.env`.
- **Web Dashboard (orchestrator/main.py, templates/bot_control.html):**
  - FastAPI + Jinja2 UI for running the bot, viewing status, and seeing logs.
- **MCP Server:**
  - Used for other orchestrator workflows (not directly for the trading bot, but available for extension).

---

## Running the Platform

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
2. **Set up your `.env` file** by copying `.env.example` and adding your secrets.
3. **Start everything (Windows):**
   ```powershell
   ./start_all.ps1
   ```
   - This launches the MCP server, orchestrator, and opens the dashboard.
4. **Access the dashboard:**
   - Go to [http://localhost:8001/bot-control](http://localhost:8001/bot-control)
   - Click "Run Bot Now" to execute a trading cycle.
   - View logs and status directly in the dashboard.
   - All actions and errors are also sent to your Slack channel.

---

## Logging & Notifications
- **All bot actions, trades, and errors** are logged in memory and displayed in the dashboard (auto-refreshes every 10 seconds).
- **Slack notifications**: Every log entry is also sent to your configured Slack channel.
- **Logs are not persisted across restarts** (for persistent logging, extend to file or database).

## Running Tests
Install dependencies first, then execute the test suite with `pytest`:

```sh
pip install -r requirements.txt
pytest
```

---

## Prerequisites
- Python 3.8+
- [ccxt](https://github.com/ccxt/ccxt) (installed via requirements.txt)
- A Binance US account and API key/secret
- A Slack workspace and an Incoming Webhook URL
- Windows PowerShell (for `start_all.ps1`)

---

## Extending the Platform
- Add new strategies in `orchestrator/strategies/`
- Add new exchanges in `orchestrator/exchange/`
- Add more integrations in `orchestrator/integrations/`
- Expand the dashboard UI in `orchestrator/templates/bot_control.html`

---

## Support
For questions or help, open an issue or contact the maintainer. 