#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket推送客户端模块 - 连接到外部WebSocket服务器推送识别结果
功能:
1. 连接到外部WebSocket服务器
2. Python客户端注册
3. 识别结果推送
4. 心跳保持和自动重连
5. 错误处理和日志记录
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
from typing import Dict, Any, Optional, Callable
from datetime import datetime

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = None

from src.core.utils import (
    get_timestamp, format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning
)

class WebSocketPushClient:
    """WebSocket推送客户端"""
    
    def __init__(self, server_url: str = "ws://bjl_heguan_wss.yhyule666.com:8001", client_id: str = "python_client_001"):
        """初始化WebSocket推送客户端"""
        self.server_url = server_url
        self.client_id = client_id
        self.version = "1.0.0"
        self.capabilities = ["card_recognition", "real_time_processing"]
        
        # 连接状态
        self.websocket = None
        self.connected = False
        self.registered = False
        self.running = False
        
        # 线程和事件循环
        self.client_thread = None
        self.loop = None
        
        # 重连配置
        self.retry_times = 3
        self.retry_delay = 5
        self.heartbeat_interval = 30
        self.connection_timeout = 10
        
        # 统计信息
        self.stats = {
            'connection_attempts': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'last_connected': None,
            'last_disconnected': None,
            'start_time': get_timestamp()
        }
        
        log_info("WebSocket推送客户端初始化完成", "PUSH_CLIENT")
    
    def start(self) -> Dict[str, Any]:
        """启动推送客户端"""
        try:
            if not WEBSOCKETS_AVAILABLE:
                return format_error_response(
                    "websockets库未安装，请运行: pip install websockets", 
                    "WEBSOCKETS_NOT_AVAILABLE"
                )
            
            if self.running:
                return format_error_response("推送客户端已在运行", "CLIENT_ALREADY_RUNNING")
            
            # 在新线程中启动客户端
            self.client_thread = threading.Thread(target=self._run_client_thread, daemon=True)
            self.running = True
            self.client_thread.start()
            
            # 等待连接建立
            max_wait = 10  # 最大等待10秒
            wait_time = 0.5
            total_waited = 0
            
            while total_waited < max_wait and self.running:
                if self.connected:
                    break
                time.sleep(wait_time)
                total_waited += wait_time
            
            if self.connected:
                log_success(f"WebSocket推送客户端启动成功: {self.server_url}", "PUSH_CLIENT")
                return format_success_response(
                    "WebSocket推送客户端启动成功",
                    data={
                        'server_url': self.server_url,
                        'client_id': self.client_id,
                        'connected': self.connected,
                        'registered': self.registered
                    }
                )
            else:
                self.running = False
                return format_error_response("客户端连接超时", "CONNECTION_TIMEOUT")
                
        except Exception as e:
            self.running = False
            log_error(f"WebSocket推送客户端启动失败: {e}", "PUSH_CLIENT")
            return format_error_response(f"客户端启动失败: {str(e)}", "CLIENT_START_ERROR")
    
    def _run_client_thread(self):
        """在新线程中运行客户端"""
        try:
            # 创建新的事件循环
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # 启动WebSocket客户端
            self.loop.run_until_complete(self._start_websocket_client())
            
        except Exception as e:
            log_error(f"WebSocket推送客户端线程异常: {e}", "PUSH_CLIENT")
            self.running = False
    
    async def _start_websocket_client(self):
        """启动WebSocket客户端（异步）"""
        retry_count = 0
        
        while self.running and retry_count <= self.retry_times:
            try:
                self.stats['connection_attempts'] += 1
                log_info(f"尝试连接WebSocket服务器: {self.server_url} (第{retry_count + 1}次)", "PUSH_CLIENT")
                
                # 建立WebSocket连接
                async with websockets.connect(
                    self.server_url,
                    ping_interval=self.heartbeat_interval,
                    ping_timeout=self.connection_timeout,
                    close_timeout=5
                ) as websocket:
                    self.websocket = websocket
                    self.connected = True
                    self.stats['successful_connections'] += 1
                    self.stats['last_connected'] = get_timestamp()
                    
                    log_success(f"WebSocket连接建立: {self.server_url}", "PUSH_CLIENT")
                    
                    # 处理连接生命周期
                    await self._handle_connection_lifecycle()
                    
            except websockets.exceptions.ConnectionClosed:
                log_warning(f"WebSocket连接已关闭", "PUSH_CLIENT")
                self._handle_disconnection()
            except Exception as e:
                log_error(f"WebSocket连接失败: {e}", "PUSH_CLIENT")
                self.stats['failed_connections'] += 1
                self._handle_disconnection()
                
                retry_count += 1
                if retry_count <= self.retry_times and self.running:
                    log_info(f"等待 {self.retry_delay} 秒后重试...", "PUSH_CLIENT")
                    await asyncio.sleep(self.retry_delay)
        
        if self.running:
            log_error(f"WebSocket连接重试次数已用尽", "PUSH_CLIENT")
            self.running = False
    
    async def _handle_connection_lifecycle(self):
        """处理连接生命周期"""
        try:
            # 接收欢迎消息
            welcome_message = await self.websocket.recv()
            welcome_data = json.loads(welcome_message)
            log_info(f"收到欢迎消息: {welcome_data.get('message', 'Unknown')}", "PUSH_CLIENT")
            self.stats['messages_received'] += 1
            
            # 注册Python客户端
            await self._register_client()
            
            # 启动消息处理循环
            await self._message_loop()
            
        except Exception as e:
            log_error(f"连接生命周期处理异常: {e}", "PUSH_CLIENT")
            raise
    
    async def _register_client(self):
        """注册Python客户端"""
        try:
            register_message = {
                "type": "python_register",
                "client_id": self.client_id,
                "version": self.version,
                "capabilities": self.capabilities
            }
            
            await self.websocket.send(json.dumps(register_message, ensure_ascii=False))
            self.stats['messages_sent'] += 1
            
            # 等待注册响应
            response_message = await self.websocket.recv()
            response_data = json.loads(response_message)
            self.stats['messages_received'] += 1
            
            if response_data.get('status') == 'success':
                self.registered = True
                log_success(f"客户端注册成功: {self.client_id}", "PUSH_CLIENT")
            else:
                log_error(f"客户端注册失败: {response_data.get('message', 'Unknown error')}", "PUSH_CLIENT")
                
        except Exception as e:
            log_error(f"客户端注册异常: {e}", "PUSH_CLIENT")
    
    async def _message_loop(self):
        """消息处理循环"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.stats['messages_received'] += 1
                    await self._handle_server_message(data)
                    
                except json.JSONDecodeError as e:
                    log_error(f"消息JSON解析失败: {e}", "PUSH_CLIENT")
                except Exception as e:
                    log_error(f"处理服务器消息异常: {e}", "PUSH_CLIENT")
                    
        except websockets.exceptions.ConnectionClosed:
            log_info("WebSocket连接已关闭", "PUSH_CLIENT")
        except Exception as e:
            log_error(f"消息循环异常: {e}", "PUSH_CLIENT")
    
    async def _handle_server_message(self, data: Dict[str, Any]):
        """处理服务器消息"""
        message_type = data.get('type', 'unknown')
        
        if message_type == 'pong':
            log_info("收到心跳响应", "PUSH_CLIENT")
        elif message_type == 'recognition_update_ack':
            log_info("识别结果推送确认", "PUSH_CLIENT")
        elif message_type == 'error':
            log_error(f"服务器错误: {data.get('error', 'Unknown error')}", "PUSH_CLIENT")
        else:
            log_info(f"收到未知消息类型: {message_type}", "PUSH_CLIENT")
    
    def _handle_disconnection(self):
        """处理断开连接"""
        self.connected = False
        self.registered = False
        self.websocket = None
        self.stats['last_disconnected'] = get_timestamp()
        log_warning("WebSocket连接断开", "PUSH_CLIENT")
    
    def stop(self) -> Dict[str, Any]:
        """停止推送客户端"""
        try:
            if not self.running:
                return format_error_response("推送客户端未运行", "CLIENT_NOT_RUNNING")
            
            self.running = False
            
            # 关闭WebSocket连接
            if self.websocket and self.connected:
                if self.loop and self.loop.is_running():
                    asyncio.run_coroutine_threadsafe(self._close_connection(), self.loop)
            
            # 等待客户端线程结束
            if self.client_thread and self.client_thread.is_alive():
                self.client_thread.join(timeout=5)
            
            log_success("WebSocket推送客户端已停止", "PUSH_CLIENT")
            
            return format_success_response("WebSocket推送客户端停止成功")
            
        except Exception as e:
            log_error(f"停止WebSocket推送客户端失败: {e}", "PUSH_CLIENT")
            return format_error_response(f"停止客户端失败: {str(e)}", "CLIENT_STOP_ERROR")
    
    async def _close_connection(self):
        """关闭连接（异步）"""
        try:
            if self.websocket:
                await self.websocket.close(code=1000, reason="客户端主动关闭")
        except Exception as e:
            log_error(f"关闭WebSocket连接失败: {e}", "PUSH_CLIENT")
    
    def push_recognition_result(self, camera_id: str, positions: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """推送识别结果"""
        try:
            if not self.connected or not self.registered:
                return format_error_response("客户端未连接或未注册", "CLIENT_NOT_READY")
            
            message = {
                "type": "recognition_result_update",
                "camera_id": camera_id,
                "positions": positions,
                "timestamp": get_timestamp()
            }
            
            if self.loop and self.loop.is_running():
                # 在事件循环中发送消息
                future = asyncio.run_coroutine_threadsafe(
                    self._send_message(message), 
                    self.loop
                )
                
                # 等待发送完成
                result = future.result(timeout=5)
                return result
            else:
                return format_error_response("事件循环未运行", "LOOP_NOT_RUNNING")
                
        except Exception as e:
            log_error(f"推送识别结果失败: {e}", "PUSH_CLIENT")
            return format_error_response(f"推送失败: {str(e)}", "PUSH_ERROR")
    
    async def _send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息（异步）"""
        try:
            if not self.websocket:
                return format_error_response("WebSocket连接不存在", "NO_CONNECTION")
            
            message_json = json.dumps(message, ensure_ascii=False)
            await self.websocket.send(message_json)
            self.stats['messages_sent'] += 1
            
            log_info(f"消息发送成功: {message['type']}", "PUSH_CLIENT")
            
            return format_success_response("消息发送成功", data={'message_type': message['type']})
            
        except Exception as e:
            log_error(f"发送消息失败: {e}", "PUSH_CLIENT")
            return format_error_response(f"发送失败: {str(e)}", "SEND_ERROR")
    
    def send_heartbeat(self) -> Dict[str, Any]:
        """发送心跳"""
        try:
            if not self.connected:
                return format_error_response("客户端未连接", "CLIENT_NOT_CONNECTED")
            
            ping_message = {"type": "ping"}
            
            if self.loop and self.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._send_message(ping_message), 
                    self.loop
                )
                result = future.result(timeout=3)
                return result
            else:
                return format_error_response("事件循环未运行", "LOOP_NOT_RUNNING")
                
        except Exception as e:
            log_error(f"发送心跳失败: {e}", "PUSH_CLIENT")
            return format_error_response(f"心跳失败: {str(e)}", "HEARTBEAT_ERROR")
    
    def get_client_status(self) -> Dict[str, Any]:
        """获取客户端状态"""
        try:
            status_data = {
                'server_url': self.server_url,
                'client_id': self.client_id,
                'running': self.running,
                'connected': self.connected,
                'registered': self.registered,
                'websockets_available': WEBSOCKETS_AVAILABLE,
                'thread_alive': self.client_thread.is_alive() if self.client_thread else False,
                'stats': self.stats
            }
            
            return format_success_response(
                "获取客户端状态成功",
                data=status_data
            )
            
        except Exception as e:
            log_error(f"获取客户端状态失败: {e}", "PUSH_CLIENT")
            return format_error_response(f"获取状态失败: {str(e)}", "GET_STATUS_ERROR")

