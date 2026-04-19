"""
统一日志配置
"""

import logging
import sys
from pathlib import Path


def setup_logging(
    level: int = logging.INFO,
    log_file: str = "fund_analysis.log",
) -> logging.Logger:
    """
    配置日志
    
    Args:
        level: 日志级别
        log_file: 日志文件名
        
    Returns:
        Logger实例
    """
    # 创建日志目录
    log_dir = Path("output")
    log_dir.mkdir(exist_ok=True)
    
    log_path = log_dir / log_file
    
    # 配置根日志
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    return logging.getLogger(__name__)
