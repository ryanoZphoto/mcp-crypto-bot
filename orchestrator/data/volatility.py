import numpy as np
from typing import List

def calculate_volatility(prices: List[float], window: int = 20) -> float:
    """
    Calculate a proprietary volatility index as the standard deviation of log returns over a window.
    Args:
        prices (List[float]): List of historical prices (most recent last).
        window (int): Number of periods to use for volatility calculation.
    Returns:
        float: Volatility index (standard deviation of log returns).
    """
    if len(prices) < window + 1:
        raise ValueError(f"Not enough price data to calculate volatility (need at least {window + 1}).")
    try:
        log_returns = np.diff(np.log(prices[-(window+1):]))
        volatility = np.std(log_returns)
        return float(volatility)
    except Exception as e:
        print(f"Error calculating volatility: {e}")
        return 0.0 