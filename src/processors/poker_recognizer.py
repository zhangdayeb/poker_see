#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv8扑克牌识别模块
功能: 使用YOLOv8模型识别单张扑克牌图片，返回花色和点数
用法: python poker_recognizer.py <图片路径>
模型: src/config/yolov8/best.pt
"""

import sys
import os
import json
from pathlib import Path

def get_project_root():
    """获取项目根目录"""
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir
    
    # 向上查找项目根目录（包含main.py的目录）
    while project_root.parent != project_root:
        if (project_root / "main.py").exists():
            break
        project_root = project_root.parent
    
    return project_root

def load_yolov8_model():
    """加载YOLOv8模型"""
    try:
        from ultralytics import YOLO
        
        # 获取模型路径
        project_root = get_project_root()
        model_path = project_root / "src" / "config" / "yolov8" / "best.pt"
        
        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        print(f"加载模型: {model_path}")
        model = YOLO(str(model_path))
        
        return model, str(model_path)
        
    except ImportError:
        raise ImportError("请安装ultralytics库: pip install ultralytics")
    except Exception as e:
        raise Exception(f"模型加载失败: {str(e)}")

def parse_yolo_results(results):
    """解析YOLO识别结果"""
    try:
        if not results or len(results) == 0:
            return None
        
        # 获取第一个结果
        result = results[0]
        
        # 检查是否有检测结果
        if result.boxes is None or len(result.boxes) == 0:
            return None
        
        # 获取置信度最高的检测结果
        boxes = result.boxes
        confidences = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy()
        
        # 找到置信度最高的检测
        max_conf_idx = confidences.argmax()
        best_confidence = float(confidences[max_conf_idx])
        best_class = int(classes[max_conf_idx])
        
        # 获取类别名称
        class_names = result.names  # 模型的类别名称字典
        if best_class in class_names:
            class_name = class_names[best_class]
        else:
            class_name = f"class_{best_class}"
        
        return {
            "class_id": best_class,
            "class_name": class_name,
            "confidence": best_confidence,
            "total_detections": len(boxes)
        }
        
    except Exception as e:
        raise Exception(f"解析YOLO结果失败: {str(e)}")

def parse_card_name(class_name):
    """解析扑克牌类别名称"""
    try:
        # 扑克牌花色和点数映射
        suit_mapping = {
            'spades': {'name': '黑桃', 'symbol': '♠️', 'en': 'spades'},
            'hearts': {'name': '红桃', 'symbol': '♥️', 'en': 'hearts'},
            'diamonds': {'name': '方块', 'symbol': '♦️', 'en': 'diamonds'},
            'clubs': {'name': '梅花', 'symbol': '♣️', 'en': 'clubs'},
            's': {'name': '黑桃', 'symbol': '♠️', 'en': 'spades'},
            'h': {'name': '红桃', 'symbol': '♥️', 'en': 'hearts'},
            'd': {'name': '方块', 'symbol': '♦️', 'en': 'diamonds'},
            'c': {'name': '梅花', 'symbol': '♣️', 'en': 'clubs'}
        }
        
        rank_mapping = {
            'A': 'A', 'a': 'A',
            '2': '2', '3': '3', '4': '4', '5': '5',
            '6': '6', '7': '7', '8': '8', '9': '9', '10': '10',
            'J': 'J', 'j': 'J',
            'Q': 'Q', 'q': 'Q', 
            'K': 'K', 'k': 'K',
            'T': '10'  # 有时10用T表示
        }
        
        # 尝试解析不同格式的类别名称
        class_name = class_name.lower().strip()
        
        suit = None
        rank = None
        
        # 格式1: "spades_A", "hearts_K" 等
        if '_' in class_name:
            parts = class_name.split('_')
            if len(parts) == 2:
                suit_part, rank_part = parts
                if suit_part in suit_mapping:
                    suit = suit_mapping[suit_part]
                if rank_part.upper() in rank_mapping:
                    rank = rank_mapping[rank_part.upper()]
        
        # 格式2: "SA", "HK", "D10" 等
        elif len(class_name) >= 2:
            suit_char = class_name[0]
            rank_part = class_name[1:]
            
            if suit_char in suit_mapping:
                suit = suit_mapping[suit_char]
            if rank_part.upper() in rank_mapping:
                rank = rank_mapping[rank_part.upper()]
        
        # 格式3: 直接包含花色和点数信息
        else:
            # 检查是否包含花色关键词
            for key, value in suit_mapping.items():
                if key in class_name:
                    suit = value
                    break
            
            # 检查是否包含点数关键词
            for key, value in rank_mapping.items():
                if key.lower() in class_name:
                    rank = value
                    break
        
        # 如果解析失败，返回原始类别名称
        if suit is None or rank is None:
            return {
                "suit": "unknown",
                "rank": "unknown",
                "suit_name": "未知",
                "suit_symbol": "?",
                "display_name": class_name,
                "parsed": False
            }
        
        return {
            "suit": suit['en'],
            "rank": rank,
            "suit_name": suit['name'],
            "suit_symbol": suit['symbol'],
            "display_name": f"{suit['symbol']}{rank}",
            "parsed": True
        }
        
    except Exception as e:
        return {
            "suit": "error",
            "rank": "error",
            "suit_name": "解析错误",
            "suit_symbol": "?",
            "display_name": f"解析失败: {str(e)}",
            "parsed": False
        }

def recognize_poker_card(image_path):
    """
    使用YOLOv8识别单张扑克牌
    
    Args:
        image_path (str): 图片路径
        
    Returns:
        dict: 识别结果
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"图片文件不存在: {image_path}"
            }
        
        print(f"正在识别: {image_path}")
        
        # 加载YOLOv8模型
        try:
            model, model_path = load_yolov8_model()
        except Exception as e:
            return {
                "success": False,
                "error": f"模型加载失败: {str(e)}"
            }
        
        # 执行推理
        try:
            print("执行YOLOv8推理...")
            results = model(image_path, verbose=False)  # verbose=False 减少输出
        except Exception as e:
            return {
                "success": False,
                "error": f"推理失败: {str(e)}"
            }
        
        # 解析结果
        try:
            yolo_result = parse_yolo_results(results)
            if yolo_result is None:
                return {
                    "success": False,
                    "error": "未检测到扑克牌"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"结果解析失败: {str(e)}"
            }
        
        # 解析扑克牌信息
        card_info = parse_card_name(yolo_result["class_name"])
        
        # 获取图片尺寸
        try:
            import cv2
            image = cv2.imread(image_path)
            if image is not None:
                height, width = image.shape[:2]
                image_size = {"width": width, "height": height}
            else:
                image_size = {"width": 0, "height": 0}
        except:
            image_size = {"width": 0, "height": 0}
        
        # 构建最终结果
        result = {
            "success": True,
            "suit": card_info["suit"],
            "rank": card_info["rank"],
            "suit_symbol": card_info["suit_symbol"],
            "suit_name": card_info["suit_name"],
            "display_name": card_info["display_name"],
            "confidence": round(yolo_result["confidence"], 3),
            "image_path": image_path,
            "image_size": image_size,
            "model_info": {
                "model_path": model_path,
                "class_id": yolo_result["class_id"],
                "class_name": yolo_result["class_name"],
                "total_detections": yolo_result["total_detections"],
                "parsed_successfully": card_info["parsed"]
            }
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"识别异常: {str(e)}"
        }

