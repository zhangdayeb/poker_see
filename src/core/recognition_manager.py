#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别结果管理模块 - 处理扑克牌识别结果的接收、保存和查询
功能:
1. 接收识别结果数据
2. 保存识别结果到文件
3. 获取最新识别结果
4. 格式化识别结果供荷官端使用
5. 识别结果数据验证
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from utils import (
    get_timestamp, safe_json_load, safe_json_dump, 
    format_success_response, format_error_response,
    get_result_dir, log_info, log_success, log_error, log_warning
)

class RecognitionManager:
    """识别结果管理器"""
    
    def __init__(self):
        """初始化识别结果管理器"""
        self.result_dir = get_result_dir()
        self.latest_file = self.result_dir / "latest_recognition.json"
        self.history_dir = self.result_dir / "history"
        
        # 确保目录存在
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        log_info("识别结果管理器初始化完成", "RECOGNITION")
    
    def receive_recognition_data(self, recognition_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收识别结果数据
        
        Args:
            recognition_data: 识别结果数据
            
        Returns:
            处理结果响应
        """
        try:
            # 验证数据格式
            if not self._validate_recognition_data(recognition_data):
                return format_error_response("识别结果数据格式无效", "INVALID_DATA")
            
            # 添加接收时间戳
            recognition_data['received_at'] = get_timestamp()
            
            # 保存最新结果
            if not self._save_latest_result(recognition_data):
                return format_error_response("保存识别结果失败", "SAVE_FAILED")
            
            # 保存历史记录
            self._save_history_result(recognition_data)
            
            # 统计识别结果
            stats = self._calculate_recognition_stats(recognition_data)
            
            log_success(f"接收识别结果成功: {stats['recognized_count']}/{stats['total_positions']} 个位置", "RECOGNITION")
            
            return format_success_response(
                "识别结果接收成功",
                data={
                    "stats": stats,
                    "received_at": recognition_data['received_at']
                }
            )
            
        except Exception as e:
            log_error(f"接收识别结果失败: {e}", "RECOGNITION")
            return format_error_response(f"接收识别结果失败: {str(e)}", "RECEIVE_ERROR")
    
    def get_latest_recognition(self) -> Dict[str, Any]:
        """
        获取最新的识别结果
        
        Returns:
            最新识别结果
        """
        try:
            if not self.latest_file.exists():
                # 返回默认的空结果
                return self._get_empty_recognition_result()
            
            # 读取最新结果
            recognition_data = safe_json_load(self.latest_file)
            if not recognition_data:
                return self._get_empty_recognition_result()
            
            # 格式化返回数据
            return format_success_response(
                "获取识别结果成功",
                data=recognition_data
            )
            
        except Exception as e:
            log_error(f"获取识别结果失败: {e}", "RECOGNITION")
            return format_error_response(f"获取识别结果失败: {str(e)}", "GET_ERROR")
    
    def format_for_dealer(self, include_metadata: bool = True) -> Dict[str, Any]:
        """
        格式化识别结果供荷官端使用
        
        Args:
            include_metadata: 是否包含元数据
            
        Returns:
            格式化后的识别结果
        """
        try:
            latest_result = self.get_latest_recognition()
            
            if latest_result['status'] != 'success':
                return latest_result
            
            recognition_data = latest_result['data']
            positions = recognition_data.get('positions', {})
            
            # 格式化位置数据
            formatted_positions = {}
            for position, data in positions.items():
                formatted_positions[position] = {
                    'suit': data.get('suit', ''),
                    'rank': data.get('rank', ''),
                    'confidence': round(data.get('confidence', 0.0), 3),
                    'recognized': bool(data.get('suit') and data.get('rank'))
                }
            
            result = {
                'positions': formatted_positions,
                'timestamp': recognition_data.get('received_at', get_timestamp())
            }
            
            if include_metadata:
                stats = self._calculate_recognition_stats(recognition_data)
                result['metadata'] = {
                    'total_cameras': recognition_data.get('total_cameras', 0),
                    'total_positions': stats['total_positions'],
                    'recognized_count': stats['recognized_count'],
                    'recognition_rate': stats['recognition_rate']
                }
            
            return format_success_response("荷官端数据格式化成功", data=result)
            
        except Exception as e:
            log_error(f"格式化荷官端数据失败: {e}", "RECOGNITION")
            return format_error_response(f"格式化数据失败: {str(e)}", "FORMAT_ERROR")
    
    def get_recognition_history(self, limit: int = 10) -> Dict[str, Any]:
        """
        获取识别结果历史记录
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            历史记录列表
        """
        try:
            history_files = list(self.history_dir.glob("recognition_*.json"))
            history_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            history_list = []
            for file_path in history_files[:limit]:
                data = safe_json_load(file_path)
                if data:
                    # 只保留关键信息
                    summary = {
                        'timestamp': data.get('received_at', ''),
                        'total_cameras': data.get('total_cameras', 0),
                        'recognized_count': sum(1 for pos in data.get('positions', {}).values() 
                                              if pos.get('suit') and pos.get('rank')),
                        'file_name': file_path.name
                    }
                    history_list.append(summary)
            
            return format_success_response(
                f"获取历史记录成功",
                data={
                    'history': history_list,
                    'total_count': len(history_files)
                }
            )
            
        except Exception as e:
            log_error(f"获取历史记录失败: {e}", "RECOGNITION")
            return format_error_response(f"获取历史记录失败: {str(e)}", "HISTORY_ERROR")
    
    def _validate_recognition_data(self, data: Dict[str, Any]) -> bool:
        """验证识别结果数据格式"""
        try:
            # 检查基本结构
            if not isinstance(data, dict):
                log_warning("识别数据不是字典格式", "RECOGNITION")
                return False
            
            # 检查positions字段
            positions = data.get('positions', {})
            if not isinstance(positions, dict):
                log_warning("positions字段格式错误", "RECOGNITION")
                return False
            
            # 验证每个位置的数据
            valid_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
            for position, position_data in positions.items():
                if not isinstance(position_data, dict):
                    continue
                
                # 检查字段类型
                if 'confidence' in position_data:
                    try:
                        float(position_data['confidence'])
                    except (ValueError, TypeError):
                        log_warning(f"位置 {position} 的置信度格式错误", "RECOGNITION")
            
            return True
            
        except Exception as e:
            log_error(f"数据验证失败: {e}", "RECOGNITION")
            return False
    
    def _save_latest_result(self, data: Dict[str, Any]) -> bool:
        """保存最新识别结果"""
        try:
            return safe_json_dump(data, self.latest_file)
        except Exception as e:
            log_error(f"保存最新结果失败: {e}", "RECOGNITION")
            return False
    
    def _save_history_result(self, data: Dict[str, Any]) -> bool:
        """保存历史识别结果"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            history_file = self.history_dir / f"recognition_{timestamp}.json"
            return safe_json_dump(data, history_file)
        except Exception as e:
            log_error(f"保存历史结果失败: {e}", "RECOGNITION")
            return False
    
    def _calculate_recognition_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """计算识别统计信息"""
        positions = data.get('positions', {})
        total_positions = len(positions)
        recognized_count = sum(1 for pos in positions.values() 
                             if isinstance(pos, dict) and pos.get('suit') and pos.get('rank'))
        
        recognition_rate = (recognized_count / total_positions * 100) if total_positions > 0 else 0
        
        return {
            'total_positions': total_positions,
            'recognized_count': recognized_count,
            'recognition_rate': round(recognition_rate, 1)
        }
    
    def _get_empty_recognition_result(self) -> Dict[str, Any]:
        """获取默认的空识别结果"""
        empty_positions = {}
        default_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        for position in default_positions:
            empty_positions[position] = {
                'suit': '',
                'rank': '',
                'confidence': 0.0
            }
        
        return format_success_response(
            "暂无识别结果",
            data={
                'positions': empty_positions,
                'total_cameras': 0,
                'received_at': get_timestamp()
            }
        )
    
    def cleanup_old_history(self, keep_count: int = 50) -> int:
        """清理旧的历史记录文件"""
        try:
            history_files = list(self.history_dir.glob("recognition_*.json"))
            if len(history_files) <= keep_count:
                return 0
            
            # 按修改时间排序，保留最新的
            history_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            deleted_count = 0
            for file_to_delete in history_files[keep_count:]:
                try:
                    file_to_delete.unlink()
                    deleted_count += 1
                except OSError as e:
                    log_error(f"删除历史文件失败 {file_to_delete}: {e}", "RECOGNITION")
            
            if deleted_count > 0:
                log_info(f"清理了 {deleted_count} 个历史记录文件", "RECOGNITION")
            
            return deleted_count
            
        except Exception as e:
            log_error(f"清理历史文件失败: {e}", "RECOGNITION")
            return 0

# 创建全局实例
recognition_manager = RecognitionManager()

# 导出主要函数
def receive_recognition_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """接收识别结果数据"""
    return recognition_manager.receive_recognition_data(data)

def get_latest_recognition() -> Dict[str, Any]:
    """获取最新识别结果"""
    return recognition_manager.get_latest_recognition()

def format_for_dealer(include_metadata: bool = True) -> Dict[str, Any]:
    """格式化数据供荷官端使用"""
    return recognition_manager.format_for_dealer(include_metadata)

def get_recognition_history(limit: int = 10) -> Dict[str, Any]:
    """获取识别历史记录"""
    return recognition_manager.get_recognition_history(limit)

def cleanup_old_history(keep_count: int = 50) -> int:
    """清理旧的历史记录"""
    return recognition_manager.cleanup_old_history(keep_count)

if __name__ == "__main__":
    # 测试识别结果管理器
    print("🧪 测试识别结果管理器")
    
    # 测试数据
    test_data = {
        "total_cameras": 2,
        "positions": {
            "zhuang_1": {"suit": "♠", "rank": "A", "confidence": 0.95},
            "zhuang_2": {"suit": "♥", "rank": "K", "confidence": 0.88},
            "zhuang_3": {"suit": "", "rank": "", "confidence": 0.0},
            "xian_1": {"suit": "♦", "rank": "Q", "confidence": 0.92},
            "xian_2": {"suit": "", "rank": "", "confidence": 0.0},
            "xian_3": {"suit": "♣", "rank": "10", "confidence": 0.85}
        }
    }
    
    # 测试接收数据
    result = receive_recognition_data(test_data)
    print(f"接收结果: {result}")
    
    # 测试获取最新结果
    latest = get_latest_recognition()
    print(f"最新结果: {latest}")
    
    # 测试荷官端格式化
    dealer_data = format_for_dealer()
    print(f"荷官端数据: {dealer_data}")
    
    print("✅ 识别结果管理器测试完成")