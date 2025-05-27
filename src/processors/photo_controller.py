#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合的拍照控制模块 - 基于简化版RTSP拍照程序
使用与测试程序相同的简化FFmpeg命令确保可靠性
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

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
import threading

from src.core.utils import (
    validate_camera_id, get_image_dir, get_file_size, get_config_dir,
    format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)
from src.core.config_manager import get_camera_by_id

class IntegratedPhotoController:
    """整合的拍照控制器 - 基于简化版RTSP拍照"""
    
    def __init__(self):
        """初始化整合拍照控制器"""
        # 设置路径
        self.image_dir = get_image_dir()
        self.image_dir.mkdir(parents=True, exist_ok=True)
        
        # 拍照状态记录
        self.photo_status = {}
        
        # 检查ffmpeg是否可用
        self._check_ffmpeg()
        
        log_info("整合拍照控制器初始化完成", "PHOTO_CONTROLLER")
    
    def _check_ffmpeg(self):
        """检查ffmpeg是否可用"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.ffmpeg_available = True
                log_success("ffmpeg可用，支持RTSP拍照", "PHOTO_CONTROLLER")
            else:
                self.ffmpeg_available = False
                log_warning("ffmpeg不可用，无法进行RTSP拍照", "PHOTO_CONTROLLER")
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            self.ffmpeg_available = False
            log_warning("ffmpeg检查失败，无法进行RTSP拍照", "PHOTO_CONTROLLER")
    
    def take_photo_by_id(self, camera_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        根据摄像头ID进行拍照
        
        Args:
            camera_id: 摄像头ID
            options: 拍照选项
            
        Returns:
            拍照结果
        """
        try:
            print(f"🎥 [DEBUG] take_photo_by_id 开始，摄像头ID: {camera_id}")
            
            # 验证摄像头ID
            if not validate_camera_id(camera_id):
                return format_error_response("摄像头ID格式无效", "INVALID_CAMERA_ID")
            
            # 检查摄像头配置是否存在
            print(f"🎥 [DEBUG] 正在调用 get_camera_by_id({camera_id})")
            camera_result = get_camera_by_id(camera_id)
            print(f"🎥 [DEBUG] get_camera_by_id 返回结果: {camera_result}")
            
            if camera_result['status'] != 'success':
                return format_error_response(f"摄像头 {camera_id} 配置不存在", "CAMERA_NOT_FOUND")
            
            camera_config = camera_result['data']['camera']
            print(f"🎥 [DEBUG] 提取的 camera_config: {camera_config}")
            print(f"🎥 [DEBUG] camera_config 中的 IP: {camera_config.get('ip', 'NOT_FOUND')}")
            print(f"🎥 [DEBUG] camera_config 中的 username: {camera_config.get('username', 'NOT_FOUND')}")
            print(f"🎥 [DEBUG] camera_config 中的 password: {camera_config.get('password', 'NOT_FOUND')}")
            
            # 检查是否启用
            if not camera_config.get('enabled', True):
                return format_error_response(f"摄像头 {camera_id} 已禁用", "CAMERA_DISABLED")
            
            # 记录拍照开始状态
            self._update_photo_status(camera_id, 'starting', '开始拍照...')
            
            # 执行拍照
            print(f"🎥 [DEBUG] 正在调用 _rtsp_photo_capture")
            start_time = time.time()
            photo_result = self._rtsp_photo_capture(camera_id, camera_config)
            duration = round(time.time() - start_time, 2)
            
            print(f"🎥 [DEBUG] _rtsp_photo_capture 返回结果: {photo_result}")
            
            if photo_result['success']:
                # 拍照成功，处理结果
                result = self._handle_photo_success(camera_id, photo_result, duration)
                self._update_photo_status(camera_id, 'completed', '拍照完成')
                return result
            else:
                # 拍照失败
                error_msg = photo_result.get('error', '拍照失败')
                self._update_photo_status(camera_id, 'failed', error_msg)
                return format_error_response(f"摄像头 {camera_id} 拍照失败: {error_msg}", "PHOTO_FAILED")
                
        except Exception as e:
            print(f"💥 [DEBUG] take_photo_by_id 异常: {e}")
            import traceback
            traceback.print_exc()
            self._update_photo_status(camera_id, 'error', str(e))
            log_error(f"摄像头 {camera_id} 拍照过程出错: {e}", "PHOTO_CONTROLLER")
            return format_error_response(f"拍照过程出错: {str(e)}", "PHOTO_ERROR")
    
    def _build_rtsp_url(self, camera_config: Dict[str, Any]) -> str:
        """构建RTSP URL"""
        print(f"🔗 [DEBUG] _build_rtsp_url 开始构建")
        
        username = camera_config.get('username', 'admin')
        password = camera_config.get('password', '')
        ip = camera_config.get('ip', '')
        port = camera_config.get('port', 554)
        stream_path = camera_config.get('stream_path', '/Streaming/Channels/101')
        
        print(f"🔗 [DEBUG] username: {username}")
        print(f"🔗 [DEBUG] password: {password}")
        print(f"🔗 [DEBUG] ip: {ip}")
        print(f"🔗 [DEBUG] port: {port}")
        print(f"🔗 [DEBUG] stream_path: {stream_path}")
        
        rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}{stream_path}"
        print(f"🔗 [DEBUG] 构建的完整RTSP URL: {rtsp_url}")
        
        return rtsp_url
    
    def _rtsp_photo_capture(self, camera_id: str, camera_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用ffmpeg进行RTSP拍照 - 基于简化版程序的可靠命令
        
        Args:
            camera_id: 摄像头ID
            camera_config: 摄像头配置
            
        Returns:
            拍照结果
        """
        try:
            print(f"📸 [DEBUG] _rtsp_photo_capture 开始")
            print(f"📸 [DEBUG] 接收到的 camera_config: {camera_config}")
            
            if not self.ffmpeg_available:
                return {
                    'success': False,
                    'error': 'ffmpeg不可用，无法进行RTSP拍照'
                }
            
            # 检查必需字段
            required_fields = ['ip', 'username', 'password']
            print(f"📸 [DEBUG] 开始检查必需字段: {required_fields}")
            
            for field in required_fields:
                field_value = camera_config.get(field)
                print(f"📸 [DEBUG] 检查字段 {field}: 值='{field_value}', 类型={type(field_value)}")
                
                # 更严格的检查：确保字段存在且不为空字符串
                if field_value is None or field_value == '' or (isinstance(field_value, str) and field_value.strip() == ''):
                    print(f"❌ [DEBUG] 字段 {field} 为空或不存在")
                    return {
                        'success': False,
                        'error': f'摄像头配置缺少必需字段: {field}'
                    }
                else:
                    print(f"✅ [DEBUG] 字段 {field} 检查通过")
            
            # 构建RTSP URL和输出路径
            print(f"📸 [DEBUG] 开始构建 RTSP URL")
            rtsp_url = self._build_rtsp_url(camera_config)
            print(f"📸 [DEBUG] 构建的 RTSP URL: {rtsp_url}")
            
            filename = f"camera_{camera_id}.png"
            output_path = self.image_dir / filename
            print(f"📸 [DEBUG] 输出路径: {output_path}")
            
            # 使用与简化版程序完全相同的FFmpeg命令
            cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-i', rtsp_url,
                '-vframes', '1',
                '-y',  # 覆盖现有文件
                str(output_path)
            ]
            
            print(f"📸 [DEBUG] FFmpeg命令: {cmd}")
            
            # 隐藏密码用于日志
            safe_url = rtsp_url.replace(camera_config['password'], '***')
            log_info(f"执行RTSP拍照: {safe_url}", "PHOTO_CONTROLLER")
            print(f"📸 [DEBUG] 安全URL (用于日志): {safe_url}")
            
            # 执行ffmpeg命令
            print(f"📸 [DEBUG] 开始执行 FFmpeg 命令...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20  # 20秒超时，与简化版一致
            )
            
            print(f"📸 [DEBUG] FFmpeg 执行完成")
            print(f"📸 [DEBUG] 返回码: {result.returncode}")
            print(f"📸 [DEBUG] stdout: {result.stdout}")
            print(f"📸 [DEBUG] stderr: {result.stderr}")
            
            # 检查结果
            if result.returncode == 0:
                print(f"📸 [DEBUG] FFmpeg 执行成功，检查输出文件")
                print(f"📸 [DEBUG] 文件是否存在: {output_path.exists()}")
                
                if output_path.exists():
                    file_size = output_path.stat().st_size
                    print(f"📸 [DEBUG] 文件大小: {file_size} bytes")
                    
                    if file_size > 0:
                        log_success(f"RTSP拍照成功: {filename} ({file_size/1024:.1f} KB)", "PHOTO_CONTROLLER")
                        
                        return {
                            'success': True,
                            'filename': filename,
                            'file_path': str(output_path),
                            'file_size': file_size,
                            'mode': 'rtsp'
                        }
                    else:
                        print(f"❌ [DEBUG] 文件大小为0")
                        output_path.unlink(missing_ok=True)
                        return {
                            'success': False,
                            'error': '拍照文件为空'
                        }
                else:
                    print(f"❌ [DEBUG] 输出文件不存在")
                    return {
                        'success': False,
                        'error': '拍照文件未生成'
                    }
            else:
                # ffmpeg执行失败
                error_msg = result.stderr.strip() if result.stderr else "FFmpeg执行失败"
                print(f"❌ [DEBUG] FFmpeg执行失败: {error_msg}")
                log_error(f"FFmpeg执行失败: {error_msg}", "PHOTO_CONTROLLER")
                return {
                    'success': False,
                    'error': f'FFmpeg执行失败: {error_msg}'
                }
                
        except subprocess.TimeoutExpired:
            print(f"⏰ [DEBUG] FFmpeg执行超时")
            log_error(f"RTSP拍照超时: {camera_id}", "PHOTO_CONTROLLER")
            return {
                'success': False,
                'error': 'RTSP拍照超时，请检查网络连接和摄像头状态'
            }
        except Exception as e:
            print(f"💥 [DEBUG] _rtsp_photo_capture 异常: {e}")
            import traceback
            traceback.print_exc()
            log_error(f"RTSP拍照异常: {e}", "PHOTO_CONTROLLER")
            return {
                'success': False,
                'error': f'RTSP拍照异常: {str(e)}'
            }
    
    def _handle_photo_success(self, camera_id: str, photo_result: Dict[str, Any], 
                             duration: float) -> Dict[str, Any]:
        """处理拍照成功的结果"""
        try:
            filename = photo_result.get('filename', '')
            file_path = photo_result.get('file_path', '')
            file_size = photo_result.get('file_size', 0)
            
            # 验证文件是否存在
            if file_path and Path(file_path).exists():
                actual_file_size = get_file_size(file_path)
                if actual_file_size != file_size:
                    file_size = actual_file_size
            
            # 记录拍照历史
            self._record_photo_history(camera_id, filename, file_size, duration)
            
            log_success(f"摄像头 {camera_id} 拍照成功: {filename} ({file_size/1024:.1f} KB, {duration}s)", 
                       "PHOTO_CONTROLLER")
            
            return format_success_response(
                f"摄像头 {camera_id} 拍照成功",
                data={
                    'camera_id': camera_id,
                    'filename': filename,
                    'file_path': file_path,
                    'file_size': file_size,
                    'duration': duration,
                    'image_url': f"/image/{filename}",
                    'timestamp': get_timestamp(),
                    'mode': photo_result.get('mode', 'rtsp')
                }
            )
            
        except Exception as e:
            log_error(f"处理拍照成功结果时出错: {e}", "PHOTO_CONTROLLER")
            return format_error_response(f"处理拍照结果失败: {str(e)}", "RESULT_PROCESS_ERROR")
    
    def _update_photo_status(self, camera_id: str, status: str, message: str):
        """更新拍照状态"""
        self.photo_status[camera_id] = {
            'status': status,
            'message': message,
            'timestamp': get_timestamp()
        }
    
    def _record_photo_history(self, camera_id: str, filename: str, file_size: int, duration: float):
        """记录拍照历史"""
        try:
            history_entry = {
                'camera_id': camera_id,
                'filename': filename,
                'file_size': file_size,
                'duration': duration,
                'timestamp': get_timestamp()
            }
            
            log_info(f"记录拍照历史: {camera_id} -> {filename}", "PHOTO_CONTROLLER")
            
        except Exception as e:
            log_error(f"记录拍照历史失败: {e}", "PHOTO_CONTROLLER")
    
    def get_photo_status(self, camera_id: str = None) -> Dict[str, Any]:
        """获取拍照状态"""
        try:
            if camera_id:
                if not validate_camera_id(camera_id):
                    return format_error_response("摄像头ID格式无效", "INVALID_CAMERA_ID")
                
                status = self.photo_status.get(camera_id, {
                    'status': 'idle',
                    'message': '未进行拍照',
                    'timestamp': get_timestamp()
                })
                
                return format_success_response(
                    f"获取摄像头 {camera_id} 状态成功",
                    data={'camera_id': camera_id, 'status': status}
                )
            else:
                return format_success_response(
                    "获取所有拍照状态成功",
                    data={'all_status': self.photo_status}
                )
                
        except Exception as e:
            log_error(f"获取拍照状态失败: {e}", "PHOTO_CONTROLLER")
            return format_error_response(f"获取状态失败: {str(e)}", "GET_STATUS_ERROR")
    
    def list_photos(self, camera_id: str = None, limit: int = 20) -> Dict[str, Any]:
        """列出图片文件"""
        try:
            if not self.image_dir.exists():
                return format_success_response("图片目录不存在", data={'photos': []})
            
            # 获取图片文件
            if camera_id:
                pattern = f"camera_{camera_id}.png"
            else:
                pattern = "camera_*.png"
            
            photo_files = list(self.image_dir.glob(pattern))
            photo_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # 限制返回数量
            photo_files = photo_files[:limit]
            
            # 构建返回数据
            photos = []
            for photo_file in photo_files:
                file_info = {
                    'filename': photo_file.name,
                    'file_size': get_file_size(photo_file),
                    'modified_time': photo_file.stat().st_mtime,
                    'image_url': f"/image/{photo_file.name}",
                    'camera_id': self._extract_camera_id_from_filename(photo_file.name)
                }
                photos.append(file_info)
            
            return format_success_response(
                f"获取图片列表成功 ({len(photos)} 张)",
                data={
                    'photos': photos,
                    'total_count': len(photos),
                    'camera_filter': camera_id
                }
            )
            
        except Exception as e:
            log_error(f"列出图片文件失败: {e}", "PHOTO_CONTROLLER")
            return format_error_response(f"获取图片列表失败: {str(e)}", "LIST_PHOTOS_ERROR")
    
    def _extract_camera_id_from_filename(self, filename: str) -> str:
        """从文件名中提取摄像头ID"""
        try:
            # 文件名格式: camera_001.png
            parts = filename.split('_')
            if len(parts) >= 2 and parts[0] == 'camera':
                return parts[1].split('.')[0]  # 移除扩展名
            return 'unknown'
        except:
            return 'unknown'
    
    def test_camera_connection(self, camera_id: str) -> Dict[str, Any]:
        """测试摄像头连接"""
        try:
            camera_result = get_camera_by_id(camera_id)
            if camera_result['status'] != 'success':
                return format_error_response(f"摄像头 {camera_id} 配置不存在", "CAMERA_NOT_FOUND")
            
            camera_config = camera_result['data']['camera']
            
            if not camera_config.get('enabled', True):
                return format_error_response(f"摄像头 {camera_id} 已禁用", "CAMERA_DISABLED")
            
            # 构建RTSP URL
            rtsp_url = self._build_rtsp_url(camera_config)
            safe_url = rtsp_url.replace(camera_config.get('password', ''), '***')
            
            log_info(f"测试摄像头连接: {safe_url}", "PHOTO_CONTROLLER")
            
            # 使用ffprobe测试连接（更轻量级）
            cmd = [
                'ffprobe',
                '-rtsp_transport', 'tcp',
                '-i', rtsp_url,
                '-t', '1',
                '-v', 'quiet',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return format_success_response(
                    f"摄像头 {camera_id} 连接正常",
                    data={'camera_id': camera_id, 'rtsp_url': safe_url}
                )
            else:
                error_msg = result.stderr.strip() if result.stderr else "连接测试失败"
                return format_error_response(
                    f"摄像头 {camera_id} 连接失败: {error_msg}",
                    "CONNECTION_FAILED"
                )
                
        except subprocess.TimeoutExpired:
            return format_error_response(f"摄像头 {camera_id} 连接超时", "CONNECTION_TIMEOUT")
        except Exception as e:
            log_error(f"测试摄像头连接失败: {e}", "PHOTO_CONTROLLER")
            return format_error_response(f"连接测试异常: {str(e)}", "TEST_ERROR")


# 创建全局实例
integrated_photo_controller = IntegratedPhotoController()

# 导出主要函数
def take_photo_by_id(camera_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """根据摄像头ID拍照"""
    return integrated_photo_controller.take_photo_by_id(camera_id, options)

def get_photo_status(camera_id: str = None) -> Dict[str, Any]:
    """获取拍照状态"""
    return integrated_photo_controller.get_photo_status(camera_id)

def list_photos(camera_id: str = None, limit: int = 20) -> Dict[str, Any]:
    """列出图片文件"""
    return integrated_photo_controller.list_photos(camera_id, limit)

def test_camera_connection(camera_id: str) -> Dict[str, Any]:
    """测试摄像头连接"""
    return integrated_photo_controller.test_camera_connection(camera_id)

if __name__ == "__main__":
    # 测试拍照控制器
    print("🧪 测试RTSP拍照控制器")
    
    try:
        # 测试连接
        result = test_camera_connection("001")
        print(f"连接测试: {result}")
        
        # 测试拍照功能
        result = take_photo_by_id("001")
        print(f"拍照测试: {result}")
        
        print("✅ 拍照控制器测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()