# -*- coding: utf-8 -*-
"""
服务器模块
Server modules
"""

# 使用安全导入
__all__ = []

# 尝试导入 HTTP 服务器
try:
    from .http_server import start_http_server, stop_http_server, get_server_info
    
    __all__.extend([
        'start_http_server',
        'stop_http_server', 
        'get_server_info'
    ])
    
except ImportError as e:
    print(f"Warning: Could not import http_server module: {e}")

# 尝试导入 WebSocket 服务器
try:
    from .websocket_server import start_websocket_server, stop_websocket_server, get_websocket_server_info
    
    __all__.extend([
        'start_websocket_server',
        'stop_websocket_server',
        'get_websocket_server_info'
    ])
    
except ImportError as e:
    print(f"Warning: Could not import websocket_server module: {e}")

# 如果没有任何模块可导入
if not __all__:
    print("Warning: No server modules could be imported")