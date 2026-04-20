import unittest
import sys
import os
import time
import pandas as pd
import numpy as np

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.providers.akshare_data_provider import AkshareDataProvider
from src.core.visualizers.technical_chart import TechnicalChart
from src.backtest.engines.backtest import BacktestEngine
from src.backtest.strategies.annual_line import AnnualLineStrategy
from src.core.models import StrategyConfig, TradeRule

class TestCoreFunctions(unittest.TestCase):
    """测试核心功能的单元测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.provider = AkshareDataProvider()
        self.chart = TechnicalChart()
        
        # 获取测试数据
        self.fund_data = self.provider.get_etf_data(
            code='512890',
            start='2024-01-01',
            end='2024-12-31'
        )
        
        # 创建策略配置
        self.config = StrategyConfig(
            fund_code='512890',
            start_date='2024-01-01',
            end_date='2024-12-31',
            init_cash=100000,
            dividend_mode='reinvest',
            rules=[
                TradeRule(
                    rule_id='buy_below_ma',
                    trigger_type='bias_below',
                    threshold=0.0,
                    action='BUY',
                    position_ratio=1.0
                )
            ]
        )
    
    def test_technical_indicators(self):
        """测试技术指标计算"""
        df = self.fund_data.df
        
        # 测试MACD计算
        start_time = time.time()
        dif, dea, macd = self.chart._calculate_macd(df)
        macd_time = time.time() - start_time
        self.assertIsNotNone(dif)
        self.assertIsNotNone(dea)
        self.assertIsNotNone(macd)
        self.assertEqual(len(dif), len(df))
        print(f"MACD计算时间: {macd_time:.4f} 秒")
        
        # 测试RSI计算
        start_time = time.time()
        rsi = self.chart._calculate_rsi(df)
        rsi_time = time.time() - start_time
        self.assertIsNotNone(rsi)
        self.assertEqual(len(rsi), len(df))
        print(f"RSI计算时间: {rsi_time:.4f} 秒")
        
        # 测试KDJ计算
        start_time = time.time()
        k, d, j = self.chart._calculate_kdj(df)
        kdj_time = time.time() - start_time
        self.assertIsNotNone(k)
        self.assertIsNotNone(d)
        self.assertIsNotNone(j)
        self.assertEqual(len(k), len(df))
        print(f"KDJ计算时间: {kdj_time:.4f} 秒")
        
        # 测试回撤计算
        start_time = time.time()
        drawdown = self.chart._calculate_drawdown(df)
        drawdown_time = time.time() - start_time
        self.assertIsNotNone(drawdown)
        self.assertEqual(len(drawdown), len(df))
        print(f"回撤计算时间: {drawdown_time:.4f} 秒")
    
    def test_backtest_engine(self):
        """测试回测引擎"""
        strategy = AnnualLineStrategy()
        engine = BacktestEngine(strategy)
        
        start_time = time.time()
        result = engine.run(self.config, self.fund_data)
        backtest_time = time.time() - start_time
        
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.metrics)
        self.assertIsNotNone(result.equity_curve)
        print(f"回测执行时间: {backtest_time:.4f} 秒")
        print(f"总交易次数: {len(result.trades)}")
        print(f"累计收益率: {result.metrics.get('total_return', 0):.2f}%")
    
    def test_data_provider(self):
        """测试数据获取模块"""
        start_time = time.time()
        fund_data = self.provider.get_etf_data(
            code='512890',
            start='2024-01-01',
            end='2024-01-31'
        )
        data_time = time.time() - start_time
        
        self.assertIsNotNone(fund_data)
        self.assertIsNotNone(fund_data.df)
        self.assertIn('acc_nav', fund_data.df.columns)
        self.assertIn('bias', fund_data.df.columns)
        print(f"数据获取时间: {data_time:.4f} 秒")
        print(f"数据行数: {len(fund_data.df)}")
    
    def test_strategy_evaluation(self):
        """测试策略评估"""
        strategy = AnnualLineStrategy()
        df = self.fund_data.df
        
        # 测试策略评估
        for _, row in df.iterrows():
            triggered = strategy.evaluate(row)
            self.assertIsInstance(triggered, list)
            # 检查触发的规则是否有效
            for rule in triggered:
                self.assertIn(rule.action, ['BUY', 'SELL'])
        
        print("策略评估测试通过")

if __name__ == '__main__':
    unittest.main()
