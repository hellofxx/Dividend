"""
数据源层

提供统一的数据获取接口。
仅使用 AkshareProvider 作为数据源。
"""

from .base import BaseProvider
from .akshare_provider import AkshareProvider

__all__ = ["BaseProvider", "AkshareProvider"]
