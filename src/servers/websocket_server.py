#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket服务器核心模块 - 基于websockets库的WebSocket服务器
功能:
1. WebSocket服务器启动和管理
2. 连接处理和消息路由
3. 与荷官通信模块集成
4. 错误处理和日志记录
5. 服务器状态监控
"""


import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
def setup_project_paths():
    """设置项目路径，确保可以正确导入模块"""
    current_file = Path(__file__).resolve()
    
    # 找到项目根目录（包含 main.py 的目录）
    project_root = current_file
    while project_root.parent != project_root:
        if (project_root / "main.py").exists():
            break
        project_root = project_root.parent
    
    # 将项目根目录添加到 Python 路径
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

# 调用路径设置
PROJECT_ROOT = setup_project_paths()


import asyncio
import json
import threading
import time
from typing import Dict, Any, Optional, Set
import logging

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = None

from src.core.utils import (
    get_timestamp, format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning
)
# 在 websocket_server.py 文件中，找到类似这样的导入语句：
# from dealer_websocket import xxx

# 将其修改为使用正确的路径和安全导入：

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径（如果还没有的话）
def setup_project_paths():
    """设置项目路径，确保可以正确导入模块"""
    current_file = Path(__file__).resolve()
    
    # 找到项目根目录（包含 main.py 的目录）
    project_root = current_file
    while project_root.parent != project_root:
        if (project_root / "main.py").exists():
            break
        project_root = project_root.parent
    
    # 将项目根目录添加到 Python 路径
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

# 调用路径设置
PROJECT_ROOT = setup_project_paths()

# 安全导入 dealer_websocket 模块
try:
    from src.websocket.dealer_websocket import (
        handle_new_connection,
        handle_message,
        handle_connection_closed,
        push_recognition_update,
        get_online_dealers
    )
    dealer_websocket_available = True
    print("[WEBSOCKET] dealer_websocket module imported successfully")
except ImportError as e:
    print(f"[WEBSOCKET] Warning: Could not import dealer_websocket module: {e}")
    dealer_websocket_available = False
    
    # 创建临时替代函数
    def handle_new_connection(websocket, remote_address):
        return {
            'status': 'error',
            'message': 'dealer_websocket module not available'
        }
    
    def handle_message(websocket, connection_id, message_text):
        return {
            'status': 'error',
            'message': 'dealer_websocket module not available'
        }
    
    def handle_connection_closed(connection_id, reason="客户端断开"):
        return {
            'status': 'error',
            'message': 'dealer_websocket module not available'
        }
    
    def push_recognition_update(dealer_id=None):
        return {
            'status': 'error',
            'message': 'dealer_websocket module not available'
        }
    
    def get_online_dealers():
        return {
            'status': 'error',
            'message': 'dealer_websocket module not available',
            'data': {'dealers': [], 'total_count': 0}
        }
from src.websocket.connection_manager import cleanup_all_connections, get_connection_stats

class WebSocketServer:
    """WebSocket服务器"""
    
    def __init__(self, host: str = 'localhost', port: int = 8001):
        """初始化WebSocket服务器"""
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
        self.loop = None
        
        # 连接跟踪
        self.active_websockets: Set[WebSocketServerProtocol] = set()
        self.connection_mapping: Dict[WebSocketServerProtocol, str] = {}
        
        # 检查websockets库是否可用
        if not WEBSOCKETS_AVAILABLE:
            log_error("websockets库未安装，WebSocket服务器无法启动", "WEBSOCKET")
        
        log_info("WebSocket服务器初始化完成", "WEBSOCKET")
    
    def start_server(self) -> Dict[str, Any]:
        """启动WebSocket服务器"""
        try:
            if not WEBSOCKETS_AVAILABLE:
                return format_error_response(
                    "websockets库未安装，请运行: pip install websockets", 
                    "WEBSOCKETS_NOT_AVAILABLE"
                )
            
            if self.running:
                return format_error_response("服务器已在运行", "SERVER_ALREADY_RUNNING")
            
            # 在新线程中启动服务器
            self.server_thread = threading.Thread(target=self._run_server_thread, daemon=True)
            self.running = True
            self.server_thread.start()
            
            # 等待服务器启动
            max_wait = 5  # 最大等待5秒
            wait_time = 0.1
            total_waited = 0
            
            while total_waited < max_wait:
                if self.server is not None:
                    break
                time.sleep(wait_time)
                total_waited += wait_time
            
            if self.server:
                log_success(f"WebSocket服务器启动成功: ws://{self.host}:{self.port}", "WEBSOCKET")
                return format_success_response(
                    "WebSocket服务器启动成功",
                    data={
                        'host': self.host,
                        'port': self.port,
                        'url': f"ws://{self.host}:{self.port}"
                    }
                )
            else:
                self.running = False
                return format_error_response("服务器启动超时", "SERVER_START_TIMEOUT")
                
        except Exception as e:
            self.running = False
            log_error(f"WebSocket服务器启动失败: {e}", "WEBSOCKET")
            return format_error_response(f"服务器启动失败: {str(e)}", "SERVER_START_ERROR")
    
    def _run_server_thread(self):
        """在新线程中运行服务器"""
        try:
            # 创建新的事件循环
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # 启动WebSocket服务器
            self.loop.run_until_complete(self._start_websocket_server())
            
        except Exception as e:
            log_error(f"WebSocket服务器线程异常: {e}", "WEBSOCKET")
            self.running = False
    
    async def _start_websocket_server(self):
        """启动WebSocket服务器（异步）"""
        try:
            # 创建WebSocket服务器
            self.server = await websockets.serve(
                self._handle_websocket_connection,
                self.host,
                self.port,
                ping_interval=30,  # 30秒ping间隔
                ping_timeout=10,   # 10秒ping超时
                max_size=1024*1024,  # 1MB最大消息大小
                compression=None   # 禁用压缩以提高性能
            )
            
            log_info(f"WebSocket服务器监听: {self.host}:{self.port}", "WEBSOCKET")
            
            # 运行服务器直到停止
            await self.server.wait_closed()
            
        except Exception as e:
            log_error(f"WebSocket服务器运行异常: {e}", "WEBSOCKET")
            self.running = False
    
    async def _handle_websocket_connection(self, websocket, path):
        """处理WebSocket连接"""
        connection_id = None
        remote_address = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        try:
            # 添加到活跃连接集合
            self.active_websockets.add(websocket)
            
            # 处理新连接
            connection_result = handle_new_connection(websocket, remote_address)
            
            if connection_result['status'] == 'success':
                connection_id = connection_result['data']['connection_id']
                self.connection_mapping[websocket] = connection_id
                
                log_success(f"WebSocket连接建立: {connection_id} from {remote_address}", "WEBSOCKET")
                
                # 处理消息循环
                await self._message_loop(websocket, connection_id)
            else:
                log_error(f"连接处理失败: {connection_result.get('message', 'Unknown error')}", "WEBSOCKET")
                await websocket.close(code=1011, reason="连接处理失败")
                
        except websockets.exceptions.ConnectionClosed:
            log_info(f"WebSocket连接正常关闭: {connection_id or remote_address}", "WEBSOCKET")
        except websockets.exceptions.ConnectionClosedError as e:
            log_warning(f"WebSocket连接异常关闭: {connection_id or remote_address} - {e}", "WEBSOCKET")
        except Exception as e:
            log_error(f"WebSocket连接处理异常: {connection_id or remote_address} - {e}", "WEBSOCKET")
        finally:
            # 清理连接
            await self._cleanup_connection(websocket, connection_id, remote_address)
    
    async def _message_loop(self, websocket, connection_id: str):
        """消息处理循环"""
        try:
            async for message in websocket:
                try:
                    # 处理消息
                    result = handle_message(websocket, connection_id, message)
                    
                    if result['status'] != 'success':
                        log_warning(f"消息处理警告: {result.get('message', 'Unknown')}", "WEBSOCKET")
                        
                except Exception as e:
                    log_error(f"处理消息异常: {e}", "WEBSOCKET")
                    
                    # 发送错误响应
                    error_response = {
                        'type': 'error',
                        'error': '消息处理异常',
                        'details': str(e),
                        'timestamp': get_timestamp()
                    }
                    
                    try:
                        await websocket.send(json.dumps(error_response, ensure_ascii=False))
                    except:
                        break  # 如果无法发送错误响应，退出循环
                        
        except websockets.exceptions.ConnectionClosed:
            pass  # 连接关闭，正常退出循环
        except Exception as e:
            log_error(f"消息循环异常: {e}", "WEBSOCKET")
    
    async def _cleanup_connection(self, websocket, connection_id: str, remote_address: str):
        """清理连接"""
        try:
            # 从活跃连接中移除
            self.active_websockets.discard(websocket)
            
            # 从连接映射中移除
            if websocket in self.connection_mapping:
                del self.connection_mapping[websocket]
            
            # 处理连接关闭
            if connection_id:
                handle_connection_closed(connection_id, "WebSocket连接关闭")
            
            log_info(f"WebSocket连接清理完成: {connection_id or remote_address}", "WEBSOCKET")
            
        except Exception as e:
            log_error(f"清理WebSocket连接异常: {e}", "WEBSOCKET")
    
    def stop_server(self) -> Dict[str, Any]:
        """停止WebSocket服务器"""
        try:
            if not self.running:
                return format_error_response("服务器未运行", "SERVER_NOT_RUNNING")
            
            self.running = False
            
            # 关闭服务器
            if self.server:
                if self.loop and self.loop.is_running():
                    # 在事件循环中关闭服务器
                    asyncio.run_coroutine_threadsafe(self._close_server(), self.loop)
                
                # 等待服务器线程结束
                if self.server_thread and self.server_thread.is_alive():
                    self.server_thread.join(timeout=10)
            
            # 清理所有连接
            cleanup_all_connections()
            
            log_success("WebSocket服务器已停止", "WEBSOCKET")
            
            return format_success_response("WebSocket服务器停止成功")
            
        except Exception as e:
            log_error(f"停止WebSocket服务器失败: {e}", "WEBSOCKET")
            return format_error_response(f"停止服务器失败: {str(e)}", "SERVER_STOP_ERROR")
    
    async def _close_server(self):
        """关闭服务器（异步）"""
        try:
            if self.server:
                # 关闭所有活跃连接
                if self.active_websockets:
                    close_tasks = []
                    for ws in self.active_websockets.copy():
                        close_tasks.append(ws.close(code=1001, reason="服务器关闭"))
                    
                    if close_tasks:
                        await asyncio.gather(*close_tasks, return_exceptions=True)
                
                # 关闭服务器
                self.server.close()
                await self.server.wait_closed()
                
        except Exception as e:
            log_error(f"异步关闭服务器失败: {e}", "WEBSOCKET")
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        try:
            # 获取连接统计
            conn_stats_result = get_connection_stats()
            conn_stats = conn_stats_result['data'] if conn_stats_result['status'] == 'success' else {}
            
            server_info = {
                'host': self.host,
                'port': self.port,
                'running': self.running,
                'websockets_available': WEBSOCKETS_AVAILABLE,
                'active_websockets': len(self.active_websockets),
                'connection_mappings': len(self.connection_mapping),
                'server_url': f"ws://{self.host}:{self.port}",
                'thread_alive': self.server_thread.is_alive() if self.server_thread else False,
                'connection_stats': conn_stats
            }
            
            return format_success_response(
                "获取服务器信息成功",
                data=server_info
            )
            
        except Exception as e:
            log_error(f"获取服务器信息失败: {e}", "WEBSOCKET")
            return format_error_response(f"获取服务器信息失败: {str(e)}", "GET_INFO_ERROR")
    
    def broadcast_to_all(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """广播消息给所有连接"""
        try:
            if not self.loop or not self.loop.is_running():
                return format_error_response("服务器未运行", "SERVER_NOT_RUNNING")
            
            if not self.active_websockets:
                return format_success_response("没有活跃连接", data={'sent_count': 0})
            
            # 在事件循环中执行广播
            future = asyncio.run_coroutine_threadsafe(
                self._async_broadcast(message), 
                self.loop
            )
            
            # 等待广播完成
            result = future.result(timeout=10)
            return result
            
        except Exception as e:
            log_error(f"广播消息失败: {e}", "WEBSOCKET")
            return format_error_response(f"广播失败: {str(e)}", "BROADCAST_ERROR")
    
    async def _async_broadcast(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """异步广播消息"""
        try:
            message_json = json.dumps(message, ensure_ascii=False)
            
            # 创建发送任务
            send_tasks = []
            for websocket in self.active_websockets.copy():
                send_tasks.append(self._safe_send(websocket, message_json))
            
            # 执行所有发送任务
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            
            # 统计结果
            success_count = sum(1 for result in results if result is True)
            error_count = len(results) - success_count
            
            log_info(f"广播完成: 成功 {success_count}, 失败 {error_count}", "WEBSOCKET")
            
            return format_success_response(
                "广播完成",
                data={
                    'sent_count': success_count,
                    'error_count': error_count,
                    'total_connections': len(self.active_websockets)
                }
            )
            
        except Exception as e:
            log_error(f"异步广播失败: {e}", "WEBSOCKET")
            return format_error_response(f"异步广播失败: {str(e)}", "ASYNC_BROADCAST_ERROR")
    
    async def _safe_send(self, websocket, message: str) -> bool:
        """安全发送消息"""
        try:
            await websocket.send(message)
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，从活跃连接中移除
            self.active_websockets.discard(websocket)
            return False
        except Exception as e:
            log_error(f"发送消息失败: {e}", "WEBSOCKET")
            return False

class WebSocketServerManager:
    """WebSocket服务器管理器"""
    
    def __init__(self):
        """初始化服务器管理器"""
        self.server = None
        log_info("WebSocket服务器管理器初始化完成", "WEBSOCKET")
    
    def start_server(self, host: str = 'localhost', port: int = 8001) -> Dict[str, Any]:
        """启动服务器"""
        try:
            if self.server and self.server.running:
                return format_error_response("服务器已在运行", "SERVER_ALREADY_RUNNING")
            
            self.server = WebSocketServer(host, port)
            return self.server.start_server()
            
        except Exception as e:
            log_error(f"启动WebSocket服务器管理器失败: {e}", "WEBSOCKET")
            return format_error_response(f"启动失败: {str(e)}", "MANAGER_START_ERROR")
    
    def stop_server(self) -> Dict[str, Any]:
        """停止服务器"""
        try:
            if not self.server:
                return format_error_response("服务器未初始化", "SERVER_NOT_INITIALIZED")
            
            result = self.server.stop_server()
            self.server = None
            return result
            
        except Exception as e:
            log_error(f"停止WebSocket服务器管理器失败: {e}", "WEBSOCKET")
            return format_error_response(f"停止失败: {str(e)}", "MANAGER_STOP_ERROR")
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        if not self.server:
            return format_error_response("服务器未初始化", "SERVER_NOT_INITIALIZED")
        
        return self.server.get_server_info()
    
    def broadcast_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """广播消息"""
        if not self.server:
            return format_error_response("服务器未初始化", "SERVER_NOT_INITIALIZED")
        
        return self.server.broadcast_to_all(message)

# 创建全局服务器管理器
websocket_server_manager = WebSocketServerManager()

# 导出主要函数
def start_websocket_server(host: str = 'localhost', port: int = 8001) -> Dict[str, Any]:
    """启动WebSocket服务器"""
    return websocket_server_manager.start_server(host, port)

def stop_websocket_server() -> Dict[str, Any]:
    """停止WebSocket服务器"""
    return websocket_server_manager.stop_server()

def get_websocket_server_info() -> Dict[str, Any]:
    """获取WebSocket服务器信息"""
    return websocket_server_manager.get_server_info()

def broadcast_websocket_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """广播WebSocket消息"""
    return websocket_server_manager.broadcast_message(message)

def run_websocket_server_blocking(host: str = 'localhost', port: int = 8001):
    """以阻塞模式运行WebSocket服务器"""
    try:
        print("🚀 扑克识别系统 WebSocket 服务器")
        print("=" * 50)
        print(f"📡 WebSocket地址: ws://{host}:{port}")
        print(f"🤵 荷官端连接: ws://{host}:{port}")
        print(f"💬 支持消息类型: ping, get_recognition_result, dealer_register")
        print("=" * 50)
        
        if not WEBSOCKETS_AVAILABLE:
            print("❌ websockets库未安装!")
            print("   请运行: pip install websockets")
            return False
        
        print("💡 功能说明:")
        print("1. 荷官端通过WebSocket连接获取识别结果")
        print("2. 支持断线重连和心跳检测")
        print("3. 实时推送识别结果更新")
        print("4. 按 Ctrl+C 停止服务器")
        print("=" * 50)
        
        # 启动服务器
        result = start_websocket_server(host, port)
        
        if result['status'] == 'success':
            log_success(f"WebSocket服务器启动成功: ws://{host}:{port}", "WEBSOCKET")
            
            try:
                # 保持运行直到中断
                while True:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n👋 正在停止服务器...")
                stop_result = stop_websocket_server()
                
                if stop_result['status'] == 'success':
                    print("✅ WebSocket服务器已停止")
                else:
                    print(f"⚠️ 停止服务器时出现问题: {stop_result.get('message', 'Unknown error')}")
                    
                return True
        else:
            print(f"❌ WebSocket服务器启动失败: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        log_error(f"运行WebSocket服务器失败: {e}", "WEBSOCKET")
        print(f"❌ 服务器运行异常: {e}")
        return False

if __name__ == "__main__":
    # 直接运行WebSocket服务器
    
    
    host = 'localhost'
    port = 8001
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ 端口号格式错误，使用默认端口 8001")
    
    if len(sys.argv) > 2:
        host = sys.argv[2]
    
    # 运行服务器
    try:
        success = run_websocket_server_blocking(host, port)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        sys.exit(1)