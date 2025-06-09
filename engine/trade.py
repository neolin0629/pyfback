"""
交易记录类定义
"""

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import uuid


class TradeType(Enum):
    """交易类型枚举"""
    BUY = "buy"          # 买入开仓
    SELL = "sell"        # 卖出开仓  
    CLOSE_LONG = "close_long"    # 平多仓
    CLOSE_SHORT = "close_short"  # 平空仓


class TradeStatus(Enum):
    """交易状态枚举"""
    PENDING = "pending"      # 等待执行
    FILLED = "filled"        # 已成交
    CANCELLED = "cancelled"  # 已取消
    REJECTED = "rejected"    # 被拒绝


@dataclass
class Trade:
    """
    交易记录数据结构
    
    记录单笔交易的详细信息，包括交易类型、数量、价格、手续费等。
    """
    trade_id: str                        # 交易ID
    symbol: str                          # 合约代码
    trade_type: TradeType               # 交易类型
    quantity: float                     # 交易数量
    price: float                        # 成交价格
    timestamp: dt.datetime              # 交易时间
    status: TradeStatus = TradeStatus.PENDING  # 交易状态
    commission: float = 0.0             # 手续费
    slippage: float = 0.0              # 滑点
    realized_pnl: float = 0.0          # 已实现盈亏
    order_price: Optional[float] = None # 委托价格
    fill_time: Optional[dt.datetime] = None  # 成交时间
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)  # 额外信息
    
    def __post_init__(self):
        """数据验证"""
        if self.quantity <= 0:
            raise ValueError("交易数量必须大于0")
        
        if self.price <= 0:
            raise ValueError("交易价格必须大于0")
        
        if self.commission < 0:
            raise ValueError("手续费不能为负数")
    
    @property
    def trade_value(self) -> float:
        """交易金额"""
        return self.quantity * self.price
    
    @property
    def total_cost(self) -> float:
        """总成本（包含手续费和滑点）"""
        slippage_cost = self.quantity * abs(self.slippage)
        return self.trade_value + self.commission + slippage_cost
    
    @property
    def is_buy(self) -> bool:
        """是否为买入"""
        return self.trade_type in [TradeType.BUY]
    
    @property
    def is_sell(self) -> bool:
        """是否为卖出"""
        return self.trade_type in [TradeType.SELL]
    
    @property
    def is_close(self) -> bool:
        """是否为平仓"""
        return self.trade_type in [TradeType.CLOSE_LONG, TradeType.CLOSE_SHORT]
    
    @property
    def is_long_side(self) -> bool:
        """是否为多头方向"""
        return self.trade_type in [TradeType.BUY, TradeType.CLOSE_SHORT]
    
    @property
    def is_short_side(self) -> bool:
        """是否为空头方向"""
        return self.trade_type in [TradeType.SELL, TradeType.CLOSE_LONG]
    
    @property
    def is_filled(self) -> bool:
        """是否已成交"""
        return self.status == TradeStatus.FILLED
    
    @property
    def is_pending(self) -> bool:
        """是否等待中"""
        return self.status == TradeStatus.PENDING
    
    def fill(self, fill_price: Optional[float] = None, 
             fill_time: Optional[dt.datetime] = None) -> None:
        """
        标记交易为已成交
        
        Args:
            fill_price: 实际成交价格，如果为None则使用原价格
            fill_time: 成交时间，如果为None则使用当前时间
        """
        if fill_price is not None:
            self.price = fill_price
        
        self.fill_time = fill_time or dt.datetime.now()
        self.status = TradeStatus.FILLED
    
    def cancel(self) -> None:
        """取消交易"""
        self.status = TradeStatus.CANCELLED
    
    def reject(self, reason: str = "") -> None:
        """
        拒绝交易
        
        Args:
            reason: 拒绝原因
        """
        self.status = TradeStatus.REJECTED
        if reason:
            self.metadata["reject_reason"] = reason
    
    def calculate_pnl(self, exit_price: float) -> float:
        """
        计算盈亏（用于平仓时计算）
        
        Args:
            exit_price: 平仓价格
        
        Returns:
            盈亏金额
        """
        if self.is_long_side:
            return self.quantity * (exit_price - self.price)
        else:
            return self.quantity * (self.price - exit_price)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'trade_type': self.trade_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'timestamp': self.timestamp,
            'status': self.status.value,
            'commission': self.commission,
            'slippage': self.slippage,
            'realized_pnl': self.realized_pnl,
            'order_price': self.order_price,
            'fill_time': self.fill_time,
            'trade_value': self.trade_value,
            'total_cost': self.total_cost,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """从字典创建Trade对象"""
        data = data.copy()
        
        # 转换枚举类型
        if 'trade_type' in data:
            data['trade_type'] = TradeType(data['trade_type'])
        if 'status' in data:
            data['status'] = TradeStatus(data['status'])
        
        # 移除计算字段
        data.pop('trade_value', None)
        data.pop('total_cost', None)
        
        return cls(**data)
    
    @classmethod
    def create_buy_trade(cls, symbol: str, quantity: float, price: float,
                        timestamp: Optional[dt.datetime] = None,
                        **kwargs) -> 'Trade':
        """创建买入交易"""
        return cls(
            trade_id=str(uuid.uuid4()),
            symbol=symbol,
            trade_type=TradeType.BUY,
            quantity=quantity,
            price=price,
            timestamp=timestamp or dt.datetime.now(),
            **kwargs
        )
    
    @classmethod
    def create_sell_trade(cls, symbol: str, quantity: float, price: float,
                         timestamp: Optional[dt.datetime] = None,
                         **kwargs) -> 'Trade':
        """创建卖出交易"""
        return cls(
            trade_id=str(uuid.uuid4()),
            symbol=symbol,
            trade_type=TradeType.SELL,
            quantity=quantity,
            price=price,
            timestamp=timestamp or dt.datetime.now(),
            **kwargs
        )
    
    @classmethod
    def create_close_long_trade(cls, symbol: str, quantity: float, price: float,
                               timestamp: Optional[dt.datetime] = None,
                               **kwargs) -> 'Trade':
        """创建平多交易"""
        return cls(
            trade_id=str(uuid.uuid4()),
            symbol=symbol,
            trade_type=TradeType.CLOSE_LONG,
            quantity=quantity,
            price=price,
            timestamp=timestamp or dt.datetime.now(),
            **kwargs
        )
    
    @classmethod
    def create_close_short_trade(cls, symbol: str, quantity: float, price: float,
                                timestamp: Optional[dt.datetime] = None,
                                **kwargs) -> 'Trade':
        """创建平空交易"""
        return cls(
            trade_id=str(uuid.uuid4()),
            symbol=symbol,
            trade_type=TradeType.CLOSE_SHORT,
            quantity=quantity,
            price=price,
            timestamp=timestamp or dt.datetime.now(),
            **kwargs
        )
    
    def __repr__(self) -> str:
        status_str = "✓" if self.is_filled else "○"
        side_str = "买" if self.is_long_side else "卖"
        
        return (
            f"Trade({status_str} {self.symbol} {side_str}{self.quantity} "
            f"@{self.price:.2f} {self.trade_type.value} "
            f"{self.timestamp.strftime('%H:%M:%S')})"
        )


