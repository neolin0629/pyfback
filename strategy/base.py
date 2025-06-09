"""
策略基类定义
"""

import datetime as dt
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import pandas as pd

from data.bar import Bar
from .signals import Signal, SignalType
from .position import Position, PositionManager
from config import get_config


class StrategyBase(ABC):
    """
    策略基类
    
    所有交易策略都应继承此类并实现相应的抽象方法。
    提供策略生命周期管理、参数配置、信号生成等基础功能。
    """
    
    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        """
        初始化策略
        
        Args:
            name: 策略名称
            params: 策略参数字典
        """
        self.name = name
        self.params = params or {}
        
        # 策略状态
        self.is_initialized = False
        self.is_running = False
        self.current_bar: Optional[Bar] = None
        self.bar_count = 0
        
        # 历史数据缓存
        self.bar_history: List[Bar] = []
        self.signal_history: List[Signal] = []
        
        # 持仓管理
        self.position_manager = PositionManager()
        
        # 策略配置
        self.config = get_config("strategy")
        
        # 策略指标和状态
        self.indicators: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}
    
    @abstractmethod
    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """
        处理新K线数据
        
        这是策略的核心方法，需要子类实现具体的交易逻辑。
        
        Args:
            bar: K线数据
        
        Returns:
            交易信号或None
        """
        pass
    
    def on_start(self) -> None:
        """
        策略启动时的初始化
        
        在回测开始前调用，可以在此进行策略的初始化工作。
        """
        self.is_initialized = True
        self.is_running = True
        print(f"策略 {self.name} 启动")
    
    def on_finish(self) -> None:
        """
        策略结束时的清理工作
        
        在回测结束后调用，可以在此进行清理和统计工作。
        """
        self.is_running = False
        print(f"策略 {self.name} 结束")
        self._print_summary()
    
    def on_trade(self, trade_info: Dict[str, Any]) -> None:
        """
        交易执行后的回调
        
        Args:
            trade_info: 交易信息字典
        """
        pass
    
    def set_params(self, params: Dict[str, Any]) -> None:
        """
        设置策略参数
        
        Args:
            params: 参数字典
        """
        self.params.update(params)
    
    def get_params(self) -> Dict[str, Any]:
        """获取策略参数"""
        return self.params.copy()
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """
        获取单个参数值
        
        Args:
            key: 参数名
            default: 默认值
        
        Returns:
            参数值
        """
        return self.params.get(key, default)
    
    def update_bar(self, bar: Bar) -> Optional[Signal]:
        """
        更新K线数据并生成信号
        
        Args:
            bar: K线数据
        
        Returns:
            交易信号或None
        """
        if not self.is_running:
            return None
        
        # 更新当前状态
        self.current_bar = bar
        self.bar_count += 1
        
        # 添加到历史数据
        self.bar_history.append(bar)
        self._manage_history_size()
        
        # 更新持仓价格
        if bar.symbol in self.position_manager.positions:
            self.position_manager.get_position(bar.symbol).update_price(bar.close)
        
        # 生成交易信号
        signal = self.on_bar(bar)
        
        # 记录信号
        if signal is not None:
            self.signal_history.append(signal)
            
        return signal
    
    def get_position(self, symbol: str) -> Position:
        """获取持仓信息"""
        return self.position_manager.get_position(symbol)
    
    def get_current_price(self, symbol: Optional[str] = None) -> Optional[float]:
        """
        获取当前价格
        
        Args:
            symbol: 合约代码，如果为None则使用当前K线的合约
        
        Returns:
            当前价格
        """
        if self.current_bar is None:
            return None
        
        if symbol is None or symbol == self.current_bar.symbol:
            return self.current_bar.close
        
        return None
    
    def get_history_bars(self, count: int = 10) -> List[Bar]:
        """
        获取历史K线数据
        
        Args:
            count: 获取的数量
        
        Returns:
            历史K线列表
        """
        return self.bar_history[-count:] if count > 0 else self.bar_history
    
    def get_history_prices(self, count: int = 10, 
                          price_type: str = 'close') -> List[float]:
        """
        获取历史价格序列
        
        Args:
            count: 获取的数量
            price_type: 价格类型 ('open', 'high', 'low', 'close')
        
        Returns:
            价格列表
        """
        bars = self.get_history_bars(count)
        if price_type == 'open':
            return [bar.open for bar in bars]
        elif price_type == 'high':
            return [bar.high for bar in bars]
        elif price_type == 'low':
            return [bar.low for bar in bars]
        else:  # close
            return [bar.close for bar in bars]
    
    def calculate_sma(self, period: int, 
                     price_type: str = 'close') -> Optional[float]:
        """
        计算简单移动平均
        
        Args:
            period: 周期
            price_type: 价格类型
        
        Returns:
            移动平均值
        """
        prices = self.get_history_prices(period, price_type)
        if len(prices) < period:
            return None
        return sum(prices) / len(prices)
    
    def calculate_ema(self, period: int, 
                     price_type: str = 'close') -> Optional[float]:
        """
        计算指数移动平均
        
        Args:
            period: 周期
            price_type: 价格类型
        
        Returns:
            指数移动平均值
        """
        prices = self.get_history_prices(period + 10, price_type)  # 多取一些数据
        if len(prices) < period:
            return None
        
        # 简单的EMA计算
        alpha = 2.0 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return ema
    
    def calculate_volatility(self, period: int = 20) -> Optional[float]:
        """
        计算价格波动率
        
        Args:
            period: 计算周期
        
        Returns:
            波动率
        """
        prices = self.get_history_prices(period + 1, 'close')
        if len(prices) < period + 1:
            return None
        
        # 计算收益率
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
        
        if len(returns) < period:
            return None
        
        # 计算标准差
        mean_return = sum(returns) / len(returns)
        variance = sum((ret - mean_return) ** 2 for ret in returns) / len(returns)
        
        return variance ** 0.5
    
    def set_indicator(self, name: str, value: Any) -> None:
        """设置技术指标值"""
        self.indicators[name] = value
    
    def get_indicator(self, name: str, default: Any = None) -> Any:
        """获取技术指标值"""
        return self.indicators.get(name, default)
    
    def set_state(self, key: str, value: Any) -> None:
        """设置策略状态"""
        self.state[key] = value
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """获取策略状态"""
        return self.state.get(key, default)
    
    def _manage_history_size(self, max_size: int = 1000) -> None:
        """管理历史数据大小"""
        if len(self.bar_history) > max_size:
            self.bar_history = self.bar_history[-max_size:]
    
    def _print_summary(self) -> None:
        """打印策略摘要"""
        print(f"\n=== 策略 {self.name} 运行摘要 ===")
        print(f"处理K线数量: {self.bar_count}")
        print(f"生成信号数量: {len(self.signal_history)}")
        
        # 持仓摘要
        active_positions = self.position_manager.get_active_positions()
        print(f"活跃持仓数量: {len(active_positions)}")
        
        total_unrealized = self.position_manager.get_total_unrealized_pnl()
        total_realized = self.position_manager.get_total_realized_pnl()
        print(f"未实现盈亏: {total_unrealized:.2f}")
        print(f"已实现盈亏: {total_realized:.2f}")
        print("=" * 40)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'name': self.name,
            'params': self.params,
            'is_running': self.is_running,
            'bar_count': self.bar_count,
            'signal_count': len(self.signal_history),
            'active_positions': len(self.position_manager.get_active_positions()),
            'total_unrealized_pnl': self.position_manager.get_total_unrealized_pnl(),
            'total_realized_pnl': self.position_manager.get_total_realized_pnl(),
        }
    
    def __repr__(self) -> str:
        return (
            f"Strategy({self.name}, bars={self.bar_count}, "
            f"signals={len(self.signal_history)}, "
            f"running={self.is_running})"
        )


class SimpleStrategy(StrategyBase):
    """
    简单策略示例
    
    基于移动平均线的简单策略实现，用于演示策略基类的使用。
    """
    
    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        """
        初始化简单策略
        
        Args:
            fast_period: 快速移动平均周期
            slow_period: 慢速移动平均周期
        """
        super().__init__("简单移动平均策略", {
            'fast_period': fast_period,
            'slow_period': slow_period
        })
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """移动平均策略逻辑"""
        # 计算移动平均
        fast_ma = self.calculate_sma(self.fast_period)
        slow_ma = self.calculate_sma(self.slow_period)
        
        if fast_ma is None or slow_ma is None:
            return None
        
        # 保存指标
        self.set_indicator('fast_ma', fast_ma)
        self.set_indicator('slow_ma', slow_ma)
        
        current_position = self.get_position(bar.symbol)
        
        # 金叉买入
        if fast_ma > slow_ma and current_position.is_flat:
            return Signal.buy_signal(
                symbol=bar.symbol,
                quantity=1,
                timestamp=bar.datetime
            )
        
        # 死叉卖出
        elif fast_ma < slow_ma and current_position.is_long:
            return Signal.close_signal(
                symbol=bar.symbol,
                timestamp=bar.datetime
            )
        
        return None