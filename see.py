#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克识别系统完整测试程序 - see.py (增强版混合识别)
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
        
        # 混合识别器配置
        self.recognition_config = {
            # YOLO配置
            'yolo_enabled': True,
            'yolo_confidence_threshold': 0.3,
            'yolo_high_confidence_threshold': 0.8,
            
            # OCR配置
            'ocr_enabled': True,
            'ocr_confidence_threshold': 0.3,
            'ocr_prefer_paddle': True,
            
            # OpenCV花色识别配置
            'opencv_suit_enabled': True,
            'opencv_suit_confidence_threshold': 0.4,
            
            # 融合策略
            'fusion_strategy': 'weighted',  # weighted, voting, priority
            'min_confidence_for_result': 0.3,
            'enable_result_validation': True,
            
            # 调试配置
            'debug_mode': False,
            'save_intermediate_results': False
        }
        
        # 统计信息
        self.stats = {
            'total_tests': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'start_time': time.time(),
            'recognition_method_stats': {
                'yolo_complete': 0,      # YOLO完整识别
                'hybrid_combined': 0,    # 混合组合识别
                'ocr_only': 0,          # 仅OCR识别
                'opencv_only': 0,       # 仅OpenCV识别
                'failed': 0             # 识别失败
            },
            'fusion_strategy_stats': {
                'weighted': 0,
                'voting': 0,
                'priority': 0
            }
        }
        
        print("🎮 增强版扑克识别系统测试器 (混合识别) 初始化完成")
    
    def initialize(self) -> bool:
        """初始化系统"""
        try:
            print("🚀 初始化扑克混合识别测试系统...")
            print("=" * 60)
            
            # 检查各个模块的可用性
            self._check_module_availability()
            
            # 检查混合识别器能力
            self._check_hybrid_recognition_capabilities()
            
            return True
            
        except Exception as e:
            print(f"❌ 系统初始化失败: {e}")
            return False
    
    def _check_module_availability(self):
        """检查模块可用性"""
        print("🔍 检查核心模块可用性:")
        
        # 检查配置管理器
        try:
            from src.core.config_manager import get_all_cameras
            config_result = get_all_cameras()
            print(f"   配置管理器: {'✅ 可用' if config_result['status'] == 'success' else '⚠️  有问题'}")
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
        
        # 检查结果合并器
        try:
            from src.processors.poker_result_merger import merge_poker_recognition_results
            print("   结果合并器: ✅ 可用")
        except ImportError as e:
            print(f"   结果合并器: ❌ 导入失败 - {e}")
    
    def _check_hybrid_recognition_capabilities(self):
        """检查混合识别器能力"""
        try:
            from src.processors.poker_hybrid_recognizer import get_hybrid_recognition_capabilities
            
            capabilities = get_hybrid_recognition_capabilities()
            
            print("\n🧠 混合识别器能力检查:")
            available_methods = capabilities.get('available_methods', {})
            
            for method, available in available_methods.items():
                status = "✅ 可用" if available else "❌ 不可用" 
                method_name = {
                    'yolo': 'YOLO检测器',
                    'ocr_easy': 'EasyOCR',
                    'ocr_paddle': 'PaddleOCR', 
                    'opencv_suit': 'OpenCV花色识别'
                }.get(method, method)
                print(f"   {method_name}: {status}")
            
            # 检查识别能力
            caps = capabilities.get('capabilities', {})
            print(f"\n🎯 识别能力:")
            print(f"   完整识别: {'✅' if caps.get('complete_recognition') else '❌'}")
            print(f"   点数识别: {'✅' if caps.get('rank_recognition') else '❌'}")
            print(f"   花色识别: {'✅' if caps.get('suit_recognition') else '❌'}")
            print(f"   混合融合: {'✅' if caps.get('hybrid_fusion') else '❌'}")
            
        except ImportError as e:
            print(f"\n❌ 混合识别器导入失败: {e}")
        except Exception as e:
            print(f"\n⚠️  混合识别器检查异常: {e}")
    
    def step1_load_camera_config(self) -> bool:
        """步骤1: 读取摄像头配置"""
        try:
            print("\n📷 步骤1: 读取摄像头配置")
            print("-" * 50)
            
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
    
    def step4_recognize_cards_hybrid(self, main_files: List[str], left_files: List[str]) -> Dict[str, Any]:
        """步骤4: 混合识别扑克牌"""
        try:
            print("\n🧠 步骤4: 混合识别扑克牌")
            print("-" * 50)
            
            from src.processors.poker_hybrid_recognizer import recognize_poker_card_hybrid
            
            position_results = {}
            successful_count = 0
            total_count = len(main_files)
            
            # 创建主图片和左上角图片的对应关系
            main_to_left_map = self._create_image_mapping(main_files, left_files)
            
            print(f"开始混合识别 {total_count} 个图片区域...")
            print(f"使用融合策略: {self.recognition_config['fusion_strategy']}")
            
            for i, main_image_path in enumerate(main_files):
                main_image_file = Path(main_image_path)
                position = self._extract_position_from_filename(main_image_file.name)
                left_image_path = main_to_left_map.get(main_image_path)
                
                print(f"\n   ({i+1}/{total_count}) 识别位置: {position}")
                print(f"   主图片: {main_image_file.name}")
                if left_image_path:
                    print(f"   左上角: {Path(left_image_path).name}")
                
                # 使用混合识别器
                start_time = time.time()
                result = recognize_poker_card_hybrid(
                    main_image_path, 
                    left_image_path,
                    config=self.recognition_config
                )
                duration = time.time() - start_time
                
                if result['success']:
                    print(f"   ✅ {result['display_name']} (置信度: {result.get('confidence', 0):.3f})")
                    print(f"      方法: {', '.join(result.get('hybrid_info', {}).get('used_methods', []))}")
                    print(f"      耗时: {duration:.3f}秒")
                    
                    successful_count += 1
                    
                    # 统计识别方法
                    self._update_method_stats(result)
                    
                    # 显示验证警告
                    if result.get('validation_warnings'):
                        print(f"      ⚠️  验证警告: {', '.join(result['validation_warnings'])}")
                else:
                    print(f"   ❌ 识别失败: {result.get('error', '未知错误')}")
                    print(f"      耗时: {duration:.3f}秒")
                    self.stats['recognition_method_stats']['failed'] += 1
                
                position_results[position] = result
            
            success_rate = (successful_count / total_count * 100) if total_count > 0 else 0
            
            print(f"\n🎯 混合识别完成:")
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
            print(f"❌ 混合识别异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def step5_merge_results(self, position_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """步骤5: 合并识别结果"""
        try:
            print("\n📊 步骤5: 合并识别结果")
            print("-" * 50)
            
            from src.processors.poker_result_merger import merge_poker_recognition_results
            
            # 配置合并器
            merger_config = {
                'min_confidence_threshold': 0.3,
                'high_confidence_threshold': 0.8,
                'conflict_resolution_strategy': 'highest_confidence',
                'enable_consistency_check': True,
                'quality_assessment_enabled': True,
                'duplicate_detection_enabled': True,
                'include_metadata': True,
                'include_quality_metrics': True,
                'include_debug_info': self.recognition_config['debug_mode']
            }
            
            metadata = {
                'test_mode': True,
                'fusion_strategy': self.recognition_config['fusion_strategy'],
                'recognition_methods_used': list(self.stats['recognition_method_stats'].keys())
            }
            
            start_time = time.time()
            merge_result = merge_poker_recognition_results(
                position_results,
                camera_id=self.selected_camera_id,
                metadata=metadata,
                config=merger_config
            )
            duration = time.time() - start_time
            
            if merge_result['success']:
                print(f"✅ 结果合并成功! (耗时: {duration:.3f}秒)")
                
                # 显示合并统计
                summary = merge_result.get('summary', {})
                print(f"   总位置: {summary.get('total_positions', 0)}")
                print(f"   成功位置: {summary.get('successful_positions', 0)}")
                print(f"   成功率: {summary.get('success_rate', 0):.1%}")
                
                # 显示质量评估
                if 'quality' in merge_result:
                    quality = merge_result['quality']
                    print(f"   质量等级: {quality.get('quality_level', 'N/A')}")
                    print(f"   质量评分: {quality.get('quality_score', 0):.3f}")
                
                # 显示警告
                if merge_result.get('warnings'):
                    print(f"   ⚠️  警告: {'; '.join(merge_result['warnings'])}")
                
                return merge_result
            else:
                print(f"❌ 结果合并失败: {merge_result.get('error', '未知错误')}")
                return merge_result
                
        except Exception as e:
            print(f"❌ 结果合并异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def step6_display_final_results(self, merge_result: Dict[str, Any]):
        """步骤6: 显示最终结果"""
        try:
            print("\n📋 步骤6: 最终结果展示")
            print("=" * 60)
            
            if not merge_result.get('success', False):
                print("❌ 无有效结果可显示")
                return
            
            # 位置名称映射
            position_names = {
                'zhuang_1': '庄家1', 'zhuang_2': '庄家2', 'zhuang_3': '庄家3',
                'xian_1': '闲家1', 'xian_2': '闲家2', 'xian_3': '闲家3'
            }
            
            print("🎴 各位置识别详情:")
            print("-" * 60)
            
            positions = merge_result.get('positions', {})
            standard_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
            
            for position in standard_positions:
                position_name = position_names.get(position, position)
                
                if position in positions:
                    result = positions[position]
                    
                    if result.get('success', False):
                        display_name = result.get('display_name', 'N/A')
                        confidence = result.get('confidence', 0)
                        method = result.get('method', 'unknown')
                        
                        status_icon = "✅"
                        status_text = f"{display_name} (置信度: {confidence:.3f}) [{method}]"
                        
                        # 显示详细信息
                        if 'suit_name' in result and 'rank' in result:
                            status_text += f" - {result['suit_name']} {result['rank']}"
                        
                        # 显示混合识别信息
                        if 'hybrid_info' in result:
                            hybrid_info = result['hybrid_info']
                            if 'used_methods' in hybrid_info:
                                methods_str = ', '.join(hybrid_info['used_methods'])
                                status_text += f" (方法: {methods_str})"
                    else:
                        status_icon = "❌"
                        error = result.get('error', '未知错误')
                        status_text = f"识别失败 ({error})"
                else:
                    status_icon = "⚪"
                    status_text = "未处理"
                
                print(f"   {position_name:>6}: {status_icon} {status_text}")
            
            # 显示汇总统计
            summary = merge_result.get('summary', {})
            print("-" * 60)
            print(f"📈 汇总统计:")
            print(f"   成功位置: {summary.get('successful_positions', 0)}/{summary.get('total_positions', 0)}")
            print(f"   成功率: {summary.get('success_rate', 0):.1%}")
            
            # 显示识别的卡牌
            recognized_cards = summary.get('recognized_cards', [])
            if recognized_cards:
                print(f"   识别卡牌: {', '.join(recognized_cards)}")
            
            # 显示质量信息
            if 'quality' in merge_result:
                quality = merge_result['quality']
                print(f"\n🏆 质量评估:")
                print(f"   质量等级: {quality.get('quality_level', 'N/A')}")
                print(f"   质量评分: {quality.get('quality_score', 0):.3f}")
                print(f"   平均置信度: {quality.get('confidence_stats', {}).get('average', 0):.3f}")
                
                if quality.get('suggestions'):
                    print(f"   建议: {'; '.join(quality['suggestions'])}")
            
            # 显示处理时间
            processing_duration = merge_result.get('processing_duration', 0)
            recognition_duration = merge_result.get('recognition_duration', 0) 
            print(f"\n⏱️  性能信息:")
            print(f"   识别耗时: {recognition_duration:.3f}秒")
            print(f"   合并耗时: {processing_duration:.3f}秒")
            
        except Exception as e:
            print(f"❌ 显示最终结果异常: {e}")
    
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
                return f"{parts[2]}_{parts[3].split('.')[0]}"  # zhuang_1
            return "unknown"
        except:
            return "unknown"
    
    def _update_method_stats(self, result: Dict[str, Any]):
        """更新识别方法统计"""
        try:
            method = result.get('method', 'unknown')
            hybrid_info = result.get('hybrid_info', {})
            used_methods = hybrid_info.get('used_methods', [])
            fusion_strategy = hybrid_info.get('fusion_strategy', '')
            
            # 统计识别方法
            if method == 'yolo' and len(used_methods) == 1:
                self.stats['recognition_method_stats']['yolo_complete'] += 1
            elif len(used_methods) > 1:
                self.stats['recognition_method_stats']['hybrid_combined'] += 1
            elif 'ocr' in used_methods:
                self.stats['recognition_method_stats']['ocr_only'] += 1
            elif 'opencv_suit' in used_methods:
                self.stats['recognition_method_stats']['opencv_only'] += 1
            
            # 统计融合策略
            if fusion_strategy in self.stats['fusion_strategy_stats']:
                self.stats['fusion_strategy_stats'][fusion_strategy] += 1
                
        except Exception:
            pass  # 忽略统计错误
    
    def run_complete_test(self) -> bool:
        """运行完整测试流程"""
        try:
            print(f"\n🎯 开始完整混合识别测试流程")
            print(f"摄像头: {self.selected_camera_id}")
            print(f"融合策略: {self.recognition_config['fusion_strategy']}")
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
            
            # 步骤4: 混合识别
            recognition_result = self.step4_recognize_cards_hybrid(
                crop_result['main_files'],
                crop_result['left_files']
            )
            if not recognition_result['success']:
                self.stats['failed_tests'] += 1
                return False
            
            # 步骤5: 合并结果
            merge_result = self.step5_merge_results(recognition_result['position_results'])
            if not merge_result['success']:
                self.stats['failed_tests'] += 1  
                return False
            
            # 步骤6: 显示最终结果
            self.step6_display_final_results(merge_result)
            
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
                print(f"\n🧠 识别方法统计 (总计: {total_recognitions} 次):")
                method_names = {
                    'yolo_complete': 'YOLO完整识别',
                    'hybrid_combined': '混合组合识别',
                    'ocr_only': '仅OCR识别',
                    'opencv_only': '仅OpenCV识别',
                    'failed': '识别失败'
                }
                for method, count in method_stats.items():
                    if count > 0:
                        percentage = (count / total_recognitions) * 100
                        method_name = method_names.get(method, method)
                        print(f"  {method_name}: {count} 次 ({percentage:.1f}%)")
            
            # 显示融合策略统计
            fusion_stats = self.stats['fusion_strategy_stats']
            total_fusions = sum(fusion_stats.values())
            if total_fusions > 0:
                print(f"\n🔄 融合策略统计 (总计: {total_fusions} 次):")
                for strategy, count in fusion_stats.items():
                    if count > 0:
                        percentage = (count / total_fusions) * 100
                        print(f"  {strategy}: {count} 次 ({percentage:.1f}%)")
            
            print("=" * 40)
            
        except Exception as e:
            print(f"❌ 统计信息显示异常: {e}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='扑克识别系统完整测试程序 (混合识别版)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python see.py                    # 交互模式，单次测试
  python see.py --auto             # 自动循环测试
  python see.py --count 5          # 连续测试5次
  python see.py --camera 002       # 指定摄像头ID
  python see.py --strategy voting  # 使用投票融合策略
  python see.py --debug            # 启用调试模式
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
    parser.add_argument('--strategy', choices=['weighted', 'voting', 'priority'], 
                       default='weighted', help='融合策略 (默认: weighted)')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试模式')
    parser.add_argument('--no-yolo', action='store_true',
                       help='禁用YOLO识别')
    parser.add_argument('--no-ocr', action='store_true',
                       help='禁用OCR识别')
    parser.add_argument('--no-opencv', action='store_true',
                       help='禁用OpenCV花色识别')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        args = parse_arguments()
        
        # 创建测试器
        tester = EnhancedPokerRecognitionTester()
        
        # 更新识别配置
        tester.recognition_config.update({
            'fusion_strategy': args.strategy,
            'debug_mode': args.debug,
            'yolo_enabled': not args.no_yolo,
            'ocr_enabled': not args.no_ocr,
            'opencv_suit_enabled': not args.no_opencv
        })
        
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
        
        print("👋 扑克混合识别测试系统已关闭")
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())