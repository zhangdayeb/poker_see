#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API统一处理模块 - 整合所有业务模块，提供RESTful API接口
功能:
1. API路由定义和分发
2. 请求参数验证和处理
3. 响应格式统一
4. 错误处理和日志记录
5. 集成所有业务模块
6. WebSocket推送功能API接口
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
from typing import Dict, Any, Optional, Callable
from urllib.parse import urlparse, parse_qs
from src.core.utils import (
    parse_json_string, format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)

# 安全导入所有业务模块
try:
    from src.core import config_manager
    config_manager_available = True
except ImportError as e:
    print(f"Warning: Could not import config_manager: {e}")
    config_manager_available = False

try:
    from src.core import mark_manager
    mark_manager_available = True
except ImportError as e:
    print(f"Warning: Could not import mark_manager: {e}")
    mark_manager_available = False

try:
    from src.processors import photo_controller
    photo_controller_available = True
except ImportError as e:
    print(f"Warning: Could not import photo_controller: {e}")
    photo_controller_available = False

try:
    from src.core import recognition_manager
    recognition_manager_available = True
except ImportError as e:
    print(f"Warning: Could not import recognition_manager: {e}")
    recognition_manager_available = False

try:
    from src.servers import static_handler
    static_handler_available = True
except ImportError as e:
    print(f"Warning: Could not import static_handler: {e}")
    static_handler_available = False

try:
    from src.clients import websocket_client
    websocket_client_available = True
except ImportError as e:
    print(f"Warning: Could not import websocket_client: {e}")
    websocket_client_available = False

# 创建安全的模块接口
class SafeModuleInterface:
    """安全的模块接口，处理模块不可用的情况"""
    
    @staticmethod
    def safe_call(module_available, func_name, *args, **kwargs):
        """安全调用模块函数"""
        if not module_available:
            return format_error_response(
                f"模块不可用: {func_name}",
                "MODULE_NOT_AVAILABLE"
            )
        
        try:
            # 根据函数名调用对应的模块函数
            if func_name == 'get_all_cameras' and config_manager_available:
                return config_manager.get_all_cameras()
            elif func_name == 'get_camera_by_id' and config_manager_available:
                return config_manager.get_camera_by_id(*args)
            elif func_name == 'update_camera' and config_manager_available:
                return config_manager.update_camera(*args, **kwargs)
            elif func_name == 'add_camera' and config_manager_available:
                return config_manager.add_camera(*args)
            elif func_name == 'delete_camera' and config_manager_available:
                return config_manager.delete_camera(*args)
            elif func_name == 'get_config_status' and config_manager_available:
                return config_manager.get_config_status()
            
            elif func_name == 'save_camera_marks' and mark_manager_available:
                return mark_manager.save_camera_marks(*args)
            elif func_name == 'batch_save_marks' and mark_manager_available:
                return mark_manager.batch_save_marks(*args)
            elif func_name == 'validate_marks_data' and mark_manager_available:
                return mark_manager.validate_marks_data(*args)
            elif func_name == 'get_mark_statistics' and mark_manager_available:
                return mark_manager.get_mark_statistics(*args)
            
            elif func_name == 'take_photo_by_id' and photo_controller_available:
                return photo_controller.take_photo_by_id(*args, **kwargs)
            elif func_name == 'get_photo_status' and photo_controller_available:
                return photo_controller.get_photo_status(*args)
            elif func_name == 'list_photos' and photo_controller_available:
                return photo_controller.list_photos(*args, **kwargs)
            elif func_name == 'cleanup_old_photos' and photo_controller_available:
                return photo_controller.cleanup_old_photos(*args, **kwargs)
            
            elif func_name == 'get_latest_recognition' and recognition_manager_available:
                return recognition_manager.get_latest_recognition()
            elif func_name == 'receive_recognition_data' and recognition_manager_available:
                return recognition_manager.receive_recognition_data(*args)
            elif func_name == 'manual_push_recognition_result' and recognition_manager_available:
                return recognition_manager.manual_push_recognition_result(*args)
            elif func_name == 'update_push_config' and recognition_manager_available:
                return recognition_manager.update_push_config(*args)
            elif func_name == 'get_push_config' and recognition_manager_available:
                return recognition_manager.get_push_config()
            elif func_name == 'get_push_status' and recognition_manager_available:
                return recognition_manager.get_push_status()
            elif func_name == 'get_system_statistics' and recognition_manager_available:
                return recognition_manager.get_system_statistics()
            elif func_name == 'cleanup_old_history' and recognition_manager_available:
                return recognition_manager.cleanup_old_history(*args)
            
            else:
                return format_error_response(
                    f"未知函数或模块不可用: {func_name}",
                    "UNKNOWN_FUNCTION"
                )
                
        except Exception as e:
            log_error(f"调用模块函数失败 {func_name}: {e}", "API")
            return format_error_response(
                f"函数调用失败: {str(e)}",
                "FUNCTION_CALL_ERROR"
            )

