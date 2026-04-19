"""成交量图表模块

展示ETF成交量柱状图，包含成交量均线。
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

class VolumeChart:
    """成交量图表"""
    
    def __init__(self, figsize=(12, 3)):
        """初始化成交量图表
        
        Args:
            figsize: 图表大小
        """
        self.figsize = figsize
    
    def create(self, df: pd.DataFrame, ma_period: int = 5):
        """创建成交量图表
        
        Args:
            df: 包含成交量数据的DataFrame
            ma_period: 成交量均线周期
            
        Returns:
            plt.Figure: 图表对象
        """
        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_subplot(111)
        
        # 绘制成交量柱状图
        for i, row in df.iterrows():
            color = 'red' if row['close'] >= row['open'] else 'green'
            ax.bar(row['date'], row['volume'], color=color, alpha=0.6)
        
        # 绘制成交量均线
        if 'volume' in df.columns:
            volume_ma = df['volume'].rolling(window=ma_period).mean()
            ax.plot(df['date'], volume_ma, color='blue', linewidth=1, label=f'均量({ma_period})')
        
        # 设置日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        
        # 设置标签和标题
        ax.set_ylabel('成交量')
        ax.set_title('成交量')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        return fig