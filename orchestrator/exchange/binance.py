import os
import ccxt
from typing import Optional
import logging

class BinanceClient:
    """
    Binance exchange connector using ccxt. Loads credentials from environment variables.
    """
    def __init__(self):
        api_key = os.getenv('binanceusdt_api_key')
        api_secret = os.getenv('binanceusdt_api_secret')
        if not api_key or not api_secret:
            raise ValueError("Binance API key/secret not set in environment variables.")
        try:
            self.client = ccxt.binanceus({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            })
            # Test the connection to ensure credentials work
            self.client.fetch_balance()
            print("Successfully connected to Binance API")
        except Exception as e:
            print(f"Error initializing Binance client: {e}")
            logging.error(f"Binance connection error: {str(e)}")
            raise

    def get_balance(self, asset: str = 'USDT') -> float:
        """Get balance for a specific asset."""
        try:
            balance = self.client.fetch_balance()
            return balance['total'].get(asset, 0.0)
        except Exception as e:
            print(f"Error fetching balance: {e}")
            logging.error(f"Failed to get balance for {asset}: {str(e)}")
            return 0.0

    def get_price(self, symbol: str = 'BTC/USDT') -> float:
        """Get the latest price for a symbol."""
        try:
            ticker = self.client.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            print(f"Error fetching price: {e}")
            logging.error(f"Failed to get price for {symbol}: {str(e)}")
            return 0.0

    def create_order(self, symbol: str, side: str, amount: float, price: Optional[float] = None, type: str = 'market'):
        """Create an order (market or limit)."""
        try:
            if type == 'market':
                order = self.client.create_market_order(symbol, side, amount)
            else:
                order = self.client.create_limit_order(symbol, side, amount, price)
            return order
        except Exception as e:
            print(f"Error creating order: {e}")
            logging.error(f"Failed to create {side} {type} order for {symbol}: {str(e)}")
            return None

    def get_order_status(self, order_id: str, symbol: str) -> dict:
        """Get the status of an order by ID."""
        try:
            return self.client.fetch_order(order_id, symbol)
        except Exception as e:
            print(f"Error fetching order status: {e}")
            logging.error(f"Failed to get status for order {order_id}: {str(e)}")
            return {} 