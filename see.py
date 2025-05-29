#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克识别测试系统 - see.py (统一识别器版本)
业务逻辑:
1. 读取摄像头配置
2. 轮询拍照和识别 (使用统一识别器)
3. 保存识别结果
4. 显示实时统计
"""

import sys
import time
import json
import signal
import argparse
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 路径设置
def setup_project_paths():
    """设置项目路径"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent
    
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

PROJECT_ROOT = setup_project_paths()

class UnifiedSeeSystem:
    """基于统一识别器的测试系统"""
    
    def __init__(self):
        """初始化系统"""
        self.shutdown_requested = False
        
        # 系统配置
        self.config = {
            'recognition_interval': 3,  # 识别间隔(秒)
            'camera_switch_delay': 1,   # 摄像头切换延迟(秒)
            'max_retry_times': 2,       # 最大重试次数
            'save_results': True,       # 保存识别结果
            'show_detailed_results': True,  # 显示详细结果
            'show_quality_info': True,  # 显示质量信息
        }
        
        # 统一识别器配置
        self.recognition_config = {
            # 输出格式
            'output_format': 'standard',  # standard, simple, database
            
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
            'fusion_strategy': 'weighted',  # weighted, voting, priority
            'min_confidence_for_result': 0.3,
            'enable_result_validation': True,
            
            # 结果整合
            'enable_result_merging': True,
            'quality_assessment_enabled': True,
            'duplicate_detection_enabled': True,
            'include_quality_metrics': True,
            'include_debug_info': False,
        }
        
        # 摄像头配置
        self.enabled_cameras = []
        self.current_camera_index = 0
        
        # 统计信息
        self.stats = {
            'start_time': datetime.now(),
            'total_cycles': 0,
            'camera_stats': {},
            'last_results': {},
            'recognition_method_stats': {
                'yolo_complete': 0,
                'hybrid_combined': 0,
                'single_method': 0,
                'failed': 0
            },
            'quality_stats': {
                'excellent': 0,
                'good': 0,
                'average': 0,
                'poor': 0,
                'very_poor': 0
            },
            'performance_stats': {
                'total_recognition_time': 0.0,
                'average_recognition_time': 0.0,
                'fastest_recognition': float('inf'),
                'slowest_recognition': 0.0
            }
        }
        
        # 结果保存目录
        self.result_dir = PROJECT_ROOT / "result" / "see_results"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        
        # 显示控制
        self.display_lock = threading.Lock()
        
        print("🚀 统一识别器版测试系统初始化完成")
    
    def step1_load_camera_config(self) -> bool:
        """步骤1: 读取摄像头配置"""
        try:
            print("\n📷 步骤1: 读取摄像头配置")
            print("-" * 50)
            
            # 使用配置管理器
            from src.core.config_manager import get_all_cameras
            
            result = get_all_cameras()
            if result['status'] != 'success':
                print(f"❌ 获取摄像头配置失败: {result['message']}")
                return False
            
            cameras = result['data']['cameras']
            if not cameras:
                print("❌ 没有找到摄像头配置")
                return False
            
            # 过滤启用的摄像头
            self.enabled_cameras = [c for c in cameras if c.get('enabled', True)]
            if not self.enabled_cameras:
                print("❌ 没有找到启用的摄像头")
                return False
            
            print(f"✅ 找到 {len(self.enabled_cameras)} 个启用的摄像头:")
            for i, camera in enumerate(self.enabled_cameras):
                camera_id = camera['id']
                
                # 初始化摄像头统计
                self.stats['camera_stats'][camera_id] = {
                    'total_attempts': 0,
                    'successful_recognitions': 0,
                    'failed_recognitions': 0,
                    'last_recognition_time': None,
                    'last_result': None,
                    'average_duration': 0.0,
                    'total_duration': 0.0,
                    'best_quality_score': 0.0,
                    'recognition_method_counts': {
                        'yolo_complete': 0,
                        'hybrid_combined': 0,
                        'single_method': 0
                    },
                    'quality_history': []
                }
                
                print(f"   {i+1}. {camera['name']} (ID: {camera_id}) - IP: {camera['ip']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 读取摄像头配置失败: {e}")
            return False
    
    def step2_recognize_camera_unified(self, camera_id: str) -> Dict[str, Any]:
        """步骤2: 使用统一识别器识别摄像头"""
        try:
            print(f"   🧠 使用统一识别器识别...")
            
            # 导入统一识别器
            from src.processors.poker_hybrid_recognizer import recognize_camera_complete
            
            # 记录开始时间
            start_time = time.time()
            
            # 使用统一识别器 - 一行代码完成所有工作
            result = recognize_camera_complete(
                camera_id=camera_id,
                image_path=None,  # 自动拍照
                config=self.recognition_config
            )
            
            # 计算耗时
            duration = time.time() - start_time
            result['actual_duration'] = duration
            
            # 更新统计信息
            self._update_camera_stats(camera_id, result, duration)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'camera_id': camera_id,
                'error': str(e),
                'error_code': 'UNIFIED_RECOGNITION_ERROR',
                'actual_duration': 0.0
            }
    
    def step3_save_recognition_result(self, camera_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """步骤3: 保存识别结果"""
        try:
            if not self.config['save_results']:
                return {'success': True, 'message': '结果保存已禁用'}
            
            print(f"   💾 保存识别结果...")
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"recognition_{camera_id}_{timestamp}.json"
            file_path = self.result_dir / filename
            
            # 保存结果
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # 保存最新结果
            self.stats['last_results'][camera_id] = result
            
            print(f"   ✅ 结果已保存: {filename}")
            
            return {
                'success': True,
                'file_path': str(file_path),
                'filename': filename
            }
            
        except Exception as e:
            print(f"   ❌ 保存结果失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _update_camera_stats(self, camera_id: str, result: Dict[str, Any], duration: float):
        """更新摄像头统计信息"""
        try:
            stats = self.stats['camera_stats'][camera_id]
            
            # 基本统计
            stats['total_attempts'] += 1
            stats['total_duration'] += duration
            stats['average_duration'] = stats['total_duration'] / stats['total_attempts']
            
            if result['success']:
                stats['successful_recognitions'] += 1
                stats['last_recognition_time'] = datetime.now().strftime('%H:%M:%S')
                stats['last_result'] = result
                
                # 更新识别方法统计
                self._update_recognition_method_stats(camera_id, result)
                
                # 更新质量统计
                if 'quality' in result:
                    self._update_quality_stats(camera_id, result['quality'])
                
                # 更新全局识别方法统计
                self._update_global_method_stats(result)
                
            else:
                stats['failed_recognitions'] += 1
                self.stats['recognition_method_stats']['failed'] += 1
            
            # 更新性能统计
            perf_stats = self.stats['performance_stats']
            perf_stats['total_recognition_time'] += duration
            perf_stats['fastest_recognition'] = min(perf_stats['fastest_recognition'], duration)
            perf_stats['slowest_recognition'] = max(perf_stats['slowest_recognition'], duration)
            
            total_recognitions = sum(self.stats['recognition_method_stats'].values())
            if total_recognitions > 0:
                perf_stats['average_recognition_time'] = perf_stats['total_recognition_time'] / total_recognitions
                
        except Exception as e:
            print(f"⚠️  更新统计信息失败: {e}")
    
    def _update_recognition_method_stats(self, camera_id: str, result: Dict[str, Any]):
        """更新识别方法统计"""
        try:
            camera_stats = self.stats['camera_stats'][camera_id]
            
            # 检查是否使用了结果合并
            if result.get('merge_enabled', False):
                # 检查质量信息判断方法类型
                summary = result.get('summary', {})
                successful_positions = summary.get('successful_positions', 0)
                
                if successful_positions >= 4:  # 大部分位置识别成功，可能是YOLO主导
                    camera_stats['recognition_method_counts']['yolo_complete'] += 1
                else:  # 部分成功，可能是混合方法
                    camera_stats['recognition_method_counts']['hybrid_combined'] += 1
            else:
                # 简单模式
                camera_stats['recognition_method_counts']['single_method'] += 1
                
        except Exception:
            pass  # 忽略统计错误
    
    def _update_quality_stats(self, camera_id: str, quality_info: Dict[str, Any]):
        """更新质量统计"""
        try:
            camera_stats = self.stats['camera_stats'][camera_id]
            quality_score = quality_info.get('quality_score', 0.0)
            quality_level = quality_info.get('quality_level', '').lower()
            
            # 更新摄像头最佳质量
            camera_stats['best_quality_score'] = max(camera_stats['best_quality_score'], quality_score)
            
            # 更新质量历史
            camera_stats['quality_history'].append(quality_score)
            if len(camera_stats['quality_history']) > 10:
                camera_stats['quality_history'] = camera_stats['quality_history'][-10:]
            
            # 更新全局质量统计
            quality_mapping = {
                '优秀': 'excellent',
                '良好': 'good',
                '一般': 'average',
                '较差': 'poor',
                '很差': 'very_poor'
            }
            
            for chinese, english in quality_mapping.items():
                if chinese in quality_level:
                    self.stats['quality_stats'][english] += 1
                    break
                    
        except Exception:
            pass  # 忽略统计错误
    
    def _update_global_method_stats(self, result: Dict[str, Any]):
        """更新全局方法统计"""
        try:
            if result.get('merge_enabled', False):
                summary = result.get('summary', {})
                successful_positions = summary.get('successful_positions', 0)
                
                if successful_positions >= 4:
                    self.stats['recognition_method_stats']['yolo_complete'] += 1
                else:
                    self.stats['recognition_method_stats']['hybrid_combined'] += 1
            else:
                self.stats['recognition_method_stats']['single_method'] += 1
                
        except Exception:
            pass  # 忽略统计错误
    
    def run_main_loop(self):
        """运行主循环"""
        try:
            print(f"\n🔄 开始统一识别器测试循环")
            print(f"   识别间隔: {self.config['recognition_interval']} 秒")
            print(f"   切换延迟: {self.config['camera_switch_delay']} 秒")
            print(f"   启用摄像头: {len(self.enabled_cameras)} 个")
            print(f"   融合策略: {self.recognition_config['fusion_strategy']}")
            print(f"   结果合并: {'启用' if self.recognition_config['enable_result_merging'] else '禁用'}")
            print(f"   保存结果: {'启用' if self.config['save_results'] else '禁用'}")
            print("=" * 60)
            
            while not self.shutdown_requested:
                cycle_start_time = time.time()
                self.stats['total_cycles'] += 1
                
                # 显示循环信息
                self._display_cycle_header()
                
                # 轮询处理每个摄像头
                for i, camera in enumerate(self.enabled_cameras):
                    if self.shutdown_requested:
                        break
                    
                    camera_id = camera['id']
                    camera_name = camera.get('name', f'摄像头{camera_id}')
                    
                    # 显示当前处理的摄像头
                    self._display_camera_processing(i + 1, len(self.enabled_cameras), camera_name, camera_id)
                    
                    # 执行完整流程
                    success = self._process_single_camera_workflow(camera_id)
                    
                    # 摄像头切换延迟
                    if i < len(self.enabled_cameras) - 1 and not self.shutdown_requested:
                        time.sleep(self.config['camera_switch_delay'])
                
                # 显示本轮统计
                cycle_duration = time.time() - cycle_start_time
                self._display_cycle_summary(cycle_duration)
                
                # 循环间隔
                remaining_time = max(0, self.config['recognition_interval'] - cycle_duration)
                if remaining_time > 0 and not self.shutdown_requested:
                    self._display_waiting(remaining_time)
                    time.sleep(remaining_time)
                    
        except KeyboardInterrupt:
            print("\n⏹️  接收到停止信号")
            self.shutdown_requested = True
        except Exception as e:
            print(f"\n❌ 主循环异常: {e}")
            self.shutdown_requested = True
    
    def _process_single_camera_workflow(self, camera_id: str) -> bool:
        """处理单个摄像头的完整工作流程"""
        workflow_start_time = time.time()
        
        try:
            # 使用统一识别器进行识别
            recognition_result = self.step2_recognize_camera_unified(camera_id)
            
            if not recognition_result['success']:
                self._display_step_result("统一识别", False, 
                                        recognition_result.get('error', '识别失败'), 
                                        recognition_result.get('actual_duration', 0))
                return False
            
            # 显示识别结果
            self._display_recognition_results(camera_id, recognition_result)
            
            # 保存结果
            save_result = self.step3_save_recognition_result(camera_id, recognition_result)
            self._display_step_result("保存结果", save_result['success'], 
                                    save_result.get('filename', save_result.get('message', '')), 0)
            
            # 显示总耗时
            total_duration = time.time() - workflow_start_time
            print(f"      💫 总耗时: {total_duration:.2f}秒")
            
            return True
            
        except Exception as e:
            print(f"      ❌ 工作流程异常: {e}")
            return False
    
    def _display_cycle_header(self):
        """显示循环头部信息"""
        with self.display_lock:
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"\n🔄 第 {self.stats['total_cycles']} 轮循环 ({current_time})")
            print("=" * 60)
    
    def _display_camera_processing(self, current: int, total: int, camera_name: str, camera_id: str):
        """显示当前处理的摄像头"""
        with self.display_lock:
            print(f"\n📷 ({current}/{total}) {camera_name} (ID: {camera_id})")
            print("-" * 40)
    
    def _display_step_result(self, step_name: str, success: bool, message: str, duration: float):
        """显示步骤结果"""
        with self.display_lock:
            status_icon = "✅" if success else "❌"
            if duration > 0:
                print(f"      {status_icon} {step_name}: {message} ({duration:.2f}s)")
            else:
                print(f"      {status_icon} {step_name}: {message}")
    
    def _display_recognition_results(self, camera_id: str, result: Dict[str, Any]):
        """显示识别结果"""
        with self.display_lock:
            summary = result.get('summary', {})
            success_count = summary.get('successful_positions', 0)
            total_count = summary.get('total_positions', 6)
            success_rate = summary.get('success_rate', 0)
            duration = result.get('total_duration', 0)
            
            print(f"      ✅ 统一识别: {success_count}/{total_count} 成功 ({success_rate:.1f}%) ({duration:.2f}s)")
            
            # 显示识别到的卡牌
            recognized_cards = summary.get('recognized_cards', [])
            if recognized_cards:
                cards_str = " | ".join(recognized_cards)
                print(f"         🎴 识别结果: {cards_str}")
            
            # 显示质量信息
            if self.config['show_quality_info'] and 'quality' in result:
                quality = result['quality']
                quality_level = quality.get('quality_level', 'N/A')
                quality_score = quality.get('quality_score', 0)
                print(f"         🏆 质量: {quality_level} ({quality_score:.3f})")
            
            # 显示详细结果
            if self.config['show_detailed_results']:
                self._display_detailed_positions(result.get('positions', {}))
            
            # 显示警告
            warnings = result.get('warnings', [])
            if warnings:
                print(f"         ⚠️  警告: {'; '.join(warnings)}")
    
    def _display_detailed_positions(self, positions: Dict[str, Any]):
        """显示详细位置结果"""
        with self.display_lock:
            position_names = {
                'zhuang_1': '庄1', 'zhuang_2': '庄2', 'zhuang_3': '庄3',
                'xian_1': '闲1', 'xian_2': '闲2', 'xian_3': '闲3'
            }
            
            details = []
            for position in ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']:
                pos_result = positions.get(position, {})
                pos_name = position_names.get(position, position)
                
                if pos_result.get('success', False):
                    display_name = pos_result.get('display_name', 'N/A')
                    confidence = pos_result.get('confidence', 0)
                    method = pos_result.get('method', 'unknown')
                    
                    # 简化方法显示
                    method_short = 'Y' if method == 'yolo' else ('H' if 'hybrid' in method else 'O')
                    
                    details.append(f"{pos_name}:{display_name}({confidence:.2f})[{method_short}]")
                else:
                    details.append(f"{pos_name}:-- ")
            
            if details:
                details_str = " | ".join(details)
                print(f"         📋 详细: {details_str}")
    
    def _display_cycle_summary(self, cycle_duration: float):
        """显示循环汇总"""
        with self.display_lock:
            print(f"\n📊 本轮汇总: 耗时 {cycle_duration:.2f}秒")
            
            # 显示全局识别方法统计
            method_stats = self.stats['recognition_method_stats']
            total_recognitions = sum(method_stats.values())
            if total_recognitions > 0:
                yolo_pct = (method_stats['yolo_complete'] / total_recognitions) * 100
                hybrid_pct = (method_stats['hybrid_combined'] / total_recognitions) * 100
                single_pct = (method_stats['single_method'] / total_recognitions) * 100
                failed_pct = (method_stats['failed'] / total_recognitions) * 100
                
                print(f"   🧠 识别方法: YOLO完整{method_stats['yolo_complete']}({yolo_pct:.0f}%) "
                      f"混合{method_stats['hybrid_combined']}({hybrid_pct:.0f}%) "
                      f"单一{method_stats['single_method']}({single_pct:.0f}%) "
                      f"失败{method_stats['failed']}({failed_pct:.0f}%)")
            
            # 显示性能统计
            perf_stats = self.stats['performance_stats']
            if perf_stats['average_recognition_time'] > 0:
                print(f"   ⚡ 性能: 平均{perf_stats['average_recognition_time']:.2f}s "
                      f"最快{perf_stats['fastest_recognition']:.2f}s "
                      f"最慢{perf_stats['slowest_recognition']:.2f}s")
            
            # 显示各摄像头状态
            for camera_id, stats in self.stats['camera_stats'].items():
                camera_name = next((c['name'] for c in self.enabled_cameras if c['id'] == camera_id), camera_id)
                
                success_rate = (stats['successful_recognitions'] / stats['total_attempts'] * 100) if stats['total_attempts'] > 0 else 0
                last_time = stats.get('last_recognition_time', '未知')
                avg_duration = stats.get('average_duration', 0)
                best_quality = stats.get('best_quality_score', 0)
                
                # 方法统计
                method_counts = stats['recognition_method_counts']
                method_str = f"Y{method_counts['yolo_complete']}H{method_counts['hybrid_combined']}S{method_counts['single_method']}"
                
                status_icon = "✅" if stats['successful_recognitions'] > 0 else "⚪"
                
                print(f"   {status_icon} {camera_name}: 成功{stats['successful_recognitions']}/{stats['total_attempts']} "
                      f"({success_rate:.0f}%) 平均{avg_duration:.2f}s 质量{best_quality:.2f} "
                      f"方法[{method_str}] 最后:{last_time}")
    
    def _display_waiting(self, wait_time: float):
        """显示等待信息"""
        with self.display_lock:
            print(f"⏳ 等待 {wait_time:.1f}秒 后开始下轮循环...")
    
    def display_final_statistics(self):
        """显示最终统计"""
        try:
            print("\n📈 最终运行统计")
            print("=" * 50)
            
            # 计算运行时间
            total_time = datetime.now() - self.stats['start_time']
            print(f"⏰ 总运行时间: {str(total_time).split('.')[0]}")
            print(f"🔄 总循环数: {self.stats['total_cycles']}")
            
            # 显示识别方法统计
            method_stats = self.stats['recognition_method_stats']
            total_recognitions = sum(method_stats.values())
            if total_recognitions > 0:
                print(f"\n🧠 识别方法统计 (总计: {total_recognitions} 次):")
                method_names = {
                    'yolo_complete': 'YOLO完整识别',
                    'hybrid_combined': '混合组合识别',
                    'single_method': '单一方法识别',
                    'failed': '识别失败'
                }
                for method, count in method_stats.items():
                    if count > 0:
                        percentage = (count / total_recognitions) * 100
                        method_name = method_names.get(method, method)
                        print(f"  {method_name}: {count} 次 ({percentage:.1f}%)")
            
            # 显示质量统计
            quality_stats = self.stats['quality_stats']
            total_quality = sum(quality_stats.values())
            if total_quality > 0:
                print(f"\n🏆 质量等级统计 (总计: {total_quality} 次):")
                quality_names = {
                    'excellent': '优秀',
                    'good': '良好',
                    'average': '一般',
                    'poor': '较差',
                    'very_poor': '很差'
                }
                for level, count in quality_stats.items():
                    if count > 0:
                        percentage = (count / total_quality) * 100
                        level_name = quality_names.get(level, level)
                        print(f"  {level_name}: {count} 次 ({percentage:.1f}%)")
            
            # 显示性能统计
            perf_stats = self.stats['performance_stats']
            if perf_stats['total_recognition_time'] > 0:
                print(f"\n⚡ 性能统计:")
                print(f"  总识别时间: {perf_stats['total_recognition_time']:.2f}秒")
                print(f"  平均识别时间: {perf_stats['average_recognition_time']:.2f}秒")
                print(f"  最快识别: {perf_stats['fastest_recognition']:.2f}秒")
                print(f"  最慢识别: {perf_stats['slowest_recognition']:.2f}秒")
            
            # 显示各摄像头详细统计
            print(f"\n📷 各摄像头详细统计:")
            for camera_id, stats in self.stats['camera_stats'].items():
                camera_name = next((c['name'] for c in self.enabled_cameras if c['id'] == camera_id), camera_id)
                
                success_rate = (stats['successful_recognitions'] / stats['total_attempts'] * 100) if stats['total_attempts'] > 0 else 0
                
                print(f"   {camera_name} (ID: {camera_id}):")
                print(f"     总尝试: {stats['total_attempts']} 次")
                print(f"     成功识别: {stats['successful_recognitions']} 次 ({success_rate:.1f}%)")
                print(f"     失败识别: {stats['failed_recognitions']} 次")
                print(f"     平均耗时: {stats['average_duration']:.2f}秒")
                print(f"     最佳质量: {stats['best_quality_score']:.3f}")
                
                # 方法分布
                method_counts = stats['recognition_method_counts']
                method_items = [f"{k}:{v}" for k, v in method_counts.items() if v > 0]
                if method_items:
                    print(f"     方法分布: {', '.join(method_items)}")
                
                # 质量历史
                if stats['quality_history']:
                    avg_quality = sum(stats['quality_history']) / len(stats['quality_history'])
                    print(f"     平均质量: {avg_quality:.3f} (最近{len(stats['quality_history'])}次)")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ 显示统计信息失败: {e}")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='统一识别器版测试系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python see.py                           # 默认配置运行
  python see.py --interval 5              # 设置循环间隔为5秒
  python see.py --no-save                 # 禁用结果保存
  python see.py --strategy voting         # 使用投票融合策略
  python see.py --no-merge                # 禁用结果合并
  python see.py --simple                  # 使用简化输出格式
  python see.py --no-yolo                 # 禁用YOLO识别
  python see.py --no-details              # 不显示详细结果
        """
    )
    
    parser.add_argument('--interval', type=int, default=3,
                       help='识别循环间隔(秒) (默认: 3)')
    parser.add_argument('--camera-delay', type=float, default=1.0,
                       help='摄像头切换延迟(秒) (默认: 1.0)')
    parser.add_argument('--max-retries', type=int, default=2,
                       help='最大重试次数 (默认: 2)')
    parser.add_argument('--no-save', action='store_true',
                       help='禁用结果保存')
    parser.add_argument('--no-merge', action='store_true',
                       help='禁用结果合并')
    parser.add_argument('--strategy', choices=['weighted', 'voting', 'priority'], 
                       default='weighted', help='融合策略 (默认: weighted)')
    parser.add_argument('--simple', action='store_true',
                       help='使用简化输出格式')
    parser.add_argument('--no-yolo', action='store_true',
                       help='禁用YOLO识别')
    parser.add_argument('--no-ocr', action='store_true',
                       help='禁用OCR识别')
    parser.add_argument('--no-opencv', action='store_true',
                       help='禁用OpenCV花色识别')
    parser.add_argument('--no-details', action='store_true',
                       help='不显示详细识别结果')
    parser.add_argument('--no-quality', action='store_true',
                       help='不显示质量信息')
    
    return parser.parse_args()


def main():
    """主函数"""
    try:
        args = parse_arguments()
        
        # 创建统一版系统实例
        system = UnifiedSeeSystem()
        
        # 更新系统配置
        system.config.update({
            'recognition_interval': args.interval,
            'camera_switch_delay': args.camera_delay,
            'max_retry_times': args.max_retries,
            'save_results': not args.no_save,
            'show_detailed_results': not args.no_details,
            'show_quality_info': not args.no_quality,
        })
        
        # 更新识别配置
        system.recognition_config.update({
            'output_format': 'simple' if args.simple else 'standard',
            'fusion_strategy': args.strategy,
            'enable_result_merging': not args.no_merge,
            'yolo_enabled': not args.no_yolo,
            'ocr_enabled': not args.no_ocr,
            'opencv_suit_enabled': not args.no_opencv,
            'include_quality_metrics': not args.no_quality,
        })
        
        # 步骤1: 读取摄像头配置
        if not system.step1_load_camera_config():
            return 1
        
        # 显示系统配置
        print(f"\n🚀 统一识别器版系统配置:")
        print(f"   循环间隔: {system.config['recognition_interval']} 秒")
        print(f"   切换延迟: {system.config['camera_switch_delay']} 秒")
        print(f"   最大重试: {system.config['max_retry_times']} 次")
        print(f"   保存结果: {'启用' if system.config['save_results'] else '禁用'}")
        print(f"   输出格式: {system.recognition_config['output_format']}")
        print(f"   结果合并: {'启用' if system.recognition_config['enable_result_merging'] else '禁用'}")
        print(f"   融合策略: {system.recognition_config['fusion_strategy']}")
        print(f"   YOLO识别: {'启用' if system.recognition_config['yolo_enabled'] else '禁用'}")
        print(f"   OCR识别: {'启用' if system.recognition_config['ocr_enabled'] else '禁用'}")
        print(f"   OpenCV识别: {'启用' if system.recognition_config['opencv_suit_enabled'] else '禁用'}")
        print(f"   显示详情: {'启用' if system.config['show_detailed_results'] else '禁用'}")
        print(f"   质量信息: {'启用' if system.config['show_quality_info'] else '禁用'}")
        
        # 设置信号处理
        def signal_handler(signum, frame):
            print(f"\n📡 接收到信号 {signum}，准备关闭系统...")
            system.shutdown_requested = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("\n🔄 按 Ctrl+C 停止系统")
        
        # 运行主循环
        system.run_main_loop()
        
        # 显示最终统计
        if system.stats['total_cycles'] > 0:
            system.display_final_statistics()
        
        print("👋 统一识别器版测试系统已关闭")
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())