safe_interface = SafeModuleInterface()

class APIHandler:
    """API处理器 - 统一的API接口管理"""
    
    def __init__(self):
        """初始化API处理器"""
        # API路由表
        self.routes = {
            # GET路由
            'GET': {
                '/api/cameras': self._handle_get_all_cameras,
                '/api/camera/{id}': self._handle_get_camera_by_id,
                '/api/recognition_result': self._handle_get_recognition_result,
                '/api/photo/status': self._handle_get_photo_status,
                '/api/photo/status/{id}': self._handle_get_camera_photo_status,
                '/api/photos': self._handle_list_photos,
                '/api/photos/{id}': self._handle_list_camera_photos,
                '/api/marks/statistics': self._handle_get_mark_statistics,
                '/api/config/status': self._handle_get_config_status,
                '/api/system/info': self._handle_get_system_info,
                '/api/system/statistics': self._handle_get_system_statistics,
                # WebSocket推送相关GET接口
                '/api/push/config': self._handle_get_push_config,
                '/api/push/status': self._handle_get_push_status,
                '/api/push/clients/websocket/status': self._handle_get_websocket_client_status,
            },
            # POST路由
            'POST': {
                '/api/recognition_result': self._handle_post_recognition_result,
                '/api/take_photo': self._handle_take_photo,
                '/api/camera/{id}/marks': self._handle_save_camera_marks,
                '/api/save_marks': self._handle_batch_save_marks,
                '/api/camera/add': self._handle_add_camera,
                '/api/camera/{id}/update': self._handle_update_camera,
                '/api/marks/validate': self._handle_validate_marks,
                '/api/photos/cleanup': self._handle_cleanup_photos,
                '/api/history/cleanup': self._handle_cleanup_history,
                # WebSocket推送相关POST接口
                '/api/push/config': self._handle_update_push_config,
                '/api/push/manual': self._handle_manual_push,
                '/api/push/clients/websocket/start': self._handle_start_websocket_client,
                '/api/push/clients/websocket/stop': self._handle_stop_websocket_client,
                '/api/push/clients/websocket/heartbeat': self._handle_websocket_heartbeat,
            },
            # PUT路由
            'PUT': {
                '/api/camera/{id}': self._handle_update_camera
            },
            # DELETE路由
            'DELETE': {
                '/api/camera/{id}': self._handle_delete_camera
            }
        }
        
        log_info("API处理器初始化完成", "API")
    
    def handle_request(self, method: str, path: str, query_params: Dict[str, Any] = None, 
                      post_data: bytes = None) -> Dict[str, Any]:
        """
        处理API请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            path: 请求路径
            query_params: 查询参数
            post_data: POST数据
            
        Returns:
            API响应
        """
        try:
            # 记录请求
            log_info(f"{method} {path}", "API")
            
            # 查找路由处理器
            handler = self._find_route_handler(method, path)
            
            if not handler:
                return format_error_response(
                    f"API接口不存在: {method} {path}",
                    "API_NOT_FOUND"
                )
            
            # 解析路径参数
            path_params = self._extract_path_params(handler['pattern'], path)
            
            # 处理POST数据
            request_data = None
            if post_data and method in ['POST', 'PUT']:
                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    return format_error_response(
                        f"请求数据格式错误: {str(e)}",
                        "INVALID_REQUEST_DATA"
                    )
            
            # 调用处理器
            return handler['func'](
                path_params=path_params,
                query_params=query_params or {},
                request_data=request_data
            )
            
        except Exception as e:
            log_error(f"API请求处理失败 {method} {path}: {e}", "API")
            return format_error_response(
                f"服务器内部错误: {str(e)}",
                "INTERNAL_SERVER_ERROR"
            )
    
    def _find_route_handler(self, method: str, path: str) -> Optional[Dict[str, Any]]:
        """查找路由处理器"""
        if method not in self.routes:
            return None
        
        method_routes = self.routes[method]
        
        # 精确匹配
        if path in method_routes:
            return {
                'func': method_routes[path],
                'pattern': path
            }
        
        # 参数匹配 (例如 /api/camera/{id})
        for pattern, handler in method_routes.items():
            if self._match_pattern(pattern, path):
                return {
                    'func': handler,
                    'pattern': pattern
                }
        
        return None
    
    def _match_pattern(self, pattern: str, path: str) -> bool:
        """匹配路由模式"""
        pattern_parts = pattern.split('/')
        path_parts = path.split('/')
        
        if len(pattern_parts) != len(path_parts):
            return False
        
        for pattern_part, path_part in zip(pattern_parts, path_parts):
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                # 参数占位符，跳过检查
                continue
            elif pattern_part != path_part:
                return False
        
        return True
    
    def _extract_path_params(self, pattern: str, path: str) -> Dict[str, str]:
        """提取路径参数"""
        params = {}
        pattern_parts = pattern.split('/')
        path_parts = path.split('/')
        
        for pattern_part, path_part in zip(pattern_parts, path_parts):
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                param_name = pattern_part[1:-1]  # 移除大括号
                params[param_name] = path_part
        
        return params
    
    # ==================== GET 路由处理器 ====================
    
    def _handle_get_all_cameras(self, **kwargs) -> Dict[str, Any]:
        """获取所有摄像头配置"""
        return safe_interface.safe_call(config_manager_available, 'get_all_cameras')
    
    def _handle_get_camera_by_id(self, path_params: Dict[str, str], **kwargs) -> Dict[str, Any]:
        """获取指定摄像头配置"""
        camera_id = path_params.get('id')
        if not camera_id:
            return format_error_response("摄像头ID不能为空", "MISSING_CAMERA_ID")
        
        return safe_interface.safe_call(config_manager_available, 'get_camera_by_id', camera_id)
    
    def _handle_get_recognition_result(self, **kwargs) -> Dict[str, Any]:
        """获取最新识别结果"""
        return safe_interface.safe_call(recognition_manager_available, 'get_latest_recognition')
    
    def _handle_get_photo_status(self, **kwargs) -> Dict[str, Any]:
        """获取所有摄像头拍照状态"""
        return safe_interface.safe_call(photo_controller_available, 'get_photo_status')
    
    def _handle_get_camera_photo_status(self, path_params: Dict[str, str], **kwargs) -> Dict[str, Any]:
        """获取指定摄像头拍照状态"""
        camera_id = path_params.get('id')
        return safe_interface.safe_call(photo_controller_available, 'get_photo_status', camera_id)
    
    def _handle_list_photos(self, query_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """列出所有图片"""
        limit = int(query_params.get('limit', [20])[0]) if 'limit' in query_params else 20
        return safe_interface.safe_call(photo_controller_available, 'list_photos', limit=limit)
    
    def _handle_list_camera_photos(self, path_params: Dict[str, str], 
                                  query_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """列出指定摄像头的图片"""
        camera_id = path_params.get('id')
        limit = int(query_params.get('limit', [10])[0]) if 'limit' in query_params else 10
        return safe_interface.safe_call(photo_controller_available, 'list_photos', camera_id, limit=limit)
    
    def _handle_get_mark_statistics(self, query_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """获取标记统计信息"""
        camera_id = query_params.get('camera_id', [None])[0] if 'camera_id' in query_params else None
        return safe_interface.safe_call(mark_manager_available, 'get_mark_statistics', camera_id)
    
    def _handle_get_config_status(self, **kwargs) -> Dict[str, Any]:
        """获取配置状态"""
        return safe_interface.safe_call(config_manager_available, 'get_config_status')
    
    def _handle_get_system_info(self, **kwargs) -> Dict[str, Any]:
        """获取系统信息"""
        return format_success_response(
            "系统信息获取成功",
            data={
                'system_name': '扑克识别系统',
                'version': '2.1',
                'api_version': '1.0',
                'timestamp': get_timestamp(),
                'module_status': {
                    'config_manager': config_manager_available,
                    'mark_manager': mark_manager_available,
                    'photo_controller': photo_controller_available,
                    'recognition_manager': recognition_manager_available,
                    'static_handler': static_handler_available,
                    'websocket_client': websocket_client_available
                },
                'available_endpoints': {
                    'GET': list(self.routes['GET'].keys()),
                    'POST': list(self.routes['POST'].keys()),
                    'PUT': list(self.routes['PUT'].keys()),
                    'DELETE': list(self.routes['DELETE'].keys())
                }
            }
        )
    
    def _handle_get_system_statistics(self, **kwargs) -> Dict[str, Any]:
        """获取系统统计信息"""
        return safe_interface.safe_call(recognition_manager_available, 'get_system_statistics')
    
    # ==================== WebSocket推送相关GET路由处理器 ====================
    
    def _handle_get_push_config(self, **kwargs) -> Dict[str, Any]:
        """获取推送配置"""
        return safe_interface.safe_call(recognition_manager_available, 'get_push_config')
    
    def _handle_get_push_status(self, **kwargs) -> Dict[str, Any]:
        """获取推送状态"""
        return safe_interface.safe_call(recognition_manager_available, 'get_push_status')
    
    def _handle_get_websocket_client_status(self, **kwargs) -> Dict[str, Any]:
        """获取WebSocket客户端状态"""
        if not websocket_client_available:
            return format_error_response("WebSocket客户端模块不可用", "WEBSOCKET_CLIENT_NOT_AVAILABLE")
        
        try:
            from src.clients.websocket_client import get_push_client_status
            return get_push_client_status()
        except Exception as e:
            return format_error_response(f"获取WebSocket客户端状态失败: {str(e)}", "GET_WS_STATUS_ERROR")
    
    # ==================== POST 路由处理器 ====================
    
    def _handle_post_recognition_result(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """接收识别结果"""
        if not request_data:
            return format_error_response("请求数据不能为空", "EMPTY_REQUEST_DATA")
        
        return safe_interface.safe_call(recognition_manager_available, 'receive_recognition_data', request_data)
    
    def _handle_take_photo(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """拍照"""
        if not request_data:
            return format_error_response("请求数据不能为空", "EMPTY_REQUEST_DATA")
        
        camera_id = request_data.get('camera_id')
        if not camera_id:
            return format_error_response("摄像头ID不能为空", "MISSING_CAMERA_ID")
        
        options = request_data.get('options', {})
        return safe_interface.safe_call(photo_controller_available, 'take_photo_by_id', camera_id, options=options)
    
    def _handle_save_camera_marks(self, path_params: Dict[str, str], 
                                 request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """保存摄像头标记数据"""
        camera_id = path_params.get('id')
        if not camera_id:
            return format_error_response("摄像头ID不能为空", "MISSING_CAMERA_ID")
        
        if not request_data:
            return format_error_response("标记数据不能为空", "EMPTY_MARKS_DATA")
        
        return safe_interface.safe_call(mark_manager_available, 'save_camera_marks', camera_id, request_data)
    
    def _handle_batch_save_marks(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """批量保存标记数据"""
        if not request_data:
            return format_error_response("批量数据不能为空", "EMPTY_BATCH_DATA")
        
        return safe_interface.safe_call(mark_manager_available, 'batch_save_marks', request_data)
    
    def _handle_add_camera(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """添加摄像头"""
        if not request_data:
            return format_error_response("摄像头数据不能为空", "EMPTY_CAMERA_DATA")
        
        return safe_interface.safe_call(config_manager_available, 'add_camera', request_data)
    
    def _handle_update_camera(self, path_params: Dict[str, str], 
                             request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """更新摄像头信息"""
        camera_id = path_params.get('id')
        if not camera_id:
            return format_error_response("摄像头ID不能为空", "MISSING_CAMERA_ID")
        
        if not request_data:
            return format_error_response("更新数据不能为空", "EMPTY_UPDATE_DATA")
        
        return safe_interface.safe_call(config_manager_available, 'update_camera', camera_id, request_data)
    
    def _handle_delete_camera(self, path_params: Dict[str, str], **kwargs) -> Dict[str, Any]:
        """删除摄像头"""
        camera_id = path_params.get('id')
        if not camera_id:
            return format_error_response("摄像头ID不能为空", "MISSING_CAMERA_ID")
        
        return safe_interface.safe_call(config_manager_available, 'delete_camera', camera_id)
    
    def _handle_validate_marks(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """验证标记数据"""
        if not request_data:
            return format_error_response("标记数据不能为空", "EMPTY_MARKS_DATA")
        
        return safe_interface.safe_call(mark_manager_available, 'validate_marks_data', request_data)
    
    def _handle_cleanup_photos(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """清理图片文件"""
        keep_count = request_data.get('keep_count', 50) if request_data else 50
        camera_id = request_data.get('camera_id') if request_data else None
        
        return safe_interface.safe_call(photo_controller_available, 'cleanup_old_photos', keep_count, camera_id)
    
    def _handle_cleanup_history(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """清理历史记录"""
        keep_count = request_data.get('keep_count', 50) if request_data else 50
        
        return safe_interface.safe_call(recognition_manager_available, 'cleanup_old_history', keep_count)
    
    # ==================== WebSocket推送相关POST路由处理器 ====================
    
    def _handle_update_push_config(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """更新推送配置"""
        if not request_data:
            return format_error_response("推送配置数据不能为空", "EMPTY_CONFIG_DATA")
        
        return safe_interface.safe_call(recognition_manager_available, 'update_push_config', request_data)
    
    def _handle_manual_push(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """手动推送识别结果"""
        push_type = request_data.get('push_type', 'websocket') if request_data else 'websocket'
        camera_id = request_data.get('camera_id') if request_data else None
        
        return safe_interface.safe_call(recognition_manager_available, 'manual_push_recognition_result', push_type, camera_id)
    
    def _handle_start_websocket_client(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """启动WebSocket推送客户端"""
        if not websocket_client_available:
            return format_error_response("WebSocket客户端模块不可用", "WEBSOCKET_CLIENT_NOT_AVAILABLE")
        
        try:
            from src.clients.websocket_client import start_push_client
            
            server_url = request_data.get('server_url', 'ws://localhost:8001') if request_data else 'ws://localhost:8001'
            client_id = request_data.get('client_id', 'python_client_001') if request_data else 'python_client_001'
            
            return start_push_client(server_url, client_id)
        except Exception as e:
            return format_error_response(f"启动WebSocket客户端失败: {str(e)}", "START_WS_CLIENT_ERROR")
    
    def _handle_stop_websocket_client(self, **kwargs) -> Dict[str, Any]:
        """停止WebSocket推送客户端"""
        if not websocket_client_available:
            return format_error_response("WebSocket客户端模块不可用", "WEBSOCKET_CLIENT_NOT_AVAILABLE")
        
        try:
            from src.clients.websocket_client import stop_push_client
            return stop_push_client()
        except Exception as e:
            return format_error_response(f"停止WebSocket客户端失败: {str(e)}", "STOP_WS_CLIENT_ERROR")
    
    def _handle_websocket_heartbeat(self, **kwargs) -> Dict[str, Any]:
        """发送WebSocket心跳"""
        if not websocket_client_available:
            return format_error_response("WebSocket客户端模块不可用", "WEBSOCKET_CLIENT_NOT_AVAILABLE")
        
        try:
            from src.clients.websocket_client import push_client
            if push_client:
                return push_client.send_heartbeat()
            else:
                return format_error_response("WebSocket客户端未初始化", "WS_CLIENT_NOT_INITIALIZED")
        except Exception as e:
            return format_error_response(f"发送心跳失败: {str(e)}", "HEARTBEAT_ERROR")
    
    def get_api_documentation(self) -> Dict[str, Any]:
        """获取API文档"""
        docs = {
            'api_info': {
                'name': '扑克识别系统 API',
                'version': '1.0',
                'description': '提供摄像头配置、标记管理、拍照控制、识别结果处理和WebSocket推送功能的完整API接口'
            },
            'endpoints': {}
        }
        
        # 生成API文档
        endpoint_docs = {
            # GET接口
            'GET /api/cameras': '获取所有摄像头配置',
            'GET /api/camera/{id}': '获取指定摄像头配置',
            'GET /api/recognition_result': '获取最新识别结果',
            'GET /api/photo/status': '获取所有摄像头拍照状态',
            'GET /api/photo/status/{id}': '获取指定摄像头拍照状态',
            'GET /api/photos': '列出所有图片文件',
            'GET /api/photos/{id}': '列出指定摄像头的图片',
            'GET /api/marks/statistics': '获取标记统计信息',
            'GET /api/config/status': '获取配置文件状态',
            'GET /api/system/info': '获取系统信息',
            'GET /api/system/statistics': '获取系统统计信息',
            
            # WebSocket推送相关GET接口
            'GET /api/push/config': '获取推送配置',
            'GET /api/push/status': '获取推送状态',
            'GET /api/push/clients/websocket/status': '获取WebSocket客户端状态',
            
            # POST接口
            'POST /api/recognition_result': '接收识别结果数据',
            'POST /api/take_photo': '摄像头拍照',
            'POST /api/camera/{id}/marks': '保存摄像头标记数据',
            'POST /api/save_marks': '批量保存标记数据',
            'POST /api/camera/add': '添加新摄像头',
            'POST /api/marks/validate': '验证标记数据格式',
            'POST /api/photos/cleanup': '清理旧图片文件',
            'POST /api/history/cleanup': '清理识别历史记录',
            
            # WebSocket推送相关POST接口
            'POST /api/push/config': '更新推送配置',
            'POST /api/push/manual': '手动推送识别结果',
            'POST /api/push/clients/websocket/start': '启动WebSocket推送客户端',
            'POST /api/push/clients/websocket/stop': '停止WebSocket推送客户端',
            'POST /api/push/clients/websocket/heartbeat': '发送WebSocket心跳',
            
            # PUT接口
            'PUT /api/camera/{id}': '更新摄像头信息',
            
            # DELETE接口
            'DELETE /api/camera/{id}': '删除摄像头配置'
        }
        
        docs['endpoints'] = endpoint_docs
        
        return format_success_response(
            "API文档获取成功",
            data=docs
        )


# 创建全局实例
api_handler = APIHandler()

# 导出主要函数
def handle_api_request(method: str, path: str, query_params: Dict[str, Any] = None, 
                      post_data: bytes = None) -> Dict[str, Any]:
    """处理API请求"""
    return api_handler.handle_request(method, path, query_params, post_data)

def get_api_documentation() -> Dict[str, Any]:
    """获取API文档"""
    return api_handler.get_api_documentation()

def list_api_routes() -> Dict[str, Any]:
    """列出所有API路由"""
    return format_success_response(
        "API路由列表获取成功",
        data={
            'routes': api_handler.routes,
            'total_routes': sum(len(routes) for routes in api_handler.routes.values())
        }
    )

if __name__ == "__main__":
    # 测试API处理器
    print("🧪 测试API处理器（WebSocket推送版）")
    
    # 测试GET请求
    print("\n📋 测试GET请求")
    
    # 测试获取所有摄像头
    result = handle_api_request('GET', '/api/cameras')
    print(f"GET /api/cameras: {result['status']}")
    
    # 测试GET单个摄像头
    result = handle_api_request('GET', '/api/camera/001')
    print(f"GET /api/camera/001: {result['status']}")
    
    # 测试系统信息
    result = handle_api_request('GET', '/api/system/info')
    print(f"GET /api/system/info: {result['status']}")
    
    # 测试系统统计
    result = handle_api_request('GET', '/api/system/statistics')
    print(f"GET /api/system/statistics: {result['status']}")
    
    # 测试推送配置
    result = handle_api_request('GET', '/api/push/config')
    print(f"GET /api/push/config: {result['status']}")
    
    # 测试推送状态
    result = handle_api_request('GET', '/api/push/status')
    print(f"GET /api/push/status: {result['status']}")
    
    # 测试WebSocket客户端状态
    result = handle_api_request('GET', '/api/push/clients/websocket/status')
    print(f"GET /api/push/clients/websocket/status: {result['status']}")
    
    # 测试POST请求
    print("\n📤 测试POST请求")
    
    # 测试拍照
    photo_data = json.dumps({'camera_id': '001'}).encode('utf-8')
    result = handle_api_request('POST', '/api/take_photo', post_data=photo_data)
    print(f"POST /api/take_photo: {result['status']}")
    
    # 测试保存标记
    marks_data = json.dumps({
        'marks': {
            'zhuang_1': {'x': 100, 'y': 150, 'width': 60, 'height': 80}
        }
    }).encode('utf-8')
    result = handle_api_request('POST', '/api/camera/001/marks', post_data=marks_data)
    print(f"POST /api/camera/001/marks: {result['status']}")
    
    # 测试手动推送
    push_data = json.dumps({'push_type': 'websocket', 'camera_id': '001'}).encode('utf-8')
    result = handle_api_request('POST', '/api/push/manual', post_data=push_data)
    print(f"POST /api/push/manual: {result['status']}")
    
    # 测试启动WebSocket客户端
    ws_data = json.dumps({
        'server_url': 'ws://localhost:8001',
        'client_id': 'test_client_001'
    }).encode('utf-8')
    result = handle_api_request('POST', '/api/push/clients/websocket/start', post_data=ws_data)
    print(f"POST /api/push/clients/websocket/start: {result['status']}")
    
    # 测试清理历史记录
    cleanup_data = json.dumps({'keep_count': 20}).encode('utf-8')
    result = handle_api_request('POST', '/api/history/cleanup', post_data=cleanup_data)
    print(f"POST /api/history/cleanup: {result['status']}")
    
    # 测试API文档
    print("\n📚 测试API文档")
    docs = get_api_documentation()
    print(f"API文档: {docs['status']}")
    if docs['status'] == 'success':
        print(f"   总计接口数: {len(docs['data']['endpoints'])}")
    
    # 测试路由列表
    routes = list_api_routes()
    print(f"路由列表: {routes['status']}")
    if routes['status'] == 'success':
        print(f"   总计路由数: {routes['data']['total_routes']}")
    
    print("✅ API处理器测试完成")