#!/usr/bin/env python3
"""
测试优化效果

验证以下功能：
1. 技术指标计算（MACD、RSI、KDJ）
2. 图表生成
3. 回测功能
4. 性能测试
"""

import sys
import time
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.providers.akshare_provider import AkshareProvider
from src.core.visualizers.technical_chart import TechnicalChart
from src.core.visualizers.interactive_chart import InteractiveChart
from src.core.visualizers.compare import CompareChart
from src.backtest.strategies.annual_line import AnnualLineStrategy
from src.backtest.engines.backtest import BacktestEngine
from src.backtest.engines.benchmark import BenchmarkEngine
from src.core.models import StrategyConfig, TradeRule

def test_technical_indicators():
    """测试技术指标计算"""
    print("\n=== 测试技术指标计算 ===")
    
    # 获取测试数据
    provider = AkshareProvider()
    fund_data = provider.get_etf_history(
        code='512890',
        start='2024-01-01',
        end='2024-12-31'
    )
    
    print(f"获取数据成功: {len(fund_data.df)} 条记录")
    
    # 测试技术指标计算
    chart = TechnicalChart()
    
    # 测试MACD
    start_time = time.time()
    dif, dea, macd = chart._calculate_macd(fund_data.df)
    macd_time = time.time() - start_time
    print(f"MACD计算时间: {macd_time:.4f} 秒")
    print(f"MACD数据长度: {len(macd)}")
    
    # 测试RSI
    start_time = time.time()
    rsi = chart._calculate_rsi(fund_data.df)
    rsi_time = time.time() - start_time
    print(f"RSI计算时间: {rsi_time:.4f} 秒")
    print(f"RSI数据长度: {len(rsi)}")
    
    # 测试KDJ
    start_time = time.time()
    k, d, j = chart._calculate_kdj(fund_data.df)
    kdj_time = time.time() - start_time
    print(f"KDJ计算时间: {kdj_time:.4f} 秒")
    print(f"KDJ数据长度: {len(k)}")
    
    return macd_time + rsi_time + kdj_time

def test_chart_generation():
    """测试图表生成"""
    print("\n=== 测试图表生成 ===")
    
    # 获取测试数据
    provider = AkshareProvider()
    fund_data = provider.get_etf_history(
        code='512890',
        start='2024-01-01',
        end='2024-12-31'
    )
    
    # 创建策略和回测
    buy_rule = TradeRule(
        rule_id="buy_step_1",
        trigger_type="bias_below",
        threshold=0.0,
        action="BUY",
        position_ratio=1.0,
    )
    sell_rule = TradeRule(
        rule_id="sell_step_1",
        trigger_type="bias_above",
        threshold=10.0,
        action="SELL",
        position_ratio=1.0,
    )
    config = StrategyConfig(
        fund_code='512890',
        start_date='2024-01-01',
        end_date='2024-12-31',
        init_cash=100000.0,
        dividend_mode='reinvest',
        rules=[buy_rule, sell_rule],
    )
    
    strategy = AnnualLineStrategy(
        name="年线策略",
        buy_rules=[config.rules[0]],
        sell_rules=[config.rules[1]],
    )
    engine = BacktestEngine(strategy=strategy)
    result = engine.run(config=config, fund_data=fund_data)
    
    # 测试技术分析图生成
    start_time = time.time()
    technical_chart = TechnicalChart()
    technical_fig = technical_chart.create(
        df=fund_data.df,
        result=result,
        fund_code='512890',
        fund_name='红利低波ETF'
    )
    technical_time = time.time() - start_time
    print(f"技术分析图生成时间: {technical_time:.4f} 秒")
    
    # 测试交互式图表生成
    start_time = time.time()
    interactive_chart = InteractiveChart()
    interactive_fig = interactive_chart.create(
        df=fund_data.df,
        result=result,
        fund_code='512890',
        fund_name='红利低波ETF'
    )
    interactive_time = time.time() - start_time
    print(f"交互式图表生成时间: {interactive_time:.4f} 秒")
    
    # 测试基准对比
    benchmark_engine = BenchmarkEngine()
    compare_result = benchmark_engine.run_all(
        config=config,
        main_result=result,
        fund_data=fund_data,
        provider=provider,
    )
    
    # 测试策略对比图生成
    start_time = time.time()
    compare_chart = CompareChart()
    compare_fig = compare_chart.create(compare_result=compare_result)
    compare_time = time.time() - start_time
    print(f"策略对比图生成时间: {compare_time:.4f} 秒")
    
    # 清理图表
    import matplotlib.pyplot as plt
    plt.close('all')
    
    return technical_time + interactive_time + compare_time

def test_backtest_performance():
    """测试回测性能"""
    print("\n=== 测试回测性能 ===")
    
    # 获取测试数据
    provider = AkshareProvider()
    fund_data = provider.get_etf_history(
        code='512890',
        start='2021-01-01',
        end='2024-12-31'
    )
    
    # 创建策略和回测
    buy_rule = TradeRule(
        rule_id="buy_step_1",
        trigger_type="bias_below",
        threshold=0.0,
        action="BUY",
        position_ratio=1.0,
    )
    sell_rule = TradeRule(
        rule_id="sell_step_1",
        trigger_type="bias_above",
        threshold=10.0,
        action="SELL",
        position_ratio=1.0,
    )
    config = StrategyConfig(
        fund_code='512890',
        start_date='2021-01-01',
        end_date='2024-12-31',
        init_cash=100000.0,
        dividend_mode='reinvest',
        rules=[buy_rule, sell_rule],
    )
    
    strategy = AnnualLineStrategy(
        name="年线策略",
        buy_rules=[config.rules[0]],
        sell_rules=[config.rules[1]],
    )
    engine = BacktestEngine(strategy=strategy)
    
    # 测试回测性能
    start_time = time.time()
    result = engine.run(config=config, fund_data=fund_data)
    backtest_time = time.time() - start_time
    
    print(f"回测时间: {backtest_time:.4f} 秒")
    print(f"交易次数: {len(result.trades)}")
    print(f"累计收益率: {result.metrics.get('total_return', 0):+.2f}%")
    print(f"年化收益率: {result.metrics.get('annual_return', 0):+.2f}%")
    print(f"最大回撤: {result.metrics.get('max_drawdown', 0):.2f}%")
    
    return backtest_time

def main():
    """主测试函数"""
    print("开始测试优化效果...")
    
    # 测试技术指标计算
    indicator_time = test_technical_indicators()
    
    # 测试图表生成
    chart_time = test_chart_generation()
    
    # 测试回测性能
    backtest_time = test_backtest_performance()
    
    print("\n=== 测试结果汇总 ===")
    print(f"技术指标计算总时间: {indicator_time:.4f} 秒")
    print(f"图表生成总时间: {chart_time:.4f} 秒")
    print(f"回测总时间: {backtest_time:.4f} 秒")
    print(f"总测试时间: {indicator_time + chart_time + backtest_time:.4f} 秒")
    
    print("\n测试完成！所有功能正常运行。")

if __name__ == "__main__":
    import sys
    main()
