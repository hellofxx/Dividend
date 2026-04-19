"""
年线乖离率策略测试
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest.strategies.annual_line import AnnualLineStrategy
from src.core.models import TradeRule


class TestAnnualLineStrategy(unittest.TestCase):
    """测试年线乖离率策略"""
    
    def setUp(self):
        """测试前准备"""
        # 创建策略实例
        self.strategy = AnnualLineStrategy()
        
        # 创建模拟数据
        dates = pd.date_range('2021-01-01', '2022-12-31', freq='B')  # 工作日
        np.random.seed(42)
        
        base_price = 1.0
        prices = [base_price]
        for _ in range(1, len(dates)):
            change = np.random.normal(0.0005, 0.01)  # 日均收益0.05%，波动1%
            prices.append(prices[-1] * (1 + change))
        
        self.fund_data = pd.DataFrame({
            'date': dates,
            'close': prices,
            'ma_250': prices,  # 简化，使用close作为ma_250
            'bias': np.random.normal(0, 5, len(dates))  # 模拟bias
        })
    
    def test_strategy_initialization(self):
        """测试策略初始化"""
        strategy = AnnualLineStrategy()
        self.assertEqual(strategy.state, 'IDLE')
    
    def test_evaluate_buy_signal(self):
        """测试买入信号"""
        # 模拟bias为负，应该产生买入信号
        self.fund_data['bias'] = -5.0
        trade_rules = self.strategy.evaluate(self.fund_data.iloc[-1])
        self.assertIsInstance(trade_rules, list)
        self.assertGreater(len(trade_rules), 0)
        self.assertIsInstance(trade_rules[0], TradeRule)
        self.assertEqual(trade_rules[0].action, 'BUY')
    
    def test_evaluate_sell_signal(self):
        """测试卖出信号"""
        # 模拟bias为正且大于阈值，应该产生卖出信号
        self.strategy.state = 'HELD'  # 设置为持有状态
        self.fund_data['bias'] = 15.0
        trade_rules = self.strategy.evaluate(self.fund_data.iloc[-1])
        self.assertIsInstance(trade_rules, list)
        self.assertGreater(len(trade_rules), 0)
        self.assertIsInstance(trade_rules[0], TradeRule)
        self.assertEqual(trade_rules[0].action, 'SELL')
    
    def test_evaluate_no_signal(self):
        """测试无信号"""
        # 模拟bias为正但小于阈值，应该无信号
        self.fund_data['bias'] = 5.0
        trade_rules = self.strategy.evaluate(self.fund_data.iloc[-1])
        self.assertIsInstance(trade_rules, list)
        self.assertEqual(len(trade_rules), 0)


if __name__ == '__main__':
    unittest.main()
