#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时识别推送入口程序 - 生产环境实时识别和推送
功能:
1. 多摄像头循环识别
2. 实时结果推送 (WebSocket)
3. 智能调度和错误重试
4. 性能监控和状态报告
5. 7x24小时稳定运行
"""

import sys
import time
import signal
import argparse
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# 路径设置
def setup_project_paths():
    """设置项目路径"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent
    
    # 将项目根目录添加到Python路径
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

# 设置项目路径
PROJECT_ROOT = setup_project_paths()

# 导入系统模块
from config_loader import (
    load_camera_config, load_recognition_config, load_push_config,
    get_enabled_cameras, get_camera_by_id, validate_all_configs
)
from state_manager import (
    register_process, unregister_process, update_heartbeat,
    lock_camera, release_camera, check_camera_available, get_system_status
)

# 导入核心模块
from src.core.utils import (
    get_timestamp, ensure_dirs_exist, get_result_dir,
    log_info, log_success, log_error, log_warning
)

class TuiSystem:
    """实时识别推送系统"""
    
    def __init__(self):
        """初始化实时识别推送系统"""
        self.process_name = "tui"
        self.process_type = "production"
        self.shutdown_requested = False
        
        # 系统配置
        self.config = {
            'recognition_interval': 3,  # 每个摄像头识别间隔(秒)
            'cycle_delay': 1,  # 摄像头切换间隔(秒)
            'max_retry_times': 3,  # 最大重试次数
            'retry_delay': 2,  # 重试延迟(秒)
            'heartbeat_interval': 30,  # 心跳间隔(秒)
            'status_report_interval': 300,  # 状态报告间隔(秒，5分钟)
            'push_timeout': 10,  # 推送超时(秒)
            'enable_websocket': True,  # 启用WebSocket推送
            'save_recognition_results': True,  # 保存识别结果
            'monitor_performance': True  # 监控性能
        }
        
        # 摄像头配置
        self.enabled_cameras = []
        self.recognition_config = {}
        self.push_config = {}
        
        # 运行状态
        self.running_threads = {}
        self.camera_locks = {}
        self.websocket_client = None
        
        # 统计信息
        self.stats = {
            'start_time': get_timestamp(),
            'total_cycles': 0,
            'total_recognitions': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'total_pushes': 0,
            'successful_pushes': 0,
            'failed_pushes': 0,
            'camera_stats': {},  # 按摄像头统计
            'recognition_times': [],
            'push_times': [],
            'error_counts': {},
            'last_status_report': get_timestamp()
        }
        
        # 监控和告警
        self.performance_monitor = None
        self.status_monitor = None
        
        log_info("实时识别推送系统初始化完成", "TUI")
    
    def initialize_system(self) -> bool:
        """初始化系统"""
        try:
            print("🚀 实时识别推送系统启动中...")
            print("=" * 60)
            
            # 注册进程
            register_result = register_process(self.process_name, self.process_type)
            if register_result['status'] != 'success':
                print(f"❌ 进程注册失败: {register_result['message']}")
                return False
            
            # 检查配置
            if not self._check_system_config():
                return False
            
            # 加载配置
            if not self._load_all_configs():
                return False
            
            # 初始化组件
            if not self._initialize_components():
                return False
            
            # 启动监控
            if not self._start_monitoring():
                return False
            
            return True
            
        except Exception as e:
            log_error(f"系统初始化失败: {e}", "TUI")
            print(f"❌ 系统初始化失败: {e}")
            return False
    
    def _check_system_config(self) -> bool:
        """检查系统配置"""
        try:
            print("📋 检查系统配置...")
            
            # 验证所有配置
            validation_result = validate_all_configs()
            if validation_result['status'] != 'success':
                print(f"❌ 配置验证失败: {validation_result['message']}")
                return False
            
            validation_data = validation_result['data']
            if not validation_data['overall_valid']:
                print("❌ 配置文件存在问题")
                return False
            
            print("✅ 系统配置检查通过")
            return True
            
        except Exception as e:
            log_error(f"配置检查失败: {e}", "TUI")
            print(f"❌ 配置检查失败: {e}")
            return False
    
    def _load_all_configs(self) -> bool:
        """加载所有配置"""
        try:
            print("⚙️  加载系统配置...")
            
            # 加载摄像头配置
            cameras_result = get_enabled_cameras()
            if cameras_result['status'] != 'success':
                print(f"❌ 加载摄像头配置失败: {cameras_result['message']}")
                return False
            
            self.enabled_cameras = cameras_result['data']['cameras']
            if not self.enabled_cameras:
                print("❌ 没有启用的摄像头")
                return False
            
            # 加载识别配置
            recognition_result = load_recognition_config()
            if recognition_result['status'] != 'success':
                print(f"❌ 加载识别配置失败: {recognition_result['message']}")
                return False
            
            self.recognition_config = recognition_result['data']
            
            # 加载推送配置
            push_result = load_push_config()
            if push_result['status'] != 'success':
                print(f"❌ 加载推送配置失败: {push_result['message']}")
                return False
            
            self.push_config = push_result['data']
            
            print(f"✅ 配置加载完成:")
            print(f"   启用摄像头: {len(self.enabled_cameras)} 个")
            print(f"   识别模式: {self.recognition_config.get('processing', {}).get('recognition_mode', 'hybrid')}")
            print(f"   WebSocket推送: {'启用' if self.push_config.get('websocket', {}).get('enabled', False) else '禁用'}")
            
            # 初始化摄像头统计
            for camera in self.enabled_cameras:
                camera_id = camera['id']
                self.stats['camera_stats'][camera_id] = {
                    'total_recognitions': 0,
                    'successful_recognitions': 0,
                    'failed_recognitions': 0,
                    'last_recognition_time': None,
                    'last_success_time': None,
                    'consecutive_failures': 0,
                    'average_recognition_time': 0.0
                }
            
            return True
            
        except Exception as e:
            log_error(f"加载配置失败: {e}", "TUI")
            print(f"❌ 加载配置失败: {e}")
            return False
    
    def _initialize_components(self) -> bool:
        """初始化组件"""
        try:
            print("🔧 初始化系统组件...")
            
            # 确保目录存在
            ensure_dirs_exist(
                get_result_dir(),
                get_result_dir() / "recognition",
                get_result_dir() / "monitoring"
            )
            
            # 初始化WebSocket客户端
            if (self.config['enable_websocket'] and 
                self.push_config.get('websocket', {}).get('enabled', False)):
                
                if not self._initialize_websocket_client():
                    log_warning("WebSocket客户端初始化失败，将跳过推送功能", "TUI")
            
            print("✅ 系统组件初始化完成")
            return True
            
        except Exception as e:
            log_error(f"组件初始化失败: {e}", "TUI")
            print(f"❌ 组件初始化失败: {e}")
            return False
    
    def _initialize_websocket_client(self) -> bool:
        """初始化WebSocket客户端"""
        try:
            ws_config = self.push_config.get('websocket', {})
            server_url = ws_config.get('server_url', 'ws://localhost:8001')
            client_id = ws_config.get('client_id', 'python_client_tui')
            
            print(f"📡 初始化WebSocket客户端: {server_url}")
            
            # 导入WebSocket客户端
            from src.clients.websocket_client import start_push_client
            
            # 启动客户端
            result = start_push_client(server_url, client_id)
            
            if result['status'] == 'success':
                print("✅ WebSocket客户端启动成功")
                return True
            else:
                print(f"❌ WebSocket客户端启动失败: {result['message']}")
                return False
                
        except Exception as e:
            log_error(f"WebSocket客户端初始化失败: {e}", "TUI")
            return False
    
    def _start_monitoring(self) -> bool:
        """启动监控"""
        try:
            if not self.config['monitor_performance']:
                return True
            
            print("📊 启动性能监控...")
            
            # 启动性能监控线程
            self.performance_monitor = threading.Thread(
                target=self._performance_monitor_loop,
                daemon=True
            )
            self.performance_monitor.start()
            
            # 启动状态报告线程
            self.status_monitor = threading.Thread(
                target=self._status_report_loop,
                daemon=True
            )
            self.status_monitor.start()
            
            print("✅ 监控系统启动成功")
            return True
            
        except Exception as e:
            log_error(f"启动监控失败: {e}", "TUI")
            print(f"❌ 启动监控失败: {e}")
            return False
    
    def run_recognition_loop(self):
        """运行识别循环"""
        try:
            print("\n🔄 开始实时识别循环...")
            print(f"   识别间隔: {self.config['recognition_interval']} 秒")
            print(f"   切换延迟: {self.config['cycle_delay']} 秒")
            print(f"   摄像头数量: {len(self.enabled_cameras)}")
            print("-" * 50)
            
            last_heartbeat = time.time()
            
            while not self.shutdown_requested:
                cycle_start_time = time.time()
                self.stats['total_cycles'] += 1
                
                print(f"\n🔄 第 {self.stats['total_cycles']} 轮识别循环 ({datetime.now().strftime('%H:%M:%S')})")
                
                # 循环处理每个摄像头
                for i, camera in enumerate(self.enabled_cameras):
                    if self.shutdown_requested:
                        break
                    
                    camera_id = camera['id']
                    camera_name = camera.get('name', f'摄像头{camera_id}')
                    
                    print(f"   📷 ({i+1}/{len(self.enabled_cameras)}) {camera_name} ({camera_id})")
                    
                    # 执行识别
                    recognition_success = self._process_single_camera(camera_id)
                    
                    # 摄像头切换延迟
                    if i < len(self.enabled_cameras) - 1:  # 不是最后一个摄像头
                        time.sleep(self.config['cycle_delay'])
                
                # 更新心跳
                current_time = time.time()
                if current_time - last_heartbeat >= self.config['heartbeat_interval']:
                    update_heartbeat()
                    last_heartbeat = current_time
                
                # 循环间隔
                cycle_duration = time.time() - cycle_start_time
                remaining_time = max(0, self.config['recognition_interval'] - cycle_duration)
                
                if remaining_time > 0:
                    print(f"   ⏳ 等待 {remaining_time:.1f} 秒后开始下轮循环...")
                    time.sleep(remaining_time)
                else:
                    print(f"   ⚡ 循环耗时 {cycle_duration:.1f} 秒，立即开始下轮")
                    
        except KeyboardInterrupt:
            print("\n⏹️  接收到停止信号")
            self.shutdown_requested = True
        except Exception as e:
            log_error(f"识别循环异常: {e}", "TUI")
            print(f"❌ 识别循环异常: {e}")
            self.shutdown_requested = True
    
    def _process_single_camera(self, camera_id: str) -> bool:
        """处理单个摄像头识别"""
        recognition_start_time = time.time()
        retry_count = 0
        
        while retry_count <= self.config['max_retry_times']:
            try:
                # 更新统计
                self.stats['total_recognitions'] += 1
                self.stats['camera_stats'][camera_id]['total_recognitions'] += 1
                
                # 检查摄像头可用性
                availability = check_camera_available(camera_id)
                if availability['status'] == 'success' and not availability['data']['available']:
                    print(f"      ⚠️  摄像头被占用，跳过")
                    return False
                
                # 执行完整识别流程
                result = self._execute_recognition_pipeline(camera_id)
                
                if result['success']:
                    # 识别成功
                    recognition_time = time.time() - recognition_start_time
                    
                    # 更新统计
                    self.stats['successful_recognitions'] += 1
                    self.stats['camera_stats'][camera_id]['successful_recognitions'] += 1
                    self.stats['camera_stats'][camera_id]['last_success_time'] = get_timestamp()
                    self.stats['camera_stats'][camera_id]['consecutive_failures'] = 0
                    self.stats['recognition_times'].append(recognition_time)
                    
                    # 推送结果
                    if result.get('recognition_data'):
                        push_success = self._push_recognition_result(camera_id, result['recognition_data'])
                        
                        if push_success:
                            print(f"      ✅ 识别+推送成功 ({recognition_time:.1f}s)")
                        else:
                            print(f"      ⚠️  识别成功，推送失败 ({recognition_time:.1f}s)")
                    else:
                        print(f"      ✅ 识别成功 ({recognition_time:.1f}s)")
                    
                    return True
                else:
                    # 识别失败，尝试重试
                    retry_count += 1
                    self.stats['camera_stats'][camera_id]['consecutive_failures'] += 1
                    
                    if retry_count <= self.config['max_retry_times']:
                        print(f"      ❌ 识别失败，重试 {retry_count}/{self.config['max_retry_times']}: {result.get('error', 'Unknown error')}")
                        time.sleep(self.config['retry_delay'])
                    else:
                        print(f"      ❌ 识别失败，达到最大重试次数: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                retry_count += 1
                log_error(f"摄像头 {camera_id} 识别异常: {e}", "TUI")
                
                if retry_count <= self.config['max_retry_times']:
                    print(f"      💥 识别异常，重试 {retry_count}/{self.config['max_retry_times']}: {str(e)}")
                    time.sleep(self.config['retry_delay'])
                else:
                    print(f"      💥 识别异常，达到最大重试次数: {str(e)}")
        
        # 所有重试都失败
        self.stats['failed_recognitions'] += 1
        self.stats['camera_stats'][camera_id]['failed_recognitions'] += 1
        self.stats['camera_stats'][camera_id]['last_recognition_time'] = get_timestamp()
        
        return False
    
    def _execute_recognition_pipeline(self, camera_id: str) -> Dict[str, Any]:
        """执行完整识别流程"""
        try:
            # 1. 锁定摄像头
            lock_result = lock_camera(camera_id)
            if lock_result['status'] != 'success':
                return {
                    'success': False,
                    'error': f"无法锁定摄像头: {lock_result['message']}"
                }
            
            try:
                # 2. 拍照
                photo_result = self._take_photo(camera_id)
                if not photo_result['success']:
                    return {
                        'success': False,
                        'error': f"拍照失败: {photo_result['error']}"
                    }
                
                # 3. 裁剪图片
                crop_result = self._crop_images(photo_result['file_path'])
                if not crop_result['success']:
                    return {
                        'success': False,
                        'error': f"裁剪失败: {crop_result['error']}"
                    }
                
                # 4. 识别图片
                recognition_result = self._recognize_images(crop_result['cropped_images'])
                if not recognition_result['success']:
                    return {
                        'success': False,
                        'error': f"识别失败: {recognition_result['error']}"
                    }
                
                # 5. 格式化识别结果
                formatted_result = self._format_recognition_result(camera_id, recognition_result)
                
                return {
                    'success': True,
                    'recognition_data': formatted_result,
                    'photo_info': photo_result,
                    'crop_info': crop_result,
                    'raw_recognition': recognition_result
                }
                
            finally:
                # 释放摄像头锁
                release_camera(camera_id)
                
        except Exception as e:
            return {
                'success': False,
                'error': f"识别流程异常: {str(e)}"
            }
    
    def _take_photo(self, camera_id: str) -> Dict[str, Any]:
        """拍照"""
        try:
            from src.processors.photo_controller import take_photo_by_id
            
            result = take_photo_by_id(camera_id)
            
            if result['status'] == 'success':
                return {
                    'success': True,
                    'filename': result['data']['filename'],
                    'file_path': result['data']['file_path'],
                    'file_size': result['data']['file_size']
                }
            else:
                return {
                    'success': False,
                    'error': result['message']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"拍照异常: {str(e)}"
            }
    
    def _crop_images(self, image_path: str) -> Dict[str, Any]:
        """裁剪图片"""
        try:
            from src.processors.image_cutter import process_image
            
            success = process_image(image_path)
            
            if success:
                # 获取裁剪后的图片列表
                image_dir = Path(image_path).parent / "cut"
                if image_dir.exists():
                    cropped_images = list(image_dir.glob(f"{Path(image_path).stem}_*.png"))
                    return {
                        'success': True,
                        'cropped_images': [str(img) for img in cropped_images],
                        'total_count': len(cropped_images)
                    }
                else:
                    return {
                        'success': False,
                        'error': '裁剪目录不存在'
                    }
            else:
                return {
                    'success': False,
                    'error': '图片裁剪失败'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"裁剪异常: {str(e)}"
            }
    
    def _recognize_images(self, cropped_images: List[str]) -> Dict[str, Any]:
        """识别图片"""
        try:
            recognition_results = {}
            total_images = len(cropped_images)
            successful_count = 0
            
            for image_path in cropped_images:
                image_name = Path(image_path).name
                position = self._extract_position_from_filename(image_name)
                
                # 根据配置选择识别方法
                recognition_mode = self.recognition_config.get('processing', {}).get('recognition_mode', 'hybrid')
                
                if recognition_mode == 'yolo_only':
                    result = self._recognize_with_yolo(image_path)
                elif recognition_mode == 'ocr_only':
                    result = self._recognize_with_ocr(image_path)
                else:  # hybrid
                    result = self._recognize_hybrid(image_path)
                
                if result['success']:
                    successful_count += 1
                
                recognition_results[position] = result
            
            return {
                'success': successful_count > 0,  # 至少有一个成功就算成功
                'results': recognition_results,
                'total_count': total_images,
                'successful_count': successful_count,
                'success_rate': round(successful_count / total_images * 100, 1) if total_images > 0 else 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"识别异常: {str(e)}"
            }
    
    def _recognize_with_yolo(self, image_path: str) -> Dict[str, Any]:
        """使用YOLOv8识别"""
        try:
            from src.processors.poker_recognizer import recognize_poker_card
            
            result = recognize_poker_card(image_path)
            
            if result['success']:
                return {
                    'success': True,
                    'suit': result['suit'],
                    'rank': result['rank'],
                    'confidence': result['confidence'],
                    'method': 'yolo'
                }
            else:
                return {
                    'success': False,
                    'error': result['error'],
                    'method': 'yolo'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"YOLO识别异常: {str(e)}",
                'method': 'yolo'
            }
    
    def _recognize_with_ocr(self, image_path: str) -> Dict[str, Any]:
        """使用OCR识别"""
        try:
            # 优先使用PaddleOCR
            try:
                from src.processors.poker_paddle_ocr import recognize_poker_character
                
                result = recognize_poker_character(image_path)
                
                if result['success']:
                    return {
                        'success': True,
                        'suit': '',
                        'rank': result['character'],
                        'confidence': result['confidence'],
                        'method': 'paddle_ocr'
                    }
                else:
                    raise Exception(result['error'])
                    
            except ImportError:
                # 回退到EasyOCR
                from src.processors.poker_ocr import recognize_poker_character
                
                result = recognize_poker_character(image_path)
                
                if result['success']:
                    return {
                        'success': True,
                        'suit': '',
                        'rank': result['character'],
                        'confidence': result['confidence'],
                        'method': 'easy_ocr'
                    }
                else:
                    return {
                        'success': False,
                        'error': result['error'],
                        'method': 'ocr'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': f"OCR识别异常: {str(e)}",
                'method': 'ocr'
            }
    
    def _recognize_hybrid(self, image_path: str) -> Dict[str, Any]:
        """混合识别方法"""
        try:
            # 先尝试YOLO
            yolo_result = self._recognize_with_yolo(image_path)
            
            # 如果YOLO成功且置信度高，直接返回
            if (yolo_result['success'] and 
                yolo_result.get('confidence', 0) >= 0.8):
                yolo_result['method'] = 'hybrid_yolo'
                return yolo_result
            
            # 否则尝试OCR作为补充
            ocr_result = self._recognize_with_ocr(image_path)
            
            # 如果OCR成功，结合两种结果
            if ocr_result['success']:
                if yolo_result['success']:
                    # 结合YOLO的花色和OCR的点数
                    return {
                        'success': True,
                        'suit': yolo_result['suit'],
                        'rank': ocr_result['rank'],
                        'confidence': (yolo_result.get('confidence', 0) + ocr_result.get('confidence', 0)) / 2,
                        'method': 'hybrid_combined'
                    }
                else:
                    ocr_result['method'] = 'hybrid_ocr'
                    return ocr_result
            
            # 都失败时返回YOLO结果
            yolo_result['method'] = 'hybrid_yolo_fallback'
            return yolo_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"混合识别异常: {str(e)}",
                'method': 'hybrid'
            }
    
    def _extract_position_from_filename(self, filename: str) -> str:
        """从文件名提取位置信息"""
        try:
            # 文件名格式: camera_001_zhuang_1.png
            parts = filename.split('_')
            if len(parts) >= 4:
                return f"{parts[2]}_{parts[3]}"  # zhuang_1
            return "unknown"
        except:
            return "unknown"
    
    def _format_recognition_result(self, camera_id: str, recognition_result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化识别结果"""
        try:
            positions = {}
            
            # 标准位置列表
            standard_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
            
            for position in standard_positions:
                if position in recognition_result['results']:
                    result = recognition_result['results'][position]
                    
                    if result['success']:
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
                else:
                    positions[position] = {
                        'suit': '',
                        'rank': '',
                        'confidence': 0.0
                    }
            
            return {
                'camera_id': camera_id,
                'positions': positions,
                'timestamp': get_timestamp(),
                'recognition_summary': {
                    'total_positions': recognition_result['total_count'],
                    'successful_positions': recognition_result['successful_count'],
                    'success_rate': recognition_result['success_rate']
                }
            }
            
        except Exception as e:
            log_error(f"格式化识别结果失败: {e}", "TUI")
            return {
                'camera_id': camera_id,
                'positions': {},
                'timestamp': get_timestamp(),
                'error': str(e)
            }
    
    def _push_recognition_result(self, camera_id: str, recognition_data: Dict[str, Any]) -> bool:
        """推送识别结果"""
        try:
            push_start_time = time.time()
            
            # 保存识别结果到本地
            if self.config['save_recognition_results']:
                self._save_recognition_result(recognition_data)
            
            # WebSocket推送
            if self.config['enable_websocket']:
                push_success = self._push_to_websocket(recognition_data)
                
                push_time = time.time() - push_start_time
                self.stats['push_times'].append(push_time)
                self.stats['total_pushes'] += 1
                
                if push_success:
                    self.stats['successful_pushes'] += 1
                    return True
                else:
                    self.stats['failed_pushes'] += 1
                    return False
            
            return True  # 如果没有启用推送，认为成功
            
        except Exception as e:
            log_error(f"推送识别结果失败: {e}", "TUI")
            self.stats['failed_pushes'] += 1
            return False
    
    def _push_to_websocket(self, recognition_data: Dict[str, Any]) -> bool:
        """推送到WebSocket"""
        try:
            from src.clients.websocket_client import push_recognition_result
            
            camera_id = recognition_data['camera_id']
            positions = recognition_data['positions']
            
            # 格式化推送数据
            push_positions = {}
            for position, pos_data in positions.items():
                push_positions[position] = {
                    'suit': pos_data.get('suit', ''),
                    'rank': pos_data.get('rank', '')
                }
            
            # 执行推送
            result = push_recognition_result(camera_id, push_positions)
            
            return result['status'] == 'success'
            
        except Exception as e:
            log_error(f"WebSocket推送失败: {e}", "TUI")
            return False
    
    def _save_recognition_result(self, recognition_data: Dict[str, Any]):
        """保存识别结果到本地"""
        try:
            # 导入识别管理器
            from src.core.recognition_manager import receive_recognition_data
            
            # 保存结果
            result = receive_recognition_data(recognition_data)
            
            if result['status'] != 'success':
                log_warning(f"保存识别结果失败: {result['message']}", "TUI")
                
        except Exception as e:
            log_error(f"保存识别结果异常: {e}", "TUI")
    
    def _performance_monitor_loop(self):
        """性能监控循环"""
        try:
            while not self.shutdown_requested:
                time.sleep(60)  # 每分钟检查一次
                
                if self.shutdown_requested:
                    break
                
                self._check_system_performance()
                self._check_camera_health()
                
        except Exception as e:
            log_error(f"性能监控循环异常: {e}", "TUI")
    
    def _status_report_loop(self):
        """状态报告循环"""
        try:
            while not self.shutdown_requested:
                time.sleep(self.config['status_report_interval'])
                
                if self.shutdown_requested:
                    break
                
                self._generate_status_report()
                
        except Exception as e:
            log_error(f"状态报告循环异常: {e}", "TUI")
    
    def _check_system_performance(self):
        """检查系统性能"""
        try:
            # 检查识别时间
            if self.stats['recognition_times']:
                recent_times = self.stats['recognition_times'][-20:]  # 最近20次
                avg_time = sum(recent_times) / len(recent_times)
                
                if avg_time > 30:  # 超过30秒告警
                    log_warning(f"识别时间过长: 平均 {avg_time:.1f} 秒", "TUI")
            
            # 检查推送时间
            if self.stats['push_times']:
                recent_push_times = self.stats['push_times'][-20:]
                avg_push_time = sum(recent_push_times) / len(recent_push_times)
                
                if avg_push_time > 5:  # 超过5秒告警
                    log_warning(f"推送时间过长: 平均 {avg_push_time:.1f} 秒", "TUI")
            
            # 检查成功率
            if self.stats['total_recognitions'] > 0:
                success_rate = self.stats['successful_recognitions'] / self.stats['total_recognitions']
                
                if success_rate < 0.8:  # 成功率低于80%告警
                    log_warning(f"识别成功率过低: {success_rate*100:.1f}%", "TUI")
                    
        except Exception as e:
            log_error(f"系统性能检查失败: {e}", "TUI")
    
    def _check_camera_health(self):
        """检查摄像头健康状态"""
        try:
            for camera_id, stats in self.stats['camera_stats'].items():
                # 检查连续失败次数
                if stats['consecutive_failures'] >= 5:
                    log_warning(f"摄像头 {camera_id} 连续失败 {stats['consecutive_failures']} 次", "TUI")
                
                # 检查是否长时间没有成功识别
                if stats['last_success_time']:
                    try:
                        last_success = datetime.fromisoformat(stats['last_success_time'])
                        if datetime.now() - last_success > timedelta(minutes=30):
                            log_warning(f"摄像头 {camera_id} 超过30分钟未成功识别", "TUI")
                    except ValueError:
                        pass
                        
        except Exception as e:
            log_error(f"摄像头健康检查失败: {e}", "TUI")
    
    def _generate_status_report(self):
        """生成状态报告"""
        try:
            current_time = get_timestamp()
            
            # 计算运行时间
            start_time = datetime.fromisoformat(self.stats['start_time'])
            current_datetime = datetime.fromisoformat(current_time)
            uptime = current_datetime - start_time
            
            # 计算成功率
            total_recognitions = self.stats['total_recognitions']
            successful_recognitions = self.stats['successful_recognitions']
            recognition_success_rate = (successful_recognitions / total_recognitions * 100) if total_recognitions > 0 else 0
            
            total_pushes = self.stats['total_pushes']
            successful_pushes = self.stats['successful_pushes']
            push_success_rate = (successful_pushes / total_pushes * 100) if total_pushes > 0 else 0
            
            # 计算平均时间
            avg_recognition_time = 0
            if self.stats['recognition_times']:
                avg_recognition_time = sum(self.stats['recognition_times']) / len(self.stats['recognition_times'])
            
            avg_push_time = 0
            if self.stats['push_times']:
                avg_push_time = sum(self.stats['push_times']) / len(self.stats['push_times'])
            
            # 生成报告
            report = f"""
🚀 实时识别推送系统状态报告
{'='*50}
📅 报告时间: {current_time}
⏰ 运行时长: {str(uptime).split('.')[0]}
🔄 总循环数: {self.stats['total_cycles']}

📊 识别统计:
   总识别次数: {total_recognitions}
   成功次数: {successful_recognitions}  
   失败次数: {self.stats['failed_recognitions']}
   成功率: {recognition_success_rate:.1f}%
   平均耗时: {avg_recognition_time:.2f}秒

📡 推送统计:
   总推送次数: {total_pushes}
   成功次数: {successful_pushes}
   失败次数: {self.stats['failed_pushes']}
   成功率: {push_success_rate:.1f}%
   平均耗时: {avg_push_time:.2f}秒

📷 摄像头状态:"""
            
            for camera_id, camera_stats in self.stats['camera_stats'].items():
                camera = next((c for c in self.enabled_cameras if c['id'] == camera_id), None)
                camera_name = camera.get('name', f'摄像头{camera_id}') if camera else camera_id
                
                camera_success_rate = 0
                if camera_stats['total_recognitions'] > 0:
                    camera_success_rate = camera_stats['successful_recognitions'] / camera_stats['total_recognitions'] * 100
                
                status_icon = "✅" if camera_stats['consecutive_failures'] == 0 else "⚠️" if camera_stats['consecutive_failures'] < 3 else "❌"
                
                report += f"""
   {status_icon} {camera_name} ({camera_id}):
      识别: {camera_stats['successful_recognitions']}/{camera_stats['total_recognitions']} ({camera_success_rate:.1f}%)
      连续失败: {camera_stats['consecutive_failures']} 次"""
            
            report += f"\n{'='*50}"
            
            print(report)
            log_info("状态报告生成完成", "TUI")
            
            self.stats['last_status_report'] = current_time
            
        except Exception as e:
            log_error(f"生成状态报告失败: {e}", "TUI")
    
    def display_final_statistics(self):
        """显示最终统计信息"""
        try:
            print("\n📊 最终运行统计:")
            print("=" * 50)
            
            # 计算运行时间
            start_time = datetime.fromisoformat(self.stats['start_time'])
            end_time = datetime.now()
            total_uptime = end_time - start_time
            
            print(f"⏰ 总运行时间: {str(total_uptime).split('.')[0]}")
            print(f"🔄 总循环数: {self.stats['total_cycles']}")
            print(f"📊 总识别次数: {self.stats['total_recognitions']}")
            print(f"✅ 成功识别: {self.stats['successful_recognitions']}")
            print(f"❌ 失败识别: {self.stats['failed_recognitions']}")
            
            if self.stats['total_recognitions'] > 0:
                success_rate = self.stats['successful_recognitions'] / self.stats['total_recognitions'] * 100
                print(f"📈 识别成功率: {success_rate:.1f}%")
            
            print(f"📡 总推送次数: {self.stats['total_pushes']}")
            print(f"✅ 成功推送: {self.stats['successful_pushes']}")
            print(f"❌ 失败推送: {self.stats['failed_pushes']}")
            
            if self.stats['total_pushes'] > 0:
                push_success_rate = self.stats['successful_pushes'] / self.stats['total_pushes'] * 100
                print(f"📈 推送成功率: {push_success_rate:.1f}%")
            
            # 显示摄像头统计
            print(f"\n📷 各摄像头统计:")
            for camera_id, camera_stats in self.stats['camera_stats'].items():
                camera = next((c for c in self.enabled_cameras if c['id'] == camera_id), None)
                camera_name = camera.get('name', f'摄像头{camera_id}') if camera else camera_id
                
                camera_success_rate = 0
                if camera_stats['total_recognitions'] > 0:
                    camera_success_rate = camera_stats['successful_recognitions'] / camera_stats['total_recognitions'] * 100
                
                print(f"   {camera_name} ({camera_id}): {camera_stats['successful_recognitions']}/{camera_stats['total_recognitions']} ({camera_success_rate:.1f}%)")
            
            print("=" * 50)
            
        except Exception as e:
            log_error(f"显示最终统计失败: {e}", "TUI")
    
    def shutdown_system(self):
        """关闭系统"""
        try:
            print("\n🔄 正在关闭实时识别推送系统...")
            
            # 停止WebSocket客户端
            if self.config['enable_websocket']:
                try:
                    from src.clients.websocket_client import stop_push_client
                    result = stop_push_client()
                    if result['status'] == 'success':
                        print("✅ WebSocket客户端已关闭")
                except Exception as e:
                    log_error(f"关闭WebSocket客户端失败: {e}", "TUI")
            
            # 等待监控线程结束
            if self.performance_monitor and self.performance_monitor.is_alive():
                self.performance_monitor.join(timeout=2)
            
            if self.status_monitor and self.status_monitor.is_alive():
                self.status_monitor.join(timeout=2)
            
            # 注销进程
            unregister_result = unregister_process()
            if unregister_result['status'] == 'success':
                print("✅ 进程注销成功")
            
            # 显示最终统计
            self.display_final_statistics()
            
            print("👋 实时识别推送系统已安全关闭")
            
        except Exception as e:
            log_error(f"关闭系统失败: {e}", "TUI")
            print(f"❌ 关闭系统时出错: {e}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='实时识别推送系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python tui.py                             # 默认配置运行
  python tui.py --interval 5               # 设置识别间隔为5秒
  python tui.py --no-websocket             # 禁用WebSocket推送
  python tui.py --daemon                   # 后台运行模式
  python tui.py --test-mode --duration 60  # 测试模式运行60秒
        """
    )
    
    parser.add_argument('--interval', type=int, default=3,
                       help='识别间隔(秒) (默认: 3)')
    parser.add_argument('--cycle-delay', type=float, default=1.0,
                       help='摄像头切换延迟(秒) (默认: 1.0)')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='最大重试次数 (默认: 3)')
    parser.add_argument('--retry-delay', type=float, default=2.0,
                       help='重试延迟(秒) (默认: 2.0)')
    parser.add_argument('--no-websocket', action='store_true',
                       help='禁用WebSocket推送')
    parser.add_argument('--no-save-results', action='store_true',
                       help='不保存识别结果到本地')
    parser.add_argument('--no-monitoring', action='store_true',
                       help='禁用性能监控')
    parser.add_argument('--daemon', action='store_true',
                       help='后台运行模式')
    parser.add_argument('--test-mode', action='store_true',
                       help='测试模式')
    parser.add_argument('--duration', type=int, default=0,
                       help='测试模式运行时长(秒)，0表示无限制')
    parser.add_argument('--status-interval', type=int, default=300,
                       help='状态报告间隔(秒) (默认: 300)')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析参数
        args = parse_arguments()
        
        # 创建实时识别推送系统实例
        system = TuiSystem()
        
        # 更新配置
        system.config.update({
            'recognition_interval': args.interval,
            'cycle_delay': args.cycle_delay,
            'max_retry_times': args.max_retries,
            'retry_delay': args.retry_delay,
            'enable_websocket': not args.no_websocket,
            'save_recognition_results': not args.no_save_results,
            'monitor_performance': not args.no_monitoring,
            'status_report_interval': args.status_interval
        })
        
        # 初始化系统
        if not system.initialize_system():
            return 1
        
        # 显示系统信息
        print(f"\n🚀 系统配置:")
        print(f"   识别间隔: {system.config['recognition_interval']} 秒")
        print(f"   切换延迟: {system.config['cycle_delay']} 秒")
        print(f"   最大重试: {system.config['max_retry_times']} 次")
        print(f"   WebSocket推送: {'启用' if system.config['enable_websocket'] else '禁用'}")
        print(f"   保存结果: {'启用' if system.config['save_recognition_results'] else '禁用'}")
        print(f"   性能监控: {'启用' if system.config['monitor_performance'] else '禁用'}")
        
        if args.test_mode:
            print(f"   🧪 测试模式: {args.duration if args.duration > 0 else '无限制'} 秒")
        
        # 设置信号处理
        def signal_handler(signum, frame):
            print(f"\n📡 接收到信号 {signum}，准备关闭系统...")
            system.shutdown_requested = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 测试模式
        if args.test_mode and args.duration > 0:
            print(f"\n🧪 测试模式运行 {args.duration} 秒...")
            
            # 启动识别循环线程
            recognition_thread = threading.Thread(target=system.run_recognition_loop, daemon=True)
            recognition_thread.start()
            
            # 等待指定时间
            time.sleep(args.duration)
            system.shutdown_requested = True
            
            # 等待线程结束
            recognition_thread.join(timeout=5)
            
        else:
            # 正常运行模式
            if args.daemon:
                print("\n🔄 后台运行模式，按 Ctrl+C 停止")
            else:
                print("\n🔄 前台运行模式，按 Ctrl+C 停止")
            
            # 运行识别循环
            system.run_recognition_loop()
        
        # 关闭系统
        system.shutdown_system()
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())