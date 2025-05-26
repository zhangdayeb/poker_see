#!/usr/bin/env python3
import os
from pathlib import Path

# 项目根目录
project_root = Path(__file__).parent

# 需要创建 __init__.py 的目录
directories = [
    "src",
    "src/core", 
    "src/servers",
    "src/websocket",
    "src/processors",  # 如果存在
    "src/workflows",   # 如果存在
    "src/tests"        # 如果存在
]

# __init__.py 模板
init_template = '''# -*- coding: utf-8 -*-
"""
{description}
"""
'''

# 特殊的 __init__.py 内容
special_inits = {
    "src": '''# -*- coding: utf-8 -*-
"""
扑克识别系统
Poker Recognition System
"""

__version__ = "2.1.0"
''',
    
    "src/core": '''# -*- coding: utf-8 -*-
"""
核心功能模块
"""

from .utils import get_timestamp, log_info, log_success, log_error, log_warning
from .config_manager import get_config_status

__all__ = [
    'get_timestamp', 'log_info', 'log_success', 'log_error', 'log_warning',
    'get_config_status'
]
''',
    
    "src/servers": '''# -*- coding: utf-8 -*-
"""
服务器模块
"""

from .http_server import start_http_server, stop_http_server
from .websocket_server import start_websocket_server, stop_websocket_server

__all__ = [
    'start_http_server', 'stop_http_server',
    'start_websocket_server', 'stop_websocket_server'
]
''',
    
    "src/websocket": '''# -*- coding: utf-8 -*-
"""
WebSocket功能模块
"""

from .connection_manager import cleanup_all_connections, get_connection_stats

__all__ = [
    'cleanup_all_connections', 'get_connection_stats'
]
'''
}

def create_init_files():
    """创建所有需要的 __init__.py 文件"""
    print("🔧 开始创建 __init__.py 文件...")
    
    for dir_path in directories:
        full_path = project_root / dir_path
        
        # 检查目录是否存在
        if not full_path.exists():
            print(f"⚠️  目录不存在，跳过: {dir_path}")
            continue
            
        # 创建 __init__.py 文件
        init_file = full_path / "__init__.py"
        
        if init_file.exists():
            print(f"✅ 已存在: {init_file}")
            continue
        
        # 获取内容
        if dir_path in special_inits:
            content = special_inits[dir_path]
        else:
            content = init_template.format(description=f"{dir_path} 模块")
        
        # 写入文件
        try:
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已创建: {init_file}")
        except Exception as e:
            print(f"❌ 创建失败 {init_file}: {e}")
    
    print("🎉 __init__.py 文件创建完成！")

if __name__ == "__main__":
    create_init_files()