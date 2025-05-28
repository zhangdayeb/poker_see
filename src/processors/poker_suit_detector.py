#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenCV扑克牌花色识别器 - 基于颜色和形状特征识别花色
功能: 识别红桃♥️、黑桃♠️、方块♦️、梅花♣️
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import cv2
import numpy as np

def preprocess_image_for_suit(image_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    预处理图片以提取花色信息
    
    Args:
        image_path: 图片路径
        
    Returns:
        (原图, HSV图)
    """
    try:
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")
        
        # 高斯模糊去噪
        blurred = cv2.GaussianBlur(image, (5, 5), 0)
        
        # 转换到HSV色彩空间
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        
        return blurred, hsv
        
    except Exception as e:
        print(f"[SUIT] 图片预处理失败: {e}")
        # 返回空数组作为备选
        empty = np.zeros((100, 100, 3), dtype=np.uint8)
        empty_hsv = np.zeros((100, 100, 3), dtype=np.uint8)
        return empty, empty_hsv

def detect_red_regions(hsv_image: np.ndarray) -> np.ndarray:
    """
    检测红色区域（红桃和方块）
    
    Args:
        hsv_image: HSV格式图片
        
    Returns:
        红色区域的二值掩码
    """
    try:
        # 红色在HSV中有两个范围
        # 范围1: 低红色 (0-10)
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        mask1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
        
        # 范围2: 高红色 (160-180)
        lower_red2 = np.array([160, 50, 50])
        upper_red2 = np.array([180, 255, 255])
        mask2 = cv2.inRange(hsv_image, lower_red2, upper_red2)
        
        # 合并两个红色范围
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # 形态学操作去除噪点
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
        
        return red_mask
        
    except Exception as e:
        print(f"[SUIT] 红色检测失败: {e}")
        return np.zeros((100, 100), dtype=np.uint8)

def detect_black_regions(hsv_image: np.ndarray) -> np.ndarray:
    """
    检测黑色区域（黑桃和梅花）
    
    Args:
        hsv_image: HSV格式图片
        
    Returns:
        黑色区域的二值掩码
    """
    try:
        # 黑色范围 (低饱和度，低亮度)
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 50, 80])
        black_mask = cv2.inRange(hsv_image, lower_black, upper_black)
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
        black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
        
        return black_mask
        
    except Exception as e:
        print(f"[SUIT] 黑色检测失败: {e}")
        return np.zeros((100, 100), dtype=np.uint8)

def analyze_shape_features(mask: np.ndarray) -> Dict[str, float]:
    """
    分析形状特征
    
    Args:
        mask: 二值掩码
        
    Returns:
        形状特征字典
    """
    try:
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return {
                "area": 0.0,
                "perimeter": 0.0,
                "circularity": 0.0,
                "aspect_ratio": 0.0,
                "extent": 0.0,
                "solidity": 0.0
            }
        
        # 选择最大轮廓
        largest_contour = max(contours, key=cv2.contourArea)
        
        # 计算各种形状特征
        area = cv2.contourArea(largest_contour)
        perimeter = cv2.arcLength(largest_contour, True)
        
        # 圆形度 (4π*面积/周长²)
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
        
        # 外接矩形
        x, y, w, h = cv2.boundingRect(largest_contour)
        aspect_ratio = float(w) / h if h > 0 else 0
        
        # 充实度 (轮廓面积/外接矩形面积)
        rect_area = w * h
        extent = area / rect_area if rect_area > 0 else 0
        
        # 凸包
        hull = cv2.convexHull(largest_contour)
        hull_area = cv2.contourArea(hull)
        solidity = area / hull_area if hull_area > 0 else 0
        
        return {
            "area": area,
            "perimeter": perimeter,
            "circularity": circularity,
            "aspect_ratio": aspect_ratio,
            "extent": extent,
            "solidity": solidity
        }
        
    except Exception as e:
        print(f"[SUIT] 形状特征分析失败: {e}")
        return {
            "area": 0.0,
            "perimeter": 0.0,
            "circularity": 0.0,
            "aspect_ratio": 0.0,
            "extent": 0.0,
            "solidity": 0.0
        }

def classify_red_suit(shape_features: Dict[str, float]) -> str:
    """
    基于形状特征分类红色花色
    
    Args:
        shape_features: 形状特征
        
    Returns:
        花色类型 ('hearts' 或 'diamonds')
    """
    try:
        circularity = shape_features.get("circularity", 0)
        aspect_ratio = shape_features.get("aspect_ratio", 0)
        solidity = shape_features.get("solidity", 0)
        
        # 红桃特征：
        # - 较高的圆形度（心形顶部是圆的）
        # - 长宽比接近1
        # - 凸包实度较低（心形有凹陷）
        
        # 方块特征：
        # - 较低的圆形度（菱形有尖角）
        # - 长宽比接近1
        # - 凸包实度较高（菱形相对规整）
        
        hearts_score = 0
        diamonds_score = 0
        
        # 圆形度评分
        if circularity > 0.6:
            hearts_score += 2
        elif circularity < 0.4:
            diamonds_score += 2
        
        # 长宽比评分
        if 0.8 <= aspect_ratio <= 1.2:
            hearts_score += 1
            diamonds_score += 1
        
        # 凸包实度评分
        if solidity < 0.8:
            hearts_score += 2  # 红桃有凹陷
        elif solidity > 0.9:
            diamonds_score += 2  # 方块较规整
        
        return "hearts" if hearts_score > diamonds_score else "diamonds"
        
    except Exception as e:
        print(f"[SUIT] 红色花色分类失败: {e}")
        return "hearts"  # 默认返回红桃

def classify_black_suit(shape_features: Dict[str, float]) -> str:
    """
    基于形状特征分类黑色花色
    
    Args:
        shape_features: 形状特征
        
    Returns:
        花色类型 ('spades' 或 'clubs')
    """
    try:
        circularity = shape_features.get("circularity", 0)
        aspect_ratio = shape_features.get("aspect_ratio", 0)
        solidity = shape_features.get("solidity", 0)
        extent = shape_features.get("extent", 0)
        
        # 黑桃特征：
        # - 较低的圆形度（有尖头）
        # - 长宽比通常大于1（纵向较长）
        # - 中等凸包实度
        
        # 梅花特征：
        # - 较低的圆形度（三个圆形组合）
        # - 长宽比接近1
        # - 较低的凸包实度（三叶形状复杂）
        
        spades_score = 0
        clubs_score = 0
        
        # 圆形度评分
        if circularity < 0.5:
            spades_score += 1
            clubs_score += 1
        
        # 长宽比评分
        if aspect_ratio > 1.1:
            spades_score += 2  # 黑桃通常较高
        elif 0.8 <= aspect_ratio <= 1.1:
            clubs_score += 2  # 梅花较方
        
        # 凸包实度评分
        if 0.7 <= solidity <= 0.85:
            spades_score += 1
        elif solidity < 0.7:
            clubs_score += 2  # 梅花形状更复杂
        
        # 充实度评分
        if extent > 0.6:
            spades_score += 1
        elif extent < 0.6:
            clubs_score += 1
        
        return "spades" if spades_score > clubs_score else "clubs"
        
    except Exception as e:
        print(f"[SUIT] 黑色花色分类失败: {e}")
        return "spades"  # 默认返回黑桃

def detect_poker_suit(image_path: str) -> Dict[str, Any]:
    """
    识别扑克牌花色 - 主要接口
    
    Args:
        image_path: 图片路径（建议使用_left.png文件）
        
    Returns:
        识别结果字典
    """
    try:
        print(f"[SUIT] 开始花色识别: {image_path}")
        
        # 检查文件是否存在
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"图片文件不存在: {image_path}",
                "method": "opencv_suit"
            }
        
        # 预处理图片
        original, hsv = preprocess_image_for_suit(image_path)
        
        # 检测红色和黑色区域
        red_mask = detect_red_regions(hsv)
        black_mask = detect_black_regions(hsv)
        
        # 计算红色和黑色区域的面积
        red_area = np.sum(red_mask > 0)
        black_area = np.sum(black_mask > 0)
        
        print(f"[SUIT] 红色区域面积: {red_area}, 黑色区域面积: {black_area}")
        
        # 判断是红色花色还是黑色花色
        if red_area > black_area and red_area > 100:  # 最小面积阈值
            # 红色花色 (红桃或方块)
            red_features = analyze_shape_features(red_mask)
            suit_type = classify_red_suit(red_features)
            
            if suit_type == "hearts":
                result = {
                    "success": True,
                    "suit": "hearts",
                    "suit_name": "红桃",
                    "suit_symbol": "♥️",
                    "color": "red",
                    "confidence": min(0.9, red_area / 1000),  # 基于面积计算置信度
                    "method": "opencv_suit",
                    "features": red_features
                }
            else:  # diamonds
                result = {
                    "success": True,
                    "suit": "diamonds",
                    "suit_name": "方块",
                    "suit_symbol": "♦️",
                    "color": "red",
                    "confidence": min(0.9, red_area / 1000),
                    "method": "opencv_suit",
                    "features": red_features
                }
                
        elif black_area > 100:  # 最小面积阈值
            # 黑色花色 (黑桃或梅花)
            black_features = analyze_shape_features(black_mask)
            suit_type = classify_black_suit(black_features)
            
            if suit_type == "spades":
                result = {
                    "success": True,
                    "suit": "spades",
                    "suit_name": "黑桃",
                    "suit_symbol": "♠️",
                    "color": "black",
                    "confidence": min(0.9, black_area / 1000),
                    "method": "opencv_suit",
                    "features": black_features
                }
            else:  # clubs
                result = {
                    "success": True,
                    "suit": "clubs",
                    "suit_name": "梅花",
                    "suit_symbol": "♣️",
                    "color": "black",
                    "confidence": min(0.9, black_area / 1000),
                    "method": "opencv_suit",
                    "features": black_features
                }
        else:
            # 未检测到明显的花色区域
            return {
                "success": False,
                "error": f"未检测到明显花色区域 (红色: {red_area}, 黑色: {black_area})",
                "method": "opencv_suit",
                "red_area": red_area,
                "black_area": black_area
            }
        
        print(f"[SUIT] 花色识别成功: {result['suit_name']} {result['suit_symbol']} (置信度: {result['confidence']:.3f})")
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"花色识别异常: {str(e)}",
            "method": "opencv_suit_exception"
        }

def test_suit_detector():
    """测试花色检测器"""
    print("🧪 测试OpenCV花色识别器")
    print("=" * 50)
    
    # 测试图片路径（左上角图片）
    test_images = [
        "src/image/cut/camera_001_zhuang_1_left.png",
        "src/image/cut/camera_001_zhuang_2_left.png",
        "src/image/cut/camera_001_xian_1_left.png"
    ]
    
    for image_path in test_images:
        print(f"\n测试图片: {image_path}")
        print("-" * 40)
        
        result = detect_poker_suit(image_path)
        
        if result["success"]:
            print("✅ 花色识别成功!")
            print(f"   花色: {result['suit_name']} ({result['suit_symbol']})")
            print(f"   颜色: {result['color']}")
            print(f"   置信度: {result['confidence']:.3f}")
            print(f"   方法: {result['method']}")
            
            # 显示形状特征
            if 'features' in result:
                features = result['features']
                print(f"   形状特征:")
                print(f"     面积: {features.get('area', 0):.1f}")
                print(f"     圆形度: {features.get('circularity', 0):.3f}")
                print(f"     长宽比: {features.get('aspect_ratio', 0):.3f}")
                print(f"     凸包实度: {features.get('solidity', 0):.3f}")
        else:
            print("❌ 花色识别失败!")
            print(f"   错误: {result['error']}")
            print(f"   方法: {result.get('method', 'unknown')}")

if __name__ == "__main__":
    test_suit_detector()