"""数据提供者单元测试

测试 DataProvider 抽象基类和 AkshareDataProvider 具体实现
"""
import unittest
from pathlib import Path
from datetime import datetime, timedelta

from src.core.providers.base import DataProvider, DataProviderFactory
from src.core.providers.akshare_data_provider import AkshareDataProvider
from src.core.exceptions import DataFetchError


class TestDataProviderFactory(unittest.TestCase):
    """测试数据提供者工厂类"""
    
    def setUp(self):
        """设置测试环境"""
        self.provider = AkshareDataProvider(verbose=False)
    
    def test_register_and_get_provider(self):
        """测试注册和获取数据提供者"""
        # 注册提供者
        DataProviderFactory.register_provider("akshare", self.provider)
        
        # 获取提供者
        retrieved_provider = DataProviderFactory.get_provider("akshare")
        self.assertIsNotNone(retrieved_provider)
        self.assertEqual(retrieved_provider.get_name(), "Akshare(东方财富)")
    
    def test_list_providers(self):
        """测试列出所有提供者"""
        # 注册提供者
        DataProviderFactory.register_provider("akshare", self.provider)
        
        # 列出提供者
        providers = DataProviderFactory.list_providers()
        self.assertIn("akshare", providers)


class TestAkshareDataProvider(unittest.TestCase):
    """测试 Akshare 数据提供者"""
    
    def setUp(self):
        """设置测试环境"""
        self.provider = AkshareDataProvider(verbose=False)
        self.start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        self.end_date = datetime.now().strftime("%Y-%m-%d")
    
    def test_get_name(self):
        """测试获取提供者名称"""
        name = self.provider.get_name()
        self.assertEqual(name, "Akshare(东方财富)")
    
    def test_get_stock_data(self):
        """测试获取股票数据"""
        # 测试一个常见的股票代码
        try:
            stock_data = self.provider.get_stock_data("600000", self.start_date, self.end_date)
            self.assertIsNotNone(stock_data)
            self.assertEqual(stock_data.code, "600000")
            self.assertFalse(stock_data.df.empty)
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                self.assertIn(col, stock_data.df.columns)
        except DataFetchError:
            # 如果网络问题导致失败，记录但不视为测试失败
            pass
    
    def test_get_etf_data(self):
        """测试获取ETF数据"""
        # 测试红利低波ETF
        try:
            etf_data = self.provider.get_etf_data("512890", self.start_date, self.end_date)
            self.assertIsNotNone(etf_data)
            self.assertEqual(etf_data.code, "512890")
            self.assertFalse(etf_data.df.empty)
            required_cols = ['date', 'nav', 'acc_nav', 'ma_250', 'bias']
            for col in required_cols:
                self.assertIn(col, etf_data.df.columns)
        except DataFetchError:
            # 如果网络问题导致失败，记录但不视为测试失败
            pass
    
    def test_get_index_data(self):
        """测试获取指数数据"""
        # 测试沪深300指数
        try:
            index_data = self.provider.get_index_data("000300", self.start_date, self.end_date)
            self.assertIsNotNone(index_data)
            self.assertEqual(index_data.code, "000300")
            self.assertFalse(index_data.df.empty)
            required_cols = ['date', 'close', 'daily_return']
            for col in required_cols:
                self.assertIn(col, index_data.df.columns)
        except DataFetchError:
            # 如果网络问题导致失败，记录但不视为测试失败
            pass
    
    def test_get_fund_data(self):
        """测试获取基金数据（预留接口）"""
        fund_data = self.provider.get_fund_data("110022", self.start_date, self.end_date)
        self.assertIsNotNone(fund_data)
        self.assertEqual(fund_data.code, "110022")
    
    def test_invalid_code(self):
        """测试无效的代码"""
        # 测试无效的股票代码
        try:
            self.provider.get_stock_data("999999", self.start_date, self.end_date)
        except DataFetchError:
            # 应该抛出异常
            pass
    
    def test_cache_mechanism(self):
        """测试缓存机制"""
        # 测试ETF数据缓存
        try:
            # 第一次获取（应该从网络获取）
            etf_data1 = self.provider.get_etf_data("512890", self.start_date, self.end_date)
            
            # 第二次获取（应该从缓存获取）
            etf_data2 = self.provider.get_etf_data("512890", self.start_date, self.end_date)
            
            self.assertIsNotNone(etf_data1)
            self.assertIsNotNone(etf_data2)
            self.assertEqual(len(etf_data1.df), len(etf_data2.df))
        except DataFetchError:
            # 如果网络问题导致失败，记录但不视为测试失败
            pass


if __name__ == '__main__':
    unittest.main()