# -*- coding: utf-8 -*-
"""
推送客户端模块
Push client modules
"""

# 使用安全导入
__all__ = []

# 尝试导入 WebSocket 推送客户端
try:
    from .websocket_client import (
        WebSocketPushClient,
        start_push_client,
        stop_push_client,
        get_push_client_status,
        push_recognition_result
    )
    
    __all__.extend([
        'WebSocketPushClient',
        'start_push_client',
        'stop_push_client',
        'get_push_client_status',
        'push_recognition_result'
    ])
    
except ImportError as e:
    print(f"Warning: Could not import websocket_client module: {e}")

# 尝试导入 HTTP 推送客户端
try:
    from .http_client import (
        HTTPPushClient,
        push_via_http
    )
    
    __all__.extend([
        'HTTPPushClient',
        'push_via_http'
    ])
    
except ImportError as e:
    print(f"Warning: Could not import http_client module: {e}")

# 如果没有任何模块可导入
if not __all__:
    print("Warning: No push client modules could be imported")
else:
    print(f"Push client module loaded successfully with {len(__all__)} functions")