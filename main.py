"""
量化工作室 QuantStudio v1.2
===========================
整合红利低波回测系统 + ETF技术分析工具

核心功能：
1. 判断模式：实时ETF技术分析 + 多因子买入信号判定
2. 回测模式：量化回测分析 + 多策略基准对比

使用方法：
    python main.py                           # 默认进入交互式菜单
    python main.py --mode judgment           # 直接进入判断模式
    python main.py --mode backtest          # 直接进入回测模式
    python main.py --mode judgment --etf-code 512890
    python main.py --mode backtest --etf-code 512890 --start-date 2021-01-01
"""

import argparse
import logging
import os
import sys
import tkinter as tk
from pathlib import Path
from enum import Enum

# ── matplotlib 后端配置 ──────────────────────────────────────────────
_no_ui = '--no-ui' in sys.argv
import matplotlib
if not _no_ui:
    try:
        matplotlib.use('TkAgg')
    except Exception:
        matplotlib.use('Agg')
else:
    matplotlib.use('Agg')

import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# ── 统一导入路径 ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.utils import setup_logging
from src.core.exceptions import DataFetchError, DividendModeError, FrameworkError

logger = setup_logging()


class AppMode(Enum):
    """应用模式枚举"""
    MENU = "menu"           # 交互式菜单
    JUDGMENT = "judgment"  # 判断模式
    BACKTEST = "backtest"  # 回测模式


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='量化工作室 QuantStudio v1.2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python main.py                           # 默认进入交互式菜单
    python main.py --mode judgment           # 进入判断模式
    python main.py --mode backtest           # 进入回测模式
    python main.py --mode judgment --etf-code 510300
    python main.py --mode backtest --etf-code 512890 --start-date 2021-01-01
        """)

    parser.add_argument('--mode', type=str, default='menu',
                        choices=['menu', 'judgment', 'backtest'],
                        help='运行模式: menu=交互菜单, judgment=判断模式, backtest=回测模式')

    # ETF 相关
    parser.add_argument('--etf-code', type=str, default='512890',
                        help='ETF代码 (默认: 512890 红利低波ETF)')

    # 回测参数
    parser.add_argument('--start-date', type=str, default='2021-01-01',
                        help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2025-12-31',
                        help='回测结束日期 (YYYY-MM-DD)')

    # 策略参数
    parser.add_argument('--buy-threshold', type=float, default=0.0,
                        help='买入乖离率阈值 (默认: 0.0)')
    parser.add_argument('--sell-threshold', type=float, default=10.0,
                        help='卖出乖离率阈值 (默认: 10.0)')
    parser.add_argument('--dividend-mode', type=str, default='reinvest',
                        choices=['reinvest', 'cash'],
                        help='分红模式: reinvest=再投, cash=落袋')

    # 资金
    parser.add_argument('--initial-capital', type=float, default=100000.0,
                        help='初始资金 (默认: 100000 元)')

    # 可视化
    parser.add_argument('--theme', type=str, default='professional',
                        choices=['professional', 'modern', 'dark', 'pastel', 'vivid'],
                        help='可视化主题 (默认: professional)')

    # 交互
    parser.add_argument('--no-ui', action='store_true', help='禁用弹窗')
    parser.add_argument('--auto-save', action='store_true', help='自动保存')

    # 兼容旧参数
    parser.add_argument('--fund-code', type=str, default=None,
                        help='(兼容) 等同于 --etf-code')

    return parser.parse_args()


def print_banner():
    """打印启动横幅"""
    print("\n" + "=" * 70)
    print("              量化工作室 QuantStudio v1.2")
    print("=" * 70)
    print("  功能模式:")
    print("    [1] 判断模式 - ETF技术分析 + 多因子买入信号判定")
    print("    [2] 回测模式 - 量化回测 + 多策略基准对比")
    print("    [3] 退出")
    print("-" * 70)


def print_judgment_banner(args):
    """打印判断模式横幅"""
    print("\n" + "=" * 70)
    print("              判断模式 - ETF技术分析")
    print("=" * 70)
    print(f"  ETF代码   : {args.etf_code}")
    print(f"  数据源    : Akshare")
    print(f"  可视化主题: {args.theme.upper()}")
    print("-" * 70)


def print_backtest_banner(args):
    """打印回测模式横幅"""
    div_mode = "分红再投" if args.dividend_mode == 'reinvest' else "分红落袋"
    print("\n" + "=" * 70)
    print("              回测模式 - 量化回测分析")
    print("=" * 70)
    print(f"  ETF代码   : {args.etf_code}")
    print(f"  回测时间  : {args.start_date} 至 {args.end_date}")
    print(f"  买入阈值  : Bias <= {args.buy_threshold:.1f}%")
    print(f"  卖出阈值  : Bias >= {args.sell_threshold:.1f}%")
    print(f"  分红模式  : {div_mode}")
    print(f"  初始资金  : {args.initial_capital:,.0f} 元")
    print(f"  可视化主题: {args.theme.upper()}")
    print(f"  数据源    : Akshare")
    print("-" * 70)


def run_judgment_mode(args):
    """运行判断模式 - ETF技术分析"""
    import tkinter as tk
    from src.judgment.ui.main_window import MainWindow

    print_judgment_banner(args)

    root = tk.Tk()
    root.title(f'量化工作室 - 判断模式 - {args.etf_code}')
    root.geometry('1200x800')

    try:
        app = MainWindow(root, args.etf_code, args.theme)
        root.mainloop()
    except Exception as e:
        logger.error(f"判断模式异常: {e}", exc_info=True)
        print(f"[ERROR] 判断模式异常: {e}")
        return 1

    return 0


def run_backtest_mode(args):
    """运行回测模式 - 量化回测分析"""
    from src.core.models import StrategyConfig, TradeRule
    from src.core.providers.akshare_provider import AkshareProvider
    from src.backtest.strategies.annual_line import AnnualLineStrategy
    from src.backtest.engines.backtest import BacktestEngine
    from src.backtest.engines.benchmark import BenchmarkEngine
    from src.core.visualizers import MainChart, get_theme
    from src.core.visualizers.compare import CompareChart
    from src.core.visualizers.technical_chart import TechnicalChart
    from src.backtest.ui import ResultDialog, PreviewDialog, show_message
    from src.core.utils import generate_filename, ensure_dir

    print_backtest_banner(args)

    try:
        # 1. 数据获取
        print("\n" + "-" * 70)
        print("                         数据获取阶段")
        print("-" * 70)
        provider = AkshareProvider()
        print(f"[INFO] 数据源: {provider.get_name()}")

        fund_data = provider.get_etf_history(
            code=args.etf_code,
            start=args.start_date,
            end=args.end_date,
        )
        print(f"[OK]  获取完成: {fund_data.name} | {len(fund_data.df)} 条数据")

        # 2. 策略配置 & 回测
        print("\n" + "-" * 70)
        print("                         策略回测阶段")
        print("-" * 70)

        buy_rule = TradeRule(
            rule_id="buy_step_1",
            trigger_type="bias_below",
            threshold=args.buy_threshold,
            action="BUY",
            position_ratio=1.0,
        )
        sell_rule = TradeRule(
            rule_id="sell_step_1",
            trigger_type="bias_above",
            threshold=args.sell_threshold,
            action="SELL",
            position_ratio=1.0,
        )
        config = StrategyConfig(
            fund_code=args.etf_code,
            start_date=args.start_date,
            end_date=args.end_date,
            init_cash=args.initial_capital,
            dividend_mode=args.dividend_mode,
            rules=[buy_rule, sell_rule],
        )

        strategy = AnnualLineStrategy(
            name=f"年线策略(Bias<={args.buy_threshold}%)",
            buy_rules=[config.rules[0]],
            sell_rules=[config.rules[1]],
        )
        engine = BacktestEngine(strategy=strategy)
        result = engine.run(config=config, fund_data=fund_data)
        print(f"[OK]  回测完成: {len(result.trades)} 笔交易")

        # 3. 基准对比
        print("[INFO] 运行基准对比...")
        benchmark_engine = BenchmarkEngine()
        compare_result = benchmark_engine.run_all(
            config=config,
            main_result=result,
            fund_data=fund_data,
            provider=provider,
        )
        print("[OK]  基准对比完成")

        # 4. 打印结果
        print("\n" + "-" * 70)
        print("                         回测结果汇总")
        print("-" * 70)

        m = result.metrics
        print(f"  累计收益率: {m.get('total_return', 0):+.2f}%")
        print(f"  年化收益率: {m.get('annual_return', 0):+.2f}%")
        print(f"  最大回撤:   {m.get('max_drawdown', 0):.2f}%")
        print(f"  夏普比率:   {m.get('sharpe_ratio', 0):.2f}")
        print(f"  交易次数:   {len(result.trades)} 笔")

        # 5. 图表生成
        print("\n" + "-" * 70)
        print("                         图表生成阶段")
        print("-" * 70)
        output_dir = ensure_dir(Path("output"))

        main_chart = MainChart(theme=args.theme)
        fig = main_chart.create(
            df=fund_data.df,
            result=result,
            fund_code=args.etf_code,
            fund_name=fund_data.name,
        )
        main_filename = generate_filename(prefix=f"fund_{args.etf_code}", ext="png")
        main_path = output_dir / main_filename
        main_chart.save(fig, main_path)
        print(f"[OK]  主分析图: {main_path}")

        compare_chart = CompareChart(theme=args.theme)
        compare_fig = compare_chart.create(compare_result=compare_result)
        compare_filename = generate_filename(prefix=f"fund_{args.etf_code}_compare", ext="png")
        compare_path = output_dir / compare_filename
        compare_chart.save(compare_fig, compare_path)
        print(f"[OK]  策略对比图: {compare_path}")

        technical_chart = TechnicalChart(theme=args.theme)
        technical_fig = technical_chart.create(
            df=fund_data.df,
            result=result,
            fund_code=args.etf_code,
            fund_name=fund_data.name,
        )
        technical_filename = generate_filename(prefix=f"fund_{args.etf_code}_technical", ext="png")
        technical_path = output_dir / technical_filename
        technical_chart.save(technical_fig, technical_path)
        print(f"[OK]  技术分析图: {technical_path}")

        # 6. 弹窗展示
        if not args.no_ui:
            # 弹窗计数和关闭状态跟踪
            total_dialogs = 4  # 1个结果弹窗 + 3个图表弹窗
            closed_dialogs = 0
            save_operations = []

            def on_save_image(image_path):
                """保存单张图片"""
                print(f"[OK] 已保存: {image_path}")
                # 这里可以添加实际的保存逻辑
                save_operations.append(image_path)

            def on_cancel():
                """处理弹窗关闭"""
                nonlocal closed_dialogs
                closed_dialogs += 1
                print(f"[INFO] 弹窗关闭，剩余 {total_dialogs - closed_dialogs} 个弹窗")
                
                # 当所有弹窗都关闭后，退出应用程序
                if closed_dialogs >= total_dialogs:
                    print("[INFO] 所有弹窗已关闭，退出程序")
                    # 确保保存操作完成
                    if save_operations:
                        print(f"[INFO] 已完成 {len(save_operations)} 个保存操作")
                    root.quit()

            root = tk.Tk()
            root.withdraw()

            # 创建结果弹窗
            result_dialog = ResultDialog(parent=root)
            result_win = result_dialog.show(
                result=result,
                compare_result=compare_result,
                on_save=lambda: None,  # 不自动保存
                on_cancel=on_cancel,
                output_dir=output_dir,
                fund_code=args.etf_code,
                start_date=args.start_date,
                end_date=args.end_date,
                modal=False,
            )

            # 创建图表弹窗
            chart_paths = [
                (main_path, "主分析图表"),
                (compare_path, "策略对比图"),
                (technical_path, "技术分析图"),
            ]

            for path, title in chart_paths:
                if path.exists():
                    preview = PreviewDialog(parent=root)
                    preview.show(
                        image_path=path,
                        title=title,
                        on_save=lambda p=path: on_save_image(p),
                        on_regenerate=lambda: print("[INFO] 重新生成图表"),
                        on_cancel=on_cancel,
                        modal=False,
                    )

            print(f"[OK]  共创建 {total_dialogs} 个弹窗")
            try:
                root.mainloop()
            except KeyboardInterrupt:
                pass

        print("\n" + "=" * 70)
        print("                          分析完成！")
        print("=" * 70)
        return 0

    except DividendModeError as e:
        print(f"\n[ERROR] 分红模式配置错误：{e}")
        return 1
    except DataFetchError as e:
        print(f"\n[ERROR] 数据获取失败：{e}")
        return 1
    except FrameworkError as e:
        print(f"\n[ERROR] 策略执行异常：{e}")
        return 1
    except Exception as e:
        logger.error(f"未知异常: {e}", exc_info=True)
        print(f"\n[ERROR] 程序异常: {e}")
        return 1


def interactive_menu():
    """交互式菜单"""
    while True:
        print_banner()
        choice = input("请选择功能模式 [1/2/3]: ").strip()

        if choice == '1':
            args = parse_arguments()
            args.mode = 'judgment'
            return run_judgment_mode(args)
        elif choice == '2':
            args = parse_arguments()
            args.mode = 'backtest'
            return run_backtest_mode(args)
        elif choice == '3':
            print("\n感谢使用量化工作室！")
            return 0
        else:
            print("\n[ERROR] 无效选择，请重新输入")


def main():
    args = parse_arguments()

    if args.fund_code is not None:
        args.etf_code = args.fund_code

    if args.mode == 'menu':
        return interactive_menu()
    elif args.mode == 'judgment':
        return run_judgment_mode(args)
    elif args.mode == 'backtest':
        return run_backtest_mode(args)
    else:
        print(f"[ERROR] 未知模式: {args.mode}")
        return 1


if __name__ == "__main__":
    sys.exit(main())