# 创建全局推送客户端实例
push_client = None

def start_push_client(server_url: str = "ws://localhost:8001", client_id: str = "python_client_001") -> Dict[str, Any]:
    """启动推送客户端"""
    global push_client
    
    try:
        if push_client and push_client.running:
            return format_error_response("推送客户端已在运行", "CLIENT_ALREADY_RUNNING")
        
        push_client = WebSocketPushClient(server_url, client_id)
        return push_client.start()
        
    except Exception as e:
        log_error(f"启动推送客户端失败: {e}", "PUSH_CLIENT")
        return format_error_response(f"启动失败: {str(e)}", "START_ERROR")

def stop_push_client() -> Dict[str, Any]:
    """停止推送客户端"""
    global push_client
    
    try:
        if not push_client:
            return format_error_response("推送客户端未初始化", "CLIENT_NOT_INITIALIZED")
        
        result = push_client.stop()
        push_client = None
        return result
        
    except Exception as e:
        log_error(f"停止推送客户端失败: {e}", "PUSH_CLIENT")
        return format_error_response(f"停止失败: {str(e)}", "STOP_ERROR")

def get_push_client_status() -> Dict[str, Any]:
    """获取推送客户端状态"""
    global push_client
    
    if not push_client:
        return format_error_response("推送客户端未初始化", "CLIENT_NOT_INITIALIZED")
    
    return push_client.get_client_status()

