#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克牌识别程序
功能: 使用YOLOv8模型识别裁剪后的扑克牌图片
作者: AI助手
版本: 1.0
"""

import os
import sys
import json
import argparse
from pathlib import Path
import logging
from datetime import datetime
import requests
import time

class PokerRecognition:
    def __init__(self, config_path="../config/camera.json", model_path="../config/yolov8/best.pt"):
        """
        初始化扑克牌识别系统
        
        Args:
            config_path: 摄像头配置文件路径
            model_path: YOLOv8模型文件路径
        """
        self.config_path = config_path
        self.model_path = model_path
        self.config = None
        self.model = None
        self.logger = None
        
        # 设置路径
        self.setup_paths()
        
        # 加载配置
        self.load_config()
        
        # 设置日志
        self.setup_logging()
        
        # 加载模型
        self.load_model()
        
        # 扑克牌位置定义
        self.positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        self.logger.info("扑克牌识别系统初始化完成")
    
    def setup_paths(self):
        """设置各种路径"""
        # 获取当前脚本目录
        self.script_dir = Path(__file__).parent.absolute()
        self.project_root = self.script_dir.parent
        
        # 设置各个目录路径
        self.config_dir = self.project_root / "config"
        self.image_dir = self.project_root / "image"
        self.cut_dir = self.image_dir / "cut"
        self.result_dir = self.project_root / "result"
        
        # 创建必要的目录
        self.result_dir.mkdir(exist_ok=True)
        
    def load_config(self):
        """加载配置文件"""
        try:
            config_file = self.config_dir / "camera.json"
            
            if not config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {config_file}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            print(f"✅ 配置文件加载成功")
            
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            self.config = None
    
    def setup_logging(self):
        """设置日志系统"""
        try:
            # 设置日志格式
            log_format = '%(asctime)s - %(levelname)s - %(message)s'
            
            # 配置日志
            logging.basicConfig(
                level=logging.INFO,
                format=log_format,
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler(self.result_dir / "recognition.log", encoding='utf-8')
                ]
            )
            
            self.logger = logging.getLogger(__name__)
            
        except Exception as e:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            self.logger.warning(f"日志设置失败，使用默认配置: {e}")
    
    def load_model(self):
        """加载YOLOv8模型"""
        try:
            # 检查模型文件是否存在
            model_file = self.config_dir / "yolov8" / "best.pt"
            
            if not model_file.exists():
                raise FileNotFoundError(f"模型文件不存在: {model_file}")
            
            # 导入YOLOv8
            try:
                from ultralytics import YOLO
            except ImportError:
                raise ImportError("请安装ultralytics: pip install ultralytics")
            
            # 加载模型
            self.model = YOLO(str(model_file))
            self.logger.info(f"✅ YOLOv8模型加载成功: {model_file}")
            
            # 获取类别名称
            self.class_names = self.model.names
            self.logger.info(f"📋 模型类别数量: {len(self.class_names)}")
            
        except Exception as e:
            self.logger.error(f"❌ 模型加载失败: {e}")
            self.model = None
    
    def get_enabled_cameras(self):
        """获取启用的摄像头列表"""
        if not self.config:
            return []
        
        return [cam for cam in self.config.get('cameras', []) if cam.get('enabled', True)]
    
    def get_cut_images_for_camera(self, camera_id):
        """获取指定摄像头的所有裁剪图片"""
        cut_images = {}
        
        for position in self.positions:
            image_filename = f"camera_{camera_id}_{position}.png"
            image_path = self.cut_dir / image_filename
            
            if image_path.exists():
                cut_images[position] = image_path
            else:
                self.logger.warning(f"⚠️  图片不存在: {image_filename}")
        
        return cut_images
    
    def recognize_single_image(self, image_path, position):
        """识别单张扑克牌图片"""
        try:
            if not self.model:
                return {
                    'position': position,
                    'suit': '',
                    'rank': '',
                    'confidence': 0.0,
                    'error': '模型未加载'
                }
            
            # 使用YOLOv8进行预测
            results = self.model(str(image_path), conf=0.25, verbose=False)
            
            # 解析结果
            if results and len(results) > 0:
                result = results[0]
                
                # 获取检测框和类别
                if result.boxes is not None and len(result.boxes) > 0:
                    # 获取置信度最高的检测结果
                    confidences = result.boxes.conf.cpu().numpy()
                    best_idx = confidences.argmax()
                    
                    best_conf = float(confidences[best_idx])
                    best_class = int(result.boxes.cls[best_idx].cpu().numpy())
                    
                    # 解析类别名称
                    class_name = self.class_names.get(best_class, 'unknown')
                    suit, rank = self.parse_card_name(class_name)
                    
                    self.logger.info(f"✅ {position}: {class_name} (置信度: {best_conf:.3f})")
                    
                    return {
                        'position': position,
                        'suit': suit,
                        'rank': rank,
                        'confidence': best_conf,
                        'class_name': class_name
                    }
                else:
                    self.logger.warning(f"⚠️  {position}: 未检测到扑克牌")
                    return {
                        'position': position,
                        'suit': '',
                        'rank': '',
                        'confidence': 0.0,
                        'error': '未检测到扑克牌'
                    }
            else:
                self.logger.warning(f"⚠️  {position}: 识别结果为空")
                return {
                    'position': position,
                    'suit': '',
                    'rank': '',
                    'confidence': 0.0,
                    'error': '识别结果为空'
                }
                
        except Exception as e:
            self.logger.error(f"❌ {position} 识别失败: {e}")
            return {
                'position': position,
                'suit': '',
                'rank': '',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def parse_card_name(self, class_name):
        """
        解析扑克牌类别名称，提取花色和点数
        
        Args:
            class_name: 模型输出的类别名称
            
        Returns:
            tuple: (花色, 点数)
        """
        try:
            # 根据你的模型输出格式调整这个函数
            # 假设格式为 "suit_rank" 或 "rank_suit"
            
            if '_' in class_name:
                parts = class_name.split('_')
                if len(parts) >= 2:
                    # 尝试识别花色和点数
                    suit_candidates = ['spades', 'hearts', 'diamonds', 'clubs', 
                                     'S', 'H', 'D', 'C', '♠', '♥', '♦', '♣']
                    rank_candidates = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
                    
                    suit = ''
                    rank = ''
                    
                    for part in parts:
                        if part.upper() in suit_candidates or part in suit_candidates:
                            suit = self.normalize_suit(part)
                        elif part.upper() in rank_candidates or part in rank_candidates:
                            rank = part.upper()
                    
                    return suit, rank
            
            # 如果无法解析，返回原始类别名称
            return class_name, ''
            
        except Exception as e:
            self.logger.warning(f"解析卡牌名称失败: {class_name}, {e}")
            return class_name, ''
    
    def normalize_suit(self, suit):
        """标准化花色名称"""
        suit_map = {
            'spades': '♠', 'S': '♠', '♠': '♠',
            'hearts': '♥', 'H': '♥', '♥': '♥', 
            'diamonds': '♦', 'D': '♦', '♦': '♦',
            'clubs': '♣', 'C': '♣', '♣': '♣'
        }
        
        return suit_map.get(suit.upper(), suit)
    
    def recognize_camera(self, camera_id):
        """识别指定摄像头的所有扑克牌"""
        # 获取摄像头信息
        camera = None
        for cam in self.config.get('cameras', []):
            if cam['id'] == camera_id:
                camera = cam
                break
        
        if not camera:
            self.logger.error(f"❌ 摄像头 {camera_id} 不存在")
            return None
        
        if not camera.get('enabled', True):
            self.logger.warning(f"⚠️  摄像头 {camera_id} ({camera['name']}) 已禁用")
            return None
        
        self.logger.info(f"📷 开始识别摄像头: {camera['name']} (ID: {camera_id})")
        
        # 获取裁剪图片
        cut_images = self.get_cut_images_for_camera(camera_id)
        
        if not cut_images:
            self.logger.warning(f"⚠️  摄像头 {camera_id} 没有找到裁剪图片")
            return None
        
        self.logger.info(f"🎯 找到 {len(cut_images)} 张裁剪图片")
        
        # 识别每张图片
        results = {}
        for position in self.positions:
            if position in cut_images:
                result = self.recognize_single_image(cut_images[position], position)
                results[position] = result
            else:
                # 位置没有图片，设置为空
                results[position] = {
                    'position': position,
                    'suit': '',
                    'rank': '',
                    'confidence': 0.0,
                    'error': '图片不存在'
                }
        
        return {
            'camera_id': camera_id,
            'camera_name': camera['name'],
            'timestamp': datetime.now().isoformat(),
            'results': results
        }
    
    def recognize_all_cameras(self):
        """识别所有启用摄像头的扑克牌"""
        enabled_cameras = self.get_enabled_cameras()
        
        if not enabled_cameras:
            self.logger.warning("⚠️  没有启用的摄像头")
            return {}
        
        self.logger.info(f"🚀 开始识别 {len(enabled_cameras)} 个摄像头")
        
        all_results = {}
        
        for camera in enabled_cameras:
            camera_id = camera['id']
            result = self.recognize_camera(camera_id)
            
            if result:
                all_results[camera_id] = result
            
            # 间隔处理
            if camera != enabled_cameras[-1]:
                self.logger.info("-" * 50)
        
        return all_results
    
    def generate_final_result(self, all_results):
        """生成最终的识别结果"""
        final_result = {
            'timestamp': datetime.now().isoformat(),
            'total_cameras': len(all_results),
            'cameras': {}
        }
        
        # 为每个位置创建汇总结果
        position_summary = {}
        for position in self.positions:
            position_summary[position] = {
                'suit': '',
                'rank': '',
                'confidence': 0.0,
                'source_camera': '',
                'cameras': {}
            }
        
        # 收集所有摄像头的结果
        for camera_id, camera_result in all_results.items():
            camera_name = camera_result['camera_name']
            final_result['cameras'][camera_id] = {
                'name': camera_name,
                'timestamp': camera_result['timestamp'],
                'positions': {}
            }
            
            for position in self.positions:
                if position in camera_result['results']:
                    pos_result = camera_result['results'][position]
                    final_result['cameras'][camera_id]['positions'][position] = pos_result
                    
                    # 更新位置汇总（选择置信度最高的结果）
                    if pos_result['confidence'] > position_summary[position]['confidence']:
                        position_summary[position] = {
                            'suit': pos_result['suit'],
                            'rank': pos_result['rank'],
                            'confidence': pos_result['confidence'],
                            'source_camera': camera_id,
                            'cameras': {}
                        }
                    
                    # 记录各摄像头的结果
                    position_summary[position]['cameras'][camera_id] = {
                        'suit': pos_result['suit'],
                        'rank': pos_result['rank'],
                        'confidence': pos_result['confidence']
                    }
        
        # 添加位置汇总
        final_result['positions'] = position_summary
        
        return final_result
    
    def save_result_to_file(self, result, filename="result.json"):
        """保存结果到文件"""
        try:
            result_file = self.result_dir / filename
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 结果已保存到: {result_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 保存结果失败: {e}")
            return False
    
    def send_result_to_server(self, result, server_url="http://localhost:8000"):
        """发送结果到HTTP服务器"""
        try:
            api_url = f"{server_url}/api/recognition_result"
            
            response = requests.post(
                api_url,
                json=result,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"✅ 结果已发送到服务器: {api_url}")
                return True
            else:
                self.logger.warning(f"⚠️  服务器响应异常: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"⚠️  无法连接到服务器: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ 发送结果到服务器失败: {e}")
            return False
    
    def run_recognition(self, camera_id=None, save_file=True, send_server=True):
        """运行扑克牌识别"""
        if not self.model:
            self.logger.error("❌ 模型未加载，无法进行识别")
            return False
        
        try:
            # 识别扑克牌
            if camera_id:
                # 识别指定摄像头
                single_result = self.recognize_camera(camera_id)
                if single_result:
                    all_results = {camera_id: single_result}
                else:
                    return False
            else:
                # 识别所有摄像头
                all_results = self.recognize_all_cameras()
            
            if not all_results:
                self.logger.warning("⚠️  没有识别到任何结果")
                return False
            
            # 生成最终结果
            final_result = self.generate_final_result(all_results)
            
            # 保存到文件
            if save_file:
                self.save_result_to_file(final_result)
            
            # 发送到服务器
            if send_server:
                self.send_result_to_server(final_result)
            
            # 输出汇总信息
            self.print_summary(final_result)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 识别过程失败: {e}")
            return False
    
    def print_summary(self, result):
        """打印识别结果汇总"""
        self.logger.info("=" * 50)
        self.logger.info("🎯 识别结果汇总:")
        
        positions = result.get('positions', {})
        
        for position in self.positions:
            if position in positions:
                pos_data = positions[position]
                suit = pos_data['suit']
                rank = pos_data['rank']
                confidence = pos_data['confidence']
                source = pos_data['source_camera']
                
                if suit and rank:
                    self.logger.info(f"   {position}: {suit}{rank} (置信度: {confidence:.3f}, 来源: {source})")
                else:
                    self.logger.info(f"   {position}: 未识别")
        
        self.logger.info("=" * 50)

def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(
        description='扑克牌识别程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python see.py                     # 识别所有启用摄像头的扑克牌
  python see.py -c 001              # 识别指定摄像头的扑克牌
  python see.py --no-save           # 不保存到文件
  python see.py --no-server         # 不发送到服务器
        '''
    )
    
    parser.add_argument('-c', '--camera', type=str, help='指定摄像头ID进行识别')
    parser.add_argument('--no-save', action='store_true', help='不保存结果到文件')
    parser.add_argument('--no-server', action='store_true', help='不发送结果到服务器')
    parser.add_argument('--server-url', type=str, default='http://localhost:8000', help='HTTP服务器地址')
    
    args = parser.parse_args()
    
    print("👁️  扑克牌识别程序 v1.0")
    print("=" * 50)
    
    try:
        # 创建识别系统实例
        recognizer = PokerRecognition()
        
        # 运行识别
        success = recognizer.run_recognition(
            camera_id=args.camera,
            save_file=not args.no_save,
            send_server=not args.no_server
        )
        
        if success:
            print("🎉 识别完成!")
        else:
            print("😞 识别失败!")
            
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()