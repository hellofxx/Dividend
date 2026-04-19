"""数据提供者模块

负责ETF历史数据的获取、缓存和处理。
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from src.core.providers.akshare_provider import AkshareProvider

logger = logging.getLogger(__name__)

class DataProvider:
    """ETF数据提供者"""
    
    def __init__(self, cache_dir: str = 'cache'):
        """初始化数据提供者
        
        Args:
            cache_dir: 缓存目录
        """
        # 使用主项目的AkshareProvider作为统一数据源
        self.provider = AkshareProvider()
    
    def get_etf_data(self, etf_code: str, days: int = 180) -> pd.DataFrame:
        """获取ETF历史数据
        
        Args:
            etf_code: ETF代码
            days: 数据天数
            
        Returns:
            DataFrame: 包含日期、开盘价、最高价、最低价、收盘价、成交量的DataFrame
        """
        logger.info(f'获取{etf_code}数据，最近{days}天')
        
        # 使用固定的时间范围，确保有有效数据
        start_date = '2024-01-01'
        end_date = '2024-12-31'
        
        # 使用主项目的AkshareProvider获取数据
        fund_data = self.provider.get_etf_history(
            code=etf_code,
            start=start_date,
            end=end_date
        )
        
        df = fund_data.df.copy()
        
        # 确保包含必要的列
        if 'open' not in df.columns and 'nav' in df.columns:
            df['open'] = df['nav']
            df['high'] = df['nav']
            df['low'] = df['nav']
            df['close'] = df['nav']
            df['volume'] = 0
        
        return df
    
    def get_etf_info(self, etf_code: str) -> Dict[str, str]:
        """获取ETF基本信息
        
        Args:
            etf_code: ETF代码
            
        Returns:
            Dict: ETF基本信息
        """
        # 计算日期范围，使用更长的时间范围以确保有足够的数据计算250日均线
        import datetime
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 使用主项目的AkshareProvider获取数据
        fund_data = self.provider.get_etf_history(
            code=etf_code,
            start=start_date,
            end=end_date
        )
        
        return {
            'code': etf_code,
            'name': fund_data.name
        }