#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenCV识别引擎 - 基于传统计算机视觉的扑克牌识别
功能:
1. 模板匹配识别
2. 轮廓检测和形状分析
3. 颜色分析识别花色
4. 特征点匹配（可选）
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import numpy as np

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

class OpenCVEngine(BaseEngine):
    """OpenCV识别引擎"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化OpenCV引擎"""
        self.cv2 = None
        self.cv2_available = False
        self.templates = {}
        self.templates_path = None
        
        super().__init__("OpenCV", config)
    
    def _initialize_engine(self):
        """初始化OpenCV引擎"""
        try:
            # 检查OpenCV是否可用
            try:
                import cv2
                self.cv2 = cv2
                self.cv2_available = True
                log_success(f"OpenCV库加载成功 (版本: {cv2.__version__})", "OPENCV_ENGINE")
            except ImportError as e:
                log_error(f"OpenCV库不可用: {e}", "OPENCV_ENGINE")
                self.cv2_available = False
                self.enabled = False
                return
            
            # 初始化模板匹配
            if self.config.get('template_matching', {}).get('enabled', True):
                self._initialize_templates()
            
        except Exception as e:
            log_error(f"OpenCV引擎初始化失败: {e}", "OPENCV_ENGINE")
            self.enabled = False
    
    def _initialize_templates(self):
        """初始化模板"""
        try:
            self.templates_path = self.config.get('template_matching', {}).get('templates_path', 'src/config/templates/')
            
            # 转换为绝对路径
            if not Path(self.templates_path).is_absolute():
                self.templates_path = PROJECT_ROOT / self.templates_path
            
            templates_dir = Path(self.templates_path)
            
            if not templates_dir.exists():
                log_warning(f"模板目录不存在: {self.templates_path}", "OPENCV_ENGINE")
                return
            
            # 加载模板文件
            template_files = list(templates_dir.glob("*.png")) + list(templates_dir.glob("*.jpg"))
            
            for template_file in template_files:
                try:
                    template_name = template_file.stem
                    template_img = self.cv2.imread(str(template_file), self.cv2.IMREAD_GRAYSCALE)
                    
                    if template_img is not None:
                        self.templates[template_name] = template_img
                        log_info(f"加载模板: {template_name}", "OPENCV_ENGINE")
                    else:
                        log_warning(f"模板加载失败: {template_file}", "OPENCV_ENGINE")
                        
                except Exception as e:
                    log_error(f"加载模板文件失败 {template_file}: {e}", "OPENCV_ENGINE")
            
            log_success(f"模板加载完成，共 {len(self.templates)} 个模板", "OPENCV_ENGINE")
            
        except Exception as e:
            log_error(f"模板初始化失败: {e}", "OPENCV_ENGINE")
    
    def _recognize_image(self, image_path: str) -> Dict[str, Any]:
        """使用OpenCV识别图片"""
        try:
            if not self.cv2_available:
                return {
                    'success': False,
                    'error': 'OpenCV不可用'
                }
            
            # 读取图片
            image = self.cv2.imread(image_path)
            if image is None:
                return {
                    'success': False,
                    'error': '无法读取图片'
                }
            
            gray = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2GRAY)
            
            # 尝试不同的识别方法
            results = []
            
            # 方法1: 模板匹配
            if self.config.get('template_matching', {}).get('enabled', True):
                template_result = self._template_matching(gray)
                if template_result['success']:
                    results.append(template_result)
            
            # 方法2: 轮廓检测
            if self.config.get('contour_detection', {}).get('enabled', True):
                contour_result = self._contour_detection(image, gray)
                if contour_result['success']:
                    results.append(contour_result)
            
            # 方法3: 颜色分析
            if self.config.get('color_analysis', {}).get('enabled', True):
                color_result = self._color_analysis(image)
                if color_result['success']:
                    results.append(color_result)
            
            # 方法4: 特征匹配（可选）
            if self.config.get('feature_matching', {}).get('enabled', False):
                feature_result = self._feature_matching(gray)
                if feature_result['success']:
                    results.append(feature_result)
            
            # 选择最佳结果
            if results:
                best_result = max(results, key=lambda x: x.get('confidence', 0))
                return best_result
            else:
                return {
                    'success': False,
                    'error': '所有OpenCV方法都未识别成功'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'OpenCV识别异常: {str(e)}'
            }
    
    def _template_matching(self, gray_image: np.ndarray) -> Dict[str, Any]:
        """模板匹配识别"""
        try:
            if not self.templates:
                return {
                    'success': False,
                    'error': '没有可用的模板'
                }
            
            threshold = self.config.get('template_matching', {}).get('threshold', 0.8)
            method_name = self.config.get('template_matching', {}).get('method', 'TM_CCOEFF_NORMED')
            
            # 获取匹配方法
            method = getattr(self.cv2, method_name, self.cv2.TM_CCOEFF_NORMED)
            
            best_match = None
            best_confidence = 0
            
            for template_name, template in self.templates.items():
                # 执行模板匹配
                result = self.cv2.matchTemplate(gray_image, template, method)
                min_val, max_val, min_loc, max_loc = self.cv2.minMaxLoc(result)
                
                # 根据方法选择合适的值
                if method in [self.cv2.TM_SQDIFF, self.cv2.TM_SQDIFF_NORMED]:
                    confidence = 1 - min_val
                    match_loc = min_loc
                else:
                    confidence = max_val
                    match_loc = max_loc
                
                if confidence > threshold and confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        'template_name': template_name,
                        'confidence': confidence,
                        'location': match_loc
                    }
            
            if best_match:
                # 解析模板名称获取扑克牌信息
                card_info = self._parse_template_name(best_match['template_name'])
                
                return {
                    'success': True,
                    'suit': card_info['suit'],
                    'rank': card_info['rank'],
                    'suit_name': card_info['suit_name'],
                    'suit_symbol': card_info['suit_symbol'],
                    'display_name': card_info['display_name'],
                    'confidence': best_confidence,
                    'method': 'template_matching',
                    'template_name': best_match['template_name'],
                    'location': best_match['location']
                }
            else:
                return {
                    'success': False,
                    'error': f'模板匹配置信度低于阈值 {threshold}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'模板匹配异常: {str(e)}'
            }
    
    def _contour_detection(self, image: np.ndarray, gray_image: np.ndarray) -> Dict[str, Any]:
        """轮廓检测识别"""
        try:
            config = self.config.get('contour_detection', {})
            min_area = config.get('min_area', 1000)
            max_area = config.get('max_area', 50000)
            aspect_ratio_range = config.get('aspect_ratio_range', [0.6, 0.8])
            
            # 边缘检测
            edges = self.cv2.Canny(gray_image, 50, 150)
            
            # 查找轮廓
            contours, _ = self.cv2.findContours(edges, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)
            
            valid_contours = []
            
            for contour in contours:
                area = self.cv2.contourArea(contour)
                
                if min_area <= area <= max_area:
                    # 计算边界矩形
                    x, y, w, h = self.cv2.boundingRect(contour)
                    aspect_ratio = float(w) / h
                    
                    if aspect_ratio_range[0] <= aspect_ratio <= aspect_ratio_range[1]:
                        valid_contours.append({
                            'contour': contour,
                            'area': area,
                            'bbox': (x, y, w, h),
                            'aspect_ratio': aspect_ratio
                        })
            
            if valid_contours:
                # 选择最大的轮廓
                best_contour = max(valid_contours, key=lambda x: x['area'])
                
                # 这里可以添加更多的形状分析逻辑
                # 目前返回一个基本的结果
                confidence = min(0.8, best_contour['area'] / max_area)
                
                return {
                    'success': True,
                    'suit': 'unknown',
                    'rank': 'unknown',
                    'suit_name': '未知',
                    'suit_symbol': '?',
                    'display_name': '检测到扑克牌',
                    'confidence': confidence,
                    'method': 'contour_detection',
                    'contour_info': best_contour
                }
            else:
                return {
                    'success': False,
                    'error': '未检测到有效轮廓'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'轮廓检测异常: {str(e)}'
            }
    
    def _color_analysis(self, image: np.ndarray) -> Dict[str, Any]:
        """颜色分析识别花色"""
        try:
            config = self.config.get('color_analysis', {})
            
            # 转换到HSV颜色空间
            hsv = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2HSV)
            
            # 红色范围（红桃和方块）
            red_lower = np.array(config.get('red_threshold', [0, 50, 50])[:3])
            red_upper = np.array(config.get('red_threshold', [10, 255, 255])[3:6])
            red_mask1 = self.cv2.inRange(hsv, red_lower, red_upper)
            
            red_lower2 = np.array([170, 50, 50])
            red_upper2 = np.array([180, 255, 255])
            red_mask2 = self.cv2.inRange(hsv, red_lower2, red_upper2)
            
            red_mask = red_mask1 + red_mask2
            
            # 黑色范围（黑桃和梅花）
            black_lower = np.array(config.get('black_threshold', [0, 0, 0])[:3])
            black_upper = np.array(config.get('black_threshold', [180, 255, 30])[3:6])
            black_mask = self.cv2.inRange(hsv, black_lower, black_upper)
            
            # 计算红色和黑色像素数量
            red_pixels = np.sum(red_mask > 0)
            black_pixels = np.sum(black_mask > 0)
            
            total_pixels = image.shape[0] * image.shape[1]
            red_ratio = red_pixels / total_pixels
            black_ratio = black_pixels / total_pixels
            
            # 判断颜色
            if red_ratio > black_ratio and red_ratio > 0.01:
                # 红色系（红桃或方块）
                confidence = min(0.7, red_ratio * 10)
                
                # 这里可以添加更精细的红桃/方块区分逻辑
                # 目前简单返回红桃
                return {
                    'success': True,
                    'suit': 'hearts',
                    'rank': 'unknown',
                    'suit_name': '红桃',
                    'suit_symbol': '♥️',
                    'display_name': '♥️?',
                    'confidence': confidence,
                    'method': 'color_analysis',
                    'color_info': {
                        'red_ratio': red_ratio,
                        'black_ratio': black_ratio
                    }
                }
            elif black_ratio > 0.02:
                # 黑色系（黑桃或梅花）
                confidence = min(0.7, black_ratio * 5)
                
                # 这里可以添加更精细的黑桃/梅花区分逻辑
                # 目前简单返回黑桃
                return {
                    'success': True,
                    'suit': 'spades',
                    'rank': 'unknown',
                    'suit_name': '黑桃',
                    'suit_symbol': '♠️',
                    'display_name': '♠️?',
                    'confidence': confidence,
                    'method': 'color_analysis',
                    'color_info': {
                        'red_ratio': red_ratio,
                        'black_ratio': black_ratio
                    }
                }
            else:
                return {
                    'success': False,
                    'error': '无法识别扑克牌颜色'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'颜色分析异常: {str(e)}'
            }
    
    def _feature_matching(self, gray_image: np.ndarray) -> Dict[str, Any]:
        """特征点匹配识别"""
        try:
            config = self.config.get('feature_matching', {})
            detector_name = config.get('detector', 'ORB')
            matcher_name = config.get('matcher', 'BFMatcher')
            
            # 创建特征检测器
            if detector_name == 'ORB':
                detector = self.cv2.ORB_create()
            elif detector_name == 'SIFT':
                detector = self.cv2.SIFT_create()
            elif detector_name == 'SURF':
                detector = self.cv2.SURF_create()
            else:
                return {
                    'success': False,
                    'error': f'不支持的特征检测器: {detector_name}'
                }
            
            # 检测关键点和描述符
            keypoints, descriptors = detector.detectAndCompute(gray_image, None)
            
            if descriptors is None or len(descriptors) == 0:
                return {
                    'success': False,
                    'error': '未检测到特征点'
                }
            
            # 这里应该与预先存储的模板特征进行匹配
            # 目前返回一个基本结果
            confidence = min(0.6, len(keypoints) / 100)
            
            return {
                'success': True,
                'suit': 'unknown',
                'rank': 'unknown',
                'suit_name': '未知',
                'suit_symbol': '?',
                'display_name': '特征匹配',
                'confidence': confidence,
                'method': 'feature_matching',
                'feature_info': {
                    'keypoints_count': len(keypoints),
                    'descriptor_shape': descriptors.shape if descriptors is not None else None
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'特征匹配异常: {str(e)}'
            }
    
    def _parse_template_name(self, template_name: str) -> Dict[str, Any]:
        """解析模板名称获取扑克牌信息"""
        try:
            # 假设模板名称格式为: hearts_A, spades_K 等
            parts = template_name.lower().split('_')
            
            if len(parts) >= 2:
                suit_part = parts[0]
                rank_part = parts[1]
                
                # 花色映射
                suit_mapping = {
                    'hearts': {'name': '红桃', 'symbol': '♥️', 'en': 'hearts'},
                    'spades': {'name': '黑桃', 'symbol': '♠️', 'en': 'spades'},
                    'diamonds': {'name': '方块', 'symbol': '♦️', 'en': 'diamonds'},
                    'clubs': {'name': '梅花', 'symbol': '♣️', 'en': 'clubs'},
                    'h': {'name': '红桃', 'symbol': '♥️', 'en': 'hearts'},
                    's': {'name': '黑桃', 'symbol': '♠️', 'en': 'spades'},
                    'd': {'name': '方块', 'symbol': '♦️', 'en': 'diamonds'},
                    'c': {'name': '梅花', 'symbol': '♣️', 'en': 'clubs'}
                }
                
                suit_info = suit_mapping.get(suit_part, {
                    'name': '未知', 'symbol': '?', 'en': 'unknown'
                })
                
                return {
                    'suit': suit_info['en'],
                    'rank': rank_part.upper(),
                    'suit_name': suit_info['name'],
                    'suit_symbol': suit_info['symbol'],
                    'display_name': f"{suit_info['symbol']}{rank_part.upper()}"
                }
            else:
                return {
                    'suit': 'unknown',
                    'rank': 'unknown',
                    'suit_name': '未知',
                    'suit_symbol': '?',
                    'display_name': template_name
                }
                
        except Exception:
            return {
                'suit': 'unknown',
                'rank': 'unknown',
                'suit_name': '未知',
                'suit_symbol': '?',
                'display_name': template_name
            }
    
    def is_available(self) -> bool:
        """检查OpenCV引擎是否可用"""
        return self.enabled and self.cv2_available
    
    def get_opencv_info(self) -> Dict[str, Any]:
        """获取OpenCV引擎信息"""
        info = {
            'cv2_available': self.cv2_available,
            'cv2_version': self.cv2.__version__ if self.cv2 else None,
            'templates_count': len(self.templates),
            'templates_path': str(self.templates_path) if self.templates_path else None
        }
        
        # 添加配置信息
        for method in ['template_matching', 'contour_detection', 'color_analysis', 'feature_matching']:
            method_config = self.config.get(method, {})
            info[method] = {
                'enabled': method_config.get('enabled', False),
                'config': method_config
            }
        
        return info

if __name__ == "__main__":
    print("🧪 测试OpenCV识别引擎")
    
    # 测试配置
    test_config = {
        'enabled': True,
        'priority': 3,
        'template_matching': {
            'enabled': True,
            'templates_path': 'src/config/templates/',
            'threshold': 0.8,
            'method': 'TM_CCOEFF_NORMED'
        },
        'contour_detection': {
            'enabled': True,
            'min_area': 1000,
            'max_area': 50000,
            'aspect_ratio_range': [0.6, 0.8]
        },
        'color_analysis': {
            'enabled': True,
            'red_threshold': [0, 50, 50, 10, 255, 255],
            'black_threshold': [0, 0, 0, 180, 255, 30]
        },
        'feature_matching': {
            'enabled': False,
            'detector': 'ORB',
            'matcher': 'BFMatcher'
        }
    }
    
    # 创建OpenCV引擎
    opencv_engine = OpenCVEngine(test_config)
    
    print(f"引擎信息: {opencv_engine}")
    print(f"引擎可用: {opencv_engine.is_available()}")
    
    # 获取OpenCV信息
    opencv_info = opencv_engine.get_opencv_info()
    print(f"OpenCV信息: {opencv_info}")
    
    # 获取引擎统计
    stats = opencv_engine.get_stats()
    print(f"引擎统计: {stats}")
    
    print("✅ OpenCV引擎测试完成")