def push_recognition_result(camera_id: str, positions: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """推送识别结果"""
    global push_client
    
    if not push_client:
        return format_error_response("推送客户端未初始化", "CLIENT_NOT_INITIALIZED")
    
    return push_client.push_recognition_result(camera_id, positions)

if __name__ == "__main__":
    # 测试推送客户端
    print("🧪 测试WebSocket推送客户端")
    
    # 启动客户端
    result = start_push_client("ws://localhost:8001", "test_client_001")
    print(f"启动结果: {result}")
    
    if result['status'] == 'success':
        # 等待连接稳定
        time.sleep(2)
        
        # 测试推送识别结果
        test_positions = {
            "zhuang_1": {"suit": "hearts", "rank": "A"},
            "zhuang_2": {"suit": "spades", "rank": "K"},
            "zhuang_3": {"suit": "", "rank": ""},
            "xian_1": {"suit": "diamonds", "rank": "Q"},
            "xian_2": {"suit": "clubs", "rank": "J"},
            "xian_3": {"suit": "", "rank": ""}
        }
        
        push_result = push_recognition_result("camera_001", test_positions)
        print(f"推送结果: {push_result}")
        
        # 测试心跳
        if push_client:
            heartbeat_result = push_client.send_heartbeat()
            print(f"心跳结果: {heartbeat_result}")
        
        # 获取状态
        status = get_push_client_status()
        print(f"客户端状态: {status}")
        
        # 等待一段时间
        time.sleep(5)
        
        # 停止客户端
        stop_result = stop_push_client()
        print(f"停止结果: {stop_result}")
    
    print("✅ WebSocket推送客户端测试完成")