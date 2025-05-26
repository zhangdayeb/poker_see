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

# 导入所有业务模块
import config_manager
import mark_manager
import photo_controller
import recognition_manager
import static_handler

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
                '/api/system/info': self._handle_get_system_info
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
                '/api/photos/cleanup': self._handle_cleanup_photos
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
        return config_manager.get_all_cameras()
    
    def _handle_get_camera_by_id(self, path_params: Dict[str, str], **kwargs) -> Dict[str, Any]:
        """获取指定摄像头配置"""
        camera_id = path_params.get('id')
        if not camera_id:
            return format_error_response("摄像头ID不能为空", "MISSING_CAMERA_ID")
        
        return config_manager.get_camera_by_id(camera_id)
    
    def _handle_get_recognition_result(self, **kwargs) -> Dict[str, Any]:
        """获取最新识别结果"""
        return recognition_manager.get_latest_recognition()
    
    def _handle_get_photo_status(self, **kwargs) -> Dict[str, Any]:
        """获取所有摄像头拍照状态"""
        return photo_controller.get_photo_status()
    
    def _handle_get_camera_photo_status(self, path_params: Dict[str, str], **kwargs) -> Dict[str, Any]:
        """获取指定摄像头拍照状态"""
        camera_id = path_params.get('id')
        return photo_controller.get_photo_status(camera_id)
    
    def _handle_list_photos(self, query_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """列出所有图片"""
        limit = int(query_params.get('limit', [20])[0]) if 'limit' in query_params else 20
        return photo_controller.list_photos(limit=limit)
    
    def _handle_list_camera_photos(self, path_params: Dict[str, str], 
                                  query_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """列出指定摄像头的图片"""
        camera_id = path_params.get('id')
        limit = int(query_params.get('limit', [10])[0]) if 'limit' in query_params else 10
        return photo_controller.list_photos(camera_id, limit)
    
    def _handle_get_mark_statistics(self, query_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """获取标记统计信息"""
        camera_id = query_params.get('camera_id', [None])[0] if 'camera_id' in query_params else None
        return mark_manager.get_mark_statistics(camera_id)
    
    def _handle_get_config_status(self, **kwargs) -> Dict[str, Any]:
        """获取配置状态"""
        return config_manager.get_config_status()
    
    def _handle_get_system_info(self, **kwargs) -> Dict[str, Any]:
        """获取系统信息"""
        return format_success_response(
            "系统信息获取成功",
            data={
                'system_name': '扑克识别系统',
                'version': '2.0',
                'api_version': '1.0',
                'timestamp': get_timestamp(),
                'available_endpoints': {
                    'GET': list(self.routes['GET'].keys()),
                    'POST': list(self.routes['POST'].keys()),
                    'PUT': list(self.routes['PUT'].keys()),
                    'DELETE': list(self.routes['DELETE'].keys())
                }
            }
        )
    
    # ==================== POST 路由处理器 ====================
    
    def _handle_post_recognition_result(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """接收识别结果"""
        if not request_data:
            return format_error_response("请求数据不能为空", "EMPTY_REQUEST_DATA")
        
        return recognition_manager.receive_recognition_data(request_data)
    
    def _handle_take_photo(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """拍照"""
        if not request_data:
            return format_error_response("请求数据不能为空", "EMPTY_REQUEST_DATA")
        
        camera_id = request_data.get('camera_id')
        if not camera_id:
            return format_error_response("摄像头ID不能为空", "MISSING_CAMERA_ID")
        
        options = request_data.get('options', {})
        return photo_controller.take_photo_by_id(camera_id, options)
    
    def _handle_save_camera_marks(self, path_params: Dict[str, str], 
                                 request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """保存摄像头标记数据"""
        camera_id = path_params.get('id')
        if not camera_id:
            return format_error_response("摄像头ID不能为空", "MISSING_CAMERA_ID")
        
        if not request_data:
            return format_error_response("标记数据不能为空", "EMPTY_MARKS_DATA")
        
        return mark_manager.save_camera_marks(camera_id, request_data)
    
    def _handle_batch_save_marks(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """批量保存标记数据"""
        if not request_data:
            return format_error_response("批量数据不能为空", "EMPTY_BATCH_DATA")
        
        return mark_manager.batch_save_marks(request_data)
    
    def _handle_add_camera(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """添加摄像头"""
        if not request_data:
            return format_error_response("摄像头数据不能为空", "EMPTY_CAMERA_DATA")
        
        return config_manager.add_camera(request_data)
    
    def _handle_update_camera(self, path_params: Dict[str, str], 
                             request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """更新摄像头信息"""
        camera_id = path_params.get('id')
        if not camera_id:
            return format_error_response("摄像头ID不能为空", "MISSING_CAMERA_ID")
        
        if not request_data:
            return format_error_response("更新数据不能为空", "EMPTY_UPDATE_DATA")
        
        return config_manager.update_camera(camera_id, request_data)
    
    def _handle_delete_camera(self, path_params: Dict[str, str], **kwargs) -> Dict[str, Any]:
        """删除摄像头"""
        camera_id = path_params.get('id')
        if not camera_id:
            return format_error_response("摄像头ID不能为空", "MISSING_CAMERA_ID")
        
        return config_manager.delete_camera(camera_id)
    
    def _handle_validate_marks(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """验证标记数据"""
        if not request_data:
            return format_error_response("标记数据不能为空", "EMPTY_MARKS_DATA")
        
        return mark_manager.validate_marks_data(request_data)
    
    def _handle_cleanup_photos(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """清理图片文件"""
        keep_count = request_data.get('keep_count', 50) if request_data else 50
        camera_id = request_data.get('camera_id') if request_data else None
        
        return photo_controller.cleanup_old_photos(keep_count, camera_id)
    
    def get_api_documentation(self) -> Dict[str, Any]:
        """获取API文档"""
        docs = {
            'api_info': {
                'name': '扑克识别系统 API',
                'version': '1.0',
                'description': '提供摄像头配置、标记管理、拍照控制和识别结果处理的完整API接口'
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
            
            # POST接口
            'POST /api/recognition_result': '接收识别结果数据',
            'POST /api/take_photo': '摄像头拍照',
            'POST /api/camera/{id}/marks': '保存摄像头标记数据',
            'POST /api/save_marks': '批量保存标记数据',
            'POST /api/camera/add': '添加新摄像头',
            'POST /api/marks/validate': '验证标记数据格式',
            'POST /api/photos/cleanup': '清理旧图片文件',
            
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
    print("🧪 测试API处理器")
    
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