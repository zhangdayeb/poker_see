#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克牌OCR识别模块
功能: 使用EasyOCR识别扑克牌左上角字符，返回点数
用法: python poker_ocr.py <图片路径>
依赖: pip install easyocr
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

def load_easyocr_reader():
    """加载EasyOCR识别器"""
    try:
        import easyocr
        
        print("🔧 正在初始化EasyOCR识别器...")
        print("📥 首次使用可能需要下载模型文件，请稍候...")
        
        # 创建OCR识别器，只识别英文和数字
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        
        print("✅ EasyOCR识别器加载成功")
        return reader
        
    except ImportError:
        raise ImportError("请安装EasyOCR库: pip install easyocr")
    except Exception as e:
        raise Exception(f"EasyOCR初始化失败: {str(e)}")

def normalize_card_character(text):
    """
    标准化识别到的字符为扑克牌点数
    
    Args:
        text (str): OCR识别的原始文本
        
    Returns:
        str: 标准化后的扑克牌点数，识别失败返回None
    """
    if not text:
        return None
    
    # 清理文本：去除空格、转换大小写
    cleaned_text = text.strip().upper()
    
    # 扑克牌点数映射表
    card_mapping = {
        # 标准点数
        'A': 'A', 'a': 'A',
        '2': '2', '3': '3', '4': '4', '5': '5',
        '6': '6', '7': '7', '8': '8', '9': '9', '10': '10',
        'J': 'J', 'j': 'J',
        'Q': 'Q', 'q': 'Q',
        'K': 'K', 'k': 'K',
        
        # 常见OCR误识别修正
        '0': '10',  # 0 可能是 10
        'O': '10',  # O 可能是 10
        '1': 'A',   # 1 可能是 A
        'I': 'A',   # I 可能是 A
        'L': 'A',   # L 可能是 A
        '8': '8',   # 8 就是 8
        'B': '8',   # B 可能是 8
        'G': '6',   # G 可能是 6
        'S': '5',   # S 可能是 5
        'T': '10',  # T 在扑克中表示 10
    }
    
    # 直接映射
    if cleaned_text in card_mapping:
        return card_mapping[cleaned_text]
    
    # 处理多字符情况，提取第一个有效字符
    for char in cleaned_text:
        if char in card_mapping:
            return card_mapping[char]
    
    # 特殊处理：包含数字的情况
    if '10' in cleaned_text:
        return '10'
    
    # 如果包含数字2-9
    for num in ['2', '3', '4', '5', '6', '7', '8', '9']:
        if num in cleaned_text:
            return num
    
    return None

def recognize_poker_character(image_path):
    """
    使用EasyOCR识别扑克牌字符
    
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
        
        print(f"🖼️  正在识别: {image_path}")
        
        # 加载EasyOCR识别器
        try:
            reader = load_easyocr_reader()
        except Exception as e:
            return {
                "success": False,
                "error": f"OCR初始化失败: {str(e)}"
            }
        
        # 执行OCR识别
        try:
            print("🔍 执行OCR识别...")
            results = reader.readtext(image_path)
        except Exception as e:
            return {
                "success": False,
                "error": f"OCR识别失败: {str(e)}"
            }
        
        # 处理识别结果
        if not results:
            return {
                "success": False,
                "error": "未识别到任何文字"
            }
        
        # 获取所有识别到的文本
        detected_texts = []
        best_confidence = 0
        best_text = ""
        
        for (bbox, text, confidence) in results:
            detected_texts.append({
                "text": text,
                "confidence": round(confidence, 3),
                "bbox": bbox
            })
            
            # 记录置信度最高的文本
            if confidence > best_confidence:
                best_confidence = confidence
                best_text = text
        
        print(f"📝 识别到 {len(detected_texts)} 个文本区域")
        for i, item in enumerate(detected_texts):
            print(f"   {i+1}. '{item['text']}' (置信度: {item['confidence']})")
        
        # 标准化最佳识别结果
        if best_text:
            normalized_char = normalize_card_character(best_text)
            
            if normalized_char:
                print(f"🎯 最佳识别: '{best_text}' -> '{normalized_char}' (置信度: {best_confidence:.3f})")
                
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
                    try:
                        from PIL import Image
                        with Image.open(image_path) as img:
                            image_size = {"width": img.width, "height": img.height}
                    except:
                        image_size = {"width": 0, "height": 0}
                
                return {
                    "success": True,
                    "character": normalized_char,
                    "original_text": best_text,
                    "confidence": round(best_confidence, 3),
                    "image_path": image_path,
                    "image_size": image_size,
                    "all_detections": detected_texts,
                    "total_detections": len(detected_texts)
                }
            else:
                return {
                    "success": False,
                    "error": f"无法解析扑克牌字符: '{best_text}'"
                }
        else:
            return {
                "success": False,
                "error": "识别结果为空"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"识别异常: {str(e)}"
        }

def main():
    """主函数"""
    print("🎴 扑克牌OCR识别器")
    print("=" * 40)
    
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("用法: python poker_ocr.py <图片路径>")
        print("示例: python poker_ocr.py src/image/cut/camera_001_zhuang_1_left.png")
        sys.exit(1)
    
    # 获取图片路径
    image_path = sys.argv[1]
    
    # 如果是相对路径，转换为绝对路径
    if not os.path.isabs(image_path):
        project_root = get_project_root()
        image_path = project_root / image_path
        image_path = str(image_path)
    
    # 执行识别
    result = recognize_poker_character(image_path)
    
    # 输出结果
    print("-" * 40)
    if result["success"]:
        print("✅ 识别成功!")
        print(f"🎯 识别字符: {result['character']}")
        print(f"📝 原始文本: {result['original_text']}")
        print(f"🎯 置信度: {result['confidence']:.3f}")
        print(f"📐 图片尺寸: {result['image_size']['width']}×{result['image_size']['height']}")
        print(f"🔍 检测数量: {result['total_detections']}")
        
        # 显示单个字符结果（方便程序调用）
        print(f"\n🎴 结果字符: {result['character']}")
        
    else:
        print("❌ 识别失败!")
        print(f"📛 错误: {result['error']}")
    
    # 输出JSON格式结果（供其他程序调用）
    print("\n" + "=" * 40)
    print("JSON结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()