def main():
    """主函数"""
    print("YOLOv8扑克牌识别器")
    print("=" * 40)
    
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("用法: python poker_recognizer.py <图片路径>")
        print("示例: python poker_recognizer.py src/image/cut/camera_001_zhuang_1.png")
        sys.exit(1)
    
    # 获取图片路径
    image_path = sys.argv[1]
    
    # 如果是相对路径，转换为绝对路径
    if not os.path.isabs(image_path):
        project_root = get_project_root()
        image_path = project_root / image_path
        image_path = str(image_path)
    
    # 执行识别
    result = recognize_poker_card(image_path)
    
    # 输出结果
    if result["success"]:
        print("✅ 识别成功!")
        print(f"花色: {result['suit_name']} ({result['suit_symbol']})")
        print(f"点数: {result['rank']}")
        print(f"显示: {result['display_name']}")
        print(f"置信度: {result['confidence']:.3f}")
        print(f"图片尺寸: {result['image_size']['width']}×{result['image_size']['height']}")
        print(f"模型路径: {result['model_info']['model_path']}")
        print(f"检测类别: {result['model_info']['class_name']} (ID: {result['model_info']['class_id']})")
        print(f"检测数量: {result['model_info']['total_detections']}")
    else:
        print("❌ 识别失败!")
        print(f"错误: {result['error']}")
    
    # 输出JSON格式结果（供其他程序调用）
    print("\n" + "=" * 40)
    print("JSON结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()