# Orchestrator package init
# Expose main components for easy import and IDE discovery

from .exchange import binance
from .integrations import slack
from .data import volatility
from .strategies import moving_average
from .bots import manager 
