#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片裁剪程序
功能: 根据标记位置裁剪摄像头图片
作者: AI助手
版本: 1.0
"""

import os

import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw
import logging
from datetime import datetime

class ImageCutter:
    def __init__(self, config_path="../config/camera.json"):
        """
        初始化图片裁剪系统
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = None
        self.logger = None
        
        # 设置路径
        self.setup_paths()
        
        # 加载配置
        self.load_config()
        
        # 设置日志
        self.setup_logging()
        
        self.logger.info("图片裁剪系统初始化完成")
    
    def setup_paths(self):
        """设置各种路径"""
        # 获取当前脚本目录
        self.script_dir = Path(__file__).parent.absolute()
        self.project_root = self.script_dir.parent
        
        # 设置各个目录路径
        self.config_dir = self.project_root / "config"
        self.image_dir = self.project_root / "image"
        self.cut_dir = self.image_dir / "cut"
        self.result_dir = self.project_root / "result"
        
        # 创建必要的目录
        self.cut_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(exist_ok=True)
        
    def load_config(self):
        """加载配置文件"""
        try:
            config_file = self.config_dir / "camera.json"
            
            if not config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {config_file}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            print(f"✅ 配置文件加载成功: {config_file}")
            
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            self.config = None
    
    def setup_logging(self):
        """设置日志系统"""
        try:
            # 设置日志格式
            log_format = '%(asctime)s - %(levelname)s - %(message)s'
            
            # 配置日志
            logging.basicConfig(
                level=logging.INFO,
                format=log_format,
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler(self.result_dir / "cut.log", encoding='utf-8')
                ]
            )
            
            self.logger = logging.getLogger(__name__)
            
        except Exception as e:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            self.logger.warning(f"日志设置失败，使用默认配置: {e}")
    
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
        """裁剪单个标记区域"""
        try:
            # 获取标记区域坐标
            x = int(mark_data['x'])
            y = int(mark_data['y'])
            width = int(mark_data['width'])
            height = int(mark_data['height'])
            
            # 获取图片实际尺寸
            img_width, img_height = image.size
            
            self.logger.info(f"🔍 {mark_name} 原始坐标: ({x}, {y}), 尺寸: {width}x{height}")
            self.logger.info(f"📐 图片尺寸: {img_width}x{img_height}")
            
            # 检查坐标是否需要缩放转换
            # 标记工具中图片固定显示为 2560x1440，但实际图片可能不同
            display_width = 2560
            display_height = 1440
            
            # 计算缩放比例
            scale_x = img_width / display_width
            scale_y = img_height / display_height
            
            # 转换坐标到实际图片尺寸
            actual_x = int(x * scale_x)
            actual_y = int(y * scale_y)
            actual_width = int(width * scale_x)
            actual_height = int(height * scale_y)
            
            self.logger.info(f"🔄 缩放比例: X={scale_x:.3f}, Y={scale_y:.3f}")
            self.logger.info(f"✂️  转换后坐标: ({actual_x}, {actual_y}), 尺寸: {actual_width}x{actual_height}")
            
            # 确保坐标在图片范围内
            actual_x = max(0, min(actual_x, img_width - 1))
            actual_y = max(0, min(actual_y, img_height - 1))
            
            # 确保裁剪区域不超出图片边界
            right = min(actual_x + actual_width, img_width)
            bottom = min(actual_y + actual_height, img_height)
            
            # 确保裁剪区域有效
            if right <= actual_x or bottom <= actual_y:
                raise ValueError(f"裁剪区域无效: ({actual_x}, {actual_y}) -> ({right}, {bottom})")
            
            # 裁剪图片
            cropped = image.crop((actual_x, actual_y, right, bottom))
            
            # 生成输出文件名
            output_filename = f"camera_{camera_id}_{mark_name}.png"
            output_path = self.cut_dir / output_filename
            
            # 保存裁剪后的图片
            cropped.save(output_path, 'PNG')
            
            # 获取文件大小
            file_size = output_path.stat().st_size
            
            self.logger.info(f"✅ 裁剪成功: {output_filename} ({cropped.size[0]}×{cropped.size[1]}, {file_size/1024:.1f}KB)")
            
            return {
                'success': True,
                'filename': output_filename,
                'size': cropped.size,
                'file_size': file_size,
                'original_coords': (x, y, width, height),
                'actual_coords': (actual_x, actual_y, actual_width, actual_height),
                'scale': (scale_x, scale_y)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 裁剪失败 {mark_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cut_camera_marks(self, camera_id):
        """裁剪指定摄像头的所有标记"""
        # 获取摄像头配置
        camera = self.get_camera_by_id(camera_id)
        if not camera:
            self.logger.error(f"❌ 摄像头 {camera_id} 不存在")
            return {'success': False, 'error': f'摄像头 {camera_id} 不存在'}
        
        # 检查摄像头是否启用
        if not camera.get('enabled', True):
            self.logger.warning(f"⚠️  摄像头 {camera_id} ({camera['name']}) 已禁用，跳过裁剪")
            return {'success': False, 'error': f'摄像头 {camera_id} 已禁用'}
        
        # 检查图片文件是否存在
        if not self.check_image_exists(camera):
            self.logger.warning(f"⚠️  摄像头 {camera_id} 的图片文件 {camera['filename']} 不存在，跳过裁剪")
            return {'success': False, 'error': f'图片文件 {camera["filename"]} 不存在'}
        
        # 获取有效标记
        valid_marks = self.get_valid_marks(camera)
        if not valid_marks:
            self.logger.warning(f"⚠️  摄像头 {camera_id} ({camera['name']}) 没有有效标记，跳过裁剪")
            return {'success': False, 'error': f'摄像头 {camera_id} 没有有效标记'}
        
        self.logger.info(f"📷 开始裁剪摄像头: {camera['name']} (ID: {camera_id})")
        self.logger.info(f"📁 图片文件: {camera['filename']}")
        self.logger.info(f"🎯 标记数量: {len(valid_marks)}")
        
        try:
            # 打开图片
            image_path = self.image_dir / camera['filename']
            with Image.open(image_path) as image:
                self.logger.info(f"📐 图片尺寸: {image.size[0]}×{image.size[1]}")
                
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
                self.logger.info(f"📊 裁剪完成: {success_count}/{total_marks} 成功")
                
                return {
                    'success': True,
                    'camera_id': camera_id,
                    'camera_name': camera['name'],
                    'total_marks': total_marks,
                    'success_count': success_count,
                    'results': results
                }
                
        except Exception as e:
            self.logger.error(f"❌ 打开图片失败: {e}")
            return {'success': False, 'error': f'打开图片失败: {e}'}
    
    def cut_all_cameras(self):
        """裁剪所有启用摄像头的标记"""
        enabled_cameras = self.get_enabled_cameras()
        
        if not enabled_cameras:
            self.logger.warning("⚠️  没有启用的摄像头")
            return {'success': False, 'error': '没有启用的摄像头'}
        
        self.logger.info(f"🚀 开始批量裁剪 {len(enabled_cameras)} 个摄像头")
        
        all_results = {}
        total_success = 0
        total_cameras = 0
        
        for camera in enabled_cameras:
            camera_id = camera['id']
            result = self.cut_camera_marks(camera_id)
            all_results[camera_id] = result
            
            if result['success']:
                total_success += 1
            total_cameras += 1
            
            # 间隔处理
            if camera != enabled_cameras[-1]:
                self.logger.info("-" * 50)
        
        # 总体统计
        self.logger.info("=" * 50)
        self.logger.info(f"📊 批量裁剪完成: {total_success}/{total_cameras} 个摄像头成功")
        
        # 统计总裁剪数量
        total_cuts = 0
        successful_cuts = 0
        
        for result in all_results.values():
            if result['success']:
                total_cuts += result['total_marks']
                successful_cuts += result['success_count']
        
        if total_cuts > 0:
            self.logger.info(f"🎯 总裁剪数量: {successful_cuts}/{total_cuts} 个标记成功")
        
        return {
            'success': True,
            'total_cameras': total_cameras,
            'success_cameras': total_success,
            'total_cuts': total_cuts,
            'successful_cuts': successful_cuts,
            'results': all_results
        }
    
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
    
    def run_diagnostics(self):
        """运行系统诊断"""
        self.logger.info("🔍 开始系统诊断...")
        
        # 检查配置
        self.logger.info("1. 检查配置文件...")
        if self.config:
            cameras_count = len(self.config.get('cameras', []))
            enabled_count = len(self.get_enabled_cameras())
            self.logger.info(f"   ✅ 配置正常，共 {cameras_count} 个摄像头，{enabled_count} 个启用")
        else:
            self.logger.error("   ❌ 配置文件加载失败")
            return
        
        # 检查目录
        self.logger.info("2. 检查目录结构...")
        dirs_to_check = [
            ('配置目录', self.config_dir),
            ('图片目录', self.image_dir),
            ('裁剪输出目录', self.cut_dir),
            ('结果目录', self.result_dir)
        ]
        
        for name, path in dirs_to_check:
            if path.exists():
                self.logger.info(f"   ✅ {name}: {path}")
            else:
                self.logger.error(f"   ❌ {name}不存在: {path}")
        
        # 检查PIL库
        self.logger.info("3. 检查图片处理库...")
        try:
            from PIL import Image
            self.logger.info("   ✅ PIL (Pillow) 库正常")
        except ImportError:
            self.logger.error("   ❌ PIL 库未安装，请运行: pip install Pillow")
        
        # 检查摄像头和图片
        self.logger.info("4. 检查摄像头状态...")
        enabled_cameras = self.get_enabled_cameras()
        
        for camera in enabled_cameras:
            camera_id = camera['id']
            name = camera['name']
            
            # 检查图片文件
            if self.check_image_exists(camera):
                # 检查标记
                valid_marks = self.get_valid_marks(camera)
                if valid_marks:
                    self.logger.info(f"   ✅ {name} (ID: {camera_id}): 图片存在, {len(valid_marks)}个有效标记")
                else:
                    self.logger.warning(f"   ⚠️  {name} (ID: {camera_id}): 图片存在, 但无有效标记")
            else:
                self.logger.warning(f"   ⚠️  {name} (ID: {camera_id}): 图片文件缺失 ({camera['filename']})")
        
        self.logger.info("🔍 系统诊断完成")

def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(
        description='图片裁剪程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python cut.py                    # 裁剪所有启用摄像头的标记
  python cut.py -c 001             # 裁剪指定摄像头的标记
  python cut.py -l                 # 列出所有摄像头状态
  python cut.py -d                 # 运行系统诊断
  python cut.py --debug            # 启用调试模式，显示详细坐标转换信息
        '''
    )
    
    parser.add_argument('-c', '--camera', type=str, help='指定摄像头ID进行裁剪')
    parser.add_argument('-l', '--list', action='store_true', help='列出所有摄像头状态')
    parser.add_argument('-d', '--diagnostics', action='store_true', help='运行系统诊断')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    print("✂️  图片裁剪程序 v1.0")
    print("=" * 50)
    
    try:
        # 创建裁剪系统实例
        cutter = ImageCutter()
        
        # 设置调试模式
        if args.debug:
            cutter.logger.setLevel(logging.DEBUG)
            print("🔍 调试模式已启用")
        
        if args.list:
            # 列出摄像头状态
            cutter.list_cameras()
            
        elif args.diagnostics:
            # 运行系统诊断
            cutter.run_diagnostics()
            
        elif args.camera:
            # 裁剪指定摄像头
            print(f"📷 裁剪指定摄像头: {args.camera}")
            result = cutter.cut_camera_marks(args.camera)
            
            if result['success']:
                print(f"🎉 裁剪完成!")
                print(f"摄像头: {result['camera_name']}")
                print(f"成功: {result['success_count']}/{result['total_marks']} 个标记")
                
                # 显示详细结果
                if args.debug:
                    print("\n📊 详细结果:")
                    for mark_name, mark_result in result['results'].items():
                        if mark_result['success']:
                            coords = mark_result.get('original_coords', (0, 0, 0, 0))
                            actual = mark_result.get('actual_coords', (0, 0, 0, 0))
                            scale = mark_result.get('scale', (1.0, 1.0))
                            print(f"  {mark_name}:")
                            print(f"    原始坐标: ({coords[0]}, {coords[1]}) {coords[2]}x{coords[3]}")
                            print(f"    实际坐标: ({actual[0]}, {actual[1]}) {actual[2]}x{actual[3]}")
                            print(f"    缩放比例: {scale[0]:.3f} x {scale[1]:.3f}")
            else:
                print(f"😞 裁剪失败: {result['error']}")
                
        else:
            # 裁剪所有摄像头
            print("🚀 开始批量裁剪所有启用的摄像头...")
            result = cutter.cut_all_cameras()
            
            if result['success']:
                print(f"🎉 批量裁剪完成!")
                print(f"摄像头: {result['success_cameras']}/{result['total_cameras']} 成功")
                if result['total_cuts'] > 0:
                    print(f"标记: {result['successful_cuts']}/{result['total_cuts']} 成功")
            else:
                print(f"😞 批量裁剪失败: {result['error']}")
        
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()