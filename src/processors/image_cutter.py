#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片裁剪处理模块 - 整合自 local/cut.py
功能: 根据标记位置裁剪摄像头图片
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

from PIL import Image, ImageDraw
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径


from src.core.utils import (
    get_config_dir, get_image_dir, get_result_dir,
    safe_json_load, format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)

class ImageCutter:
    """图片裁剪处理类 - 整合自 cut.py"""
    
    def __init__(self, config_path=None):
        """
        初始化图片裁剪系统
        
        Args:
            config_path: 配置文件路径，默认使用标准配置路径
        """
        # 设置路径
        self.setup_paths()
        
        # 加载配置
        self.config_path = config_path or (get_config_dir() / "camera.json")
        self.config = None
        self.load_config()
        
        # 设置日志
        self.setup_logging()
        
        log_info("图片裁剪系统初始化完成", "IMAGE_CUTTER")
    
    def setup_paths(self):
        """设置各种路径"""
        self.image_dir = get_image_dir()
        self.cut_dir = self.image_dir / "cut"
        self.result_dir = get_result_dir()
        
        # 创建必要的目录
        self.cut_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(exist_ok=True)
        
    def load_config(self):
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
            self.config = safe_json_load(self.config_path, {})
            if not self.config:
                raise ValueError("配置文件内容为空或格式错误")
            
            log_success(f"配置文件加载成功: {self.config_path}", "IMAGE_CUTTER")
            
        except Exception as e:
            log_error(f"配置文件加载失败: {e}", "IMAGE_CUTTER")
            self.config = None
    
    def setup_logging(self):
        """设置日志系统"""
        try:
            log_format = '%(asctime)s - %(levelname)s - %(message)s'
            
            logging.basicConfig(
                level=logging.INFO,
                format=log_format,
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler(self.result_dir / "image_cutter.log", encoding='utf-8')
                ]
            )
            
            self.logger = logging.getLogger(__name__)
            
        except Exception as e:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            log_warning(f"日志设置失败，使用默认配置: {e}", "IMAGE_CUTTER")
    
    def get_enabled_cameras(self):
        """获取启用的摄像头列表"""
        if not self.config:
            return []
        
        return [cam for cam in self.config.get('cameras', []) if cam.get('enabled', True)]
    
    def get_camera_by_id(self, camera_id):
        """根据ID获取摄像头配置"""
        if not self.config:
            return None
        
        for camera in self.config.get('cameras', []):
            if camera['id'] == camera_id:
                return camera
        
        return None
    
    def check_image_exists(self, camera):
        """检查摄像头图片是否存在"""
        image_file = self.image_dir / camera['filename']
        return image_file.exists()
    
    def get_valid_marks(self, camera):
        """获取有效的标记位置"""
        mark_positions = camera.get('mark_positions', {})
        valid_marks = {}
        
        for position_key, position_data in mark_positions.items():
            if (position_data.get('marked', False) and 
                position_data.get('x', 0) >= 0 and 
                position_data.get('y', 0) >= 0 and
                position_data.get('width', 0) > 0 and 
                position_data.get('height', 0) > 0):
                valid_marks[position_key] = position_data
        
        return valid_marks
    
    def cut_single_mark(self, image, mark_name, mark_data, camera_id):
        """
        裁剪单个标记区域
        
        Args:
            image: PIL Image对象
            mark_name: 标记名称
            mark_data: 标记数据
            camera_id: 摄像头ID
            
        Returns:
            Dict: 裁剪结果
        """
        try:
            # 获取标记区域坐标 (JSON中保存的是实际图片的中心点坐标)
            center_x = int(mark_data['x'])  # 中心点X坐标
            center_y = int(mark_data['y'])  # 中心点Y坐标
            width = int(mark_data['width'])     # 实际宽度
            height = int(mark_data['height'])   # 实际高度
            
            # 获取图片实际尺寸
            img_width, img_height = image.size
            
            log_info(f"🔍 {mark_name} JSON坐标(中心点): ({center_x}, {center_y}), 尺寸: {width}x{height}", "IMAGE_CUTTER")
            log_info(f"📐 图片尺寸: {img_width}x{img_height}", "IMAGE_CUTTER")
            
            # 🎯 核心修正：JSON中的坐标已经是实际图片坐标，直接使用
            # 不需要缩放转换，因为biaoji.html已经保存了实际图片坐标
            
            # 从中心点坐标转换为左上角坐标 (用于PIL裁剪)
            left = center_x - width // 2    # 左上角X = 中心X - 宽度/2
            top = center_y - height // 2    # 左上角Y = 中心Y - 高度/2
            right = left + width            # 右下角X = 左上角X + 宽度
            bottom = top + height           # 右下角Y = 左上角Y + 高度
            
            log_info(f"🔄 坐标转换: 中心点({center_x}, {center_y}) -> 左上角({left}, {top})", "IMAGE_CUTTER")
            log_info(f"✂️  裁剪区域: ({left}, {top}) -> ({right}, {bottom})", "IMAGE_CUTTER")
            
            # 确保坐标在图片范围内
            left = max(0, left)
            top = max(0, top)
            right = min(right, img_width)
            bottom = min(bottom, img_height)
            
            # 重新计算实际裁剪尺寸(防止边界溢出后尺寸改变)
            actual_width = right - left
            actual_height = bottom - top
            
            log_info(f"🛡️  边界修正后: ({left}, {top}) -> ({right}, {bottom}), 实际尺寸: {actual_width}x{actual_height}", "IMAGE_CUTTER")
            
            # 确保裁剪区域有效
            if actual_width <= 0 or actual_height <= 0:
                raise ValueError(f"裁剪区域无效: 宽度={actual_width}, 高度={actual_height}")
            
            # 裁剪图片 - PIL的crop使用 (left, top, right, bottom)
            cropped = image.crop((left, top, right, bottom))
            
            # 生成输出文件名
            output_filename = f"camera_{camera_id}_{mark_name}.png"
            output_path = self.cut_dir / output_filename
            
            # 保存裁剪后的图片
            cropped.save(output_path, 'PNG')
            
            # 获取文件大小
            file_size = output_path.stat().st_size
            
            log_success(f"✅ 裁剪成功: {output_filename} ({cropped.size[0]}×{cropped.size[1]}, {file_size/1024:.1f}KB)", "IMAGE_CUTTER")
            
            return {
                'success': True,
                'filename': output_filename,
                'path': str(output_path),
                'size': cropped.size,
                'file_size': file_size,
                'original_coords': (center_x, center_y, width, height),  # 原始中心点坐标
                'crop_coords': (left, top, right, bottom),               # 实际裁剪坐标
                'actual_size': (actual_width, actual_height)             # 实际裁剪尺寸
            }
            
        except Exception as e:
            log_error(f"❌ 裁剪失败 {mark_name}: {e}", "IMAGE_CUTTER")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cut_camera_marks(self, camera_id):
        """
        裁剪指定摄像头的所有标记
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            Dict: 裁剪结果
        """
        try:
            # 获取摄像头配置
            camera = self.get_camera_by_id(camera_id)
            if not camera:
                return format_error_response(f"摄像头 {camera_id} 不存在", "CAMERA_NOT_FOUND")
            
            # 检查摄像头是否启用
            if not camera.get('enabled', True):
                return format_error_response(f"摄像头 {camera_id} 已禁用", "CAMERA_DISABLED")
            
            # 检查图片文件是否存在
            if not self.check_image_exists(camera):
                return format_error_response(f"图片文件 {camera['filename']} 不存在", "IMAGE_NOT_FOUND")
            
            # 获取有效标记
            valid_marks = self.get_valid_marks(camera)
            if not valid_marks:
                return format_error_response(f"摄像头 {camera_id} 没有有效标记", "NO_VALID_MARKS")
            
            log_info(f"📷 开始裁剪摄像头: {camera['name']} (ID: {camera_id})", "IMAGE_CUTTER")
            log_info(f"📁 图片文件: {camera['filename']}", "IMAGE_CUTTER")
            log_info(f"🎯 标记数量: {len(valid_marks)}", "IMAGE_CUTTER")
            
            # 打开图片
            image_path = self.image_dir / camera['filename']
            with Image.open(image_path) as image:
                log_info(f"📐 图片尺寸: {image.size[0]}×{image.size[1]}", "IMAGE_CUTTER")
                
                # 裁剪所有标记
                results = {}
                success_count = 0
                
                for mark_name, mark_data in valid_marks.items():
                    result = self.cut_single_mark(image, mark_name, mark_data, camera_id)
                    results[mark_name] = result
                    
                    if result['success']:
                        success_count += 1
                
                # 统计结果
                total_marks = len(valid_marks)
                log_info(f"📊 裁剪完成: {success_count}/{total_marks} 成功", "IMAGE_CUTTER")
                
                return format_success_response(
                    f"摄像头 {camera_id} 裁剪完成",
                    data={
                        'camera_id': camera_id,
                        'camera_name': camera['name'],
                        'total_marks': total_marks,
                        'success_count': success_count,
                        'results': results
                    }
                )
                
        except Exception as e:
            log_error(f"❌ 裁剪摄像头 {camera_id} 失败: {e}", "IMAGE_CUTTER")
            return format_error_response(f"裁剪失败: {str(e)}", "CUT_ERROR")
    
    def cut_all_cameras(self):
        """裁剪所有启用摄像头的标记"""
        try:
            enabled_cameras = self.get_enabled_cameras()
            
            if not enabled_cameras:
                return format_error_response("没有启用的摄像头", "NO_ENABLED_CAMERAS")
            
            log_info(f"🚀 开始批量裁剪 {len(enabled_cameras)} 个摄像头", "IMAGE_CUTTER")
            
            all_results = {}
            total_success = 0
            total_cameras = 0
            
            for camera in enabled_cameras:
                camera_id = camera['id']
                result = self.cut_camera_marks(camera_id)
                all_results[camera_id] = result
                
                if result['status'] == 'success':
                    total_success += 1
                total_cameras += 1
                
                # 间隔处理
                if camera != enabled_cameras[-1]:
                    log_info("-" * 50, "IMAGE_CUTTER")
            
            # 总体统计
            log_info("=" * 50, "IMAGE_CUTTER")
            log_info(f"📊 批量裁剪完成: {total_success}/{total_cameras} 个摄像头成功", "IMAGE_CUTTER")
            
            # 统计总裁剪数量
            total_cuts = 0
            successful_cuts = 0
            
            for result in all_results.values():
                if result['status'] == 'success':
                    total_cuts += result['data']['total_marks']
                    successful_cuts += result['data']['success_count']
            
            if total_cuts > 0:
                log_info(f"🎯 总裁剪数量: {successful_cuts}/{total_cuts} 个标记成功", "IMAGE_CUTTER")
            
            return format_success_response(
                "批量裁剪完成",
                data={
                    'total_cameras': total_cameras,
                    'success_cameras': total_success,
                    'total_cuts': total_cuts,
                    'successful_cuts': successful_cuts,
                    'results': all_results
                }
            )
            
        except Exception as e:
            log_error(f"❌ 批量裁剪失败: {e}", "IMAGE_CUTTER")
            return format_error_response(f"批量裁剪失败: {str(e)}", "BATCH_CUT_ERROR")
    
    def list_cameras(self):
        """列出所有摄像头状态"""
        if not self.config:
            print("❌ 配置文件未加载")
            return
        
        cameras = self.config.get('cameras', [])
        
        print(f"\n📷 摄像头列表 (共 {len(cameras)} 个):")
        print("=" * 80)
        
        for camera in cameras:
            camera_id = camera['id']
            name = camera['name']
            enabled = camera.get('enabled', True)
            filename = camera['filename']
            
            # 检查状态
            status_parts = []
            
            if not enabled:
                status_parts.append("❌ 禁用")
            else:
                status_parts.append("✅ 启用")
            
            # 检查图片文件
            if self.check_image_exists(camera):
                status_parts.append("📸 图片存在")
            else:
                status_parts.append("📸 图片缺失")
            
            # 检查标记
            valid_marks = self.get_valid_marks(camera)
            if valid_marks:
                status_parts.append(f"🎯 {len(valid_marks)}个标记")
            else:
                status_parts.append("🎯 无标记")
            
            status = " | ".join(status_parts)
            
            print(f"ID: {camera_id} | {name}")
            print(f"    文件: {filename}")
            print(f"    状态: {status}")
            
            if valid_marks:
                marks_list = ", ".join(valid_marks.keys())
                print(f"    标记: {marks_list}")
            
            print()
    
    def get_cut_images_for_camera(self, camera_id):
        """获取指定摄像头的所有裁剪图片"""
        cut_images = {}
        positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        for position in positions:
            image_filename = f"camera_{camera_id}_{position}.png"
            image_path = self.cut_dir / image_filename
            
            if image_path.exists():
                cut_images[position] = image_path
            else:
                log_warning(f"⚠️  图片不存在: {image_filename}", "IMAGE_CUTTER")
        
        return cut_images

if __name__ == "__main__":
    # 测试图片裁剪功能
    print("🧪 测试图片裁剪模块")
    
    try:
        cutter = ImageCutter()
        
        # 列出摄像头状态
        cutter.list_cameras()
        
        # 测试裁剪单个摄像头
        result = cutter.cut_camera_marks("001")
        print(f"裁剪结果: {result}")
        
        print("✅ 图片裁剪模块测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()