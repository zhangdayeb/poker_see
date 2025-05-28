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
        
        # 标准位置列表
        self.standard_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        log_info("识别结果管理器初始化完成", "RECOGNITION")
    
    def _load_push_config(self) -> Dict[str, Any]:
        """加载推送配置"""
        default_config = {
            "websocket": {
                "enabled": True,
                "server_url": "ws://localhost:8001",
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
            for position in self.standard_positions:
                pos_data = positions.get(position, {})
                formatted_positions[position] = {
                    'suit': pos_data.get('suit', ''),
                    'rank': pos_data.get('rank', ''),
                    'confidence': round(pos_data.get('confidence', 0.0), 3),
                    'recognized': bool(pos_data.get('suit') and pos_data.get('rank'))
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
                    'recognition_rate': stats['recognition_rate'],
                    'average_confidence': stats['average_confidence']
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
                try:
                    data = safe_json_load(file_path)
                    if data:
                        # 计算统计信息
                        stats = self._calculate_recognition_stats(data)
                        
                        summary = {
                            'timestamp': data.get('received_at', ''),
                            'total_cameras': data.get('total_cameras', 0),
                            'recognized_count': stats['recognized_count'],
                            'recognition_rate': stats['recognition_rate'],
                            'average_confidence': stats['average_confidence'],
                            'file_name': file_path.name
                        }
                        history_list.append(summary)
                except Exception as e:
                    log_warning(f"读取历史文件失败 {file_path}: {e}", "RECOGNITION")
                    continue
            
            return format_success_response(
                f"获取历史记录成功",
                data={
                    'history': history_list,
                    'total_files': len(history_files),
                    'returned_count': len(history_list)
                }
            )
            
        except Exception as e:
            log_error(f"获取历史记录失败: {e}", "RECOGNITION")
            return format_error_response(f"获取历史记录失败: {str(e)}", "HISTORY_ERROR")
    
    # ==================== 推送功能 ====================
    
    def setup_push_client(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """设置推送客户端"""
        try:
            # 导入WebSocket客户端
            try:
                from src.clients.websocket_client import WebSocketPushClient
            except ImportError:
                return format_error_response("WebSocket客户端模块不可用", "WEBSOCKET_NOT_AVAILABLE")
            
            # 使用提供的配置或默认配置
            ws_config = config or self.push_config.get("websocket", {})
            
            if not ws_config.get("enabled", True):
                return format_error_response("WebSocket推送已禁用", "WEBSOCKET_DISABLED")
            
            # 创建推送客户端
            server_url = ws_config.get("server_url", "ws://localhost:8001")
            client_id = ws_config.get("client_id", "python_client_001")
            
            self.push_client = WebSocketPushClient(server_url, client_id)
            start_result = self.push_client.start()
            
            if start_result['status'] == 'success':
                self.push_client_active = True
                log_success(f"推送客户端设置成功: {server_url}", "RECOGNITION")
            else:
                self.push_client_active = False
                log_error(f"推送客户端启动失败: {start_result['message']}", "RECOGNITION")
            
            return start_result
            
        except Exception as e:
            log_error(f"设置推送客户端失败: {e}", "RECOGNITION")
            return format_error_response(f"设置推送客户端失败: {str(e)}", "SETUP_PUSH_ERROR")
    
    def push_recognition_result(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """推送识别结果"""
        try:
            # 获取要推送的数据
            if data is None:
                latest_result = self.get_latest_recognition()
                if latest_result['status'] != 'success':
                    return format_error_response("没有可推送的识别结果", "NO_DATA_TO_PUSH")
                data = latest_result['data']
            
            # 检查推送客户端状态
            if not self.push_client_active or not self.push_client:
                # 尝试设置推送客户端
                setup_result = self.setup_push_client()
                if setup_result['status'] != 'success':
                    return setup_result
            
            # 过滤数据（如果配置了过滤条件）
            filtered_data = self._filter_recognition_data(data)
            
            # 格式化推送数据
            push_data = self._format_push_data(filtered_data)
            
            # 执行推送
            camera_id = data.get('camera_id', 'unknown')
            positions = push_data.get('positions', {})
            
            push_result = self.push_client.push_recognition_result(camera_id, positions)
            
            if push_result['status'] == 'success':
                log_success(f"识别结果推送成功: {camera_id}", "RECOGNITION")
            else:
                log_error(f"识别结果推送失败: {push_result['message']}", "RECOGNITION")
            
            return push_result
            
        except Exception as e:
            log_error(f"推送识别结果失败: {e}", "RECOGNITION")
            return format_error_response(f"推送失败: {str(e)}", "PUSH_ERROR")
    
    def _auto_push_recognition_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """自动推送识别结果"""
        try:
            if not self.push_config.get("auto_push_on_receive", True):
                return format_success_response("自动推送已禁用", data={'auto_push': False})
            
            return self.push_recognition_result(data)
            
        except Exception as e:
            log_error(f"自动推送失败: {e}", "RECOGNITION")
            return format_error_response(f"自动推送失败: {str(e)}", "AUTO_PUSH_ERROR")
    
    def _filter_recognition_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """根据配置过滤识别数据"""
        try:
            filter_config = self.push_config.get("push_filter", {})
            min_confidence = filter_config.get("min_confidence", 0.0)
            allowed_positions = filter_config.get("positions", self.standard_positions)
            
            filtered_data = data.copy()
            positions = filtered_data.get('positions', {})
            filtered_positions = {}
            
            for position, pos_data in positions.items():
                # 检查位置是否在允许列表中
                if position not in allowed_positions:
                    continue
                
                # 检查置信度
                confidence = pos_data.get('confidence', 0.0)
                if confidence >= min_confidence:
                    filtered_positions[position] = pos_data
                else:
                    # 置信度不足时发送空数据
                    filtered_positions[position] = {
                        'suit': '',
                        'rank': '',
                        'confidence': confidence
                    }
            
            filtered_data['positions'] = filtered_positions
            return filtered_data
            
        except Exception as e:
            log_warning(f"过滤识别数据失败: {e}", "RECOGNITION")
            return data
    
    def _format_push_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化推送数据"""
        try:
            positions = data.get('positions', {})
            formatted_positions = {}
            
            for position, pos_data in positions.items():
                formatted_positions[position] = {
                    'suit': pos_data.get('suit', ''),
                    'rank': pos_data.get('rank', '')
                }
            
            return {
                'positions': formatted_positions,
                'timestamp': data.get('received_at', get_timestamp()),
                'camera_id': data.get('camera_id', 'unknown')
            }
            
        except Exception as e:
            log_error(f"格式化推送数据失败: {e}", "RECOGNITION")
            return {'positions': {}, 'timestamp': get_timestamp()}
    
    def manual_push_recognition_result(self, push_type: str = "websocket", camera_id: str = None) -> Dict[str, Any]:
        """手动推送识别结果"""
        try:
            # 获取最新识别结果
            latest_result = self.get_latest_recognition()
            if latest_result['status'] != 'success':
                return format_error_response("没有可推送的识别结果", "NO_DATA_TO_PUSH")
            
            data = latest_result['data']
            
            # 如果指定了camera_id，添加到数据中
            if camera_id:
                data['camera_id'] = camera_id
            
            # 执行推送
            push_result = self.push_recognition_result(data)
            
            if push_result['status'] == 'success':
                log_success("手动推送识别结果成功", "RECOGNITION")
            
            return push_result
            
        except Exception as e:
            log_error(f"手动推送识别结果失败: {e}", "RECOGNITION")
            return format_error_response(f"手动推送失败: {str(e)}", "MANUAL_PUSH_ERROR")
    
    # ==================== 配置管理 ====================
    
    def update_push_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """更新推送配置"""
        try:
            if not isinstance(new_config, dict):
                return format_error_response("配置数据格式无效", "INVALID_CONFIG_FORMAT")
            
            # 更新配置
            old_config = self.push_config.copy()
            
            # 合并配置
            if "websocket" in new_config:
                self.push_config["websocket"].update(new_config["websocket"])
            
            if "auto_push_on_receive" in new_config:
                self.push_config["auto_push_on_receive"] = bool(new_config["auto_push_on_receive"])
            
            if "push_filter" in new_config:
                self.push_config["push_filter"].update(new_config["push_filter"])
            
            # 保存配置
            if self._save_push_config():
                log_success("推送配置更新成功", "RECOGNITION")
                
                # 如果WebSocket配置发生变化，重新设置客户端
                if ("websocket" in new_config and 
                    old_config.get("websocket") != self.push_config.get("websocket")):
                    
                    if self.push_client_active:
                        # 重新设置推送客户端
                        setup_result = self.setup_push_client()
                        log_info(f"推送客户端重新设置结果: {setup_result['status']}", "RECOGNITION")
                
                return format_success_response(
                    "推送配置更新成功",
                    data={"updated_config": self.push_config}
                )
            else:
                return format_error_response("保存推送配置失败", "SAVE_CONFIG_ERROR")
                
        except Exception as e:
            log_error(f"更新推送配置失败: {e}", "RECOGNITION")
            return format_error_response(f"更新配置失败: {str(e)}", "UPDATE_CONFIG_ERROR")
    
    def get_push_config(self) -> Dict[str, Any]:
        """获取推送配置"""
        try:
            return format_success_response(
                "获取推送配置成功",
                data=self.push_config
            )
        except Exception as e:
            log_error(f"获取推送配置失败: {e}", "RECOGNITION")
            return format_error_response(f"获取配置失败: {str(e)}", "GET_CONFIG_ERROR")
    
    def get_push_status(self) -> Dict[str, Any]:
        """获取推送状态"""
        try:
            client_status = None
            if self.push_client:
                client_status_result = self.push_client.get_client_status()
                if client_status_result['status'] == 'success':
                    client_status = client_status_result['data']
            
            status_data = {
                'push_client_active': self.push_client_active,
                'auto_push_enabled': self.push_config.get("auto_push_on_receive", True),
                'websocket_enabled': self.push_config.get("websocket", {}).get("enabled", True),
                'client_status': client_status,
                'config_loaded': bool(self.push_config),
                'last_config_update': self.push_config.get("updated_at", "")
            }
            
            return format_success_response("获取推送状态成功", data=status_data)
            
        except Exception as e:
            log_error(f"获取推送状态失败: {e}", "RECOGNITION")
            return format_error_response(f"获取状态失败: {str(e)}", "GET_STATUS_ERROR")
    
    # ==================== 维护功能 ====================
    
    def cleanup_old_history(self, keep_count: int = 50) -> Dict[str, Any]:
        """清理旧的历史记录文件"""
        try:
            history_files = list(self.history_dir.glob("recognition_*.json"))
            if len(history_files) <= keep_count:
                return format_success_response(f"历史文件数量正常: {len(history_files)}", data={'deleted_count': 0})
            
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
            
            return format_success_response(
                f"历史记录清理完成",
                data={'deleted_count': deleted_count, 'remaining_count': keep_count}
            )
            
        except Exception as e:
            log_error(f"清理历史文件失败: {e}", "RECOGNITION")
            return format_error_response(f"清理失败: {str(e)}", "CLEANUP_ERROR")
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            # 历史文件统计
            history_files = list(self.history_dir.glob("recognition_*.json"))
            history_count = len(history_files)
            
            # 最新结果统计
            latest_stats = {'recognized_count': 0, 'total_positions': len(self.standard_positions)}
            if self.latest_file.exists():
                latest_data = safe_json_load(self.latest_file)
                if latest_data:
                    latest_stats = self._calculate_recognition_stats(latest_data)
            
            # 推送统计
            push_stats = {
                'client_active': self.push_client_active,
                'auto_push_enabled': self.push_config.get("auto_push_on_receive", True),
                'websocket_enabled': self.push_config.get("websocket", {}).get("enabled", True)
            }
            
            if self.push_client:
                client_status = self.push_client.get_client_status()
                if client_status['status'] == 'success':
                    push_stats.update(client_status['data'].get('stats', {}))
            
            system_stats = {
                'recognition_stats': latest_stats,
                'history_files_count': history_count,
                'push_stats': push_stats,
                'system_status': {
                    'result_dir_exists': self.result_dir.exists(),
                    'history_dir_exists': self.history_dir.exists(),
                    'latest_file_exists': self.latest_file.exists(),
                    'config_file_exists': self.push_config_file.exists()
                },
                'timestamp': get_timestamp()
            }
            
            return format_success_response("获取系统统计成功", data=system_stats)
            
        except Exception as e:
            log_error(f"获取系统统计失败: {e}", "RECOGNITION")
            return format_error_response(f"获取统计失败: {str(e)}", "STATS_ERROR")

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

def manual_push_recognition_result(push_type: str = "websocket", camera_id: str = None) -> Dict[str, Any]:
    """手动推送识别结果"""
    return recognition_manager.manual_push_recognition_result(push_type, camera_id)

def update_push_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """更新推送配置"""
    return recognition_manager.update_push_config(config)

def get_push_config() -> Dict[str, Any]:
    """获取推送配置"""
    return recognition_manager.get_push_config()

def get_push_status() -> Dict[str, Any]:
    """获取推送状态"""
    return recognition_manager.get_push_status()

def cleanup_old_history(keep_count: int = 50) -> Dict[str, Any]:
    """清理旧的历史记录"""
    return recognition_manager.cleanup_old_history(keep_count)

def get_system_statistics() -> Dict[str, Any]:
    """获取系统统计信息"""
    return recognition_manager.get_system_statistics()

if __name__ == "__main__":
    # 测试识别结果管理器
    print("🧪 测试识别结果管理器（完整版）")
    
    # 测试数据
    test_data = {
        "total_cameras": 2,
        "camera_id": "001",
        "positions": {
            "zhuang_1": {"suit": "hearts", "rank": "A", "confidence": 0.95},
            "zhuang_2": {"suit": "spades", "rank": "K", "confidence": 0.88},
            "zhuang_3": {"suit": "", "rank": "", "confidence": 0.0},
            "xian_1": {"suit": "diamonds", "rank": "Q", "confidence": 0.92},
            "xian_2": {"suit": "", "rank": "", "confidence": 0.0},
            "xian_3": {"suit": "clubs", "rank": "10", "confidence": 0.85}
        }
    }
    
    print("\n📥 测试接收识别数据")
    result = receive_recognition_data(test_data)
    print(f"接收结果: {result['status']} - {result['message']}")
    
    print("\n📊 测试获取最新结果")
    latest = get_latest_recognition()
    print(f"最新结果: {latest['status']}")
    
    print("\n🎭 测试荷官端格式化")
    dealer_data = format_for_dealer()
    print(f"荷官端数据: {dealer_data['status']}")
    
    print("\n📚 测试获取历史记录")
    history = get_recognition_history(5)
    print(f"历史记录: {history['status']}")
    
    print("\n⚙️ 测试推送配置")
    config = get_push_config()
    print(f"推送配置: {config['status']}")
    
    print("\n📊 测试推送状态")
    status = get_push_status()
    print(f"推送状态: {status['status']}")
    
    print("\n🔧 测试手动推送")
    push_result = manual_push_recognition_result("websocket", "001")
    print(f"手动推送: {push_result['status']}")
    
    print("\n📈 测试系统统计")
    stats = get_system_statistics()
    print(f"系统统计: {stats['status']}")
    
    print("\n🧹 测试历史清理")
    cleanup_result = cleanup_old_history(10)
    print(f"清理结果: {cleanup_result['status']}")
    
    print("✅ 识别结果管理器测试完成")