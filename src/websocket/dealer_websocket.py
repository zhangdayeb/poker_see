#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
荷官WebSocket通信模块 - 处理与荷官端的WebSocket通信业务逻辑
功能:
1. 荷官端WebSocket消息处理
2. 识别结果数据推送
3. 连接验证和认证
4. 消息格式化和验证
5. 业务逻辑处理
"""

import json
import uuid
from typing import Dict, Any, Optional, Callable
from utils import (
    get_timestamp, format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning
)
from connection_manager import (
    add_connection, remove_connection, update_heartbeat, send_to_dealer,
    get_dealer_connection, get_all_connections
)
from recognition_manager import format_for_dealer

class DealerWebSocketHandler:
    """荷官WebSocket通信处理器"""
    
    def __init__(self):
        """初始化荷官通信处理器"""
        # 消息处理器映射
        self.message_handlers = {
            'ping': self._handle_ping,
            'get_recognition_result': self._handle_get_recognition_result,
            'connection_test': self._handle_connection_test,
            'dealer_register': self._handle_dealer_register,
            'dealer_heartbeat': self._handle_dealer_heartbeat,
            'get_system_status': self._handle_get_system_status
        }
        
        # 认证配置
        self.require_auth = False  # 暂时不需要认证
        self.valid_dealer_ids = set()  # 有效的荷官ID集合
        
        log_info("荷官WebSocket通信处理器初始化完成", "DEALER")
    
    def handle_new_connection(self, websocket, remote_address: str) -> Dict[str, Any]:
        """
        处理新的WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            remote_address: 客户端地址
            
        Returns:
            连接处理结果
        """
        try:
            # 生成连接ID
            connection_id = f"dealer_{uuid.uuid4().hex[:8]}"
            
            # 客户端信息
            client_info = {
                'remote_address': remote_address,
                'user_agent': 'WebSocket Client',
                'connected_at': get_timestamp()
            }
            
            # 添加到连接管理器（暂时不指定dealer_id）
            result = add_connection(websocket, connection_id, None, client_info)
            
            if result['status'] == 'success':
                # 发送欢迎消息
                welcome_message = {
                    'type': 'welcome',
                    'connection_id': connection_id,
                    'message': '欢迎连接到扑克识别系统',
                    'timestamp': get_timestamp(),
                    'server_info': {
                        'version': '2.0',
                        'supported_actions': list(self.message_handlers.keys())
                    }
                }
                
                self._send_message(websocket, welcome_message)
                
                log_success(f"新连接建立: {connection_id} from {remote_address}", "DEALER")
                
                return format_success_response(
                    "连接建立成功",
                    data={'connection_id': connection_id}
                )
            else:
                return result
                
        except Exception as e:
            log_error(f"处理新连接失败: {e}", "DEALER")
            return format_error_response(f"连接建立失败: {str(e)}", "CONNECTION_FAILED")
    
    def handle_message(self, websocket, connection_id: str, message_text: str) -> Dict[str, Any]:
        """
        处理WebSocket消息
        
        Args:
            websocket: WebSocket连接对象
            connection_id: 连接ID
            message_text: 消息文本
            
        Returns:
            消息处理结果
        """
        try:
            # 解析JSON消息
            try:
                message = json.loads(message_text)
            except json.JSONDecodeError as e:
                error_response = {
                    'type': 'error',
                    'error': 'JSON格式错误',
                    'details': str(e),
                    'timestamp': get_timestamp()
                }
                self._send_message(websocket, error_response)
                return format_error_response("JSON格式错误", "INVALID_JSON")
            
            # 验证消息格式
            if not isinstance(message, dict) or 'type' not in message:
                error_response = {
                    'type': 'error',
                    'error': '消息格式无效',
                    'message': '消息必须包含type字段',
                    'timestamp': get_timestamp()
                }
                self._send_message(websocket, error_response)
                return format_error_response("消息格式无效", "INVALID_MESSAGE_FORMAT")
            
            message_type = message['type']
            
            # 更新心跳
            update_heartbeat(connection_id)
            
            # 查找并调用消息处理器
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                response = handler(websocket, connection_id, message)
                
                # 发送响应
                if response:
                    self._send_message(websocket, response)
                
                log_info(f"处理消息: {message_type} from {connection_id}", "DEALER")
                
                return format_success_response(f"消息 {message_type} 处理成功")
            else:
                # 未知消息类型
                error_response = {
                    'type': 'error',
                    'error': '未知消息类型',
                    'message_type': message_type,
                    'supported_types': list(self.message_handlers.keys()),
                    'timestamp': get_timestamp()
                }
                self._send_message(websocket, error_response)
                
                return format_error_response(f"未知消息类型: {message_type}", "UNKNOWN_MESSAGE_TYPE")
                
        except Exception as e:
            log_error(f"处理消息失败: {e}", "DEALER")
            
            # 发送错误响应
            error_response = {
                'type': 'error',
                'error': '服务器内部错误',
                'details': str(e),
                'timestamp': get_timestamp()
            }
            self._send_message(websocket, error_response)
            
            return format_error_response(f"消息处理失败: {str(e)}", "MESSAGE_PROCESSING_ERROR")
    
    def handle_connection_closed(self, connection_id: str, reason: str = "客户端断开") -> Dict[str, Any]:
        """
        处理连接关闭
        
        Args:
            connection_id: 连接ID
            reason: 关闭原因
            
        Returns:
            处理结果
        """
        try:
            result = remove_connection(connection_id, reason)
            log_info(f"连接关闭: {connection_id} - {reason}", "DEALER")
            return result
            
        except Exception as e:
            log_error(f"处理连接关闭失败: {e}", "DEALER")
            return format_error_response(f"处理连接关闭失败: {str(e)}", "CONNECTION_CLOSE_ERROR")
    
    # ==================== 消息处理器 ====================
    
    def _handle_ping(self, websocket, connection_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理ping消息"""
        return {
            'type': 'pong',
            'connection_id': connection_id,
            'timestamp': get_timestamp(),
            'message': 'pong'
        }
    
    def _handle_get_recognition_result(self, websocket, connection_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取识别结果请求"""
        try:
            # 获取识别结果
            recognition_result = format_for_dealer(include_metadata=True)
            
            if recognition_result['status'] == 'success':
                response = {
                    'type': 'recognition_result',
                    'status': 'success',
                    'data': recognition_result['data'],
                    'timestamp': get_timestamp(),
                    'connection_id': connection_id
                }
            else:
                response = {
                    'type': 'recognition_result',
                    'status': 'error',
                    'error': recognition_result.get('message', '获取识别结果失败'),
                    'timestamp': get_timestamp(),
                    'connection_id': connection_id
                }
            
            return response
            
        except Exception as e:
            log_error(f"获取识别结果失败: {e}", "DEALER")
            return {
                'type': 'recognition_result',
                'status': 'error',
                'error': f'获取识别结果失败: {str(e)}',
                'timestamp': get_timestamp(),
                'connection_id': connection_id
            }
    
    def _handle_connection_test(self, websocket, connection_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理连接测试"""
        test_data = message.get('test_data', 'no data')
        
        return {
            'type': 'connection_test_response',
            'status': 'success',
            'message': '连接测试成功',
            'echo_data': test_data,
            'connection_id': connection_id,
            'timestamp': get_timestamp()
        }
    
    def _handle_dealer_register(self, websocket, connection_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理荷官注册"""
        try:
            dealer_id = message.get('dealer_id')
            dealer_name = message.get('dealer_name', f'荷官{dealer_id}')
            
            if not dealer_id:
                return {
                    'type': 'dealer_register_response',
                    'status': 'error',
                    'error': '荷官ID不能为空',
                    'timestamp': get_timestamp()
                }
            
            # 更新连接信息，添加荷官ID
            from connection_manager import connection_manager
            with connection_manager.connections_lock:
                if connection_id in connection_manager.active_connections:
                    connection_info = connection_manager.active_connections[connection_id]
                    
                    # 检查是否有其他连接使用了相同的dealer_id
                    old_connection_id = connection_manager.dealer_connections.get(dealer_id)
                    if old_connection_id and old_connection_id != connection_id:
                        if old_connection_id in connection_manager.active_connections:
                            log_warning(f"荷官 {dealer_id} 有重复连接，移除旧连接 {old_connection_id}", "DEALER")
                            connection_manager._remove_connection_internal(old_connection_id, "重复注册")
                    
                    # 更新连接信息
                    connection_info['dealer_id'] = dealer_id
                    connection_info['dealer_name'] = dealer_name
                    connection_manager.dealer_connections[dealer_id] = connection_id
                    
                    log_success(f"荷官注册成功: {dealer_id} ({dealer_name}) - 连接: {connection_id}", "DEALER")
                    
                    return {
                        'type': 'dealer_register_response',
                        'status': 'success',
                        'message': '荷官注册成功',
                        'dealer_id': dealer_id,
                        'dealer_name': dealer_name,
                        'connection_id': connection_id,
                        'timestamp': get_timestamp()
                    }
                else:
                    return {
                        'type': 'dealer_register_response',
                        'status': 'error',
                        'error': '连接不存在',
                        'timestamp': get_timestamp()
                    }
            
        except Exception as e:
            log_error(f"荷官注册失败: {e}", "DEALER")
            return {
                'type': 'dealer_register_response',
                'status': 'error',
                'error': f'注册失败: {str(e)}',
                'timestamp': get_timestamp()
            }
    
    def _handle_dealer_heartbeat(self, websocket, connection_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理荷官心跳"""
        dealer_id = message.get('dealer_id')
        
        # 更新心跳时间
        heartbeat_updated = update_heartbeat(connection_id)
        
        return {
            'type': 'dealer_heartbeat_response',
            'status': 'success' if heartbeat_updated else 'warning',
            'message': '心跳更新成功' if heartbeat_updated else '心跳更新失败',
            'dealer_id': dealer_id,
            'connection_id': connection_id,
            'timestamp': get_timestamp()
        }
    
    def _handle_get_system_status(self, websocket, connection_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取系统状态请求"""
        try:
            # 获取连接统计
            from connection_manager import get_connection_stats
            conn_stats = get_connection_stats()
            
            # 获取所有连接信息
            all_connections = get_all_connections()
            
            system_status = {
                'server_time': get_timestamp(),
                'connection_stats': conn_stats['data'] if conn_stats['status'] == 'success' else {},
                'active_connections': len(all_connections),
                'dealers_online': len([conn for conn in all_connections if conn.get('dealer_id')]),
                'system_health': 'healthy'
            }
            
            return {
                'type': 'system_status_response',
                'status': 'success',
                'data': system_status,
                'timestamp': get_timestamp(),
                'connection_id': connection_id
            }
            
        except Exception as e:
            log_error(f"获取系统状态失败: {e}", "DEALER")
            return {
                'type': 'system_status_response',
                'status': 'error',
                'error': f'获取系统状态失败: {str(e)}',
                'timestamp': get_timestamp(),
                'connection_id': connection_id
            }
    
    def _send_message(self, websocket, message: Dict[str, Any]) -> bool:
        """
        发送消息到WebSocket
        
        Args:
            websocket: WebSocket连接对象
            message: 要发送的消息
            
        Returns:
            发送是否成功
        """
        try:
            message_json = json.dumps(message, ensure_ascii=False)
            # 这里需要根据实际的WebSocket库来实现
            # websocket.send(message_json)
            # 暂时只记录日志
            log_info(f"发送消息: {message.get('type', 'unknown')} ({len(message_json)} bytes)", "DEALER")
            return True
            
        except Exception as e:
            log_error(f"发送消息失败: {e}", "DEALER")
            return False
    
    def push_recognition_update(self, dealer_id: str = None) -> Dict[str, Any]:
        """
        推送识别结果更新
        
        Args:
            dealer_id: 指定荷官ID，如果为None则推送给所有荷官
            
        Returns:
            推送结果
        """
        try:
            # 获取最新识别结果
            recognition_result = format_for_dealer(include_metadata=True)
            
            if recognition_result['status'] != 'success':
                return format_error_response("获取识别结果失败", "GET_RECOGNITION_FAILED")
            
            # 构建推送消息
            push_message = {
                'type': 'recognition_update',
                'data': recognition_result['data'],
                'timestamp': get_timestamp(),
                'push_type': 'automatic'
            }
            
            if dealer_id:
                # 推送给指定荷官
                result = send_to_dealer(dealer_id, push_message)
                log_info(f"推送识别更新给荷官: {dealer_id}", "DEALER")
                return result
            else:
                # 推送给所有在线荷官
                all_connections = get_all_connections()
                dealer_connections = [conn for conn in all_connections if conn.get('dealer_id')]
                
                success_count = 0
                error_count = 0
                
                for conn in dealer_connections:
                    dealer_id = conn['dealer_id']
                    result = send_to_dealer(dealer_id, push_message)
                    
                    if result['status'] == 'success':
                        success_count += 1
                    else:
                        error_count += 1
                
                log_info(f"推送识别更新完成: 成功 {success_count}, 失败 {error_count}", "DEALER")
                
                return format_success_response(
                    "识别结果推送完成",
                    data={
                        'success_count': success_count,
                        'error_count': error_count,
                        'total_dealers': len(dealer_connections)
                    }
                )
                
        except Exception as e:
            log_error(f"推送识别更新失败: {e}", "DEALER")
            return format_error_response(f"推送失败: {str(e)}", "PUSH_UPDATE_ERROR")
    
    def get_online_dealers(self) -> Dict[str, Any]:
        """获取在线荷官列表"""
        try:
            all_connections = get_all_connections()
            dealers = []
            
            for conn in all_connections:
                if conn.get('dealer_id'):
                    dealer_info = {
                        'dealer_id': conn['dealer_id'],
                        'dealer_name': conn.get('dealer_name', f"荷官{conn['dealer_id']}"),
                        'connection_id': conn['connection_id'],
                        'connected_at': conn['connected_at'],
                        'last_heartbeat': conn['last_heartbeat'],
                        'status': conn['status'],
                        'message_count': conn['message_count'],
                        'client_info': conn.get('client_info', {})
                    }
                    dealers.append(dealer_info)
            
            return format_success_response(
                f"获取在线荷官成功 ({len(dealers)} 个)",
                data={
                    'dealers': dealers,
                    'total_count': len(dealers)
                }
            )
            
        except Exception as e:
            log_error(f"获取在线荷官失败: {e}", "DEALER")
            return format_error_response(f"获取在线荷官失败: {str(e)}", "GET_DEALERS_ERROR")

# 创建全局实例
dealer_websocket_handler = DealerWebSocketHandler()

# 导出主要函数
def handle_new_connection(websocket, remote_address: str) -> Dict[str, Any]:
    """处理新连接"""
    return dealer_websocket_handler.handle_new_connection(websocket, remote_address)

def handle_message(websocket, connection_id: str, message_text: str) -> Dict[str, Any]:
    """处理消息"""
    return dealer_websocket_handler.handle_message(websocket, connection_id, message_text)

def handle_connection_closed(connection_id: str, reason: str = "客户端断开") -> Dict[str, Any]:
    """处理连接关闭"""
    return dealer_websocket_handler.handle_connection_closed(connection_id, reason)

def push_recognition_update(dealer_id: str = None) -> Dict[str, Any]:
    """推送识别结果更新"""
    return dealer_websocket_handler.push_recognition_update(dealer_id)

def get_online_dealers() -> Dict[str, Any]:
    """获取在线荷官"""
    return dealer_websocket_handler.get_online_dealers()

if __name__ == "__main__":
    # 测试荷官WebSocket处理器
    print("🧪 测试荷官WebSocket处理器")
    
    # 模拟WebSocket连接
    class MockWebSocket:
        def __init__(self, name):
            self.name = name
            self.messages = []
        
        def send(self, message):
            self.messages.append(message)
            print(f"[{self.name}] 发送: {message}")
    
    # 测试新连接
    mock_ws = MockWebSocket("test_dealer")
    conn_result = handle_new_connection(mock_ws, "192.168.1.100:12345")
    print(f"新连接: {conn_result['status']}")
    
    if conn_result['status'] == 'success':
        connection_id = conn_result['data']['connection_id']
        
        # 测试荷官注册
        register_msg = json.dumps({
            'type': 'dealer_register',
            'dealer_id': 'dealer_001',
            'dealer_name': '测试荷官'
        })
        
        register_result = handle_message(mock_ws, connection_id, register_msg)
        print(f"荷官注册: {register_result['status']}")
        
        # 测试获取识别结果
        get_result_msg = json.dumps({
            'type': 'get_recognition_result'
        })
        
        result_response = handle_message(mock_ws, connection_id, get_result_msg)
        print(f"获取识别结果: {result_response['status']}")
        
        # 测试ping消息
        ping_msg = json.dumps({
            'type': 'ping',
            'timestamp': get_timestamp()
        })
        
        ping_result = handle_message(mock_ws, connection_id, ping_msg)
        print(f"Ping测试: {ping_result['status']}")
        
        # 测试获取在线荷官
        online_dealers = get_online_dealers()
        print(f"在线荷官: {online_dealers['status']}")
        if online_dealers['status'] == 'success':
            print(f"   荷官数量: {online_dealers['data']['total_count']}")
        
        # 测试推送识别更新
        push_result = push_recognition_update("dealer_001")
        print(f"推送更新: {push_result['status']}")
        
        # 测试连接关闭
        close_result = handle_connection_closed(connection_id, "测试完成")
        print(f"关闭连接: {close_result['status']}")
    
    print("✅ 荷官WebSocket处理器测试完成")