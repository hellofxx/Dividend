"""布林带图表模块

展示布林带指标图，包含中轨、上轨和下轨。
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from src.judgment.indicators.bollinger import BollingerBands

class BollingerChart:
    """布林带图表"""
    
    def __init__(self, figsize=(12, 3)):
        """初始化布林带图表
        
        Args:
            figsize: 图表大小
        """
        self.figsize = figsize
    
    def create(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2):
        """创建布林带图表
        
        Args:
            df: 包含价格数据的DataFrame
            period: 计算周期
            std_dev: 标准差倍数
            
        Returns:
            plt.Figure: 图表对象
        """
        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_subplot(111)
        
        # 计算布林带指标
        middle_band, upper_band, lower_band = BollingerBands.calculate(df, period, std_dev)
        
        # 绘制价格和布林带
        ax.plot(df['date'], df['close'], linewidth=1, color='blue', label='收盘价')
        ax.plot(df['date'], middle_band, linewidth=1, color='black', label=f'中轨({period})')
        ax.plot(df['date'], upper_band, linewidth=1, color='red', linestyle='--', label='上轨')
        ax.plot(df['date'], lower_band, linewidth=1, color='green', linestyle='--', label='下轨')
        
        # 填充布林带区域
        ax.fill_between(df['date'], upper_band, lower_band, color='gray', alpha=0.1)
        
        # 设置日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        
        # 设置标签和标题
        ax.set_ylabel('价格')
        ax.set_title(f'布林带 ({period},{std_dev})')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        return fig