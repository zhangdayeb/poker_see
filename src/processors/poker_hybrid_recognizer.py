#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克牌混合识别器 - 结合YOLO、OCR和OpenCV多种方法的智能识别系统
功能:
1. YOLO全卡识别 (高置信度直接返回)
2. OCR字符识别 (识别左上角字符)
3. OpenCV花色识别 (基于颜色和形状)
4. 智能结果融合和决策
5. 置信度评估和结果优化
"""

import sys
from pathlib import Path

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

# 调用路径设置
PROJECT_ROOT = setup_project_paths()

import os
import time
from typing import Dict, Any, Optional, List, Tuple
from src.core.utils import (
    format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)

class HybridPokerRecognizer:
    """混合扑克牌识别器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化混合识别器
        
        Args:
            config: 识别配置参数
        """
        # 默认配置
        self.config = {
            # YOLO配置
            'yolo_enabled': True,
            'yolo_confidence_threshold': 0.3,
            'yolo_high_confidence_threshold': 0.8,  # 高置信度阈值，直接采用
            
            # OCR配置
            'ocr_enabled': True,
            'ocr_confidence_threshold': 0.3,
            'ocr_prefer_paddle': True,  # 优先使用PaddleOCR
            
            # OpenCV花色识别配置
            'opencv_suit_enabled': True,
            'opencv_suit_confidence_threshold': 0.4,
            
            # 融合策略配置
            'fusion_strategy': 'weighted',  # weighted, voting, priority
            'min_confidence_for_result': 0.3,  # 最终结果最低置信度要求
            'enable_result_validation': True,  # 启用结果验证
            
            # 调试配置
            'debug_mode': False,
            'save_intermediate_results': False
        }
        
        # 更新用户配置
        if config:
            self.config.update(config)
        
        # 识别方法可用性检查
        self.available_methods = self._check_available_methods()
        
        log_info("混合识别器初始化完成", "HYBRID")
    
    def _check_available_methods(self) -> Dict[str, bool]:
        """检查各识别方法的可用性"""
        availability = {
            'yolo': False,
            'ocr_easy': False,
            'ocr_paddle': False,
            'opencv_suit': True  # OpenCV通常都可用
        }
        
        # 检查YOLO
        try:
            from src.processors.poker_yolo_detector import detect_with_yolo
            availability['yolo'] = True
            log_info("YOLO检测器可用", "HYBRID")
        except ImportError:
            log_warning("YOLO检测器不可用", "HYBRID")
        
        # 检查OCR
        try:
            import easyocr
            availability['ocr_easy'] = True
            log_info("EasyOCR可用", "HYBRID")
        except ImportError:
            log_warning("EasyOCR不可用", "HYBRID")
        
        try:
            from paddleocr import PaddleOCR
            availability['ocr_paddle'] = True
            log_info("PaddleOCR可用", "HYBRID")
        except ImportError:
            log_warning("PaddleOCR不可用", "HYBRID")
        
        return availability
    
    def recognize_poker_card(self, image_path: str, left_image_path: str = None) -> Dict[str, Any]:
        """
        混合识别扑克牌 - 主要接口
        
        Args:
            image_path: 主图片路径 (完整扑克牌图片)
            left_image_path: 左上角图片路径 (用于OCR和花色识别)
            
        Returns:
            识别结果字典
        """
        try:
            log_info(f"开始混合识别: {image_path}", "HYBRID")
            
            # 检查文件存在性
            if not os.path.exists(image_path):
                return format_error_response(f"图片文件不存在: {image_path}", "FILE_NOT_FOUND")
            
            # 如果未提供左上角图片，尝试自动查找
            if not left_image_path:
                left_image_path = self._find_left_corner_image(image_path)
            
            recognition_start_time = time.time()
            
            # 存储各方法的识别结果
            method_results = {}
            
            # 步骤1: YOLO全卡识别
            if self.config['yolo_enabled'] and self.available_methods['yolo']:
                yolo_result = self._recognize_with_yolo(image_path)
                method_results['yolo'] = yolo_result
                
                # 如果YOLO高置信度识别成功，可以直接返回
                if (yolo_result['success'] and 
                    yolo_result.get('confidence', 0) >= self.config['yolo_high_confidence_threshold']):
                    
                    log_success(f"YOLO高置信度识别成功: {yolo_result['display_name']}", "HYBRID")
                    return self._format_final_result(yolo_result, method_results, time.time() - recognition_start_time)
            
            # 步骤2: OCR字符识别 (需要左上角图片)
            if self.config['ocr_enabled'] and left_image_path and os.path.exists(left_image_path):
                ocr_result = self._recognize_with_ocr(left_image_path)
                method_results['ocr'] = ocr_result
            elif self.config['ocr_enabled']:
                log_warning("OCR启用但左上角图片不可用", "HYBRID")
            
            # 步骤3: OpenCV花色识别 (需要左上角图片)
            if (self.config['opencv_suit_enabled'] and self.available_methods['opencv_suit'] and 
                left_image_path and os.path.exists(left_image_path)):
                suit_result = self._recognize_suit_with_opencv(left_image_path)
                method_results['opencv_suit'] = suit_result
            elif self.config['opencv_suit_enabled']:
                log_warning("OpenCV花色识别启用但左上角图片不可用", "HYBRID")
            
            # 步骤4: 结果融合
            final_result = self._fuse_recognition_results(method_results)
            
            recognition_duration = time.time() - recognition_start_time
            
            if final_result['success']:
                log_success(f"混合识别成功: {final_result['display_name']} (耗时: {recognition_duration:.2f}s)", "HYBRID")
            else:
                log_warning(f"混合识别失败: {final_result.get('error', '未知错误')} (耗时: {recognition_duration:.2f}s)", "HYBRID")
            
            return self._format_final_result(final_result, method_results, recognition_duration)
            
        except Exception as e:
            log_error(f"混合识别异常: {e}", "HYBRID")
            return format_error_response(f"混合识别异常: {str(e)}", "HYBRID_RECOGNITION_ERROR")
    
    def _recognize_with_yolo(self, image_path: str) -> Dict[str, Any]:
        """使用YOLO进行识别"""
        try:
            from src.processors.poker_yolo_detector import detect_with_yolo
            
            if self.config['debug_mode']:
                log_info(f"执行YOLO识别: {image_path}", "HYBRID")
            
            result = detect_with_yolo(image_path, self.config['yolo_confidence_threshold'])
            
            if result['success']:
                result['weight'] = 1.0  # YOLO权重最高
                result['method_type'] = 'complete'  # 完整识别
            
            return result
            
        except Exception as e:
            log_error(f"YOLO识别异常: {e}", "HYBRID")
            return {
                'success': False,
                'error': f'YOLO识别异常: {str(e)}',
                'method': 'yolo',
                'weight': 0.0
            }
    
    def _recognize_with_ocr(self, left_image_path: str) -> Dict[str, Any]:
        """使用OCR进行字符识别"""
        try:
            from src.processors.poker_ocr_detector import detect_poker_character
            
            if self.config['debug_mode']:
                log_info(f"执行OCR识别: {left_image_path}", "HYBRID")
            
            result = detect_poker_character(left_image_path, self.config['ocr_prefer_paddle'])
            
            if result['success']:
                # OCR只能识别点数，权重较低
                result['weight'] = 0.6
                result['method_type'] = 'rank_only'  # 仅点数识别
                result['suit'] = ''  # OCR不识别花色
                result['suit_name'] = ''
                result['suit_symbol'] = ''
                result['display_name'] = result.get('character', '')
            
            return result
            
        except Exception as e:
            log_error(f"OCR识别异常: {e}", "HYBRID")
            return {
                'success': False,
                'error': f'OCR识别异常: {str(e)}',
                'method': 'ocr',
                'weight': 0.0
            }
    
    def _recognize_suit_with_opencv(self, left_image_path: str) -> Dict[str, Any]:
        """使用OpenCV进行花色识别"""
        try:
            from src.processors.poker_suit_detector import detect_poker_suit
            
            if self.config['debug_mode']:
                log_info(f"执行OpenCV花色识别: {left_image_path}", "HYBRID")
            
            result = detect_poker_suit(left_image_path)
            
            if result['success']:
                # OpenCV只能识别花色，权重较低
                result['weight'] = 0.5
                result['method_type'] = 'suit_only'  # 仅花色识别
                result['rank'] = ''  # 不识别点数
                result['display_name'] = result.get('suit_symbol', '')
            
            return result
            
        except Exception as e:
            log_error(f"OpenCV花色识别异常: {e}", "HYBRID")
            return {
                'success': False,
                'error': f'OpenCV花色识别异常: {str(e)}',
                'method': 'opencv_suit',
                'weight': 0.0
            }
    
    def _fuse_recognition_results(self, method_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """融合多种识别方法的结果"""
        try:
            if self.config['debug_mode']:
                log_info(f"开始结果融合，可用结果: {list(method_results.keys())}", "HYBRID")
            
            # 过滤出成功的结果
            successful_results = {k: v for k, v in method_results.items() if v.get('success', False)}
            
            if not successful_results:
                return {
                    'success': False,
                    'error': '所有识别方法都失败',
                    'method': 'fusion_failed'
                }
            
            # 根据融合策略选择最终结果
            if self.config['fusion_strategy'] == 'weighted':
                return self._weighted_fusion(successful_results)
            elif self.config['fusion_strategy'] == 'voting':
                return self._voting_fusion(successful_results)
            elif self.config['fusion_strategy'] == 'priority':
                return self._priority_fusion(successful_results)
            else:
                # 默认使用加权融合
                return self._weighted_fusion(successful_results)
                
        except Exception as e:
            log_error(f"结果融合异常: {e}", "HYBRID")
            return {
                'success': False,
                'error': f'结果融合异常: {str(e)}',
                'method': 'fusion_error'
            }
    
    def _weighted_fusion(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """加权融合策略"""
        try:
            # 如果有完整识别结果（YOLO），优先使用
            for method, result in results.items():
                if result.get('method_type') == 'complete' and result.get('confidence', 0) >= self.config['yolo_confidence_threshold']:
                    return result
            
            # 否则尝试组合部分识别结果
            best_suit = ''
            best_suit_symbol = ''
            best_suit_name = ''
            best_rank = ''
            combined_confidence = 0.0
            used_methods = []
            
            # 查找最好的花色识别结果
            suit_results = [(k, v) for k, v in results.items() 
                          if v.get('suit') and v.get('method_type') in ['complete', 'suit_only']]
            if suit_results:
                best_suit_method, best_suit_result = max(suit_results, key=lambda x: x[1].get('confidence', 0) * x[1].get('weight', 1))
                best_suit = best_suit_result.get('suit', '')
                best_suit_symbol = best_suit_result.get('suit_symbol', '')
                best_suit_name = best_suit_result.get('suit_name', '')
                combined_confidence += best_suit_result.get('confidence', 0) * best_suit_result.get('weight', 1) * 0.5
                used_methods.append(best_suit_method)
            
            # 查找最好的点数识别结果
            rank_results = [(k, v) for k, v in results.items() 
                          if v.get('rank') or v.get('character') and v.get('method_type') in ['complete', 'rank_only']]
            if rank_results:
                best_rank_method, best_rank_result = max(rank_results, key=lambda x: x[1].get('confidence', 0) * x[1].get('weight', 1))
                best_rank = best_rank_result.get('rank') or best_rank_result.get('character', '')
                combined_confidence += best_rank_result.get('confidence', 0) * best_rank_result.get('weight', 1) * 0.5
                used_methods.append(best_rank_method)
            
            # 标准化置信度
            if len(used_methods) > 0:
                combined_confidence = min(combined_confidence, 1.0)
            
            if best_suit or best_rank:
                display_name = f"{best_suit_symbol}{best_rank}" if best_suit_symbol and best_rank else (best_suit_symbol or best_rank)
                
                return {
                    'success': True,
                    'suit': best_suit,
                    'rank': best_rank,
                    'suit_symbol': best_suit_symbol,
                    'suit_name': best_suit_name,
                    'display_name': display_name,
                    'confidence': combined_confidence,
                    'method': 'weighted_fusion',
                    'used_methods': used_methods,
                    'fusion_type': 'combined'
                }
            else:
                return {
                    'success': False,
                    'error': '无法从部分识别结果中组合完整信息',
                    'method': 'weighted_fusion_failed'
                }
                
        except Exception as e:
            log_error(f"加权融合失败: {e}", "HYBRID")
            return {
                'success': False,
                'error': f'加权融合失败: {str(e)}',
                'method': 'weighted_fusion_error'
            }
    
    def _voting_fusion(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """投票融合策略"""
        try:
            # 统计各结果的投票
            suit_votes = {}
            rank_votes = {}
            
            for method, result in results.items():
                weight = result.get('weight', 1.0)
                confidence = result.get('confidence', 0.0)
                vote_strength = weight * confidence
                
                # 花色投票
                suit = result.get('suit', '')
                if suit:
                    suit_votes[suit] = suit_votes.get(suit, 0) + vote_strength
                
                # 点数投票
                rank = result.get('rank') or result.get('character', '')
                if rank:
                    rank_votes[rank] = rank_votes.get(rank, 0) + vote_strength
            
            # 选择得票最高的结果
            best_suit = max(suit_votes.items(), key=lambda x: x[1])[0] if suit_votes else ''
            best_rank = max(rank_votes.items(), key=lambda x: x[1])[0] if rank_votes else ''
            
            if best_suit or best_rank:
                # 查找对应的详细信息
                suit_info = self._get_suit_info(best_suit)
                combined_confidence = (suit_votes.get(best_suit, 0) + rank_votes.get(best_rank, 0)) / 2
                
                return {
                    'success': True,
                    'suit': best_suit,
                    'rank': best_rank,
                    'suit_symbol': suit_info['symbol'],
                    'suit_name': suit_info['name'],
                    'display_name': f"{suit_info['symbol']}{best_rank}",
                    'confidence': min(combined_confidence, 1.0),
                    'method': 'voting_fusion',
                    'suit_votes': suit_votes,
                    'rank_votes': rank_votes
                }
            else:
                return {
                    'success': False,
                    'error': '投票融合未产生有效结果',
                    'method': 'voting_fusion_failed'
                }
                
        except Exception as e:
            log_error(f"投票融合失败: {e}", "HYBRID")
            return {
                'success': False,
                'error': f'投票融合失败: {str(e)}',
                'method': 'voting_fusion_error'
            }
    
    def _priority_fusion(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """优先级融合策略"""
        try:
            # 方法优先级：YOLO > OCR+OpenCV组合 > 单独OCR > 单独OpenCV
            priority_order = ['yolo', 'ocr', 'opencv_suit']
            
            # 首先尝试完整识别方法
            for method in priority_order:
                if method in results and results[method].get('method_type') == 'complete':
                    if results[method].get('confidence', 0) >= self.config['min_confidence_for_result']:
                        return results[method]
            
            # 其次尝试组合部分识别
            ocr_result = results.get('ocr', {})
            opencv_result = results.get('opencv_suit', {})
            
            if ocr_result.get('success') and opencv_result.get('success'):
                # 组合OCR和OpenCV结果
                combined_confidence = (ocr_result.get('confidence', 0) + opencv_result.get('confidence', 0)) / 2
                
                return {
                    'success': True,
                    'suit': opencv_result.get('suit', ''),
                    'rank': ocr_result.get('character', ''),
                    'suit_symbol': opencv_result.get('suit_symbol', ''),
                    'suit_name': opencv_result.get('suit_name', ''),
                    'display_name': f"{opencv_result.get('suit_symbol', '')}{ocr_result.get('character', '')}",
                    'confidence': combined_confidence,
                    'method': 'priority_fusion_combined',
                    'used_methods': ['ocr', 'opencv_suit']
                }
            
            # 最后按优先级返回单个结果
            for method in priority_order:
                if method in results:
                    return results[method]
            
            return {
                'success': False,
                'error': '优先级融合未找到合适结果',
                'method': 'priority_fusion_failed'
            }
            
        except Exception as e:
            log_error(f"优先级融合失败: {e}", "HYBRID")
            return {
                'success': False,
                'error': f'优先级融合失败: {str(e)}',
                'method': 'priority_fusion_error'
            }
    
    def _get_suit_info(self, suit: str) -> Dict[str, str]:
        """获取花色详细信息"""
        suit_mapping = {
            'spades': {'name': '黑桃', 'symbol': '♠️'},
            'hearts': {'name': '红桃', 'symbol': '♥️'},
            'diamonds': {'name': '方块', 'symbol': '♦️'},
            'clubs': {'name': '梅花', 'symbol': '♣️'}
        }
        
        return suit_mapping.get(suit, {'name': '未知', 'symbol': '?'})
    
    def _find_left_corner_image(self, image_path: str) -> Optional[str]:
        """查找对应的左上角图片"""
        try:
            image_file = Path(image_path)
            
            # 尝试不同的命名模式
            possible_patterns = [
                f"{image_file.stem}_left.png",
                f"{image_file.stem}_left{image_file.suffix}",
            ]
            
            for pattern in possible_patterns:
                left_path = image_file.parent / pattern
                if left_path.exists():
                    return str(left_path)
            
            return None
            
        except Exception:
            return None
    
    def _format_final_result(self, result: Dict[str, Any], method_results: Dict[str, Dict[str, Any]], 
                           duration: float) -> Dict[str, Any]:
        """格式化最终结果"""
        try:
            # 基本结果格式化
            formatted_result = {
                'success': result.get('success', False),
                'suit': result.get('suit', ''),
                'rank': result.get('rank', ''),
                'suit_symbol': result.get('suit_symbol', ''),
                'suit_name': result.get('suit_name', ''),
                'display_name': result.get('display_name', ''),
                'confidence': result.get('confidence', 0.0),
                'recognition_duration': duration,
                'timestamp': get_timestamp(),
                'method': result.get('method', 'hybrid'),
                'hybrid_info': {
                    'fusion_strategy': self.config['fusion_strategy'],
                    'used_methods': result.get('used_methods', [result.get('method', '')]),
                    'available_methods': list(method_results.keys()),
                    'method_results': method_results if self.config['debug_mode'] else {}
                }
            }
            
            # 添加错误信息
            if not result.get('success', False):
                formatted_result['error'] = result.get('error', '识别失败')
                formatted_result['error_code'] = result.get('error_code', 'RECOGNITION_FAILED')
            
            # 结果验证
            if self.config['enable_result_validation'] and formatted_result['success']:
                validation_result = self._validate_result(formatted_result)
                formatted_result.update(validation_result)
            
            return formatted_result
            
        except Exception as e:
            log_error(f"结果格式化失败: {e}", "HYBRID")
            return {
                'success': False,
                'error': f'结果格式化失败: {str(e)}',
                'method': 'format_error',
                'recognition_duration': duration,
                'timestamp': get_timestamp()
            }
    
    def _validate_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证识别结果的合理性"""
        try:
            validation_info = {
                'validation_passed': True,
                'validation_warnings': []
            }
            
            # 检查置信度
            confidence = result.get('confidence', 0.0)
            if confidence < self.config['min_confidence_for_result']:
                validation_info['validation_warnings'].append(f"置信度过低: {confidence:.3f}")
            
            # 检查花色和点数的一致性
            suit = result.get('suit', '')
            rank = result.get('rank', '')
            
            if suit and rank:
                # 验证花色格式
                valid_suits = ['spades', 'hearts', 'diamonds', 'clubs']
                if suit not in valid_suits:
                    validation_info['validation_warnings'].append(f"无效花色: {suit}")
                
                # 验证点数格式
                valid_ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
                if rank not in valid_ranks:
                    validation_info['validation_warnings'].append(f"无效点数: {rank}")
            
            # 如果有警告，标记验证未通过
            if validation_info['validation_warnings']:
                validation_info['validation_passed'] = False
            
            return validation_info
            
        except Exception as e:
            return {
                'validation_passed': False,
                'validation_error': str(e)
            }
    
    def get_recognition_capabilities(self) -> Dict[str, Any]:
        """获取当前识别能力信息"""
        return {
            'available_methods': self.available_methods,
            'config': self.config,
            'capabilities': {
                'complete_recognition': self.available_methods.get('yolo', False),
                'rank_recognition': any([
                    self.available_methods.get('ocr_easy', False),
                    self.available_methods.get('ocr_paddle', False)
                ]),
                'suit_recognition': self.available_methods.get('opencv_suit', False),
                'hybrid_fusion': len([k for k, v in self.available_methods.items() if v]) > 1
            }
        }

