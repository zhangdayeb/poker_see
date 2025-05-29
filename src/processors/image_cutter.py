#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能图片裁剪器 - 基于标记位置自动裁剪扑克牌区域（支持横图智能旋转）
用法: python image_cutter.py <图片路径>
示例: python image_cutter.py src/image/camera_001.png

功能:
1. 根据配置文件中的标记位置裁剪6个区域
2. 每个区域再裁剪左上角1/4部分
3. 智能识别横图并旋转为竖图（针对zhuang_3和xian_3）
"""

import sys
import os
import json
import cv2
import numpy as np
from pathlib import Path
from PIL import Image

def get_project_root():
    """获取项目根目录"""
    current_file = Path(__file__).resolve()
    project_root = current_file
    
    # 向上查找项目根目录（包含main.py的目录）
    while project_root.parent != project_root:
        if (project_root / "main.py").exists():
            break
        project_root = project_root.parent
    
    return project_root

def load_camera_config(camera_id):
    """
    加载指定摄像头的配置
    
    Args:
        camera_id: 摄像头ID (如 "001")
        
    Returns:
        dict: 摄像头配置，如果找不到返回None
    """
    try:
        project_root = get_project_root()
        config_path = project_root / "src" / "config" / "camera.json"
        
        if not config_path.exists():
            print(f"❌ 配置文件不存在: {config_path}")
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 查找指定摄像头
        for camera in config.get('cameras', []):
            if camera.get('id') == camera_id:
                return camera
        
        print(f"❌ 找不到摄像头ID: {camera_id}")
        return None
        
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return None

def extract_camera_id_from_filename(image_path):
    """
    从文件名中提取摄像头ID
    
    Args:
        image_path: 图片路径 (如 "src/image/camera_001.png")
        
    Returns:
        str: 摄像头ID (如 "001")，提取失败返回None
    """
    try:
        filename = Path(image_path).name  # 获取文件名
        # 文件名格式: camera_001.png
        if filename.startswith('camera_') and '.' in filename:
            # 提取ID部分 (去掉 camera_ 前缀和文件扩展名)
            camera_id = filename.replace('camera_', '').split('.')[0]
            return camera_id
        return None
    except:
        return None

def get_valid_marks(camera_config):
    """
    获取有效的标记位置
    
    Args:
        camera_config: 摄像头配置
        
    Returns:
        dict: 有效标记位置 {position_name: position_data}
    """
    mark_positions = camera_config.get('mark_positions', {})
    valid_marks = {}
    
    # 标准的6个位置
    positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
    
    for position in positions:
        if position in mark_positions:
            position_data = mark_positions[position]
            
            # 检查标记是否有效（已标记且坐标有效）
            if (position_data.get('marked', False) and 
                position_data.get('x', 0) > 0 and 
                position_data.get('y', 0) > 0 and
                position_data.get('width', 0) > 0 and 
                position_data.get('height', 0) > 0):
                
                valid_marks[position] = position_data
                print(f"✅ 找到有效标记: {position} - 中心({position_data['x']}, {position_data['y']}) 尺寸({position_data['width']}×{position_data['height']})")
    
    return valid_marks

def should_rotate_image(position_name: str, width: int, height: int) -> bool:
    """
    判断是否需要旋转图片
    
    Args:
        position_name: 位置名称
        width: 图片宽度
        height: 图片高度
        
    Returns:
        bool: 是否需要旋转
    """
    # 只对特定位置的横图进行旋转
    horizontal_positions = ['zhuang_3', 'xian_3']
    is_horizontal = width > height * 1.2  # 宽度比高度大20%以上认为是横图
    
    return position_name in horizontal_positions and is_horizontal

def rotate_image_to_vertical(pil_image, position_name: str):
    """
    将横图旋转为竖图
    
    Args:
        pil_image: PIL图像对象
        position_name: 位置名称
        
    Returns:
        PIL.Image: 旋转后的图像
    """
    try:
        width, height = pil_image.size
        
        if should_rotate_image(position_name, width, height):
            # 逆时针旋转90度，使横图变竖图
            rotated_image = pil_image.rotate(90, expand=True)
            new_width, new_height = rotated_image.size
            
            print(f"  ↻ 横图旋转: {width}×{height} -> {new_width}×{new_height}")
            return rotated_image
        
        return pil_image
        
    except Exception as e:
        print(f"❌ 图片旋转失败: {e}")
        return pil_image

def crop_region(image, position_name, position_data):
    """
    裁剪指定区域（支持智能旋转）
    
    Args:
        image: PIL Image对象
        position_name: 位置名称
        position_data: 位置数据 (包含中心坐标和尺寸)
        
    Returns:
        PIL.Image: 裁剪后的图片，失败返回None
    """
    try:
        # 获取标记区域的中心坐标和尺寸
        center_x = int(position_data['x'])     # 中心点X坐标
        center_y = int(position_data['y'])     # 中心点Y坐标
        width = int(position_data['width'])    # 区域宽度
        height = int(position_data['height'])  # 区域高度
        
        # 获取图片尺寸
        img_width, img_height = image.size
        
        print(f"🔍 {position_name}: 中心坐标({center_x}, {center_y}), 尺寸({width}×{height})")
        
        # 从中心坐标计算裁剪区域的边界
        # 左上角坐标 = 中心坐标 - 尺寸/2
        left = center_x - width // 2
        top = center_y - height // 2
        right = left + width
        bottom = top + height
        
        print(f"🔍 {position_name}: 裁剪区域({left}, {top}) -> ({right}, {bottom})")
        
        # 确保坐标在图片范围内
        left = max(0, left)
        top = max(0, top)
        right = min(right, img_width)
        bottom = min(bottom, img_height)
        
        # 检查裁剪区域是否有效
        if right <= left or bottom <= top:
            print(f"❌ {position_name}: 裁剪区域无效")
            return None
        
        print(f"✂️  {position_name}: 修正后区域({left}, {top}) -> ({right}, {bottom})")
        
        # 执行裁剪
        cropped = image.crop((left, top, right, bottom))
        
        # 新增：智能旋转处理
        cropped_width, cropped_height = cropped.size
        if should_rotate_image(position_name, cropped_width, cropped_height):
            print(f"  🔄 检测到横图 {position_name}，准备旋转...")
            cropped = rotate_image_to_vertical(cropped, position_name)
        
        return cropped
        
    except Exception as e:
        print(f"❌ {position_name}: 裁剪失败 - {e}")
        return None

def crop_left_quarter(image, position_name: str = ""):
    """
    裁剪图片左上角的1/4部分
    
    Args:
        image: PIL Image对象
        position_name: 位置名称（用于日志）
        
    Returns:
        PIL.Image: 左上角1/4的图片
    """
    try:
        width, height = image.size
        
        # 计算1/4区域的尺寸
        quarter_width = width // 2
        quarter_height = height // 2
        
        # 裁剪左上角区域 (0, 0) -> (width/2, height/2)
        left_quarter = image.crop((0, 0, quarter_width, quarter_height))
        
        print(f"  ↳ {position_name} 左上角1/4: {quarter_width}×{quarter_height}")
        
        return left_quarter
        
    except Exception as e:
        print(f"❌ {position_name} 左上角裁剪失败: {e}")
        return None

def process_image(image_path):
    """
    处理单张图片（支持智能旋转）
    
    Args:
        image_path: 图片路径
        
    Returns:
        bool: 处理是否成功
    """
    try:
        print(f"🖼️  开始处理图片: {image_path}")
        
        # 检查图片是否存在
        image_path = Path(image_path)
        if not image_path.exists():
            print(f"❌ 图片文件不存在: {image_path}")
            return False
        
        # 提取摄像头ID
        camera_id = extract_camera_id_from_filename(image_path.name)
        if not camera_id:
            print(f"❌ 无法从文件名提取摄像头ID: {image_path.name}")
            return False
        
        print(f"📷 检测到摄像头ID: {camera_id}")
        
        # 加载摄像头配置
        camera_config = load_camera_config(camera_id)
        if not camera_config:
            return False
        
        print(f"✅ 摄像头配置加载成功: {camera_config.get('name', camera_id)}")
        
        # 获取有效标记
        valid_marks = get_valid_marks(camera_config)
        if not valid_marks:
            print(f"❌ 摄像头 {camera_id} 没有有效标记")
            return False
        
        print(f"🎯 找到 {len(valid_marks)} 个有效标记")
        
        # 打开图片
        try:
            with Image.open(image_path) as image:
                print(f"📐 图片尺寸: {image.size[0]}×{image.size[1]}")
                
                # 设置输出目录
                output_dir = image_path.parent / "cut"
                output_dir.mkdir(exist_ok=True)
                
                success_count = 0
                total_count = len(valid_marks)
                rotation_count = 0  # 统计旋转次数
                
                # 处理每个标记位置
                for position_name, position_data in valid_marks.items():
                    print(f"\n🔄 处理位置: {position_name}")
                    
                    # 第一步：裁剪标记区域（支持智能旋转）
                    cropped = crop_region(image, position_name, position_data)
                    if cropped is None:
                        continue
                    
                    # 检查是否进行了旋转
                    original_width = int(position_data['width'])
                    original_height = int(position_data['height'])
                    if should_rotate_image(position_name, original_width, original_height):
                        rotation_count += 1
                    
                    # 保存完整裁剪图片
                    main_filename = f"camera_{camera_id}_{position_name}.png"
                    main_path = output_dir / main_filename
                    cropped.save(main_path, 'PNG')
                    print(f"💾 保存: {main_filename} ({cropped.size[0]}×{cropped.size[1]})")
                    
                    # 第二步：裁剪左上角1/4
                    left_quarter = crop_left_quarter(cropped, position_name)
                    if left_quarter is not None:
                        # 保存左上角1/4图片
                        left_filename = f"camera_{camera_id}_{position_name}_left.png"
                        left_path = output_dir / left_filename
                        left_quarter.save(left_path, 'PNG')
                        print(f"💾 保存: {left_filename} ({left_quarter.size[0]}×{left_quarter.size[1]})")
                    
                    success_count += 1
                
                print(f"\n📊 处理完成: {success_count}/{total_count} 个位置成功")
                if rotation_count > 0:
                    print(f"🔄 智能旋转: {rotation_count} 个横图已旋转为竖图")
                print(f"📁 输出目录: {output_dir}")
                
                return success_count > 0
                
        except Exception as e:
            print(f"❌ 图片处理失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 处理异常: {e}")
        return False

def main():
    """主函数"""
    print("🎯 智能图片裁剪器 v2.1 (支持横图智能旋转)")
    print("=" * 50)
    
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("用法: python image_cutter.py <图片路径>")
        print("示例: python image_cutter.py src/image/camera_001.png")
        print("     python image_cutter.py /path/to/camera_002.png")
        print("\n新功能:")
        print("✨ 自动识别 zhuang_3 和 xian_3 位置的横图")
        print("🔄 智能旋转横图为竖图，优化OCR识别效果")
        print("📏 旋转判断条件: 宽度 > 高度 × 1.2")
        sys.exit(1)
    
    # 获取图片路径
    image_path = sys.argv[1]
    
    # 如果是相对路径，转换为绝对路径
    if not os.path.isabs(image_path):
        project_root = get_project_root()
        image_path = project_root / image_path
    
    # 处理图片
    success = process_image(image_path)
    
    if success:
        print("\n✅ 智能图片裁剪完成!")
        print("💡 横图已智能旋转为竖图，提高OCR识别准确率")
    else:
        print("\n❌ 图片裁剪失败!")
        sys.exit(1)

if __name__ == "__main__":
    main()