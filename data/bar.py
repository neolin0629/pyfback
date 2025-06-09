"""
K线数据结构定义
"""

import datetime as dt
from dataclasses import dataclass
from typing import Optional


@dataclass
class Bar:
    """
    K线数据结构
    
    表示单个时间周期的期货行情数据，包含开高低收价格、成交量和持仓量信息。
    """
    symbol: str                    # 合约代码
    datetime: dt.datetime         # 时间戳
    open: float                   # 开盘价
    high: float                   # 最高价
    low: float                    # 最低价
    close: float                  # 收盘价
    volume: int                   # 成交量
    open_interest: int            # 持仓量
    freq: str = "1min"           # 频率标识
    
    def __post_init__(self):
        """数据验证"""
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("最高价不能小于开盘价、收盘价或最低价")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("最低价不能大于开盘价、收盘价或最高价")
        if self.volume < 0:
            raise ValueError("成交量不能为负数")
        if self.open_interest < 0:
            raise ValueError("持仓量不能为负数")
    
    @property
    def typical_price(self) -> float:
        """典型价格：(最高价 + 最低价 + 收盘价) / 3"""
        return (self.high + self.low + self.close) / 3.0
    
    @property
    def weighted_price(self) -> float:
        """加权价格：(开盘价 + 最高价 + 最低价 + 收盘价) / 4"""
        return (self.open + self.high + self.low + self.close) / 4.0
    
    @property
    def price_range(self) -> float:
        """价格区间：最高价 - 最低价"""
        return self.high - self.low
    
    @property
    def body_size(self) -> float:
        """实体大小：|收盘价 - 开盘价|"""
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        """上影线长度"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """下影线长度"""
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        """是否为阳线"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """是否为阴线"""
        return self.close < self.open
    
    @property
    def is_doji(self) -> bool:
        """是否为十字星（开盘价等于收盘价）"""
        return self.close == self.open
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'symbol': self.symbol,
            'datetime': self.datetime,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'open_interest': self.open_interest,
            'freq': self.freq,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Bar':
        """从字典创建Bar对象"""
        return cls(**data)
    
    def __repr__(self) -> str:
        return (
            f"Bar(symbol='{self.symbol}', datetime={self.datetime}, "
            f"OHLC=[{self.open:.2f}, {self.high:.2f}, {self.low:.2f}, {self.close:.2f}], "
            f"volume={self.volume}, freq='{self.freq}')"
        )