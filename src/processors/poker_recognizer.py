#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合的拍照控制模块 - 集成拍照、裁剪、识别完整流程
功能:
1. 摄像头拍照功能
2. 图片裁剪处理（整合 cut.py）
3. 扑克识别处理（整合 see.py）
4. 完整的拍照->裁剪->识别工作流
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

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

from src.core.utils import (
    validate_camera_id, get_image_dir, get_file_size, get_config_dir,
    format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)
from src.core.config_manager import get_camera_by_id
from src.processors.image_cutter import ImageCutter
from src.processors.poker_recognizer import PokerRecognizer

class IntegratedPhotoController:
    """整合的拍照控制器 - 完整的拍照到识别流程"""
    
    def __init__(self):
        """初始化整合拍照控制器"""
        # 设置路径
        self.image_dir = get_image_dir()
        self.image_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化子模块
        self.image_cutter = ImageCutter()
        self.poker_recognizer = PokerRecognizer()
        
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
                log_info(f"执行ffmpeg命令: {' '.join(ffmpeg_cmd[:5])}...", "PHOTO_CONTROLLER")
            
            # 执行ffmpeg命令
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30秒超时
            )
            
            if result.returncode == 0 and output_path.exists():
                file_size = get_file_size(output_path)
                
                if file_size > 1024:  # 至少1KB
                    log_success(f"RTSP拍照成功: {filename} ({file_size} bytes)", "PHOTO_CONTROLLER")
                    
                    return {
                        'success': True,
                        'filename': filename,
                        'file_path': str(output_path),
                        'file_size': file_size,
                        'mode': 'rtsp'
                    }
                else:
                    # 文件太小，可能拍照失败
                    output_path.unlink(missing_ok=True)
                    raise Exception(f"生成的图片文件太小: {file_size} bytes")
            else:
                error_msg = result.stderr if result.stderr else "ffmpeg执行失败"
                raise Exception(f"ffmpeg错误: {error_msg}")
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'RTSP拍照超时'
            }
        except Exception as e:
            log_error(f"RTSP拍照失败: {e}", "PHOTO_CONTROLLER")
            return {
                'success': False,
                'error': f'RTSP拍照失败: {str(e)}'
            }
    
    def _simulate_photo_capture(self, camera_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        模拟拍照功能（用于测试）
        
        Args:
            camera_id: 摄像头ID
            options: 拍照选项
            
        Returns:
            模拟拍照结果
        """
        try:
            # 模拟拍照延迟
            time.sleep(0.5)
            
            # 生成文件名
            filename = f"camera_{camera_id}.png"
            file_path = self.image_dir / filename
            
            # 创建模拟图片文件
            mock_image_content = self._create_test_image_content(camera_id)
            
            with open(file_path, 'wb') as f:
                f.write(mock_image_content)
            
            file_size = get_file_size(file_path)
            
            log_warning(f"使用模拟拍照模式 - 摄像头 {camera_id}", "PHOTO_CONTROLLER")
            
            return {
                'success': True,
                'filename': filename,
                'file_path': str(file_path),
                'file_size': file_size,
                'mode': 'simulation'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'模拟拍照失败: {str(e)}'
            }
    
    def _create_test_image_content(self, camera_id: str) -> bytes:
        """创建测试图片内容"""
        try:
            # 尝试使用PIL库创建真实的PNG图片
            try:
                from PIL import Image, ImageDraw, ImageFont
                
                # 创建800x600的RGB图片
                width, height = 800, 600
                image = Image.new('RGB', (width, height), color='lightblue')
                draw = ImageDraw.Draw(image)
                
                # 绘制测试内容
                draw.rectangle([10, 10, width-10, height-10], outline='darkblue', width=3)
                
                # 添加标题
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
                
                title_text = f"Camera {camera_id} Test Image"
                if font:
                    draw.text((50, 50), title_text, fill='darkblue', font=font)
                else:
                    draw.text((50, 50), title_text, fill='darkblue')
                
                # 绘制扑克牌位置标记
                positions = [
                    (150, 150, "庄1"), (300, 150, "庄2"), (450, 150, "庄3"),
                    (150, 350, "闲1"), (300, 350, "闲2"), (450, 350, "闲3")
                ]
                
                for x, y, label in positions:
                    draw.ellipse([x-20, y-20, x+20, y+20], fill='red', outline='darkred', width=2)
                    if font:
                        draw.text((x-10, y+25), label, fill='black', font=font)
                    else:
                        draw.text((x-10, y+25), label, fill='black')
                
                # 添加时间戳
                timestamp_text = f"Generated: {get_timestamp()}"
                if font:
                    draw.text((50, height-50), timestamp_text, fill='gray', font=font)
                else:
                    draw.text((50, height-50), timestamp_text, fill='gray')
                
                # 保存到字节流
                from io import BytesIO
                img_buffer = BytesIO()
                image.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                return img_buffer.read()
                
            except ImportError:
                log_warning("PIL库未安装，使用简化的PNG生成", "PHOTO_CONTROLLER")
                return self._create_simple_png(camera_id)
                
        except Exception as e:
            log_error(f"创建测试图片失败: {e}", "PHOTO_CONTROLLER")
            return f"TEST_IMAGE_CAMERA_{camera_id}_PLACEHOLDER_DATA".encode() * 100
    
    def _create_simple_png(self, camera_id: str) -> bytes:
        """创建简单的PNG文件（不依赖PIL）"""
        try:
            import zlib
            
            width, height = 400, 300
            
            # PNG文件头
            png_signature = b'\x89PNG\r\n\x1a\n'
            
            # IHDR chunk
            ihdr_data = (
                width.to_bytes(4, 'big') +
                height.to_bytes(4, 'big') +
                b'\x08' +  # 位深度
                b'\x02' +  # 颜色类型 (RGB)
                b'\x00' +  # 压缩方法
                b'\x00' +  # 过滤方法
                b'\x00'    # 交错方法
            )
            
            ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data).to_bytes(4, 'big')
            ihdr_chunk = len(ihdr_data).to_bytes(4, 'big') + b'IHDR' + ihdr_data + ihdr_crc
            
            # 创建图像数据 (蓝色背景)
            row_data = b'\x00' + b'\x00\x80\xff' * width
            image_data = row_data * height
            
            # 压缩图像数据
            compressed_data = zlib.compress(image_data)
            
            # IDAT chunk
            idat_crc = zlib.crc32(b'IDAT' + compressed_data).to_bytes(4, 'big')
            idat_chunk = len(compressed_data).to_bytes(4, 'big') + b'IDAT' + compressed_data + idat_crc
            
            # IEND chunk
            iend_crc = zlib.crc32(b'IEND').to_bytes(4, 'big')
            iend_chunk = b'\x00\x00\x00\x00' + b'IEND' + iend_crc
            
            # 组合完整的PNG
            png_data = png_signature + ihdr_chunk + idat_chunk + iend_chunk
            
            log_success(f"创建简单PNG图片: {len(png_data)} bytes", "PHOTO_CONTROLLER")
            return png_data
            
        except Exception as e:
            log_error(f"创建简单PNG失败: {e}", "PHOTO_CONTROLLER")
            return (b'\x89PNG\r\n\x1a\n' + 
                   f"FAKE_PNG_FOR_CAMERA_{camera_id}".encode() * 50)
    
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
            
            log_success(f"摄像头 {camera_id} 拍照成功: {filename} ({file_size} bytes, {duration}s)", 
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
                    'mode': photo_result.get('mode', 'normal')
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
    
    def capture_and_process(self, camera_id: str, include_recognition: bool = True) -> Dict[str, Any]:
        """
        完整的拍照->裁剪->识别流程
        
        Args:
            camera_id: 摄像头ID
            include_recognition: 是否包含识别步骤
            
        Returns:
            完整处理结果
        """
        try:
            log_info(f"🚀 开始完整处理流程: 摄像头 {camera_id}", "PHOTO_CONTROLLER")
            
            # 步骤1: 拍照
            log_info("📸 步骤1: 拍照", "PHOTO_CONTROLLER")
            photo_result = self.take_photo_by_id(camera_id)
            
            if photo_result['status'] != 'success':
                return format_error_response(f"拍照失败: {photo_result['message']}", "PHOTO_FAILED")
            
            # 步骤2: 裁剪
            log_info("✂️  步骤2: 图片裁剪", "PHOTO_CONTROLLER")
            cut_result = self.image_cutter.cut_camera_marks(camera_id)
            
            if cut_result['status'] != 'success':
                return format_error_response(f"图片裁剪失败: {cut_result['message']}", "CUT_FAILED")
            
            # 准备返回结果
            result_data = {
                'camera_id': camera_id,
                'photo_result': photo_result['data'],
                'cut_result': cut_result['data'],
                'timestamp': get_timestamp()
            }
            
            # 步骤3: 识别（可选）
            if include_recognition:
                log_info("🎯 步骤3: 扑克识别", "PHOTO_CONTROLLER")
                recognition_result = self.poker_recognizer.recognize_camera(camera_id)
                
                if recognition_result['status'] == 'success':
                    result_data['recognition_result'] = recognition_result['data']
                    log_success("🎉 完整处理流程成功完成（包含识别）", "PHOTO_CONTROLLER")
                else:
                    result_data['recognition_error'] = recognition_result['message']
                    log_warning(f"识别步骤失败: {recognition_result['message']}", "PHOTO_CONTROLLER")
            else:
                log_success("🎉 拍照和裁剪流程成功完成", "PHOTO_CONTROLLER")
            
            return format_success_response(
                f"摄像头 {camera_id} 处理完成",
                data=result_data
            )
            
        except Exception as e:
            log_error(f"完整处理流程失败: {e}", "PHOTO_CONTROLLER")
            return format_error_response(f"处理流程失败: {str(e)}", "PROCESS_ERROR")
    
    def batch_capture_and_process(self, camera_ids: list = None, include_recognition: bool = True) -> Dict[str, Any]:
        """
        批量处理多个摄像头
        
        Args:
            camera_ids: 摄像头ID列表，如果为None则处理所有启用的摄像头
            include_recognition: 是否包含识别步骤
            
        Returns:
            批量处理结果
        """
        try:
            # 获取要处理的摄像头列表
            if camera_ids is None:
                # 获取所有启用的摄像头
                enabled_cameras = self.image_cutter.get_enabled_cameras()
                camera_ids = [cam['id'] for cam in enabled_cameras]
            
            if not camera_ids:
                return format_error_response("没有摄像头需要处理", "NO_CAMERAS")
            
            log_info(f"🚀 开始批量处理 {len(camera_ids)} 个摄像头", "PHOTO_CONTROLLER")
            
            # 批量处理结果
            all_results = {}
            success_count = 0
            
            for camera_id in camera_ids:
                log_info(f"处理摄像头: {camera_id}", "PHOTO_CONTROLLER")
                
                result = self.capture_and_process(camera_id, include_recognition)
                all_results[camera_id] = result
                
                if result['status'] == 'success':
                    success_count += 1
                
                log_info("-" * 50, "PHOTO_CONTROLLER")
            
            # 汇总结果
            log_info("=" * 50, "PHOTO_CONTROLLER")
            log_info(f"📊 批量处理完成: {success_count}/{len(camera_ids)} 成功", "PHOTO_CONTROLLER")
            
            # 如果包含识别，生成最终识别结果
            final_recognition = None
            if include_recognition:
                recognition_results = {}
                for camera_id, result in all_results.items():
                    if (result['status'] == 'success' and 
                        'recognition_result' in result['data']):
                        recognition_results[camera_id] = result['data']['recognition_result']
                
                if recognition_results:
                    final_recognition = self.poker_recognizer.generate_final_result(recognition_results)
                    
                    # 保存最终识别结果
                    self.poker_recognizer.save_result_to_file(final_recognition)
            
            return format_success_response(
                "批量处理完成",
                data={
                    'total_cameras': len(camera_ids),
                    'success_count': success_count,
                    'camera_results': all_results,
                    'final_recognition': final_recognition,
                    'timestamp': get_timestamp()
                }
            )
            
        except Exception as e:
            log_error(f"批量处理失败: {e}", "PHOTO_CONTROLLER")
            return format_error_response(f"批量处理失败: {str(e)}", "BATCH_PROCESS_ERROR")
    
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
    
    def cleanup_old_photos(self, keep_count: int = 50, camera_id: str = None) -> Dict[str, Any]:
        """清理旧的图片文件"""
        try:
            if not self.image_dir.exists():
                return format_success_response("图片目录不存在，无需清理", data={'deleted_count': 0})
            
            if camera_id:
                pattern = f"camera_{camera_id}.png"
            else:
                pattern = "camera_*.png"
            
            photo_files = list(self.image_dir.glob(pattern))
            photo_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            if len(photo_files) <= keep_count:
                return format_success_response(
                    f"图片数量 ({len(photo_files)}) 未超过限制 ({keep_count})，无需清理",
                    data={'deleted_count': 0}
                )
            
            # 删除超出数量的文件
            deleted_count = 0
            total_size_deleted = 0
            
            for file_to_delete in photo_files[keep_count:]:
                try:
                    file_size = get_file_size(file_to_delete)
                    file_to_delete.unlink()
                    deleted_count += 1
                    total_size_deleted += file_size
                except OSError as e:
                    log_error(f"删除图片文件失败 {file_to_delete}: {e}", "PHOTO_CONTROLLER")
            
            log_info(f"清理旧图片完成: 删除 {deleted_count} 个文件，释放 {total_size_deleted} 字节", "PHOTO_CONTROLLER")
            
            return format_success_response(
                f"清理完成，删除了 {deleted_count} 个旧图片文件",
                data={
                    'deleted_count': deleted_count,
                    'size_freed': total_size_deleted,
                    'remaining_count': len(photo_files) - deleted_count
                }
            )
            
        except Exception as e:
            log_error(f"清理图片文件失败: {e}", "PHOTO_CONTROLLER")
            return format_error_response(f"清理失败: {str(e)}", "CLEANUP_ERROR")

# 创建全局实例
integrated_photo_controller = IntegratedPhotoController()

# 导出主要函数
def take_photo_by_id(camera_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """根据摄像头ID拍照"""
    return integrated_photo_controller.take_photo_by_id(camera_id, options)

def capture_and_process(camera_id: str, include_recognition: bool = True) -> Dict[str, Any]:
    """完整的拍照->裁剪->识别流程"""
    return integrated_photo_controller.capture_and_process(camera_id, include_recognition)

def batch_capture_and_process(camera_ids: list = None, include_recognition: bool = True) -> Dict[str, Any]:
    """批量处理多个摄像头"""
    return integrated_photo_controller.batch_capture_and_process(camera_ids, include_recognition)

def get_photo_status(camera_id: str = None) -> Dict[str, Any]:
    """获取拍照状态"""
    return integrated_photo_controller.get_photo_status(camera_id)

def list_photos(camera_id: str = None, limit: int = 20) -> Dict[str, Any]:
    """列出图片文件"""
    return integrated_photo_controller.list_photos(camera_id, limit)

def cleanup_old_photos(keep_count: int = 50, camera_id: str = None) -> Dict[str, Any]:
    """清理旧图片文件"""
    return integrated_photo_controller.cleanup_old_photos(keep_count, camera_id)

if __name__ == "__main__":
    # 测试整合拍照控制器
    print("🧪 测试整合拍照控制器")
    
    try:
        # 测试完整流程
        result = capture_and_process("001", include_recognition=True)
        print(f"完整处理流程: {result['status']}")
        
        if result['status'] == 'success':
            data = result['data']
            print(f"  拍照: ✅")
            print(f"  裁剪: ✅ ({data['cut_result']['success_count']}/{data['cut_result']['total_marks']})")
            if 'recognition_result' in data:
                print(f"  识别: ✅")
            else:
                print(f"  识别: ❌ {data.get('recognition_error', '未知错误')}")
        
        print("✅ 整合拍照控制器测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()_success("ffmpeg可用，支持RTSP拍照", "PHOTO_CONTROLLER")
            else:
                self.ffmpeg_available = False
                log_warning("ffmpeg不可用，将使用模拟拍照", "PHOTO_CONTROLLER")
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            self.ffmpeg_available = False
            log_warning("ffmpeg检查失败，将使用模拟拍照", "PHOTO_CONTROLLER")
    
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
            # 验证摄像头ID
            if not validate_camera_id(camera_id):
                return format_error_response("摄像头ID格式无效", "INVALID_CAMERA_ID")
            
            # 检查摄像头配置是否存在
            camera_result = get_camera_by_id(camera_id)
            if camera_result['status'] != 'success':
                return format_error_response(f"摄像头 {camera_id} 配置不存在", "CAMERA_NOT_FOUND")
            
            camera_config = camera_result['data']['camera']
            
            # 记录拍照开始状态
            self._update_photo_status(camera_id, 'starting', '开始拍照...')
            
            # 执行拍照
            start_time = time.time()
            photo_result = self._execute_photo_capture(camera_id, camera_config, options)
            duration = round(time.time() - start_time, 2)
            
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
            self._update_photo_status(camera_id, 'error', str(e))
            log_error(f"摄像头 {camera_id} 拍照过程出错: {e}", "PHOTO_CONTROLLER")
            return format_error_response(f"拍照过程出错: {str(e)}", "PHOTO_ERROR")
    
    def _execute_photo_capture(self, camera_id: str, camera_config: Dict[str, Any], 
                              options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行实际的拍照操作
        
        Args:
            camera_id: 摄像头ID
            camera_config: 摄像头配置
            options: 拍照选项
            
        Returns:
            拍照执行结果
        """
        try:
            if self.ffmpeg_available and self._has_rtsp_config(camera_config):
                # 使用ffmpeg进行RTSP拍照
                return self._rtsp_photo_capture(camera_id, camera_config)
            else:
                # 使用模拟拍照
                return self._simulate_photo_capture(camera_id, options)
                
        except Exception as e:
            log_error(f"执行拍照时出错: {e}", "PHOTO_CONTROLLER")
            return {
                'success': False,
                'error': f'拍照执行错误: {str(e)}'
            }
    
    def _has_rtsp_config(self, camera_config: Dict[str, Any]) -> bool:
        """检查摄像头是否有RTSP配置"""
        required_fields = ['ip', 'username', 'password', 'port', 'stream_path']
        return all(field in camera_config for field in required_fields)
    
    def _rtsp_photo_capture(self, camera_id: str, camera_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用ffmpeg进行RTSP拍照
        
        Args:
            camera_id: 摄像头ID
            camera_config: 摄像头配置
            
        Returns:
            拍照结果
        """
        try:
            # 构建RTSP URL
            ip = camera_config['ip']
            username = camera_config['username']
            password = camera_config['password']
            port = camera_config['port']
            stream_path = camera_config['stream_path']
            
            rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}{stream_path}"
            
            # 生成输出文件名
            filename = f"camera_{camera_id}.png"
            output_path = self.image_dir / filename
            
            # 构建ffmpeg命令
            ffmpeg_cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-stimeout', '10000000',
                '-i', rtsp_url,
                '-vframes', '1',
                '-q:v', '2',
                '-y',  # 覆盖输出文件
                str(output_path)
            ]
            
            log