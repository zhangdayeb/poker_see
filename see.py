#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
see.py - 单摄像头识别测试脚本
功能:
1. 命令行调用: python see.py --camera 001 (仅支持单摄像头模式)
2. 拍照 + 命令行调用切图: python src/processors/image_cutter.py src/image/camera_001.png
3. 命令行调用识别器: python src/processors/poker_hybrid_recognizer.py --main ... --left ...
4. 给出整体识别结果
5. 功能尽量简单

使用方式: python see.py --camera 001
"""

import sys
import subprocess
import os
import re
import time
import argparse
from pathlib import Path
from typing import Dict, Any

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

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='单摄像头识别测试脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python see.py --camera 001    # 识别摄像头001
  python see.py --camera 002    # 识别摄像头002
        """
    )
    
    parser.add_argument('--camera', required=True, help='摄像头ID (如: 001, 002, 004)')
    
    return parser.parse_args()

def take_photo_step(camera_id: str) -> Dict[str, Any]:
    """
    拍照步骤
    
    Args:
        camera_id: 摄像头ID
        
    Returns:
        拍照结果
    """
    print(f"📸 拍照摄像头 {camera_id}...")
    
    try:
        from src.processors.photo_controller import take_photo_by_id
        
        result = take_photo_by_id(camera_id)
        
        if result['success']:
            filename = result['data']['filename']
            file_size_mb = result['data'].get('file_size', 0) / (1024 * 1024)
            print(f"✅ 拍照成功: {filename} ({file_size_mb:.1f}MB)")
            
            return {
                'success': True,
                'image_path': result['data']['file_path'],
                'filename': filename
            }
        else:
            raise Exception(f"拍照失败: {result.get('message', '未知错误')}")
            
    except Exception as e:
        raise Exception(f"拍照步骤失败: {str(e)}")

def call_image_cutter_cli(image_path: str) -> Dict[str, Any]:
    """
    通过命令行调用切图组件
    命令: python src/processors/image_cutter.py src/image/camera_001.png
    
    Args:
        image_path: 图片路径
        
    Returns:
        切图结果
    """
    print(f"✂️  切图处理...")
    
    cmd = [
        'python', 'src/processors/image_cutter.py',
        image_path
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=str(PROJECT_ROOT),
            timeout=60  # 60秒超时
        )
        
        if result.returncode == 0:
            print("✅ 切图成功")
            return {
                'success': True, 
                'output': result.stdout,
                'cmd': ' '.join(cmd)
            }
        else:
            error_msg = result.stderr.strip() if result.stderr else '切图失败'
            raise Exception(f"切图失败: {error_msg}")
            
    except subprocess.TimeoutExpired:
        raise Exception("切图超时 (>60s)")
    except Exception as e:
        raise Exception(f"切图异常: {str(e)}")

def call_single_recognizer_cli(main_path: str, left_path: str) -> Dict[str, Any]:
    """
    调用单个位置的识别器
    命令: python src/processors/poker_hybrid_recognizer.py --main ... --left ...
    
    Args:
        main_path: 主图片路径
        left_path: 左上角图片路径
        
    Returns:
        识别结果
    """
    cmd = [
        'python', 'src/processors/poker_hybrid_recognizer.py',
        '--main', main_path
    ]
    
    # 如果左上角图片存在，添加参数
    if os.path.exists(left_path):
        cmd.extend(['--left', left_path])
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=str(PROJECT_ROOT),
            timeout=30  # 30秒超时
        )
        
        if result.returncode == 0:
            return parse_recognizer_output_simple(result.stdout)
        else:
            return {
                'success': False,
                'error': '识别失败',
                'card': '',
                'confidence': 0.0
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': '识别超时',
            'card': '',
            'confidence': 0.0
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'card': '',
            'confidence': 0.0
        }

