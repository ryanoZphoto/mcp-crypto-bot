from typing import List
import numpy as np

class MovingAverageStrategy:
    """
    Simple moving average crossover strategy.
    Buy when short MA crosses above long MA, sell when short MA crosses below long MA.
    """
    def should_buy(self, prices: List[float], short_window: int = 5, long_window: int = 20) -> bool:
        """
        Determine if a buy signal is present.
        """
        if len(prices) < long_window + 1:
            return False
        short_ma = np.mean(prices[-short_window:])
        long_ma = np.mean(prices[-long_window:])
        prev_short_ma = np.mean(prices[-short_window-1:-1])
        prev_long_ma = np.mean(prices[-long_window-1:-1])
        return prev_short_ma <= prev_long_ma and short_ma > long_ma

    def should_sell(self, prices: List[float], short_window: int = 5, long_window: int = 20) -> bool:
        """
        Determine if a sell signal is present.
        """
        if len(prices) < long_window + 1:
            return False
        short_ma = np.mean(prices[-short_window:])
        long_ma = np.mean(prices[-long_window:])
        prev_short_ma = np.mean(prices[-short_window-1:-1])
        prev_long_ma = np.mean(prices[-long_window-1:-1])
        return prev_short_ma >= prev_long_ma and short_ma < long_ma 