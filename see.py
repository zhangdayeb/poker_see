#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单摄像头识别测试入口程序 - 专门用于测试识别流程
功能:
1. 选择任意摄像头进行识别测试
2. 支持多种识别算法 (YOLOv8/OCR/混合)
3. 实时显示识别过程和结果
4. 性能分析和调试信息
5. 识别结果可视化展示
"""

import sys
import time
import signal
import argparse
import os
from pathlib import Path
from typing import Dict, Any, List, Optional  # 添加类型注解导入

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
    load_camera_config, load_recognition_config, get_enabled_cameras, 
    get_camera_by_id, validate_all_configs
)
from state_manager import (
    register_process, unregister_process, update_heartbeat,
    lock_camera, release_camera, check_camera_available
)

# 导入核心模块
from src.core.utils import (
    get_timestamp, ensure_dirs_exist, get_config_dir, get_image_dir, get_result_dir,
    log_info, log_success, log_error, log_warning
)

class SeeSystem:
    """识别测试系统"""
    
    def __init__(self):
        """初始化识别测试系统"""
        self.process_name = "see"
        self.process_type = "testing"
        self.shutdown_requested = False
        
        # 系统配置
        self.config = {
            'camera_id': None,
            'recognition_mode': 'hybrid',  # yolo_only, ocr_only, hybrid
            'auto_mode': False,
            'loop_interval': 5,  # 自动模式循环间隔(秒)
            'save_debug_images': True,
            'show_confidence': True,
            'max_recognition_time': 30  # 最大识别时间(秒)
        }
        
        # 算法配置
        self.recognition_config = {}
        
        # 统计信息
        self.stats = {
            'total_recognitions': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'start_time': get_timestamp(),
            'recognition_times': []
        }
        
        log_info("识别测试系统初始化完成", "SEE")
    
    def initialize_system(self) -> bool:
        """初始化系统"""
        try:
            print("🔍 扑克识别测试系统启动中...")
            print("=" * 60)
            
            # 注册进程
            register_result = register_process(self.process_name, self.process_type)
            if register_result['status'] != 'success':
                print(f"❌ 进程注册失败: {register_result['message']}")
                return False
            
            # 检查配置
            if not self._check_system_config():
                return False
            
            # 加载识别配置
            if not self._load_recognition_config():
                return False
            
            # 检查目录
            self._ensure_directories()
            
            return True
            
        except Exception as e:
            log_error(f"系统初始化失败: {e}", "SEE")
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
            
            # 获取摄像头配置
            camera_result = get_enabled_cameras()
            if camera_result['status'] != 'success':
                print(f"❌ 获取摄像头配置失败: {camera_result['message']}")
                return False
            
            camera_count = camera_result['data']['total_count']
            if camera_count == 0:
                print("⚠️  没有找到启用的摄像头")
                return False
            
            print(f"✅ 配置检查完成: {camera_count} 个启用摄像头")
            return True
            
        except Exception as e:
            log_error(f"配置检查失败: {e}", "SEE")
            print(f"❌ 配置检查失败: {e}")
            return False
    
    def _load_recognition_config(self) -> bool:
        """加载识别配置"""
        try:
            print("🧠 加载识别算法配置...")
            
            config_result = load_recognition_config()
            if config_result['status'] != 'success':
                print(f"❌ 加载识别配置失败: {config_result['message']}")
                return False
            
            self.recognition_config = config_result['data']
            
            # 显示算法状态
            algorithms = self.recognition_config.get('algorithms', {})
            enabled_algos = []
            for algo_name, algo_config in algorithms.items():
                if algo_config.get('enabled', False):
                    enabled_algos.append(algo_name)
            
            print(f"✅ 识别配置加载完成")
            print(f"   启用算法: {', '.join(enabled_algos) if enabled_algos else '无'}")
            print(f"   识别模式: {self.recognition_config.get('processing', {}).get('recognition_mode', 'hybrid')}")
            
            return True
            
        except Exception as e:
            log_error(f"加载识别配置失败: {e}", "SEE")
            print(f"❌ 加载识别配置失败: {e}")
            return False
    
    def _ensure_directories(self):
        """确保必要目录存在"""
        try:
            dirs = [
                get_config_dir(),
                get_image_dir(),
                get_result_dir(),
                get_image_dir() / "cut",  # 裁剪图片目录
                get_result_dir() / "recognition"  # 识别结果目录
            ]
            ensure_dirs_exist(*dirs)
            print("✅ 系统目录检查完成")
        except Exception as e:
            log_error(f"目录检查失败: {e}", "SEE")
    
    def select_camera_interactive(self) -> bool:
        """交互式选择摄像头"""
        try:
            # 获取启用的摄像头
            cameras_result = get_enabled_cameras()
            if cameras_result['status'] != 'success':
                print("❌ 获取摄像头列表失败")
                return False
            
            cameras = cameras_result['data']['cameras']
            if not cameras:
                print("❌ 没有可用的摄像头")
                return False
            
            print("\n📷 可用摄像头列表:")
            for i, camera in enumerate(cameras):
                camera_name = camera.get('name', f'摄像头{camera["id"]}')
                enabled_status = "✅" if camera.get('enabled', True) else "❌"
                print(f"   {i+1}. {enabled_status} {camera_name} ({camera['id']}) - {camera.get('ip', 'N/A')}")
            
            while True:
                try:
                    choice = input("\n请选择要测试的摄像头 (输入序号): ").strip()
                    index = int(choice) - 1
                    
                    if 0 <= index < len(cameras):
                        selected_camera = cameras[index]
                        self.config['camera_id'] = selected_camera['id']
                        
                        print(f"✅ 已选择摄像头: {selected_camera.get('name')} ({selected_camera['id']})")
                        return True
                    else:
                        print("❌ 无效的选择，请重新输入")
                        
                except ValueError:
                    print("❌ 请输入有效的数字")
                except KeyboardInterrupt:
                    print("\n👋 取消选择")
                    return False
                    
        except Exception as e:
            log_error(f"选择摄像头失败: {e}", "SEE")
            print(f"❌ 选择摄像头失败: {e}")
            return False
    
    def take_photo(self, camera_id: str) -> Dict[str, Any]:
        """拍照"""
        try:
            print(f"📸 正在拍照 (摄像头: {camera_id})...")
            
            # 检查摄像头可用性
            availability = check_camera_available(camera_id)
            if availability['status'] == 'success' and not availability['data']['available']:
                return {
                    'success': False,
                    'error': f"摄像头 {camera_id} 被其他进程占用"
                }
            
            # 锁定摄像头
            lock_result = lock_camera(camera_id)
            if lock_result['status'] != 'success':
                return {
                    'success': False,
                    'error': f"无法锁定摄像头: {lock_result['message']}"
                }
            
            try:
                # 导入拍照控制器
                from src.processors.photo_controller import take_photo_by_id
                
                # 执行拍照
                photo_result = take_photo_by_id(camera_id)
                
                if photo_result['status'] == 'success':
                    print("✅ 拍照成功")
                    return {
                        'success': True,
                        'filename': photo_result['data']['filename'],
                        'file_path': photo_result['data']['file_path'],
                        'file_size': photo_result['data']['file_size']
                    }
                else:
                    return {
                        'success': False,
                        'error': photo_result['message']
                    }
            
            finally:
                # 释放摄像头
                release_camera(camera_id)
                
        except Exception as e:
            log_error(f"拍照失败: {e}", "SEE")
            return {
                'success': False,
                'error': f"拍照异常: {str(e)}"
            }
    
    def crop_images(self, image_path: str) -> Dict[str, Any]:
        """裁剪图片"""
        try:
            print("✂️  正在裁剪图片...")
            
            # 导入图片裁剪器
            from src.processors.image_cutter import process_image
            
            # 执行裁剪
            success = process_image(image_path)
            
            if success:
                print("✅ 图片裁剪完成")
                
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
            log_error(f"裁剪图片失败: {e}", "SEE")
            return {
                'success': False,
                'error': f"裁剪异常: {str(e)}"
            }
    
    def recognize_images(self, cropped_images: List[str]) -> Dict[str, Any]:
        """识别图片"""
        try:
            print("🧠 正在识别扑克牌...")
            
            recognition_results = {}
            total_images = len(cropped_images)
            successful_count = 0
            
            for i, image_path in enumerate(cropped_images):
                image_name = Path(image_path).name
                position = self._extract_position_from_filename(image_name)
                
                print(f"   ({i+1}/{total_images}) 识别 {position}...", end=' ')
                
                # 根据配置选择识别方法
                if self.config['recognition_mode'] == 'yolo_only':
                    result = self._recognize_with_yolo(image_path)
                elif self.config['recognition_mode'] == 'ocr_only':
                    result = self._recognize_with_ocr(image_path)
                else:  # hybrid
                    result = self._recognize_hybrid(image_path)
                
                if result['success']:
                    print(f"✅ {result['display_name']} (置信度: {result.get('confidence', 0):.3f})")
                    successful_count += 1
                else:
                    print(f"❌ {result.get('error', '未知错误')}")
                
                recognition_results[position] = result
            
            print(f"🎯 识别完成: {successful_count}/{total_images} 成功")
            
            return {
                'success': True,
                'results': recognition_results,
                'total_count': total_images,
                'successful_count': successful_count,
                'success_rate': round(successful_count / total_images * 100, 1) if total_images > 0 else 0
            }
            
        except Exception as e:
            log_error(f"识别图片失败: {e}", "SEE")
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
                    'display_name': result['display_name'],
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
            # 先尝试使用PaddleOCR
            try:
                from src.processors.poker_paddle_ocr import recognize_poker_character
                
                result = recognize_poker_character(image_path)
                
                if result['success']:
                    character = result['character']
                    return {
                        'success': True,
                        'suit': '',  # OCR只能识别点数
                        'rank': character,
                        'display_name': character,
                        'confidence': result['confidence'],
                        'method': 'paddle_ocr'
                    }
                else:
                    raise Exception(result['error'])
                    
            except ImportError:
                # 如果PaddleOCR不可用，使用EasyOCR
                from src.processors.poker_ocr import recognize_poker_character
                
                result = recognize_poker_character(image_path)
                
                if result['success']:
                    character = result['character']
                    return {
                        'success': True,
                        'suit': '',
                        'rank': character,
                        'display_name': character,
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
                # 如果YOLO也成功，优先使用YOLO的花色信息
                if yolo_result['success']:
                    return {
                        'success': True,
                        'suit': yolo_result['suit'],
                        'rank': ocr_result['rank'],  # 使用OCR的点数
                        'display_name': f"{yolo_result.get('suit_symbol', '')}{ocr_result['rank']}",
                        'confidence': (yolo_result.get('confidence', 0) + ocr_result.get('confidence', 0)) / 2,
                        'method': 'hybrid_combined'
                    }
                else:
                    ocr_result['method'] = 'hybrid_ocr'
                    return ocr_result
            
            # 如果都失败，返回YOLO结果（即使失败）
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
            # 文件名格式: camera_001_zhuang_1.png 或 camera_001_zhuang_1_left.png
            parts = filename.split('_')
            if len(parts) >= 4:
                return f"{parts[2]}_{parts[3]}"  # zhuang_1
            return "unknown"
        except:
            return "unknown"
    
    def display_recognition_results(self, results: Dict[str, Any]):
        """显示识别结果"""
        try:
            print("\n📊 识别结果详情:")
            print("=" * 60)
            
            positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
            position_names = {
                'zhuang_1': '庄家1', 'zhuang_2': '庄家2', 'zhuang_3': '庄家3',
                'xian_1': '闲家1', 'xian_2': '闲家2', 'xian_3': '闲家3'
            }
            
            for position in positions:
                if position in results['results']:
                    result = results['results'][position]
                    position_name = position_names.get(position, position)
                    
                    if result['success']:
                        display_name = result.get('display_name', f"{result.get('suit', '')}{result.get('rank', '')}")
                        confidence = result.get('confidence', 0)
                        method = result.get('method', 'unknown')
                        
                        print(f"   {position_name:>6}: ✅ {display_name:>4} (置信度: {confidence:.3f}, 方法: {method})")
                    else:
                        error = result.get('error', '未知错误')
                        method = result.get('method', 'unknown')
                        print(f"   {position_name:>6}: ❌ 识别失败 ({method}: {error})")
                else:
                    print(f"   {position_names.get(position, position):>6}: ⚪ 未处理")
            
            print("=" * 60)
            print(f"总计: {results['successful_count']}/{results['total_count']} 成功 "
                  f"(成功率: {results['success_rate']}%)")
            
        except Exception as e:
            log_error(f"显示识别结果失败: {e}", "SEE")
    
    def update_statistics(self, success: bool, duration: float):
        """更新统计信息"""
        self.stats['total_recognitions'] += 1
        if success:
            self.stats['successful_recognitions'] += 1
        else:
            self.stats['failed_recognitions'] += 1
        
        self.stats['recognition_times'].append(duration)
        
        # 只保留最近100次的时间记录
        if len(self.stats['recognition_times']) > 100:
            self.stats['recognition_times'] = self.stats['recognition_times'][-100:]
    
    def display_statistics(self):
        """显示统计信息"""
        try:
            print("\n📈 系统统计信息:")
            print("=" * 40)
            
            total = self.stats['total_recognitions']
            success = self.stats['successful_recognitions']
            failed = self.stats['failed_recognitions']
            
            print(f"总识别次数: {total}")
            print(f"成功次数: {success}")
            print(f"失败次数: {failed}")
            
            if total > 0:
                success_rate = (success / total) * 100
                print(f"成功率: {success_rate:.1f}%")
            
            # 显示时间统计
            times = self.stats['recognition_times']
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                print(f"平均识别时间: {avg_time:.2f}秒")
                print(f"最快识别时间: {min_time:.2f}秒")
                print(f"最慢识别时间: {max_time:.2f}秒")
            
            print("=" * 40)
            
        except Exception as e:
            log_error(f"显示统计信息失败: {e}", "SEE")
    
    def run_single_recognition(self) -> bool:
        """运行单次识别"""
        try:
            if not self.config['camera_id']:
                print("❌ 未选择摄像头")
                return False
            
            camera_id = self.config['camera_id']
            
            print(f"\n🎯 开始识别流程 (摄像头: {camera_id})")
            print("-" * 50)
            
            start_time = time.time()
            
            # 1. 拍照
            photo_result = self.take_photo(camera_id)
            if not photo_result['success']:
                print(f"❌ 拍照失败: {photo_result['error']}")
                self.update_statistics(False, time.time() - start_time)
                return False
            
            # 2. 裁剪图片
            crop_result = self.crop_images(photo_result['file_path'])
            if not crop_result['success']:
                print(f"❌ 裁剪失败: {crop_result['error']}")
                self.update_statistics(False, time.time() - start_time)
                return False
            
            # 3. 识别图片
            recognition_result = self.recognize_images(crop_result['cropped_images'])
            if not recognition_result['success']:
                print(f"❌ 识别失败: {recognition_result['error']}")
                self.update_statistics(False, time.time() - start_time)
                return False
            
            # 4. 显示结果
            self.display_recognition_results(recognition_result)
            
            duration = time.time() - start_time
            success = recognition_result['successful_count'] > 0
            
            self.update_statistics(success, duration)
            
            print(f"⏱️  总耗时: {duration:.2f}秒")
            
            return True
            
        except Exception as e:
            log_error(f"单次识别失败: {e}", "SEE")
            print(f"❌ 识别过程异常: {e}")
            return False
    
    def run_auto_mode(self):
        """运行自动模式"""
        try:
            print(f"\n🔄 自动识别模式 (间隔: {self.config['loop_interval']}秒)")
            print("按 Ctrl+C 停止自动模式")
            print("-" * 50)
            
            cycle_count = 0
            
            while not self.shutdown_requested:
                cycle_count += 1
                print(f"\n🔄 第 {cycle_count} 轮识别:")
                
                # 执行识别
                success = self.run_single_recognition()
                
                if success:
                    print("✅ 本轮识别完成")
                else:
                    print("❌ 本轮识别失败")
                
                # 更新心跳
                update_heartbeat()
                
                # 等待下次循环
                if not self.shutdown_requested:
                    print(f"⏳ 等待 {self.config['loop_interval']} 秒...")
                    time.sleep(self.config['loop_interval'])
                    
        except KeyboardInterrupt:
            print("\n⏹️  自动模式已停止")
        except Exception as e:
            log_error(f"自动模式异常: {e}", "SEE")
            print(f"❌ 自动模式异常: {e}")
    
    def interactive_mode(self):
        """交互模式"""
        try:
            print("\n🎮 交互模式")
            print("命令列表:")
            print("  1 或 r  - 执行单次识别")
            print("  2 或 a  - 切换到自动模式")
            print("  3 或 s  - 显示统计信息")
            print("  4 或 c  - 更换摄像头")
            print("  5 或 q  - 退出程序")
            print("-" * 40)
            
            while not self.shutdown_requested:
                try:
                    cmd = input("\n请输入命令: ").strip().lower()
                    
                    if cmd in ['1', 'r']:
                        self.run_single_recognition()
                    elif cmd in ['2', 'a']:
                        self.run_auto_mode()
                    elif cmd in ['3', 's']:
                        self.display_statistics()
                    elif cmd in ['4', 'c']:
                        if self.select_camera_interactive():
                            print("✅ 摄像头更换成功")
                    elif cmd in ['5', 'q']:
                        break
                    else:
                        print("❌ 未知命令，请重新输入")
                        
                except KeyboardInterrupt:
                    print("\n👋 退出交互模式")
                    break
                    
        except Exception as e:
            log_error(f"交互模式异常: {e}", "SEE")
            print(f"❌ 交互模式异常: {e}")
    
    def shutdown_system(self):
        """关闭系统"""
        try:
            print("\n🔄 正在关闭识别测试系统...")
            
            # 注销进程
            unregister_result = unregister_process()
            if unregister_result['status'] == 'success':
                print("✅ 进程注销成功")
            
            # 显示最终统计
            if self.stats['total_recognitions'] > 0:
                print("\n📊 最终统计:")
                self.display_statistics()
            
            print("👋 识别测试系统已安全关闭")
            
        except Exception as e:
            log_error(f"关闭系统失败: {e}", "SEE")
            print(f"❌ 关闭系统时出错: {e}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='扑克识别测试系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python see.py                              # 交互模式
  python see.py --camera 001                # 指定摄像头
  python see.py --camera 001 --auto         # 自动循环识别
  python see.py --camera 001 --mode yolo    # 使用YOLO算法
  python see.py --camera 001 --once         # 执行一次识别后退出
        """
    )
    
    parser.add_argument('--camera', '--camera-id', dest='camera_id',
                       help='指定摄像头ID')
    parser.add_argument('--mode', choices=['yolo_only', 'ocr_only', 'hybrid'],
                       default='hybrid', help='识别模式 (默认: hybrid)')
    parser.add_argument('--auto', action='store_true',
                       help='自动循环识别模式')
    parser.add_argument('--interval', type=int, default=5,
                       help='自动模式循环间隔(秒) (默认: 5)')
    parser.add_argument('--once', action='store_true',
                       help='执行一次识别后退出')
    parser.add_argument('--no-debug-images', action='store_true',
                       help='不保存调试图片')
    parser.add_argument('--hide-confidence', action='store_true',
                       help='隐藏置信度信息')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析参数
        args = parse_arguments()
        
        # 创建识别测试系统实例
        system = SeeSystem()
        
        # 更新配置
        system.config.update({
            'camera_id': args.camera_id,
            'recognition_mode': args.mode,
            'auto_mode': args.auto,
            'loop_interval': args.interval,
            'save_debug_images': not args.no_debug_images,
            'show_confidence': not args.hide_confidence
        })
        
        # 初始化系统
        if not system.initialize_system():
            return 1
        
        # 选择摄像头
        if not system.config['camera_id']:
            if not system.select_camera_interactive():
                print("❌ 未选择摄像头，程序退出")
                return 1
        else:
            # 验证指定的摄像头
            camera_result = get_camera_by_id(system.config['camera_id'])
            if camera_result['status'] != 'success':
                print(f"❌ 摄像头 {system.config['camera_id']} 不存在")
                return 1
            print(f"✅ 使用摄像头: {camera_result['data']['camera'].get('name')} ({system.config['camera_id']})")
        
        # 设置信号处理
        def signal_handler(signum, frame):
            print(f"\n📡 接收到信号 {signum}，准备退出...")
            system.shutdown_requested = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 根据参数选择运行模式
        if args.once:
            # 单次识别模式
            print(f"🎯 单次识别模式")
            success = system.run_single_recognition()
            system.display_statistics()
            return 0 if success else 1
        elif args.auto:
            # 自动循环模式
            system.run_auto_mode()
        else:
            # 交互模式
            system.interactive_mode()
        
        # 关闭系统
        system.shutdown_system()
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())