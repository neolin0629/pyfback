"""
持仓管理类
"""

import datetime as dt
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List


class PositionSide(Enum):
    """持仓方向枚举"""
    LONG = "long"      # 多头
    SHORT = "short"    # 空头
    FLAT = "flat"      # 空仓


@dataclass
class Position:
    """
    持仓信息数据结构
    
    记录单个合约的持仓状态，包括方向、数量、成本等信息。
    """
    symbol: str                    # 合约代码
    side: PositionSide            # 持仓方向
    quantity: float               # 持仓数量（绝对值）
    avg_price: float              # 平均成本价
    current_price: float          # 当前价格
    timestamp: dt.datetime        # 最后更新时间
    unrealized_pnl: float = 0.0   # 未实现盈亏
    realized_pnl: float = 0.0     # 已实现盈亏
    
    def __post_init__(self):
        """数据验证"""
        if self.quantity < 0:
            raise ValueError("持仓数量不能为负数")
        
        if self.avg_price <= 0:
            raise ValueError("平均价格必须大于0")
        
        if self.current_price <= 0:
            raise ValueError("当前价格必须大于0")
    
    @property
    def is_long(self) -> bool:
        """是否为多头持仓"""
        return self.side == PositionSide.LONG and self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        """是否为空头持仓"""
        return self.side == PositionSide.SHORT and self.quantity > 0
    
    @property
    def is_flat(self) -> bool:
        """是否为空仓"""
        return self.side == PositionSide.FLAT or self.quantity == 0
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.quantity * self.current_price
    
    @property
    def cost_value(self) -> float:
        """成本价值"""
        return self.quantity * self.avg_price
    
    def calculate_unrealized_pnl(self, current_price: Optional[float] = None) -> float:
        """
        计算未实现盈亏
        
        Args:
            current_price: 当前价格，如果为None则使用实例中的current_price
        
        Returns:
            未实现盈亏
        """
        price = current_price or self.current_price
        
        if self.is_flat:
            return 0.0
        
        price_diff = price - self.avg_price
        
        if self.is_long:
            pnl = self.quantity * price_diff
        else:  # short position
            pnl = self.quantity * (-price_diff)
        
        return pnl
    
    def update_price(self, new_price: float) -> None:
        """更新当前价格并重新计算未实现盈亏"""
        self.current_price = new_price
        self.unrealized_pnl = self.calculate_unrealized_pnl()
        self.timestamp = dt.datetime.now()
    
    def add_position(self, quantity: float, price: float) -> None:
        """
        增加持仓
        
        Args:
            quantity: 增加的数量（正数）
            price: 成交价格
        """
        if quantity <= 0:
            raise ValueError("增加的数量必须大于0")
        
        if self.is_flat:
            # 从空仓开始建仓
            self.quantity = quantity
            self.avg_price = price
        else:
            # 加仓，重新计算平均成本
            total_cost = self.cost_value + quantity * price
            self.quantity += quantity
            self.avg_price = total_cost / self.quantity
        
        self.timestamp = dt.datetime.now()
    
    def reduce_position(self, quantity: float, price: float) -> float:
        """
        减少持仓
        
        Args:
            quantity: 减少的数量（正数）
            price: 成交价格
        
        Returns:
            本次平仓的已实现盈亏
        """
        if quantity <= 0:
            raise ValueError("减少的数量必须大于0")
        
        if quantity > self.quantity:
            raise ValueError("减少数量不能超过当前持仓")
        
        # 计算本次平仓的已实现盈亏
        price_diff = price - self.avg_price
        if self.is_long:
            realized_pnl = quantity * price_diff
        else:  # short position
            realized_pnl = quantity * (-price_diff)
        
        self.realized_pnl += realized_pnl
        self.quantity -= quantity
        
        # 如果全部平仓，设置为空仓
        if self.quantity == 0:
            self.side = PositionSide.FLAT
        
        self.timestamp = dt.datetime.now()
        return realized_pnl
    
    def close_position(self, price: float) -> float:
        """
        全部平仓
        
        Args:
            price: 平仓价格
        
        Returns:
            平仓的已实现盈亏
        """
        if self.is_flat:
            return 0.0
        
        return self.reduce_position(self.quantity, price)
    
    def reverse_position(self, new_quantity: float, price: float) -> float:
        """
        反向开仓
        
        Args:
            new_quantity: 新的持仓数量
            price: 成交价格
        
        Returns:
            原持仓平仓的已实现盈亏
        """
        # 先平掉原有持仓
        realized_pnl = self.close_position(price)
        
        # 开新的反向持仓
        if new_quantity > 0:
            self.quantity = new_quantity
            self.avg_price = price
            self.side = PositionSide.SHORT if self.side == PositionSide.LONG else PositionSide.LONG
            self.timestamp = dt.datetime.now()
        
        return realized_pnl
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'avg_price': self.avg_price,
            'current_price': self.current_price,
            'timestamp': self.timestamp,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'market_value': self.market_value,
            'cost_value': self.cost_value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """从字典创建Position对象"""
        data = data.copy()
        if 'side' in data:
            data['side'] = PositionSide(data['side'])
        # 移除计算字段
        data.pop('market_value', None)
        data.pop('cost_value', None)
        return cls(**data)
    
    @classmethod
    def create_long_position(cls, symbol: str, quantity: float, 
                           price: float) -> 'Position':
        """创建多头持仓"""
        return cls(
            symbol=symbol,
            side=PositionSide.LONG,
            quantity=quantity,
            avg_price=price,
            current_price=price,
            timestamp=dt.datetime.now()
        )
    
    @classmethod
    def create_short_position(cls, symbol: str, quantity: float, 
                            price: float) -> 'Position':
        """创建空头持仓"""
        return cls(
            symbol=symbol,
            side=PositionSide.SHORT,
            quantity=quantity,
            avg_price=price,
            current_price=price,
            timestamp=dt.datetime.now()
        )
    
    @classmethod
    def create_flat_position(cls, symbol: str) -> 'Position':
        """创建空仓"""
        return cls(
            symbol=symbol,
            side=PositionSide.FLAT,
            quantity=0,
            avg_price=0,
            current_price=0,
            timestamp=dt.datetime.now()
        )
    
    def __repr__(self) -> str:
        side_str = {"long": "多", "short": "空", "flat": "空"}[self.side.value]
        return (
            f"Position({self.symbol} {side_str}{self.quantity} "
            f"@{self.avg_price:.2f} "
            f"PnL={self.unrealized_pnl:.2f})"
        )


