#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置加载器 - 为三个入口程序提供统一的配置管理
功能:
1. 摄像头配置加载和验证
2. 识别算法配置管理
3. 推送配置管理
4. 配置文件检查和修复
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
def setup_project_paths():
    """设置项目路径，确保可以正确导入模块"""
    current_file = Path(__file__).resolve()
    
    # 找到项目根目录（包含 config_loader.py 的目录）
    project_root = current_file.parent
    
    # 将项目根目录添加到 Python 路径
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

# 调用路径设置
PROJECT_ROOT = setup_project_paths()

import json
from typing import Dict, Any, List, Optional
from src.core.utils import (
    get_config_dir, safe_json_load, safe_json_dump,
    format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)

class ConfigLoader:
    """统一配置加载器"""
    
    def __init__(self):
        """初始化配置加载器"""
        self.config_dir = get_config_dir()
        self.camera_config_file = self.config_dir / "camera.json"
        self.recognition_config_file = self.config_dir / "recognition_config.json"
        self.push_config_file = self.config_dir / "push_config.json"
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        log_info("统一配置加载器初始化完成", "CONFIG_LOADER")
    
    def load_camera_config(self) -> Dict[str, Any]:
        """
        加载摄像头配置
        
        Returns:
            摄像头配置结果
        """
        try:
            if not self.camera_config_file.exists():
                return self._create_default_camera_config()
            
            config = safe_json_load(self.camera_config_file)
            if not config or not isinstance(config, dict):
                log_warning("摄像头配置文件格式错误，使用默认配置", "CONFIG_LOADER")
                return self._create_default_camera_config()
            
            # 验证配置完整性
            validation_result = self._validate_camera_config(config)
            if not validation_result['valid']:
                log_error(f"摄像头配置验证失败: {validation_result['error']}", "CONFIG_LOADER")
                return format_error_response(f"摄像头配置无效: {validation_result['error']}", "INVALID_CONFIG")
            
            log_success(f"摄像头配置加载成功: {len(config.get('cameras', []))} 个摄像头", "CONFIG_LOADER")
            
            return format_success_response(
                "摄像头配置加载成功",
                data=config
            )
            
        except Exception as e:
            log_error(f"加载摄像头配置失败: {e}", "CONFIG_LOADER")
            return format_error_response(f"加载摄像头配置失败: {str(e)}", "LOAD_CAMERA_CONFIG_ERROR")
    
    def _create_default_camera_config(self) -> Dict[str, Any]:
        """创建默认摄像头配置"""
        default_config = {
            "system": {
                "ffmpeg": {
                    "path": "ffmpeg",
                    "timeout": 15,
                    "retry_times": 3,
                    "retry_delay": 2
                },
                "output": {
                    "directory": "image",
                    "format": "png",
                    "quality": "high"
                }
            },
            "cameras": [],
            "created_at": get_timestamp(),
            "updated_at": get_timestamp()
        }
        
        # 保存默认配置
        if safe_json_dump(default_config, self.camera_config_file):
            log_info("创建默认摄像头配置文件", "CONFIG_LOADER")
        
        return format_success_response("创建默认摄像头配置", data=default_config)
    
    def _validate_camera_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证摄像头配置"""
        try:
            # 检查基本结构
            if 'cameras' not in config:
                return {"valid": False, "error": "缺少cameras字段"}
            
            cameras = config['cameras']
            if not isinstance(cameras, list):
                return {"valid": False, "error": "cameras字段必须是列表"}
            
            # 验证每个摄像头配置
            camera_ids = []
            for i, camera in enumerate(cameras):
                if not isinstance(camera, dict):
                    return {"valid": False, "error": f"摄像头 {i} 配置格式错误"}
                
                # 检查必需字段
                required_fields = ['id', 'name', 'ip', 'username', 'password']
                for field in required_fields:
                    if field not in camera:
                        return {"valid": False, "error": f"摄像头 {i} 缺少字段: {field}"}
                
                # 检查ID唯一性
                camera_id = camera['id']
                if camera_id in camera_ids:
                    return {"valid": False, "error": f"摄像头ID重复: {camera_id}"}
                camera_ids.append(camera_id)
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": f"验证异常: {str(e)}"}
    
    def load_recognition_config(self) -> Dict[str, Any]:
        """
        加载识别算法配置
        
        Returns:
            识别配置结果
        """
        try:
            if not self.recognition_config_file.exists():
                return self._create_default_recognition_config()
            
            config = safe_json_load(self.recognition_config_file)
            if not config:
                return self._create_default_recognition_config()
            
            log_success("识别配置加载成功", "CONFIG_LOADER")
            
            return format_success_response(
                "识别配置加载成功",
                data=config
            )
            
        except Exception as e:
            log_error(f"加载识别配置失败: {e}", "CONFIG_LOADER")
            return format_error_response(f"加载识别配置失败: {str(e)}", "LOAD_RECOGNITION_CONFIG_ERROR")
    
    def _create_default_recognition_config(self) -> Dict[str, Any]:
        """创建默认识别配置"""
        default_config = {
            "algorithms": {
                "yolo": {
                    "enabled": True,
                    "model_path": "src/config/yolov8/best.pt",
                    "confidence_threshold": 0.5,
                    "nms_threshold": 0.4
                },
                "ocr_easy": {
                    "enabled": True,
                    "languages": ["en"],
                    "gpu": False,
                    "confidence_threshold": 0.3
                },
                "ocr_paddle": {
                    "enabled": False,
                    "use_angle_cls": False,
                    "lang": "en",
                    "gpu": False
                }
            },
            "processing": {
                "image_preprocessing": {
                    "resize_enabled": False,
                    "resize_width": 640,
                    "resize_height": 480,
                    "enhance_enabled": True
                },
                "recognition_mode": "hybrid",  # yolo_only, ocr_only, hybrid
                "confidence_filter": 0.3,
                "result_combination": "best_confidence"
            },
            "output": {
                "save_results": True,
                "save_debug_images": False,
                "result_format": "json"
            },
            "created_at": get_timestamp(),
            "updated_at": get_timestamp()
        }
        
        # 保存默认配置
        if safe_json_dump(default_config, self.recognition_config_file):
            log_info("创建默认识别配置文件", "CONFIG_LOADER")
        
        return format_success_response("创建默认识别配置", data=default_config)
    
    def load_push_config(self) -> Dict[str, Any]:
        """
        加载推送配置
        
        Returns:
            推送配置结果
        """
        try:
            if not self.push_config_file.exists():
                return self._create_default_push_config()
            
            config = safe_json_load(self.push_config_file)
            if not config:
                return self._create_default_push_config()
            
            log_success("推送配置加载成功", "CONFIG_LOADER")
            
            return format_success_response(
                "推送配置加载成功",
                data=config
            )
            
        except Exception as e:
            log_error(f"加载推送配置失败: {e}", "CONFIG_LOADER")
            return format_error_response(f"加载推送配置失败: {str(e)}", "LOAD_PUSH_CONFIG_ERROR")
    
    def _create_default_push_config(self) -> Dict[str, Any]:
        """创建默认推送配置"""
        default_config = {
            "websocket": {
                "enabled": True,
                "server_url": "ws://bjl_heguan_wss.yhyule666.com:8001",
                "client_id": "python_client_001",
                "auto_reconnect": True,
                "reconnect_delay": 5,
                "heartbeat_interval": 30
            },
            "push_settings": {
                "auto_push": True,
                "push_interval": 2,  # 秒
                "batch_push": False,
                "retry_times": 3,
                "retry_delay": 1
            },
            "filter": {
                "min_confidence": 0.3,
                "positions": ["zhuang_1", "zhuang_2", "zhuang_3", "xian_1", "xian_2", "xian_3"],
                "only_recognized": False  # 是否只推送识别成功的位置
            },
            "created_at": get_timestamp(),
            "updated_at": get_timestamp()
        }
        
        # 保存默认配置
        if safe_json_dump(default_config, self.push_config_file):
            log_info("创建默认推送配置文件", "CONFIG_LOADER")
        
        return format_success_response("创建默认推送配置", data=default_config)
    
    def get_enabled_cameras(self) -> Dict[str, Any]:
        """
        获取所有启用的摄像头
        
        Returns:
            启用的摄像头列表
        """
        try:
            camera_config_result = self.load_camera_config()
            if camera_config_result['status'] != 'success':
                return camera_config_result
            
            all_cameras = camera_config_result['data'].get('cameras', [])
            enabled_cameras = [
                camera for camera in all_cameras 
                if camera.get('enabled', True)
            ]
            
            return format_success_response(
                f"获取启用摄像头成功: {len(enabled_cameras)} 个",
                data={
                    'cameras': enabled_cameras,
                    'total_count': len(enabled_cameras),
                    'all_count': len(all_cameras)
                }
            )
            
        except Exception as e:
            log_error(f"获取启用摄像头失败: {e}", "CONFIG_LOADER")
            return format_error_response(f"获取启用摄像头失败: {str(e)}", "GET_ENABLED_CAMERAS_ERROR")
    
    def get_camera_by_id(self, camera_id: str) -> Dict[str, Any]:
        """
        根据ID获取指定摄像头配置
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            摄像头配置
        """
        try:
            camera_config_result = self.load_camera_config()
            if camera_config_result['status'] != 'success':
                return camera_config_result
            
            cameras = camera_config_result['data'].get('cameras', [])
            
            for camera in cameras:
                if camera.get('id') == camera_id:
                    return format_success_response(
                        f"获取摄像头 {camera_id} 配置成功",
                        data={'camera': camera}
                    )
            
            return format_error_response(f"摄像头 {camera_id} 不存在", "CAMERA_NOT_FOUND")
            
        except Exception as e:
            log_error(f"获取摄像头 {camera_id} 配置失败: {e}", "CONFIG_LOADER")
            return format_error_response(f"获取摄像头配置失败: {str(e)}", "GET_CAMERA_ERROR")
    
    def validate_all_configs(self) -> Dict[str, Any]:
        """
        验证所有配置文件
        
        Returns:
            验证结果
        """
        try:
            validation_results = {}
            overall_valid = True
            
            # 验证摄像头配置
            camera_result = self.load_camera_config()
            validation_results['camera_config'] = {
                'valid': camera_result['status'] == 'success',
                'message': camera_result['message'],
                'file_exists': self.camera_config_file.exists()
            }
            if camera_result['status'] != 'success':
                overall_valid = False
            
            # 验证识别配置
            recognition_result = self.load_recognition_config()
            validation_results['recognition_config'] = {
                'valid': recognition_result['status'] == 'success',
                'message': recognition_result['message'],
                'file_exists': self.recognition_config_file.exists()
            }
            if recognition_result['status'] != 'success':
                overall_valid = False
            
            # 验证推送配置
            push_result = self.load_push_config()
            validation_results['push_config'] = {
                'valid': push_result['status'] == 'success',
                'message': push_result['message'],
                'file_exists': self.push_config_file.exists()
            }
            if push_result['status'] != 'success':
                overall_valid = False
            
            return format_success_response(
                f"配置验证完成: {'全部有效' if overall_valid else '存在问题'}",
                data={
                    'overall_valid': overall_valid,
                    'validation_results': validation_results
                }
            )
            
        except Exception as e:
            log_error(f"配置验证失败: {e}", "CONFIG_LOADER")
            return format_error_response(f"配置验证失败: {str(e)}", "VALIDATE_CONFIGS_ERROR")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要信息
        
        Returns:
            配置摘要
        """
        try:
            summary = {
                'config_directory': str(self.config_dir),
                'config_files': {
                    'camera_config': {
                        'path': str(self.camera_config_file),
                        'exists': self.camera_config_file.exists()
                    },
                    'recognition_config': {
                        'path': str(self.recognition_config_file),  
                        'exists': self.recognition_config_file.exists()
                    },
                    'push_config': {
                        'path': str(self.push_config_file),
                        'exists': self.push_config_file.exists()
                    }
                }
            }
            
            # 获取摄像头数量
            camera_result = self.load_camera_config()
            if camera_result['status'] == 'success':
                cameras = camera_result['data'].get('cameras', [])
                enabled_cameras = [c for c in cameras if c.get('enabled', True)]
                summary['camera_summary'] = {
                    'total_cameras': len(cameras),
                    'enabled_cameras': len(enabled_cameras),
                    'disabled_cameras': len(cameras) - len(enabled_cameras)
                }
            else:
                summary['camera_summary'] = {'error': camera_result['message']}
            
            return format_success_response(
                "获取配置摘要成功",
                data=summary
            )
            
        except Exception as e:
            log_error(f"获取配置摘要失败: {e}", "CONFIG_LOADER")
            return format_error_response(f"获取配置摘要失败: {str(e)}", "GET_SUMMARY_ERROR")

