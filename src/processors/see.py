#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极简扑克识别工具 - see.py
功能: 拍照 → 切图 → 识别 → 输出结果
用法: python src/processors/see.py --camera 001
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# 固定位置列表
POSITIONS = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='极简扑克识别工具')
    parser.add_argument('--camera', type=str, required=True, help='摄像头ID (如: 001)')
    args = parser.parse_args()
    return args.camera

def print_error_and_exit(error_msg, details=None):
    """输出错误JSON并退出"""
    result = {
        "success": False,
        "error": error_msg,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        result["details"] = details
    
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(1)

# 设置项目路径
def setup_project_paths():
    """设置项目路径"""
    current_file = Path(__file__).resolve()
    project_root = current_file
    while project_root.parent != project_root:
        if (project_root / "main.py").exists():
            break
        project_root = project_root.parent
    
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

# 设置路径
PROJECT_ROOT = setup_project_paths()

def take_photo(camera_id):
    """执行拍照 - 直接调用函数"""
    try:
        from src.processors.photo_controller import take_photo_silent
        
        result = take_photo_silent(camera_id)
        return result["success"]
        
    except ImportError as e:
        print_error_and_exit("拍照模块导入失败", str(e))
    except Exception as e:
        print_error_and_exit("拍照异常", str(e))

def cut_image(camera_id):
    """执行切图 - 直接调用函数"""
    try:
        from src.processors.image_cutter import process_image_silent
        
        # 构建图片路径
        image_path = PROJECT_ROOT / "src" / "image" / f"camera_{camera_id}.png"
        
        if not image_path.exists():
            print_error_and_exit("拍照文件不存在")
        
        result = process_image_silent(str(image_path))
        return result["success"]
        
    except ImportError as e:
        print_error_and_exit("切图模块导入失败", str(e))
    except Exception as e:
        print_error_and_exit("切图异常", str(e))

def recognize_single_position(camera_id, position):
    """识别单个位置 - 直接调用函数"""
    try:
        from src.processors.poker_hybrid_recognizer import recognize_single_card_silent
        
        # 构建图片路径
        main_image = PROJECT_ROOT / "src" / "image" / "cut" / f"camera_{camera_id}_{position}.png"
        left_image = PROJECT_ROOT / "src" / "image" / "cut" / f"camera_{camera_id}_{position}_left.png"
        
        # 检查主图片是否存在
        if not main_image.exists():
            return {
                "success": False,
                "error": "图片不存在"
            }
        
        # 调用识别函数
        left_path = str(left_image) if left_image.exists() else None
        result = recognize_single_card_silent(str(main_image), left_path)
        
        if result["success"]:
            return {
                "success": True,
                "card": result.get("display_name", "未知"),
                "confidence": result.get("confidence", 0.0)
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "识别失败")
            }
            
    except ImportError as e:
        return {
            "success": False,
            "error": f"识别模块导入失败: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def recognize_all_positions(camera_id):
    """识别所有位置"""
    results = {}
    successful_cards = []
    successful_count = 0
    
    for position in POSITIONS:
        result = recognize_single_position(camera_id, position)
        results[position] = result
        
        if result["success"]:
            successful_count += 1
            if result["card"] != "未知":
                successful_cards.append(result["card"])
    
    # 计算成功率
    success_rate = (successful_count / len(POSITIONS)) * 100
    
    return {
        "success": successful_count > 0,
        "camera_id": camera_id,
        "timestamp": datetime.now().isoformat(),
        "positions": results,
        "summary": {
            "total": len(POSITIONS),
            "successful": successful_count,
            "failed": len(POSITIONS) - successful_count,
            "success_rate": f"{success_rate:.1f}%",
            "cards": successful_cards
        }
    }

def recognize_camera(camera_id):
    """
    供其他模块调用的摄像头识别函数
    
    Args:
        camera_id: 摄像头ID (如: "001")
        
    Returns:
        dict: 识别结果字典
    """
    start_time = time.time()
    
    try:
        # 步骤1: 拍照
        if not take_photo(camera_id):
            return {
                "success": False,
                "error": "拍照失败",
                "timestamp": datetime.now().isoformat()
            }
        
        # 步骤2: 切图
        if not cut_image(camera_id):
            return {
                "success": False,
                "error": "切图失败", 
                "timestamp": datetime.now().isoformat()
            }
        
        # 步骤3: 识别所有位置
        results = recognize_all_positions(camera_id)
        
        # 添加处理时间
        processing_time = time.time() - start_time
        results["processing_time"] = round(processing_time, 1)
        
        return results
        
    except Exception as e:
        return {
            "success": False,
            "error": f"处理异常: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

def recognize_camera_json(camera_id):
    """
    供其他模块调用的JSON字符串版本
    
    Args:
        camera_id: 摄像头ID (如: "001")
        
    Returns:
        str: JSON格式的识别结果
    """
    result = recognize_camera(camera_id)
    return json.dumps(result, ensure_ascii=False)

def main():
    """主函数"""
    start_time = time.time()
    
    # 解析参数
    camera_id = parse_args()
    
    # 步骤1: 拍照
    if not take_photo(camera_id):
        print_error_and_exit("拍照失败")
    
    # 步骤2: 切图
    if not cut_image(camera_id):
        print_error_and_exit("切图失败")
    
    # 步骤3: 识别所有位置
    results = recognize_all_positions(camera_id)
    
    # 添加处理时间
    processing_time = time.time() - start_time
    results["processing_time"] = round(processing_time, 1)
    
    # 步骤4: 输出结果
    print(json.dumps(results, ensure_ascii=False))
    
    # 根据识别结果设置退出码
    sys.exit(0 if results["success"] else 1)

if __name__ == "__main__":
    main()