"""布林带指标计算模块

布林带（Bollinger Bands）是一种 volatility 指标，由中轨、上轨和下轨组成。
"""

import pandas as pd

class BollingerBands:
    """布林带指标计算器"""
    
    @staticmethod
    def calculate(df: pd.DataFrame, period: int = 20, std_dev: float = 2) -> tuple:
        """计算布林带指标
        
        Args:
            df: 包含收盘价的DataFrame
            period: 计算周期
            std_dev: 标准差倍数
            
        Returns:
            tuple: (中轨, 上轨, 下轨)
        """
        if 'close' not in df.columns:
            raise ValueError('DataFrame must contain "close" column')
        
        # 计算中轨（移动平均线）
        middle_band = df['close'].rolling(window=period).mean()
        
        # 计算标准差
        std = df['close'].rolling(window=period).std()
        
        # 计算上轨和下轨
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return middle_band, upper_band, lower_band
    
    @staticmethod
    def get_signal(close: float, upper_band: float, lower_band: float) -> str:
        """根据布林带值获取交易信号
        
        Args:
            close: 收盘价
            upper_band: 上轨
            lower_band: 下轨
            
        Returns:
            str: 交易信号
        """
        if close > upper_band:
            return '超买'
        elif close < lower_band:
            return '超卖'
        else:
            return '正常'