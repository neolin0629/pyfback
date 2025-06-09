"""
回测引擎模块 - 核心回测逻辑和交易执行
"""

from .backtest_engine import BacktestEngine
from .portfolio import Portfolio
from .trade import Trade, TradeType, TradeStatus
from .execution import ExecutionEngine
from .events import Event, EventType

__all__ = [
    "BacktestEngine",
    "Portfolio", 
    "Trade",
    "TradeType",
    "TradeStatus",
    "ExecutionEngine",
    "Event",
    "EventType",
]

__version__ = "0.1.0"