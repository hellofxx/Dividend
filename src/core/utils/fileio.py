"""
路径管理、文件命名
"""

from datetime import datetime
from pathlib import Path
from typing import Optional


def ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_filename(
    prefix: str,
    fund_code: Optional[str] = None,
    suffix: Optional[str] = None,
    ext: str = "png",
) -> str:
    """
    生成时间戳文件名
    
    Args:
        prefix: 前缀
        fund_code: 基金代码
        suffix: 后缀
        ext: 扩展名
        
    Returns:
        str: 文件名
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    parts = [prefix]
    
    if fund_code:
        parts.append(fund_code)
    
    parts.append(timestamp)
    
    if suffix:
        parts.append(suffix)
    
    return "_".join(parts) + f".{ext}"
