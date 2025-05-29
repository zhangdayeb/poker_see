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
import subprocess
from pathlib import Path
from datetime import datetime

# 固定位置列表
POSITIONS = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']

def get_project_root():
    """获取项目根目录"""
    current_file = Path(__file__).resolve()
    # 从 src/processors/see.py 向上找到项目根目录
    return current_file.parent.parent.parent

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

def take_photo(camera_id):
    """执行拍照"""
    project_root = get_project_root()
    photo_script = project_root / "src" / "processors" / "photo_controller.py"
    
    cmd = [sys.executable, str(photo_script), "--camera", camera_id]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(project_root)
        )
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print_error_and_exit("拍照超时")
    except Exception as e:
        print_error_and_exit("拍照异常", str(e))

def cut_image(camera_id):
    """执行切图"""
    project_root = get_project_root()
    cutter_script = project_root / "src" / "processors" / "image_cutter.py"
    image_path = project_root / "src" / "image" / f"camera_{camera_id}.png"
    
    # 检查拍照文件是否存在
    if not image_path.exists():
        print_error_and_exit("拍照文件不存在")
    
    cmd = [sys.executable, str(cutter_script), str(image_path)]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(project_root)
        )
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print_error_and_exit("切图超时")
    except Exception as e:
        print_error_and_exit("切图异常", str(e))

def recognize_single_position(camera_id, position):
    """识别单个位置"""
    project_root = get_project_root()
    recognizer_script = project_root / "src" / "processors" / "poker_hybrid_recognizer.py"
    
    # 构建图片路径
    cut_dir = project_root / "src" / "image" / "cut"
    main_image = cut_dir / f"camera_{camera_id}_{position}.png"
    left_image = cut_dir / f"camera_{camera_id}_{position}_left.png"
    
    # 检查主图片是否存在
    if not main_image.exists():
        return {
            "success": False,
            "error": "图片不存在"
        }
    
    # 构建识别命令
    cmd = [sys.executable, str(recognizer_script), "--main", str(main_image)]
    if left_image.exists():
        cmd.extend(["--left", str(left_image)])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(project_root)
        )
        
        if result.returncode == 0:
            # 解析识别输出，提取关键信息
            output_lines = result.stdout.strip().split('\n')
            
            # 查找最终结果行
            for line in reversed(output_lines):
                if '最终结果:' in line:
                    # 解析结果行，提取卡牌和置信度
                    try:
                        if '置信度:' in line:
                            parts = line.split('最终结果:')[1].strip()
                            card_part = parts.split('(置信度:')[0].strip()
                            confidence_part = parts.split('置信度:')[1].split(',')[0].strip().rstrip(')')
                            
                            return {
                                "success": True,
                                "card": card_part,
                                "confidence": float(confidence_part)
                            }
                    except:
                        pass
            
            # 如果没有找到标准格式，返回基本成功
            return {
                "success": True,
                "card": "未知",
                "confidence": 0.0
            }
        else:
            return {
                "success": False,
                "error": "识别失败"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "识别超时"
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