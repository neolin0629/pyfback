"""
交易信号类定义
"""

import datetime as dt
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class SignalType(Enum):
    """信号类型枚举"""
    BUY = "buy"          # 买入
    SELL = "sell"        # 卖出
    HOLD = "hold"        # 持有
    CLOSE = "close"      # 平仓
    CLOSE_LONG = "close_long"    # 平多仓
    CLOSE_SHORT = "close_short"  # 平空仓


@dataclass
class Signal:
    """
    交易信号数据结构
    
    表示策略产生的交易信号，包含交易方向、数量、价格类型等信息。
    """
    symbol: str                           # 合约代码
    signal_type: SignalType              # 信号类型
    quantity: float                      # 数量（正数表示多头，负数表示空头）
    timestamp: dt.datetime               # 信号产生时间
    price_type: str = "market"           # 价格类型：market, limit
    limit_price: Optional[float] = None  # 限价（仅当price_type为limit时使用）
    stop_price: Optional[float] = None   # 止损价
    take_profit: Optional[float] = None  # 止盈价
    priority: int = 0                    # 信号优先级（数值越大优先级越高）
    metadata: Optional[Dict[str, Any]] = None  # 额外信息
    
    def __post_init__(self):
        """数据验证"""
        if self.quantity == 0:
            raise ValueError("交易数量不能为0")
        
        if self.price_type == "limit" and self.limit_price is None:
            raise ValueError("限价单必须指定限价")
        
        if self.stop_price is not None and self.stop_price <= 0:
            raise ValueError("止损价必须大于0")
        
        if self.take_profit is not None and self.take_profit <= 0:
            raise ValueError("止盈价必须大于0")
    
    @property
    def direction(self) -> int:
        """
        交易方向
        
        Returns:
            1: 做多, -1: 做空, 0: 平仓
        """
        if self.signal_type in [SignalType.BUY]:
            return 1 if self.quantity > 0 else -1
        elif self.signal_type in [SignalType.SELL]:
            return -1 if self.quantity > 0 else 1
        elif self.signal_type in [SignalType.CLOSE, SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT]:
            return 0
        else:
            return 1 if self.quantity > 0 else -1
    
    @property
    def is_long_signal(self) -> bool:
        """是否为做多信号"""
        return self.direction > 0
    
    @property
    def is_short_signal(self) -> bool:
        """是否为做空信号"""
        return self.direction < 0
    
    @property
    def is_close_signal(self) -> bool:
        """是否为平仓信号"""
        return self.direction == 0
    
    @property
    def is_market_order(self) -> bool:
        """是否为市价单"""
        return self.price_type == "market"
    
    @property
    def is_limit_order(self) -> bool:
        """是否为限价单"""
        return self.price_type == "limit"
    
    @property
    def abs_quantity(self) -> float:
        """绝对数量"""
        return abs(self.quantity)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'quantity': self.quantity,
            'timestamp': self.timestamp,
            'price_type': self.price_type,
            'limit_price': self.limit_price,
            'stop_price': self.stop_price,
            'take_profit': self.take_profit,
            'priority': self.priority,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Signal':
        """从字典创建Signal对象"""
        data = data.copy()
        if 'signal_type' in data:
            data['signal_type'] = SignalType(data['signal_type'])
        return cls(**data)
    
    @classmethod
    def buy_signal(cls, symbol: str, quantity: float, 
                   timestamp: Optional[dt.datetime] = None,
                   **kwargs) -> 'Signal':
        """创建买入信号"""
        return cls(
            symbol=symbol,
            signal_type=SignalType.BUY,
            quantity=abs(quantity),
            timestamp=timestamp or dt.datetime.now(),
            **kwargs
        )
    
    @classmethod
    def sell_signal(cls, symbol: str, quantity: float,
                    timestamp: Optional[dt.datetime] = None,
                    **kwargs) -> 'Signal':
        """创建卖出信号"""
        return cls(
            symbol=symbol,
            signal_type=SignalType.SELL,
            quantity=abs(quantity),
            timestamp=timestamp or dt.datetime.now(),
            **kwargs
        )
    
    @classmethod
    def close_signal(cls, symbol: str, quantity: Optional[float] = None,
                     timestamp: Optional[dt.datetime] = None,
                     **kwargs) -> 'Signal':
        """创建平仓信号"""
        return cls(
            symbol=symbol,
            signal_type=SignalType.CLOSE,
            quantity=quantity or 0,  # 0表示全部平仓
            timestamp=timestamp or dt.datetime.now(),
            **kwargs
        )
    
    @classmethod
    def hold_signal(cls, symbol: str,
                    timestamp: Optional[dt.datetime] = None,
                    **kwargs) -> 'Signal':
        """创建持有信号"""
        return cls(
            symbol=symbol,
            signal_type=SignalType.HOLD,
            quantity=0,
            timestamp=timestamp or dt.datetime.now(),
            **kwargs
        )
    
    def __repr__(self) -> str:
        direction_str = "多" if self.is_long_signal else "空" if self.is_short_signal else "平"
        return (
            f"Signal({self.symbol} {direction_str} {self.abs_quantity} "
            f"{self.signal_type.value} {self.price_type} "
            f"@ {self.timestamp.strftime('%H:%M:%S')})"
        )


