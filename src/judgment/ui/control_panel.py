"""控制面板模块

实现顶部导航栏，包含ETF代码输入框、手动刷新按钮、参数设置入口。
"""

import tkinter as tk
from tkinter import ttk

class ControlPanel(ttk.Frame):
    """控制面板"""
    
    def __init__(self, parent, etf_code: str, on_refresh, on_config):
        """初始化控制面板
        
        Args:
            parent: 父窗口
            etf_code: ETF代码
            on_refresh: 刷新回调函数
            on_config: 配置回调函数
        """
        super().__init__(parent)
        
        # ETF代码输入
        ttk.Label(self, text="ETF代码:").pack(side=tk.LEFT, padx=5)
        self.etf_entry = ttk.Entry(self, width=10)
        self.etf_entry.insert(0, etf_code)
        self.etf_entry.pack(side=tk.LEFT, padx=5)
        
        # 刷新按钮
        self.refresh_btn = ttk.Button(self, text="刷新", command=on_refresh)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # 配置按钮
        self.config_btn = ttk.Button(self, text="参数设置", command=on_config)
        self.config_btn.pack(side=tk.LEFT, padx=5)
        
        # 图表类型选择
        ttk.Label(self, text="图表类型:").pack(side=tk.LEFT, padx=5)
        self.chart_type_var = tk.StringVar(value="candle")
        chart_types = ["蜡烛图", "折线图"]
        self.chart_type_combo = ttk.Combobox(
            self, 
            textvariable=self.chart_type_var, 
            values=chart_types, 
            state="readonly",
            width=8
        )
        self.chart_type_combo.pack(side=tk.LEFT, padx=5)
    
    def get_etf_code(self) -> str:
        """获取ETF代码
        
        Returns:
            str: ETF代码
        """
        return self.etf_entry.get().strip()
    
    def get_chart_type(self) -> str:
        """获取图表类型
        
        Returns:
            str: 图表类型 ('candle' 或 'line')
        """
        return "candle" if self.chart_type_var.get() == "蜡烛图" else "line"