class TradeManager:
    """
    交易管理器
    
    管理所有交易记录，提供交易查询、统计等功能。
    """
    
    def __init__(self):
        """初始化交易管理器"""
        self.trades: Dict[str, Trade] = {}
        self.trade_history: list = []
    
    def add_trade(self, trade: Trade) -> None:
        """添加交易记录"""
        self.trades[trade.trade_id] = trade
        self.trade_history.append(trade)
    
    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """获取指定交易"""
        return self.trades.get(trade_id)
    
    def get_trades_by_symbol(self, symbol: str) -> list:
        """获取指定合约的所有交易"""
        return [trade for trade in self.trade_history 
                if trade.symbol == symbol]
    
    def get_filled_trades(self) -> list:
        """获取所有已成交的交易"""
        return [trade for trade in self.trade_history 
                if trade.is_filled]
    
    def get_pending_trades(self) -> list:
        """获取所有等待中的交易"""
        return [trade for trade in self.trade_history 
                if trade.is_pending]
    
    def get_trades_by_type(self, trade_type: TradeType) -> list:
        """获取指定类型的交易"""
        return [trade for trade in self.trade_history 
                if trade.trade_type == trade_type]
    
    def get_total_commission(self) -> float:
        """获取总手续费"""
        return sum(trade.commission for trade in self.get_filled_trades())
    
    def get_total_realized_pnl(self) -> float:
        """获取总已实现盈亏"""
        return sum(trade.realized_pnl for trade in self.get_filled_trades())
    
    def get_trade_count(self) -> int:
        """获取交易总数"""
        return len(self.trade_history)
    
    def get_filled_trade_count(self) -> int:
        """获取已成交交易数"""
        return len(self.get_filled_trades())
    
    def clear_trades(self) -> None:
        """清空所有交易记录"""
        self.trades.clear()
        self.trade_history.clear()
    
    def to_dataframe(self):
        """转换为DataFrame（需要pandas）"""
        try:
            import pandas as pd
            data = [trade.to_dict() for trade in self.trade_history]
            return pd.DataFrame(data)
        except ImportError:
            print("需要安装pandas才能使用to_dataframe功能")
            return None
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """获取交易摘要"""
        filled_trades = self.get_filled_trades()
        
        return {
            'total_trades': len(self.trade_history),
            'filled_trades': len(filled_trades),
            'pending_trades': len(self.get_pending_trades()),
            'total_commission': self.get_total_commission(),
            'total_realized_pnl': self.get_total_realized_pnl(),
            'buy_trades': len(self.get_trades_by_type(TradeType.BUY)),
            'sell_trades': len(self.get_trades_by_type(TradeType.SELL)),
            'close_long_trades': len(self.get_trades_by_type(TradeType.CLOSE_LONG)),
            'close_short_trades': len(self.get_trades_by_type(TradeType.CLOSE_SHORT)),
        }
    
    def __repr__(self) -> str:
        summary = self.get_trade_summary()
        return (
            f"TradeManager(total={summary['total_trades']}, "
            f"filled={summary['filled_trades']}, "
            f"pnl={summary['total_realized_pnl']:.2f})"
        )