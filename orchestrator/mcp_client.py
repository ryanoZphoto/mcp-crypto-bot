"""
MCP Client integration for orchestrator.

This module connects to a real MCP server using the official Python SDK.
"""

import asyncio
import os
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from orchestrator.integrations.slack import send_slack_message

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

COINS = ["BTC", "ETH", "SOL", "DOGE", "ADA"]

def get_new_sheet_rows(symbol="BTC"):
    """Fetch the current coin price from the MCP server (sync wrapper)."""
    return asyncio.run(get_coin_price(symbol))

async def get_coin_price(symbol="BTC"):
    async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_coin_price", {"symbol": symbol})
            value = getattr(result.content, "text", result.content)
            print("DEBUG: result.content =", result.content, "value =", value)
            return [symbol, value]

