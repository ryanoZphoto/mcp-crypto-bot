import time
import datetime
from orchestrator.exchange.binance import BinanceClient
from orchestrator.strategies.moving_average import MovingAverageStrategy
from orchestrator.data.volatility import calculate_volatility
from orchestrator.integrations.slack import send_slack_message
import numpy as np
import json
import os
import threading

# At the top of the file
# Add a lock for the last_bot_run_data to prevent race conditions
last_bot_run_data_lock = threading.Lock()

# Each log entry will be a dict with timestamp, category, and message
bot_logs = []
bot_logs_history = []  # To store historical logs
log_categories = [
    "INFO", "ERROR", "TRADE", "SIGNAL", "PRICE", "METRIC", "SYSTEM"
]

# Define the path to store log files
LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
    "logs"
)
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Initialize with empty data structure
last_bot_run_data = {
    'timestamps': [],
    'prices': [],
    'short_ma': [],
    'long_ma': [],
    'signals': [],
    'volatility': None,
    'live_update': False,  # Flag to indicate if data is being updated in real-time
    'no_data': True        # Flag to indicate no real data is available
}

class TradingBot:
    """
    Trading bot manager that runs a moving average strategy with volatility filter on Binance.
    """
    def __init__(
        self,
        symbol: str = 'BTC/USDT',
        trade_amount: float = 0.001,
        short_window: int = 5,
        long_window: int = 20,
        vol_window: int = 20,
        min_vol: float = None,
        stop_event=None
    ):
        self.symbol = symbol
        self.trade_amount = trade_amount
        self.short_window = short_window
        self.long_window = long_window
        self.vol_window = vol_window
        
        # Use environment variable for min_vol if not provided
        if min_vol is None:
            # Try to get from environment, default to 0.01 if not found
            self.min_vol = float(os.getenv('MIN_VOLATILITY', '0.01'))
            print(f"Using MIN_VOLATILITY from environment: {self.min_vol}")
        else:
            self.min_vol = min_vol
            
        self.stop_event = stop_event
        self.run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Archive previous logs if any
        if bot_logs:
            bot_logs_history.extend(bot_logs)
            # Save to file
            self._save_logs_to_file()
            bot_logs.clear()
            
        self.log("Bot initialized", "SYSTEM")
        self.log(f"Using volatility threshold: {self.min_vol}", "SYSTEM")
        
        # Initialize exchange with improved error handling
        try:
            self.exchange = BinanceClient()
            self.log("Successfully connected to Binance exchange", "SYSTEM")
        except Exception as e:
            import traceback
            self.log(f"Failed to initialize Binance client: {e}", "ERROR")
            self.log(f"Error details: {traceback.format_exc()}", "ERROR")
            self.log("Check your .env file for valid API credentials", "ERROR")
            raise  # Re-raise to prevent bot from running with no exchange
            
        self.strategy = MovingAverageStrategy()
        self.prices = []
        self.timestamps = []

    def fetch_recent_prices(self, limit: int = 100):
        """Fetch recent close prices for the symbol."""
        try:
            self.log(f"Fetching recent price data for {self.symbol}...", "PRICE")
            ohlcv = self.exchange.client.fetch_ohlcv(
                self.symbol, timeframe='1m', limit=limit
            )
            
            if not ohlcv or len(ohlcv) == 0:
                self.log(f"No OHLCV data returned for {self.symbol}", "ERROR")
                self.prices = []
                self.timestamps = []
                return
                
            self.prices = [candle[4] for candle in ohlcv]  # close prices
            self.timestamps = [candle[0] for candle in ohlcv]
            
            # Log more detailed information about the data
            min_price = min(self.prices) if self.prices else 0
            max_price = max(self.prices) if self.prices else 0
            avg_price = sum(self.prices) / len(self.prices) if self.prices else 0
            
            self.log(
                f"Fetched {len(self.prices)} recent close prices for {self.symbol}. "
                f"Range: ${min_price:.2f} - ${max_price:.2f}, Avg: ${avg_price:.2f}", 
                "PRICE"
            )
        except Exception as e:
            import traceback
            self.log(f"Error fetching prices: {e}", "ERROR")
            self.log(f"Error details: {traceback.format_exc()}", "ERROR")
            self.prices = []
            self.timestamps = []

    def run(self):
        global last_bot_run_data
        
        try:
            # Set real-time flag to true when bot starts
            with last_bot_run_data_lock:
                last_bot_run_data['live_update'] = True
                # 'no_data' will be set to False once data is successfully fetched.
                # If it was True, let it remain True until first fetch.
            
            while not self.stop_event.is_set():
                print("TradingBot.run() called")
                self.log("--- New Bot Run ---", "SYSTEM")
                self.log(
                    f"Trading pair: {self.symbol}, Trade amount: {self.trade_amount}", 
                    "INFO"
                )
                if self.stop_event and self.stop_event.is_set():
                    self.log("Bot stopped before starting.", "SYSTEM")
                    print("Bot stopped before starting.")
                    return
                self.fetch_recent_prices()
                if len(self.prices) < self.long_window + 1:
                    self.log(
                        f"Not enough price data to run strategy. Need at least "
                        f"{self.long_window + 1}, got {len(self.prices)}.", 
                        "ERROR"
                    )
                    time.sleep(10)
                    continue
                try:
                    volatility = calculate_volatility(
                        self.prices, window=self.vol_window
                    )
                    self.log(
                        f"Calculated volatility: {volatility:.4f} "
                        f"(threshold: {self.min_vol})", 
                        "METRIC"
                    )
                    short_ma = self._ma(self.prices, self.short_window)
                    long_ma = self._ma(self.prices, self.long_window)
                    prev_short_ma = self._ma(self.prices[:-1], self.short_window)
                    prev_long_ma = self._ma(self.prices[:-1], self.long_window)
                    self.log(
                        f"Short MA ({self.short_window}): {short_ma:.2f} | "
                        f"Long MA ({self.long_window}): {long_ma:.2f}", 
                        "METRIC"
                    )
                    self.log(
                        f"Previous Short MA: {prev_short_ma:.2f} | "
                        f"Previous Long MA: {prev_long_ma:.2f}", 
                        "METRIC"
                    )
                    current_price = self.prices[-1]
                    self.log(f"Current price: {current_price:.2f}", "PRICE")
                    
                    # Calculate all MAs for chart
                    short_ma_arr = list(np.convolve(
                        self.prices, np.ones(self.short_window)/self.short_window, mode='valid'
                    ))
                    long_ma_arr = list(np.convolve(
                        self.prices, np.ones(self.long_window)/self.long_window, mode='valid'
                    ))
                    short_ma_arr = [None]*(self.short_window-1) + short_ma_arr
                    long_ma_arr = [None]*(self.long_window-1) + long_ma_arr
                    
                    # Detect trade signals for chart
                    signals = []
                    for i in range(1, len(self.prices)):
                        if (short_ma_arr[i-1] is not None and 
                            long_ma_arr[i-1] is not None and 
                            short_ma_arr[i] is not None and 
                            long_ma_arr[i] is not None):
                            
                            if (short_ma_arr[i-1] <= long_ma_arr[i-1] and 
                                short_ma_arr[i] > long_ma_arr[i]):
                                signals.append({
                                    'type': 'buy', 
                                    'index': i, 
                                    'price': self.prices[i]
                                })
                                self.log(
                                    f"Chart signal detected: BUY at index {i}, "
                                    f"price {self.prices[i]:.2f}", 
                                    "SIGNAL"
                                )
                            elif (short_ma_arr[i-1] >= long_ma_arr[i-1] and 
                                  short_ma_arr[i] < long_ma_arr[i]):
                                signals.append({
                                    'type': 'sell', 
                                    'index': i, 
                                    'price': self.prices[i]
                                })
                                self.log(
                                    f"Chart signal detected: SELL at index {i}, "
                                    f"price {self.prices[i]:.2f}", 
                                    "SIGNAL"
                                )
                    
                    # Save all data for chart visualization with thread safety
                    print(f"Updating last_bot_run_data with {len(self.prices)} prices and {len(signals)} signals")
                    
                    # Use lock to safely update the shared data structure
                    with last_bot_run_data_lock:
                        last_bot_run_data.clear() # Clear the existing dictionary
                        last_bot_run_data.update({ # Update it with new key-value pairs
                            'timestamps': self.timestamps,
                            'prices': self.prices,
                            'short_ma': short_ma_arr,
                            'long_ma': long_ma_arr,
                            'signals': signals,
                            'volatility': volatility,
                            'live_update': True,
                            'no_data': False if self.prices else True # Set no_data based on prices
                        })
                    
                    # Debug the structure of last_bot_run_data
                    print(f"DEBUG last_bot_run_data: prices={len(self.prices)}, "
                          f"short_ma={len(short_ma_arr)}, "
                          f"long_ma={len(long_ma_arr)}, "
                          f"signals={len(signals)}")
                    
                    if volatility < self.min_vol:
                        self.log(
                            f"Volatility too low ({volatility:.4f}), skipping trade.", 
                            "INFO"
                        )
                        time.sleep(10)
                        continue
                    if self.strategy.should_buy(
                        self.prices, self.short_window, self.long_window
                    ):
                        self.log(
                            "Buy signal detected (short MA crossed above long MA).", 
                            "TRADE"
                        )
                        order = self.exchange.create_order(
                            self.symbol, 'buy', self.trade_amount
                        )
                        self.log(
                            f"Placing BUY order: {self.trade_amount} "
                            f"{self.symbol.split('/')[0]} at ~${current_price:.2f}", 
                            "TRADE"
                        )
                        self.log(f"BUY order placed: {order}", "TRADE")
                    elif self.strategy.should_sell(
                        self.prices, self.short_window, self.long_window
                    ):
                        self.log(
                            "Sell signal detected (short MA crossed below long MA).", 
                            "TRADE"
                        )
                        order = self.exchange.create_order(
                            self.symbol, 'sell', self.trade_amount
                        )
                        self.log(
                            f"Placing SELL order: {self.trade_amount} "
                            f"{self.symbol.split('/')[0]} at ~${current_price:.2f}", 
                            "TRADE"
                        )
                        self.log(f"SELL order placed: {order}", "TRADE")
                    else:
                        self.log("No trade signal this cycle.", "INFO")
                except Exception as e:
                    self.log(f"Error in bot run: {e}", "ERROR")
                time.sleep(10)  # Wait 10 seconds before next check
            self.log("Bot loop detected stop_event, exiting loop.", "SYSTEM")
        except Exception as e:
            self.log(f"FATAL: Bot loop crashed: {e}", "ERROR")
            print(f"FATAL: Bot loop crashed: {e}")
        finally:
            # Set real-time flag to false when bot stops
            with last_bot_run_data_lock:
                last_bot_run_data['live_update'] = False
                # If prices are empty or not present when bot stops, 
                # mark as no_data for the next potential static display.
                if not last_bot_run_data.get('prices'):
                    last_bot_run_data['no_data'] = True
            # Save logs to history
            self._save_logs_to_file()

    def _ma(self, prices, window):
        import numpy as np
        if len(prices) < window:
            return 0.0
        return float(np.mean(prices[-window:]))

    def log(self, message, category="INFO"):
        from datetime import datetime
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # Ensure category is valid
        if category not in log_categories:
            category = "INFO"
            
        # Create log entry
        log_entry = {
            "timestamp": timestamp_str,
            "category": category,
            "message": message,
            "run_id": self.run_id
        }
        
        # Format log for display and Slack
        entry_str = f"[{timestamp_str}] [{category}] {message}"
        bot_logs.append(log_entry)
        
        # Keep only the last 100 logs in memory
        if len(bot_logs) > 100:
            bot_logs.pop(0)
            
        send_slack_message(entry_str)
    
    def _save_logs_to_file(self):
        """Save current logs to a file with timestamp"""
        if not bot_logs:
            return
            
        # Create filename with timestamp
        filename = f"bot_logs_{self.run_id}.json"
        filepath = os.path.join(LOG_DIR, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(bot_logs, f, indent=2)
            print(f"Logs saved to {filepath}")
        except Exception as e:
            print(f"Error saving logs to file: {e}") 