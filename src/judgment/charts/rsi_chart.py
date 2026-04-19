"""RSI图表模块

展示RSI指标图，支持自定义周期参数。
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from src.judgment.indicators.rsi import RSI

class RSChart:
    """RSI图表"""
    
    def __init__(self, figsize=(12, 3)):
        """初始化RSI图表
        
        Args:
            figsize: 图表大小
        """
        self.figsize = figsize
    
    def create(self, df: pd.DataFrame, period: int = 14):
        """创建RSI图表
        
        Args:
            df: 包含价格数据的DataFrame
            period: RSI计算周期
            
        Returns:
            plt.Figure: 图表对象
        """
        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_subplot(111)
        
        # 计算RSI指标
        rsi = RSI.calculate(df, period)
        
        # 绘制RSI线
        ax.plot(df['date'], rsi, linewidth=1, color='purple', label=f'RSI({period})')
        
        # 绘制超买超卖线
        ax.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='超买')
        ax.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='超卖')
        ax.axhline(y=50, color='gray', linestyle='--', alpha=0.3)
        
        # 设置日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        
        # 设置标签和标题
        ax.set_ylabel('RSI')
        ax.set_title(f'RSI ({period})')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        return fig