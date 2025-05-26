#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket连接管理模块 - 管理WebSocket连接的生命周期
功能:
1. WebSocket连接的添加和移除
2. 连接状态监控和心跳检测
3. 断线重连处理
4. 连接信息存储和查询
5. 广播消息管理
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


import json
import time
import threading
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from src.core.utils import (
    get_timestamp, format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning
)

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        """初始化连接管理器"""
        # 活跃连接存储 {connection_id: connection_info}
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        
        # 荷官连接映射 {dealer_id: connection_id}
        self.dealer_connections: Dict[str, str] = {}
        
        # 连接锁
        self.connections_lock = threading.RLock()
        
        # 心跳检测配置
        self.heartbeat_interval = 30  # 心跳间隔(秒)
        self.connection_timeout = 60  # 连接超时(秒)
        
        # 心跳检测线程
        self.heartbeat_thread = None
        self.heartbeat_running = False
        
        # 统计信息
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'reconnections': 0,
            'timeouts': 0,
            'start_time': get_timestamp()
        }
        
        log_info("WebSocket连接管理器初始化完成", "CONN")
    
    def add_connection(self, websocket, connection_id: str, dealer_id: str = None, 
                      client_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        添加新连接
        
        Args:
            websocket: WebSocket连接对象
            connection_id: 连接ID
            dealer_id: 荷官ID（可选）
            client_info: 客户端信息
            
        Returns:
            添加结果
        """
        try:
            with self.connections_lock:
                # 检查连接是否已存在
                if connection_id in self.active_connections:
                    return format_error_response(f"连接ID {connection_id} 已存在", "CONNECTION_EXISTS")
                
                # 创建连接信息
                connection_info = {
                    'connection_id': connection_id,
                    'dealer_id': dealer_id,
                    'websocket': websocket,
                    'client_info': client_info or {},
                    'connected_at': get_timestamp(),
                    'last_heartbeat': time.time(),
                    'status': 'connected',
                    'message_count': 0,
                    'reconnect_count': 0
                }
                
                # 添加到活跃连接
                self.active_connections[connection_id] = connection_info
                
                # 如果有荷官ID，添加到荷官映射
                if dealer_id:
                    # 检查是否有旧的连接
                    old_connection_id = self.dealer_connections.get(dealer_id)
                    if old_connection_id and old_connection_id in self.active_connections:
                        log_warning(f"荷官 {dealer_id} 有旧连接 {old_connection_id}，将被替换", "CONN")
                        self._remove_connection_internal(old_connection_id)
                    
                    self.dealer_connections[dealer_id] = connection_id
                
                # 更新统计
                self.stats['total_connections'] += 1
                self.stats['active_connections'] = len(self.active_connections)
                
                # 启动心跳检测（如果还未启动）
                self._ensure_heartbeat_running()
                
                log_success(f"添加连接成功: {connection_id} (荷官: {dealer_id or 'N/A'})", "CONN")
                
                return format_success_response(
                    "连接添加成功",
                    data={
                        'connection_id': connection_id,
                        'dealer_id': dealer_id,
                        'connected_at': connection_info['connected_at'],
                        'active_connections': len(self.active_connections)
                    }
                )
                
        except Exception as e:
            log_error(f"添加连接失败: {e}", "CONN")
            return format_error_response(f"添加连接失败: {str(e)}", "ADD_CONNECTION_ERROR")
    
    def remove_connection(self, connection_id: str, reason: str = "客户端断开") -> Dict[str, Any]:
        """
        移除连接
        
        Args:
            connection_id: 连接ID
            reason: 断开原因
            
        Returns:
            移除结果
        """
        try:
            with self.connections_lock:
                return self._remove_connection_internal(connection_id, reason)
                
        except Exception as e:
            log_error(f"移除连接失败: {e}", "CONN")
            return format_error_response(f"移除连接失败: {str(e)}", "REMOVE_CONNECTION_ERROR")
    
    def _remove_connection_internal(self, connection_id: str, reason: str = "内部移除") -> Dict[str, Any]:
        """内部移除连接方法（已加锁）"""
        if connection_id not in self.active_connections:
            return format_error_response(f"连接 {connection_id} 不存在", "CONNECTION_NOT_FOUND")
        
        connection_info = self.active_connections[connection_id]
        dealer_id = connection_info.get('dealer_id')
        
        # 从活跃连接中移除
        del self.active_connections[connection_id]
        
        # 从荷官映射中移除
        if dealer_id and self.dealer_connections.get(dealer_id) == connection_id:
            del self.dealer_connections[dealer_id]
        
        # 更新统计
        self.stats['active_connections'] = len(self.active_connections)
        
        log_info(f"移除连接: {connection_id} (荷官: {dealer_id or 'N/A'}) - 原因: {reason}", "CONN")
        
        return format_success_response(
            "连接移除成功",
            data={
                'connection_id': connection_id,
                'dealer_id': dealer_id,
                'reason': reason,
                'active_connections': len(self.active_connections)
            }
        )
    
    def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        with self.connections_lock:
            return self.active_connections.get(connection_id)
    
    def get_dealer_connection(self, dealer_id: str) -> Optional[Dict[str, Any]]:
        """根据荷官ID获取连接信息"""
        with self.connections_lock:
            connection_id = self.dealer_connections.get(dealer_id)
            if connection_id:
                return self.active_connections.get(connection_id)
            return None
    
    def get_all_connections(self) -> List[Dict[str, Any]]:
        """获取所有活跃连接"""
        with self.connections_lock:
            connections = []
            for conn_info in self.active_connections.values():
                # 返回连接信息的副本（不包含websocket对象）
                safe_info = {
                    'connection_id': conn_info['connection_id'],
                    'dealer_id': conn_info.get('dealer_id'),
                    'connected_at': conn_info['connected_at'],
                    'last_heartbeat': conn_info['last_heartbeat'],
                    'status': conn_info['status'],
                    'message_count': conn_info['message_count'],
                    'reconnect_count': conn_info['reconnect_count'],
                    'client_info': conn_info.get('client_info', {})
                }
                connections.append(safe_info)
            return connections
    
    def update_heartbeat(self, connection_id: str) -> bool:
        """更新连接心跳时间"""
        try:
            with self.connections_lock:
                if connection_id in self.active_connections:
                    self.active_connections[connection_id]['last_heartbeat'] = time.time()
                    self.active_connections[connection_id]['status'] = 'connected'
                    return True
                return False
        except Exception as e:
            log_error(f"更新心跳失败: {e}", "CONN")
            return False
    
    def increment_message_count(self, connection_id: str):
        """增加消息计数"""
        try:
            with self.connections_lock:
                if connection_id in self.active_connections:
                    self.active_connections[connection_id]['message_count'] += 1
        except Exception as e:
            log_error(f"更新消息计数失败: {e}", "CONN")
    
    def handle_reconnection(self, websocket, connection_id: str, dealer_id: str) -> Dict[str, Any]:
        """处理重连"""
        try:
            with self.connections_lock:
                # 移除旧连接（如果存在）
                if connection_id in self.active_connections:
                    self._remove_connection_internal(connection_id, "重连替换")
                
                # 增加重连计数
                self.stats['reconnections'] += 1
                
                # 添加新连接，并设置重连计数
                result = self.add_connection(websocket, connection_id, dealer_id)
                
                if result['status'] == 'success':
                    self.active_connections[connection_id]['reconnect_count'] = \
                        self.active_connections[connection_id].get('reconnect_count', 0) + 1
                    
                    log_success(f"重连成功: {connection_id} (荷官: {dealer_id})", "CONN")
                
                return result
                
        except Exception as e:
            log_error(f"处理重连失败: {e}", "CONN")
            return format_error_response(f"重连处理失败: {str(e)}", "RECONNECTION_ERROR")
    
    def _ensure_heartbeat_running(self):
        """确保心跳检测线程运行"""
        if not self.heartbeat_running:
            self.heartbeat_running = True
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_checker, daemon=True)
            self.heartbeat_thread.start()
            log_info("心跳检测线程启动", "CONN")
    
    def _heartbeat_checker(self):
        """心跳检测线程"""
        while self.heartbeat_running:
            try:
                current_time = time.time()
                timeout_connections = []
                
                with self.connections_lock:
                    for connection_id, conn_info in self.active_connections.items():
                        last_heartbeat = conn_info['last_heartbeat']
                        
                        # 检查是否超时
                        if current_time - last_heartbeat > self.connection_timeout:
                            timeout_connections.append(connection_id)
                        elif current_time - last_heartbeat > self.heartbeat_interval:
                            # 标记为可能断开
                            conn_info['status'] = 'heartbeat_missing'
                
                # 移除超时连接
                for connection_id in timeout_connections:
                    self.remove_connection(connection_id, "心跳超时")
                    self.stats['timeouts'] += 1
                
                if timeout_connections:
                    log_warning(f"移除 {len(timeout_connections)} 个超时连接", "CONN")
                
            except Exception as e:
                log_error(f"心跳检测异常: {e}", "CONN")
            
            # 等待下次检测
            time.sleep(self.heartbeat_interval)
    
    def stop_heartbeat(self):
        """停止心跳检测"""
        self.heartbeat_running = False
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        log_info("心跳检测线程已停止", "CONN")
    
    def broadcast_message(self, message: Dict[str, Any], exclude_connections: Set[str] = None) -> Dict[str, Any]:
        """
        广播消息给所有连接
        
        Args:
            message: 要广播的消息
            exclude_connections: 要排除的连接ID集合
            
        Returns:
            广播结果
        """
        try:
            exclude_connections = exclude_connections or set()
            message_json = json.dumps(message, ensure_ascii=False)
            
            success_count = 0
            error_count = 0
            
            with self.connections_lock:
                for connection_id, conn_info in self.active_connections.items():
                    if connection_id in exclude_connections:
                        continue
                    
                    try:
                        websocket = conn_info['websocket']
                        # 这里需要根据实际的WebSocket库来发送消息
                        # websocket.send(message_json)
                        success_count += 1
                        self.increment_message_count(connection_id)
                        
                    except Exception as e:
                        log_error(f"广播消息到连接 {connection_id} 失败: {e}", "CONN")
                        error_count += 1
            
            log_info(f"广播消息完成: 成功 {success_count}, 失败 {error_count}", "CONN")
            
            return format_success_response(
                "消息广播完成",
                data={
                    'success_count': success_count,
                    'error_count': error_count,
                    'total_connections': len(self.active_connections)
                }
            )
            
        except Exception as e:
            log_error(f"广播消息失败: {e}", "CONN")
            return format_error_response(f"广播失败: {str(e)}", "BROADCAST_ERROR")
    
    def send_to_dealer(self, dealer_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送消息给指定荷官
        
        Args:
            dealer_id: 荷官ID
            message: 消息内容
            
        Returns:
            发送结果
        """
        try:
            connection_info = self.get_dealer_connection(dealer_id)
            
            if not connection_info:
                return format_error_response(f"荷官 {dealer_id} 未连接", "DEALER_NOT_CONNECTED")
            
            connection_id = connection_info['connection_id']
            websocket = connection_info['websocket']
            
            message_json = json.dumps(message, ensure_ascii=False)
            
            # 发送消息（需要根据实际WebSocket库实现）
            # websocket.send(message_json)
            
            self.increment_message_count(connection_id)
            
            log_success(f"消息发送给荷官 {dealer_id} 成功", "CONN")
            
            return format_success_response(
                f"消息发送给荷官 {dealer_id} 成功",
                data={
                    'dealer_id': dealer_id,
                    'connection_id': connection_id,
                    'message_size': len(message_json)
                }
            )
            
        except Exception as e:
            log_error(f"发送消息给荷官 {dealer_id} 失败: {e}", "CONN")
            return format_error_response(f"发送失败: {str(e)}", "SEND_TO_DEALER_ERROR")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        with self.connections_lock:
            current_stats = self.stats.copy()
            current_stats.update({
                'current_active': len(self.active_connections),
                'dealers_connected': len(self.dealer_connections),
                'uptime_seconds': int(time.time() - time.mktime(
                    datetime.fromisoformat(self.stats['start_time']).timetuple()
                )) if self.stats['start_time'] else 0
            })
            
            return format_success_response(
                "连接统计获取成功",
                data=current_stats
            )
    
    def cleanup_all_connections(self):
        """清理所有连接"""
        try:
            with self.connections_lock:
                connection_ids = list(self.active_connections.keys())
                
                for connection_id in connection_ids:
                    self._remove_connection_internal(connection_id, "服务器关闭")
                
                self.dealer_connections.clear()
                self.stop_heartbeat()
                
                log_info(f"清理了 {len(connection_ids)} 个连接", "CONN")
                
        except Exception as e:
            log_error(f"清理所有连接失败: {e}", "CONN")

# 创建全局实例
connection_manager = ConnectionManager()

# 导出主要函数
def add_connection(websocket, connection_id: str, dealer_id: str = None, 
                  client_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """添加连接"""
    return connection_manager.add_connection(websocket, connection_id, dealer_id, client_info)

def remove_connection(connection_id: str, reason: str = "客户端断开") -> Dict[str, Any]:
    """移除连接"""
    return connection_manager.remove_connection(connection_id, reason)

def get_connection(connection_id: str) -> Optional[Dict[str, Any]]:
    """获取连接信息"""
    return connection_manager.get_connection(connection_id)

def get_dealer_connection(dealer_id: str) -> Optional[Dict[str, Any]]:
    """获取荷官连接"""
    return connection_manager.get_dealer_connection(dealer_id)

def get_all_connections() -> List[Dict[str, Any]]:
    """获取所有连接"""
    return connection_manager.get_all_connections()

def update_heartbeat(connection_id: str) -> bool:
    """更新心跳"""
    return connection_manager.update_heartbeat(connection_id)

def handle_reconnection(websocket, connection_id: str, dealer_id: str) -> Dict[str, Any]:
    """处理重连"""
    return connection_manager.handle_reconnection(websocket, connection_id, dealer_id)

def broadcast_message(message: Dict[str, Any], exclude_connections: Set[str] = None) -> Dict[str, Any]:
    """广播消息"""
    return connection_manager.broadcast_message(message, exclude_connections)

def send_to_dealer(dealer_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """发送消息给荷官"""
    return connection_manager.send_to_dealer(dealer_id, message)

def get_connection_stats() -> Dict[str, Any]:
    """获取连接统计"""
    return connection_manager.get_connection_stats()

def cleanup_all_connections():
    """清理所有连接"""
    return connection_manager.cleanup_all_connections()

if __name__ == "__main__":
    # 测试连接管理器
    print("🧪 测试连接管理器")
    
    # 模拟WebSocket对象
    class MockWebSocket:
        def __init__(self, name):
            self.name = name
        def send(self, message):
            print(f"[{self.name}] 发送: {message}")
    
    # 测试添加连接
    ws1 = MockWebSocket("dealer1")
    result1 = add_connection(ws1, "conn_001", "dealer_001", {"ip": "192.168.1.100"})
    print(f"添加连接1: {result1['status']}")
    
    ws2 = MockWebSocket("dealer2")
    result2 = add_connection(ws2, "conn_002", "dealer_002", {"ip": "192.168.1.101"})
    print(f"添加连接2: {result2['status']}")
    
    # 测试获取连接
    all_conns = get_all_connections()
    print(f"活跃连接数: {len(all_conns)}")
    
    # 测试心跳更新
    heartbeat_result = update_heartbeat("conn_001")
    print(f"更新心跳: {heartbeat_result}")
    
    # 测试连接统计
    stats = get_connection_stats()
    print(f"连接统计: {stats['status']}")
    if stats['status'] == 'success':
        data = stats['data']
        print(f"   总连接数: {data['total_connections']}")
        print(f"   活跃连接: {data['current_active']}")
    
    # 测试发送消息给荷官
    test_message = {"type": "test", "content": "Hello dealer!"}
    send_result = send_to_dealer("dealer_001", test_message)
    print(f"发送消息: {send_result['status']}")
    
    # 测试移除连接
    remove_result = remove_connection("conn_001", "测试完成")
    print(f"移除连接: {remove_result['status']}")
    
    # 清理
    cleanup_all_connections()
    print("✅ 连接管理器测试完成")