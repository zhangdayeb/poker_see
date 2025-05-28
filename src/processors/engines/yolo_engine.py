#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO识别引擎 - 基于YOLOv8的扑克牌识别
功能:
1. YOLOv8模型加载和初始化
2. 扑克牌检测和识别
3. 结果解析和格式化
4. 置信度过滤和后处理
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

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

PROJECT_ROOT = setup_project_paths()

from src.processors.engines.base_engine import BaseEngine
from src.core.utils import log_info, log_success, log_error, log_warning

class YOLOEngine(BaseEngine):
    """YOLO识别引擎"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化YOLO引擎"""
        self.model = None
        self.model_path = None
        self.ultralytics_available = False
        
        super().__init__("YOLO", config)
    
    def _initialize_engine(self):
        """初始化YOLO引擎"""
        try:
            # 检查ultralytics是否可用
            try:
                from ultralytics import YOLO
                self.ultralytics_available = True
                log_success("ultralytics库加载成功", "YOLO_ENGINE")
            except ImportError as e:
                log_error(f"ultralytics库不可用: {e}", "YOLO_ENGINE")
                self.ultralytics_available = False
                self.enabled = False
                return
            
            # 获取模型路径
            self.model_path = self.config.get('model_path', 'src/config/yolov8/best.pt')
            
            # 转换为绝对路径
            if not Path(self.model_path).is_absolute():
                self.model_path = PROJECT_ROOT / self.model_path
            
            # 检查模型文件是否存在
            if not Path(self.model_path).exists():
                log_error(f"YOLO模型文件不存在: {self.model_path}", "YOLO_ENGINE")
                self.enabled = False
                return
            
            # 加载模型
            try:
                self.model = YOLO(str(self.model_path))
                log_success(f"YOLO模型加载成功: {self.model_path}", "YOLO_ENGINE")
            except Exception as e:
                log_error(f"YOLO模型加载失败: {e}", "YOLO_ENGINE")
                self.enabled = False
                return
            
        except Exception as e:
            log_error(f"YOLO引擎初始化失败: {e}", "YOLO_ENGINE")
            self.enabled = False
    
    def _recognize_image(self, image_path: str) -> Dict[str, Any]:
        """使用YOLO识别图片"""
        try:
            if not self.ultralytics_available or not self.model:
                return {
                    'success': False,
                    'error': 'YOLO引擎不可用'
                }
            
            # 执行预测
            results = self.model(image_path, verbose=False)
            
            if not results or len(results) == 0:
                return {
                    'success': False,
                    'error': '没有检测结果'
                }
            
            # 解析结果
            result = results[0]
            
            if result.boxes is None or len(result.boxes) == 0:
                return {
                    'success': False,
                    'error': '未检测到扑克牌'
                }
            
            # 获取最佳检测结果
            boxes = result.boxes
            confidences = boxes.conf.cpu().numpy()
            classes = boxes.cls.cpu().numpy()
            
            # 置信度过滤
            confidence_threshold = self.config.get('confidence_threshold', 0.5)
            valid_indices = confidences >= confidence_threshold
            
            if not any(valid_indices):
                return {
                    'success': False,
                    'error': f'检测置信度低于阈值 {confidence_threshold}'
                }
            
            # 选择置信度最高的检测
            max_conf_idx = confidences.argmax()
            best_confidence = float(confidences[max_conf_idx])
            best_class = int(classes[max_conf_idx])
            
            # 获取类别名称
            class_names = result.names
            if best_class in class_names:
                class_name = class_names[best_class]
            else:
                class_name = f"class_{best_class}"
            
            # 解析扑克牌信息
            card_info = self._parse_card_name(class_name)
            
            return {
                'success': True,
                'suit': card_info['suit'],
                'rank': card_info['rank'],
                'suit_name': card_info['suit_name'],
                'suit_symbol': card_info['suit_symbol'],
                'display_name': card_info['display_name'],
                'confidence': best_confidence,
                'class_name': class_name,
                'class_id': best_class,
                'total_detections': len(boxes),
                'parsed_successfully': card_info['parsed']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'YOLO识别异常: {str(e)}'
            }
    
    def _parse_card_name(self, class_name: str) -> Dict[str, Any]:
        """解析扑克牌类别名称"""
        try:
            # 扑克牌花色和点数映射
            suit_mapping = {
                'spades': {'name': '黑桃', 'symbol': '♠️', 'en': 'spades'},
                'hearts': {'name': '红桃', 'symbol': '♥️', 'en': 'hearts'},
                'diamonds': {'name': '方块', 'symbol': '♦️', 'en': 'diamonds'},
                'clubs': {'name': '梅花', 'symbol': '♣️', 'en': 'clubs'},
                's': {'name': '黑桃', 'symbol': '♠️', 'en': 'spades'},
                'h': {'name': '红桃', 'symbol': '♥️', 'en': 'hearts'},
                'd': {'name': '方块', 'symbol': '♦️', 'en': 'diamonds'},
                'c': {'name': '梅花', 'symbol': '♣️', 'en': 'clubs'}
            }
            
            rank_mapping = {
                'A': 'A', 'a': 'A',
                '2': '2', '3': '3', '4': '4', '5': '5',
                '6': '6', '7': '7', '8': '8', '9': '9', '10': '10',
                'J': 'J', 'j': 'J',
                'Q': 'Q', 'q': 'Q', 
                'K': 'K', 'k': 'K',
                'T': '10'  # 有时10用T表示
            }
            
            # 尝试解析不同格式的类别名称
            class_name = class_name.lower().strip()
            
            suit = None
            rank = None
            
            # 格式1: "spades_A", "hearts_K" 等
            if '_' in class_name:
                parts = class_name.split('_')
                if len(parts) == 2:
                    suit_part, rank_part = parts
                    if suit_part in suit_mapping:
                        suit = suit_mapping[suit_part]
                    if rank_part.upper() in rank_mapping:
                        rank = rank_mapping[rank_part.upper()]
            
            # 格式2: "SA", "HK", "D10" 等
            elif len(class_name) >= 2:
                suit_char = class_name[0]
                rank_part = class_name[1:]
                
                if suit_char in suit_mapping:
                    suit = suit_mapping[suit_char]
                if rank_part.upper() in rank_mapping:
                    rank = rank_mapping[rank_part.upper()]
            
            # 格式3: 直接包含花色和点数信息
            else:
                # 检查是否包含花色关键词
                for key, value in suit_mapping.items():
                    if key in class_name:
                        suit = value
                        break
                
                # 检查是否包含点数关键词
                for key, value in rank_mapping.items():
                    if key.lower() in class_name:
                        rank = value
                        break
            
            # 如果解析失败，返回原始类别名称
            if suit is None or rank is None:
                return {
                    "suit": "unknown",
                    "rank": "unknown",
                    "suit_name": "未知",
                    "suit_symbol": "?",
                    "display_name": class_name,
                    "parsed": False
                }
            
            return {
                "suit": suit['en'],
                "rank": rank,
                "suit_name": suit['name'],
                "suit_symbol": suit['symbol'],
                "display_name": f"{suit['symbol']}{rank}",
                "parsed": True
            }
            
        except Exception as e:
            return {
                "suit": "error",
                "rank": "error",
                "suit_name": "解析错误",
                "suit_symbol": "?",
                "display_name": f"解析失败: {str(e)}",
                "parsed": False
            }
    
    def is_available(self) -> bool:
        """检查YOLO引擎是否可用"""
        return (self.enabled and 
                self.ultralytics_available and 
                self.model is not None and
                Path(self.model_path).exists() if self.model_path else False)
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        info = {
            'model_path': str(self.model_path) if self.model_path else None,
            'model_loaded': self.model is not None,
            'ultralytics_available': self.ultralytics_available,
            'confidence_threshold': self.config.get('confidence_threshold', 0.5),
            'nms_threshold': self.config.get('nms_threshold', 0.4)
        }
        
        # 如果模型已加载，添加更多信息
        if self.model:
            try:
                info['model_names'] = getattr(self.model, 'names', {})
                info['model_type'] = str(type(self.model))
            except:
                pass
        
        return info

if __name__ == "__main__":
    print("🧪 测试YOLO识别引擎")
    
    # 测试配置
    test_config = {
        'enabled': True,
        'priority': 1,
        'model_path': 'src/config/yolov8/best.pt',
        'confidence_threshold': 0.5,
        'nms_threshold': 0.4
    }
    
    # 创建YOLO引擎
    yolo_engine = YOLOEngine(test_config)
    
    print(f"引擎信息: {yolo_engine}")
    print(f"引擎可用: {yolo_engine.is_available()}")
    
    # 获取模型信息
    model_info = yolo_engine.get_model_info()
    print(f"模型信息: {model_info}")
    
    # 获取引擎统计
    stats = yolo_engine.get_stats()
    print(f"引擎统计: {stats}")
    
    print("✅ YOLO引擎测试完成")