# -*- coding: utf-8 -*-
"""
核心功能模块
Core functionality modules
"""

# 使用安全导入，避免在包初始化时出错
__all__ = []

# 尝试导入 utils 模块
try:
    from .utils import (
        get_timestamp, 
        ensure_dirs_exist,
        get_config_dir,
        get_image_dir,
        get_result_dir,
        log_info, 
        log_success, 
        log_error, 
        log_warning
    )
    
    # 成功导入后添加到 __all__
    __all__.extend([
        'get_timestamp',
        'ensure_dirs_exist',
        'get_config_dir',
        'get_image_dir', 
        'get_result_dir',
        'log_info', 
        'log_success', 
        'log_error', 
        'log_warning'
    ])
    
except ImportError as e:
    # 如果导入失败，不影响包的初始化
    print(f"Warning: Could not import utils module: {e}")

# 尝试导入 config_manager 模块
try:
    from .config_manager import get_config_status
    
    # 成功导入后添加到 __all__
    __all__.append('get_config_status')
    
except ImportError as e:
    # 如果导入失败，不影响包的初始化
    print(f"Warning: Could not import config_manager module: {e}")

# 如果没有任何模块可导入，至少提供基本信息
if not __all__:
    print("Warning: No modules could be imported from core package")
    __version__ = "2.1.0"