def parse_recognizer_output_simple(output: str) -> Dict[str, Any]:
    """
    简化解析识别器输出
    只提取关键信息：成功/失败、卡牌、置信度
    
    Args:
        output: 识别器的输出文本
        
    Returns:
        解析后的结果
    """
    try:
        lines = output.strip().split('\n')
        
        success = False
        card = ""
        confidence = 0.0
        error_msg = ""
        
        for line in lines:
            # 检查成功标志
            if "✅ 识别成功!" in line:
                success = True
            elif "❌ 识别失败:" in line:
                success = False
                # 提取错误信息
                error_match = re.search(r'❌ 识别失败:\s*(.+)', line)
                if error_match:
                    error_msg = error_match.group(1).strip()
            elif "💥 识别失败:" in line:
                success = False
                error_match = re.search(r'💥 识别失败:\s*(.+)', line)
                if error_match:
                    error_msg = error_match.group(1).strip()
            
            # 提取最终结果
            elif "🎉 最终结果:" in line:
                # 例: "🎉 最终结果: ♥️A (置信度: 0.950, 耗时: 2.345s)"
                match = re.search(r'最终结果:\s*([^\s(]+)\s*\(置信度:\s*([\d.]+)', line)
                if match:
                    card = match.group(1)
                    confidence = float(match.group(2))
            
            # 备用提取方式 - 卡牌信息
            elif "卡牌:" in line:
                match = re.search(r'卡牌:\s*([^\s]+)', line)
                if match:
                    card = match.group(1)
            
            # 备用提取方式 - 置信度
            elif "置信度:" in line and not "最终结果:" in line:
                match = re.search(r'置信度:\s*([\d.]+)', line)
                if match:
                    confidence = float(match.group(1))
        
        # 构建结果
        if success and card:
            return {
                'success': True,
                'card': card,
                'confidence': confidence,
                'error': ''
            }
        else:
            return {
                'success': False,
                'card': '',
                'confidence': 0.0,
                'error': error_msg or '识别失败'
            }
            
    except Exception as e:
        return {
            'success': False,
            'card': '',
            'confidence': 0.0,
            'error': f'解析失败: {str(e)}'
        }

def batch_call_recognizer_cli(camera_id: str) -> Dict[str, Any]:
    """
    批量调用识别器处理6个位置
    
    Args:
        camera_id: 摄像头ID
        
    Returns:
        批量识别结果
    """
    print(f"🧠 识别处理...")
    
    positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
    results = {}
    successful_count = 0
    
    cut_dir = PROJECT_ROOT / "image" / "cut"
    
    # 检查切图目录是否存在
    if not cut_dir.exists():
        return {
            'success': False,
            'error': f'切图目录不存在: {cut_dir}',
            'successful_count': 0,
            'total_count': len(positions),
            'positions': {}
        }
    
    for position in positions:
        print(f"  🎯 识别位置: {position}")
        
        # 构建文件路径
        main_file = cut_dir / f"camera_{camera_id}_{position}.png"
        left_file = cut_dir / f"camera_{camera_id}_{position}_left.png"
        
        if not main_file.exists():
            results[position] = {
                'success': False,
                'error': '主图片不存在',
                'card': '',
                'confidence': 0.0
            }
            print(f"    ❌ 主图片不存在")
            continue
        
        # 调用识别器
        recognition_result = call_single_recognizer_cli(str(main_file), str(left_file))
        results[position] = recognition_result
        
        if recognition_result['success']:
            successful_count += 1
            print(f"    ✅ {recognition_result['card']} ({recognition_result['confidence']:.3f})")
        else:
            print(f"    ❌ {recognition_result['error']}")
    
    return {
        'success': successful_count > 0,
        'successful_count': successful_count,
        'total_count': len(positions),
        'positions': results
    }

