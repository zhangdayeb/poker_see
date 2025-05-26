#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克牌识别处理模块 - 识别扑克牌花色和点数
功能:
1. 扑克牌图像预处理
2. 花色和点数识别
3. 置信度计算
4. 结果格式化和保存
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
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from src.core.utils import (
    get_image_dir, get_result_dir, safe_json_dump,
    format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)
from src.core.config_manager import get_camera_by_id

class PokerRecognizer:
    """扑克牌识别器"""
    
    def __init__(self):
        """初始化扑克识别器"""
        # 设置路径
        self.image_dir = get_image_dir()
        self.cut_dir = self.image_dir / "cut"
        self.result_dir = get_result_dir()
        
        # 确保目录存在
        self.cut_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        
        # 扑克牌映射
        self.suits = {
            '♠': 'spades',
            '♥': 'hearts', 
            '♦': 'diamonds',
            '♣': 'clubs'
        }
        
        self.ranks = {
            'A': 'ace', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
            '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten',
            'J': 'jack', 'Q': 'queen', 'K': 'king'
        }
        
        # 识别结果缓存
        self.recognition_cache = {}
        
        log_info("扑克识别器初始化完成", "POKER_RECOGNIZER")
    
    def recognize_camera(self, camera_id: str) -> Dict[str, Any]:
        """
        识别指定摄像头的扑克牌
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            识别结果
        """
        try:
            log_info(f"🎯 开始识别摄像头 {camera_id} 的扑克牌", "POKER_RECOGNIZER")
            
            # 获取摄像头配置
            camera_result = get_camera_by_id(camera_id)
            if camera_result['status'] != 'success':
                return format_error_response(f"摄像头 {camera_id} 配置不存在", "CAMERA_NOT_FOUND")
            
            camera_config = camera_result['data']['camera']
            
            # 检查裁剪图片是否存在
            cut_images = self._get_cut_images(camera_id)
            if not cut_images:
                return format_error_response(f"摄像头 {camera_id} 没有裁剪图片", "NO_CUT_IMAGES")
            
            # 识别每个位置的扑克牌
            recognition_results = {}
            total_positions = len(cut_images)
            recognized_count = 0
            
            for position, image_path in cut_images.items():
                result = self._recognize_single_card(image_path, position)
                recognition_results[position] = result
                
                if result['recognized']:
                    recognized_count += 1
                    log_success(f"  {position}: {result['suit']}{result['rank']} (置信度: {result['confidence']:.2f})", "POKER_RECOGNIZER")
                else:
                    log_warning(f"  {position}: 未识别", "POKER_RECOGNIZER")
            
            # 计算识别统计
            recognition_rate = (recognized_count / total_positions * 100) if total_positions > 0 else 0
            
            log_info(f"📊 识别完成: {recognized_count}/{total_positions} ({recognition_rate:.1f}%)", "POKER_RECOGNIZER")
            
            return format_success_response(
                f"摄像头 {camera_id} 识别完成",
                data={
                    'camera_id': camera_id,
                    'camera_name': camera_config.get('name', f'摄像头{camera_id}'),
                    'results': recognition_results,
                    'statistics': {
                        'total_positions': total_positions,
                        'recognized_count': recognized_count,
                        'recognition_rate': round(recognition_rate, 1)
                    },
                    'timestamp': get_timestamp()
                }
            )
            
        except Exception as e:
            log_error(f"识别摄像头 {camera_id} 扑克牌失败: {e}", "POKER_RECOGNIZER")
            return format_error_response(f"识别失败: {str(e)}", "RECOGNITION_ERROR")
    
    def _get_cut_images(self, camera_id: str) -> Dict[str, Path]:
        """获取摄像头的裁剪图片"""
        cut_images = {}
        positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        for position in positions:
            image_filename = f"camera_{camera_id}_{position}.png"
            image_path = self.cut_dir / image_filename
            
            if image_path.exists():
                cut_images[position] = image_path
        
        return cut_images
    
    def _recognize_single_card(self, image_path: Path, position: str) -> Dict[str, Any]:
        """
        识别单张扑克牌
        
        Args:
            image_path: 图片路径
            position: 位置名称
            
        Returns:
            识别结果
        """
        try:
            # 检查文件是否存在
            if not image_path.exists():
                return {
                    'suit': '',
                    'rank': '',
                    'confidence': 0.0,
                    'recognized': False,
                    'error': '图片文件不存在'
                }
            
            # 模拟识别过程（实际应用中这里会调用图像识别算法）
            result = self._simulate_card_recognition(image_path, position)
            
            return result
            
        except Exception as e:
            log_error(f"识别单张扑克牌失败 {image_path}: {e}", "POKER_RECOGNIZER")
            return {
                'suit': '',
                'rank': '',
                'confidence': 0.0,
                'recognized': False,
                'error': str(e)
            }
    
    def _simulate_card_recognition(self, image_path: Path, position: str) -> Dict[str, Any]:
        """
        模拟扑克牌识别（用于测试）
        
        Args:
            image_path: 图片路径
            position: 位置名称
            
        Returns:
            模拟识别结果
        """
        import random
        
        # 模拟识别延迟
        time.sleep(0.1)
        
        # 根据位置和随机因子决定是否识别成功
        position_weights = {
            'zhuang_1': 0.9,
            'zhuang_2': 0.8,
            'zhuang_3': 0.7,
            'xian_1': 0.85,
            'xian_2': 0.75,
            'xian_3': 0.65
        }
        
        success_probability = position_weights.get(position, 0.5)
        
        if random.random() < success_probability:
            # 模拟成功识别
            suits = ['♠', '♥', '♦', '♣']
            ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
            
            suit = random.choice(suits)
            rank = random.choice(ranks)
            confidence = random.uniform(0.7, 0.95)
            
            return {
                'suit': suit,
                'rank': rank,
                'confidence': round(confidence, 3),
                'recognized': True
            }
        else:
            # 模拟识别失败
            return {
                'suit': '',
                'rank': '',
                'confidence': 0.0,
                'recognized': False
            }
    
    def batch_recognize(self, camera_ids: List[str] = None) -> Dict[str, Any]:
        """
        批量识别多个摄像头
        
        Args:
            camera_ids: 摄像头ID列表，如果为None则识别所有可用的摄像头
            
        Returns:
            批量识别结果
        """
        try:
            if camera_ids is None:
                # 获取所有有裁剪图片的摄像头
                camera_ids = self._get_available_cameras()
            
            if not camera_ids:
                return format_error_response("没有可识别的摄像头", "NO_CAMERAS")
            
            log_info(f"📹 开始批量识别 {len(camera_ids)} 个摄像头", "POKER_RECOGNIZER")
            
            all_results = {}
            success_count = 0
            total_recognized = 0
            total_positions = 0
            
            for camera_id in camera_ids:
                result = self.recognize_camera(camera_id)
                all_results[camera_id] = result
                
                if result['status'] == 'success':
                    success_count += 1
                    stats = result['data']['statistics']
                    total_recognized += stats['recognized_count']
                    total_positions += stats['total_positions']
            
            # 计算整体识别率
            overall_rate = (total_recognized / total_positions * 100) if total_positions > 0 else 0
            
            log_info(f"📊 批量识别完成: {success_count}/{len(camera_ids)} 摄像头成功", "POKER_RECOGNIZER")
            log_info(f"🎯 整体识别: {total_recognized}/{total_positions} ({overall_rate:.1f}%)", "POKER_RECOGNIZER")
            
            return format_success_response(
                "批量识别完成",
                data={
                    'total_cameras': len(camera_ids),
                    'success_cameras': success_count,
                    'overall_statistics': {
                        'total_positions': total_positions,
                        'recognized_count': total_recognized,
                        'recognition_rate': round(overall_rate, 1)
                    },
                    'camera_results': all_results,
                    'timestamp': get_timestamp()
                }
            )
            
        except Exception as e:
            log_error(f"批量识别失败: {e}", "POKER_RECOGNIZER")
            return format_error_response(f"批量识别失败: {str(e)}", "BATCH_RECOGNITION_ERROR")
    
    def _get_available_cameras(self) -> List[str]:
        """获取有裁剪图片的摄像头ID列表"""
        available_cameras = []
        
        if not self.cut_dir.exists():
            return []
        
        # 查找所有裁剪图片文件
        cut_files = list(self.cut_dir.glob("camera_*_*.png"))
        
        # 提取摄像头ID
        camera_ids = set()
        for file_path in cut_files:
            parts = file_path.stem.split('_')
            if len(parts) >= 2 and parts[0] == 'camera':
                camera_ids.add(parts[1])
        
        return list(camera_ids)
    
    def generate_final_result(self, recognition_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成最终识别结果
        
        Args:
            recognition_results: 各摄像头的识别结果
            
        Returns:
            最终汇总结果
        """
        try:
            # 汇总所有识别结果
            all_positions = {}
            total_cameras = len(recognition_results)
            total_positions = 0
            total_recognized = 0
            
            for camera_id, result in recognition_results.items():
                if result['status'] == 'success':
                    camera_results = result['data']['results']
                    for position, position_result in camera_results.items():
                        # 使用摄像头ID作为前缀避免重复
                        position_key = f"{camera_id}_{position}"
                        all_positions[position_key] = position_result
                        
                        total_positions += 1
                        if position_result.get('recognized', False):
                            total_recognized += 1
            
            overall_rate = (total_recognized / total_positions * 100) if total_positions > 0 else 0
            
            final_result = {
                'total_cameras': total_cameras,
                'total_positions': total_positions,
                'recognized_count': total_recognized,
                'recognition_rate': round(overall_rate, 1),
                'all_positions': all_positions,
                'timestamp': get_timestamp(),
                'summary': self._generate_summary(all_positions)
            }
            
            return final_result
            
        except Exception as e:
            log_error(f"生成最终结果失败: {e}", "POKER_RECOGNIZER")
            return {
                'error': str(e),
                'timestamp': get_timestamp()
            }
    
    def _generate_summary(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """生成识别结果摘要"""
        summary = {
            'zhuang_cards': [],
            'xian_cards': [],
            'unrecognized': []
        }
        
        for position_key, result in positions.items():
            if result.get('recognized', False):
                card_info = {
                    'position': position_key,
                    'suit': result['suit'],
                    'rank': result['rank'],
                    'confidence': result['confidence']
                }
                
                if 'zhuang' in position_key:
                    summary['zhuang_cards'].append(card_info)
                elif 'xian' in position_key:
                    summary['xian_cards'].append(card_info)
            else:
                summary['unrecognized'].append(position_key)
        
        return summary
    
    def save_result_to_file(self, result: Dict[str, Any]) -> bool:
        """
        保存识别结果到文件
        
        Args:
            result: 识别结果
            
        Returns:
            保存是否成功
        """
        try:
            # 生成文件名
            timestamp = get_timestamp().replace(':', '-').replace('T', '_')
            filename = f"recognition_result_{timestamp}.json"
            file_path = self.result_dir / filename
            
            # 保存结果
            if safe_json_dump(result, file_path):
                log_success(f"识别结果保存成功: {filename}", "POKER_RECOGNIZER")
                return True
            else:
                log_error(f"识别结果保存失败: {filename}", "POKER_RECOGNIZER")
                return False
                
        except Exception as e:
            log_error(f"保存识别结果失败: {e}", "POKER_RECOGNIZER")
            return False
    
    def get_recognition_history(self, limit: int = 10) -> Dict[str, Any]:
        """
        获取识别历史记录
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            历史记录
        """
        try:
            if not self.result_dir.exists():
                return format_success_response("无历史记录", data={'history': []})
            
            # 获取所有结果文件
            result_files = list(self.result_dir.glob("recognition_result_*.json"))
            result_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            history = []
            for file_path in result_files[:limit]:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 提取关键信息
                    history_item = {
                        'filename': file_path.name,
                        'timestamp': data.get('timestamp', ''),
                        'total_cameras': data.get('total_cameras', 0),
                        'recognition_rate': data.get('recognition_rate', 0),
                        'file_size': file_path.stat().st_size
                    }
                    history.append(history_item)
                    
                except Exception as e:
                    log_warning(f"读取历史文件失败 {file_path}: {e}", "POKER_RECOGNIZER")
            
            return format_success_response(
                f"获取识别历史成功 ({len(history)} 条)",
                data={'history': history}
            )
            
        except Exception as e:
            log_error(f"获取识别历史失败: {e}", "POKER_RECOGNIZER")
            return format_error_response(f"获取历史失败: {str(e)}", "HISTORY_ERROR")


# 创建全局实例
poker_recognizer = PokerRecognizer()

# 导出主要函数
def recognize_camera(camera_id: str) -> Dict[str, Any]:
    """识别指定摄像头的扑克牌"""
    return poker_recognizer.recognize_camera(camera_id)

def batch_recognize(camera_ids: List[str] = None) -> Dict[str, Any]:
    """批量识别多个摄像头"""
    return poker_recognizer.batch_recognize(camera_ids)

def generate_final_result(recognition_results: Dict[str, Any]) -> Dict[str, Any]:
    """生成最终识别结果"""
    return poker_recognizer.generate_final_result(recognition_results)

def save_result_to_file(result: Dict[str, Any]) -> bool:
    """保存识别结果到文件"""
    return poker_recognizer.save_result_to_file(result)

def get_recognition_history(limit: int = 10) -> Dict[str, Any]:
    """获取识别历史记录"""
    return poker_recognizer.get_recognition_history(limit)

if __name__ == "__main__":
    # 测试扑克识别器
    print("🧪 测试扑克识别器")
    
    try:
        # 测试单个摄像头识别
        result = recognize_camera("001")
        print(f"单摄像头识别: {result}")
        
        # 测试批量识别
        batch_result = batch_recognize(["001", "002"])
        print(f"批量识别: {batch_result}")
        
        # 测试历史记录
        history = get_recognition_history(5)
        print(f"历史记录: {history}")
        
        print("✅ 扑克识别器测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()