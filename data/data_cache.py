"""
数据缓存机制
"""

import pickle
import hashlib
from pathlib import Path
from typing import Union, Optional, Any, Dict
import pandas as pd

try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pl = None

from config import get_config


class DataCache:
    """
    数据缓存类，提供内存和磁盘缓存功能
    """
    
    def __init__(self, cache_dir: Optional[Path] = None, 
                 max_memory_items: int = 100):
        """
        初始化数据缓存
        
        Args:
            cache_dir: 缓存目录，如果为None则使用配置中的默认目录
            max_memory_items: 内存缓存最大项目数
        """
        self.cache_dir = cache_dir or get_config("data")["cache_dir"]
        self.max_memory_items = max_memory_items
        self._memory_cache: Dict[str, Any] = {}
        self._access_order: list = []
        
        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_key(self, identifier: str, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            identifier: 基础标识符
            **kwargs: 额外参数
        
        Returns:
            缓存键
        """
        key_str = f"{identifier}"
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_str += "_" + "_".join(f"{k}_{v}" for k, v in sorted_kwargs)
        
        # 使用MD5生成短键名
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _manage_memory_cache(self):
        """管理内存缓存大小"""
        while len(self._memory_cache) > self.max_memory_items:
            # 移除最久未访问的项目
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._memory_cache:
                del self._memory_cache[oldest_key]
    
    def _update_access_order(self, key: str):
        """更新访问顺序"""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def set(self, key: str, data: Any, 
            persist_to_disk: bool = True) -> None:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 要缓存的数据
            persist_to_disk: 是否持久化到磁盘
        """
        # 存储到内存缓存
        self._memory_cache[key] = data
        self._update_access_order(key)
        self._manage_memory_cache()
        
        # 持久化到磁盘
        if persist_to_disk:
            self._save_to_disk(key, data)
    
    def get(self, key: str, 
            load_from_disk: bool = True) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            load_from_disk: 如果内存中没有，是否从磁盘加载
        
        Returns:
            缓存的数据，如果不存在则返回None
        """
        # 先检查内存缓存
        if key in self._memory_cache:
            self._update_access_order(key)
            return self._memory_cache[key]
        
        # 从磁盘加载
        if load_from_disk:
            data = self._load_from_disk(key)
            if data is not None:
                # 加载到内存缓存
                self._memory_cache[key] = data
                self._update_access_order(key)
                self._manage_memory_cache()
                return data
        
        return None
    
    def has(self, key: str, check_disk: bool = True) -> bool:
        """
        检查是否存在缓存
        
        Args:
            key: 缓存键
            check_disk: 是否检查磁盘缓存
        
        Returns:
            是否存在
        """
        if key in self._memory_cache:
            return True
        
        if check_disk:
            return self._disk_cache_exists(key)
        
        return False
    
    def remove(self, key: str, remove_from_disk: bool = True) -> bool:
        """
        移除缓存数据
        
        Args:
            key: 缓存键
            remove_from_disk: 是否同时从磁盘移除
        
        Returns:
            是否成功移除
        """
        removed = False
        
        # 从内存移除
        if key in self._memory_cache:
            del self._memory_cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            removed = True
        
        # 从磁盘移除
        if remove_from_disk:
            disk_removed = self._remove_from_disk(key)
            removed = removed or disk_removed
        
        return removed
    
    def clear(self, clear_disk: bool = False) -> None:
        """
        清空缓存
        
        Args:
            clear_disk: 是否同时清空磁盘缓存
        """
        # 清空内存缓存
        self._memory_cache.clear()
        self._access_order.clear()
        
        # 清空磁盘缓存
        if clear_disk:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
    
    def cache_data(self, symbol: str, freq: str, 
                   data: Union[pd.DataFrame, Any],
                   **kwargs) -> str:
        """
        缓存数据的便捷方法
        
        Args:
            symbol: 合约代码
            freq: 频率
            data: 数据
            **kwargs: 额外参数
        
        Returns:
            缓存键
        """
        key = self._generate_key(f"data_{symbol}_{freq}", **kwargs)
        self.set(key, data)
        return key
    
    def get_cached_data(self, symbol: str, freq: str, 
                        **kwargs) -> Optional[Any]:
        """
        获取缓存数据的便捷方法
        
        Args:
            symbol: 合约代码
            freq: 频率
            **kwargs: 额外参数
        
        Returns:
            缓存的数据
        """
        key = self._generate_key(f"data_{symbol}_{freq}", **kwargs)
        return self.get(key)
    
    def _save_to_disk(self, key: str, data: Any) -> bool:
        """保存数据到磁盘"""
        try:
            cache_file = self.cache_dir / f"{key}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            return True
        except Exception as e:
            print(f"保存缓存到磁盘失败: {e}")
            return False
    
    def _load_from_disk(self, key: str) -> Optional[Any]:
        """从磁盘加载数据"""
        try:
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            print(f"从磁盘加载缓存失败: {e}")
        return None
    
    def _disk_cache_exists(self, key: str) -> bool:
        """检查磁盘缓存是否存在"""
        cache_file = self.cache_dir / f"{key}.pkl"
        return cache_file.exists()
    
    def _remove_from_disk(self, key: str) -> bool:
        """从磁盘移除缓存"""
        try:
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                cache_file.unlink()
                return True
        except Exception as e:
            print(f"从磁盘移除缓存失败: {e}")
        return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        disk_files = list(self.cache_dir.glob("*.pkl"))
        disk_size = sum(f.stat().st_size for f in disk_files)
        
        return {
            "memory_items": len(self._memory_cache),
            "max_memory_items": self.max_memory_items,
            "disk_files": len(disk_files),
            "disk_size_mb": disk_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir),
        }
    
    def __repr__(self) -> str:
        info = self.get_cache_info()
        return (
            f"DataCache(memory={info['memory_items']}/{info['max_memory_items']}, "
            f"disk={info['disk_files']} files, "
            f"size={info['disk_size_mb']:.1f}MB)"
        )


# 全局缓存实例
_global_cache = None


def get_global_cache() -> DataCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = DataCache()
    return _global_cache


def set_global_cache(cache: DataCache) -> None:
    """设置全局缓存实例"""
    global _global_cache
    _global_cache = cache