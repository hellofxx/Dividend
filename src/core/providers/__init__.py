"""
数据源层

提供统一的数据获取接口。
仅使用 AkshareDataProvider 作为数据源。
"""

from .base import DataProvider, DataProviderFactory
from .akshare_data_provider import AkshareDataProvider

__all__ = ["DataProvider", "DataProviderFactory", "AkshareDataProvider"]
