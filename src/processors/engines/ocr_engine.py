#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR识别引擎 - 基于EasyOCR和PaddleOCR的扑克牌字符识别
功能:
1. 支持多种OCR引擎 (EasyOCR, PaddleOCR)
2. 自动降级处理（优先使用PaddleOCR，失败时使用EasyOCR）
3. 左上角字符识别和标准化
4. 置信度过滤和结果验证
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# 添加项目根目录到 Python 路径
def setup_project_paths():
    """设置项目路径，确保可以正确导入模块"""
    current_file = Path(__file__).resolve()
    
    # 找到项目根目录（包含 main.py 的目录）
    project_root = current_file
    while project_root.parent != project_root:
        if (project_root / "main.py").exists():
            break
        project_root = project_root.parent
    
    # 将项目根目录添加到 Python 路径
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

PROJECT_ROOT = setup_project_paths()

from src.processors.engines.base_engine import BaseEngine
from src.core.utils import log_info, log_success, log_error, log_warning

class OCREngine(BaseEngine):
    """OCR识别引擎"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化OCR引擎"""
        self.paddle_ocr = None
        self.easy_ocr = None
        self.paddle_available = False
        self.easy_available = False
        self.provider = None
        
        super().__init__("OCR", config)
    
    def _initialize_engine(self):
        """初始化OCR引擎"""
        try:
            # 获取配置
            provider = self.config.get('provider', 'paddle')  # 默认使用PaddleOCR
            fallback_provider = self.config.get('fallback_provider', 'easy')
            
            # 初始化PaddleOCR
            if provider == 'paddle' or fallback_provider == 'paddle':
                self._initialize_paddle_ocr()
            
            # 初始化EasyOCR
            if provider == 'easy' or fallback_provider == 'easy':
                self._initialize_easy_ocr()
            
            # 确定使用的OCR提供商
            if provider == 'paddle' and self.paddle_available:
                self.provider = 'paddle'
                log_success("使用PaddleOCR作为主要OCR引擎", "OCR_ENGINE")
            elif provider == 'easy' and self.easy_available:
                self.provider = 'easy'
                log_success("使用EasyOCR作为主要OCR引擎", "OCR_ENGINE")
            elif self.paddle_available:
                self.provider = 'paddle'
                log_info("降级使用PaddleOCR", "OCR_ENGINE")
            elif self.easy_available:
                self.provider = 'easy'
                log_info("降级使用EasyOCR", "OCR_ENGINE")
            else:
                log_error("没有可用的OCR引擎", "OCR_ENGINE")
                self.enabled = False
                return
            
        except Exception as e:
            log_error(f"OCR引擎初始化失败: {e}", "OCR_ENGINE")
            self.enabled = False
    
    def _initialize_paddle_ocr(self):
        """初始化PaddleOCR"""
        try:
            from paddleocr import PaddleOCR
            
            self.paddle_ocr = PaddleOCR(
                use_angle_cls=self.config.get('use_angle_cls', False),
                lang=self.config.get('lang', 'en'),
                show_log=False,
                use_gpu=self.config.get('use_gpu', False)
            )
            
            self.paddle_available = True
            log_success("PaddleOCR初始化成功", "OCR_ENGINE")
            
        except ImportError as e:
            log_warning(f"PaddleOCR不可用: {e}", "OCR_ENGINE")
            self.paddle_available = False
        except Exception as e:
            log_error(f"PaddleOCR初始化失败: {e}", "OCR_ENGINE")
            self.paddle_available = False
    
    def _initialize_easy_ocr(self):
        """初始化EasyOCR"""
        try:
            import easyocr
            
            languages = self.config.get('languages', ['en'])
            use_gpu = self.config.get('use_gpu', False)
            
            self.easy_ocr = easyocr.Reader(languages, gpu=use_gpu, verbose=False)
            self.easy_available = True
            log_success("EasyOCR初始化成功", "OCR_ENGINE")
            
        except ImportError as e:
            log_warning(f"EasyOCR不可用: {e}", "OCR_ENGINE")
            self.easy_available = False
        except Exception as e:
            log_error(f"EasyOCR初始化失败: {e}", "OCR_ENGINE")
            self.easy_available = False
    
    def _recognize_image(self, image_path: str) -> Dict[str, Any]:
        """使用OCR识别图片中的字符"""
        try:
            # 首先尝试使用主要提供商
            if self.provider == 'paddle' and self.paddle_available:
                result = self._recognize_with_paddle(image_path)
                if result['success']:
                    return result
                
                # PaddleOCR失败，尝试EasyOCR
                if self.easy_available:
                    log_info("PaddleOCR失败，尝试EasyOCR", "OCR_ENGINE")
                    return self._recognize_with_easy(image_path)
                
                return result
            
            elif self.provider == 'easy' and self.easy_available:
                result = self._recognize_with_easy(image_path)
                if result['success']:
                    return result
                
                # EasyOCR失败，尝试PaddleOCR
                if self.paddle_available:
                    log_info("EasyOCR失败，尝试PaddleOCR", "OCR_ENGINE")
                    return self._recognize_with_paddle(image_path)
                
                return result
            
            else:
                return {
                    'success': False,
                    'error': 'OCR引擎不可用'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'OCR识别异常: {str(e)}'
            }
    
    def _recognize_with_paddle(self, image_path: str) -> Dict[str, Any]:
        """使用PaddleOCR识别"""
        try:
            if not self.paddle_available or not self.paddle_ocr:
                return {
                    'success': False,
                    'error': 'PaddleOCR不可用'
                }
            
            # 执行OCR识别
            results = self.paddle_ocr.ocr(image_path, cls=False)
            
            if not results or not results[0]:
                return {
                    'success': False,
                    'error': '未识别到任何文字'
                }
            
            # 处理识别结果
            detected_texts = []
            best_confidence = 0
            best_text = ""
            
            for line in results[0]:
                if line:
                    bbox, (text, confidence) = line
                    
                    detected_texts.append({
                        "text": text,
                        "confidence": round(float(confidence), 3),
                        "bbox": [[int(point[0]), int(point[1])] for point in bbox]
                    })
                    
                    if confidence > best_confidence:
                        best_confidence = float(confidence)
                        best_text = text
            
            # 标准化字符
            if best_text:
                normalized_char = self._normalize_card_character(best_text)
                
                if normalized_char:
                    return {
                        'success': True,
                        'rank': normalized_char,
                        'character': normalized_char,
                        'original_text': best_text,
                        'confidence': best_confidence,
                        'all_detections': detected_texts,
                        'total_detections': len(detected_texts),
                        'provider': 'paddle'
                    }
                else:
                    return {
                        'success': False,
                        'error': f'无法解析扑克牌字符: {best_text}'
                    }
            else:
                return {
                    'success': False,
                    'error': '识别结果为空'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'PaddleOCR识别异常: {str(e)}'
            }
    
    def _recognize_with_easy(self, image_path: str) -> Dict[str, Any]:
        """使用EasyOCR识别"""
        try:
            if not self.easy_available or not self.easy_ocr:
                return {
                    'success': False,
                    'error': 'EasyOCR不可用'
                }
            
            # 执行OCR识别
            results = self.easy_ocr.readtext(image_path)
            
            if not results:
                return {
                    'success': False,
                    'error': '未识别到任何文字'
                }
            
            # 处理识别结果
            detected_texts = []
            best_confidence = 0
            best_text = ""
            
            for (bbox, text, confidence) in results:
                detected_texts.append({
                    "text": text,
                    "confidence": round(float(confidence), 3),
                    "bbox": [[int(point[0]), int(point[1])] for point in bbox]
                })
                
                if confidence > best_confidence:
                    best_confidence = float(confidence)
                    best_text = text
            
            # 标准化字符
            if best_text:
                normalized_char = self._normalize_card_character(best_text)
                
                if normalized_char:
                    return {
                        'success': True,
                        'rank': normalized_char,
                        'character': normalized_char,
                        'original_text': best_text,
                        'confidence': best_confidence,
                        'all_detections': detected_texts,
                        'total_detections': len(detected_texts),
                        'provider': 'easy'
                    }
                else:
                    return {
                        'success': False,
                        'error': f'无法解析扑克牌字符: {best_text}'
                    }
            else:
                return {
                    'success': False,
                    'error': '识别结果为空'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'EasyOCR识别异常: {str(e)}'
            }
    
    def _normalize_card_character(self, text: str) -> Optional[str]:
        """标准化识别到的字符为扑克牌点数"""
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
            '6': '6',   # 6 就是 6
            'C': '6',   # C 可能是 6
            'D': 'A',   # D 可能是 A
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
    
    def is_available(self) -> bool:
        """检查OCR引擎是否可用"""
        return self.enabled and (self.paddle_available or self.easy_available)
    
    def get_ocr_info(self) -> Dict[str, Any]:
        """获取OCR引擎信息"""
        return {
            'provider': self.provider,
            'paddle_available': self.paddle_available,
            'easy_available': self.easy_available,
            'confidence_threshold': self.config.get('confidence_threshold', 0.3),
            'languages': self.config.get('languages', ['en']),
            'use_gpu': self.config.get('use_gpu', False)
        }

if __name__ == "__main__":
    print("🧪 测试OCR识别引擎")
    
    # 测试配置
    test_config = {
        'enabled': True,
        'priority': 2,
        'provider': 'paddle',
        'fallback_provider': 'easy',
        'confidence_threshold': 0.3,
        'languages': ['en'],
        'use_gpu': False,
        'use_angle_cls': False
    }
    
    # 创建OCR引擎
    ocr_engine = OCREngine(test_config)
    
    print(f"引擎信息: {ocr_engine}")
    print(f"引擎可用: {ocr_engine.is_available()}")
    
    # 获取OCR信息
    ocr_info = ocr_engine.get_ocr_info()
    print(f"OCR信息: {ocr_info}")
    
    # 获取引擎统计
    stats = ocr_engine.get_stats()
    print(f"引擎统计: {stats}")
    
    print("✅ OCR引擎测试完成")