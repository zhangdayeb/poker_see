#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO扑克牌识别器 - 基于YOLOv8的扑克牌识别
功能: 使用YOLOv8模型识别完整扑克牌，返回花色和点数
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

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
        
        project_root = get_project_root()
        model_path = project_root / "src" / "config" / "yolov8" / "best.pt"
        
        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        print(f"[YOLO] 加载模型: {model_path}")
        model = YOLO(str(model_path))
        
        return model, str(model_path)
        
    except ImportError:
        raise ImportError("请安装ultralytics库: pip install ultralytics")
    except Exception as e:
        raise Exception(f"YOLO模型加载失败: {str(e)}")

def parse_yolo_results(results):
    """解析YOLO识别结果"""
    try:
        if not results or len(results) == 0:
            return None
        
        result = results[0]
        
        if result.boxes is None or len(result.boxes) == 0:
            return None
        
        # 获取置信度最高的检测结果
        boxes = result.boxes
        confidences = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy()
        
        max_conf_idx = confidences.argmax()
        best_confidence = float(confidences[max_conf_idx])
        best_class = int(classes[max_conf_idx])
        
        # 获取类别名称
        class_names = result.names
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
    """解析扑克牌类别名称为花色和点数"""
    try:
        # 扑克牌花色映射
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
        
        # 点数映射
        rank_mapping = {
            'A': 'A', 'a': 'A',
            '2': '2', '3': '3', '4': '4', '5': '5',
            '6': '6', '7': '7', '8': '8', '9': '9', '10': '10',
            'J': 'J', 'j': 'J',
            'Q': 'Q', 'q': 'Q', 
            'K': 'K', 'k': 'K',
            'T': '10'  # 有时10用T表示
        }
        
        class_name = class_name.lower().strip()
        suit = None
        rank = None
        
        # 尝试解析不同格式
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
        
        # 如果解析失败，返回未知
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

def detect_with_yolo(image_path: str, confidence_threshold: float = 0.3) -> Dict[str, Any]:
    """
    使用YOLO检测扑克牌
    
    Args:
        image_path: 图片路径
        confidence_threshold: 置信度阈值，默认0.3 (30%)
        
    Returns:
        检测结果字典
    """
    try:
        print(f"[YOLO] 开始识别: {image_path}")
        
        # 检查文件是否存在
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"图片文件不存在: {image_path}",
                "confidence": 0.0,
                "method": "yolo"
            }
        
        # 加载YOLO模型
        try:
            model, model_path = load_yolov8_model()
        except Exception as e:
            return {
                "success": False,
                "error": f"YOLO模型加载失败: {str(e)}",
                "confidence": 0.0,
                "method": "yolo"
            }
        
        # 执行推理
        try:
            print("[YOLO] 执行推理...")
            results = model(image_path, verbose=False)
        except Exception as e:
            return {
                "success": False,
                "error": f"YOLO推理失败: {str(e)}",
                "confidence": 0.0,
                "method": "yolo"
            }
        
        # 解析结果
        try:
            yolo_result = parse_yolo_results(results)
            if yolo_result is None:
                return {
                    "success": False,
                    "error": "未检测到扑克牌",
                    "confidence": 0.0,
                    "method": "yolo"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"结果解析失败: {str(e)}",
                "confidence": 0.0,
                "method": "yolo"
            }
        
        # 检查置信度
        confidence = yolo_result["confidence"]
        print(f"[YOLO] 检测置信度: {confidence:.3f}")
        
        if confidence < confidence_threshold:
            return {
                "success": False,
                "error": f"置信度过低: {confidence:.3f} < {confidence_threshold}",
                "confidence": confidence,
                "method": "yolo",
                "raw_class_name": yolo_result["class_name"]
            }
        
        # 解析扑克牌信息
        card_info = parse_card_name(yolo_result["class_name"])
        
        # 构建成功结果
        result = {
            "success": True,
            "suit": card_info["suit"],
            "rank": card_info["rank"],
            "suit_symbol": card_info["suit_symbol"],
            "suit_name": card_info["suit_name"],
            "display_name": card_info["display_name"],
            "confidence": confidence,
            "method": "yolo",
            "model_info": {
                "model_path": model_path,
                "class_id": yolo_result["class_id"],
                "class_name": yolo_result["class_name"],
                "total_detections": yolo_result["total_detections"],
                "parsed_successfully": card_info["parsed"]
            }
        }
        
        print(f"[YOLO] 识别成功: {result['display_name']} (置信度: {confidence:.3f})")
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"YOLO识别异常: {str(e)}",
            "confidence": 0.0,
            "method": "yolo"
        }

def test_yolo_detector():
    """测试YOLO检测器"""
    print("🧪 测试YOLO扑克牌检测器")
    print("=" * 50)
    
    # 测试图片路径（需要根据实际情况调整）
    test_images = [
        "src/image/cut/camera_001_zhuang_1.png",
        "src/image/cut/camera_001_xian_1.png"
    ]
    
    for image_path in test_images:
        print(f"\n测试图片: {image_path}")
        print("-" * 30)
        
        result = detect_with_yolo(image_path)
        
        if result["success"]:
            print("✅ YOLO识别成功!")
            print(f"   花色: {result['suit_name']} ({result['suit_symbol']})")
            print(f"   点数: {result['rank']}")
            print(f"   显示: {result['display_name']}")
            print(f"   置信度: {result['confidence']:.3f}")
        else:
            print("❌ YOLO识别失败!")
            print(f"   错误: {result['error']}")
            print(f"   置信度: {result['confidence']:.3f}")

if __name__ == "__main__":
    test_yolo_detector()