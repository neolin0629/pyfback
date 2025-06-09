"""
期货回测系统全局配置文件
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 数据配置
DATA_CONFIG = {
    "default_freq": "1min",
    "supported_freqs": ["1min", "5min", "15min", "30min", "1h", "1d"],
    "cache_enabled": True,
    "cache_dir": PROJECT_ROOT / "cache",
    "data_dir": PROJECT_ROOT / "data",
}

# 回测配置
BACKTEST_CONFIG = {
    "initial_capital": 1000000.0,  # 初始资金
    "commission": 0.0001,  # 手续费率
    "slippage": 0.0001,    # 滑点
    "trading_days_per_year": 252,  # 年交易日数
    "risk_free_rate": 0.03,  # 无风险利率
}

# 策略配置
STRATEGY_CONFIG = {
    "max_position": 1.0,  # 最大仓位比例
    "min_position": -1.0,  # 最小仓位比例（允许做空）
    "position_step": 0.1,  # 仓位调整步长
}

# 统计分析配置
STATS_CONFIG = {
    "benchmark_symbol": "IH",  # 基准指数
    "confidence_level": 0.95,  # 置信度
    "rolling_window": 252,     # 滚动窗口期
}

# 报告配置
REPORT_CONFIG = {
    "template_dir": PROJECT_ROOT / "report" / "templates",
    "output_dir": PROJECT_ROOT / "output",
    "chart_format": "png",
    "chart_dpi": 300,
    "chart_figsize": (12, 8),
}

# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "log_dir": PROJECT_ROOT / "logs",
}

# 性能优化配置
PERFORMANCE_CONFIG = {
    "use_numba": True,      # 启用numba加速
    "use_polars": True,     # 使用polars代替pandas
    "parallel_processing": True,  # 启用并行处理
    "max_workers": os.cpu_count(),  # 最大工作线程数
}

# 数据库配置（可选）
DATABASE_CONFIG = {
    "enabled": False,
    "type": "sqlite",
    "path": PROJECT_ROOT / "data" / "backtest.db",
    "connection_string": "",
}


def get_config(section: Optional[str] = None) -> Dict[str, Any]:
    """
    获取配置信息
    
    Args:
        section: 配置段名称，如果为None则返回所有配置
    
    Returns:
        配置字典
    """
    all_config = {
        "data": DATA_CONFIG,
        "backtest": BACKTEST_CONFIG,
        "strategy": STRATEGY_CONFIG,
        "stats": STATS_CONFIG,
        "report": REPORT_CONFIG,
        "logging": LOGGING_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "database": DATABASE_CONFIG,
    }
    
    if section is None:
        return all_config
    
    return all_config.get(section, {})


def update_config(section: str, key: str, value: Any) -> None:
    """
    更新配置项
    
    Args:
        section: 配置段名称
        key: 配置项名称
        value: 新值
    """
    config_map = {
        "data": DATA_CONFIG,
        "backtest": BACKTEST_CONFIG,
        "strategy": STRATEGY_CONFIG,
        "stats": STATS_CONFIG,
        "report": REPORT_CONFIG,
        "logging": LOGGING_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "database": DATABASE_CONFIG,
    }
    
    if section in config_map:
        config_map[section][key] = value
    else:
        raise ValueError(f"Unknown config section: {section}")


# 确保必要的目录存在
def ensure_directories():
    """确保必要的目录存在"""
    dirs_to_create = [
        DATA_CONFIG["cache_dir"],
        REPORT_CONFIG["output_dir"], 
        LOGGING_CONFIG["log_dir"],
    ]
    
    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)


# 初始化时创建目录
ensure_directories()