def create_final_result(camera_id: str, recognition_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建最终结果
    
    Args:
        camera_id: 摄像头ID
        recognition_result: 识别结果
        
    Returns:
        最终汇总结果
    """
    if not recognition_result['success']:
        return {
            'success': False,
            'camera_id': camera_id,
            'error': recognition_result.get('error', '识别过程失败'),
            'summary': {
                'success_rate': '0/6',
                'success_percentage': 0.0,
                'recognized_cards': [],
                'failed_positions': []
            },
            'positions': {}
        }
    
    positions = recognition_result['positions']
    successful_cards = []
    failed_positions = []
    
    # 位置名称映射（简化显示）
    position_names = {
        'zhuang_1': '庄1', 'zhuang_2': '庄2', 'zhuang_3': '庄3',
        'xian_1': '闲1', 'xian_2': '闲2', 'xian_3': '闲3'
    }
    
    # 处理每个位置的结果
    for pos, result in positions.items():
        pos_name = position_names.get(pos, pos)
        if result['success']:
            successful_cards.append(f"{pos_name}:{result['card']}")
        else:
            failed_positions.append(pos_name)
    
    success_count = recognition_result['successful_count']
    total_count = recognition_result['total_count']
    success_percentage = round((success_count / total_count) * 100, 1) if total_count > 0 else 0.0
    
    return {
        'success': success_count > 0,
        'camera_id': camera_id,
        'summary': {
            'success_rate': f"{success_count}/{total_count}",
            'success_percentage': success_percentage,
            'recognized_cards': successful_cards,
            'failed_positions': failed_positions
        },
        'positions': positions
    }

def print_simple_result(result: Dict[str, Any]):
    """
    打印简化的结果
    
    Args:
        result: 最终结果
    """
    camera_id = result.get('camera_id', 'unknown')
    
    print(f"\n{'='*50}")
    print(f"🎯 摄像头 {camera_id} 识别结果")
    print(f"{'='*50}")
    
    if result['success']:
        summary = result['summary']
        print(f"✅ 识别成功: {summary['success_rate']} ({summary['success_percentage']}%)")
        
        # 显示识别的卡牌
        if summary['recognized_cards']:
            print(f"🎴 识别卡牌:")
            cards_per_line = 3
            cards = summary['recognized_cards']
            for i in range(0, len(cards), cards_per_line):
                line_cards = cards[i:i+cards_per_line]
                print(f"   {' | '.join(line_cards)}")
        
        # 显示失败位置
        if summary['failed_positions']:
            print(f"❌ 失败位置: {', '.join(summary['failed_positions'])}")
        
        # 显示详细置信度
        positions = result.get('positions', {})
        if positions:
            print(f"\n📊 详细结果:")
            position_names = {
                'zhuang_1': '庄1', 'zhuang_2': '庄2', 'zhuang_3': '庄3',
                'xian_1': '闲1', 'xian_2': '闲2', 'xian_3': '闲3'
            }
            
            for pos, pos_result in positions.items():
                pos_name = position_names.get(pos, pos)
                if pos_result['success']:
                    confidence = pos_result['confidence']
                    confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
                    print(f"   {pos_name}: {pos_result['card']} [{confidence_bar}] {confidence:.3f}")
                else:
                    print(f"   {pos_name}: ❌ {pos_result['error']}")
    else:
        error_msg = result.get('error', '未知错误')
        print(f"❌ 识别失败: {error_msg}")
    
    print(f"{'='*50}")

def execute_camera_workflow(camera_id: str) -> Dict[str, Any]:
    """
    执行单摄像头工作流程
    拍照 → 切图(CLI) → 识别(CLI) → 汇总
    
    Args:
        camera_id: 摄像头ID
        
    Returns:
        工作流程结果
    """
    try:
        workflow_start_time = time.time()
        
        print(f"\n🚀 开始处理摄像头 {camera_id}")
        print("-" * 40)
        
        # 步骤1: 拍照
        photo_result = take_photo_step(camera_id)
        
        # 步骤2: 命令行调用切图
        cut_result = call_image_cutter_cli(photo_result['image_path'])
        
        # 步骤3: 命令行批量调用识别器
        recognition_result = batch_call_recognizer_cli(camera_id)
        
        # 步骤4: 汇总结果
        final_result = create_final_result(camera_id, recognition_result)
        
        # 添加总耗时
        total_duration = time.time() - workflow_start_time
        final_result['total_duration'] = round(total_duration, 2)
        
        print(f"\n⏱️  总耗时: {total_duration:.2f}秒")
        
        return final_result
        
    except Exception as e:
        return {
            'success': False,
            'camera_id': camera_id,
            'error': str(e),
            'summary': {
                'success_rate': '0/6',
                'success_percentage': 0.0,
                'recognized_cards': [],
                'failed_positions': []
            },
            'positions': {}
        }

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        camera_id = args.camera
        
        print("🎯 单摄像头识别测试系统")
        print(f"摄像头ID: {camera_id}")
        print("流程: 拍照 → 切图(CLI) → 识别(CLI) → 汇总")
        
        # 执行工作流程
        result = execute_camera_workflow(camera_id)
        
        # 输出结果
        print_simple_result(result)
        
        # 返回状态码
        return 0 if result['success'] else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  程序被用户中断")
        return 130
    except Exception as e:
        print(f"\n💥 程序异常: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())