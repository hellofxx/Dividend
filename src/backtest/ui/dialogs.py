"""
Tkinter弹窗封装

Windows原生GUI组件。
"""

import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, Dict, Optional
from datetime import datetime

from PIL import Image, ImageGrab

from src.core.models import BacktestResult, CompareResult

logger = logging.getLogger(__name__)


class ResultDialog:
    """
    结果汇总弹窗
    
    展示指标面板及可滚动交易日志。
    提供"保存图表并退出"与"取消"。
    """
    
    def __init__(self, parent: Optional[tk.Tk] = None):
        self.parent = parent
        self.result: Optional[BacktestResult] = None
        self.compare_result: Optional[CompareResult] = None
        self.on_save: Optional[Callable[[], None]] = None
        self.dialog: Optional[tk.Toplevel] = None
        self.output_dir: Optional[Path] = None

    def show(
        self,
        result: BacktestResult,
        on_save: Callable[[], None],
        on_cancel: Callable[[], None],
        compare_result: Optional[CompareResult] = None,
        output_dir: Optional[Path] = None,
        fund_code: str = "007466",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        modal: bool = True,
    ) -> tk.Toplevel:
        """
        显示结果弹窗
        
        Args:
            result: 回测结果
            on_save: 保存按钮回调
            on_cancel: 取消按钮回调
            compare_result: 基准对比结果
            output_dir: 输出目录（用于保存弹窗截图）
            fund_code: 基金代码
            start_date: 回测开始日期
            end_date: 回测结束日期
            modal: 是否模态（默认True阻塞，False可同时显示多个弹窗）
        
        Returns:
            创建的弹窗对象（modal=False时可用于后续操作）
        """
        self.result = result
        self.compare_result = compare_result
        self.on_save = on_save
        self.output_dir = output_dir
        
        # 创建弹窗
        if self.parent is None:
            self.dialog = tk.Tk()
            self.dialog.title("回测结果汇总")
        else:
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("回测结果汇总")
            # 注意：不使用 transient()，因为 parent 被 withdraw() 会导致子窗口尺寸异常
        
        # 先设置最小尺寸，防止内容布局后窗口缩小
        self.dialog.minsize(600, 400)
        self.dialog.resizable(True, True)
        
        # 设置关闭处理
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: self._on_dialog_close(on_cancel))
        
        # 创建滚动容器
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 策略配置（放在首位）
        self._create_strategy_panel(scrollable_frame, fund_code, start_date, end_date)
        
        # 基准对标 + 风险指标（并列展示）
        self._create_benchmark_and_risk_panel(scrollable_frame)
        
        # 累计收益分解 + 年化收益分解（并列展示）
        self._create_return_and_annual_panel(scrollable_frame)
        
        # 交易日志
        self._create_trades_log(scrollable_frame)
        
        # 按钮区域
        self._create_buttons(scrollable_frame, on_cancel)
        
        # 确保弹窗可见并置顶（关键：在 update 之后重新设置尺寸）
        self.dialog.update_idletasks()
        # 强制设置尺寸和位置，确保窗口可见
        self.dialog.geometry("750x650+100+100")
        self.dialog.minsize(600, 400)  # 设置最小尺寸防止被压缩
        self.dialog.deiconify()  # 确保窗口不是图标化状态
        self.dialog.lift()
        self.dialog.focus_force()
        
        if self.parent is None:
            self.dialog.mainloop()
        
        return self.dialog
    
    def _on_dialog_close(self, on_cancel: Callable[[], None]) -> None:
        """弹窗关闭处理"""
        if on_cancel:
            on_cancel()
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None  # 清理引用
    
    def _create_strategy_panel(self, parent: tk.Widget, fund_code: str, 
                               start_date: Optional[str], end_date: Optional[str]) -> None:
        """创建策略配置面板（紧凑布局）"""
        strategy_frame = ttk.LabelFrame(parent, text="策略配置", padding=5)
        strategy_frame.pack(fill=tk.X, padx=8, pady=2)

        # 获取实际日期范围
        if self.result and hasattr(self.result, 'dates') and len(self.result.dates) > 0:
            actual_start = self.result.dates[0].strftime('%Y-%m-%d')
            actual_end = self.result.dates[-1].strftime('%Y-%m-%d')
        else:
            actual_start = start_date or "2022-01-01"
            actual_end = end_date or datetime.now().strftime('%Y-%m-%d')

        # 第一行：策略名称 + 基金代码
        row1 = ttk.Frame(strategy_frame)
        row1.pack(fill=tk.X, pady=1)
        ttk.Label(row1, text="策略:", font=('Microsoft YaHei', 8)).pack(side=tk.LEFT)
        ttk.Label(row1, text="红利低波年线策略(Bias<0买入)", font=('Microsoft YaHei', 8, 'bold')).pack(side=tk.LEFT)
        ttk.Separator(row1, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y)
        ttk.Label(row1, text="基金:", font=('Microsoft YaHei', 8)).pack(side=tk.LEFT)
        ttk.Label(row1, text=fund_code, font=('Microsoft YaHei', 8, 'bold')).pack(side=tk.LEFT)
        
        # 第二行：回测区间 + 分红模式
        row2 = ttk.Frame(strategy_frame)
        row2.pack(fill=tk.X, pady=1)
        ttk.Label(row2, text="回测区间:", font=('Microsoft YaHei', 8)).pack(side=tk.LEFT)
        ttk.Label(row2, text=f"{actual_start} ~ {actual_end}", font=('Microsoft YaHei', 8)).pack(side=tk.LEFT)
        ttk.Separator(row2, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y)
        ttk.Label(row2, text="初始资金: 100,000元 | 分红模式: 再投(reinvest)", font=('Microsoft YaHei', 8)).pack(side=tk.LEFT)
        
        # 第三行：策略逻辑简述
        row3 = ttk.Frame(strategy_frame)
        row3.pack(fill=tk.X, pady=1)
        ttk.Label(
            row3,
            text="规则: 低于250日年线即买入 | 高于年线10%以上卖出",
            font=('Microsoft YaHei', 8),
            foreground='#666666',
        ).pack(side=tk.LEFT)

    def _create_benchmark_panel(self, parent: tk.Widget) -> None:
        """创建基准对标面板"""
        if self.compare_result is None:
            return
        
        cm = self.compare_result.compare_metrics
        if cm is None or len(cm) == 0:
            return
        
        benchmark_frame = ttk.LabelFrame(parent, text="基准对标", padding=8)
        benchmark_frame.pack(fill=tk.X, padx=8, pady=3)
        
        # 获取各策略数据
        metrics_dict = {}
        for _, row in cm.iterrows():
            strategy_name = row['strategy']
            metrics_dict[strategy_name] = {
                'total_return': float(row.get('total_return', 0.0)),
                'annual_return': float(row.get('annual_return', 0.0)),
                'excess_return': float(row.get('excess_return', 0.0)),
            }
        
        # 创建对比表格
        headers = ['策略', '累计收益率', '年化收益率', '超额收益(vs沪深300)']
        
        # 表格框架
        table_frame = ttk.Frame(benchmark_frame)
        table_frame.pack(fill=tk.X, pady=2)
        
        # 表头
        for col, header in enumerate(headers):
            lbl = ttk.Label(table_frame, text=header, font=('Microsoft YaHei', 8, 'bold'),
                           width=18 if col == 0 else 14)
            lbl.grid(row=0, column=col, padx=2, pady=2)
        
        # 数据行
        strategy_order = [
            ('主策略(年线)', '红利低波策略'),
            ('一次性买入', '一次性买入'),
            ('定期定投', '定期定投'),
        ]
        
        row_idx = 1
        for strategy_key, display_name in strategy_order:
            if strategy_key in metrics_dict:
                m = metrics_dict[strategy_key]
                
                # 策略名
                ttk.Label(table_frame, text=display_name, 
                         font=('Microsoft YaHei', 9)).grid(row=row_idx, column=0, padx=2, pady=1)
                
                # 累计收益率
                total_ret = m['total_return']
                color = "green" if total_ret >= 0 else "red"
                ttk.Label(table_frame, text=f"{total_ret:+.2f}%", 
                         font=('Microsoft YaHei', 9, 'bold'),
                         foreground=color).grid(row=row_idx, column=1, padx=2, pady=1)
                
                # 年化收益率
                annual_ret = m['annual_return']
                color = "green" if annual_ret >= 0 else "red"
                ttk.Label(table_frame, text=f"{annual_ret:+.2f}%", 
                         font=('Microsoft YaHei', 9, 'bold'),
                         foreground=color).grid(row=row_idx, column=2, padx=2, pady=1)
                
                # 超额收益
                excess = m['excess_return']
                color = "green" if excess >= 0 else "red"
                ttk.Label(table_frame, text=f"{excess:+.2f}%", 
                         font=('Microsoft YaHei', 9, 'bold'),
                         foreground=color).grid(row=row_idx, column=3, padx=2, pady=1)
                
                row_idx += 1

    def _create_benchmark_and_risk_panel(self, parent: tk.Widget) -> None:
        """创建基准对标和风险指标并列面板（中间用虚线隔开，紧凑布局）"""
        # 外层容器
        outer_frame = ttk.Frame(parent)
        outer_frame.pack(fill=tk.X, padx=8, pady=2)
        
        # 左半部分：基准对标（不自拉伸，内容多高就多高）
        benchmark_frame = ttk.LabelFrame(outer_frame, text="基准对标", padding=(8, 5))
        benchmark_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self._fill_benchmark_content(benchmark_frame)
        
        # 中间虚线分隔符（用Frame+灰色背景模拟，避免Canvas的dash参数问题）
        sep = tk.Frame(outer_frame, bg='#d0d0d0', width=2)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 右半部分：风险指标（不自拉伸）
        risk_frame = ttk.LabelFrame(outer_frame, text="风险指标", padding=(8, 5))
        risk_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        self._fill_risk_content(risk_frame)
    
    def _fill_benchmark_content(self, parent: tk.Widget) -> None:
        """填充基准对标内容（含沪深300）"""
        if self.compare_result is None:
            ttk.Label(parent, text="无对比数据").pack(pady=5)
            return

        cm = self.compare_result.compare_metrics
        if cm is None or len(cm) == 0:
            ttk.Label(parent, text="无对比数据").pack(pady=5)
            return

        # 获取各策略数据 + 沪深300数据
        metrics_dict = {}
        hs300_return = 0.0
        for _, row in cm.iterrows():
            strategy_name = row['strategy']
            metrics_dict[strategy_name] = {
                'total_return': float(row.get('total_return', 0.0)),
                'annual_return': float(row.get('annual_return', 0.0)),
                'excess_return': float(row.get('excess_return', 0.0)),
            }

        # 从 CompareResult 获取沪深300数据（如果有）
        if hasattr(self.compare_result, 'index_return'):
            hs300_return = self.compare_result.index_return
        elif hasattr(self.result, 'metrics') and 'hs300_return' in self.result.metrics:
            hs300_return = self.result.metrics['hs300_return']

        # 表头行
        header_row = ttk.Frame(parent)
        header_row.pack(fill=tk.X, pady=(2, 1))
        ttk.Label(header_row, text="策略", font=('Microsoft YaHei', 8, 'bold'), width=11).pack(side=tk.LEFT)
        ttk.Label(header_row, text="累计收益", font=('Microsoft YaHei', 8, 'bold'), width=9).pack(side=tk.LEFT)
        ttk.Label(header_row, text="年化", font=('Microsoft YaHei', 8, 'bold'), width=7).pack(side=tk.LEFT)

        # 数据行
        strategy_order = [
            ('主策略(年线)', '红利低波策略'),
            ('一次性买入', '一次性买入'),
            ('定期定投', '定期定投'),
        ]

        for strategy_key, display_name in strategy_order:
            if strategy_key not in metrics_dict:
                continue
            m = metrics_dict[strategy_key]
            
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=1)
            
            # 策略名
            ttk.Label(row, text=display_name, font=('Microsoft YaHei', 9), width=11).pack(side=tk.LEFT)
            
            # 累计收益率
            total_ret = m['total_return']
            color = "green" if total_ret >= 0 else "red"
            ttk.Label(row, text=f"{total_ret:+.2f}%", font=('Microsoft YaHei', 9, 'bold'),
                     foreground=color, width=9).pack(side=tk.LEFT)
            
            # 年化收益率
            annual_ret = m['annual_return']
            color = "green" if annual_ret >= 0 else "red"
            ttk.Label(row, text=f"{annual_ret:+.1f}%", font=('Microsoft YaHei', 9),
                     foreground=color, width=7).pack(side=tk.LEFT)

        # 分隔线
        sep_frame = ttk.Frame(parent)
        sep_frame.pack(fill=tk.X, pady=3)
        ttk.Separator(sep_frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # 沪深300同期收益率
        hs300_row = ttk.Frame(parent)
        hs300_row.pack(fill=tk.X, pady=1)
        color = "green" if hs300_return >= 0 else "red"
        ttk.Label(hs300_row, text="沪深300", font=('Microsoft YaHei', 9), width=11).pack(side=tk.LEFT)
        ttk.Label(hs300_row, text=f"{hs300_return:+.2f}%", font=('Microsoft YaHei', 9, 'bold'),
                 foreground=color, width=9).pack(side=tk.LEFT)
    
    def _fill_risk_content(self, parent: tk.Widget) -> None:
        """填充风险指标内容 - 2x2网格布局"""
        metrics = self.result.metrics
        
        # 使用 grid 布局：2列 x 2行
        items = [
            ("最大回撤", f"{metrics.get('max_drawdown', 0):.2f}%", 0, 0),
            ("夏普比率", f"{metrics.get('sharpe_ratio', 0):.2f}", 0, 1),
            ("卡玛比率", f"{metrics.get('calmar_ratio', 0):.2f}", 1, 0),
            ("胜率", f"{metrics.get('win_rate', 0):.1f}%", 1, 1),
        ]
        
        for name, value, r, c in items:
            frame = ttk.Frame(parent)
            frame.grid(row=r, column=c, padx=10, pady=3, sticky='w')
            
            # 名称 + 冒号
            ttk.Label(frame, text=f"{name}:", font=('Microsoft YaHei', 8)).pack(side=tk.LEFT)
            # 数值加粗
            ttk.Label(frame, text=value, font=('Microsoft YaHei', 9, 'bold')).pack(side=tk.LEFT)

    def _create_return_and_annual_panel(self, parent: tk.Widget) -> None:
        """创建累计收益分解和年化收益分解并列面板（中间用虚线隔开，紧凑布局）"""
        # 外层容器
        outer_frame = ttk.Frame(parent)
        outer_frame.pack(fill=tk.X, padx=8, pady=2)
        
        # 左半部分：累计收益分解（不自拉伸）
        return_frame = ttk.LabelFrame(outer_frame, text="累计收益分解", padding=(8, 5))
        return_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self._fill_return_content(return_frame)
        
        # 中间分隔符（用Frame+灰色背景模拟）
        sep = tk.Frame(outer_frame, bg='#d0d0d0', width=2)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 右半部分：年化收益分解（不自拉伸）
        annual_frame = ttk.LabelFrame(outer_frame, text="年化收益分解", padding=(8, 5))
        annual_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        self._fill_annual_content(annual_frame)
    
    def _fill_return_content(self, parent: tk.Widget) -> None:
        """填充累计收益分解内容"""
        metrics = self.result.metrics
        
        items = [
            ("净值收益率", f"{metrics.get('nav_return', 0):.2f}%"),
            ("分红收益(再投)", f"{metrics.get('dividend_reinvest', 0):.2f}%"),
            ("分红收益(落袋)", f"{metrics.get('dividend_cash', 0):.2f}%"),
            ("累计收益率", f"{metrics.get('total_return', 0):.2f}%", True),
        ]
        
        for item in items:
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=1)
            name = item[0]
            value = item[1]
            is_bold = len(item) > 2 and item[2]
            
            ttk.Label(row, text=f"{name}:", font=('Microsoft YaHei', 8), width=12).pack(side=tk.LEFT)
            if is_bold:
                total_ret = metrics.get('total_return', 0)
                color = "green" if total_ret >= 0 else "red"
                ttk.Label(row, text=value, font=('Microsoft YaHei', 9, 'bold'), foreground=color).pack(side=tk.LEFT)
            else:
                ttk.Label(row, text=value, font=('Microsoft YaHei', 8)).pack(side=tk.LEFT)
    
    def _fill_annual_content(self, parent: tk.Widget) -> None:
        """填充年化收益分解内容"""
        metrics = self.result.metrics
        
        items = [
            ("净值年化", f"{metrics.get('annual_nav_return', 0):.2f}%"),
            ("分红年化(再投)", f"{metrics.get('annual_div_reinvest', 0):.2f}%"),
            ("分红年化(落袋)", f"{metrics.get('annual_div_cash', 0):.2f}%"),
            ("年化总收益", f"{metrics.get('annual_return', 0):.2f}%", True),
        ]
        
        for item in items:
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=1)
            name = item[0]
            value = item[1]
            is_bold = len(item) > 2 and item[2]
            
            ttk.Label(row, text=f"{name}:", font=('Microsoft YaHei', 8), width=12).pack(side=tk.LEFT)
            if is_bold:
                annual_ret = metrics.get('annual_return', 0)
                color = "green" if annual_ret >= 0 else "red"
                ttk.Label(row, text=value, font=('Microsoft YaHei', 9, 'bold'), foreground=color).pack(side=tk.LEFT)
            else:
                ttk.Label(row, text=value, font=('Microsoft YaHei', 8)).pack(side=tk.LEFT)

    def _get_strategy_description(self, fund_code: str, 
                                   start_date: Optional[str], 
                                   end_date: Optional[str]) -> str:
        """获取策略描述"""
        # 获取实际日期范围
        if self.result and hasattr(self.result, 'dates') and len(self.result.dates) > 0:
            actual_start = self.result.dates[0].strftime('%Y-%m-%d')
            actual_end = self.result.dates[-1].strftime('%Y-%m-%d')
        else:
            actual_start = start_date or "2022-01-01"
            actual_end = end_date or datetime.now().strftime('%Y-%m-%d')
        
        strategy_info = [
            "策略: 红利低波年线策略",
            "",
            "【策略逻辑】",
            "  1. 当基金净值低于250日年线时(Bias<0)，判断为低估区域，触发买入",
            "  2. 当基金净值高于年线10%以上(Bias≥10%)，判断为高估区域，触发卖出",
            "  3. 分红按指定模式处理(再投/落袋)",
            "",
            "【参数设置】",
            f"  基金产品: {fund_code}",
            f"  回测区间: {actual_start} 至 {actual_end}",
            "  均线周期: 250日",
            "  初始资金: 100,000元",
            "  分红模式: 默认分红再投(reinvest)",
        ]
        
        return "\n".join(strategy_info)
    
    def _create_trades_log(self, parent: tk.Widget) -> None:
        """创建交易日志区域"""
        frame = ttk.LabelFrame(parent, text="交易记录", padding=6)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=2)
        
        # 滚动文本框
        text = tk.Text(frame, height=6, wrap=tk.WORD, font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 插入交易记录 - 金额放在买入卖出之后，价格之前
        if len(self.result.trades) == 0:
            text.insert(tk.END, "无交易记录\n")
        else:
            text.insert(tk.END, f"共 {len(self.result.trades)} 笔交易\n")
            text.insert(tk.END, "-" * 65 + "\n")
            
            for trade in self.result.trades:
                action_str = "买入" if trade.action == "BUY" else "卖出"
                amount = trade.price * trade.shares
                text.insert(
                    tk.END,
                    f"{trade.date} | {action_str} | 金额:{amount:,.2f}元 | 价格:{trade.price:.4f} | 份额:{trade.shares:.2f}\n"
                )
        
        text.configure(state=tk.DISABLED)
    
    def _create_buttons(self, parent: tk.Widget, on_cancel: Callable[[], None]) -> None:
        """创建按钮区域"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=8, pady=8)
        
        # 添加保存弹窗截图按钮
        ttk.Button(
            frame,
            text="保存弹窗截图",
            command=self._save_dialog_screenshot,
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            frame,
            text="保存图表并退出",
            command=self._on_save_click,
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            frame,
            text="取消",
            command=lambda: self._on_cancel_click(on_cancel),
        ).pack(side=tk.RIGHT, padx=5)
    
    def _save_dialog_screenshot(self) -> None:
        """保存弹窗内容为图片"""
        if self.dialog is None or self.output_dir is None:
            return
        
        try:
            # 获取弹窗位置和大小
            self.dialog.update_idletasks()
            x = self.dialog.winfo_rootx()
            y = self.dialog.winfo_rooty()
            width = self.dialog.winfo_width()
            height = self.dialog.winfo_height()
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"result_dialog_{timestamp}.png"
            filepath = self.output_dir / filename
            
            # 截图
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            screenshot.save(filepath)
            
            logger.info(f"弹窗截图已保存: {filepath}")
            messagebox.showinfo("保存成功", f"弹窗截图已保存到:\n{filepath}")
            
        except Exception as e:
            logger.error(f"保存弹窗截图失败: {e}")
            messagebox.showerror("保存失败", f"保存截图失败: {e}")
    
    def _on_save_click(self) -> None:
        """保存按钮点击"""
        if self.on_save:
            self.on_save()
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None  # 清理引用
    
    def _on_cancel_click(self, on_cancel: Callable[[], None]) -> None:
        """取消按钮点击"""
        if on_cancel:
            on_cancel()
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None  # 清理引用


class PreviewDialog:
    """
    图表预览弹窗
    
    嵌入渲染完成的图片。
    提供"保存"、"重新生成"、"取消"。
    支持非模态模式（可同时显示多个弹窗）。
    
    布局策略：按钮固定在底部（pack side=BOTTOM），
    图片区域填充剩余空间（pack expand=True）。
    缩放策略：拖拽时用 BILINEAR 快速渲染，
    停止拖拽后用 LANCZOS 高质量重绘。
    """
    
    # 类变量：跟踪所有弹窗实例
    _instances: list = []
    
    def __init__(self, parent: Optional[tk.Tk] = None):
        self.parent = parent
        self.dialog: Optional[tk.Toplevel] = None
        self.image_path: Optional[Path] = None
        self._instance_id: Optional[int] = None
    
    def show(
        self,
        image_path: Path,
        on_save: Callable[[], None],
        on_regenerate: Callable[[], None],
        on_cancel: Callable[[], None],
        title: str = "图表预览",
        modal: bool = False,
    ) -> tk.Toplevel:
        """
        显示预览弹窗
        
        Args:
            image_path: 图片路径
            on_save: 保存按钮回调
            on_regenerate: 重新生成按钮回调
            on_cancel: 取消按钮回调
            title: 弹窗标题
            modal: 是否模态（默认False，可同时显示多个弹窗）
        
        Returns:
            创建的弹窗对象
        """
        self.image_path = image_path
        
        # 创建弹窗
        if self.parent is None:
            self.dialog = tk.Tk()
            self.dialog.title(title)
        else:
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title(title)
            # 注意：不使用 transient()，因为 parent 被 withdraw() 会导致子窗口尺寸异常
        
        # 先设置最小尺寸，防止内容布局后窗口缩小
        self.dialog.minsize(500, 400)
        
        # 添加到实例跟踪
        self._instance_id = len(PreviewDialog._instances)
        PreviewDialog._instances.append(self)
        
        # 设置关闭处理
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: self._on_close(on_cancel))
        
        # 初始窗口尺寸
        self.dialog.geometry("900x700")
        self.dialog.resizable(True, True)

        # === 关键布局变更：先 pack 按钮到底部，再 pack 图片区域到上方 ===
        # 1) 按钮区域先 pack 到底部（side=BOTTOM，不 expand）
        self._create_buttons(on_save, on_regenerate, on_cancel)

        # 2) 图片显示区域后 pack，fill+BOTH+expand 占据剩余全部空间
        self._create_image_view()

        # 显示弹窗
        self.dialog.deiconify()

        # 强制完成布局后渲染图片
        self.dialog.update()
        self._render_image(high_quality=True)

        # 绑定窗口大小变化事件（用于拖拽时自适应）
        self.dialog.bind('<Configure>', self._on_dialog_configure)

        self.dialog.lift()
        self.dialog.focus_force()

        if self.parent is None:
            self.dialog.mainloop()

        return self.dialog
    
    def _on_close(self, on_cancel: Callable[[], None]) -> None:
        """弹窗关闭处理"""
        # 从实例列表移除
        if self._instance_id is not None and self in PreviewDialog._instances:
            PreviewDialog._instances.remove(self)
        
        if on_cancel:
            on_cancel()
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None  # 清理引用
    
    @classmethod
    def show_all(cls, parent: Optional[tk.Tk] = None) -> None:
        """显示所有未显示的弹窗（用于批量显示）"""
        for instance in cls._instances:
            if instance.dialog and instance.dialog.winfo_exists():
                instance.dialog.lift()  # 提升窗口到最前
                instance.dialog.focus_force()
    
    @classmethod
    def close_all(cls) -> None:
        """关闭所有弹窗"""
        for instance in cls._instances[:]:
            if instance.dialog and instance.dialog.winfo_exists():
                instance.dialog.destroy()
        cls._instances.clear()
    
    def _create_image_view(self) -> None:
        """创建图片显示区域（Label 方式）"""
        self._img_frame = ttk.Frame(self.dialog)
        self._img_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._img_label = tk.Label(self._img_frame, bg='#f5f5f5')
        self._img_label.pack(fill=tk.BOTH, expand=True)

        # 加载原始图片
        try:
            from PIL import Image as PILImage
            self._original_img = PILImage.open(self.image_path)
            self._img_w, self._img_h = self._original_img.size
            self._photo = None
        except Exception as e:
            logger.error(f"加载图片失败: {e}")
            self._original_img = None
            self._img_label.config(text=f"无法加载图片\n{e}", fg='red', justify='center')

    def _render_image(self, high_quality: bool = True) -> None:
        """
        根据当前容器尺寸渲染图片
        
        Args:
            high_quality: True=LANCZOS高质量（静止时），False=BILINEAR快速（拖拽时）
        """
        if not hasattr(self, '_original_img') or self._original_img is None:
            return

        # 获取容器实际尺寸
        self._img_frame.update_idletasks()
        fw = self._img_frame.winfo_width()
        fh = self._img_frame.winfo_height()

        if fw < 10 or fh < 10:
            return

        # contain 模式：等比缩放，完整显示在容器内
        scale_w = fw / max(self._img_w, 1)
        scale_h = fh / max(self._img_h, 1)
        scale = min(scale_w, scale_h)

        new_w = int(max(self._img_w * scale, 1))
        new_h = int(max(self._img_h * scale, 1))

        # 尺寸缓存：避免相同尺寸重复渲染
        cache_key = (new_w, new_h, high_quality)
        if hasattr(self, '_render_cache') and self._render_cache == cache_key and self._photo is not None:
            return
        self._render_cache = cache_key

        from PIL import Image as PILImage, ImageTk
        # 拖拽时用 BILINEAR（快约3-5倍），停止后用 LANCZOS（高质量）
        resample = PILImage.Resampling.LANCZOS if high_quality else PILImage.Resampling.BILINEAR
        resized = self._original_img.resize((new_w, new_h), resample)

        self._photo = ImageTk.PhotoImage(resized)
        self._img_label.config(image=self._photo, text='', anchor='center')

    def _on_dialog_configure(self, event) -> None:
        """弹窗大小变化时重绘图片（拖拽时快速渲染，停止后高质量）"""
        if event.widget != self.dialog:
            # 忽略子组件的 Configure 事件（只响应窗口级）
            return
        if event.width < 50 or event.height < 50:
            return
        # 取消之前的定时器（防抖）
        if hasattr(self, '_resize_timer') and self._resize_timer:
            try:
                self.dialog.after_cancel(self._resize_timer)
            except Exception:
                pass
        # 立即用快速算法渲染（BILINEAR），拖拽体验流畅
        self._render_image(high_quality=False)
        # 200ms 无新事件后，用高质量算法（LANCZOS）重绘
        self._resize_timer = self.dialog.after(200, lambda: self._render_image(high_quality=True))
    
    def _create_buttons(
        self,
        on_save: Callable[[], None],
        on_regenerate: Callable[[], None],
        on_cancel: Callable[[], None],
    ) -> None:
        """创建按钮区域（固定到底部）"""
        frame = ttk.Frame(self.dialog)
        # side=BOTTOM：按钮固定在弹窗下方；fill=X：横向撑满
        frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(
            frame,
            text="保存",
            command=lambda: self._on_button_click(on_save),
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            frame,
            text="重新生成",
            command=lambda: self._on_button_click(on_regenerate),
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            frame,
            text="取消",
            command=lambda: self._on_button_click(on_cancel),
        ).pack(side=tk.RIGHT, padx=5)
    
    def _on_button_click(self, callback: Callable[[], None]) -> None:
        """按钮点击处理"""
        if callback:
            callback()
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None  # 清理引用


def show_message(title: str, message: str, msg_type: str = "info") -> None:
    """显示消息弹窗"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    if msg_type == "error":
        messagebox.showerror(title, message)
    elif msg_type == "warning":
        messagebox.showwarning(title, message)
    else:
        messagebox.showinfo(title, message)
    
    root.destroy()
