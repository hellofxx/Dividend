"""KDJ图表模块

展示KDJ指标图，包含K线、D线和J线。
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from src.judgment.indicators.kdj import KDJ

class KDJChart:
    """KDJ图表"""
    
    def __init__(self, figsize=(12, 3)):
        """初始化KDJ图表
        
        Args:
            figsize: 图表大小
        """
        self.figsize = figsize
    
    def create(self, df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3):
        """创建KDJ图表
        
        Args:
            df: 包含价格数据的DataFrame
            n: 计算周期
            m1: K线平滑周期
            m2: D线平滑周期
            
        Returns:
            plt.Figure: 图表对象
        """
        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_subplot(111)
        
        # 计算KDJ指标
        k, d, j = KDJ.calculate(df, n, m1, m2)
        
        # 绘制K线、D线和J线
        ax.plot(df['date'], k, linewidth=1, color='blue', label='K')
        ax.plot(df['date'], d, linewidth=1, color='orange', label='D')
        ax.plot(df['date'], j, linewidth=1, color='green', label='J')
        
        # 绘制超买超卖线
        ax.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='超买')
        ax.axhline(y=20, color='green', linestyle='--', alpha=0.5, label='超卖')
        ax.axhline(y=50, color='gray', linestyle='--', alpha=0.3)
        
        # 设置日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        
        # 设置标签和标题
        ax.set_ylabel('KDJ')
        ax.set_title(f'KDJ ({n},{m1},{m2})')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        return fig