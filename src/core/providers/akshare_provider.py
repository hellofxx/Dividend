"""
Akshare 数据接口实现（统一数据源 v4.0）

使用 akshare 获取所有数据：
- ETF 前复权数据（512890 红利低波ETF）
- 指数数据（沪深300、上证指数）

核心方法：
- get_etf_history(): 获取ETF前复权数据（含 ma_250、bias）
- get_index_history(): 获取指数数据（含 daily_return）

缓存机制：
- 本地 pickle 缓存
- 指数数据永久缓存，ETF数据7天过期
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from ..exceptions import DataFetchError
from ..models import FundData, IndexData

logger = logging.getLogger(__name__)


class AkshareProvider:
    """
    Akshare 数据提供商（唯一数据源）
    
    获取 ETF 前复权数据和指数数据
    """
    
    # 指数代码映射（仅保留实际使用的）
    INDEX_MAP = {
        "000300": {"symbol": "000300", "market": "sh", "name": "沪深300"},
        "000001": {"symbol": "000001", "market": "sh", "name": "上证指数"},
    }
    
    # ETF 代码映射
    ETF_MAP = {
        "512890": {"symbol": "sh512890", "name": "红利低波ETF"},
    }
    
    CACHE_EXPIRY_DAYS = 7
    PERMANENT_CACHE_CODES = {'000300', '000001', '512890'}
    
    def __init__(self, cache_dir: str = None, cache_expiry_days: int = None):
        if cache_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            self._cache_dir = project_root / "cache"
        else:
            self._cache_dir = Path(cache_dir)
        
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_expiry = timedelta(days=cache_expiry_days or self.CACHE_EXPIRY_DAYS)
    
    def _is_permanent_cache(self, code: str) -> bool:
        return code in self.PERMANENT_CACHE_CODES
    
    def get_name(self) -> str:
        return "Akshare(东方财富)"
    
    # ------------------------------------------------------------------
    # ETF 数据获取（核心数据源）
    # ------------------------------------------------------------------

    def get_etf_history(self, code: str, start: str, end: str) -> FundData:
        """
        获取ETF前复权历史数据（核心数据源）
        
        使用 akshare 的 fund_etf_hist_em 接口获取前复权数据，
        若失败则降级到 stock_zh_index_daily（不复权数据）。
        
        返回 FundData 格式（兼容现有回测引擎）：
        - nav = close（前复权收盘价）
        - acc_nav = close（ETF前复权价格即累计价格）
        - ma_250 = 250日均线
        - bias = 乖离率
        - dividends = 空（前复权数据已包含分红）
        """
        etf_info = self.ETF_MAP.get(code, {"symbol": f"sh{code}", "name": f"ETF{code}"})
        etf_name = etf_info["name"]
        
        logger.info(f"获取ETF {code}({etf_name})数据: {start} 至 {end}")
        
        # 检查缓存
        cache_path = self._cache_dir / f"etf_{code}_raw.pkl"
        cached_df = self._load_from_cache(cache_path, code)
        
        if cached_df is not None:
            date_col = 'date' if 'date' in cached_df.columns else '日期'
            data_start = pd.to_datetime(cached_df[date_col].min())
            data_end = pd.to_datetime(cached_df[date_col].max())
            user_start = pd.to_datetime(start)
            user_end = pd.to_datetime(end)
            
            if data_start <= user_start and data_end >= user_end:
                logger.info(f"从缓存加载ETF数据: {len(cached_df)} 条")
                return self._process_etf_data(cached_df, code, etf_name, start, end)
            elif data_start <= user_end and data_end >= user_start:
                logger.warning(f"缓存数据不完全覆盖: 数据范围 {data_start.strftime('%Y-%m-%d')} ~ {data_end.strftime('%Y-%m-%d')}")
                return self._process_etf_data(cached_df, code, etf_name, start, end)
        
        # 从 akshare 获取
        import akshare as ak
        
        df = None
        
        # 方法1: fund_etf_hist_em（支持前复权）
        try:
            logger.info(f"尝试 fund_etf_hist_em 获取 {code} 前复权数据...")
            df = ak.fund_etf_hist_em(
                symbol=code,
                period='daily',
                start_date=start.replace('-', ''),
                end_date=end.replace('-', ''),
                adjust='qfq',
            )
            if df is not None and len(df) > 0:
                logger.info(f"fund_etf_hist_em 获取成功: {len(df)} 条")
        except Exception as e1:
            logger.warning(f"fund_etf_hist_em 失败: {str(e1)[:80]}")
        
        # 方法2: stock_zh_index_daily（新浪源，不支持复权，但稳定可用）
        if df is None or len(df) == 0:
            try:
                logger.info(f"降级到 stock_zh_index_daily 获取 {code} 数据...")
                symbol = etf_info["symbol"]
                df = ak.stock_zh_index_daily(symbol=symbol)
                if df is not None and len(df) > 0:
                    logger.info(f"stock_zh_index_daily 获取成功: {len(df)} 条")
            except Exception as e2:
                logger.error(f"stock_zh_index_daily 也失败: {str(e2)[:80]}")
                raise DataFetchError(f"无法获取ETF {code} 的数据")
        
        if df is None or len(df) == 0:
            raise DataFetchError(f"ETF {code} 数据为空")
        
        # 保存缓存
        self._save_to_cache(cache_path, df)
        
        return self._process_etf_data(df, code, etf_name, start, end)

    def _process_etf_data(
        self,
        raw_df: pd.DataFrame,
        code: str,
        name: str,
        start: str,
        end: str,
    ) -> FundData:
        """处理ETF原始数据，计算 ma_250 和 bias，返回 FundData"""
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
        df['acc_nav'] = df['close']
        
        bias_stats = df['bias'].describe()
        logger.info(f"ETF {name} 处理完成: {len(df)} 条 ({df['date'].min().date()} ~ {df['date'].max().date()})")
        logger.info(f"bias 统计: mean={bias_stats['mean']:.2f}%, std={bias_stats['std']:.2f}%")
        
        return FundData(
            code=code,
            name=name,
            df=df[['date', 'nav', 'acc_nav', 'ma_250', 'bias']],
            dividends=pd.DataFrame(),
        )

    # ------------------------------------------------------------------
    # 指数数据获取
    # ------------------------------------------------------------------

    def get_index_history(self, code: str, start: str, end: str) -> IndexData:
        """
        获取指数前复权历史数据
        
        Args:
            code: 指数代码，如 "000300"（沪深300）、"000001"（上证指数）
            start: 开始日期，格式 "YYYY-MM-DD"
            end: 结束日期，格式 "YYYY-MM-DD"
            
        Returns:
            IndexData
        """
        if code not in self.INDEX_MAP:
            logger.warning(f"未映射的指数代码 {code}，尝试直接获取")
        
        index_info = self.INDEX_MAP.get(code, {"symbol": code, "market": "sh", "name": f"指数{code}"})
        index_name = index_info["name"]
        
        logger.info(f"获取指数 {code}({index_name})数据: {start} 至 {end}")
        
        # 检查缓存
        cache_path = self._cache_dir / f"index_{code}_raw.pkl"
        cached_df = self._load_from_cache(cache_path, code)
        
        if cached_df is not None and self._check_date_range(cached_df, start, end):
            logger.info(f"从缓存加载指数数据: {len(cached_df)} 条")
            return self._process_index_data(cached_df, code, index_name, start, end)
        
        # 从 akshare 获取
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                import akshare as ak
                
                logger.info(f"调用 akshare 获取指数 {code} 数据...")
                df = None
                
                try:
                    df = ak.index_zh_a_hist(
                        symbol=index_info["symbol"],
                        period="daily",
                        start_date=start.replace("-", ""),
                        end_date=end.replace("-", ""),
                    )
                    logger.info(f"主接口获取成功: {len(df)} 条")
                except Exception as e1:
                    logger.warning(f"主接口 index_zh_a_hist 失败: {e1}，尝试备用接口...")
                    symbol = f"{index_info['market']}{index_info['symbol']}"
                    df = ak.stock_zh_index_daily(symbol=symbol)
                    logger.info(f"备用接口获取成功: {len(df)} 条")
                
                if df is None or len(df) == 0:
                    raise DataFetchError(f"未找到指数 {code} 的历史数据")
                
                # 保存缓存
                self._save_to_cache(cache_path, df)
                
                return self._process_index_data(df, code, index_name, start, end)
                
            except ImportError:
                logger.error("akshare 未安装，请先执行: pip install akshare")
                raise DataFetchError("akshare 库未安装")
            except DataFetchError:
                raise
            except Exception as e:
                retry_count += 1
                logger.error(f"获取指数数据失败: {e} (尝试 {retry_count}/{max_retries})")
                if retry_count >= max_retries:
                    # 尝试使用过期缓存
                    if cache_path.exists():
                        cached_df = self._load_from_cache(cache_path, code, ignore_expiry=True)
                        if cached_df is not None:
                            return self._process_index_data(cached_df, code, index_name, start, end)
                    # 返回空数据，避免程序崩溃
                    logger.warning(f"无缓存可用，返回空数据")
                    empty_df = pd.DataFrame(columns=['date', 'close', 'daily_return'])
                    return IndexData(code=code, name=index_name, df=empty_df)
                import time
                time.sleep(2)

    def _process_index_data(
        self,
        raw_df: pd.DataFrame,
        code: str,
        name: str,
        start: str,
        end: str,
    ) -> IndexData:
        """处理原始指数数据，计算日收益率，返回 IndexData"""
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
        
        logger.info(f"指数 {name} 处理完成: {len(df)} 条 ({df['date'].min().date()} ~ {df['date'].max().date()})")
        
        return IndexData(
            code=code,
            name=name,
            df=df[['date', 'close', 'daily_return']]
        )

    # ------------------------------------------------------------------
    # 缓存机制
    # ------------------------------------------------------------------

    def _load_from_cache(self, cache_path: Path, code: str = None, ignore_expiry: bool = False) -> Optional[pd.DataFrame]:
        """从本地缓存加载数据"""
        if not cache_path.exists():
            return None
        
        is_permanent = code is not None and self._is_permanent_cache(code)
        file_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        
        if not ignore_expiry and not is_permanent and file_age > self._cache_expiry:
            logger.info(f"缓存已过期（{file_age.days}天），重新获取")
            return None
        
        try:
            import pickle
            with open(cache_path, 'rb') as f:
                cached_df = pickle.load(f)
            
            if not isinstance(cached_df, pd.DataFrame):
                logger.warning(f"缓存格式不正确，重新获取")
                return None
            
            logger.info(f"从缓存加载成功，缓存年龄: {file_age.days}天")
            return cached_df
        except Exception as e:
            logger.warning(f"缓存加载失败: {e}")
            return None
    
    def _save_to_cache(self, cache_path: Path, df: pd.DataFrame):
        """保存数据到本地缓存"""
        try:
            import pickle
            with open(cache_path, 'wb') as f:
                pickle.dump(df, f)
            logger.info(f"数据已缓存: {cache_path}（{len(df)}条）")
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")
    
    def _check_date_range(self, df: pd.DataFrame, start: str, end: str) -> bool:
        """检查缓存数据是否覆盖所需日期范围"""
        user_start = pd.to_datetime(start)
        user_end = pd.to_datetime(end)
        date_col = 'date' if 'date' in df.columns else ('日期' if '日期' in df.columns else df.columns[0])
        actual_start = pd.to_datetime(df[date_col].min())
        actual_end = pd.to_datetime(df[date_col].max())
        return user_start >= actual_start and user_end <= actual_end
