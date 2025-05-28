#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR扑克牌字符识别器 - 识别扑克牌左上角的字符
功能: 使用OCR技术识别A, 2-10, J, Q, K等字符
"""

import sys
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import cv2
import numpy as np

def preprocess_image_for_ocr(image_path: str) -> np.ndarray:
    """
    预处理图片以提高OCR识别率
    
    Args:
        image_path: 图片路径
        
    Returns:
        预处理后的图片数组
    """
    try:
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")
        
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 图像增强
        # 1. 高斯模糊去噪
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # 2. 对比度增强 (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)
        
        # 3. 二值化 - 尝试多种方法
        # 方法1: OTSU自适应阈值
        _, binary1 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 方法2: 自适应阈值
        binary2 = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
        
        # 选择更清晰的二值化结果（基于白色像素比例）
        white_ratio1 = np.sum(binary1 == 255) / binary1.size
        white_ratio2 = np.sum(binary2 == 255) / binary2.size
        
        # 选择白色像素比例适中的结果（避免过度曝光或过暗）
        if 0.1 <= white_ratio1 <= 0.8:
            binary = binary1
        elif 0.1 <= white_ratio2 <= 0.8:
            binary = binary2
        else:
            binary = binary1  # 默认使用OTSU
        
        # 4. 形态学操作清理噪点
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # 5. 尺寸调整（放大以提高识别率）
        height, width = cleaned.shape
        scale_factor = 3
        enlarged = cv2.resize(cleaned, (width * scale_factor, height * scale_factor), 
                            interpolation=cv2.INTER_CUBIC)
        
        return enlarged
        
    except Exception as e:
        print(f"[OCR] 图片预处理失败: {e}")
        # 返回原始灰度图作为备选
        try:
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            return image if image is not None else np.zeros((100, 100), dtype=np.uint8)
        except:
            return np.zeros((100, 100), dtype=np.uint8)

def normalize_poker_character(raw_text: str) -> Optional[str]:
    """
    标准化识别出的字符
    
    Args:
        raw_text: OCR识别的原始文本
        
    Returns:
        标准化后的扑克牌字符
    """
    try:
        if not raw_text:
            return None
        
        # 清理文本：移除空格、特殊字符
        cleaned = re.sub(r'[^\w]', '', raw_text.upper().strip())
        
        # 扑克牌字符映射表
        char_mapping = {
            # 标准字符
            'A': 'A', 'ACE': 'A',
            '2': '2', 'TWO': '2', 'II': '2',
            '3': '3', 'THREE': '3', 'III': '3',
            '4': '4', 'FOUR': '4', 'IV': '4',
            '5': '5', 'FIVE': '5', 'V': '5',
            '6': '6', 'SIX': '6', 'VI': '6',
            '7': '7', 'SEVEN': '7', 'VII': '7',
            '8': '8', 'EIGHT': '8', 'VIII': '8',
            '9': '9', 'NINE': '9', 'IX': '9',
            '10': '10', 'TEN': '10', 'X': '10', 'T': '10',
            'J': 'J', 'JACK': 'J', 'KNAVE': 'J',
            'Q': 'Q', 'QUEEN': 'Q',
            'K': 'K', 'KING': 'K',
            
            # 常见误识别修正
            '0': '10', 'O': '10', 'D': '10',  # 10经常被识别为0/O/D
            '1': 'A', 'I': 'A', 'L': 'A',     # A经常被识别为1/I/L
            'G': '6', 'S': '5', 'B': '8',     # 数字误识别
            'H': 'A', 'R': 'A', 'P': 'A',     # A的变形
            'C': '6', 'U': 'J', 'N': 'J',     # 其他误识别
        }
        
        # 直接匹配
        if cleaned in char_mapping:
            return char_mapping[cleaned]
        
        # 模糊匹配：检查是否包含关键字符
        for key, value in char_mapping.items():
            if key in cleaned or cleaned in key:
                return value
        
        # 长度为1的情况，尝试数字识别
        if len(cleaned) == 1:
            if cleaned.isdigit():
                digit = int(cleaned)
                if 2 <= digit <= 9:
                    return str(digit)
        
        # 长度为2的情况，可能是10
        if len(cleaned) == 2:
            if cleaned.isdigit() and cleaned == '10':
                return '10'
            elif '1' in cleaned and ('0' in cleaned or 'O' in cleaned):
                return '10'
        
        return None
        
    except Exception as e:
        print(f"[OCR] 字符标准化失败: {e}")
        return None

def detect_with_easyocr(image_path: str) -> Dict[str, Any]:
    """使用EasyOCR识别字符"""
    try:
        import easyocr
        
        # 创建EasyOCR读取器（仅英文，提高速度和准确性）
        reader = easyocr.Reader(['en'], gpu=False)
        
        # 预处理图片
        processed_image = preprocess_image_for_ocr(image_path)
        
        # OCR识别
        results = reader.readtext(processed_image, detail=1, paragraph=False)
        
        if not results:
            return {
                "success": False,
                "error": "EasyOCR未识别到文字",
                "raw_results": [],
                "method": "easyocr"
            }
        
        # 处理识别结果
        best_result = None
        best_confidence = 0
        
        for (bbox, text, confidence) in results:
            normalized = normalize_poker_character(text)
            if normalized and confidence > best_confidence:
                best_result = normalized
                best_confidence = confidence
        
        if best_result:
            return {
                "success": True,
                "character": best_result,
                "confidence": best_confidence,
                "raw_results": results,
                "method": "easyocr"
            }
        else:
            return {
                "success": False,
                "error": "无法识别有效的扑克牌字符",
                "raw_results": results,
                "method": "easyocr"
            }
            
    except ImportError:
        return {
            "success": False,
            "error": "EasyOCR库未安装，请运行: pip install easyocr",
            "method": "easyocr"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"EasyOCR识别失败: {str(e)}",
            "method": "easyocr"
        }

def detect_with_paddleocr(image_path: str) -> Dict[str, Any]:
    """使用PaddleOCR识别字符"""
    try:
        from paddleocr import PaddleOCR
        
        # 创建PaddleOCR实例
        ocr = PaddleOCR(use_angle_cls=False, lang='en', use_gpu=False, show_log=False)
        
        # 预处理图片
        processed_image = preprocess_image_for_ocr(image_path)
        
        # OCR识别
        results = ocr.ocr(processed_image, cls=False)
        
        if not results or not results[0]:
            return {
                "success": False,
                "error": "PaddleOCR未识别到文字",
                "raw_results": [],
                "method": "paddleocr"
            }
        
        # 处理识别结果
        best_result = None
        best_confidence = 0
        
        for line in results[0]:
            bbox, (text, confidence) = line
            normalized = normalize_poker_character(text)
            if normalized and confidence > best_confidence:
                best_result = normalized
                best_confidence = confidence
        
        if best_result:
            return {
                "success": True,
                "character": best_result,
                "confidence": best_confidence,
                "raw_results": results[0],
                "method": "paddleocr"
            }
        else:
            return {
                "success": False,
                "error": "无法识别有效的扑克牌字符",
                "raw_results": results[0],
                "method": "paddleocr"
            }
            
    except ImportError:
        return {
            "success": False,
            "error": "PaddleOCR库未安装，请运行: pip install paddlepaddle paddleocr",
            "method": "paddleocr"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"PaddleOCR识别失败: {str(e)}",
            "method": "paddleocr"
        }

def detect_poker_character(image_path: str, use_paddle: bool = True) -> Dict[str, Any]:
    """
    识别扑克牌字符 - 主要接口
    
    Args:
        image_path: 图片路径（应该是_left.png文件）
        use_paddle: 是否优先使用PaddleOCR
        
    Returns:
        识别结果字典
    """
    try:
        print(f"[OCR] 开始字符识别: {image_path}")
        
        # 检查文件是否存在
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"图片文件不存在: {image_path}",
                "method": "ocr"
            }
        
        # 验证是否是左上角图片
        if not image_path.endswith('_left.png'):
            print(f"[OCR] 警告: 建议使用左上角图片(_left.png)进行字符识别")
        
        results = []
        
        # 尝试PaddleOCR
        if use_paddle:
            print("[OCR] 尝试PaddleOCR...")
            paddle_result = detect_with_paddleocr(image_path)
            results.append(paddle_result)
            
            if paddle_result["success"] and paddle_result["confidence"] > 0.5:
                print(f"[OCR] PaddleOCR识别成功: {paddle_result['character']} (置信度: {paddle_result['confidence']:.3f})")
                return paddle_result
        
        # 尝试EasyOCR
        print("[OCR] 尝试EasyOCR...")
        easy_result = detect_with_easyocr(image_path)
        results.append(easy_result)
        
        if easy_result["success"]:
            print(f"[OCR] EasyOCR识别成功: {easy_result['character']} (置信度: {easy_result['confidence']:.3f})")
            return easy_result
        
        # 如果PaddleOCR有结果但置信度较低，返回它
        if use_paddle and results and results[0]["success"]:
            print(f"[OCR] 使用PaddleOCR低置信度结果: {results[0]['character']}")
            return results[0]
        
        # 所有方法都失败
        error_messages = [r.get("error", "未知错误") for r in results]
        return {
            "success": False,
            "error": f"OCR识别失败: {'; '.join(error_messages)}",
            "method": "ocr_failed",
            "attempted_methods": [r.get("method", "unknown") for r in results]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"OCR识别异常: {str(e)}",
            "method": "ocr_exception"
        }

def test_ocr_detector():
    """测试OCR检测器"""
    print("🧪 测试OCR字符识别器")
    print("=" * 50)
    
    # 测试图片路径（左上角图片）
    test_images = [
        "src/image/cut/camera_001_zhuang_1_left.png",
        "src/image/cut/camera_001_xian_1_left.png"
    ]
    
    for image_path in test_images:
        print(f"\n测试图片: {image_path}")
        print("-" * 40)
        
        result = detect_poker_character(image_path)
        
        if result["success"]:
            print("✅ OCR识别成功!")
            print(f"   字符: {result['character']}")
            print(f"   置信度: {result['confidence']:.3f}")
            print(f"   方法: {result['method']}")
        else:
            print("❌ OCR识别失败!")
            print(f"   错误: {result['error']}")
            print(f"   方法: {result.get('method', 'unknown')}")

if __name__ == "__main__":
    test_ocr_detector()