# 创建全局实例
hybrid_recognizer = HybridPokerRecognizer()

# 导出主要函数
def recognize_poker_card_hybrid(image_path: str, left_image_path: str = None, 
                               config: Dict[str, Any] = None) -> Dict[str, Any]:
    """混合识别扑克牌 - 主要接口函数"""
    if config:
        # 使用自定义配置创建临时识别器
        temp_recognizer = HybridPokerRecognizer(config)
        return temp_recognizer.recognize_poker_card(image_path, left_image_path)
    else:
        # 使用全局识别器
        return hybrid_recognizer.recognize_poker_card(image_path, left_image_path)

def get_hybrid_recognition_capabilities() -> Dict[str, Any]:
    """获取混合识别能力信息"""
    return hybrid_recognizer.get_recognition_capabilities()

if __name__ == "__main__":
    # 测试混合识别器
    print("🧪 测试混合扑克牌识别器")
    print("=" * 60)
    
    # 显示可用能力
    capabilities = get_hybrid_recognition_capabilities()
    print("🔍 识别能力:")
    for method, available in capabilities['available_methods'].items():
        status = "✅ 可用" if available else "❌ 不可用"
        print(f"   {method}: {status}")
    
    # 测试识别
    test_images = [
        ("src/image/cut/camera_001_zhuang_1.png", "src/image/cut/camera_001_zhuang_1_left.png"),
        ("src/image/cut/camera_001_xian_1.png", "src/image/cut/camera_001_xian_1_left.png")
    ]
    
    for main_image, left_image in test_images:
        if os.path.exists(main_image):
            print(f"\n📸 测试图片: {main_image}")
            print("-" * 40)
            
            result = recognize_poker_card_hybrid(main_image, left_image)
            
            if result['success']:
                print("✅ 混合识别成功!")
                print(f"   结果: {result['display_name']}")
                print(f"   花色: {result['suit_name']} ({result['suit_symbol']})")
                print(f"   点数: {result['rank']}")
                print(f"   置信度: {result['confidence']:.3f}")
                print(f"   耗时: {result['recognition_duration']:.3f}秒")
                print(f"   使用方法: {result['hybrid_info']['used_methods']}")
                
                if result.get('validation_warnings'):
                    print(f"   验证警告: {result['validation_warnings']}")
            else:
                print("❌ 混合识别失败!")
                print(f"   错误: {result.get('error', '未知错误')}")
                print(f"   耗时: {result.get('recognition_duration', 0):.3f}秒")
        else:
            print(f"\n❌ 测试图片不存在: {main_image}")
    
    print("\n✅ 混合识别器测试完成")