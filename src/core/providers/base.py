"""
数据源抽象基类 (v4.0)

v4.0 变更：
- 新增 get_etf_history() 抽象方法（ETF 前复权数据）
- 保留 get_index_history() 抽象方法（指数数据）
- 删除 get_history()（旧接口，已不使用）
"""

from abc import ABC, abstractmethod
from ..models import FundData, IndexData


class BaseProvider(ABC):
    """
    数据提供商抽象基类

    当前实现：AkshareProvider（唯一数据源）
    扩展方向：Wind / Choice / Tushare
    """

    @abstractmethod
    def get_etf_history(self, code: str, start: str, end: str) -> FundData:
        """
        获取ETF前复权历史数据（核心数据源）

        Args:
            code: ETF代码（如 "512890"）
            start: 开始日期 (YYYY-MM-DD)
            end: 结束日期 (YYYY-MM-DD)

        Returns:
            FundData: 含 nav, acc_nav, ma_250, bias 的标准化数据

        Raises:
            DataFetchError: 数据获取或解析失败
        """
        pass

    @abstractmethod
    def get_index_history(self, code: str, start: str, end: str) -> IndexData:
        """
        获取指数历史数据（含 daily_return）

        Args:
            code: 指数代码（如 "000300" 表示沪深300）
            start: 开始日期 (YYYY-MM-DD)
            end: 结束日期 (YYYY-MM-DD)

        Returns:
            IndexData: 标准化指数行情数据

        Raises:
            DataFetchError: 数据获取或解析失败
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """获取数据源名称"""
        pass
