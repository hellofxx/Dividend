"""数据提供者抽象基类

定义数据获取的统一接口，支持多种金融数据类型
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

import pandas as pd


class DataProvider(ABC):
    """数据提供者抽象基类
    
    定义所有数据提供者必须实现的接口
    """
    
    def __init__(self, cache_dir: Optional[str] = None, verbose: bool = True):
        self._cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent.parent.parent.parent / "cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._verbose = verbose
    
    @abstractmethod
    def get_name(self) -> str:
        """获取数据源名称"""
        pass
    
    @abstractmethod
    def get_stock_data(self, code: str, start: str, end: str, **kwargs) -> Any:
        """获取股票数据
        
        Args:
            code: 股票代码
            start: 开始日期，格式 "YYYY-MM-DD"
            end: 结束日期，格式 "YYYY-MM-DD"
            **kwargs: 额外参数
            
        Returns:
            股票数据对象
        """
        pass
    
    @abstractmethod
    def get_etf_data(self, code: str, start: str, end: str, **kwargs) -> Any:
        """获取ETF数据
        
        Args:
            code: ETF代码
            start: 开始日期，格式 "YYYY-MM-DD"
            end: 结束日期，格式 "YYYY-MM-DD"
            **kwargs: 额外参数
            
        Returns:
            ETF数据对象
        """
        pass
    
    @abstractmethod
    def get_index_data(self, code: str, start: str, end: str, **kwargs) -> Any:
        """获取指数数据
        
        Args:
            code: 指数代码
            start: 开始日期，格式 "YYYY-MM-DD"
            end: 结束日期，格式 "YYYY-MM-DD"
            **kwargs: 额外参数
            
        Returns:
            指数数据对象
        """
        pass
    
    @abstractmethod
    def get_fund_data(self, code: str, start: str, end: str, **kwargs) -> Any:
        """获取公募基金数据
        
        Args:
            code: 基金代码
            start: 开始日期，格式 "YYYY-MM-DD"
            end: 结束日期，格式 "YYYY-MM-DD"
            **kwargs: 额外参数
            
        Returns:
            基金数据对象
        """
        pass
    
    def _load_from_cache(self, cache_path: Path, **kwargs) -> Optional[pd.DataFrame]:
        """从缓存加载数据
        
        子类可以重写此方法以实现特定的缓存逻辑
        """
        if not cache_path.exists():
            return None
        
        try:
            return pd.read_pickle(cache_path)
        except Exception:
            return None
    
    def _save_to_cache(self, cache_path: Path, data: pd.DataFrame, **kwargs):
        """保存数据到缓存
        
        子类可以重写此方法以实现特定的缓存逻辑
        """
        if data is None or data.empty:
            return
        
        try:
            data.to_pickle(cache_path)
        except Exception:
            pass


class DataProviderFactory:
    """数据提供者工厂类
    
    用于创建不同类型的数据提供者实例
    """
    
    _providers: Dict[str, DataProvider] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider: DataProvider):
        """注册数据提供者
        
        Args:
            name: 提供者名称
            provider: 数据提供者实例
        """
        cls._providers[name] = provider
    
    @classmethod
    def get_provider(cls, name: str) -> Optional[DataProvider]:
        """获取数据提供者
        
        Args:
            name: 提供者名称
            
        Returns:
            数据提供者实例
        """
        return cls._providers.get(name)
    
    @classmethod
    def list_providers(cls) -> list:
        """列出所有可用的数据提供者
        
        Returns:
            提供者名称列表
        """
        return list(cls._providers.keys())