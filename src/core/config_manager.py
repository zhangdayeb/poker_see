#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块 - 处理camera.json配置文件的读写操作
功能:
1. 读取摄像头配置
2. 更新摄像头配置
3. 管理标记位置数据
4. 配置文件的创建和验证
5. 单个摄像头配置的CRUD操作
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from utils import (
    get_config_dir, safe_json_load, safe_json_dump,
    format_success_response, format_error_response,
    validate_camera_id, validate_mark_position,
    log_info, log_success, log_error, log_warning, get_timestamp
)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config_dir = get_config_dir()
        self.config_file = self.config_dir / "camera.json"
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 如果配置文件不存在，创建默认配置
        if not self.config_file.exists():
            self._create_default_config()
        
        log_info("配置管理器初始化完成", "CONFIG")
    
    def get_all_cameras(self) -> Dict[str, Any]:
        """
        获取所有摄像头配置
        
        Returns:
            所有摄像头配置数据
        """
        try:
            config = safe_json_load(self.config_file, {})
            cameras = config.get('cameras', [])
            
            return format_success_response(
                "获取摄像头配置成功",
                data={
                    'cameras': cameras,
                    'total_cameras': len(cameras)
                }
            )
            
        except Exception as e:
            log_error(f"获取摄像头配置失败: {e}", "CONFIG")
            return format_error_response(f"获取配置失败: {str(e)}", "GET_CONFIG_ERROR")
    
    def get_camera_by_id(self, camera_id: str) -> Dict[str, Any]:
        """
        根据ID获取单个摄像头配置
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            单个摄像头配置
        """
        try:
            if not validate_camera_id(camera_id):
                return format_error_response("摄像头ID格式无效", "INVALID_CAMERA_ID")
            
            config = safe_json_load(self.config_file, {})
            cameras = config.get('cameras', [])
            
            # 查找指定摄像头
            camera = None
            for cam in cameras:
                if cam.get('id') == camera_id:
                    camera = cam
                    break
            
            if not camera:
                return format_error_response(f"摄像头ID {camera_id} 不存在", "CAMERA_NOT_FOUND")
            
            return format_success_response(
                f"获取摄像头 {camera_id} 配置成功",
                data={'camera': camera}
            )
            
        except Exception as e:
            log_error(f"获取摄像头 {camera_id} 配置失败: {e}", "CONFIG")
            return format_error_response(f"获取摄像头配置失败: {str(e)}", "GET_CAMERA_ERROR")
    
    def update_camera_marks(self, camera_id: str, marks: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新摄像头的标记位置数据
        
        Args:
            camera_id: 摄像头ID
            marks: 标记位置数据
            
        Returns:
            更新结果
        """
        try:
            if not validate_camera_id(camera_id):
                return format_error_response("摄像头ID格式无效", "INVALID_CAMERA_ID")
            
            if not isinstance(marks, dict):
                return format_error_response("标记数据格式无效", "INVALID_MARKS_DATA")
            
            # 读取现有配置
            config = safe_json_load(self.config_file, {})
            cameras = config.get('cameras', [])
            
            # 查找并更新指定摄像头
            camera_found = False
            updated_marks = 0
            
            for camera in cameras:
                if camera.get('id') == camera_id:
                    # 确保mark_positions字段存在
                    if 'mark_positions' not in camera:
                        camera['mark_positions'] = self._get_default_mark_positions()
                    
                    # 更新标记数据
                    for position_key, position_data in marks.items():
                        if self._is_valid_position_key(position_key):
                            if validate_mark_position(position_data):
                                camera['mark_positions'][position_key].update(position_data)
                                camera['mark_positions'][position_key]['marked'] = True
                                camera['mark_positions'][position_key]['updated_at'] = get_timestamp()
                                updated_marks += 1
                            else:
                                log_warning(f"跳过无效的标记数据: {position_key}", "CONFIG")
                    
                    camera_found = True
                    break
            
            if not camera_found:
                return format_error_response(f"摄像头ID {camera_id} 不存在", "CAMERA_NOT_FOUND")
            
            # 保存配置文件
            if not safe_json_dump(config, self.config_file):
                return format_error_response("保存配置文件失败", "SAVE_CONFIG_ERROR")
            
            log_success(f"摄像头 {camera_id} 标记数据更新成功 ({updated_marks} 个标记点)", "CONFIG")
            
            return format_success_response(
                f"摄像头 {camera_id} 标记数据更新成功",
                data={
                    'camera_id': camera_id,
                    'updated_marks': updated_marks
                }
            )
            
        except Exception as e:
            log_error(f"更新摄像头 {camera_id} 标记数据失败: {e}", "CONFIG")
            return format_error_response(f"更新标记数据失败: {str(e)}", "UPDATE_MARKS_ERROR")
    
    def add_camera(self, camera_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加新摄像头配置
        
        Args:
            camera_data: 摄像头配置数据
            
        Returns:
            添加结果
        """
        try:
            camera_id = camera_data.get('id')
            if not validate_camera_id(camera_id):
                return format_error_response("摄像头ID格式无效", "INVALID_CAMERA_ID")
            
            # 检查ID是否已存在
            existing_camera = self.get_camera_by_id(camera_id)
            if existing_camera['status'] == 'success':
                return format_error_response(f"摄像头ID {camera_id} 已存在", "CAMERA_EXISTS")
            
            # 读取现有配置
            config = safe_json_load(self.config_file, {'cameras': []})
            
            # 创建新摄像头配置
            new_camera = {
                'id': camera_id,
                'name': camera_data.get('name', f'摄像头{camera_id}'),
                'url': camera_data.get('url', ''),
                'description': camera_data.get('description', ''),
                'mark_positions': self._get_default_mark_positions(),
                'created_at': get_timestamp(),
                'updated_at': get_timestamp()
            }
            
            # 添加到配置中
            config['cameras'].append(new_camera)
            
            # 保存配置文件
            if not safe_json_dump(config, self.config_file):
                return format_error_response("保存配置文件失败", "SAVE_CONFIG_ERROR")
            
            log_success(f"添加摄像头 {camera_id} 成功", "CONFIG")
            
            return format_success_response(
                f"添加摄像头 {camera_id} 成功",
                data={'camera': new_camera}
            )
            
        except Exception as e:
            log_error(f"添加摄像头失败: {e}", "CONFIG")
            return format_error_response(f"添加摄像头失败: {str(e)}", "ADD_CAMERA_ERROR")
    
    def update_camera(self, camera_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新摄像头基本信息
        
        Args:
            camera_id: 摄像头ID
            update_data: 更新数据
            
        Returns:
            更新结果
        """
        try:
            if not validate_camera_id(camera_id):
                return format_error_response("摄像头ID格式无效", "INVALID_CAMERA_ID")
            
            # 读取现有配置
            config = safe_json_load(self.config_file, {})
            cameras = config.get('cameras', [])
            
            # 查找并更新指定摄像头
            camera_found = False
            for camera in cameras:
                if camera.get('id') == camera_id:
                    # 更新允许的字段
                    updatable_fields = ['name', 'url', 'description']
                    for field in updatable_fields:
                        if field in update_data:
                            camera[field] = update_data[field]
                    
                    camera['updated_at'] = get_timestamp()
                    camera_found = True
                    break
            
            if not camera_found:
                return format_error_response(f"摄像头ID {camera_id} 不存在", "CAMERA_NOT_FOUND")
            
            # 保存配置文件
            if not safe_json_dump(config, self.config_file):
                return format_error_response("保存配置文件失败", "SAVE_CONFIG_ERROR")
            
            log_success(f"摄像头 {camera_id} 信息更新成功", "CONFIG")
            
            return format_success_response(
                f"摄像头 {camera_id} 信息更新成功",
                data={'camera_id': camera_id}
            )
            
        except Exception as e:
            log_error(f"更新摄像头 {camera_id} 信息失败: {e}", "CONFIG")
            return format_error_response(f"更新摄像头信息失败: {str(e)}", "UPDATE_CAMERA_ERROR")
    
    def delete_camera(self, camera_id: str) -> Dict[str, Any]:
        """
        删除摄像头配置
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            删除结果
        """
        try:
            if not validate_camera_id(camera_id):
                return format_error_response("摄像头ID格式无效", "INVALID_CAMERA_ID")
            
            # 读取现有配置
            config = safe_json_load(self.config_file, {})
            cameras = config.get('cameras', [])
            
            # 查找并删除指定摄像头
            original_count = len(cameras)
            config['cameras'] = [cam for cam in cameras if cam.get('id') != camera_id]
            
            if len(config['cameras']) == original_count:
                return format_error_response(f"摄像头ID {camera_id} 不存在", "CAMERA_NOT_FOUND")
            
            # 保存配置文件
            if not safe_json_dump(config, self.config_file):
                return format_error_response("保存配置文件失败", "SAVE_CONFIG_ERROR")
            
            log_success(f"删除摄像头 {camera_id} 成功", "CONFIG")
            
            return format_success_response(
                f"删除摄像头 {camera_id} 成功",
                data={'camera_id': camera_id}
            )
            
        except Exception as e:
            log_error(f"删除摄像头 {camera_id} 失败: {e}", "CONFIG")
            return format_error_response(f"删除摄像头失败: {str(e)}", "DELETE_CAMERA_ERROR")
    
    def _create_default_config(self) -> None:
        """创建默认配置文件"""
        try:
            default_config = {
                "version": "1.0",
                "created_at": get_timestamp(),
                "cameras": [
                    {
                        "id": "001",
                        "name": "摄像头1",
                        "url": "http://192.168.1.100:8080/video",
                        "description": "默认摄像头",
                        "mark_positions": self._get_default_mark_positions(),
                        "created_at": get_timestamp(),
                        "updated_at": get_timestamp()
                    }
                ]
            }
            
            if safe_json_dump(default_config, self.config_file):
                log_success("创建默认配置文件成功", "CONFIG")
            else:
                log_error("创建默认配置文件失败", "CONFIG")
                
        except Exception as e:
            log_error(f"创建默认配置失败: {e}", "CONFIG")
    
    def _get_default_mark_positions(self) -> Dict[str, Any]:
        """获取默认的标记位置配置"""
        default_positions = {}
        position_names = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        for position in position_names:
            default_positions[position] = {
                'x': 0,
                'y': 0,
                'width': 50,
                'height': 70,
                'marked': False,
                'created_at': get_timestamp(),
                'updated_at': get_timestamp()
            }
        
        return default_positions
    
    def _is_valid_position_key(self, position_key: str) -> bool:
        """验证位置键是否有效"""
        valid_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        return position_key in valid_positions
    
    def get_config_status(self) -> Dict[str, Any]:
        """获取配置文件状态信息"""
        try:
            config = safe_json_load(self.config_file, {})
            cameras = config.get('cameras', [])
            
            # 统计标记完成情况
            total_cameras = len(cameras)
            marked_cameras = 0
            total_positions = 0
            marked_positions = 0
            
            for camera in cameras:
                mark_positions = camera.get('mark_positions', {})
                camera_marked_count = 0
                
                for position_data in mark_positions.values():
                    total_positions += 1
                    if position_data.get('marked', False):
                        marked_positions += 1
                        camera_marked_count += 1
                
                if camera_marked_count > 0:
                    marked_cameras += 1
            
            return format_success_response(
                "获取配置状态成功",
                data={
                    'config_file': str(self.config_file),
                    'file_exists': self.config_file.exists(),
                    'total_cameras': total_cameras,
                    'marked_cameras': marked_cameras,
                    'total_positions': total_positions,
                    'marked_positions': marked_positions,
                    'completion_rate': round((marked_positions / total_positions * 100) if total_positions > 0 else 0, 1)
                }
            )
            
        except Exception as e:
            log_error(f"获取配置状态失败: {e}", "CONFIG")
            return format_error_response(f"获取配置状态失败: {str(e)}", "GET_STATUS_ERROR")

# 创建全局实例
config_manager = ConfigManager()

# 导出主要函数
def get_all_cameras() -> Dict[str, Any]:
    """获取所有摄像头配置"""
    return config_manager.get_all_cameras()

def get_camera_by_id(camera_id: str) -> Dict[str, Any]:
    """根据ID获取摄像头配置"""
    return config_manager.get_camera_by_id(camera_id)

def update_camera_marks(camera_id: str, marks: Dict[str, Any]) -> Dict[str, Any]:
    """更新摄像头标记数据"""
    return config_manager.update_camera_marks(camera_id, marks)

def add_camera(camera_data: Dict[str, Any]) -> Dict[str, Any]:
    """添加新摄像头"""
    return config_manager.add_camera(camera_data)

def update_camera(camera_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """更新摄像头信息"""
    return config_manager.update_camera(camera_id, update_data)

def delete_camera(camera_id: str) -> Dict[str, Any]:
    """删除摄像头"""
    return config_manager.delete_camera(camera_id)

def get_config_status() -> Dict[str, Any]:
    """获取配置状态"""
    return config_manager.get_config_status()

if __name__ == "__main__":
    # 测试配置管理器
    print("🧪 测试配置管理器")
    
    # 测试获取所有摄像头
    all_cameras = get_all_cameras()
    print(f"所有摄像头: {all_cameras}")
    
    # 测试获取单个摄像头
    camera_001 = get_camera_by_id("001")
    print(f"摄像头001: {camera_001}")
    
    # 测试更新标记数据
    test_marks = {
        "zhuang_1": {"x": 100, "y": 150, "width": 60, "height": 80},
        "xian_1": {"x": 200, "y": 250, "width": 55, "height": 75}
    }
    update_result = update_camera_marks("001", test_marks)
    print(f"更新标记结果: {update_result}")
    
    # 测试配置状态
    status = get_config_status()
    print(f"配置状态: {status}")
    
    print("✅ 配置管理器测试完成")