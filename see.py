#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克识别系统完整测试程序 - see.py (增强版)
功能:
1. 使用统一配置加载器
2. 拍照
3. 裁剪图片
4. 混合识别扑克牌 (YOLO + OCR + OpenCV)
5. 结果合并和分析
6. 展示详细结果
"""

import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# 设置项目路径
def setup_project_paths():
    """设置项目路径"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent
    
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

PROJECT_ROOT = setup_project_paths()

class EnhancedPokerRecognitionTester:
    """增强版扑克识别系统测试器"""
    
    def __init__(self):
        """初始化测试器"""
        self.selected_camera_id = None
        self.camera_config = None
        
        # 统计信息
        self.stats = {
            'total_tests': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'start_time': time.time(),
            'recognition_method_stats': {
                'yolo_only': 0,
                'hybrid': 0,
                'ocr_only': 0,
                'opencv_only': 0,
                'failed': 0
            }
        }
        
        print("🎮 增强版扑克识别系统测试器初始化完成")
    
    def initialize(self) -> bool:
        """初始化系统"""
        try:
            print("🚀 初始化扑克识别测试系统...")
            print("=" * 60)
            
            # 检查各个模块的可用性
            self._check_module_availability()
            
            return True
            
        except Exception as e:
            print(f"❌ 系统初始化失败: {e}")
            return False
    
    def _check_module_availability(self):
        """检查模块可用性"""
        print("🔍 检查模块可用性:")
        
        # 检查配置加载器
        try:
            from src.core.config_manager import get_all_cameras
            config_result = get_all_cameras()
            print(f"   配置管理器: {'✅ 可用' if config_result['status'] == 'success' else '⚠️  有问题'}")
            if config_result['status'] != 'success':
                print(f"      问题: {config_result.get('message', '未知')}")
        except ImportError as e:
            print(f"   配置管理器: ❌ 导入失败 - {e}")
        
        # 检查拍照控制器
        try:
            from src.processors.photo_controller import take_photo_by_id
            print("   拍照控制器: ✅ 可用")
        except ImportError as e:
            print(f"   拍照控制器: ❌ 导入失败 - {e}")
        
        # 检查图片裁剪器
        try:
            from src.processors.image_cutter import process_image
            print("   图片裁剪器: ✅ 可用")
        except ImportError as e:
            print(f"   图片裁剪器: ❌ 导入失败 - {e}")
        
        # 检查混合识别器
        try:
            from src.processors.poker_recognizer import recognize_poker_card
            print("   扑克识别器: ✅ 可用")
        except ImportError as e:
            print(f"   扑克识别器: ❌ 导入失败 - {e}")
    
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
            enabled_cameras = [c for c in cameras if c.get('enabled', True)]
            if not enabled_cameras:
                print("❌ 没有找到启用的摄像头")
                return False
            
            print(f"✅ 找到 {len(enabled_cameras)} 个启用的摄像头:")
            for i, camera in enumerate(enabled_cameras):
                print(f"   {i+1}. {camera['name']} (ID: {camera['id']}) - IP: {camera['ip']}")
            
            # 选择第一个摄像头进行测试
            self.selected_camera_id = enabled_cameras[0]['id']
            selected_camera = enabled_cameras[0]
            
            print(f"\n🎯 选择摄像头进行测试:")
            print(f"   ID: {selected_camera['id']}")
            print(f"   名称: {selected_camera['name']}")
            print(f"   IP: {selected_camera['ip']}")
            print(f"   用户名: {selected_camera['username']}")
            print(f"   端口: {selected_camera['port']}")
            print(f"   流路径: {selected_camera['stream_path']}")
            
            # 检查标记位置
            mark_positions = selected_camera.get('mark_positions', {})
            marked_positions = [pos for pos, data in mark_positions.items() if data.get('marked', False)]
            print(f"   已标记位置: {len(marked_positions)} 个 ({', '.join(marked_positions)})")
            
            return True
            
        except Exception as e:
            print(f"❌ 读取摄像头配置异常: {e}")
            return False
    
    def step2_take_photo(self) -> Dict[str, Any]:
        """步骤2: 拍照"""
        try:
            print("\n📸 步骤2: 拍照")
            print("-" * 40)
            
            if not self.selected_camera_id:
                print("❌ 未选择摄像头")
                return {'success': False, 'error': '未选择摄像头'}
            
            from src.processors.photo_controller import take_photo_by_id
            
            print(f"正在拍照 (摄像头: {self.selected_camera_id})...")
            
            start_time = time.time()
            photo_result = take_photo_by_id(self.selected_camera_id)
            duration = time.time() - start_time
            
            if photo_result['status'] == 'success':
                data = photo_result['data']
                print("✅ 拍照成功!")
                print(f"   文件名: {data['filename']}")
                print(f"   文件路径: {data['file_path']}")
                print(f"   文件大小: {data['file_size']} bytes ({data['file_size']/1024:.1f} KB)")
                print(f"   耗时: {duration:.2f} 秒")
                print(f"   图片URL: {data['image_url']}")
                
                # 验证文件是否存在
                file_path = Path(data['file_path'])
                if file_path.exists():
                    actual_size = file_path.stat().st_size
                    print(f"   文件验证: ✅ 存在，实际大小 {actual_size} bytes")
                    return {
                        'success': True,
                        'file_path': str(file_path),
                        'filename': data['filename'],
                        'file_size': actual_size
                    }
                else:
                    print("   文件验证: ❌ 文件不存在")
                    return {'success': False, 'error': '拍照文件不存在'}
            else:
                print(f"❌ 拍照失败: {photo_result['message']}")
                return {'success': False, 'error': photo_result['message']}
                
        except Exception as e:
            print(f"❌ 拍照异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def step3_crop_images(self, image_path: str) -> Dict[str, Any]:
        """步骤3: 裁剪图片"""
        try:
            print("\n✂️  步骤3: 裁剪图片")
            print("-" * 40)
            
            from src.processors.image_cutter import process_image
            
            print(f"正在裁剪图片: {Path(image_path).name}")
            
            start_time = time.time()
            success = process_image(image_path)
            duration = time.time() - start_time
            
            if success:
                print(f"✅ 图片裁剪成功! (耗时: {duration:.2f} 秒)")
                
                # 查找裁剪后的图片
                image_file = Path(image_path)
                cut_dir = image_file.parent / "cut"
                
                if cut_dir.exists():
                    pattern = f"{image_file.stem}_*.png"
                    all_files = list(cut_dir.glob(pattern))
                    
                    # 分离主图片和左上角图片
                    main_files = [f for f in all_files if not f.name.endswith('_left.png')]
                    left_files = [f for f in all_files if f.name.endswith('_left.png')]
                    
                    main_files.sort(key=lambda x: x.name)
                    left_files.sort(key=lambda x: x.name)
                    
                    print(f"   生成主图片: {len(main_files)} 个")
                    for i, crop_file in enumerate(main_files):
                        file_size = crop_file.stat().st_size
                        print(f"   {i+1}. {crop_file.name} ({file_size} bytes)")
                    
                    print(f"   生成左上角图片: {len(left_files)} 个")
                    
                    return {
                        'success': True,
                        'main_files': [str(f) for f in main_files],
                        'left_files': [str(f) for f in left_files],
                        'cut_dir': str(cut_dir),
                        'total_count': len(all_files)
                    }
                else:
                    print("❌ 裁剪目录不存在")
                    return {'success': False, 'error': '裁剪目录不存在'}
            else:
                print(f"❌ 图片裁剪失败 (耗时: {duration:.2f} 秒)")
                return {'success': False, 'error': '图片裁剪失败'}
                
        except Exception as e:
            print(f"❌ 裁剪图片异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def step4_recognize_cards(self, main_files: List[str], left_files: List[str]) -> Dict[str, Any]:
        """步骤4: 识别扑克牌"""
        try:
            print("\n🧠 步骤4: 识别扑克牌")
            print("-" * 50)
            
            from src.processors.poker_recognizer import recognize_poker_card
            
            position_results = {}
            successful_count = 0
            total_count = len(main_files)
            
            print(f"开始识别 {total_count} 个图片区域...")
            
            for i, main_image_path in enumerate(main_files):
                main_image_file = Path(main_image_path)
                position = self._extract_position_from_filename(main_image_file.name)
                
                print(f"\n   ({i+1}/{total_count}) 识别位置: {position}")
                print(f"   图片: {main_image_file.name}")
                
                # 使用YOLO识别器
                result = recognize_poker_card(main_image_path)
                
                if result['success']:
                    print(f"   ✅ {result['display_name']} (置信度: {result.get('confidence', 0):.3f})")
                    successful_count += 1
                    self.stats['recognition_method_stats']['yolo_only'] += 1
                else:
                    print(f"   ❌ 识别失败: {result.get('error', '未知错误')}")
                    self.stats['recognition_method_stats']['failed'] += 1
                
                position_results[position] = result
            
            success_rate = (successful_count / total_count * 100) if total_count > 0 else 0
            
            print(f"\n🎯 识别完成:")
            print(f"   成功: {successful_count}/{total_count}")
            print(f"   成功率: {success_rate:.1f}%")
            
            return {
                'success': True,
                'position_results': position_results,
                'successful_count': successful_count,
                'total_count': total_count,
                'success_rate': success_rate
            }
            
        except Exception as e:
            print(f"❌ 识别异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def step5_display_results(self, position_results: Dict[str, Dict[str, Any]]):
        """步骤5: 显示识别结果"""
        try:
            print("\n📊 步骤5: 识别结果展示")
            print("=" * 60)
            
            # 位置名称映射
            position_names = {
                'zhuang_1': '庄家1', 'zhuang_2': '庄家2', 'zhuang_3': '庄家3',
                'xian_1': '闲家1', 'xian_2': '闲家2', 'xian_3': '闲家3'
            }
            
            print("🎴 各位置识别详情:")
            print("-" * 60)
            
            # 按位置顺序显示
            standard_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
            
            for position in standard_positions:
                position_name = position_names.get(position, position)
                
                if position in position_results:
                    result = position_results[position]
                    
                    if result.get('success', False):
                        display_name = result.get('display_name', 'N/A')
                        confidence = result.get('confidence', 0)
                        
                        status_icon = "✅"
                        status_text = f"{display_name} (置信度: {confidence:.3f})"
                        
                        # 显示详细信息
                        if 'suit_name' in result and 'rank' in result:
                            status_text += f" - {result['suit_name']} {result['rank']}"
                    else:
                        status_icon = "❌"
                        error = result.get('error', '未知错误')
                        status_text = f"识别失败 ({error})"
                else:
                    status_icon = "⚪"
                    status_text = "未处理"
                
                print(f"   {position_name:>6}: {status_icon} {status_text}")
            
            # 显示汇总统计
            successful_positions = sum(1 for result in position_results.values() if result.get('success', False))
            total_positions = len(position_results)
            success_rate = (successful_positions / total_positions * 100) if total_positions > 0 else 0
            
            print("-" * 60)
            print(f"📈 汇总统计:")
            print(f"   成功位置: {successful_positions}/{total_positions}")
            print(f"   成功率: {success_rate:.1f}%")
            
            # 显示识别的卡牌
            recognized_cards = []
            for result in position_results.values():
                if result.get('success', False) and result.get('display_name'):
                    recognized_cards.append(result['display_name'])
            
            if recognized_cards:
                print(f"   识别卡牌: {', '.join(recognized_cards)}")
            
        except Exception as e:
            print(f"❌ 显示结果异常: {e}")
    
    def _extract_position_from_filename(self, filename: str) -> str:
        """从文件名提取位置信息"""
        try:
            # 文件名格式: camera_001_zhuang_1.png
            parts = filename.split('_')
            if len(parts) >= 4:
                return f"{parts[2]}_{parts[3].split('.')[0]}"  # zhuang_1
            return "unknown"
        except:
            return "unknown"
    
    def run_complete_test(self) -> bool:
        """运行完整测试流程"""
        try:
            print(f"\n🎯 开始完整识别测试流程")
            print(f"摄像头: {self.selected_camera_id}")
            print("=" * 60)
            
            self.stats['total_tests'] += 1
            start_time = time.time()
            
            # 步骤2: 拍照
            photo_result = self.step2_take_photo()
            if not photo_result['success']:
                self.stats['failed_tests'] += 1
                return False
            
            # 步骤3: 裁剪
            crop_result = self.step3_crop_images(photo_result['file_path'])
            if not crop_result['success']:
                self.stats['failed_tests'] += 1
                return False
            
            # 步骤4: 识别
            recognition_result = self.step4_recognize_cards(
                crop_result['main_files'], 
                crop_result['left_files']
            )
            if not recognition_result['success']:
                self.stats['failed_tests'] += 1
                return False
            
            # 步骤5: 显示结果
            self.step5_display_results(recognition_result['position_results'])
            
            duration = time.time() - start_time
            print(f"\n⏱️  总耗时: {duration:.2f} 秒")
            
            self.stats['successful_tests'] += 1
            return True
            
        except Exception as e:
            print(f"❌ 完整测试异常: {e}")
            self.stats['failed_tests'] += 1
            return False
    
    def display_statistics(self):
        """显示统计信息"""
        try:
            print("\n📈 测试统计信息")
            print("=" * 40)
            
            total_time = time.time() - self.stats['start_time']
            
            print(f"总测试次数: {self.stats['total_tests']}")
            print(f"成功次数: {self.stats['successful_tests']}")
            print(f"失败次数: {self.stats['failed_tests']}")
            
            if self.stats['total_tests'] > 0:
                success_rate = (self.stats['successful_tests'] / self.stats['total_tests']) * 100
                print(f"成功率: {success_rate:.1f}%")
            
            print(f"总运行时间: {total_time:.1f} 秒")
            
            # 显示识别方法统计
            method_stats = self.stats['recognition_method_stats']
            total_recognitions = sum(method_stats.values())
            if total_recognitions > 0:
                print(f"\n识别方法统计 (总计: {total_recognitions} 次):")
                for method, count in method_stats.items():
                    if count > 0:
                        percentage = (count / total_recognitions) * 100
                        print(f"  {method}: {count} 次 ({percentage:.1f}%)")
            
            print("=" * 40)
            
        except Exception as e:
            print(f"❌ 统计信息显示异常: {e}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='扑克识别系统完整测试程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python see.py                    # 交互模式，单次测试
  python see.py --auto             # 自动循环测试
  python see.py --count 5          # 连续测试5次
  python see.py --camera 002       # 指定摄像头ID
        """
    )
    
    parser.add_argument('--camera', '--camera-id', dest='camera_id',
                       help='指定摄像头ID')
    parser.add_argument('--auto', action='store_true',
                       help='自动循环测试模式')
    parser.add_argument('--count', type=int, default=1,
                       help='测试次数 (默认: 1)')
    parser.add_argument('--interval', type=int, default=5,
                       help='自动模式测试间隔(秒) (默认: 5)')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        args = parse_arguments()
        
        # 创建测试器
        tester = EnhancedPokerRecognitionTester()
        
        # 初始化系统
        if not tester.initialize():
            return 1
        
        # 步骤1: 读取摄像头配置
        if not tester.step1_load_camera_config():
            return 1
        
        # 如果指定了摄像头ID，使用指定的摄像头
        if args.camera_id:
            from src.core.config_manager import get_camera_by_id
            camera_result = get_camera_by_id(args.camera_id)
            if camera_result['status'] == 'success':
                tester.selected_camera_id = args.camera_id
                print(f"✅ 使用指定摄像头: {args.camera_id}")
            else:
                print(f"❌ 指定的摄像头 {args.camera_id} 不存在")
                return 1
        
        try:
            if args.auto:
                # 自动循环模式
                print(f"\n🔄 自动循环测试模式 (间隔: {args.interval}秒)")
                print("按 Ctrl+C 停止测试")
                
                test_count = 0
                while True:
                    test_count += 1
                    print(f"\n🔄 第 {test_count} 次测试:")
                    
                    success = tester.run_complete_test()
                    
                    if success:
                        print("✅ 本次测试完成")
                    else:
                        print("❌ 本次测试失败")
                    
                    print(f"⏳ 等待 {args.interval} 秒...")
                    time.sleep(args.interval)
                    
            else:
                # 指定次数测试
                for i in range(args.count):
                    if args.count > 1:
                        print(f"\n🔄 第 {i+1}/{args.count} 次测试:")
                    
                    success = tester.run_complete_test()
                    
                    if success:
                        print("✅ 测试完成")
                    else:
                        print("❌ 测试失败")
                    
                    # 如果不是最后一次测试，等待一下
                    if i < args.count - 1:
                        time.sleep(2)
        
        except KeyboardInterrupt:
            print("\n⏹️  测试被用户中断")
        
        # 显示最终统计
        if tester.stats['total_tests'] > 0:
            tester.display_statistics()
        
        print("👋 扑克识别测试系统已关闭")
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())