class PositionManager:
    """
    持仓管理器
    
    管理多个合约的持仓状态，提供持仓查询、更新等功能。
    """
    
    def __init__(self):
        """初始化持仓管理器"""
        self.positions: Dict[str, Position] = {}
    
    def get_position(self, symbol: str) -> Position:
        """
        获取持仓信息
        
        Args:
            symbol: 合约代码
        
        Returns:
            持仓对象
        """
        if symbol not in self.positions:
            self.positions[symbol] = Position.create_flat_position(symbol)
        return self.positions[symbol]
    
    def update_position(self, symbol: str, quantity: float, 
                       side: PositionSide, price: float) -> None:
        """
        更新持仓
        
        Args:
            symbol: 合约代码
            quantity: 数量
            side: 持仓方向
            price: 价格
        """
        if symbol not in self.positions:
            self.positions[symbol] = Position.create_flat_position(symbol)
        
        position = self.positions[symbol]
        
        if side == PositionSide.FLAT:
            position.close_position(price)
        elif side == PositionSide.LONG:
            if position.is_short:
                position.reverse_position(quantity, price)
            else:
                position.side = PositionSide.LONG
                if position.is_flat:
                    position.quantity = quantity
                    position.avg_price = price
                else:
                    position.add_position(quantity - position.quantity, price)
        elif side == PositionSide.SHORT:
            if position.is_long:
                position.reverse_position(quantity, price)
            else:
                position.side = PositionSide.SHORT
                if position.is_flat:
                    position.quantity = quantity
                    position.avg_price = price
                else:
                    position.add_position(quantity - position.quantity, price)
        
        position.update_price(price)
    
    def update_prices(self, prices: Dict[str, float]) -> None:
        """批量更新价格"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions.copy()
    
    def get_active_positions(self) -> Dict[str, Position]:
        """获取所有非空仓位"""
        return {symbol: pos for symbol, pos in self.positions.items() 
                if not pos.is_flat}
    
    def get_total_unrealized_pnl(self) -> float:
        """获取总未实现盈亏"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
    
    def get_total_realized_pnl(self) -> float:
        """获取总已实现盈亏"""
        return sum(pos.realized_pnl for pos in self.positions.values())
    
    def get_total_market_value(self) -> float:
        """获取总市值"""
        return sum(pos.market_value for pos in self.positions.values() 
                  if not pos.is_flat)
    
    def clear_positions(self) -> None:
        """清空所有持仓"""
        self.positions.clear()
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """转换为字典格式"""
        return {symbol: pos.to_dict() 
                for symbol, pos in self.positions.items()}
    
    def __repr__(self) -> str:
        active_count = len(self.get_active_positions())
        total_pnl = self.get_total_unrealized_pnl()
        return (
            f"PositionManager(active={active_count}, "
            f"unrealized_pnl={total_pnl:.2f})"
        )