class SignalGenerator:
    """
    信号生成器基类
    
    提供信号生成的通用功能和工具方法。
    """
    
    def __init__(self, symbol: str):
        """
        初始化信号生成器
        
        Args:
            symbol: 合约代码
        """
        self.symbol = symbol
        self.last_signal: Optional[Signal] = None
        self.signal_history: list = []
    
    def generate_signal(self, **kwargs) -> Optional[Signal]:
        """
        生成交易信号（需要子类实现）
        
        Returns:
            交易信号或None
        """
        raise NotImplementedError("子类必须实现generate_signal方法")
    
    def add_signal(self, signal: Signal) -> None:
        """添加信号到历史记录"""
        self.last_signal = signal
        self.signal_history.append(signal)
    
    def get_last_signal(self) -> Optional[Signal]:
        """获取最后一个信号"""
        return self.last_signal
    
    def get_signal_history(self) -> list:
        """获取信号历史"""
        return self.signal_history.copy()
    
    def clear_history(self) -> None:
        """清除信号历史"""
        self.signal_history.clear()
        self.last_signal = None


class SimpleSignalGenerator(SignalGenerator):
    """
    简单信号生成器示例
    
    基于价格突破的简单信号生成逻辑。
    """
    
    def __init__(self, symbol: str, 
                 buy_threshold: float = 1.02,
                 sell_threshold: float = 0.98):
        """
        初始化简单信号生成器
        
        Args:
            symbol: 合约代码
            buy_threshold: 买入阈值倍数
            sell_threshold: 卖出阈值倍数
        """
        super().__init__(symbol)
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.reference_price: Optional[float] = None
    
    def set_reference_price(self, price: float) -> None:
        """设置参考价格"""
        self.reference_price = price
    
    def generate_signal(self, current_price: float, 
                       quantity: float = 1,
                       **kwargs) -> Optional[Signal]:
        """
        基于价格突破生成信号
        
        Args:
            current_price: 当前价格
            quantity: 交易数量
            **kwargs: 额外参数
        
        Returns:
            交易信号或None
        """
        if self.reference_price is None:
            self.reference_price = current_price
            return None
        
        # 价格上涨超过阈值，生成买入信号
        if current_price > self.reference_price * self.buy_threshold:
            signal = Signal.buy_signal(
                symbol=self.symbol,
                quantity=quantity,
                **kwargs
            )
            self.add_signal(signal)
            self.reference_price = current_price  # 更新参考价格
            return signal
        
        # 价格下跌超过阈值，生成卖出信号
        elif current_price < self.reference_price * self.sell_threshold:
            signal = Signal.sell_signal(
                symbol=self.symbol,
                quantity=quantity,
                **kwargs
            )
            self.add_signal(signal)
            self.reference_price = current_price  # 更新参考价格
            return signal
        
        return None