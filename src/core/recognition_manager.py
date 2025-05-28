#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别结果管理模块 - 处理扑克牌识别结果的接收、保存、查询和推送
功能:
1. 识别结果数据的接收和验证
2. 最新结果和历史记录的保存管理
3. WebSocket推送功能集成
4. 识别结果格式化供荷官端使用
5. 推送配置管理和状态监控
6. 数据统计和清理维护
"""

import sys
from pathlib import Path

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

# 调用路径设置
PROJECT_ROOT = setup_project_paths()

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from src.core.utils import (
    get_timestamp, safe_json_load, safe_json_dump, 
    format_success_response, format_error_response,
    get_result_dir, log_info, log_success, log_error, log_warning
)

class RecognitionManager:
    """识别结果管理器"""
    
    def __init__(self):
        """初始化识别结果管理器"""
        # 标准位置列表
        self.standard_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        # 文件路径设置
        self.result_dir = get_result_dir()
        self.latest_file = self.result_dir / "latest_recognition.json"
        self.history_dir = self.result_dir / "history"
        self.push_config_file = self.result_dir / "push_config.json"
        
        # 确保目录存在
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # 推送客户端状态
        self.push_client = None
        self.push_client_active = False
        
        # 加载推送配置
        self.push_config = self._load_push_config()
        
        log_info("识别结果管理器初始化完成", "RECOGNITION")
    
    def _load_push_config(self) -> Dict[str, Any]:
        """加载推送配置"""
        default_config = {
            "websocket": {
                "enabled": True,
                "server_url": "ws://bjl_heguan_wss.yhyule666.com:8001",
                "client_id": "python_client_001",
                "auto_push": True,
                "retry_times": 3
            },
            "auto_push_on_receive": True,
            "push_filter": {
                "min_confidence": 0.3,
                "positions": self.standard_positions.copy()
            },
            "created_at": get_timestamp(),
            "updated_at": get_timestamp()
        }
        
        try:
            config = safe_json_load(self.push_config_file, default_config)
            
            # 确保配置完整性
            if not isinstance(config, dict):
                config = default_config
            
            # 检查必需字段
            if "websocket" not in config:
                config["websocket"] = default_config["websocket"]
            if "push_filter" not in config:
                config["push_filter"] = default_config["push_filter"]
            
            log_info("推送配置加载成功", "RECOGNITION")
            return config
            
        except Exception as e:
            log_error(f"加载推送配置失败: {e}", "RECOGNITION")
            return default_config
    
    def _save_push_config(self) -> bool:
        """保存推送配置"""
        try:
            self.push_config["updated_at"] = get_timestamp()
            return safe_json_dump(self.push_config, self.push_config_file)
        except Exception as e:
            log_error(f"保存推送配置失败: {e}", "RECOGNITION")
            return False
    
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
            validation_result = self._validate_recognition_data(recognition_data)
            if not validation_result['valid']:
                return format_error_response(
                    f"识别结果数据格式无效: {validation_result['error']}", 
                    "INVALID_DATA"
                )
            
            # 添加接收时间戳和处理信息
            processed_data = recognition_data.copy()
            processed_data['received_at'] = get_timestamp()
            processed_data['processed_by'] = 'recognition_manager'
            processed_data['version'] = '1.0'
            
            # 标准化位置数据
            standardized_data = self._standardize_recognition_data(processed_data)
            
            # 保存最新结果
            if not self._save_latest_result(standardized_data):
                return format_error_response("保存识别结果失败", "SAVE_FAILED")
            
            # 保存历史记录
            self._save_history_result(standardized_data)
            
            # 计算统计信息
            stats = self._calculate_recognition_stats(standardized_data)
            
            # 自动推送（如果启用）
            push_result = None
            if self.push_config.get("auto_push_on_receive", True):
                push_result = self._auto_push_recognition_result(standardized_data)
            
            log_success(f"接收识别结果成功: {stats['recognized_count']}/{stats['total_positions']} 个位置", "RECOGNITION")
            
            response_data = {
                "stats": stats,
                "received_at": standardized_data['received_at'],
                "auto_push_result": push_result
            }
            
            return format_success_response("识别结果接收成功", data=response_data)
            
        except Exception as e:
            log_error(f"接收识别结果失败: {e}", "RECOGNITION")
            return format_error_response(f"接收识别结果失败: {str(e)}", "RECEIVE_ERROR")
    
    def _validate_recognition_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证识别结果数据格式"""
        try:
            # 检查基本结构
            if not isinstance(data, dict):
                return {"valid": False, "error": "数据不是字典格式"}
            
            # 检查positions字段
            positions = data.get('positions', {})
            if not isinstance(positions, dict):
                return {"valid": False, "error": "positions字段格式错误"}
            
            # 验证每个位置的数据
            for position, position_data in positions.items():
                if not isinstance(position_data, dict):
                    continue
                
                # 检查花色和点数字段
                suit = position_data.get('suit', '')
                rank = position_data.get('rank', '')
                
                # 检查置信度字段
                if 'confidence' in position_data:
                    try:
                        confidence = float(position_data['confidence'])
                        if confidence < 0 or confidence > 1:
                            log_warning(f"位置 {position} 的置信度超出范围: {confidence}", "RECOGNITION")
                    except (ValueError, TypeError):
                        return {"valid": False, "error": f"位置 {position} 的置信度格式错误"}
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": f"数据验证异常: {str(e)}"}
    
    def _standardize_recognition_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化识别结果数据"""
        try:
            standardized = data.copy()
            positions = standardized.get('positions', {})
            
            # 确保所有标准位置都存在
            for position in self.standard_positions:
                if position not in positions:
                    positions[position] = {
                        'suit': '',
                        'rank': '',
                        'confidence': 0.0
                    }
                else:
                    # 标准化现有位置数据
                    pos_data = positions[position]
                    if not isinstance(pos_data, dict):
                        positions[position] = {'suit': '', 'rank': '', 'confidence': 0.0}
                    else:
                        # 确保必需字段存在
                        pos_data.setdefault('suit', '')
                        pos_data.setdefault('rank', '')
                        pos_data.setdefault('confidence', 0.0)
                        
                        # 标准化置信度
                        try:
                            pos_data['confidence'] = max(0.0, min(1.0, float(pos_data['confidence'])))
                        except (ValueError, TypeError):
                            pos_data['confidence'] = 0.0
            
            standardized['positions'] = positions
            return standardized
            
        except Exception as e:
            log_error(f"标准化识别数据失败: {e}", "RECOGNITION")
            return data
    
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
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # 包含毫秒
            history_file = self.history_dir / f"recognition_{timestamp}.json"
            return safe_json_dump(data, history_file)
        except Exception as e:
            log_error(f"保存历史结果失败: {e}", "RECOGNITION")
            return False
    
    def _calculate_recognition_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """计算识别统计信息"""
        positions = data.get('positions', {})
        total_positions = len(self.standard_positions)
        recognized_count = 0
        high_confidence_count = 0
        avg_confidence = 0.0
        
        confidences = []
        
        for position in self.standard_positions:
            pos_data = positions.get(position, {})
            suit = pos_data.get('suit', '')
            rank = pos_data.get('rank', '')
            confidence = pos_data.get('confidence', 0.0)
            
            if suit and rank:
                recognized_count += 1
                confidences.append(confidence)
                
                if confidence >= 0.8:
                    high_confidence_count += 1
        
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
        
        recognition_rate = (recognized_count / total_positions * 100) if total_positions > 0 else 0
        
        return {
            'total_positions': total_positions,
            'recognized_count': recognized_count,
            'high_confidence_count': high_confidence_count,
            'recognition_rate': round(recognition_rate, 1),
            'average_confidence': round(avg_confidence, 3),
            'timestamp': get_timestamp()
        }
    
    def _auto_push_recognition_result(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """自动推送识别结果"""
        try:
            # 检查是否启用推送
            if not self.push_config.get("auto_push_on_receive", True):
                return None
            
            ws_config = self.push_config.get("websocket", {})
            if not ws_config.get("enabled", True):
                return None
            
            # 尝试推送到WebSocket
            return self._push_to_websocket(data)
            
        except Exception as e:
            log_error(f"自动推送失败: {e}", "RECOGNITION")
            return {"status": "error", "message": str(e)}
    
    def _push_to_websocket(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """推送到WebSocket服务器"""
        try:
            # 尝试导入并使用WebSocket客户端
            try:
                from src.clients.websocket_client import push_recognition_result
                
                # 提取位置数据进行推送
                positions = data.get('positions', {})
                camera_id = data.get('camera_id', 'camera_001')
                
                # 格式化推送数据
                push_positions = {}
                for position, pos_data in positions.items():
                    if isinstance(pos_data, dict):
                        push_positions[position] = {
                            'suit': pos_data.get('suit', ''),
                            'rank': pos_data.get('rank', '')
                        }
                
                # 推送结果
                push_result = push_recognition_result(camera_id, push_positions)
                
                if push_result['status'] == 'success':
                    log_success("识别结果WebSocket推送成功", "RECOGNITION")
                else:
                    log_warning(f"识别结果WebSocket推送失败: {push_result.get('message', 'Unknown error')}", "RECOGNITION")
                
                return push_result
                
            except ImportError:
                log_warning("WebSocket客户端模块不可用", "RECOGNITION")
                return {"status": "error", "message": "WebSocket客户端不可用"}
                
        except Exception as e:
            log_error(f"WebSocket推送异常: {e}", "RECOGNITION")
            return {"status": "error", "message": str(e)}
    
    def get_latest_recognition(self) -> Dict[str, Any]:
        """
        获取最新的识别结果
        
        Returns:
            最新识别结果
        """
        try:
            if not self.latest_file.exists():
                return self._get_empty_recognition_result()
            
            # 读取最新结果
            recognition_data = safe_json_load(self.latest_file)
            if not recognition_data:
                return self._get_empty_recognition_result()
            
            return format_success_response("获取识别结果成功", data=recognition_data)
            
        except Exception as e:
            log_error(f"获取识别结果失败: {e}", "RECOGNITION")
            return format_error_response(f"获取识别结果失败: {str(e)}", "GET_ERROR")
    
    def _get_empty_recognition_result(self) -> Dict[str, Any]:
        """获取默认的空识别结果"""
        empty_positions = {}
        
        for position in self.standard_positions:
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
                'received_at': get_timestamp(),
                'empty_result': True
            }
        )
    
    def get_push_config(self) -> Dict[str, Any]:
        """获取推送配置"""
        try:
            return format_success_response(
                "获取推送配置成功",
                data=self.push_config
            )
        except Exception as e:
            log_error(f"获取推送配置失败: {e}", "RECOGNITION")
            return format_error_response(f"获取推送配置失败: {str(e)}", "GET_CONFIG_ERROR")
    
    def update_push_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """更新推送配置"""
        try:
            if not isinstance(new_config, dict):
                return format_error_response("配置数据格式无效", "INVALID_CONFIG")
            
            # 更新配置
            self.push_config.update(new_config)
            
            # 保存配置
            if self._save_push_config():
                log_success("推送配置更新成功", "RECOGNITION")
                return format_success_response("推送配置更新成功", data=self.push_config)
            else:
                return format_error_response("保存推送配置失败", "SAVE_CONFIG_ERROR")
                
        except Exception as e:
            log_error(f"更新推送配置失败: {e}", "RECOGNITION")
            return format_error_response(f"更新推送配置失败: {str(e)}", "UPDATE_CONFIG_ERROR")
    
    def get_push_status(self) -> Dict[str, Any]:
        """获取推送状态"""
        try:
            status_data = {
                "websocket": {
                    "enabled": self.push_config.get("websocket", {}).get("enabled", False),
                    "server_url": self.push_config.get("websocket", {}).get("server_url", ""),
                    "client_id": self.push_config.get("websocket", {}).get("client_id", ""),
                    "auto_push": self.push_config.get("websocket", {}).get("auto_push", False)
                },
                "auto_push_on_receive": self.push_config.get("auto_push_on_receive", True),
                "push_filter": self.push_config.get("push_filter", {}),
                "last_updated": self.push_config.get("updated_at", "")
            }
            
            # 尝试获取WebSocket客户端状态
            try:
                from src.clients.websocket_client import get_push_client_status
                ws_status = get_push_client_status()
                if ws_status['status'] == 'success':
                    status_data["websocket"]["client_status"] = ws_status['data']
                else:
                    status_data["websocket"]["client_status"] = {"error": ws_status.get('message', 'Unknown error')}
            except ImportError:
                status_data["websocket"]["client_status"] = {"error": "WebSocket客户端模块不可用"}
            
            return format_success_response("获取推送状态成功", data=status_data)
            
        except Exception as e:
            log_error(f"获取推送状态失败: {e}", "RECOGNITION")
            return format_error_response(f"获取推送状态失败: {str(e)}", "GET_STATUS_ERROR")
    
    def manual_push_recognition_result(self, push_type: str = 'websocket', camera_id: str = None) -> Dict[str, Any]:
        """手动推送识别结果"""
        try:
            # 获取最新识别结果
            latest_result = self.get_latest_recognition()
            if latest_result['status'] != 'success':
                return format_error_response("没有可推送的识别结果", "NO_DATA")
            
            data = latest_result['data']
            
            # 设置摄像头ID
            if camera_id:
                data['camera_id'] = camera_id
            
            # 根据推送类型进行推送
            if push_type == 'websocket':
                push_result = self._push_to_websocket(data)
                
                if push_result['status'] == 'success':
                    log_success("手动WebSocket推送成功", "RECOGNITION")
                    return format_success_response("手动推送成功", data=push_result)
                else:
                    return format_error_response(f"手动推送失败: {push_result.get('message', 'Unknown error')}", "PUSH_FAILED")
            else:
                return format_error_response(f"不支持的推送类型: {push_type}", "UNSUPPORTED_PUSH_TYPE")
                
        except Exception as e:
            log_error(f"手动推送失败: {e}", "RECOGNITION")
            return format_error_response(f"手动推送失败: {str(e)}", "MANUAL_PUSH_ERROR")
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            # 统计历史记录数量
            history_count = 0
            if self.history_dir.exists():
                history_count = len(list(self.history_dir.glob("recognition_*.json")))
            
            # 获取最新结果状态
            latest_exists = self.latest_file.exists()
            latest_size = self.latest_file.stat().st_size if latest_exists else 0
            
            # 计算目录大小
            total_size = 0
            if self.result_dir.exists():
                for file_path in self.result_dir.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
            
            stats_data = {
                "recognition": {
                    "total_recognitions": history_count,
                    "latest_result_exists": latest_exists,
                    "latest_result_size": latest_size
                },
                "storage": {
                    "result_directory": str(self.result_dir),
                    "history_directory": str(self.history_dir),
                    "total_files": history_count + (1 if latest_exists else 0),
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2)
                },
                "push_config": {
                    "websocket_enabled": self.push_config.get("websocket", {}).get("enabled", False),
                    "auto_push_enabled": self.push_config.get("auto_push_on_receive", True),
                    "last_config_update": self.push_config.get("updated_at", "")
                },
                "system": {
                    "result_dir_exists": self.result_dir.exists(),
                    "history_dir_exists": self.history_dir.exists(),
                    "push_config_file_exists": self.push_config_file.exists()
                }
            }
            
            return format_success_response("获取系统统计成功", data=stats_data)
            
        except Exception as e:
            log_error(f"获取系统统计失败: {e}", "RECOGNITION")
            return format_error_response(f"获取系统统计失败: {str(e)}", "GET_STATS_ERROR")
    
    def cleanup_old_history(self, keep_count: int = 100) -> Dict[str, Any]:
        """清理老的历史记录"""
        try:
            if not self.history_dir.exists():
                return format_success_response("历史目录不存在，无需清理", data={"deleted_count": 0})
            
            # 获取所有历史文件，按时间排序
            history_files = list(self.history_dir.glob("recognition_*.json"))
            history_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # 删除超出保留数量的文件
            deleted_count = 0
            files_to_delete = history_files[keep_count:]
            
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except OSError as e:
                    log_error(f"删除历史文件失败 {file_path}: {e}", "RECOGNITION")
            
            log_success(f"清理历史记录完成，删除了 {deleted_count} 个文件", "RECOGNITION")
            
            return format_success_response(
                f"清理历史记录成功，删除了 {deleted_count} 个文件",
                data={
                    "deleted_count": deleted_count,
                    "remaining_count": len(history_files) - deleted_count,
                    "keep_count": keep_count
                }
            )
            
        except Exception as e:
            log_error(f"清理历史记录失败: {e}", "RECOGNITION")
            return format_error_response(f"清理历史记录失败: {str(e)}", "CLEANUP_ERROR")

# 创建全局实例
recognition_manager = RecognitionManager()

# 导出主要函数
def receive_recognition_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """接收识别结果数据"""
    return recognition_manager.receive_recognition_data(data)

def get_latest_recognition() -> Dict[str, Any]:
    """获取最新识别结果"""
    return recognition_manager.get_latest_recognition()

def get_push_config() -> Dict[str, Any]:
    """获取推送配置"""
    return recognition_manager.get_push_config()

def update_push_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """更新推送配置"""
    return recognition_manager.update_push_config(config)

def get_push_status() -> Dict[str, Any]:
    """获取推送状态"""
    return recognition_manager.get_push_status()

def manual_push_recognition_result(push_type: str = 'websocket', camera_id: str = None) -> Dict[str, Any]:
    """手动推送识别结果"""
    return recognition_manager.manual_push_recognition_result(push_type, camera_id)

def get_system_statistics() -> Dict[str, Any]:
    """获取系统统计信息"""
    return recognition_manager.get_system_statistics()

def cleanup_old_history(keep_count: int = 100) -> Dict[str, Any]:
    """清理老的历史记录"""
    return recognition_manager.cleanup_old_history(keep_count)

if __name__ == "__main__":
    # 测试识别结果管理器
    print("🧪 测试识别结果管理器")
    
    # 测试接收识别数据
    test_data = {
        "camera_id": "camera_001",
        "positions": {
            "zhuang_1": {"suit": "hearts", "rank": "A", "confidence": 0.95},
            "zhuang_2": {"suit": "spades", "rank": "K", "confidence": 0.88},
            "xian_1": {"suit": "diamonds", "rank": "Q", "confidence": 0.92}
        },
        "timestamp": get_timestamp()
    }
    
    result = receive_recognition_data(test_data)
    print(f"接收识别数据: {result['status']}")
    
    # 测试获取最新结果
    latest = get_latest_recognition()
    print(f"获取最新结果: {latest['status']}")
    
    # 测试推送配置
    push_config = get_push_config()
    print(f"获取推送配置: {push_config['status']}")
    
    # 测试推送状态
    push_status = get_push_status()
    print(f"获取推送状态: {push_status['status']}")
    
    # 测试系统统计
    stats = get_system_statistics()
    print(f"获取系统统计: {stats['status']}")
    
    print("✅ 识别结果管理器测试完成")