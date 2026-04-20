"""Akshare 数据提供者实现

基于 akshare 库实现的数据获取模块，支持股票、ETF、指数和基金数据
"""
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

import pandas as pd

from .base import DataProvider
from ..exceptions import DataFetchError
from ..models import FundData, IndexData, StockData

logger = logging.getLogger(__name__)


class AkshareDataProvider(DataProvider):
    """Akshare 数据提供者实现
    
    基于 akshare 库实现的数据获取，支持多种金融数据类型
    """
    
    # 指数代码映射
    INDEX_MAP = {
        "000300": {"symbol": "000300", "market": "sh", "name": "沪深300"},
        "000001": {"symbol": "000001", "market": "sh", "name": "上证指数"},
    }
    
    # ETF 代码映射
    ETF_MAP = {
        "512890": {"symbol": "sh512890", "name": "红利低波ETF"},
    }
    
    # 缓存配置
    CACHE_EXPIRY_DAYS = 7
    PERMANENT_CACHE_CODES = {'000300', '000001'}  # 指数永久缓存
    ETF_CACHE_CODES = {'512890'}  # ETF 7天过期
    
    def __init__(self, cache_dir: Optional[str] = None, cache_expiry_days: Optional[int] = None, verbose: bool = True):
        super().__init__(cache_dir, verbose)
        self._cache_expiry = timedelta(days=cache_expiry_days or self.CACHE_EXPIRY_DAYS)
        
        # 启动时清理过期缓存
        self._clean_expired_cache()
    
    def get_name(self) -> str:
        return "Akshare(东方财富)"
    
    def get_stock_data(self, code: str, start: str, end: str, **kwargs) -> Any:
        """获取股票数据
        
        使用 akshare 的 stock_zh_a_hist 接口获取股票历史数据
        
        Args:
            code: 股票代码
            start: 开始日期，格式 "YYYY-MM-DD"
            end: 结束日期，格式 "YYYY-MM-DD"
            **kwargs: 额外参数
            
        Returns:
            StockData 对象
        """
        if self._verbose:
            logger.info(f"获取股票 {code} 数据: {start} 至 {end}")
        
        # 检查缓存
        cache_path = self._cache_dir / f"stock_{code}_raw.pkl"
        cached_df = self._load_from_cache(cache_path, code=code)
        
        if cached_df is not None and self._check_date_range(cached_df, start, end):
            if self._verbose:
                logger.info(f"从缓存加载股票数据: {len(cached_df)} 条")
            return self._process_stock_data(cached_df, code, f"股票{code}", start, end)
        
        # 从 akshare 获取
        import akshare as ak
        
        df = None
        
        try:
            if self._verbose:
                logger.info(f"尝试 stock_zh_a_hist 获取 {code} 数据...")
            df = ak.stock_zh_a_hist(
                symbol=code,
                period='daily',
                start_date=start.replace('-', ''),
                end_date=end.replace('-', ''),
                adjust='qfq',  # 前复权
            )
            if df is not None and len(df) > 0:
                if self._verbose:
                    logger.info(f"stock_zh_a_hist 获取成功: {len(df)} 条")
        except Exception as e:
            if self._verbose:
                logger.error(f"获取股票数据失败: {e}")
            raise DataFetchError(f"无法获取股票 {code} 的数据")
        
        if df is None or len(df) == 0:
            raise DataFetchError(f"股票 {code} 数据为空")
        
        # 保存缓存
        self._save_to_cache(cache_path, df, code=code)
        
        return self._process_stock_data(df, code, f"股票{code}", start, end)
    
    def get_etf_data(self, code: str, start: str, end: str, **kwargs) -> Any:
        """获取ETF数据
        
        ETF属于基金类别，此方法为兼容旧接口，内部调用get_fund_data
        
        Returns:
            FundData 对象
        """
        return self.get_fund_data(code, start, end, **kwargs)
    
    def get_index_data(self, code: str, start: str, end: str, **kwargs) -> Any:
        """获取指数数据
        
        返回 IndexData 格式，包含 daily_return 指标
        """
        return self._get_index_history(code, start, end)
    
    def get_fund_data(self, code: str, start: str, end: str, **kwargs) -> Any:
        """获取公募基金数据
        
        使用 akshare 的 fund_em_open_fund_info 等接口获取基金数据
        
        Args:
            code: 基金代码
            start: 开始日期，格式 "YYYY-MM-DD"
            end: 结束日期，格式 "YYYY-MM-DD"
            **kwargs: 额外参数
            
        Returns:
            FundData 对象
        """
        if self._verbose:
            logger.info(f"获取基金 {code} 数据: {start} 至 {end}")
        
        # 检查是否为ETF
        if code in self.ETF_MAP or code.startswith('51') or code.startswith('15') or code.startswith('16'):
            return self._get_etf_history(code, start, end)
        
        # 从 akshare 获取公募基金数据
        import akshare as ak
        
        df = None
        
        try:
            if self._verbose:
                logger.info(f"尝试 fund_open_fund_info_em 获取 {code} 数据...")
            # 使用基金净值接口
            df = ak.fund_open_fund_info_em(
                symbol=code,
                indicator="累计净值走势"
            )
            if df is not None and len(df) > 0:
                if self._verbose:
                    logger.info(f"fund_open_fund_info_em 获取成功: {len(df)} 条")
        except Exception as e:
            if self._verbose:
                logger.error(f"获取基金数据失败: {e}")
            # 降级处理
            empty_df = pd.DataFrame(columns=['date', 'nav', 'acc_nav', 'ma_250', 'bias'])
            return FundData(code=code, name=f"基金{code}", df=empty_df, dividends=pd.DataFrame())
        
        if df is None or len(df) == 0:
            empty_df = pd.DataFrame(columns=['date', 'nav', 'acc_nav', 'ma_250', 'bias'])
            return FundData(code=code, name=f"基金{code}", df=empty_df, dividends=pd.DataFrame())
        
        # 处理基金数据
        return self._process_fund_data(df, code, f"基金{code}", start, end)
    
    def _process_fund_data(self, raw_df: pd.DataFrame, code: str, name: str, start: str, end: str) -> FundData:
        """处理原始基金数据，计算指标，返回 FundData"""
        df = raw_df.copy()
        
        # 标准化列名
        column_mappings = {
            '净值日期': 'date',
            '累计净值': 'acc_nav',
            '单位净值': 'nav'
        }
        for old, new in column_mappings.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        # 确保日期列存在
        if 'date' not in df.columns:
            df = df.rename(columns={df.columns[0]: 'date'})
        
        # 确保净值列存在
        if 'nav' not in df.columns and 'acc_nav' in df.columns:
            df['nav'] = df['acc_nav']
        elif 'nav' not in df.columns:
            df['nav'] = 0.0
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        
        # 计算250日均线和乖离率
        df['ma_250'] = df['nav'].rolling(window=250, min_periods=1).mean()
        df['bias'] = (df['nav'] - df['ma_250']) / df['ma_250'] * 100
        
        # 过滤日期范围
        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        # 重置索引
        df = df.sort_values('date').reset_index(drop=True)
        
        return FundData(code=code, name=name, df=df, dividends=pd.DataFrame())
    
    # --------------------------------------------------------------------------
    # ETF 数据获取实现（作为基金的子类别）
    # --------------------------------------------------------------------------
    
    def _get_etf_history(self, code: str, start: str, end: str) -> FundData:
        """获取ETF前复权历史数据
        
        ETF属于基金类别，使用 akshare 的 fund_etf_hist_em 接口获取前复权数据，
        若失败则降级到 stock_zh_index_daily（不复权数据）。
        """
        etf_info = self.ETF_MAP.get(code, {"symbol": f"sh{code}", "name": f"ETF{code}"})
        etf_name = etf_info["name"]
        
        if self._verbose:
            logger.info(f"获取ETF {code}({etf_name})数据: {start} 至 {end}")
        
        # 检查缓存
        cache_path = self._cache_dir / f"etf_{code}_raw.pkl"
        cached_df = self._load_from_cache(cache_path, code=code)
        
        if cached_df is not None:
            date_col = 'date' if 'date' in cached_df.columns else '日期'
            data_start = pd.to_datetime(cached_df[date_col].min())
            data_end = pd.to_datetime(cached_df[date_col].max())
            user_start = pd.to_datetime(start)
            user_end = pd.to_datetime(end)
            
            if data_start <= user_start and data_end >= user_end:
                if self._verbose:
                    logger.info(f"从缓存加载ETF数据: {len(cached_df)} 条")
                return self._process_etf_data(cached_df, code, etf_name, start, end)
        
        # 从 akshare 获取
        import akshare as ak
        
        df = None
        
        # 方法1: fund_etf_hist_em（东方财富源，支持前复权）
        try:
            if self._verbose:
                logger.info(f"尝试 fund_etf_hist_em 获取 {code} 前复权数据...")
            df = ak.fund_etf_hist_em(
                symbol=code,
                period='daily',
                start_date=start.replace('-', ''),
                end_date=end.replace('-', ''),
                adjust='qfq',
            )
            if df is not None and len(df) > 0:
                if self._verbose:
                    logger.info(f"fund_etf_hist_em 获取成功: {len(df)} 条")
        except Exception as e1:
            if self._verbose:
                logger.warning(f"fund_etf_hist_em 失败: {str(e1)[:80]}")
        
        # 方法2: stock_zh_index_daily（新浪源，不支持复权，但稳定可用）
        if df is None or len(df) == 0:
            try:
                if self._verbose:
                    logger.info(f"降级到 stock_zh_index_daily 获取 {code} 数据...")
                symbol = etf_info["symbol"]
                df = ak.stock_zh_index_daily(symbol=symbol)
                if df is not None and len(df) > 0:
                    if self._verbose:
                        logger.info(f"stock_zh_index_daily 获取成功: {len(df)} 条")
            except Exception as e2:
                if self._verbose:
                    logger.error(f"stock_zh_index_daily 也失败: {str(e2)[:80]}")
                raise DataFetchError(f"无法获取ETF {code} 的数据")
        
        if df is None or len(df) == 0:
            raise DataFetchError(f"ETF {code} 数据为空")
        
        # 保存缓存
        self._save_to_cache(cache_path, df, code=code)
        
        return self._process_etf_data(df, code, etf_name, start, end)
    
    def _process_etf_data(self, raw_df: pd.DataFrame, code: str, name: str, start: str, end: str) -> FundData:
        """处理ETF原始数据，计算 ma_250 和 bias，返回 FundData"""
        df = raw_df.copy()
        
        # 标准化列名
        column_mappings = {
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume',
        }
        for old, new in column_mappings.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        if 'date' not in df.columns:
            df = df.rename(columns={df.columns[0]: 'date'})
        if 'close' not in df.columns:
            for col in df.columns:
                if 'close' in col.lower() or '收盘' in col:
                    df = df.rename(columns={col: 'close'})
                    break
        
        # 数据类型转换
        df['date'] = pd.to_datetime(df['date'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['date', 'close'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # 计算 250 日均线和乖离率
        df['ma_250'] = df['close'].rolling(window=250, min_periods=1).mean()
        df['bias'] = ((df['close'] / df['ma_250']) - 1) * 100
        
        # 日期过滤
        df = df[
            (df['date'] >= pd.to_datetime(start)) &
            (df['date'] <= pd.to_datetime(end))
        ].reset_index(drop=True)
        
        if len(df) == 0:
            raise DataFetchError(f"ETF {code} 在 {start}~{end} 无有效数据")
        
        # FundData 字段映射
        df['nav'] = df['close']
        
        # 计算累计净值
        df['daily_return'] = df['close'].pct_change().fillna(0)
        df['cum_return'] = (1 + df['daily_return']).cumprod()
        initial_price = df['close'].iloc[0]
        df['acc_nav'] = initial_price * df['cum_return']
        
        if self._verbose:
            bias_stats = df['bias'].describe()
            logger.info(f"ETF {name} 处理完成: {len(df)} 条 ({df['date'].min().date()} ~ {df['date'].max().date()})" )
            logger.info(f"bias 统计: mean={bias_stats['mean']:.2f}%, std={bias_stats['std']:.2f}%")
        
        return FundData(
            code=code,
            name=name,
            df=df[['date', 'nav', 'acc_nav', 'ma_250', 'bias']],
            dividends=pd.DataFrame(),
        )
    
    # --------------------------------------------------------------------------
    # 指数数据获取实现
    # --------------------------------------------------------------------------
    
    def _get_index_history(self, code: str, start: str, end: str) -> IndexData:
        """获取指数前复权历史数据
        
        使用 akshare 的多个接口获取指数历史数据，按优先级顺序尝试：
        1. 东方财富 (index_zh_a_hist)
        2. 腾讯 (stock_zh_index_daily_tx)
        3. 新浪 (stock_zh_index_daily)
        """
        if code not in self.INDEX_MAP:
            if self._verbose:
                logger.warning(f"未映射的指数代码 {code}，尝试直接获取")
        
        index_info = self.INDEX_MAP.get(code, {"symbol": code, "market": "sh", "name": f"指数{code}"})
        index_name = index_info["name"]
        
        if self._verbose:
            logger.info(f"获取指数 {code}({index_name})数据: {start} 至 {end}")
        
        # 检查缓存
        cache_path = self._cache_dir / f"index_{code}_raw.pkl"
        cached_df = self._load_from_cache(cache_path, code=code)
        
        if cached_df is not None and self._check_date_range(cached_df, start, end):
            if self._verbose:
                logger.info(f"从缓存加载指数数据: {len(cached_df)} 条")
            return self._process_index_data(cached_df, code, index_name, start, end)
        
        # 数据源配置，按优先级排序
        data_sources = [
            {
                "name": "东方财富",
                "method": self._get_index_from_eastmoney,
                "params": {"code": code, "index_info": index_info, "start": start, "end": end}
            },
            {
                "name": "腾讯",
                "method": self._get_index_from_tencent,
                "params": {"code": code, "index_info": index_info, "start": start, "end": end}
            },
            {
                "name": "新浪",
                "method": self._get_index_from_sina,
                "params": {"code": code, "index_info": index_info, "start": start, "end": end}
            }
        ]
        
        # 数据源状态记录
        data_source_status = []
        
        # 尝试各数据源
        for source in data_sources:
            source_name = source["name"]
            start_time = time.time()
            success = False
            data = None
            error = None
            
            try:
                if self._verbose:
                    logger.info(f"尝试从 {source_name} 获取指数 {code} 数据...")
                
                # 调用数据源方法
                data = source["method"](**source["params"])
                
                # 验证数据
                if data is not None and not data.empty:
                    success = True
                    if self._verbose:
                        logger.info(f"从 {source_name} 获取成功: {len(data)} 条记录")
                    # 保存缓存
                    self._save_to_cache(cache_path, data, code=code)
                    # 处理数据并返回
                    result = self._process_index_data(data, code, index_name, start, end)
                    
                    # 记录最终使用的数据源状态
                    end_time = time.time()
                    response_time = end_time - start_time
                    data_integrity = len(data) > 0
                    
                    if self._verbose:
                        logger.info(f"数据源 {source_name} 性能: 响应时间 {response_time:.2f}s, 数据完整性 {data_integrity}")
                    
                    return result
                else:
                    error = "返回数据为空"
            except Exception as e:
                error = str(e)
                if self._verbose:
                    logger.warning(f"从 {source_name} 获取失败: {error}")
            finally:
                end_time = time.time()
                response_time = end_time - start_time
                data_integrity = len(data) > 0 if data is not None else False
                
                # 记录数据源状态
                data_source_status.append({
                    "name": source_name,
                    "success": success,
                    "response_time": response_time,
                    "data_integrity": data_integrity,
                    "error": error
                })
        
        # 所有数据源都失败
        if self._verbose:
            logger.error(f"所有数据源获取指数 {code} 数据失败")
            logger.info(f"数据源状态: {data_source_status}")
        
        # 尝试使用过期缓存
        if cache_path.exists():
            cached_df = self._load_from_cache(cache_path, code=code, ignore_expiry=True)
            if cached_df is not None:
                if self._verbose:
                    logger.info(f"使用过期缓存数据")
                return self._process_index_data(cached_df, code, index_name, start, end)
        
        # 返回空数据
        if self._verbose:
            logger.warning(f"无缓存可用，返回空数据")
        empty_df = pd.DataFrame(columns=['date', 'close', 'daily_return'])
        return IndexData(code=code, name=index_name, df=empty_df)
    
    def _get_index_from_eastmoney(self, code: str, index_info: dict, start: str, end: str) -> pd.DataFrame:
        """从东方财富获取指数数据
        
        使用 akshare 的 index_zh_a_hist 接口
        """
        import akshare as ak
        
        df = ak.index_zh_a_hist(
            symbol=index_info["symbol"],
            period="daily",
            start_date=start.replace("-", ""),
            end_date=end.replace("-", ""),
        )
        
        # 验证数据
        if df is None or df.empty:
            raise DataFetchError(f"东方财富数据源返回空数据")
        
        if not self._validate_akshare_index_data(df):
            raise DataFetchError(f"东方财富数据源返回的数据格式异常")
        
        return df
    
    def _get_index_from_tencent(self, code: str, index_info: dict, start: str, end: str) -> pd.DataFrame:
        """从腾讯获取指数数据
        
        使用 akshare 的 stock_zh_index_daily_tx 接口
        """
        import akshare as ak
        
        symbol = f"{index_info['market']}{index_info['symbol']}"
        df = ak.stock_zh_index_daily_tx(symbol=symbol)
        
        # 验证数据
        if df is None or df.empty:
            raise DataFetchError(f"腾讯数据源返回空数据")
        
        if not self._validate_akshare_index_data(df):
            raise DataFetchError(f"腾讯数据源返回的数据格式异常")
        
        return df
    
    def _get_index_from_sina(self, code: str, index_info: dict, start: str, end: str) -> pd.DataFrame:
        """从新浪获取指数数据
        
        使用 akshare 的 stock_zh_index_daily 接口
        """
        import akshare as ak
        
        symbol = f"{index_info['market']}{index_info['symbol']}"
        df = ak.stock_zh_index_daily(symbol=symbol)
        
        # 验证数据
        if df is None or df.empty:
            raise DataFetchError(f"新浪数据源返回空数据")
        
        if not self._validate_akshare_index_data(df):
            raise DataFetchError(f"新浪数据源返回的数据格式异常")
        
        return df
    
    def _process_index_data(self, raw_df: pd.DataFrame, code: str, name: str, start: str, end: str) -> IndexData:
        """处理原始指数数据，计算日收益率，返回 IndexData"""
        df = raw_df.copy()
        
        # 标准化列名
        column_mappings = {
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume',
        }
        for old, new in column_mappings.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        if 'date' not in df.columns:
            df = df.rename(columns={df.columns[0]: 'date'})
        if 'close' not in df.columns:
            for col in df.columns:
                if 'close' in col.lower() or '收盘' in col:
                    df = df.rename(columns={col: 'close'})
                    break
        
        # 数据类型转换
        df['date'] = pd.to_datetime(df['date'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['date', 'close'])
        
        # 日期过滤
        df = df[
            (df['date'] >= pd.to_datetime(start)) &
            (df['date'] <= pd.to_datetime(end))
        ].reset_index(drop=True)
        
        if len(df) == 0:
            raise DataFetchError(f"指数 {code} 在 {start}~{end} 范围内无数据")
        
        df = df.sort_values('date').reset_index(drop=True)
        df['daily_return'] = df['close'].pct_change().fillna(0.0)
        
        if self._verbose:
            logger.info(f"指数 {name} 处理完成: {len(df)} 条 ({df['date'].min().date()} ~ {df['date'].max().date()})")
        
        return IndexData(
            code=code,
            name=name,
            df=df[['date', 'close', 'daily_return']]
        )
    
    def _process_stock_data(self, raw_df: pd.DataFrame, code: str, name: str, start: str, end: str) -> StockData:
        """处理原始股票数据，标准化格式，返回 StockData"""
        df = raw_df.copy()
        
        # 标准化列名
        column_mappings = {
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume',
            '成交额': 'amount', '振幅': 'amplitude',
            '涨跌幅': 'change_pct', '涨跌额': 'change', '换手率': 'turnover',
        }
        for old, new in column_mappings.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        if 'date' not in df.columns:
            df = df.rename(columns={df.columns[0]: 'date'})
        
        # 确保必需列存在
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                # 尝试从其他列名映射
                for old_col in df.columns:
                    if col in old_col.lower():
                        df = df.rename(columns={old_col: col})
                        break
                else:
                    # 如果找不到对应列，设置默认值
                    if col == 'volume':
                        df[col] = 0
                    else:
                        df[col] = df['close'] if 'close' in df.columns else 0
        
        # 数据类型转换
        df['date'] = pd.to_datetime(df['date'])
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna(subset=['date', 'close'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # 日期过滤
        df = df[
            (df['date'] >= pd.to_datetime(start)) &
            (df['date'] <= pd.to_datetime(end))
        ].reset_index(drop=True)
        
        if len(df) == 0:
            raise DataFetchError(f"股票 {code} 在 {start}~{end} 无有效数据")
        
        if self._verbose:
            logger.info(f"股票 {name} 处理完成: {len(df)} 条 ({df['date'].min().date()} ~ {df['date'].max().date()})" )
        
        return StockData(
            code=code,
            name=name,
            df=df[['date', 'open', 'high', 'low', 'close', 'volume']]
        )
    
    # --------------------------------------------------------------------------
    # 缓存和工具方法
    # --------------------------------------------------------------------------
    
    def _is_permanent_cache(self, code: str) -> bool:
        """检查是否为永久缓存"""
        return code in self.PERMANENT_CACHE_CODES
    
    def _clean_expired_cache(self):
        """清理过期的缓存文件"""
        try:
            if not self._cache_dir.exists():
                return
            
            expired_count = 0
            total_count = 0
            
            for cache_file in self._cache_dir.iterdir():
                if cache_file.suffix == '.pkl' and cache_file.is_file():
                    total_count += 1
                    file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                    
                    # 检查是否为永久缓存
                    filename = cache_file.name
                    code = None
                    if filename.startswith('index_'):
                        code = filename.split('_')[1]
                    elif filename.startswith('etf_'):
                        code = filename.split('_')[1]
                    
                    if code and self._is_permanent_cache(code):
                        continue  # 跳过永久缓存
                    
                    if file_age > self._cache_expiry:
                        cache_file.unlink()
                        expired_count += 1
            
            if self._verbose and expired_count > 0:
                logger.info(f"清理了 {expired_count} 个过期缓存文件（共 {total_count} 个）")
        except Exception as e:
            if self._verbose:
                logger.warning(f"清理缓存时发生错误: {e}")
    
    def _validate_akshare_index_data(self, df: pd.DataFrame) -> bool:
        """验证 akshare 返回的指数数据格式"""
        if df is None or df.empty:
            if self._verbose:
                logger.warning("akshare 指数数据为空")
            return False
        
        # 检查核心必要列
        has_date = False
        has_close = False
        
        # 检查日期列
        date_columns = ['日期', 'date', 'Date']
        for col in date_columns:
            if col in df.columns:
                has_date = True
                break
        
        # 检查收盘价列
        close_columns = ['收盘', 'close', 'Close']
        for col in close_columns:
            if col in df.columns:
                has_close = True
                break
        
        if not has_date:
            if self._verbose:
                logger.warning("akshare 指数数据缺少日期列")
            return False
        
        if not has_close:
            if self._verbose:
                logger.warning("akshare 指数数据缺少收盘价列")
            return False
        
        # 检查数据类型
        try:
            # 尝试转换日期类型
            for col in date_columns:
                if col in df.columns:
                    pd.to_datetime(df[col])
                    break
            
            # 尝试转换收盘价为数值类型
            for col in close_columns:
                if col in df.columns:
                    pd.to_numeric(df[col])
                    break
            
        except Exception as e:
            if self._verbose:
                logger.warning(f"akshare 指数数据类型验证失败: {e}")
            return False
        
        if self._verbose:
            logger.info(f"akshare 指数数据格式验证通过，包含 {len(df)} 条记录")
        return True
    
    def _check_date_range(self, df: pd.DataFrame, start: str, end: str) -> bool:
        """检查缓存数据是否覆盖所需日期范围"""
        user_start = pd.to_datetime(start)
        user_end = pd.to_datetime(end)
        date_col = 'date' if 'date' in df.columns else ('日期' if '日期' in df.columns else df.columns[0])
        actual_start = pd.to_datetime(df[date_col].min())
        actual_end = pd.to_datetime(df[date_col].max())
        if self._verbose:
            logger.info(f"缓存日期范围: {actual_start.date()} ~ {actual_end.date()}")
            logger.info(f"请求日期范围: {user_start.date()} ~ {user_end.date()}")
        return actual_start <= user_start and actual_end >= user_end
    
    def _load_from_cache(self, cache_path: Path, code: Optional[str] = None, ignore_expiry: bool = False, **kwargs) -> Optional[pd.DataFrame]:
        """从本地缓存加载数据"""
        if not cache_path.exists():
            if self._verbose:
                logger.info(f"缓存文件不存在: {cache_path}")
            return None
        
        try:
            is_permanent = code is not None and self._is_permanent_cache(code)
            file_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
            
            if not ignore_expiry and not is_permanent and file_age > self._cache_expiry:
                if self._verbose:
                    logger.info(f"缓存已过期（{file_age.days}天），重新获取")
                return None
            
            # 加载缓存数据
            df = pd.read_pickle(cache_path)
            
            # 验证数据完整性
            if not self._validate_cache_data(df):
                if self._verbose:
                    logger.warning("缓存数据不完整，重新获取")
                return None
            
            return df
        except Exception as e:
            if self._verbose:
                logger.warning(f"加载缓存失败: {e}，重新获取")
            return None
    
    def _validate_cache_data(self, df: pd.DataFrame) -> bool:
        """验证缓存数据的完整性"""
        # 不同数据类型有不同的必需列
        # 股票和指数数据需要 'close' 列
        # ETF和基金数据需要 'nav' 列
        has_required_cols = False
        
        # 检查是否有股票/指数必需列
        if all(col in df.columns for col in ['date', 'close']):
            has_required_cols = True
        # 检查是否有基金/ETF必需列
        elif all(col in df.columns for col in ['date', 'nav']):
            has_required_cols = True
        
        return has_required_cols and not df.empty
    
    def _save_to_cache(self, cache_path: Path, data: pd.DataFrame, code: Optional[str] = None, **kwargs):
        """保存数据到本地缓存"""
        try:
            # 数据完整性检查
            if data is None or data.empty:
                if self._verbose:
                    logger.warning("尝试保存空数据到缓存，跳过")
                return
            
            # 检查日期列
            date_col = 'date' if 'date' in data.columns else ('日期' if '日期' in data.columns else None)
            if date_col is None:
                if self._verbose:
                    logger.warning("数据缺少日期列，跳过缓存")
                return
            
            data.to_pickle(cache_path)
            if self._verbose:
                logger.info(f"数据已缓存: {cache_path}（{len(data)}条）")
        except Exception as e:
            if self._verbose:
                logger.warning(f"缓存保存失败: {e}")