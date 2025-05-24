from orchestrator.mcp_client import get_new_sheet_rows, send_slack_message, COINS

def run_sample_workflow(symbol="BTC"):
    # Fetch the current coin price from the MCP server
    coin_row = get_new_sheet_rows(symbol)[0]
    price = coin_row[1]
    # If price is a TextContent object, extract the text
    if hasattr(price, 'text'):
        price = price.text
    try:
        price_float = float(price)
        price_str = f"${price_float:,.6f}" if price_float < 1 else f"${price_float:,.2f}"
    except Exception:
        price_str = f"${price}"
    send_slack_message(f"Current {symbol} price: {price_str}")
    return f"Current {symbol} price (USD): {price_str}" 