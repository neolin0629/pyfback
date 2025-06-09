"""
策略模块 - 交易策略定义和信号生成
"""

from .base import StrategyBase
from .signals import Signal, SignalType
from .position import Position, PositionSide

# 导入示例策略（如果存在）
try:
    from .examples import *
except ImportError:
    pass

__all__ = [
    "StrategyBase",
    "Signal", 
    "SignalType",
    "Position",
    "PositionSide",
]

__version__ = "0.1.0"