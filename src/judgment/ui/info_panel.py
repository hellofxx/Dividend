"""信息面板模块

实现左侧信息面板，包含ETF基本信息、BIAS指标信息和买入信号判定结果。
"""

import tkinter as tk
from tkinter import ttk
import pandas as pd

from src.judgment.indicators.bias import BIAS
from src.judgment.indicators.signal_generator import SignalGenerator

class InfoPanel:
    """信息面板"""
    
    def __init__(self, parent):
        """初始化信息面板
        
        Args:
            parent: 父窗口
        """
        self.frame = ttk.LabelFrame(parent, text="ETF信息", width=300)
        
        # 基本信息区域
        self.basic_frame = ttk.LabelFrame(self.frame, text="基本信息")
        self.basic_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.code_label = ttk.Label(self.basic_frame, text="代码:")
        self.code_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.code_value = ttk.Label(self.basic_frame, text="-")
        self.code_value.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.name_label = ttk.Label(self.basic_frame, text="名称:")
        self.name_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.name_value = ttk.Label(self.basic_frame, text="-")
        self.name_value.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.price_label = ttk.Label(self.basic_frame, text="最新价格:")
        self.price_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.price_value = ttk.Label(self.basic_frame, text="-")
        self.price_value.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.change_label = ttk.Label(self.basic_frame, text="涨跌幅:")
        self.change_label.grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.change_value = ttk.Label(self.basic_frame, text="-")
        self.change_value.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        # BIAS指标区域
        self.bias_frame = ttk.LabelFrame(self.frame, text="BIAS指标")
        self.bias_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.bias_value_label = ttk.Label(self.bias_frame, text="BIAS值:")
        self.bias_value_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.bias_value = ttk.Label(self.bias_frame, text="-")
        self.bias_value.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.bias_level_label = ttk.Label(self.bias_frame, text="偏离程度:")
        self.bias_level_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.bias_level = ttk.Label(self.bias_frame, text="-")
        self.bias_level.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 买入信号区域
        self.signal_frame = ttk.LabelFrame(self.frame, text="买入信号")
        self.signal_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.signal_label = ttk.Label(self.signal_frame, text="信号:")
        self.signal_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.signal_value = ttk.Label(self.signal_frame, text="-", font=('Arial', 12, 'bold'))
        self.signal_value.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.reason_label = ttk.Label(self.signal_frame, text="依据:")
        self.reason_label.grid(row=1, column=0, sticky=tk.NW, padx=5, pady=2)
        self.reason_value = ttk.Label(self.signal_frame, text="-", wraplength=200, justify=tk.LEFT)
        self.reason_value.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 加载状态
        self.loading_label = ttk.Label(self.frame, text="加载中...")
    
    def pack(self, **kwargs):
        """包装控件"""
        self.frame.pack(**kwargs)
    
    def show_loading(self):
        """显示加载状态"""
        self.loading_label.pack(pady=10)
    
    def show_error(self, error_msg: str):
        """显示错误信息"""
        self.loading_label.pack_forget()
        error_label = ttk.Label(self.frame, text=error_msg, foreground="red")
        error_label.pack(pady=10)
    
    def update_info(self, etf_info: dict, df: pd.DataFrame):
        """更新信息
        
        Args:
            etf_info: ETF基本信息
            df: 包含价格数据的DataFrame
        """
        # 隐藏加载状态
        self.loading_label.pack_forget()
        
        # 更新基本信息
        self.code_value.config(text=etf_info.get('code', '-'))
        self.name_value.config(text=etf_info.get('name', '-'))
        
        if not df.empty:
            # 获取最新数据
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest
            
            # 计算涨跌幅
            change = (latest['close'] - previous['close']) / previous['close'] * 100
            
            self.price_value.config(text=f"{latest['close']:.2f}")
            self.change_value.config(
                text=f"{change:+.2f}%",
                foreground="red" if change > 0 else "green"
            )
            
            # 计算BIAS指标
            bias = BIAS.calculate(df, n=20).iloc[-1]
            bias_signal = BIAS.get_signal(bias)
            
            self.bias_value.config(text=f"{bias:.2f}")
            
            # 确定BIAS偏离程度
            if bias < -5:
                bias_level = "严重超卖"
                level_color = "green"
            elif bias < 0:
                bias_level = "轻微超卖"
                level_color = "lightgreen"
            elif bias > 5:
                bias_level = "严重超买"
                level_color = "red"
            elif bias > 0:
                bias_level = "轻微超买"
                level_color = "orange"
            else:
                bias_level = "正常"
                level_color = "black"
            
            self.bias_level.config(text=bias_level, foreground=level_color)
            
            # 更新买入信号
            signal_generator = SignalGenerator()
            signal_result = signal_generator.generate_signal(df)
            signal = signal_result['signal']
            reason = signal_result['reason']
            
            self.signal_value.config(text=signal)
            if signal == "买入":
                self.signal_value.config(foreground="green")
            elif signal == "卖出":
                self.signal_value.config(foreground="red")
            else:
                self.signal_value.config(foreground="black")
            
            # 更新信号依据
            self.reason_value.config(text=reason)