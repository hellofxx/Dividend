"""主窗口模块

实现ETF技术分析工具的主界面布局。
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from src.judgment.ui.control_panel import ControlPanel
from src.judgment.ui.info_panel import InfoPanel
from src.judgment.ui.chart_panel import ChartPanel
from src.judgment.data.data_provider import DataProvider
from src.core.utils.logger import setup_logging

logger = setup_logging()

class MainWindow:
    """主窗口"""

    def __init__(self, root, etf_code: str, theme: str = 'professional', config_path: str = None):
        """初始化主窗口

        Args:
            root: 根窗口
            etf_code: ETF代码
            theme: 可视化主题
            config_path: 配置文件路径
        """
        self.root = root
        self.etf_code = etf_code
        self.theme = theme
        self.config = {}  # 简化配置，使用空字典

        # 数据提供者
        self.data_provider = DataProvider(cache_dir='cache')

        # 创建主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建顶部控制栏
        self.control_panel = ControlPanel(self.main_frame, self.etf_code, self.on_refresh, self.on_config)
        self.control_panel.pack(fill=tk.X, pady=(0, 10))

        # 创建主内容区域
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # 创建左侧信息面板
        self.info_panel = InfoPanel(self.content_frame)
        self.info_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), ipady=10)

        # 创建右侧图表面板
        self.chart_panel = ChartPanel(self.content_frame)
        self.chart_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 强制渲染所有控件
        self.root.update()

        # 初始化数据
        self.update_data()
        
        # 添加窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def update_data(self):
        """更新数据"""
        # 显示加载状态
        self.info_panel.show_loading()
        self.chart_panel.show_loading()
        
        # 模拟数据更新（实际应在后台线程中执行）
        self.root.after(100, self._load_data)
    
    def _load_data(self):
        """加载数据"""
        try:
            # 获取ETF数据
            logger.info(f'开始获取{self.etf_code}数据')
            df = self.data_provider.get_etf_data(self.etf_code, days=180)
            logger.info(f'数据获取成功，共{len(df)}条记录')
            
            etf_info = self.data_provider.get_etf_info(self.etf_code)
            logger.info(f'获取ETF信息成功: {etf_info}')
            
            # 更新信息面板
            logger.info('开始更新信息面板')
            self.info_panel.update_info(etf_info, df)
            logger.info('信息面板更新成功')
            
            # 更新图表面板
            logger.info('开始更新图表面板')
            self.chart_panel.update_charts(df)
            logger.info('图表面板更新成功')
            
        except Exception as e:
            logger.error(f'数据加载失败: {e}', exc_info=True)
            self.info_panel.show_error(f'数据加载失败: {e}')
            self.chart_panel.show_error(f'图表生成失败: {e}')
    
    def on_refresh(self):
        """刷新数据"""
        self.etf_code = self.control_panel.get_etf_code()
        self.update_data()
    
    def on_config(self):
        """打开配置窗口"""
        # 这里可以添加配置窗口逻辑
        pass
    
    def on_close(self):
        """窗口关闭事件处理"""
        print("[INFO] 窗口关闭，终止进程")
        # 关闭窗口
        self.root.destroy()
        # 终止进程
        import sys
        sys.exit(0)