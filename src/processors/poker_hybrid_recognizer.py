#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克牌混合识别器 - 整合YOLO+OCR+OpenCV识别
功能:
1. 单张扑克牌识别（YOLO + OCR + OpenCV花色识别）
2. 摄像头全位置批量识别
3. 结果融合和综合判断
4. 命令行测试支持
5. 函数接口供其他模块调用
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

def setup_project_paths():
    """设置项目路径"""
    current_file = Path(__file__).resolve()
    project_root = current_file
    while project_root.parent != project_root:
        if (project_root / "main.py").exists():
            break
        project_root = project_root.parent
    
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

PROJECT_ROOT = setup_project_paths()

class HybridPokerRecognizer:
    """混合扑克识别器"""
    
    def __init__(self):
        """初始化识别器"""
        self.available_methods = self._check_methods_availability()
        print("🧠 混合扑克识别器初始化完成")
        self._display_methods_status()
    
    def _check_methods_availability(self) -> Dict[str, bool]:
        """检查各识别方法可用性"""
        methods = {
            'yolo': False,
            'ocr': False,
            'opencv': False
        }
        
        # 检查YOLO
        try:
            from src.processors.poker_yolo_detector import detect_with_yolo
            methods['yolo'] = True
        except ImportError:
            pass
        
        # 检查OCR
        try:
            from src.processors.poker_ocr_detector import detect_poker_character
            methods['ocr'] = True
        except ImportError:
            pass
        
        # 检查OpenCV
        try:
            from src.processors.poker_suit_detector import detect_poker_suit
            methods['opencv'] = True
        except ImportError:
            pass
        
        return methods
    
    def _display_methods_status(self):
        """显示识别方法状态"""
        print("🔍 识别方法状态:")
        method_names = {
            'yolo': 'YOLO完整识别',
            'ocr': 'OCR字符识别', 
            'opencv': 'OpenCV花色识别'
        }
        
        for method, name in method_names.items():
            status = "✅ 可用" if self.available_methods[method] else "❌ 不可用"
            print(f"   {name}: {status}")
    
    def recognize_single_card(self, main_image_path: str, left_image_path: str = None) -> Dict[str, Any]:
        """
        识别单张扑克牌 - 核心方法
        
        Args:
            main_image_path: 主图片路径
            left_image_path: 左上角图片路径（用于OCR和花色识别）
            
        Returns:
            识别结果
        """
        try:
            print(f"\n🎯 识别: {Path(main_image_path).name}")
            
            start_time = time.time()
            
            # 检查文件存在性
            if not os.path.exists(main_image_path):
                return self._format_error_result(f"主图片不存在: {main_image_path}")
            
            # 收集各方法的识别结果
            recognition_results = {}
            
            # 1. YOLO识别（完整扑克牌）
            if self.available_methods['yolo']:
                yolo_result = self._recognize_with_yolo(main_image_path)
                if yolo_result['success']:
                    recognition_results['yolo'] = yolo_result
                    print(f"   ✅ YOLO: {yolo_result['display_name']} (置信度: {yolo_result['confidence']:.3f})")
                else:
                    print(f"   ❌ YOLO: {yolo_result['error']}")
            
            # 2. OCR识别（字符）
            ocr_result = None
            if self.available_methods['ocr'] and left_image_path and os.path.exists(left_image_path):
                ocr_result = self._recognize_with_ocr(left_image_path)
                if ocr_result['success']:
                    print(f"   ✅ OCR: {ocr_result['character']} (置信度: {ocr_result['confidence']:.3f})")
                else:
                    print(f"   ❌ OCR: {ocr_result['error']}")
            elif not left_image_path:
                print(f"   ⚠️  OCR: 未提供左上角图片")
            
            # 3. OpenCV花色识别
            opencv_result = None
            if self.available_methods['opencv']:
                image_for_suit = left_image_path if left_image_path and os.path.exists(left_image_path) else main_image_path
                opencv_result = self._recognize_with_opencv(image_for_suit)
                if opencv_result['success']:
                    print(f"   ✅ OpenCV: {opencv_result['suit_name']} {opencv_result['suit_symbol']} (置信度: {opencv_result['confidence']:.3f})")
                else:
                    print(f"   ❌ OpenCV: {opencv_result['error']}")
            
            # 4. 组合OCR+OpenCV结果
            if ocr_result and ocr_result['success'] and opencv_result and opencv_result['success']:
                combined_result = self._combine_ocr_opencv(ocr_result, opencv_result)
                recognition_results['ocr_opencv'] = combined_result
                print(f"   ✅ OCR+OpenCV: {combined_result['display_name']} (组合置信度: {combined_result['confidence']:.3f})")
            
            # 5. 结果融合
            if recognition_results:
                final_result = self._fuse_results(recognition_results)
            else:
                final_result = self._format_error_result("所有识别方法都失败")
            
            # 添加处理信息
            processing_time = time.time() - start_time
            final_result['processing_time'] = processing_time
            final_result['methods_used'] = list(recognition_results.keys())
            final_result['recognition_details'] = recognition_results
            
            if final_result['success']:
                print(f"   🎉 最终结果: {final_result['display_name']} (置信度: {final_result['confidence']:.3f}, 耗时: {processing_time:.3f}s)")
            else:
                print(f"   💥 识别失败: {final_result['error']}")
            
            return final_result
            
        except Exception as e:
            return self._format_error_result(f"识别异常: {str(e)}")
    
    def recognize_camera_positions(self, camera_id: str, cut_image_dir: str) -> Dict[str, Any]:
        """
        识别摄像头所有位置
        
        Args:
            camera_id: 摄像头ID
            cut_image_dir: 裁剪图片目录
            
        Returns:
            所有位置的识别结果
        """
        try:
            print(f"\n📷 识别摄像头 {camera_id} 所有位置")
            
            cut_dir = Path(cut_image_dir)
            if not cut_dir.exists():
                return self._format_camera_error_result(camera_id, f"裁剪目录不存在: {cut_image_dir}")
            
            # 标准位置列表
            positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
            
            # 查找图片文件
            position_results = {}
            successful_count = 0
            
            for position in positions:
                # 查找主图片和左上角图片
                main_pattern = f"camera_{camera_id}_{position}.png"
                left_pattern = f"camera_{camera_id}_{position}_left.png"
                
                main_file = cut_dir / main_pattern
                left_file = cut_dir / left_pattern
                
                if main_file.exists():
                    # 识别该位置
                    left_path = str(left_file) if left_file.exists() else None
                    result = self.recognize_single_card(str(main_file), left_path)
                    
                    if result['success']:
                        successful_count += 1
                    
                    position_results[position] = result
                else:
                    # 图片不存在
                    position_results[position] = self._format_error_result(f"图片不存在: {main_pattern}")
            
            # 汇总结果
            total_positions = len(positions)
            success_rate = (successful_count / total_positions) * 100 if total_positions > 0 else 0
            
            recognized_cards = []
            for pos, result in position_results.items():
                if result['success']:
                    recognized_cards.append(f"{pos}:{result['display_name']}")
            
            summary_result = {
                'success': successful_count > 0,
                'camera_id': camera_id,
                'positions': position_results,
                'summary': {
                    'total_positions': total_positions,
                    'successful_positions': successful_count,
                    'failed_positions': total_positions - successful_count,
                    'success_rate': success_rate,
                    'recognized_cards': recognized_cards
                }
            }
            
            print(f"📊 摄像头 {camera_id} 识别完成: {successful_count}/{total_positions} 成功 ({success_rate:.1f}%)")
            
            return summary_result
            
        except Exception as e:
            return self._format_camera_error_result(camera_id, f"批量识别异常: {str(e)}")
    
    def _recognize_with_yolo(self, image_path: str) -> Dict[str, Any]:
        """使用YOLO识别"""
        try:
            from src.processors.poker_yolo_detector import detect_with_yolo
            
            result = detect_with_yolo(image_path, 0.3)
            
            if result['success']:
                return {
                    'success': True,
                    'suit': result['suit'],
                    'rank': result['rank'],
                    'suit_symbol': result['suit_symbol'],
                    'suit_name': result['suit_name'],
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
        """使用OCR识别字符"""
        try:
            from src.processors.poker_ocr_detector import detect_poker_character
            
            result = detect_poker_character(image_path)
            
            if result['success']:
                return {
                    'success': True,
                    'character': result['character'],
                    'confidence': result['confidence'],
                    'method': result['method']
                }
            else:
                return {
                    'success': False,
                    'error': result['error'],
                    'method': result.get('method', 'ocr')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"OCR识别异常: {str(e)}",
                'method': 'ocr'
            }
    
    def _recognize_with_opencv(self, image_path: str) -> Dict[str, Any]:
        """使用OpenCV识别花色"""
        try:
            from src.processors.poker_suit_detector import detect_poker_suit
            
            result = detect_poker_suit(image_path)
            
            if result['success']:
                return {
                    'success': True,
                    'suit': result['suit'],
                    'suit_name': result['suit_name'],
                    'suit_symbol': result['suit_symbol'],
                    'confidence': result['confidence'],
                    'method': result['method']
                }
            else:
                return {
                    'success': False,
                    'error': result['error'],
                    'method': result.get('method', 'opencv')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"OpenCV识别异常: {str(e)}",
                'method': 'opencv'
            }
    
    def _combine_ocr_opencv(self, ocr_result: Dict[str, Any], opencv_result: Dict[str, Any]) -> Dict[str, Any]:
        """组合OCR和OpenCV结果"""
        try:
            character = ocr_result.get('character', '')
            suit = opencv_result.get('suit', '')
            suit_name = opencv_result.get('suit_name', '')
            suit_symbol = opencv_result.get('suit_symbol', '')
            
            # 计算组合置信度（字符权重更高）
            char_confidence = ocr_result.get('confidence', 0)
            suit_confidence = opencv_result.get('confidence', 0)
            combined_confidence = (char_confidence * 0.6 + suit_confidence * 0.4)
            
            # 生成显示名称
            display_name = f"{suit_symbol}{character}" if suit_symbol and character else character
            
            return {
                'success': True,
                'suit': suit,
                'rank': character,
                'suit_symbol': suit_symbol,
                'suit_name': suit_name,
                'display_name': display_name,
                'confidence': combined_confidence,
                'method': 'ocr+opencv'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"结果组合失败: {str(e)}",
                'method': 'ocr+opencv'
            }
    
    def _fuse_results(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """结果融合 - 使用加权策略"""
        try:
            # 方法权重
            method_weights = {
                'yolo': 0.7,         # YOLO权重最高
                'ocr_opencv': 0.5,   # OCR+OpenCV组合
                'ocr': 0.3,          # 单独OCR
                'opencv': 0.2        # 单独OpenCV
            }
            
            best_result = None
            best_score = 0
            best_method = None
            
            print("   🔄 结果融合:")
            
            for method, result in results.items():
                confidence = result.get('confidence', 0)
                weight = method_weights.get(method, 0.1)
                score = confidence * weight
                
                print(f"      {method}: 置信度={confidence:.3f} × 权重={weight} = 得分={score:.3f}")
                
                if score > best_score:
                    best_score = score
                    best_result = result.copy()
                    best_method = method
            
            if best_result and best_score >= 0.2:  # 最小得分阈值
                best_result['fusion_method'] = 'weighted'
                best_result['fusion_score'] = best_score
                best_result['selected_method'] = best_method
                
                print(f"   🏆 选择: {best_method} (融合得分: {best_score:.3f})")
                return best_result
            else:
                return self._format_error_result("融合后置信度不足")
                
        except Exception as e:
            return self._format_error_result(f"结果融合失败: {str(e)}")
    
    def _format_error_result(self, error_message: str) -> Dict[str, Any]:
        """格式化错误结果"""
        return {
            'success': False,
            'suit': '',
            'rank': '',
            'suit_symbol': '',
            'suit_name': '',
            'display_name': '',
            'confidence': 0.0,
            'error': error_message
        }
    
    def _format_camera_error_result(self, camera_id: str, error_message: str) -> Dict[str, Any]:
        """格式化摄像头错误结果"""
        positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        return {
            'success': False,
            'camera_id': camera_id,
            'error': error_message,
            'positions': {pos: self._format_error_result(error_message) for pos in positions},
            'summary': {
                'total_positions': len(positions),
                'successful_positions': 0,
                'failed_positions': len(positions),
                'success_rate': 0.0,
                'recognized_cards': []
            }
        }

# ============ 新增：供其他模块调用的函数接口 ============

# 创建全局识别器实例
_global_recognizer = None

def get_recognizer():
    """获取全局识别器实例"""
    global _global_recognizer
    if _global_recognizer is None:
        _global_recognizer = HybridPokerRecognizer()
    return _global_recognizer

def recognize_single_card_func(main_image_path: str, left_image_path: str = None) -> Dict[str, Any]:
    """
    供其他模块调用的单张扑克牌识别函数
    
    Args:
        main_image_path: 主图片路径
        left_image_path: 左上角图片路径（可选）
        
    Returns:
        dict: 识别结果
    """
    recognizer = get_recognizer()
    return recognizer.recognize_single_card(main_image_path, left_image_path)

def recognize_camera_positions_func(camera_id: str, cut_image_dir: str = None) -> Dict[str, Any]:
    """
    供其他模块调用的摄像头批量识别函数
    
    Args:
        camera_id: 摄像头ID
        cut_image_dir: 裁剪图片目录，默认为 src/image/cut/
        
    Returns:
        dict: 所有位置的识别结果
    """
    if cut_image_dir is None:
        project_root = setup_project_paths()
        cut_image_dir = str(project_root / "src" / "image" / "cut")
    
    recognizer = get_recognizer()
    return recognizer.recognize_camera_positions(camera_id, cut_image_dir)

def recognize_single_card_silent(main_image_path: str, left_image_path: str = None) -> Dict[str, Any]:
    """
    静默单张识别函数，不输出调试信息
    
    Args:
        main_image_path: 主图片路径
        left_image_path: 左上角图片路径（可选）
        
    Returns:
        dict: 识别结果
    """
    # 临时禁用print输出
    import builtins
    original_print = builtins.print
    builtins.print = lambda *args, **kwargs: None
    
    try:
        result = recognize_single_card_func(main_image_path, left_image_path)
        return result
    finally:
        # 恢复print输出
        builtins.print = original_print

# ============ 命令行接口保持不变 ============

def test_single_card(main_path: str, left_path: str = None):
    """测试单张扑克牌识别"""
    print("🧪 单张扑克牌识别测试")
    print("=" * 50)
    
    recognizer = HybridPokerRecognizer()
    result = recognizer.recognize_single_card(main_path, left_path)
    
    if result['success']:
        print(f"\n✅ 识别成功!")
        print(f"   卡牌: {result['display_name']}")
        print(f"   花色: {result['suit_name']} ({result['suit_symbol']})")
        print(f"   点数: {result['rank']}")
        print(f"   置信度: {result['confidence']:.3f}")
        print(f"   融合方法: {result.get('selected_method', 'N/A')}")
        print(f"   处理时间: {result['processing_time']:.3f}秒")
        
        # 显示详细识别结果
        if 'recognition_details' in result:
            print(f"\n📋 详细识别结果:")
            for method, detail in result['recognition_details'].items():
                if detail['success']:
                    display = detail.get('display_name') or detail.get('character', '') or detail.get('suit_name', '')
                    print(f"   {method}: {display} (置信度: {detail['confidence']:.3f})")
    else:
        print(f"\n❌ 识别失败: {result['error']}")

def test_camera_batch(camera_id: str, cut_dir: str):
    """测试摄像头批量识别"""
    print(f"🧪 摄像头 {camera_id} 批量识别测试")
    print("=" * 50)
    
    recognizer = HybridPokerRecognizer()
    result = recognizer.recognize_camera_positions(camera_id, cut_dir)
    
    if result['success']:
        summary = result['summary']
        print(f"\n✅ 批量识别完成!")
        print(f"   成功率: {summary['success_rate']:.1f}%")
        print(f"   成功位置: {summary['successful_positions']}/{summary['total_positions']}")
        print(f"   识别结果:")
        
        for card_info in summary['recognized_cards']:
            print(f"      {card_info}")
        
        # 显示失败位置
        failed_positions = []
        for pos, pos_result in result['positions'].items():
            if not pos_result['success']:
                failed_positions.append(pos)
        
        if failed_positions:
            print(f"   失败位置: {', '.join(failed_positions)}")
    else:
        print(f"\n❌ 批量识别失败: {result['error']}")

def show_capabilities():
    """显示识别能力"""
    print("🔍 混合识别器能力检查")
    print("=" * 50)
    
    recognizer = HybridPokerRecognizer()
    
    total_methods = len(recognizer.available_methods)
    available_count = sum(recognizer.available_methods.values())
    
    print(f"\n📊 总计: {available_count}/{total_methods} 个方法可用")
    
    if available_count == 0:
        print("⚠️  警告: 没有可用的识别方法，请检查依赖库安装")
    elif available_count < total_methods:
        print("⚠️  部分识别方法不可用，可能影响识别准确性")
    else:
        print("✅ 所有识别方法都可用")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='扑克牌混合识别器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 单张识别
  python poker_hybrid_recognizer.py --main zhuang_1.png --left zhuang_1_left.png
  
  # 批量识别
  python poker_hybrid_recognizer.py --batch camera_001 --dir src/image/cut/
  
  # 显示能力
  python poker_hybrid_recognizer.py --capabilities
        """
    )
    
    parser.add_argument('--main', type=str, help='主图片路径')
    parser.add_argument('--left', type=str, help='左上角图片路径')
    parser.add_argument('--batch', type=str, help='批量识别摄像头ID')
    parser.add_argument('--dir', type=str, default='src/image/cut/', help='裁剪图片目录')
    parser.add_argument('--capabilities', action='store_true', help='显示识别能力')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    if args.capabilities:
        show_capabilities()
    elif args.main:
        # 单张识别
        test_single_card(args.main, args.left)
    elif args.batch:
        # 批量识别
        test_camera_batch(args.batch, args.dir)
    else:
        # 默认显示帮助
        print("请使用 --help 查看使用方法")
        show_capabilities()

if __name__ == "__main__":
    main()