#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时识别推送系统 - tui.py (新版本)
业务逻辑:
1. 读取摄像头配置
2. 轮询拍照
3. 轮询裁剪
4. 轮询识别 (使用YOLO识别器)
5. 轮询推送
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

class TuiSystem:
    """实时识别推送系统"""
    
    def __init__(self):
        """初始化系统"""
        self.shutdown_requested = False
        
        # 系统配置
        self.config = {
            'recognition_interval': 3,  # 每轮循环间隔(秒)
            'camera_switch_delay': 1,   # 摄像头切换延迟(秒)
            'max_retry_times': 3,       # 最大重试次数
            'retry_delay': 2,           # 重试延迟(秒)
            'enable_websocket': True,   # 启用WebSocket推送
            'save_recognition_results': True,  # 保存识别结果
        }
        
        # 摄像头配置
        self.enabled_cameras = []
        self.current_camera_index = 0
        
        # WebSocket客户端
        self.websocket_client = None
        self.websocket_connected = False
        
        # 统计信息
        self.stats = {
            'start_time': datetime.now(),
            'total_cycles': 0,
            'camera_stats': {},  # 每个摄像头的统计
            'last_results': {},  # 最后一次识别结果
        }
        
        # 显示状态
        self.display_lock = threading.Lock()
        
        print("🚀 实时识别推送系统初始化完成")
    
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
                    'successful_photos': 0,
                    'successful_recognitions': 0,
                    'successful_pushes': 0,
                    'last_photo_time': None,
                    'last_recognition_time': None,
                    'last_push_time': None,
                    'last_result': None,
                }
                
                print(f"   {i+1}. {camera['name']} (ID: {camera_id}) - IP: {camera['ip']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 读取摄像头配置失败: {e}")
            return False
    
    def step2_take_photo(self, camera_id: str) -> Dict[str, Any]:
        """步骤2: 拍照"""
        try:
            # 导入拍照控制器
            from src.processors.photo_controller import take_photo_by_id
            
            start_time = time.time()
            result = take_photo_by_id(camera_id)
            duration = time.time() - start_time
            
            # 更新统计
            self.stats['camera_stats'][camera_id]['total_attempts'] += 1
            
            if result['status'] == 'success':
                self.stats['camera_stats'][camera_id]['successful_photos'] += 1
                self.stats['camera_stats'][camera_id]['last_photo_time'] = datetime.now().strftime('%H:%M:%S')
                
                return {
                    'success': True,
                    'file_path': result['data']['file_path'],
                    'filename': result['data']['filename'],
                    'file_size': result['data']['file_size'],
                    'duration': duration
                }
            else:
                return {
                    'success': False,
                    'error': result['message'],
                    'duration': duration
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': 0
            }
    
    def step3_crop_images(self, image_path: str) -> Dict[str, Any]:
        """步骤3: 裁剪图片"""
        try:
            from src.processors.image_cutter import process_image
            
            start_time = time.time()
            success = process_image(image_path)
            duration = time.time() - start_time
            
            if success:
                # 查找裁剪后的图片
                image_file = Path(image_path)
                cut_dir = image_file.parent / "cut"
                
                if cut_dir.exists():
                    pattern = f"{image_file.stem}_*.png"
                    cropped_files = list(cut_dir.glob(pattern))
                    # 过滤掉左上角图片，只要主图片
                    main_files = [f for f in cropped_files if not f.name.endswith('_left.png')]
                    main_files.sort(key=lambda x: x.name)
                    
                    return {
                        'success': True,
                        'cropped_files': [str(f) for f in main_files],
                        'count': len(main_files),
                        'duration': duration
                    }
                else:
                    return {
                        'success': False,
                        'error': '裁剪目录不存在',
                        'duration': duration
                    }
            else:
                return {
                    'success': False,
                    'error': '图片裁剪失败',
                    'duration': duration
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': 0
            }
    
    def step4_recognize_images(self, camera_id: str, cropped_files: List[str]) -> Dict[str, Any]:
        """步骤4: 识别扑克牌"""
        try:
            recognition_results = {}
            successful_count = 0
            total_count = len(cropped_files)
            
            start_time = time.time()
            
            for image_path in cropped_files:
                position = self._extract_position_from_filename(Path(image_path).name)
                result = self._recognize_single_image(image_path)
                
                if result['success']:
                    successful_count += 1
                
                recognition_results[position] = result
            
            duration = time.time() - start_time
            
            # 更新统计
            if successful_count > 0:
                self.stats['camera_stats'][camera_id]['successful_recognitions'] += 1
                self.stats['camera_stats'][camera_id]['last_recognition_time'] = datetime.now().strftime('%H:%M:%S')
            
            # 格式化结果
            formatted_results = self._format_recognition_results(camera_id, recognition_results)
            
            return {
                'success': successful_count > 0,
                'results': recognition_results,
                'formatted_results': formatted_results,
                'successful_count': successful_count,
                'total_count': total_count,
                'success_rate': (successful_count / total_count * 100) if total_count > 0 else 0,
                'duration': duration
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': 0
            }
    
    def step5_push_results(self, camera_id: str, formatted_results: Dict[str, Any]) -> Dict[str, Any]:
        """步骤5: 推送识别结果"""
        try:
            if not self.config['enable_websocket']:
                return {'success': True, 'message': 'WebSocket推送已禁用', 'duration': 0}
            
            start_time = time.time()
            
            # 尝试推送到识别结果管理器
            push_result = self._push_to_recognition_manager(formatted_results)
            
            duration = time.time() - start_time
            
            # 更新统计
            if push_result['success']:
                self.stats['camera_stats'][camera_id]['successful_pushes'] += 1
                self.stats['camera_stats'][camera_id]['last_push_time'] = datetime.now().strftime('%H:%M:%S')
            
            return {
                'success': push_result['success'],
                'message': push_result['message'],
                'duration': duration
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': str(e),
                'duration': 0
            }
    
    def _recognize_single_image(self, image_path: str) -> Dict[str, Any]:
        """识别单张图片 - 使用YOLO识别器"""
        try:
            # 使用YOLO识别器
            from src.processors.poker_recognizer import recognize_poker_card
            
            result = recognize_poker_card(image_path)
            
            if result['success']:
                return {
                    'success': True,
                    'suit': result.get('suit', ''),
                    'rank': result.get('rank', ''),
                    'display_name': result.get('display_name', ''),
                    'confidence': result.get('confidence', 0),
                    'method': 'yolo'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', '识别失败'),
                    'method': 'yolo'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'method': 'exception'
            }
    
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
    
    def _format_recognition_results(self, camera_id: str, recognition_results: Dict[str, Any]) -> Dict[str, Any]:
        """格式化识别结果用于推送"""
        positions = {}
        
        # 标准位置列表
        standard_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        for position in standard_positions:
            if position in recognition_results and recognition_results[position]['success']:
                result = recognition_results[position]
                positions[position] = {
                    'suit': result.get('suit', ''),
                    'rank': result.get('rank', ''),
                    'confidence': result.get('confidence', 0.0)
                }
            else:
                positions[position] = {
                    'suit': '',
                    'rank': '',
                    'confidence': 0.0
                }
        
        return {
            'camera_id': camera_id,
            'positions': positions,
            'timestamp': datetime.now().isoformat()
        }
    
    def _push_to_recognition_manager(self, formatted_results: Dict[str, Any]) -> Dict[str, Any]:
        """推送到识别结果管理器"""
        try:
            # 使用识别结果管理器
            from src.core.recognition_manager import receive_recognition_data
            
            result = receive_recognition_data(formatted_results)
            
            if result['status'] == 'success':
                return {'success': True, 'message': '推送成功'}
            else:
                return {'success': False, 'message': result.get('message', '推送失败')}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def run_main_loop(self):
        """运行主循环"""
        try:
            print(f"\n🔄 开始实时识别推送循环")
            print(f"   识别间隔: {self.config['recognition_interval']} 秒")
            print(f"   摄像头切换延迟: {self.config['camera_switch_delay']} 秒")
            print(f"   启用摄像头: {len(self.enabled_cameras)} 个")
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
            # 步骤2: 拍照
            photo_result = self.step2_take_photo(camera_id)
            
            if not photo_result['success']:
                self._display_step_result("拍照", False, photo_result['error'], photo_result['duration'])
                return False
            
            self._display_step_result("拍照", True, f"{photo_result['filename']} ({photo_result['file_size']/1024:.1f}KB)", photo_result['duration'])
            
            # 步骤3: 裁剪
            crop_result = self.step3_crop_images(photo_result['file_path'])
            
            if not crop_result['success']:
                self._display_step_result("裁剪", False, crop_result['error'], crop_result['duration'])
                return False
            
            self._display_step_result("裁剪", True, f"{crop_result['count']} 个区域", crop_result['duration'])
            
            # 步骤4: 识别
            recognition_result = self.step4_recognize_images(camera_id, crop_result['cropped_files'])
            
            if not recognition_result['success']:
                self._display_step_result("识别", False, recognition_result.get('error', '识别失败'), recognition_result['duration'])
                return False
            
            # 显示识别结果
            self._display_recognition_results(camera_id, recognition_result)
            
            # 保存最新结果
            self.stats['last_results'][camera_id] = recognition_result['formatted_results']
            
            # 步骤5: 推送
            push_result = self.step5_push_results(camera_id, recognition_result['formatted_results'])
            self._display_step_result("推送", push_result['success'], push_result['message'], push_result['duration'])
            
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
            print(f"      {status_icon} {step_name}: {message} ({duration:.2f}s)")
    
    def _display_recognition_results(self, camera_id: str, recognition_result: Dict[str, Any]):
        """显示识别结果"""
        with self.display_lock:
            success_count = recognition_result['successful_count']
            total_count = recognition_result['total_count']
            success_rate = recognition_result['success_rate']
            duration = recognition_result['duration']
            
            print(f"      ✅ 识别: {success_count}/{total_count} 成功 ({success_rate:.1f}%) ({duration:.2f}s)")
            
            # 显示具体识别结果
            results = recognition_result['results']
            position_names = {
                'zhuang_1': '庄1', 'zhuang_2': '庄2', 'zhuang_3': '庄3',
                'xian_1': '闲1', 'xian_2': '闲2', 'xian_3': '闲3'
            }
            
            recognized_cards = []
            for position, result in results.items():
                if result['success']:
                    pos_name = position_names.get(position, position)
                    display_name = result.get('display_name', 'N/A')
                    confidence = result.get('confidence', 0)
                    recognized_cards.append(f"{pos_name}:{display_name}({confidence:.2f})")
            
            if recognized_cards:
                cards_str = " | ".join(recognized_cards)
                print(f"         🎴 {cards_str}")
    
    def _display_cycle_summary(self, cycle_duration: float):
        """显示循环汇总"""
        with self.display_lock:
            print(f"\n📊 本轮汇总: 耗时 {cycle_duration:.2f}秒")
            
            # 显示各摄像头状态
            for camera_id, stats in self.stats['camera_stats'].items():
                camera_name = next((c['name'] for c in self.enabled_cameras if c['id'] == camera_id), camera_id)
                
                success_icon = "✅" if stats['successful_recognitions'] > 0 else "⚪"
                last_time = stats.get('last_recognition_time', '未知')
                
                print(f"   {success_icon} {camera_name}: 拍照{stats['successful_photos']}/{stats['total_attempts']} "
                      f"识别{stats['successful_recognitions']} 推送{stats['successful_pushes']} "
                      f"最后:{last_time}")
    
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
            
            print(f"\n📷 各摄像头统计:")
            for camera_id, stats in self.stats['camera_stats'].items():
                camera_name = next((c['name'] for c in self.enabled_cameras if c['id'] == camera_id), camera_id)
                
                photo_rate = (stats['successful_photos'] / stats['total_attempts'] * 100) if stats['total_attempts'] > 0 else 0
                
                print(f"   {camera_name} (ID: {camera_id}):")
                print(f"     拍照: {stats['successful_photos']}/{stats['total_attempts']} ({photo_rate:.1f}%)")
                print(f"     识别: {stats['successful_recognitions']} 次成功")
                print(f"     推送: {stats['successful_pushes']} 次成功")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ 显示统计信息失败: {e}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='实时识别推送系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python tui.py                    # 默认配置运行
  python tui.py --interval 5       # 设置循环间隔为5秒
  python tui.py --no-push          # 禁用推送功能
        """
    )
    
    parser.add_argument('--interval', type=int, default=3,
                       help='识别循环间隔(秒) (默认: 3)')
    parser.add_argument('--camera-delay', type=float, default=1.0,
                       help='摄像头切换延迟(秒) (默认: 1.0)')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='最大重试次数 (默认: 3)')
    parser.add_argument('--no-push', action='store_true',
                       help='禁用推送功能')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        args = parse_arguments()
        
        # 创建系统实例
        system = TuiSystem()
        
        # 更新配置
        system.config.update({
            'recognition_interval': args.interval,
            'camera_switch_delay': args.camera_delay,
            'max_retry_times': args.max_retries,
            'enable_websocket': not args.no_push,
        })
        
        # 步骤1: 读取摄像头配置
        if not system.step1_load_camera_config():
            return 1
        
        # 显示系统配置
        print(f"\n🚀 系统配置:")
        print(f"   循环间隔: {system.config['recognition_interval']} 秒")
        print(f"   切换延迟: {system.config['camera_switch_delay']} 秒")
        print(f"   最大重试: {system.config['max_retry_times']} 次")
        print(f"   推送功能: {'启用' if system.config['enable_websocket'] else '禁用'}")
        
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
        
        print("👋 实时识别推送系统已关闭")
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())