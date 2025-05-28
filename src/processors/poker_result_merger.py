#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克识别结果合并器 - 处理多个位置的识别结果，进行整合和优化
功能:
1. 合并多个位置的识别结果
2. 结果一致性检查和冲突解决
3. 置信度统计和质量评估
4. 结果格式化和标准化输出
5. 历史结果对比和趋势分析
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

import time
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter, defaultdict
from src.core.utils import (
    format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)

class PokerResultMerger:
    """扑克识别结果合并器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化结果合并器
        
        Args:
            config: 合并器配置参数
        """
        # 默认配置
        self.config = {
            # 基础配置
            'standard_positions': ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3'],
            'min_confidence_threshold': 0.3,  # 最低置信度阈值
            'high_confidence_threshold': 0.8,  # 高置信度阈值
            
            # 冲突解决配置
            'conflict_resolution_strategy': 'highest_confidence',  # highest_confidence, voting, manual
            'enable_consistency_check': True,  # 启用一致性检查
            'consistency_tolerance': 0.1,  # 一致性容忍度
            
            # 质量评估配置
            'quality_assessment_enabled': True,
            'require_minimum_positions': 2,  # 至少需要识别出的位置数
            'duplicate_detection_enabled': True,  # 启用重复检测
            
            # 历史对比配置
            'enable_history_comparison': False,
            'history_weight': 0.2,  # 历史结果权重
            'max_history_entries': 10,  # 最大历史记录数
            
            # 输出格式配置
            'include_metadata': True,  # 包含元数据
            'include_quality_metrics': True,  # 包含质量指标
            'include_debug_info': False  # 包含调试信息
        }
        
        # 更新用户配置
        if config:
            self.config.update(config)
        
        # 历史结果存储
        self.history_results = []
        
        log_info("结果合并器初始化完成", "MERGER")
    
    def merge_recognition_results(self, position_results: Dict[str, Dict[str, Any]], 
                                camera_id: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        合并多个位置的识别结果
        
        Args:
            position_results: 各位置的识别结果 {position: result}
            camera_id: 摄像头ID
            metadata: 额外元数据
            
        Returns:
            合并后的结果
        """
        try:
            log_info(f"开始合并识别结果，位置数: {len(position_results)}", "MERGER")
            
            merge_start_time = time.time()
            
            # 验证输入数据
            validation_result = self._validate_input_data(position_results)
            if not validation_result['valid']:
                return format_error_response(f"输入数据验证失败: {validation_result['error']}", "INPUT_VALIDATION_ERROR")
            
            # 标准化位置结果
            standardized_results = self._standardize_position_results(position_results)
            
            # 执行冲突检测和解决
            if self.config['enable_consistency_check']:
                conflict_resolution = self._resolve_conflicts(standardized_results)
                standardized_results = conflict_resolution['resolved_results']
            else:
                conflict_resolution = {'conflicts_found': False, 'conflicts': [], 'resolution_actions': []}
            
            # 质量评估
            quality_assessment = {}
            if self.config['quality_assessment_enabled']:
                quality_assessment = self._assess_result_quality(standardized_results)
            
            # 重复检测
            duplicate_analysis = {}
            if self.config['duplicate_detection_enabled']:
                duplicate_analysis = self._detect_duplicates(standardized_results)
            
            # 历史对比
            history_comparison = {}
            if self.config['enable_history_comparison']:
                history_comparison = self._compare_with_history(standardized_results)
            
            # 生成最终结果
            final_result = self._generate_final_result(
                standardized_results, 
                camera_id,
                metadata,
                conflict_resolution,
                quality_assessment,
                duplicate_analysis,
                history_comparison,
                time.time() - merge_start_time
            )
            
            # 更新历史记录
            if self.config['enable_history_comparison']:
                self._update_history(final_result)
            
            log_success(f"结果合并完成，识别成功: {final_result['summary']['successful_positions']}/{final_result['summary']['total_positions']}", "MERGER")
            
            return final_result
            
        except Exception as e:
            log_error(f"结果合并异常: {e}", "MERGER")
            return format_error_response(f"结果合并异常: {str(e)}", "MERGE_ERROR")
    
    def _validate_input_data(self, position_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """验证输入数据的有效性"""
        try:
            if not isinstance(position_results, dict):
                return {'valid': False, 'error': '位置结果必须是字典格式'}
            
            if not position_results:
                return {'valid': False, 'error': '位置结果不能为空'}
            
            # 验证位置名称
            valid_positions = set(self.config['standard_positions'])
            invalid_positions = []
            
            for position in position_results.keys():
                if position not in valid_positions:
                    invalid_positions.append(position)
            
            if invalid_positions:
                log_warning(f"发现无效位置: {invalid_positions}", "MERGER")
            
            # 验证结果格式
            format_errors = []
            for position, result in position_results.items():
                if not isinstance(result, dict):
                    format_errors.append(f"位置 {position} 的结果不是字典格式")
                elif 'success' not in result:
                    format_errors.append(f"位置 {position} 的结果缺少success字段")
            
            if format_errors:
                return {'valid': False, 'error': '; '.join(format_errors)}
            
            return {'valid': True, 'error': None}
            
        except Exception as e:
            return {'valid': False, 'error': f'验证异常: {str(e)}'}
    
    def _standardize_position_results(self, position_results: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """标准化位置识别结果"""
        try:
            standardized = {}
            
            for position in self.config['standard_positions']:
                if position in position_results:
                    result = position_results[position].copy()
                    
                    # 标准化成功的结果
                    if result.get('success', False):
                        # 确保必需字段存在
                        result.setdefault('suit', '')
                        result.setdefault('rank', '')
                        result.setdefault('suit_symbol', '')
                        result.setdefault('suit_name', '')
                        result.setdefault('display_name', '')
                        result.setdefault('confidence', 0.0)
                        result.setdefault('method', 'unknown')
                        
                        # 生成显示名称（如果缺失）
                        if not result['display_name'] and result['suit_symbol'] and result['rank']:
                            result['display_name'] = f"{result['suit_symbol']}{result['rank']}"
                        elif not result['display_name'] and result['rank']:
                            result['display_name'] = result['rank']
                        elif not result['display_name'] and result['suit_symbol']:
                            result['display_name'] = result['suit_symbol']
                        
                        # 验证置信度范围
                        confidence = result.get('confidence', 0.0)
                        if not (0.0 <= confidence <= 1.0):
                            result['confidence'] = max(0.0, min(1.0, confidence))
                    
                    standardized[position] = result
                else:
                    # 创建空结果
                    standardized[position] = {
                        'success': False,
                        'suit': '',
                        'rank': '',
                        'suit_symbol': '',
                        'suit_name': '',
                        'display_name': '',
                        'confidence': 0.0,
                        'method': 'not_processed',
                        'error': '未处理'
                    }
            
            return standardized
            
        except Exception as e:
            log_error(f"标准化结果失败: {e}", "MERGER")
            return position_results
    
    def _resolve_conflicts(self, position_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """检测和解决结果冲突"""
        try:
            conflicts = []
            resolution_actions = []
            resolved_results = position_results.copy()
            
            # 获取成功的识别结果
            successful_results = {pos: result for pos, result in position_results.items() 
                                if result.get('success', False)}
            
            if len(successful_results) < 2:
                return {
                    'conflicts_found': False,
                    'conflicts': [],
                    'resolution_actions': [],
                    'resolved_results': resolved_results
                }
            
            # 检测置信度异常
            confidences = [result['confidence'] for result in successful_results.values()]
            avg_confidence = sum(confidences) / len(confidences)
            std_confidence = (sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)) ** 0.5
            
            confidence_conflicts = []
            for position, result in successful_results.items():
                confidence = result['confidence']
                if abs(confidence - avg_confidence) > 2 * std_confidence and std_confidence > 0.1:
                    confidence_conflicts.append({
                        'type': 'confidence_anomaly',
                        'position': position,
                        'confidence': confidence,
                        'avg_confidence': avg_confidence,
                        'deviation': abs(confidence - avg_confidence)
                    })
            
            if confidence_conflicts:
                conflicts.extend(confidence_conflicts)
            
            # 检测结果不一致
            card_counts = Counter()
            position_cards = {}
            
            for position, result in successful_results.items():
                if result.get('display_name'):
                    card = result['display_name']
                    card_counts[card] += 1
                    if card not in position_cards:
                        position_cards[card] = []
                    position_cards[card].append(position)
            
            # 检测重复卡牌
            duplicate_conflicts = []
            for card, count in card_counts.items():
                if count > 1:
                    duplicate_conflicts.append({
                        'type': 'duplicate_card',
                        'card': card,
                        'count': count,
                        'positions': position_cards[card]
                    })
            
            if duplicate_conflicts:
                conflicts.extend(duplicate_conflicts)
                
                # 解决重复冲突
                if self.config['conflict_resolution_strategy'] == 'highest_confidence':
                    for conflict in duplicate_conflicts:
                        card = conflict['card']
                        positions = conflict['positions']
                        
                        # 找到该卡牌在各位置的置信度
                        position_confidences = [(pos, resolved_results[pos]['confidence']) 
                                              for pos in positions]
                        position_confidences.sort(key=lambda x: x[1], reverse=True)
                        
                        # 保留置信度最高的，其他设为失败
                        keep_position = position_confidences[0][0]
                        for pos, _ in position_confidences[1:]:
                            resolved_results[pos] = {
                                'success': False,
                                'suit': '',
                                'rank': '',
                                'suit_symbol': '',
                                'suit_name': '',
                                'display_name': '',
                                'confidence': 0.0,
                                'method': 'conflict_resolved',
                                'error': f'重复冲突已解决，保留{keep_position}的结果'
                            }
                            
                            resolution_actions.append({
                                'action': 'remove_duplicate',
                                'position': pos,
                                'reason': f'重复卡牌{card}，保留置信度更高的{keep_position}'
                            })
            
            return {
                'conflicts_found': len(conflicts) > 0,
                'conflicts': conflicts,
                'resolution_actions': resolution_actions,
                'resolved_results': resolved_results
            }
            
        except Exception as e:
            log_error(f"冲突解决失败: {e}", "MERGER")
            return {
                'conflicts_found': False,
                'conflicts': [{'type': 'resolution_error', 'error': str(e)}],
                'resolution_actions': [],
                'resolved_results': position_results
            }
    
    def _assess_result_quality(self, position_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """评估结果质量"""
        try:
            successful_results = {pos: result for pos, result in position_results.items() 
                                if result.get('success', False)}
            
            total_positions = len(self.config['standard_positions'])
            successful_positions = len(successful_results)
            success_rate = successful_positions / total_positions if total_positions > 0 else 0
            
            # 置信度统计
            confidences = [result['confidence'] for result in successful_results.values()]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            min_confidence = min(confidences) if confidences else 0
            max_confidence = max(confidences) if confidences else 0
            
            # 质量等级评估
            quality_score = 0
            quality_factors = []
            
            # 成功率评分 (40%)
            success_score = success_rate * 0.4
            quality_score += success_score
            quality_factors.append(f"成功率: {success_rate:.1%} (权重40%)")
            
            # 平均置信度评分 (40%)
            confidence_score = avg_confidence * 0.4
            quality_score += confidence_score
            quality_factors.append(f"平均置信度: {avg_confidence:.3f} (权重40%)")
            
            # 一致性评分 (20%)
            consistency_score = 0.2
            if confidences:
                std_confidence = (sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)) ** 0.5
                consistency_score = max(0, 0.2 - std_confidence * 0.2)
            quality_score += consistency_score
            quality_factors.append(f"一致性: {consistency_score/0.2:.1%} (权重20%)")
            
            # 质量等级
            if quality_score >= 0.8:
                quality_level = "优秀"
            elif quality_score >= 0.6:
                quality_level = "良好"
            elif quality_score >= 0.4:
                quality_level = "一般"
            elif quality_score >= 0.2:
                quality_level = "较差"
            else:
                quality_level = "很差"
            
            # 质量建议
            suggestions = []
            if success_rate < 0.5:
                suggestions.append("建议检查摄像头角度和光照条件")
            if avg_confidence < 0.5:
                suggestions.append("建议调整识别算法参数或更换识别模型")
            if len(confidences) > 1:
                std_confidence = (sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)) ** 0.5
                if std_confidence > 0.2:
                    suggestions.append("识别结果一致性较差，建议检查图像质量")
            
            return {
                'quality_score': quality_score,
                'quality_level': quality_level,
                'success_rate': success_rate,
                'confidence_stats': {
                    'average': avg_confidence,
                    'minimum': min_confidence,
                    'maximum': max_confidence,
                    'count': len(confidences)
                },
                'quality_factors': quality_factors,
                'suggestions': suggestions,
                'meets_minimum_requirement': successful_positions >= self.config['require_minimum_positions']
            }
            
        except Exception as e:
            log_error(f"质量评估失败: {e}", "MERGER")
            return {
                'quality_score': 0.0,
                'quality_level': "评估失败",
                'error': str(e)
            }
    
    def _detect_duplicates(self, position_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """检测重复卡牌"""
        try:
            successful_results = {pos: result for pos, result in position_results.items() 
                                if result.get('success', False)}
            
            # 统计卡牌出现次数
            card_counts = Counter()
            card_positions = defaultdict(list)
            
            for position, result in successful_results.items():
                if result.get('display_name'):
                    card = result['display_name']
                    card_counts[card] += 1
                    card_positions[card].append({
                        'position': position,
                        'confidence': result.get('confidence', 0.0),
                        'method': result.get('method', 'unknown')
                    })
            
            # 识别重复
            duplicates = []
            for card, count in card_counts.items():
                if count > 1:
                    duplicates.append({
                        'card': card,
                        'count': count,
                        'positions': card_positions[card]
                    })
            
            # 分析重复模式
            duplicate_analysis = {
                'total_duplicates': len(duplicates),
                'duplicate_cards': duplicates,
                'unique_cards': len([card for card, count in card_counts.items() if count == 1]),
                'duplicate_rate': len(duplicates) / len(card_counts) if card_counts else 0
            }
            
            # 重复建议
            if duplicates:
                suggestions = [
                    "发现重复卡牌，建议检查识别算法或图像处理",
                    "可能存在反光或阴影导致的误识别",
                    "建议调整摄像头角度或光照条件"
                ]
                duplicate_analysis['suggestions'] = suggestions
            
            return duplicate_analysis
            
        except Exception as e:
            log_error(f"重复检测失败: {e}", "MERGER")
            return {
                'total_duplicates': 0,
                'error': str(e)
            }
    
    def _compare_with_history(self, current_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """与历史结果对比"""
        try:
            if not self.history_results:
                return {
                    'history_available': False,
                    'message': '无历史数据可供对比'
                }
            
            # 获取最近的历史结果
            recent_history = self.history_results[-3:] if len(self.history_results) >= 3 else self.history_results
            
            # 统计历史中每个位置的常见结果
            position_history = defaultdict(list)
            for hist_result in recent_history:
                positions = hist_result.get('positions', {})
                for pos, result in positions.items():
                    if result.get('success', False):
                        position_history[pos].append(result.get('display_name', ''))
            
            # 对比当前结果与历史结果
            comparison = {}
            consistency_score = 0
            total_comparisons = 0
            
            for position, current_result in current_results.items():
                if current_result.get('success', False) and position in position_history:
                    current_card = current_result.get('display_name', '')
                    historical_cards = position_history[position]
                    
                    # 计算一致性
                    matches = historical_cards.count(current_card)
                    consistency = matches / len(historical_cards) if historical_cards else 0
                    
                    comparison[position] = {
                        'current_card': current_card,
                        'historical_cards': historical_cards,
                        'consistency': consistency,
                        'is_consistent': consistency >= 0.5
                    }
                    
                    consistency_score += consistency
                    total_comparisons += 1
            
            overall_consistency = consistency_score / total_comparisons if total_comparisons > 0 else 0
            
            return {
                'history_available': True,
                'comparison_count': total_comparisons,
                'overall_consistency': overall_consistency,
                'position_comparisons': comparison,
                'is_consistent_with_history': overall_consistency >= 0.6
            }
            
        except Exception as e:
            log_error(f"历史对比失败: {e}", "MERGER")
            return {
                'history_available': False,
                'error': str(e)
            }
    
    def _generate_final_result(self, standardized_results: Dict[str, Dict[str, Any]], 
                             camera_id: str, metadata: Dict[str, Any],
                             conflict_resolution: Dict[str, Any],
                             quality_assessment: Dict[str, Any],
                             duplicate_analysis: Dict[str, Any],
                             history_comparison: Dict[str, Any],
                             processing_duration: float) -> Dict[str, Any]:
        """生成最终合并结果"""
        try:
            # 统计基本信息
            successful_results = {pos: result for pos, result in standardized_results.items() 
                                if result.get('success', False)}
            
            total_positions = len(self.config['standard_positions'])
            successful_positions = len(successful_results)
            
            # 构建基础结果
            final_result = {
                'success': successful_positions > 0,
                'camera_id': camera_id,
                'timestamp': get_timestamp(),
                'processing_duration': processing_duration,
                
                # 位置结果
                'positions': standardized_results,
                
                # 统计摘要
                'summary': {
                    'total_positions': total_positions,
                    'successful_positions': successful_positions,
                    'failed_positions': total_positions - successful_positions,
                    'success_rate': successful_positions / total_positions if total_positions > 0 else 0,
                    'recognized_cards': [result['display_name'] for result in successful_results.values() 
                                       if result.get('display_name')]
                }
            }
            
            # 添加质量评估
            if self.config['include_quality_metrics'] and quality_assessment:
                final_result['quality'] = quality_assessment
            
            # 添加元数据
            if self.config['include_metadata'] and metadata:
                final_result['metadata'] = metadata
            
            # 添加调试信息
            if self.config['include_debug_info']:
                final_result['debug_info'] = {
                    'conflict_resolution': conflict_resolution,
                    'duplicate_analysis': duplicate_analysis,
                    'history_comparison': history_comparison,
                    'config': self.config
                }
            
            # 添加警告信息
            warnings = []
            
            if conflict_resolution.get('conflicts_found', False):
                warnings.append(f"检测到 {len(conflict_resolution['conflicts'])} 个冲突")
            
            if duplicate_analysis.get('total_duplicates', 0) > 0:
                warnings.append(f"检测到 {duplicate_analysis['total_duplicates']} 个重复卡牌")
            
            if quality_assessment.get('quality_score', 0) < 0.5:
                warnings.append("识别质量较低")
            
            if successful_positions < self.config['require_minimum_positions']:
                warnings.append(f"识别位置数量不足 ({successful_positions}/{self.config['require_minimum_positions']})")
            
            if warnings:
                final_result['warnings'] = warnings
            
            return final_result
            
        except Exception as e:
            log_error(f"生成最终结果失败: {e}", "MERGER")
            return format_error_response(f"生成最终结果失败: {str(e)}", "GENERATE_RESULT_ERROR")
    
    def _update_history(self, result: Dict[str, Any]):
        """更新历史记录"""
        try:
            # 添加到历史记录
            self.history_results.append({
                'timestamp': result.get('timestamp', get_timestamp()),
                'camera_id': result.get('camera_id'),
                'positions': result.get('positions', {}),
                'summary': result.get('summary', {}),
                'quality': result.get('quality', {})
            })
            
            # 限制历史记录数量
            max_entries = self.config['max_history_entries']
            if len(self.history_results) > max_entries:
                self.history_results = self.history_results[-max_entries:]
            
        except Exception as e:
            log_error(f"更新历史记录失败: {e}", "MERGER")
    
    def get_merge_statistics(self) -> Dict[str, Any]:
        """获取合并统计信息"""
        try:
            if not self.history_results:
                return {
                    'total_merges': 0,
                    'message': '暂无统计数据'
                }
            
            total_merges = len(self.history_results)
            
            # 成功率统计
            success_rates = [hist.get('summary', {}).get('success_rate', 0) for hist in self.history_results]
            avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
            
            # 质量统计
            quality_scores = [hist.get('quality', {}).get('quality_score', 0) for hist in self.history_results]
            avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            # 最近趋势
            recent_results = self.history_results[-5:] if len(self.history_results) >= 5 else self.history_results
            recent_success_rates = [hist.get('summary', {}).get('success_rate', 0) for hist in recent_results]
            recent_avg_success_rate = sum(recent_success_rates) / len(recent_success_rates) if recent_success_rates else 0
            
            return {
                'total_merges': total_merges,
                'average_success_rate': avg_success_rate,
                'average_quality_score': avg_quality_score,
                'recent_success_rate': recent_avg_success_rate,
                'trend': '上升' if recent_avg_success_rate > avg_success_rate else ('下降' if recent_avg_success_rate < avg_success_rate else '稳定'),
                'history_count': len(self.history_results)
            }
            
        except Exception as e:
            log_error(f"获取统计信息失败: {e}", "MERGER")
            return {
                'total_merges': 0,
                'error': str(e)
            }
    
    def clear_history(self):
        """清空历史记录"""
        self.history_results.clear()
        log_info("历史记录已清空", "MERGER")
    
    def export_results(self, results: List[Dict[str, Any]], format_type: str = 'json') -> Dict[str, Any]:
        """
        导出合并结果
        
        Args:
            results: 要导出的结果列表
            format_type: 导出格式 ('json', 'csv', 'summary')
            
        Returns:
            导出结果
        """
        try:
            if format_type == 'json':
                return {
                    'success': True,
                    'format': 'json',
                    'data': results,
                    'export_time': get_timestamp(),
                    'total_records': len(results)
                }
            
            elif format_type == 'csv':
                # 转换为CSV格式数据
                csv_data = []
                headers = ['timestamp', 'camera_id', 'total_positions', 'successful_positions', 
                          'success_rate', 'quality_score', 'quality_level']
                
                # 添加标准位置列
                for position in self.config['standard_positions']:
                    headers.extend([f'{position}_card', f'{position}_confidence'])
                
                csv_data.append(headers)
                
                for result in results:
                    row = [
                        result.get('timestamp', ''),
                        result.get('camera_id', ''),
                        result.get('summary', {}).get('total_positions', 0),
                        result.get('summary', {}).get('successful_positions', 0),
                        result.get('summary', {}).get('success_rate', 0),
                        result.get('quality', {}).get('quality_score', 0),
                        result.get('quality', {}).get('quality_level', '')
                    ]
                    
                    # 添加位置数据
                    positions = result.get('positions', {})
                    for position in self.config['standard_positions']:
                        pos_result = positions.get(position, {})
                        row.extend([
                            pos_result.get('display_name', ''),
                            pos_result.get('confidence', 0.0)
                        ])
                    
                    csv_data.append(row)
                
                return {
                    'success': True,
                    'format': 'csv',
                    'data': csv_data,
                    'export_time': get_timestamp(),
                    'total_records': len(results)
                }
            
            elif format_type == 'summary':
                # 生成汇总报告
                if not results:
                    return {
                        'success': True,
                        'format': 'summary',
                        'data': {'message': '无数据可汇总'},
                        'export_time': get_timestamp()
                    }
                
                # 统计分析
                total_records = len(results)
                success_rates = [r.get('summary', {}).get('success_rate', 0) for r in results]
                quality_scores = [r.get('quality', {}).get('quality_score', 0) for r in results]
                
                # 位置成功率统计
                position_stats = {}
                for position in self.config['standard_positions']:
                    successes = sum(1 for r in results 
                                  if r.get('positions', {}).get(position, {}).get('success', False))
                    position_stats[position] = {
                        'success_count': successes,
                        'success_rate': successes / total_records if total_records > 0 else 0
                    }
                
                # 卡牌统计
                card_counter = Counter()
                for result in results:
                    for pos_result in result.get('positions', {}).values():
                        if pos_result.get('success', False) and pos_result.get('display_name'):
                            card_counter[pos_result['display_name']] += 1
                
                summary_data = {
                    'overview': {
                        'total_records': total_records,
                        'date_range': {
                            'start': results[0].get('timestamp', '') if results else '',
                            'end': results[-1].get('timestamp', '') if results else ''
                        },
                        'average_success_rate': sum(success_rates) / len(success_rates) if success_rates else 0,
                        'average_quality_score': sum(quality_scores) / len(quality_scores) if quality_scores else 0
                    },
                    'position_statistics': position_stats,
                    'most_common_cards': dict(card_counter.most_common(10)),
                    'quality_distribution': {
                        '优秀': sum(1 for r in results if r.get('quality', {}).get('quality_level') == '优秀'),
                        '良好': sum(1 for r in results if r.get('quality', {}).get('quality_level') == '良好'),
                        '一般': sum(1 for r in results if r.get('quality', {}).get('quality_level') == '一般'),
                        '较差': sum(1 for r in results if r.get('quality', {}).get('quality_level') == '较差'),
                        '很差': sum(1 for r in results if r.get('quality', {}).get('quality_level') == '很差')
                    }
                }
                
                return {
                    'success': True,
                    'format': 'summary',
                    'data': summary_data,
                    'export_time': get_timestamp(),
                    'total_records': total_records
                }
            
            else:
                return format_error_response(f"不支持的导出格式: {format_type}", "UNSUPPORTED_FORMAT")
                
        except Exception as e:
            log_error(f"导出结果失败: {e}", "MERGER")
            return format_error_response(f"导出失败: {str(e)}", "EXPORT_ERROR")

    def batch_merge_results(self, batch_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量合并识别结果
        
        Args:
            batch_data: 批量数据列表，每个元素包含position_results等信息
            
        Returns:
            批量合并结果
        """
        try:
            log_info(f"开始批量合并，数据量: {len(batch_data)}", "MERGER")
            
            batch_results = []
            success_count = 0
            error_count = 0
            
            for i, item in enumerate(batch_data):
                try:
                    position_results = item.get('position_results', {})
                    camera_id = item.get('camera_id')
                    metadata = item.get('metadata', {})
                    metadata['batch_index'] = i
                    
                    result = self.merge_recognition_results(position_results, camera_id, metadata)
                    
                    if result.get('success', False):
                        success_count += 1
                    else:
                        error_count += 1
                    
                    batch_results.append(result)
                    
                except Exception as e:
                    error_count += 1
                    batch_results.append({
                        'success': False,
                        'error': f'批量处理第{i}项失败: {str(e)}',
                        'batch_index': i
                    })
            
            # 批量统计
            batch_summary = {
                'total_items': len(batch_data),
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': success_count / len(batch_data) if batch_data else 0
            }
            
            log_success(f"批量合并完成: {success_count}/{len(batch_data)} 成功", "MERGER")
            
            return {
                'success': True,
                'batch_summary': batch_summary,
                'results': batch_results,
                'timestamp': get_timestamp()
            }
            
        except Exception as e:
            log_error(f"批量合并失败: {e}", "MERGER")
            return format_error_response(f"批量合并失败: {str(e)}", "BATCH_MERGE_ERROR")


# 创建全局实例
result_merger = PokerResultMerger()

# 导出主要函数
def merge_poker_recognition_results(position_results: Dict[str, Dict[str, Any]], 
                                   camera_id: str = None, 
                                   metadata: Dict[str, Any] = None,
                                   config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    合并扑克识别结果 - 主要接口函数
    
    Args:
        position_results: 各位置的识别结果
        camera_id: 摄像头ID
        metadata: 额外元数据
        config: 自定义配置
        
    Returns:
        合并后的结果
    """
    if config:
        # 使用自定义配置创建临时合并器
        temp_merger = PokerResultMerger(config)
        return temp_merger.merge_recognition_results(position_results, camera_id, metadata)
    else:
        # 使用全局合并器
        return result_merger.merge_recognition_results(position_results, camera_id, metadata)

def batch_merge_poker_results(batch_data: List[Dict[str, Any]], 
                             config: Dict[str, Any] = None) -> Dict[str, Any]:
    """批量合并扑克识别结果"""
    if config:
        temp_merger = PokerResultMerger(config)
        return temp_merger.batch_merge_results(batch_data)
    else:
        return result_merger.batch_merge_results(batch_data)

def get_merger_statistics() -> Dict[str, Any]:
    """获取合并器统计信息"""
    return result_merger.get_merge_statistics()

def export_poker_results(results: List[Dict[str, Any]], format_type: str = 'json') -> Dict[str, Any]:
    """导出扑克识别结果"""
    return result_merger.export_results(results, format_type)

def clear_merger_history():
    """清空合并器历史记录"""
    result_merger.clear_history()

if __name__ == "__main__":
    # 测试结果合并器
    print("🧪 测试扑克识别结果合并器")
    print("=" * 60)
    
    # 模拟识别结果
    test_position_results = {
        'zhuang_1': {
            'success': True,
            'suit': 'hearts',
            'rank': 'A',
            'suit_symbol': '♥️',
            'suit_name': '红桃',
            'display_name': '♥️A',
            'confidence': 0.95,
            'method': 'yolo'
        },
        'zhuang_2': {
            'success': True,
            'suit': 'spades',
            'rank': 'K',
            'suit_symbol': '♠️',
            'suit_name': '黑桃',
            'display_name': '♠️K',
            'confidence': 0.88,
            'method': 'hybrid'
        },
        'zhuang_3': {
            'success': False,
            'error': '识别失败',
            'confidence': 0.0,
            'method': 'yolo'
        },
        'xian_1': {
            'success': True,
            'suit': 'diamonds',
            'rank': 'Q',
            'suit_symbol': '♦️',
            'suit_name': '方块',
            'display_name': '♦️Q',
            'confidence': 0.78,
            'method': 'ocr+opencv'
        },
        'xian_2': {
            'success': True,
            'suit': 'clubs',
            'rank': 'J',
            'suit_symbol': '♣️',
            'suit_name': '梅花',
            'display_name': '♣️J',
            'confidence': 0.82,
            'method': 'yolo'
        },
        'xian_3': {
            'success': True,
            'suit': 'hearts',  # 故意制造重复以测试冲突检测
            'rank': 'A',
            'suit_symbol': '♥️',
            'suit_name': '红桃',
            'display_name': '♥️A',
            'confidence': 0.65,  # 较低置信度
            'method': 'ocr'
        }
    }
    
    # 测试基本合并功能
    print("📊 测试基本合并功能")
    print("-" * 40)
    
    result = merge_poker_recognition_results(
        test_position_results, 
        camera_id="camera_001",
        metadata={"test_mode": True, "image_path": "test.png"}
    )
    
    if result['success']:
        print("✅ 结果合并成功!")
        print(f"   成功率: {result['summary']['success_rate']:.1%}")
        print(f"   成功位置: {result['summary']['successful_positions']}/{result['summary']['total_positions']}")
        print(f"   识别卡牌: {', '.join(result['summary']['recognized_cards'])}")
        
        if 'quality' in result:
            print(f"   质量等级: {result['quality']['quality_level']} (评分: {result['quality']['quality_score']:.3f})")
        
        if 'warnings' in result:
            print(f"   警告: {'; '.join(result['warnings'])}")
        
        print(f"   处理耗时: {result['processing_duration']:.3f}秒")
    else:
        print("❌ 结果合并失败!")
        print(f"   错误: {result.get('error', '未知错误')}")
    
    # 测试批量合并
    print(f"\n📦 测试批量合并功能")
    print("-" * 40)
    
    batch_test_data = [
        {
            'position_results': test_position_results,
            'camera_id': 'camera_001',
            'metadata': {'batch_test': True, 'index': 0}
        },
        {
            'position_results': {
                'zhuang_1': {'success': True, 'display_name': '♠️K', 'confidence': 0.9, 'suit': 'spades', 'rank': 'K'},
                'xian_1': {'success': True, 'display_name': '♥️Q', 'confidence': 0.85, 'suit': 'hearts', 'rank': 'Q'}
            },
            'camera_id': 'camera_002',
            'metadata': {'batch_test': True, 'index': 1}
        }
    ]
    
    batch_result = batch_merge_poker_results(batch_test_data)
    
    if batch_result['success']:
        print("✅ 批量合并成功!")
        print(f"   总数量: {batch_result['batch_summary']['total_items']}")
        print(f"   成功数: {batch_result['batch_summary']['success_count']}")
        print(f"   失败数: {batch_result['batch_summary']['error_count']}")
        print(f"   成功率: {batch_result['batch_summary']['success_rate']:.1%}")
    else:
        print("❌ 批量合并失败!")
        print(f"   错误: {batch_result.get('error', '未知错误')}")
    
    # 测试导出功能
    print(f"\n📤 测试导出功能")
    print("-" * 40)
    
    export_results = [result] if result.get('success') else []
    if batch_result.get('success'):
        export_results.extend(batch_result.get('results', []))
    
    if export_results:
        # 测试JSON导出
        json_export = export_poker_results(export_results, 'json')
        print(f"JSON导出: {'✅ 成功' if json_export['success'] else '❌ 失败'}")
        
        # 测试汇总导出
        summary_export = export_poker_results(export_results, 'summary')
        print(f"汇总导出: {'✅ 成功' if summary_export['success'] else '❌ 失败'}")
        
        if summary_export['success']:
            summary_data = summary_export['data']
            print(f"   汇总记录数: {summary_data['overview']['total_records']}")
            print(f"   平均成功率: {summary_data['overview']['average_success_rate']:.1%}")
    
    # 测试统计信息
    print(f"\n📈 测试统计信息")
    print("-" * 40)
    
    stats = get_merger_statistics()
    if stats.get('total_merges', 0) > 0:
        print(f"总合并次数: {stats['total_merges']}")
        print(f"平均成功率: {stats['average_success_rate']:.1%}")
        print(f"平均质量评分: {stats['average_quality_score']:.3f}")
        print(f"趋势: {stats['trend']}")
    else:
        print("暂无统计数据")
    
    print("\n✅ 结果合并器测试完成")