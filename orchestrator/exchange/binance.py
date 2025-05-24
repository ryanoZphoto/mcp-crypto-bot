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
        self.demo_mode = os.getenv('DEMO_MODE', 'False').lower() == 'true'
        
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
            if self.demo_mode:
                print("Successfully connected to Binance API (DEMO MODE - No real trades will be executed)")
                logging.info("Running in DEMO MODE - No real trades will be executed")
            else:
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
            # In demo mode, create a simulated order response but don't execute the actual trade
            if self.demo_mode:
                current_price = self.get_price(symbol)
                logging.info(f"[DEMO MODE] Simulating {side} {type} order for {amount} {symbol} at ~${current_price}")
                
                # Create a simulated order response similar to what CCXT would return
                simulated_order = {
                    'id': f"demo-{side}-{int(current_price)}-{amount}",
                    'symbol': symbol,
                    'type': type,
                    'side': side,
                    'amount': amount,
                    'price': current_price,
                    'cost': amount * current_price,
                    'status': 'closed',
                    'timestamp': ccxt.Exchange.milliseconds(),
                    'datetime': ccxt.Exchange.iso8601(ccxt.Exchange.milliseconds()),
                    'fee': {
                        'cost': amount * current_price * 0.001,  # Simulated 0.1% fee
                        'currency': symbol.split('/')[1]
                    },
                    'info': {'demo': True},
                }
                return simulated_order
            else:
                # Execute real order
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
            # For demo orders, return a simulated completed status
            if self.demo_mode and order_id.startswith('demo-'):
                return {
                    'id': order_id,
                    'symbol': symbol,
                    'status': 'closed',
                    'filled': float(order_id.split('-')[-1]),
                    'remaining': 0,
                    'cost': float(order_id.split('-')[-2]) * float(order_id.split('-')[-1]),
                }
            return self.client.fetch_order(order_id, symbol)
        except Exception as e:
            print(f"Error fetching order status: {e}")
            logging.error(f"Failed to get status for order {order_id}: {str(e)}")
            return {} 