#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础识别引擎 - 所有识别引擎的基类
功能:
1. 定义识别引擎的基础接口
2. 提供通用的结果格式化方法
3. 统一的错误处理机制
4. 性能监控和日志记录
"""

import sys
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import time
from datetime import datetime

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

from src.core.utils import (
    format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)

class BaseEngine(ABC):
    """基础识别引擎抽象类"""
    
    def __init__(self, engine_name: str, config: Dict[str, Any] = None):
        """
        初始化基础引擎
        
        Args:
            engine_name: 引擎名称
            config: 引擎配置
        """
        self.engine_name = engine_name
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.priority = self.config.get('priority', 10)
        
        # 性能统计
        self.stats = {
            'total_recognitions': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'total_time': 0.0,
            'average_time': 0.0,
            'last_recognition_time': None,
            'last_error': None
        }
        
        # 初始化引擎
        self._initialize_engine()
        
        log_info(f"{self.engine_name} 引擎初始化完成", "ENGINE")
    
    @abstractmethod
    def _initialize_engine(self):
        """初始化引擎 - 子类必须实现"""
        pass
    
    @abstractmethod
    def _recognize_image(self, image_path: str) -> Dict[str, Any]:
        """识别图片 - 子类必须实现"""
        pass
    
    def recognize(self, image_path: str) -> Dict[str, Any]:
        """
        统一的识别接口
        
        Args:
            image_path: 图片路径
            
        Returns:
            识别结果
        """
        if not self.enabled:
            return format_error_response(f"{self.engine_name} 引擎已禁用", "ENGINE_DISABLED")
        
        # 检查图片文件
        if not Path(image_path).exists():
            return format_error_response(f"图片文件不存在: {image_path}", "FILE_NOT_FOUND")
        
        start_time = time.time()
        
        try:
            # 更新统计
            self.stats['total_recognitions'] += 1
            
            # 执行识别
            result = self._recognize_image(image_path)
            
            # 计算耗时
            duration = time.time() - start_time
            self.stats['total_time'] += duration
            self.stats['average_time'] = self.stats['total_time'] / self.stats['total_recognitions']
            self.stats['last_recognition_time'] = get_timestamp()
            
            # 格式化结果
            if result.get('success', False):
                self.stats['successful_recognitions'] += 1
                formatted_result = self._format_success_result(result, duration)
                log_info(f"{self.engine_name} 识别成功: {formatted_result.get('display_name', 'Unknown')}", "ENGINE")
                return formatted_result
            else:
                self.stats['failed_recognitions'] += 1
                self.stats['last_error'] = result.get('error', 'Unknown error')
                log_warning(f"{self.engine_name} 识别失败: {self.stats['last_error']}", "ENGINE")
                return self._format_error_result(result, duration)
                
        except Exception as e:
            duration = time.time() - start_time
            self.stats['failed_recognitions'] += 1
            self.stats['last_error'] = str(e)
            
            error_msg = f"{self.engine_name} 识别异常: {str(e)}"
            log_error(error_msg, "ENGINE")
            
            return format_error_response(error_msg, "RECOGNITION_EXCEPTION", duration=duration)
    
    def _format_success_result(self, result: Dict[str, Any], duration: float) -> Dict[str, Any]:
        """格式化成功结果"""
        return {
            'success': True,
            'engine': self.engine_name,
            'suit': result.get('suit', ''),
            'rank': result.get('rank', ''),
            'suit_name': result.get('suit_name', ''),
            'suit_symbol': result.get('suit_symbol', ''),
            'display_name': result.get('display_name', ''),
            'confidence': result.get('confidence', 0.0),
            'duration': duration,
            'timestamp': get_timestamp(),
            'raw_result': result
        }
    
    def _format_error_result(self, result: Dict[str, Any], duration: float) -> Dict[str, Any]:
        """格式化错误结果"""
        return {
            'success': False,
            'engine': self.engine_name,
            'error': result.get('error', 'Recognition failed'),
            'duration': duration,
            'timestamp': get_timestamp(),
            'raw_result': result
        }
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            'name': self.engine_name,
            'enabled': self.enabled,
            'priority': self.priority,
            'config': self.config,
            'stats': self.stats.copy()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        stats = self.stats.copy()
        
        # 计算成功率
        if stats['total_recognitions'] > 0:
            stats['success_rate'] = stats['successful_recognitions'] / stats['total_recognitions']
        else:
            stats['success_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_recognitions': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'total_time': 0.0,
            'average_time': 0.0,
            'last_recognition_time': None,
            'last_error': None
        }
        log_info(f"{self.engine_name} 统计信息已重置", "ENGINE")
    
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return self.enabled
    
    def enable(self):
        """启用引擎"""
        self.enabled = True
        log_info(f"{self.engine_name} 引擎已启用", "ENGINE")
    
    def disable(self):
        """禁用引擎"""
        self.enabled = False
        log_info(f"{self.engine_name} 引擎已禁用", "ENGINE")
    
    def validate_image(self, image_path: str) -> bool:
        """验证图片文件"""
        try:
            image_file = Path(image_path)
            
            # 检查文件存在
            if not image_file.exists():
                return False
            
            # 检查文件大小
            if image_file.stat().st_size == 0:
                return False
            
            # 检查文件扩展名
            valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
            if image_file.suffix.lower() not in valid_extensions:
                return False
            
            return True
            
        except Exception:
            return False
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.engine_name}Engine(enabled={self.enabled}, priority={self.priority})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"{self.__class__.__name__}("
                f"name='{self.engine_name}', "
                f"enabled={self.enabled}, "
                f"priority={self.priority}, "
                f"recognitions={self.stats['total_recognitions']})")

if __name__ == "__main__":
    # 测试基础引擎（创建一个简单的实现用于测试）
    class TestEngine(BaseEngine):
        def _initialize_engine(self):
            pass
        
        def _recognize_image(self, image_path: str) -> Dict[str, Any]:
            # 简单的测试实现
            return {
                'success': True,
                'suit': 'hearts',
                'rank': 'A',
                'suit_name': '红桃',
                'suit_symbol': '♥️',
                'display_name': '♥️A',
                'confidence': 0.95
            }
    
    print("🧪 测试基础识别引擎")
    
    # 创建测试引擎
    engine = TestEngine("Test", {'enabled': True, 'priority': 1})
    
    print(f"引擎信息: {engine}")
    print(f"引擎详情: {repr(engine)}")
    
    # 获取引擎信息
    info = engine.get_engine_info()
    print(f"引擎配置: {info}")
    
    # 获取统计信息
    stats = engine.get_stats()
    print(f"统计信息: {stats}")
    
    print("✅ 基础引擎测试完成")