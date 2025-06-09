"""
数据处理主类
"""

import datetime as dt
from pathlib import Path
from typing import Union, List, Optional, Dict, Any
import pandas as pd

try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pl = None

from .bar import Bar
from .data_cache import DataCache, get_global_cache
from .utils import (
    load_csv_data, 
    standardize_datetime,
    validate_data_format,
    resample_data,
    dataframe_to_bars
)
from config import get_config


class DataHandler:
    """
    数据处理主类
    
    负责历史数据的加载、处理、缓存和查询，支持多频率数据和高性能处理。
    """
    
    def __init__(self, cache_enabled: bool = True, 
                 use_polars: bool = True,
                 cache: Optional[DataCache] = None):
        """
        初始化数据处理器
        
        Args:
            cache_enabled: 是否启用缓存
            use_polars: 是否使用Polars（高性能数据处理）
            cache: 自定义缓存实例，如果为None则使用全局缓存
        """
        self.cache_enabled = cache_enabled
        self.use_polars = use_polars and POLARS_AVAILABLE
        self.cache = cache or get_global_cache()
        
        # 配置信息
        self.config = get_config("data")
        self.supported_freqs = self.config["supported_freqs"]
        
        # 数据存储
        self._data_store: Dict[str, Any] = {}
        
        if not self.use_polars:
            print("警告: Polars不可用，将使用Pandas，性能可能受影响")
    
    def load_data(self, csv_path: Union[str, Path], 
                  symbol: str, 
                  freq: str = "1min",
                  force_reload: bool = False) -> Union[pd.DataFrame, Any]:
        """
        从CSV文件加载历史数据
        
        Args:
            csv_path: CSV文件路径
            symbol: 合约代码  
            freq: 数据频率
            force_reload: 是否强制重新加载
        
        Returns:
            数据框架对象
        """
        if freq not in self.supported_freqs:
            raise ValueError(f"不支持的频率: {freq}, 支持的频率: {self.supported_freqs}")
        
        # 检查缓存
        if self.cache_enabled and not force_reload:
            cached_data = self.cache.get_cached_data(
                symbol, freq, 
                csv_path=str(csv_path)
            )
            if cached_data is not None:
                print(f"从缓存加载数据: {symbol} {freq}")
                return cached_data
        
        # 加载数据
        print(f"从CSV文件加载数据: {csv_path}")
        df = load_csv_data(csv_path, use_polars=self.use_polars)
        
        # 标准化数据
        df = standardize_datetime(df)
        validate_data_format(df)
        
        # 如果需要重采样到目标频率
        if freq != "1min":
            df = resample_data(df, freq)
        
        # 缓存数据
        if self.cache_enabled:
            self.cache.cache_data(
                symbol, freq, df,
                csv_path=str(csv_path)
            )
        
        # 存储到内存
        store_key = f"{symbol}_{freq}"
        self._data_store[store_key] = df
        
        return df
    
    def get_bar(self, symbol: str, 
                datetime: dt.datetime, 
                freq: str = "1min") -> Optional[Bar]:
        """
        获取指定时间点的K线数据
        
        Args:
            symbol: 合约代码
            datetime: 时间点
            freq: 频率
        
        Returns:
            Bar对象，如果不存在则返回None
        """
        store_key = f"{symbol}_{freq}"
        
        if store_key not in self._data_store:
            print(f"数据未加载: {symbol} {freq}")
            return None
        
        df = self._data_store[store_key]
        
        if self.use_polars and hasattr(df, 'filter'):
            # Polars查询
            try:
                row = df.filter(pl.col('datetime') == datetime)
                if len(row) == 0:
                    return None
                
                row_dict = row.to_dicts()[0]
                return Bar(
                    symbol=symbol,
                    datetime=row_dict['datetime'],
                    open=float(row_dict['open']),
                    high=float(row_dict['high']),
                    low=float(row_dict['low']),
                    close=float(row_dict['close']),
                    volume=int(row_dict['volume']),
                    open_interest=int(row_dict.get('open_interest', 0)),
                    freq=freq
                )
            except Exception:
                # 如果Polars查询失败，回退到索引查询
                pass
        
        # Pandas查询或Polars回退
        try:
            if hasattr(df, 'loc'):
                # Pandas DataFrame
                row = df[df['datetime'] == datetime]
            else:
                # 其他情况的回退处理
                return None
                
            if len(row) == 0:
                return None
            
            row = row.iloc[0]
            return Bar(
                symbol=symbol,
                datetime=row['datetime'],
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume']),
                open_interest=int(row.get('open_interest', 0)),
                freq=freq
            )
        except Exception as e:
            print(f"获取K线数据失败: {e}")
            return None
    
    def get_history(self, symbol: str, 
                    start: dt.datetime, 
                    end: dt.datetime,
                    freq: str = "1min") -> Union[pd.DataFrame, Any]:
        """
        获取历史数据序列
        
        Args:
            symbol: 合约代码
            start: 开始时间
            end: 结束时间  
            freq: 频率
        
        Returns:
            数据框架对象
        """
        store_key = f"{symbol}_{freq}"
        
        if store_key not in self._data_store:
            print(f"数据未加载: {symbol} {freq}")
            return pd.DataFrame() if not self.use_polars else pl.DataFrame()
        
        df = self._data_store[store_key]
        
        if self.use_polars and hasattr(df, 'filter'):
            # Polars查询
            try:
                result = df.filter(
                    (pl.col('datetime') >= start) & 
                    (pl.col('datetime') <= end)
                )
                return result
            except Exception:
                pass
        
        # Pandas查询或回退
        if hasattr(df, 'loc'):
            mask = (df['datetime'] >= start) & (df['datetime'] <= end)
            return df[mask].copy()
        
        return df  # 返回全部数据作为回退
    
    def get_bars(self, symbol: str, 
                 start: dt.datetime, 
                 end: dt.datetime,
                 freq: str = "1min") -> List[Bar]:
        """
        获取Bar对象列表
        
        Args:
            symbol: 合约代码
            start: 开始时间
            end: 结束时间
            freq: 频率
        
        Returns:
            Bar对象列表
        """
        df = self.get_history(symbol, start, end, freq)
        if df is None or len(df) == 0:
            return []
        
        return dataframe_to_bars(df, symbol, freq)
    
    def get_latest_bar(self, symbol: str, 
                       freq: str = "1min") -> Optional[Bar]:
        """
        获取最新的K线数据
        
        Args:
            symbol: 合约代码
            freq: 频率
        
        Returns:
            最新的Bar对象
        """
        store_key = f"{symbol}_{freq}"
        
        if store_key not in self._data_store:
            return None
        
        df = self._data_store[store_key]
        
        if len(df) == 0:
            return None
        
        if self.use_polars and hasattr(df, 'tail'):
            # Polars处理
            try:
                last_row = df.tail(1).to_dicts()[0]
                return Bar(
                    symbol=symbol,
                    datetime=last_row['datetime'],
                    open=float(last_row['open']),
                    high=float(last_row['high']),
                    low=float(last_row['low']),
                    close=float(last_row['close']),
                    volume=int(last_row['volume']),
                    open_interest=int(last_row.get('open_interest', 0)),
                    freq=freq
                )
            except Exception:
                pass
        
        # Pandas处理或回退
        if hasattr(df, 'iloc'):
            last_row = df.iloc[-1]
            return Bar(
                symbol=symbol,
                datetime=last_row['datetime'],
                open=float(last_row['open']),
                high=float(last_row['high']),
                low=float(last_row['low']),
                close=float(last_row['close']),
                volume=int(last_row['volume']),
                open_interest=int(last_row.get('open_interest', 0)),
                freq=freq
            )
        
        return None
    
    def get_data_info(self, symbol: str, 
                      freq: str = "1min") -> Optional[Dict[str, Any]]:
        """
        获取数据信息
        
        Args:
            symbol: 合约代码
            freq: 频率
        
        Returns:
            数据信息字典
        """
        store_key = f"{symbol}_{freq}"
        
        if store_key not in self._data_store:
            return None
        
        df = self._data_store[store_key]
        
        if len(df) == 0:
            return None
        
        try:
            if self.use_polars and hasattr(df, 'select'):
                # Polars处理
                start_time = df.select(pl.col('datetime').min()).item()
                end_time = df.select(pl.col('datetime').max()).item()
                row_count = len(df)
            else:
                # Pandas处理
                start_time = df['datetime'].min()
                end_time = df['datetime'].max()
                row_count = len(df)
            
            return {
                'symbol': symbol,
                'freq': freq,
                'start_time': start_time,
                'end_time': end_time,
                'total_bars': row_count,
                'data_type': 'polars' if self.use_polars else 'pandas'
            }
        except Exception as e:
            print(f"获取数据信息失败: {e}")
            return None
    
    def clear_data(self, symbol: Optional[str] = None, 
                   freq: Optional[str] = None) -> None:
        """
        清除数据
        
        Args:
            symbol: 合约代码，如果为None则清除所有
            freq: 频率，如果为None则清除所有频率
        """
        if symbol is None and freq is None:
            # 清除所有数据
            self._data_store.clear()
        elif symbol is not None and freq is not None:
            # 清除特定数据
            store_key = f"{symbol}_{freq}"
            if store_key in self._data_store:
                del self._data_store[store_key]
        elif symbol is not None:
            # 清除特定合约的所有频率数据
            keys_to_remove = [k for k in self._data_store.keys() 
                             if k.startswith(f"{symbol}_")]
            for key in keys_to_remove:
                del self._data_store[key]
    
    def get_loaded_data_list(self) -> List[Dict[str, str]]:
        """获取已加载的数据列表"""
        data_list = []
        for store_key in self._data_store.keys():
            parts = store_key.split('_', 1)
            if len(parts) == 2:
                symbol, freq = parts
                data_list.append({
                    'symbol': symbol,
                    'freq': freq,
                    'store_key': store_key
                })
        return data_list
    
    def __repr__(self) -> str:
        loaded_count = len(self._data_store)
        cache_info = self.cache.get_cache_info() if self.cache_enabled else {}
        
        return (
            f"DataHandler(loaded={loaded_count}, "
            f"polars={self.use_polars}, "
            f"cache={self.cache_enabled}, "
            f"memory_cache={cache_info.get('memory_items', 0)})"
        )