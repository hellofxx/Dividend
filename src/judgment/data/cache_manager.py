"""缓存管理器模块

负责ETF数据的本地缓存管理。
"""

import logging
import pickle
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = 'cache'):
        """初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[Any]: 缓存数据，如果不存在返回None
        """
        cache_file = self.cache_dir / f'{key}.pkl'
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            logger.debug(f'从缓存读取: {key}')
            return data
        except Exception as e:
            logger.warning(f'缓存读取失败: {e}')
            return None
    
    def set(self, key: str, data: Any) -> bool:
        """设置缓存数据
        
        Args:
            key: 缓存键
            data: 缓存数据
            
        Returns:
            bool: 缓存是否成功
        """
        cache_file = self.cache_dir / f'{key}.pkl'
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            logger.debug(f'缓存写入: {key}')
            return True
        except Exception as e:
            logger.warning(f'缓存写入失败: {e}')
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 删除是否成功
        """
        cache_file = self.cache_dir / f'{key}.pkl'
        
        if not cache_file.exists():
            return True
        
        try:
            cache_file.unlink()
            logger.debug(f'缓存删除: {key}')
            return True
        except Exception as e:
            logger.warning(f'缓存删除失败: {e}')
            return False
    
    def clear(self) -> bool:
        """清空所有缓存
        
        Returns:
            bool: 清空是否成功
        """
        try:
            for cache_file in self.cache_dir.glob('*.pkl'):
                cache_file.unlink()
            logger.info('缓存已清空')
            return True
        except Exception as e:
            logger.warning(f'缓存清空失败: {e}')
            return False