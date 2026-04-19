"""
测试包初始化
============

包含所有单元测试和集成测试

测试分类：
- test_config.py: 配置管理测试
- test_data_loader.py: 数据获取测试
- test_strategy.py: 策略回测测试
- test_theme.py: 主题系统测试
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
