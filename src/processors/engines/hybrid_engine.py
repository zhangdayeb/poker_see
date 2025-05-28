#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合识别引擎 - 结合YOLO和OCR的混合识别方案
功能:
1. 同时使用YOLO和OCR进行识别
2. 智能结果融合和置信度加权
3. 自适应策略选择
4. 结果验证和一致性检查
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
from src.processors.engines.yolo_engine import YOLOEngine
from src.processors.engines.ocr_engine import OCREngine
from src.core.utils import log_info, log_success, log_error, log_warning

class HybridEngine(BaseEngine):
    """混合识别引擎"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化混合引擎"""
        self.yolo_engine = None
        self.ocr_engine = None
        self.combination_strategy = None
        
        super().__init__("Hybrid", config)
    
    def _initialize_engine(self):
        """初始化混合引擎"""
        try:
            # 获取配置
            yolo_config = self.config.get('yolo_config', {})
            ocr_config = self.config.get('ocr_config', {})
            
            self.combination_strategy = self.config.get('combination_strategy', 'best_confidence')
            
            # 初始化YOLO引擎
            try:
                self.yolo_engine = YOLOEngine(yolo_config)
                if self.yolo_engine.is_available():
                    log_success("YOLO子引擎初始化成功", "HYBRID_ENGINE")
                else:
                    log_warning("YOLO子引擎不可用", "HYBRID_ENGINE")
            except Exception as e:
                log_error(f"YOLO子引擎初始化失败: {e}", "HYBRID_ENGINE")
                self.yolo_engine = None
            
            # 初始化OCR引擎
            try:
                self.ocr_engine = OCREngine(ocr_config)
                if self.ocr_engine.is_available():
                    log_success("OCR子引擎初始化成功", "HYBRID_ENGINE")
                else:
                    log_warning("OCR子引擎不可用", "HYBRID_ENGINE")
            except Exception as e:
                log_error(f"OCR子引擎初始化失败: {e}", "HYBRID_ENGINE")
                self.ocr_engine = None
            
            # 检查是否至少有一个引擎可用
            if not self.yolo_engine and not self.ocr_engine:
                log_error("没有可用的子引擎", "HYBRID_ENGINE")
                self.enabled = False
            elif not self.yolo_engine:
                log_warning("仅OCR引擎可用，混合模式降级", "HYBRID_ENGINE")
            elif not self.ocr_engine:
                log_warning("仅YOLO引擎可用，混合模式降级", "HYBRID_ENGINE")
            
        except Exception as e:
            log_error(f"混合引擎初始化失败: {e}", "HYBRID_ENGINE")
            self.enabled = False
    
    def _recognize_image(self, image_path: str) -> Dict[str, Any]:
        """使用混合方法识别图片"""
        try:
            # 检查执行策略
            parallel_execution = self.config.get('parallel_execution', False)
            use_primary_for_suit = self.config.get('use_primary_for_suit', True)
            use_secondary_for_rank = self.config.get('use_secondary_for_rank', True)
            
            # 确定主引擎和副引擎
            primary_engine = self.config.get('primary_engine', 'yolo')
            secondary_engine = self.config.get('secondary_engine', 'ocr')
            
            # 执行识别
            if parallel_execution:
                return self._parallel_recognition(image_path)
            else:
                return self._sequential_recognition(image_path, primary_engine, secondary_engine,
                                                  use_primary_for_suit, use_secondary_for_rank)
                
        except Exception as e:
            return {
                'success': False,
                'error': f'混合识别异常: {str(e)}'
            }
    
    def _parallel_recognition(self, image_path: str) -> Dict[str, Any]:
        """并行识别"""
        try:
            yolo_result = None
            ocr_result = None
            
            # 同时执行YOLO和OCR识别
            if self.yolo_engine and self.yolo_engine.is_available():
                yolo_result = self.yolo_engine._recognize_image(image_path)
            
            if self.ocr_engine and self.ocr_engine.is_available():
                # 对于OCR，尝试使用左上角图片
                left_corner_image = self._get_left_corner_image(image_path)
                if left_corner_image:
                    ocr_result = self.ocr_engine._recognize_image(left_corner_image)
                else:
                    ocr_result = self.ocr_engine._recognize_image(image_path)
            
            # 融合结果
            return self._combine_results(yolo_result, ocr_result, image_path)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'并行识别异常: {str(e)}'
            }
    
    def _sequential_recognition(self, image_path: str, primary_engine: str, 
                               secondary_engine: str, use_primary_for_suit: bool, 
                               use_secondary_for_rank: bool) -> Dict[str, Any]:
        """顺序识别"""
        try:
            primary_result = None
            secondary_result = None
            
            # 执行主引擎识别
            if primary_engine == 'yolo' and self.yolo_engine and self.yolo_engine.is_available():
                primary_result = self.yolo_engine._recognize_image(image_path)
            elif primary_engine == 'ocr' and self.ocr_engine and self.ocr_engine.is_available():
                left_corner_image = self._get_left_corner_image(image_path)
                if left_corner_image:
                    primary_result = self.ocr_engine._recognize_image(left_corner_image)
                else:
                    primary_result = self.ocr_engine._recognize_image(image_path)
            
            # 判断是否需要执行副引擎
            need_secondary = False
            
            if not primary_result or not primary_result.get('success', False):
                need_secondary = True
            else:
                # 检查主引擎结果的置信度
                primary_confidence = primary_result.get('confidence', 0)
                primary_min_confidence = self.config.get('primary_min_confidence', 0.8)
                
                if primary_confidence < primary_min_confidence:
                    need_secondary = True
            
            # 执行副引擎识别
            if need_secondary:
                if secondary_engine == 'yolo' and self.yolo_engine and self.yolo_engine.is_available():
                    secondary_result = self.yolo_engine._recognize_image(image_path)
                elif secondary_engine == 'ocr' and self.ocr_engine and self.ocr_engine.is_available():
                    left_corner_image = self._get_left_corner_image(image_path)
                    if left_corner_image:
                        secondary_result = self.ocr_engine._recognize_image(left_corner_image)
                    else:
                        secondary_result = self.ocr_engine._recognize_image(image_path)
            
            # 融合结果
            return self._combine_results(
                primary_result if primary_engine == 'yolo' else secondary_result,
                primary_result if primary_engine == 'ocr' else secondary_result,
                image_path
            )
            
        except Exception as e:
            return {
                'success': False,
                'error': f'顺序识别异常: {str(e)}'
            }
    
    def _combine_results(self, yolo_result: Optional[Dict[str, Any]], 
                        ocr_result: Optional[Dict[str, Any]], 
                        image_path: str) -> Dict[str, Any]:
        """融合YOLO和OCR结果"""
        try:
            # 检查结果可用性
            yolo_available = yolo_result and yolo_result.get('success', False)
            ocr_available = ocr_result and ocr_result.get('success', False)
            
            if not yolo_available and not ocr_available:
                return {
                    'success': False,
                    'error': '所有识别引擎都失败'
                }
            
            # 根据策略融合结果
            if self.combination_strategy == 'best_confidence':
                return self._combine_by_best_confidence(yolo_result, ocr_result)
            elif self.combination_strategy == 'weighted_average':
                return self._combine_by_weighted_average(yolo_result, ocr_result)
            elif self.combination_strategy == 'yolo_priority':
                return self._combine_by_yolo_priority(yolo_result, ocr_result)
            elif self.combination_strategy == 'ocr_priority':
                return self._combine_by_ocr_priority(yolo_result, ocr_result)
            elif self.combination_strategy == 'suit_rank_split':
                return self._combine_by_suit_rank_split(yolo_result, ocr_result)
            else:
                return self._combine_by_best_confidence(yolo_result, ocr_result)
                
        except Exception as e:
            return {
                'success': False,
                'error': f'结果融合异常: {str(e)}'
            }
    
    def _combine_by_best_confidence(self, yolo_result: Optional[Dict[str, Any]], 
                                   ocr_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """按最佳置信度融合"""
        try:
            yolo_confidence = yolo_result.get('confidence', 0) if yolo_result and yolo_result.get('success') else 0
            ocr_confidence = ocr_result.get('confidence', 0) if ocr_result and ocr_result.get('success') else 0
            
            if yolo_confidence >= ocr_confidence and yolo_result and yolo_result.get('success'):
                return {
                    'success': True,
                    'suit': yolo_result.get('suit', ''),
                    'rank': yolo_result.get('rank', ''),
                    'suit_name': yolo_result.get('suit_name', ''),
                    'suit_symbol': yolo_result.get('suit_symbol', ''),
                    'display_name': yolo_result.get('display_name', ''),
                    'confidence': yolo_confidence,
                    'method': 'yolo_best',
                    'yolo_result': yolo_result,
                    'ocr_result': ocr_result
                }
            elif ocr_result and ocr_result.get('success'):
                return {
                    'success': True,
                    'suit': '',  # OCR通常不识别花色
                    'rank': ocr_result.get('rank', ''),
                    'suit_name': '',
                    'suit_symbol': '',
                    'display_name': ocr_result.get('rank', ''),
                    'confidence': ocr_confidence,
                    'method': 'ocr_best',
                    'yolo_result': yolo_result,
                    'ocr_result': ocr_result
                }
            else:
                return {
                    'success': False,
                    'error': '没有可用的识别结果'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'最佳置信度融合异常: {str(e)}'
            }
    
    def _combine_by_weighted_average(self, yolo_result: Optional[Dict[str, Any]], 
                                    ocr_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """按加权平均融合"""
        try:
            weights = self.config.get('confidence_weights', {'yolo': 0.7, 'ocr': 0.3})
            
            yolo_available = yolo_result and yolo_result.get('success', False)
            ocr_available = ocr_result and ocr_result.get('success', False)
            
            if yolo_available and ocr_available:
                # 计算加权置信度
                yolo_conf = yolo_result.get('confidence', 0)
                ocr_conf = ocr_result.get('confidence', 0)
                
                weighted_confidence = (yolo_conf * weights['yolo'] + ocr_conf * weights['ocr'])
                
                return {
                    'success': True,
                    'suit': yolo_result.get('suit', ''),
                    'rank': ocr_result.get('rank', yolo_result.get('rank', '')),
                    'suit_name': yolo_result.get('suit_name', ''),
                    'suit_symbol': yolo_result.get('suit_symbol', ''),
                    'display_name': f"{yolo_result.get('suit_symbol', '')}{ocr_result.get('rank', yolo_result.get('rank', ''))}",
                    'confidence': weighted_confidence,
                    'method': 'weighted_hybrid',
                    'yolo_result': yolo_result,
                    'ocr_result': ocr_result
                }
            elif yolo_available:
                return self._format_single_result(yolo_result, 'yolo_only')
            elif ocr_available:
                return self._format_single_result(ocr_result, 'ocr_only')
            else:
                return {
                    'success': False,
                    'error': '没有可用的识别结果'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'加权平均融合异常: {str(e)}'
            }
    
    def _combine_by_suit_rank_split(self, yolo_result: Optional[Dict[str, Any]], 
                                   ocr_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """花色和点数分离融合（YOLO识别花色，OCR识别点数）"""
        try:
            yolo_available = yolo_result and yolo_result.get('success', False)
            ocr_available = ocr_result and ocr_result.get('success', False)
            
            if yolo_available and ocr_available:
                # 使用YOLO的花色和OCR的点数
                suit = yolo_result.get('suit', '')
                rank = ocr_result.get('rank', '')
                suit_name = yolo_result.get('suit_name', '')
                suit_symbol = yolo_result.get('suit_symbol', '')
                
                # 计算综合置信度
                yolo_conf = yolo_result.get('confidence', 0)
                ocr_conf = ocr_result.get('confidence', 0)
                combined_conf = (yolo_conf + ocr_conf) / 2
                
                return {
                    'success': True,
                    'suit': suit,
                    'rank': rank,
                    'suit_name': suit_name,
                    'suit_symbol': suit_symbol,
                    'display_name': f"{suit_symbol}{rank}",
                    'confidence': combined_conf,
                    'method': 'suit_rank_split',
                    'yolo_result': yolo_result,
                    'ocr_result': ocr_result
                }
            elif yolo_available:
                return self._format_single_result(yolo_result, 'yolo_fallback')
            elif ocr_available:
                return self._format_single_result(ocr_result, 'ocr_fallback')
            else:
                return {
                    'success': False,
                    'error': '没有可用的识别结果'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'花色点数分离融合异常: {str(e)}'
            }
    
    def _combine_by_yolo_priority(self, yolo_result: Optional[Dict[str, Any]], 
                                 ocr_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """YOLO优先融合"""
        yolo_available = yolo_result and yolo_result.get('success', False)
        ocr_available = ocr_result and ocr_result.get('success', False)
        
        if yolo_available:
            return self._format_single_result(yolo_result, 'yolo_priority')
        elif ocr_available:
            return self._format_single_result(ocr_result, 'ocr_fallback')
        else:
            return {
                'success': False,
                'error': '没有可用的识别结果'
            }
    
    def _combine_by_ocr_priority(self, yolo_result: Optional[Dict[str, Any]], 
                                ocr_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """OCR优先融合"""
        yolo_available = yolo_result and yolo_result.get('success', False)
        ocr_available = ocr_result and ocr_result.get('success', False)
        
        if ocr_available:
            return self._format_single_result(ocr_result, 'ocr_priority')
        elif yolo_available:
            return self._format_single_result(yolo_result, 'yolo_fallback')
        else:
            return {
                'success': False,
                'error': '没有可用的识别结果'
            }
    
    def _format_single_result(self, result: Dict[str, Any], method: str) -> Dict[str, Any]:
        """格式化单个引擎结果"""
        return {
            'success': True,
            'suit': result.get('suit', ''),
            'rank': result.get('rank', result.get('character', '')),
            'suit_name': result.get('suit_name', ''),
            'suit_symbol': result.get('suit_symbol', ''),
            'display_name': result.get('display_name', result.get('rank', result.get('character', ''))),
            'confidence': result.get('confidence', 0),
            'method': method,
            'single_result': result
        }
    
    def _get_left_corner_image(self, image_path: str) -> Optional[str]:
        """获取左上角图片路径"""
        try:
            image_file = Path(image_path)
            left_pattern = f"{image_file.stem}_left.png"
            left_file = image_file.parent