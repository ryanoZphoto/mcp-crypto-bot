from mcp.server.fastmcp import FastMCP
import requests
from fastapi import FastAPI
import threading
import sys
import os
from dotenv import load_dotenv

# Try to load environment variables
try:
    load_dotenv(override=True)
    print("Successfully loaded .env file")
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")

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

# Add endpoints for shutdown and health check
try:
    from fastapi import APIRouter
    router = APIRouter()

    @router.post("/shutdown")
    async def shutdown():
        import os
        import signal
        threading.Thread(target=lambda: os._exit(0)).start()
        return {"message": "MCP server shutting down..."}
    
    @router.get("/health")
    async def health_check():
        """Simple health check endpoint"""
        return {"status": "healthy", "service": "mcp_server"}

    mcp.app.include_router(router)
except Exception as e:
    print(f"Error setting up API routes: {e}")

if __name__ == "__main__":
    print("Starting MCP server...")
    mcp.run(transport="streamable-http")