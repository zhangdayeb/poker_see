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
    cmd = f"python src/processors/photo_controller.py --camera {camera_id}"
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print_error_and_exit("拍照超时")
    except Exception as e:
        print_error_and_exit("拍照异常", str(e))

def cut_image(camera_id):
    """执行切图"""
    # 检查拍照文件是否存在
    image_path = f"src/image/camera_{camera_id}.png"
    if not Path(image_path).exists():
        print_error_and_exit("拍照文件不存在")
    
    cmd = f"python src/processors/image_cutter.py {image_path}"
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print_error_and_exit("切图超时")
    except Exception as e:
        print_error_and_exit("切图异常", str(e))

def recognize_single_position(camera_id, position):
    """识别单个位置"""
    # 构建图片路径
    main_image = f"src/image/cut/camera_{camera_id}_{position}.png"
    left_image = f"src/image/cut/camera_{camera_id}_{position}_left.png"
    
    # 检查主图片是否存在
    if not Path(main_image).exists():
        return {
            "success": False,
            "error": "图片不存在"
        }
    
    # 构建识别命令
    cmd = f"python src/processors/poker_hybrid_recognizer.py --main {main_image}"
    if Path(left_image).exists():
        cmd += f" --left {left_image}"
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15
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