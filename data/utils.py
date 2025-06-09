"""
数据处理工具函数
"""

import datetime as dt
import pandas as pd
import polars as pl
from typing import Union, List, Dict, Any, Optional
from pathlib import Path

from .bar import Bar


def load_csv_data(csv_path: Union[str, Path], 
                  use_polars: bool = True) -> Union[pd.DataFrame, pl.DataFrame]:
    """
    从CSV文件加载期货历史数据
    
    Args:
        csv_path: CSV文件路径
        use_polars: 是否使用Polars（默认True，性能更好）
    
    Returns:
        数据框架对象
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"数据文件不存在: {csv_path}")
    
    if use_polars:
        try:
            df = pl.read_csv(
                csv_path,
                try_parse_dates=True,
                infer_schema_length=10000
            )
            return df
        except Exception as e:
            print(f"Polars读取失败，尝试使用Pandas: {e}")
            use_polars = False
    
    if not use_polars:
        df = pd.read_csv(csv_path, parse_dates=['datetime'])
        return df


def standardize_datetime(df: Union[pd.DataFrame, pl.DataFrame], 
                        datetime_col: str = 'datetime') -> Union[pd.DataFrame, pl.DataFrame]:
    """
    标准化时间列格式
    
    Args:
        df: 数据框架
        datetime_col: 时间列名
    
    Returns:
        标准化后的数据框架
    """
    if isinstance(df, pl.DataFrame):
        # Polars处理
        if datetime_col not in df.columns:
            raise ValueError(f"时间列 '{datetime_col}' 不存在")
        
        df = df.with_columns([
            pl.col(datetime_col).str.to_datetime().alias(datetime_col)
        ])
    else:
        # Pandas处理
        if datetime_col not in df.columns:
            raise ValueError(f"时间列 '{datetime_col}' 不存在")
        
        df[datetime_col] = pd.to_datetime(df[datetime_col])
    
    return df


def validate_data_format(df: Union[pd.DataFrame, pl.DataFrame]) -> bool:
    """
    验证数据格式是否符合要求
    
    Args:
        df: 数据框架
    
    Returns:
        是否符合格式要求
    """
    required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    
    if isinstance(df, pl.DataFrame):
        columns = df.columns
    else:
        columns = df.columns.tolist()
    
    # 检查必需列
    missing_cols = set(required_columns) - set(columns)
    if missing_cols:
        raise ValueError(f"缺少必需的列: {missing_cols}")
    
    # 检查数据类型和数值有效性
    if isinstance(df, pl.DataFrame):
        # Polars验证
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if df[col].dtype not in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]:
                print(f"警告: 列 '{col}' 的数据类型可能不正确")
    else:
        # Pandas验证
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                print(f"警告: 列 '{col}' 的数据类型可能不正确")
    
    return True


def resample_data(df: Union[pd.DataFrame, pl.DataFrame], 
                  freq: str, 
                  datetime_col: str = 'datetime') -> Union[pd.DataFrame, pl.DataFrame]:
    """
    重采样数据到指定频率
    
    Args:
        df: 数据框架
        freq: 目标频率 ('5min', '15min', '30min', '1h', '1d')
        datetime_col: 时间列名
    
    Returns:
        重采样后的数据框架
    """
    if isinstance(df, pl.DataFrame):
        # Polars重采样
        freq_map = {
            '5min': '5m',
            '15min': '15m', 
            '30min': '30m',
            '1h': '1h',
            '1d': '1d'
        }
        
        pl_freq = freq_map.get(freq, freq)
        
        result = df.group_by_dynamic(
            datetime_col, 
            every=pl_freq
        ).agg([
            pl.col('open').first(),
            pl.col('high').max(),
            pl.col('low').min(),
            pl.col('close').last(),
            pl.col('volume').sum(),
            pl.col('open_interest').last() if 'open_interest' in df.columns else None
        ]).filter(pl.col('open').is_not_null())
        
        return result
    else:
        # Pandas重采样
        df_copy = df.copy()
        df_copy.set_index(datetime_col, inplace=True)
        
        freq_map = {
            '5min': '5T',
            '15min': '15T',
            '30min': '30T', 
            '1h': '1H',
            '1d': '1D'
        }
        
        pd_freq = freq_map.get(freq, freq)
        
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        if 'open_interest' in df_copy.columns:
            agg_dict['open_interest'] = 'last'
        
        result = df_copy.resample(pd_freq).agg(agg_dict).dropna()
        result.reset_index(inplace=True)
        
        return result


def dataframe_to_bars(df: Union[pd.DataFrame, pl.DataFrame], 
                      symbol: str, 
                      freq: str = "1min") -> List[Bar]:
    """
    将数据框架转换为Bar对象列表
    
    Args:
        df: 数据框架
        symbol: 合约代码
        freq: 频率标识
    
    Returns:
        Bar对象列表
    """
    bars = []
    
    if isinstance(df, pl.DataFrame):
        # Polars处理
        for row in df.iter_rows(named=True):
            bar = Bar(
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
            bars.append(bar)
    else:
        # Pandas处理
        for _, row in df.iterrows():
            bar = Bar(
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
            bars.append(bar)
    
    return bars


def bars_to_dataframe(bars: List[Bar], 
                      use_polars: bool = True) -> Union[pd.DataFrame, pl.DataFrame]:
    """
    将Bar对象列表转换为数据框架
    
    Args:
        bars: Bar对象列表
        use_polars: 是否使用Polars
    
    Returns:
        数据框架对象
    """
    if not bars:
        if use_polars:
            return pl.DataFrame()
        else:
            return pd.DataFrame()
    
    data = [bar.to_dict() for bar in bars]
    
    if use_polars:
        return pl.DataFrame(data)
    else:
        return pd.DataFrame(data)


def filter_trading_hours(df: Union[pd.DataFrame, pl.DataFrame],
                        start_time: str = "09:00:00",
                        end_time: str = "15:00:00",
                        datetime_col: str = 'datetime') -> Union[pd.DataFrame, pl.DataFrame]:
    """
    过滤交易时间段的数据
    
    Args:
        df: 数据框架
        start_time: 开始时间 (HH:MM:SS格式)
        end_time: 结束时间 (HH:MM:SS格式) 
        datetime_col: 时间列名
    
    Returns:
        过滤后的数据框架
    """
    if isinstance(df, pl.DataFrame):
        # Polars处理
        result = df.filter(
            (pl.col(datetime_col).dt.time() >= dt.time.fromisoformat(start_time)) &
            (pl.col(datetime_col).dt.time() <= dt.time.fromisoformat(end_time))
        )
    else:
        # Pandas处理
        mask = (
            (df[datetime_col].dt.time >= dt.time.fromisoformat(start_time)) &
            (df[datetime_col].dt.time <= dt.time.fromisoformat(end_time))
        )
        result = df[mask].copy()
    
    return result


def calculate_returns(df: Union[pd.DataFrame, pl.DataFrame],
                     price_col: str = 'close') -> Union[pd.DataFrame, pl.DataFrame]:
    """
    计算收益率
    
    Args:
        df: 数据框架
        price_col: 价格列名
    
    Returns:
        添加收益率列的数据框架
    """
    if isinstance(df, pl.DataFrame):
        # Polars处理
        result = df.with_columns([
            (pl.col(price_col) / pl.col(price_col).shift(1) - 1).alias('return'),
            (pl.col(price_col).pct_change()).alias('pct_change')
        ])
    else:
        # Pandas处理
        result = df.copy()
        result['return'] = result[price_col].pct_change()
        result['pct_change'] = result[price_col].pct_change()
    
    return result