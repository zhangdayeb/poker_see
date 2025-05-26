# -*- coding: utf-8 -*-
"""
WebSocket功能模块
WebSocket functionality modules
"""

# 使用安全导入
__all__ = []

# 尝试导入连接管理器
try:
    from .connection_manager import cleanup_all_connections, get_connection_stats
    
    __all__.extend([
        'cleanup_all_connections',
        'get_connection_stats'
    ])
    
except ImportError as e:
    print(f"Warning: Could not import connection_manager module: {e}")

# 尝试导入荷官WebSocket处理器
try:
    from .dealer_websocket import (
        handle_new_connection,
        handle_message,
        handle_connection_closed,
        push_recognition_update,
        get_online_dealers
    )
    
    __all__.extend([
        'handle_new_connection',
        'handle_message', 
        'handle_connection_closed',
        'push_recognition_update',
        'get_online_dealers'
    ])
    
except ImportError as e:
    print(f"Warning: Could not import dealer_websocket module: {e}")

# 如果没有任何模块可导入
if not __all__:
    print("Warning: No websocket modules could be imported")
else:
    print(f"WebSocket module loaded successfully with {len(__all__)} functions")