# 创建全局实例
config_loader = ConfigLoader()

# 导出主要函数
def load_camera_config() -> Dict[str, Any]:
    """加载摄像头配置"""
    return config_loader.load_camera_config()

def load_recognition_config() -> Dict[str, Any]:
    """加载识别配置"""
    return config_loader.load_recognition_config()

def load_push_config() -> Dict[str, Any]:
    """加载推送配置"""
    return config_loader.load_push_config()

def get_enabled_cameras() -> Dict[str, Any]:
    """获取启用的摄像头"""
    return config_loader.get_enabled_cameras()

def get_camera_by_id(camera_id: str) -> Dict[str, Any]:
    """根据ID获取摄像头配置"""
    return config_loader.get_camera_by_id(camera_id)

def validate_all_configs() -> Dict[str, Any]:
    """验证所有配置"""
    return config_loader.validate_all_configs()

def get_config_summary() -> Dict[str, Any]:
    """获取配置摘要"""
    return config_loader.get_config_summary()

if __name__ == "__main__":
    # 测试配置加载器
    print("🧪 测试统一配置加载器")
    
    # 测试加载所有配置
    print("\n📋 加载配置文件")
    camera_config = load_camera_config()
    print(f"摄像头配置: {camera_config['status']}")
    
    recognition_config = load_recognition_config()
    print(f"识别配置: {recognition_config['status']}")
    
    push_config = load_push_config()
    print(f"推送配置: {push_config['status']}")
    
    # 测试获取启用的摄像头
    print("\n📷 获取启用摄像头")
    enabled_cameras = get_enabled_cameras()
    print(f"启用摄像头: {enabled_cameras['status']}")
    if enabled_cameras['status'] == 'success':
        print(f"   数量: {enabled_cameras['data']['total_count']}")
    
    # 测试配置验证
    print("\n✅ 验证所有配置")
    validation = validate_all_configs()
    print(f"配置验证: {validation['status']}")
    if validation['status'] == 'success':
        print(f"   整体有效: {validation['data']['overall_valid']}")
    
    # 测试配置摘要
    print("\n📊 获取配置摘要")
    summary = get_config_summary()
    print(f"配置摘要: {summary['status']}")
    
    print("✅ 统一配置加载器测试完成")