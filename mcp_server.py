from mcp.server.fastmcp import FastMCP
import requests
from fastapi import FastAPI
import uvicorn
import threading
import sys
import os
from dotenv import load_dotenv
import time

# Try to load environment variables
try:
    load_dotenv(override=True)
    print("Successfully loaded .env file")
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")

# Define the health API port
HEALTH_API_PORT = 8002

# Create standalone health check app for port 8002
health_app = FastAPI(title="MCP Health API")

@health_app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "mcp_server"}

@health_app.post("/shutdown")
async def shutdown():
    """Gracefully shutdown the server"""
    threading.Thread(target=lambda: os._exit(0)).start()
    return {"message": "MCP server shutting down..."}

# Create FastMCP instance
try:
    mcp = FastMCP("CryptoPriceServer")
    print("MCP server initialized successfully")
except Exception as e:
    print(f"Error initializing MCP server: {e}")
    sys.exit(1)

COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "ADA": "cardano"
}

@mcp.tool()
def get_coin_price(symbol: str = "BTC") -> float:
    """Fetch the current price in USD for a given coin symbol (BTC, ETH, SOL, DOGE, ADA)."""
    coin_id = COINS.get(symbol.upper())
    if not coin_id:
        raise ValueError(f"Unsupported coin symbol: {symbol}")
    url = (
        f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data[coin_id]["usd"]

print("API routes set up successfully")

# Start the FastAPI app in a separate thread for health checks
def run_health_api():
    uvicorn.run(health_app, host="0.0.0.0", port=HEALTH_API_PORT, log_level="info")

if __name__ == "__main__":
    print("Starting MCP server...")
    # Start FastAPI health API in a background thread
    health_thread = threading.Thread(target=run_health_api, daemon=True)
    health_thread.start()
    print(f"Health API server started on port {HEALTH_API_PORT}")
    
    # We'll sleep for a moment to let the health API bind to the port
    time.sleep(2)
    
    # Start MCP with streamable-http transport (it will use port 8000)
    print("Starting MCP with streamable-http transport...")
    try:
        # The FastMCP server will run in the main thread
        mcp.run(transport="streamable-http")
    except Exception as e:
        print(f"Error starting MCP: {e}")
        sys.exit(1)