"""
网络重试装饰器
"""

import functools
import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍数
        exceptions: 捕获的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        logger.error(f"{func.__name__} 最终失败: {e}")
                        raise
                    
                    logger.warning(
                        f"{func.__name__} 第{attempt + 1}次失败: {e}, "
                        f"{current_delay}s后重试..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return None
        
        return wrapper
    
    return decorator
