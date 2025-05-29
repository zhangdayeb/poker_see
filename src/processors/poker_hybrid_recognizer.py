#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版扑克牌混合识别器 - 统一的结果整合入口
功能:
1. 批量处理多个位置的识别
2. 统一的结果整合和优化
3. 标准化输出格式
4. 为 see.py 和 tui.py 提供统一接口
"""

import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

class UnifiedPokerRecognizer:
    """统一扑克识别器 - 整合所有识别逻辑"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化统一识别器"""
        # 默认配置
        self.config = {
            # 识别方法配置
            'yolo_enabled': True,
            'yolo_confidence_threshold': 0.3,
            'yolo_high_confidence_threshold': 0.8,
            
            'ocr_enabled': True,
            'ocr_confidence_threshold': 0.3,
            'ocr_prefer_paddle': True,
            
            'opencv_suit_enabled': True,
            'opencv_suit_confidence_threshold': 0.4,
            
            # 融合策略
            'fusion_strategy': 'weighted',
            'min_confidence_for_result': 0.3,
            'enable_result_validation': True,
            
            # 结果整合配置
            'enable_result_merging': True,
            'min_confidence_threshold': 0.3,
            'high_confidence_threshold': 0.8,
            'conflict_resolution_strategy': 'highest_confidence',
            'enable_consistency_check': True,
            'quality_assessment_enabled': True,
            'duplicate_detection_enabled': True,
            
            # 输出配置
            'output_format': 'standard',  # standard, simple, database
            'include_debug_info': False,
            'include_quality_metrics': True,
            'save_intermediate_results': False
        }
        
        # 更新用户配置
        if config:
            self.config.update(config)
        
        # 标准位置列表
        self.standard_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        # 导入识别器
        self._init_recognizers()
        
        print(f"🧠 统一扑克识别器初始化完成")
    
    def _init_recognizers(self):
        """初始化各个识别器"""
        try:
            # 混合识别器
            from src.processors.poker_hybrid_recognizer import HybridPokerRecognizer
            self.hybrid_recognizer = HybridPokerRecognizer(self.config)
            
            # 结果合并器（如果启用）
            if self.config['enable_result_merging']:
                from src.processors.poker_result_merger import PokerResultMerger
                merger_config = {
                    'min_confidence_threshold': self.config['min_confidence_threshold'],
                    'high_confidence_threshold': self.config['high_confidence_threshold'],
                    'conflict_resolution_strategy': self.config['conflict_resolution_strategy'],
                    'enable_consistency_check': self.config['enable_consistency_check'],
                    'quality_assessment_enabled': self.config['quality_assessment_enabled'],
                    'duplicate_detection_enabled': self.config['duplicate_detection_enabled']
                }
                self.result_merger = PokerResultMerger(merger_config)
            else:
                self.result_merger = None
                
        except Exception as e:
            print(f"❌ 识别器初始化失败: {e}")
            raise
    
    def recognize_camera_all_positions(self, camera_id: str, image_path: str = None) -> Dict[str, Any]:
        """
        识别摄像头所有位置的扑克牌 - 主要接口
        
        Args:
            camera_id: 摄像头ID
            image_path: 原始图片路径（可选，如果不提供则自动拍照和裁剪）
            
        Returns:
            统一格式的识别结果
        """
        try:
            print(f"🎯 开始识别摄像头 {camera_id} 的所有位置")
            
            total_start_time = time.time()
            
            # 步骤1: 准备图片（拍照+裁剪 或 使用现有图片）
            if image_path is None:
                prep_result = self._prepare_images(camera_id)
            else:
                prep_result = self._prepare_images_from_existing(image_path)
            
            if not prep_result['success']:
                return self._format_error_result(camera_id, prep_result['error'], 'IMAGE_PREPARATION')
            
            # 步骤2: 批量识别所有位置
            recognition_result = self._batch_recognize_positions(
                camera_id, 
                prep_result['main_files'], 
                prep_result['left_files']
            )
            
            if not recognition_result['success']:
                return self._format_error_result(camera_id, recognition_result['error'], 'BATCH_RECOGNITION')
            
            # 步骤3: 结果整合和优化
            if self.config['enable_result_merging']:
                final_result = self._merge_and_optimize_results(camera_id, recognition_result['position_results'])
            else:
                final_result = self._format_simple_results(camera_id, recognition_result['position_results'])
            
            # 添加总体信息
            total_duration = time.time() - total_start_time
            final_result['total_duration'] = total_duration
            final_result['preparation_info'] = prep_result.get('info', {})
            final_result['recognition_info'] = recognition_result.get('info', {})
            
            # 根据输出格式调整结果
            formatted_result = self._format_output_by_type(final_result)
            
            print(f"✅ 摄像头 {camera_id} 识别完成: {formatted_result['summary']['successful_positions']}/{formatted_result['summary']['total_positions']} 成功 (耗时: {total_duration:.2f}s)")
            
            return formatted_result
            
        except Exception as e:
            print(f"❌ 摄像头 {camera_id} 识别异常: {e}")
            return self._format_error_result(camera_id, str(e), 'RECOGNITION_EXCEPTION')
    
    def _prepare_images(self, camera_id: str) -> Dict[str, Any]:
        """准备图片：拍照+裁剪"""
        try:
            print(f"   📷 拍照...")
            
            # 拍照
            from src.processors.photo_controller import take_photo_by_id
            photo_result = take_photo_by_id(camera_id)
            
            if photo_result['status'] != 'success':
                return {
                    'success': False,
                    'error': f"拍照失败: {photo_result['message']}"
                }
            
            image_path = photo_result['data']['file_path']
            print(f"   ✅ 拍照成功: {photo_result['data']['filename']}")
            
            # 裁剪
            return self._crop_images(image_path)
            
        except Exception as e:
            return {
                'success': False,
                'error': f"图片准备异常: {str(e)}"
            }
    
    def _prepare_images_from_existing(self, image_path: str) -> Dict[str, Any]:
        """使用现有图片：仅裁剪"""
        try:
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': f"图片文件不存在: {image_path}"
                }
            
            print(f"   📁 使用现有图片: {Path(image_path).name}")
            
            # 裁剪
            return self._crop_images(image_path)
            
        except Exception as e:
            return {
                'success': False,
                'error': f"使用现有图片异常: {str(e)}"
            }
    
    def _crop_images(self, image_path: str) -> Dict[str, Any]:
        """裁剪图片"""
        try:
            print(f"   ✂️  裁剪图片...")
            
            from src.processors.image_cutter import process_image
            
            start_time = time.time()
            success = process_image(image_path)
            crop_duration = time.time() - start_time
            
            if not success:
                return {
                    'success': False,
                    'error': "图片裁剪失败"
                }
            
            # 查找裁剪后的图片
            image_file = Path(image_path)
            cut_dir = image_file.parent / "cut"
            
            if not cut_dir.exists():
                return {
                    'success': False,
                    'error': "裁剪目录不存在"
                }
            
            pattern = f"{image_file.stem}_*.png"
            all_files = list(cut_dir.glob(pattern))
            
            # 分离主图片和左上角图片
            main_files = [str(f) for f in all_files if not f.name.endswith('_left.png')]
            left_files = [str(f) for f in all_files if f.name.endswith('_left.png')]
            
            main_files.sort()
            left_files.sort()
            
            print(f"   ✅ 裁剪完成: {len(main_files)} 个区域 ({crop_duration:.2f}s)")
            
            return {
                'success': True,
                'main_files': main_files,
                'left_files': left_files,
                'info': {
                    'total_regions': len(main_files),
                    'crop_duration': crop_duration,
                    'cut_directory': str(cut_dir)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"裁剪图片异常: {str(e)}"
            }
    
    def _batch_recognize_positions(self, camera_id: str, main_files: List[str], left_files: List[str]) -> Dict[str, Any]:
        """批量识别所有位置"""
        try:
            print(f"   🧠 混合识别...")
            
            position_results = {}
            successful_count = 0
            total_count = len(main_files)
            
            # 创建主图片和左上角图片的对应关系
            main_to_left_map = self._create_image_mapping(main_files, left_files)
            
            recognition_start_time = time.time()
            
            # 逐个识别每个位置
            for main_image_path in main_files:
                position = self._extract_position_from_filename(Path(main_image_path).name)
                left_image_path = main_to_left_map.get(main_image_path)
                
                # 使用混合识别器识别单个位置
                result = self.hybrid_recognizer.recognize_poker_card(main_image_path, left_image_path)
                
                if result['success']:
                    successful_count += 1
                
                position_results[position] = result
            
            recognition_duration = time.time() - recognition_start_time
            success_rate = (successful_count / total_count * 100) if total_count > 0 else 0
            
            print(f"   ✅ 识别完成: {successful_count}/{total_count} 成功 ({success_rate:.1f}%) ({recognition_duration:.2f}s)")
            
            return {
                'success': successful_count > 0,
                'position_results': position_results,
                'info': {
                    'successful_count': successful_count,
                    'total_count': total_count,
                    'success_rate': success_rate,
                    'recognition_duration': recognition_duration
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"批量识别异常: {str(e)}"
            }
    
    def _merge_and_optimize_results(self, camera_id: str, position_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """使用结果合并器整合和优化结果"""
        try:
            print(f"   🔄 结果整合...")
            
            if not self.result_merger:
                return self._format_simple_results(camera_id, position_results)
            
            metadata = {
                'system_mode': 'unified_recognizer',
                'fusion_strategy': self.config['fusion_strategy'],
                'timestamp': datetime.now().isoformat()
            }
            
            merge_start_time = time.time()
            merge_result = self.result_merger.merge_recognition_results(
                position_results,
                camera_id=camera_id,
                metadata=metadata
            )
            merge_duration = time.time() - merge_start_time
            
            if merge_result.get('success'):
                print(f"   ✅ 整合完成 ({merge_duration:.3f}s)")
                merge_result['merge_duration'] = merge_duration
                return merge_result
            else:
                print(f"   ⚠️  整合失败，使用简单格式: {merge_result.get('error', '未知错误')}")
                return self._format_simple_results(camera_id, position_results)
            
        except Exception as e:
            print(f"   ⚠️  整合异常，使用简单格式: {e}")
            return self._format_simple_results(camera_id, position_results)
    
    def _format_simple_results(self, camera_id: str, position_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """格式化简单结果（不使用合并器）"""
        positions = {}
        successful_positions = 0
        
        for position in self.standard_positions:
            if position in position_results and position_results[position]['success']:
                result = position_results[position]
                positions[position] = {
                    'success': True,
                    'suit': result.get('suit', ''),
                    'rank': result.get('rank', ''),
                    'suit_symbol': result.get('suit_symbol', ''),
                    'suit_name': result.get('suit_name', ''),
                    'display_name': result.get('display_name', ''),
                    'confidence': result.get('confidence', 0.0),
                    'method': result.get('method', 'unknown')
                }
                successful_positions += 1
            else:
                positions[position] = {
                    'success': False,
                    'suit': '',
                    'rank': '',
                    'suit_symbol': '',
                    'suit_name': '',
                    'display_name': '',
                    'confidence': 0.0,
                    'method': 'failed',
                    'error': position_results.get(position, {}).get('error', '识别失败')
                }
        
        return {
            'success': successful_positions > 0,
            'camera_id': camera_id,
            'timestamp': datetime.now().isoformat(),
            'positions': positions,
            'summary': {
                'total_positions': len(self.standard_positions),
                'successful_positions': successful_positions,
                'failed_positions': len(self.standard_positions) - successful_positions,
                'success_rate': (successful_positions / len(self.standard_positions)) * 100,
                'recognized_cards': [pos['display_name'] for pos in positions.values() 
                                   if pos['success'] and pos['display_name']]
            },
            'processing_mode': 'simple',
            'merge_enabled': False
        }
    
    def _format_output_by_type(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """根据输出类型格式化结果"""
        try:
            output_format = self.config['output_format']
            
            if output_format == 'simple':
                return self._format_simple_output(result)
            elif output_format == 'database':
                return self._format_database_output(result)
            else:  # standard
                return result
                
        except Exception as e:
            print(f"⚠️  输出格式化失败: {e}")
            return result
    
    def _format_simple_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """简化输出格式"""
        positions = result.get('positions', {})
        simplified_positions = {}
        
        for pos, pos_result in positions.items():
            if pos_result.get('success', False):
                simplified_positions[pos] = pos_result.get('display_name', '')
            else:
                simplified_positions[pos] = ''
        
        return {
            'success': result.get('success', False),
            'camera_id': result.get('camera_id', ''),
            'timestamp': result.get('timestamp', ''),
            'positions': simplified_positions,
            'success_count': result.get('summary', {}).get('successful_positions', 0),
            'total_duration': result.get('total_duration', 0)
        }
    
    def _format_database_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """数据库输出格式"""
        positions = result.get('positions', {})
        db_positions = {}
        
        # 位置映射
        position_mapping = {
            'zhuang_1': 't1_pl0', 'zhuang_2': 't1_pl1', 'zhuang_3': 't1_pl2',
            'xian_1': 't1_pr0', 'xian_2': 't1_pr1', 'xian_3': 't1_pr2'
        }
        
        # 点数转换
        rank_mapping = {
            '': 0, 'A': 1, '2': 2, '3': 3, '4': 4, '5': 5,
            '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
            'J': 11, 'Q': 12, 'K': 13
        }
        
        # 花色转换
        suit_mapping = {
            '': '0', 'hearts': 'r', 'diamonds': 'f', 'clubs': 'm', 'spades': 'h'
        }
        
        for sys_pos, pos_result in positions.items():
            if sys_pos in position_mapping:
                db_pos = position_mapping[sys_pos]
                
                rank = pos_result.get('rank', '')
                suit = pos_result.get('suit', '')
                
                db_positions[db_pos] = {
                    'rank': str(rank_mapping.get(rank, 0)),
                    'suit': suit_mapping.get(suit, '0'),
                    'confidence': pos_result.get('confidence', 0.0)
                }
        
        return {
            'success': result.get('success', False),
            'camera_id': result.get('camera_id', ''),
            'timestamp': result.get('timestamp', ''),
            'positions': db_positions,
            'summary': result.get('summary', {}),
            'total_duration': result.get('total_duration', 0),
            'quality': result.get('quality', {}) if self.config['include_quality_metrics'] else {}
        }
    
    def _create_image_mapping(self, main_files: List[str], left_files: List[str]) -> Dict[str, str]:
        """创建主图片和左上角图片的对应关系"""
        mapping = {}
        
        for main_file in main_files:
            main_stem = Path(main_file).stem  # camera_001_zhuang_1
            
            # 查找对应的左上角图片
            for left_file in left_files:
                left_stem = Path(left_file).stem  # camera_001_zhuang_1_left
                if left_stem.startswith(main_stem):
                    mapping[main_file] = left_file
                    break
        
        return mapping
    
    def _extract_position_from_filename(self, filename: str) -> str:
        """从文件名提取位置信息"""
        try:
            # 文件名格式: camera_001_zhuang_1.png
            parts = filename.split('_')
            if len(parts) >= 4:
                return f"{parts[2]}_{parts[3].split('.')[0]}"
            return "unknown"
        except:
            return "unknown"
    
    def _format_error_result(self, camera_id: str, error_message: str, error_code: str) -> Dict[str, Any]:
        """格式化错误结果"""
        return {
            'success': False,
            'camera_id': camera_id,
            'timestamp': datetime.now().isoformat(),
            'error': error_message,
            'error_code': error_code,
            'positions': {pos: {
                'success': False,
                'suit': '',
                'rank': '',
                'confidence': 0.0,
                'error': error_message
            } for pos in self.standard_positions},
            'summary': {
                'total_positions': len(self.standard_positions),
                'successful_positions': 0,
                'failed_positions': len(self.standard_positions),
                'success_rate': 0.0,
                'recognized_cards': []
            }
        }
    
    def get_recognition_capabilities(self) -> Dict[str, Any]:
        """获取识别能力信息"""
        capabilities = {
            'config': self.config,
            'standard_positions': self.standard_positions,
            'available_output_formats': ['standard', 'simple', 'database']
        }
        
        if hasattr(self, 'hybrid_recognizer'):
            capabilities.update(self.hybrid_recognizer.get_recognition_capabilities())
        
        return capabilities


# 创建全局统一识别器实例
unified_recognizer = UnifiedPokerRecognizer()

# 导出主要接口函数
def recognize_camera_complete(camera_id: str, image_path: str = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    识别摄像头完整结果 - 主要接口
    
    Args:
        camera_id: 摄像头ID
        image_path: 图片路径（可选，如果不提供则自动拍照）
        config: 自定义配置（可选）
        
    Returns:
        完整的识别结果
    """
    if config:
        # 使用自定义配置创建临时识别器
        temp_recognizer = UnifiedPokerRecognizer(config)
        return temp_recognizer.recognize_camera_all_positions(camera_id, image_path)
    else:
        # 使用全局识别器
        return unified_recognizer.recognize_camera_all_positions(camera_id, image_path)

def recognize_camera_simple(camera_id: str, image_path: str = None) -> Dict[str, Any]:
    """识别摄像头结果 - 简化版"""
    config = {'output_format': 'simple', 'enable_result_merging': False}
    return recognize_camera_complete(camera_id, image_path, config)

def recognize_camera_database(camera_id: str, image_path: str = None) -> Dict[str, Any]:
    """识别摄像头结果 - 数据库版"""
    config = {'output_format': 'database', 'enable_result_merging': True}
    return recognize_camera_complete(camera_id, image_path, config)

def get_unified_recognition_capabilities() -> Dict[str, Any]:
    """获取统一识别器能力"""
    return unified_recognizer.get_recognition_capabilities()

if __name__ == "__main__":
    # 测试统一识别器
    print("🧪 测试统一扑克识别器")
    print("=" * 60)
    
    # 显示识别能力
    capabilities = get_unified_recognition_capabilities()
    print("🔍 识别能力:")
    for method, available in capabilities.get('available_methods', {}).items():
        status = "✅ 可用" if available else "❌ 不可用"
        print(f"   {method}: {status}")
    
    # 测试识别（需要根据实际情况调整摄像头ID）
    test_camera_id = "001"
    
    print(f"\n🎯 测试摄像头 {test_camera_id} 识别")
    print("-" * 40)
    
    # 测试完整识别
    result = recognize_camera_complete(test_camera_id)
    
    if result['success']:
        print("✅ 统一识别成功!")
        print(f"   成功率: {result['summary']['success_rate']:.1f}%")
        print(f"   成功位置: {result['summary']['successful_positions']}/{result['summary']['total_positions']}")
        print(f"   识别卡牌: {', '.join(result['summary']['recognized_cards'])}")
        print(f"   总耗时: {result.get('total_duration', 0):.2f}秒")
        
        if 'quality' in result:
            print(f"   质量等级: {result['quality'].get('quality_level', 'N/A')}")
    else:
        print("❌ 统一识别失败!")
        print(f"   错误: {result.get('error', '未知错误')}")
    
    # 测试简化识别
    print(f"\n🎯 测试简化识别")
    print("-" * 40)
    
    simple_result = recognize_camera_simple(test_camera_id)
    print(f"简化结果: {simple_result.get('positions', {})}")
    
    print("\n✅ 统一识别器测试完成")