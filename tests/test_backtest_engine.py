"""
回测引擎测试
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest.engines.backtest import BacktestEngine
from src.backtest.strategies.annual_line import AnnualLineStrategy
from src.core.models import StrategyConfig, TradeRule
from src.core.models import FundData


class TestBacktestEngine(unittest.TestCase):
    """测试回测引擎"""
    
    def setUp(self):
        """测试前准备"""
        # 创建策略实例
        self.strategy = AnnualLineStrategy()
        self.engine = BacktestEngine(strategy=self.strategy)
        
        # 创建模拟数据
        dates = pd.date_range('2021-01-01', '2022-12-31', freq='B')  # 工作日
        np.random.seed(42)
        
        base_price = 1.0
        prices = [base_price]
        for _ in range(1, len(dates)):
            change = np.random.normal(0.0005, 0.01)  # 日均收益0.05%，波动1%
            prices.append(prices[-1] * (1 + change))
        
        # 计算累计收益
        cum_returns = np.cumprod([1 + np.random.normal(0.0005, 0.01) for _ in range(len(dates))])
        acc_prices = base_price * cum_returns
        
        # 计算MA250和BIAS
        ma_250 = pd.Series(prices).rolling(window=250, min_periods=1).mean().tolist()
        bias = [(p / m - 1) * 100 for p, m in zip(prices, ma_250)]
        
        self.fund_data = FundData(
            code='512890',
            name='红利低波ETF',
            df=pd.DataFrame({
                'date': dates,
                'nav': prices,
                'acc_nav': acc_prices,
                'ma_250': ma_250,
                'bias': bias
            }),
            dividends=pd.DataFrame()
        )
        
        # 创建策略配置
        self.config = StrategyConfig(
            fund_code='512890',
            start_date='2021-01-01',
            end_date='2022-12-31',
            init_cash=100000.0,
            dividend_mode='reinvest',
            rules=[
                TradeRule(
                    rule_id='buy',
                    trigger_type='bias_below',
                    threshold=0.0,
                    action='BUY',
                    position_ratio=1.0
                ),
                TradeRule(
                    rule_id='sell',
                    trigger_type='bias_above',
                    threshold=10.0,
                    action='SELL',
                    position_ratio=1.0
                )
            ]
        )
    
    def test_basic_backtest(self):
        """测试基本回测功能"""
        result = self.engine.run(config=self.config, fund_data=self.fund_data)
        
        # 检查结果类型
        from src.core.models import BacktestResult
        self.assertIsInstance(result, BacktestResult)
        self.assertIsInstance(result.trades, list)
        self.assertIsInstance(result.equity_curve, pd.DataFrame)
        self.assertIsInstance(result.metrics, dict)
        
        # 检查资金曲线
        self.assertIn('date', result.equity_curve.columns)
        self.assertIn('total_value', result.equity_curve.columns)
        self.assertGreater(len(result.equity_curve), 0)
    
    def test_dividend_reinvest(self):
        """测试分红再投模式"""
        # 创建包含分红的基金数据
        div_dates = pd.date_range('2021-06-30', '2022-06-30', freq='6ME')
        dividends = pd.DataFrame({
            'ex_date': div_dates,
            'amount': [0.01] * len(div_dates)
        })
        
        fund_data_with_div = FundData(
            code='512890',
            name='红利低波ETF',
            df=self.fund_data.df.copy(),
            dividends=dividends
        )
        
        # 测试分红再投
        config_reinvest = StrategyConfig(
            fund_code=self.config.fund_code,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            init_cash=self.config.init_cash,
            dividend_mode='reinvest',
            rules=self.config.rules
        )
        
        result_reinvest = self.engine.run(config=config_reinvest, fund_data=fund_data_with_div)
        
        # 检查结果
        from src.core.models import BacktestResult
        self.assertIsInstance(result_reinvest, BacktestResult)
        self.assertIsInstance(result_reinvest.trades, list)
    
    def test_dividend_cash(self):
        """测试分红落袋模式"""
        # 创建包含分红的基金数据
        div_dates = pd.date_range('2021-06-30', '2022-06-30', freq='6ME')
        dividends = pd.DataFrame({
            'ex_date': div_dates,
            'amount': [0.01] * len(div_dates)
        })
        
        fund_data_with_div = FundData(
            code='512890',
            name='红利低波ETF',
            df=self.fund_data.df.copy(),
            dividends=dividends
        )
        
        # 测试分红落袋
        config_cash = StrategyConfig(
            fund_code=self.config.fund_code,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            init_cash=self.config.init_cash,
            dividend_mode='cash',
            rules=self.config.rules
        )
        
        result_cash = self.engine.run(config=config_cash, fund_data=fund_data_with_div)
        
        # 检查结果
        from src.core.models import BacktestResult
        self.assertIsInstance(result_cash, BacktestResult)
        self.assertIsInstance(result_cash.trades, list)
    
    def test_min_shares_constraint(self):
        """测试最小交易单位约束"""
        # 创建一个现金很少的配置
        small_cash_config = StrategyConfig(
            fund_code=self.config.fund_code,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            init_cash=0.001,  # 几乎没有现金
            dividend_mode=self.config.dividend_mode,
            rules=self.config.rules
        )
        
        result = self.engine.run(config=small_cash_config, fund_data=self.fund_data)
        
        # 应该没有交易
        self.assertEqual(len(result.trades), 0)
    
    def test_empty_data(self):
        """测试空数据情况"""
        # 创建空的基金数据
        empty_fund_data = FundData(
            code='512890',
            name='红利低波ETF',
            df=pd.DataFrame(columns=['date', 'nav', 'acc_nav', 'ma_250', 'bias']),
            dividends=pd.DataFrame()
        )
        
        # 应该抛出异常
        from src.core.exceptions import StrategyError
        with self.assertRaises(StrategyError):
            self.engine.run(config=self.config, fund_data=empty_fund_data)
    
    def test_end_of_period_settlement(self):
        """测试期末结算"""
        result = self.engine.run(config=self.config, fund_data=self.fund_data)
        
        # 检查期末结算
        if len(result.equity_curve) > 0:
            last_row = result.equity_curve.iloc[-1]
            self.assertIn('total_value', last_row)
            self.assertGreater(last_row['total_value'], 0)


if __name__ == '__main__':
    unittest.main()
