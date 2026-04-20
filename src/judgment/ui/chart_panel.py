"""图表面板模块

实现右侧图表面板，包含6个技术分析图表。
"""

import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

from src.judgment.charts.kline_chart import KlineChart
from src.judgment.charts.volume_chart import VolumeChart
from src.judgment.charts.macd_chart import MACDChart
from src.judgment.charts.rsi_chart import RSChart
from src.judgment.charts.kdj_chart import KDJChart
from src.judgment.charts.bollinger_chart import BollingerChart

class ChartPanel:
    """图表面板"""
    
    def __init__(self, parent):
        """初始化图表面板
        
        Args:
            parent: 父窗口
        """
        self.frame = ttk.Frame(parent)
        
        # 创建5个图表容器（移除成交量图表）
        self.chart_frames = []
        chart_titles = ['K线走势', 'MACD指标', 'RSI指标', 'KDJ指标', '布林带指标']
        for i, title in enumerate(chart_titles):
            chart_frame = ttk.LabelFrame(self.frame, text=title)
            chart_frame.grid(row=i, column=0, sticky='nsew', padx=5, pady=5)  # 增加pady间距
            self.chart_frames.append(chart_frame)
        
        # 设置行权重，确保所有图表高度一致
        for i in range(5):
            self.frame.grid_rowconfigure(i, weight=1)
        
        # 设置列权重
        self.frame.grid_columnconfigure(0, weight=1)
        
        # 图表实例（移除成交量图表）
        # 使用统一的 figsize，确保图表尺寸一致
        self.charts = {
            'kline': KlineChart(figsize=(8, 3)),  # 调整尺寸以适应窗口
            'macd': MACDChart(figsize=(8, 3)),
            'rsi': RSChart(figsize=(8, 3)),
            'kdj': KDJChart(figsize=(8, 3)),
            'bollinger': BollingerChart(figsize=(8, 3))
        }
        
        # 加载状态
        self.loading_labels = []
        for frame in self.chart_frames:
            loading_label = ttk.Label(frame, text="加载中...")
            loading_label.pack(pady=10)
            self.loading_labels.append(loading_label)
        
        # 绑定窗口尺寸变化事件（只绑定一次）
        self.frame.bind('<Configure>', self._on_configure)
    
    def pack(self, **kwargs):
        """包装控件"""
        self.frame.pack(**kwargs)
    
    def show_loading(self):
        """显示加载状态"""
        for i, frame in enumerate(self.chart_frames):
            # 清空容器
            for widget in frame.winfo_children():
                widget.destroy()
            loading_label = ttk.Label(frame, text="加载中...")
            loading_label.pack(pady=10)
            self.loading_labels[i] = loading_label
    
    def show_error(self, error_msg: str):
        """显示错误信息"""
        for i, frame in enumerate(self.chart_frames):
            # 清空容器
            for widget in frame.winfo_children():
                widget.destroy()
            error_label = ttk.Label(frame, text=error_msg, foreground="red")
            error_label.pack(pady=10)
    
    def update_charts(self, df: pd.DataFrame):
        """更新图表
        
        Args:
            df: 包含价格数据的DataFrame
        """
        if df.empty:
            return
        
        # 存储数据，用于响应式布局时重新生成图表
        self.set_data(df)
        
        # 隐藏加载状态
        for loading_label in self.loading_labels:
            loading_label.pack_forget()
        
        # 更新K线图
        self._update_chart(0, 'kline', df)
        
        # 更新MACD图
        self._update_chart(1, 'macd', df)
        
        # 更新RSI图
        self._update_chart(2, 'rsi', df)
        
        # 更新KDJ图
        self._update_chart(3, 'kdj', df)
        
        # 更新布林带图
        self._update_chart(4, 'bollinger', df)
    
    def _update_chart(self, index: int, chart_type: str, df: pd.DataFrame):
        """更新单个图表
        
        Args:
            index: 图表索引
            chart_type: 图表类型
            df: 数据
        """
        try:
            # 清空容器
            for widget in self.chart_frames[index].winfo_children():
                widget.destroy()
            
            # 创建图表
            if chart_type == 'kline':
                fig = self.charts[chart_type].create(df, chart_type='candle')
            else:
                fig = self.charts[chart_type].create(df)
            
            # 创建画布
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frames[index])
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            error_label = ttk.Label(self.chart_frames[index], text=f"图表生成失败: {e}", foreground="red")
            error_label.pack(pady=10)
    
    def _on_configure(self, event):
        """处理窗口尺寸变化事件"""
        # 防抖处理：取消之前的定时器
        if hasattr(self, '_resize_timer'):
            try:
                self.frame.after_cancel(self._resize_timer)
            except Exception:
                pass
        
        # 延迟执行，避免频繁触发
        self._resize_timer = self.frame.after(200, self._resize_charts)
    
    def _resize_charts(self):
        """重新调整图表大小"""
        # 检查数据是否存在
        if not hasattr(self, 'df') or self.df.empty:
            return
        
        # 按顺序更新所有图表，确保同步显示
        chart_types = ['kline', 'macd', 'rsi', 'kdj', 'bollinger']
        for i, chart_type in enumerate(chart_types):
            # 检查图表容器是否存在
            if i < len(self.chart_frames):
                # 清空容器
                for widget in self.chart_frames[i].winfo_children():
                    widget.destroy()
                
                # 重新创建图表
                try:
                    if chart_type == 'kline':
                        fig = self.charts[chart_type].create(self.df, chart_type='candle')
                    else:
                        fig = self.charts[chart_type].create(self.df)
                    
                    # 创建画布
                    canvas = FigureCanvasTkAgg(fig, master=self.chart_frames[i])
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                except Exception as e:
                    # 显示错误信息
                    error_label = ttk.Label(self.chart_frames[i], text=f"图表生成失败: {e}", foreground="red")
                    error_label.pack(pady=10)
    
    def set_data(self, df: pd.DataFrame):
        """设置数据，用于响应式布局时重新生成图表"""
        self.df = df