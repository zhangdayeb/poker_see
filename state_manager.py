#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态管理器 - 管理系统运行状态，避免资源冲突
功能:
1. 摄像头使用状态管理
2. 进程间资源锁定
3. 运行状态监控
4. 资源冲突检测和解决
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
def setup_project_paths():
    """设置项目路径，确保可以正确导入模块"""
    current_file = Path(__file__).resolve()
    
    # 找到项目根目录（包含 state_manager.py 的目录）
    project_root = current_file.parent
    
    # 将项目根目录添加到 Python 路径
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

# 调用路径设置
PROJECT_ROOT = setup_project_paths()

import os
import time
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from src.core.utils import (
    get_result_dir, safe_json_load, safe_json_dump,
    format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)

class StateManager:
    """状态管理器"""
    
    def __init__(self):
        """初始化状态管理器"""
        # 状态文件目录
        self.state_dir = get_result_dir() / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # 状态文件
        self.camera_locks_file = self.state_dir / "camera_locks.json"
        self.process_status_file = self.state_dir / "process_status.json"
        self.system_status_file = self.state_dir / "system_status.json"
        
        # 进程信息
        self.process_id = os.getpid()
        self.process_name = "unknown"
        self.start_time = get_timestamp()
        
        # 锁超时时间（分钟）
        self.lock_timeout = 10
        
        # 线程锁
        self.lock = threading.Lock()
        
        log_info("状态管理器初始化完成", "STATE_MANAGER")
    
    def register_process(self, process_name: str, process_type: str) -> Dict[str, Any]:
        """
        注册进程
        
        Args:
            process_name: 进程名称 (biaoji, see, tui)
            process_type: 进程类型 (marking, testing, production)
            
        Returns:
            注册结果
        """
        try:
            with self.lock:
                self.process_name = process_name
                
                # 读取现有进程状态
                process_status = safe_json_load(self.process_status_file, {})
                
                # 更新当前进程信息
                process_info = {
                    'process_id': self.process_id,
                    'process_name': process_name,
                    'process_type': process_type,
                    'start_time': self.start_time,
                    'last_heartbeat': get_timestamp(),
                    'status': 'running'
                }
                
                process_status[str(self.process_id)] = process_info
                
                # 清理过期进程
                self._cleanup_expired_processes(process_status)
                
                # 保存进程状态
                if safe_json_dump(process_status, self.process_status_file):
                    log_success(f"进程注册成功: {process_name} (PID: {self.process_id})", "STATE_MANAGER")
                    return format_success_response(
                        "进程注册成功",
                        data=process_info
                    )
                else:
                    return format_error_response("保存进程状态失败", "SAVE_PROCESS_STATUS_ERROR")
                    
        except Exception as e:
            log_error(f"进程注册失败: {e}", "STATE_MANAGER")
            return format_error_response(f"进程注册失败: {str(e)}", "REGISTER_PROCESS_ERROR")
    
    def unregister_process(self) -> Dict[str, Any]:
        """
        注销进程
        
        Returns:
            注销结果
        """
        try:
            with self.lock:
                # 读取进程状态
                process_status = safe_json_load(self.process_status_file, {})
                
                # 移除当前进程
                process_key = str(self.process_id)
                if process_key in process_status:
                    del process_status[process_key]
                
                # 释放该进程持有的所有摄像头锁
                self._release_all_camera_locks_by_process()
                
                # 保存进程状态
                if safe_json_dump(process_status, self.process_status_file):
                    log_success(f"进程注销成功: {self.process_name} (PID: {self.process_id})", "STATE_MANAGER")
                    return format_success_response("进程注销成功")
                else:
                    return format_error_response("保存进程状态失败", "SAVE_PROCESS_STATUS_ERROR")
                    
        except Exception as e:
            log_error(f"进程注销失败: {e}", "STATE_MANAGER")
            return format_error_response(f"进程注销失败: {str(e)}", "UNREGISTER_PROCESS_ERROR")
    
    def update_heartbeat(self) -> Dict[str, Any]:
        """
        更新进程心跳
        
        Returns:
            更新结果
        """
        try:
            with self.lock:
                # 读取进程状态
                process_status = safe_json_load(self.process_status_file, {})
                
                # 更新心跳时间
                process_key = str(self.process_id)
                if process_key in process_status:
                    process_status[process_key]['last_heartbeat'] = get_timestamp()
                    
                    # 保存进程状态
                    if safe_json_dump(process_status, self.process_status_file):
                        return format_success_response("心跳更新成功")
                    else:
                        return format_error_response("保存心跳失败", "SAVE_HEARTBEAT_ERROR")
                else:
                    return format_error_response("进程未注册", "PROCESS_NOT_REGISTERED")
                    
        except Exception as e:
            log_error(f"更新心跳失败: {e}", "STATE_MANAGER")
            return format_error_response(f"更新心跳失败: {str(e)}", "UPDATE_HEARTBEAT_ERROR")
    
    def lock_camera(self, camera_id: str) -> Dict[str, Any]:
        """
        锁定摄像头
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            锁定结果
        """
        try:
            with self.lock:
                # 读取摄像头锁状态
                camera_locks = safe_json_load(self.camera_locks_file, {})
                
                # 清理过期锁
                self._cleanup_expired_locks(camera_locks)
                
                # 检查摄像头是否已被锁定
                if camera_id in camera_locks:
                    existing_lock = camera_locks[camera_id]
                    if self._is_lock_valid(existing_lock):
                        # 检查是否是同一进程
                        if existing_lock['process_id'] == self.process_id:
                            # 更新锁时间
                            existing_lock['locked_at'] = get_timestamp()
                            existing_lock['expires_at'] = self._get_expiry_time()
                        else:
                            return format_error_response(
                                f"摄像头 {camera_id} 已被进程 {existing_lock['process_name']} (PID: {existing_lock['process_id']}) 锁定",
                                "CAMERA_LOCKED"
                            )
                
                # 创建新锁
                lock_info = {
                    'camera_id': camera_id,
                    'process_id': self.process_id,
                    'process_name': self.process_name,
                    'locked_at': get_timestamp(),
                    'expires_at': self._get_expiry_time()
                }
                
                camera_locks[camera_id] = lock_info
                
                # 保存锁状态
                if safe_json_dump(camera_locks, self.camera_locks_file):
                    log_info(f"摄像头 {camera_id} 锁定成功", "STATE_MANAGER")
                    return format_success_response(
                        f"摄像头 {camera_id} 锁定成功",
                        data=lock_info
                    )
                else:
                    return format_error_response("保存锁状态失败", "SAVE_LOCK_ERROR")
                    
        except Exception as e:
            log_error(f"锁定摄像头 {camera_id} 失败: {e}", "STATE_MANAGER")
            return format_error_response(f"锁定摄像头失败: {str(e)}", "LOCK_CAMERA_ERROR")
    
    def release_camera(self, camera_id: str) -> Dict[str, Any]:
        """
        释放摄像头锁
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            释放结果
        """
        try:
            with self.lock:
                # 读取摄像头锁状态
                camera_locks = safe_json_load(self.camera_locks_file, {})
                
                # 检查锁是否存在
                if camera_id not in camera_locks:
                    return format_error_response(f"摄像头 {camera_id} 未被锁定", "CAMERA_NOT_LOCKED")
                
                existing_lock = camera_locks[camera_id]
                
                # 检查是否是同一进程
                if existing_lock['process_id'] != self.process_id:
                    return format_error_response(
                        f"摄像头 {camera_id} 被其他进程锁定，无法释放",
                        "CANNOT_RELEASE_LOCK"
                    )
                
                # 移除锁
                del camera_locks[camera_id]
                
                # 保存锁状态
                if safe_json_dump(camera_locks, self.camera_locks_file):
                    log_info(f"摄像头 {camera_id} 锁释放成功", "STATE_MANAGER")
                    return format_success_response(f"摄像头 {camera_id} 锁释放成功")
                else:
                    return format_error_response("保存锁状态失败", "SAVE_LOCK_ERROR")
                    
        except Exception as e:
            log_error(f"释放摄像头锁 {camera_id} 失败: {e}", "STATE_MANAGER")
            return format_error_response(f"释放摄像头锁失败: {str(e)}", "RELEASE_CAMERA_ERROR")
    
    def check_camera_available(self, camera_id: str) -> Dict[str, Any]:
        """
        检查摄像头是否可用
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            可用性检查结果
        """
        try:
            with self.lock:
                # 读取摄像头锁状态
                camera_locks = safe_json_load(self.camera_locks_file, {})
                
                # 清理过期锁
                self._cleanup_expired_locks(camera_locks)
                
                # 检查摄像头状态
                if camera_id in camera_locks:
                    existing_lock = camera_locks[camera_id]
                    if self._is_lock_valid(existing_lock):
                        # 摄像头被锁定
                        if existing_lock['process_id'] == self.process_id:
                            # 被当前进程锁定
                            return format_success_response(
                                f"摄像头 {camera_id} 被当前进程锁定",
                                data={
                                    'available': True,
                                    'locked_by_current_process': True,
                                    'lock_info': existing_lock
                                }
                            )
                        else:
                            # 被其他进程锁定
                            return format_success_response(
                                f"摄像头 {camera_id} 被其他进程锁定",
                                data={
                                    'available': False,
                                    'locked_by_other_process': True,
                                    'lock_info': existing_lock
                                }
                            )
                
                # 摄像头可用
                return format_success_response(
                    f"摄像头 {camera_id} 可用",
                    data={
                        'available': True,
                        'locked': False
                    }
                )
                
        except Exception as e:
            log_error(f"检查摄像头 {camera_id} 可用性失败: {e}", "STATE_MANAGER")
            return format_error_response(f"检查摄像头可用性失败: {str(e)}", "CHECK_CAMERA_ERROR")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            系统状态信息
        """
        try:
            with self.lock:
                # 获取进程状态
                process_status = safe_json_load(self.process_status_file, {})
                self._cleanup_expired_processes(process_status)
                
                # 获取摄像头锁状态
                camera_locks = safe_json_load(self.camera_locks_file, {})
                self._cleanup_expired_locks(camera_locks)
                
                # 统计信息
                total_processes = len(process_status)
                running_processes = [p for p in process_status.values() if p.get('status') == 'running']
                locked_cameras = list(camera_locks.keys())
                
                # 按进程类型分组
                process_by_type = {}
                for process in process_status.values():
                    process_type = process.get('process_type', 'unknown')
                    if process_type not in process_by_type:
                        process_by_type[process_type] = []
                    process_by_type[process_type].append(process)
                
                status_data = {
                    'timestamp': get_timestamp(),
                    'summary': {
                        'total_processes': total_processes,
                        'running_processes': len(running_processes),
                        'locked_cameras': len(locked_cameras),
                        'available_cameras': 0  # 需要从配置中获取总摄像头数
                    },
                    'processes': {
                        'all_processes': process_status,
                        'by_type': process_by_type
                    },
                    'camera_locks': camera_locks,
                    'current_process': {
                        'process_id': self.process_id,
                        'process_name': self.process_name,
                        'start_time': self.start_time
                    }
                }
                
                return format_success_response(
                    "获取系统状态成功",
                    data=status_data
                )
                
        except Exception as e:
            log_error(f"获取系统状态失败: {e}", "STATE_MANAGER")
            return format_error_response(f"获取系统状态失败: {str(e)}", "GET_SYSTEM_STATUS_ERROR")
    
    def _cleanup_expired_processes(self, process_status: Dict[str, Any]):
        """清理过期进程"""
        try:
            current_time = datetime.now()
            expired_processes = []
            
            for process_key, process_info in process_status.items():
                last_heartbeat_str = process_info.get('last_heartbeat', '')
                if last_heartbeat_str:
                    try:
                        last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
                        if current_time - last_heartbeat > timedelta(minutes=self.lock_timeout):
                            expired_processes.append(process_key)
                    except ValueError:
                        # 时间格式错误，也认为过期
                        expired_processes.append(process_key)
            
            # 移除过期进程
            for process_key in expired_processes:
                process_info = process_status[process_key]
                log_warning(f"清理过期进程: {process_info.get('process_name')} (PID: {process_key})", "STATE_MANAGER")
                del process_status[process_key]
                
        except Exception as e:
            log_error(f"清理过期进程失败: {e}", "STATE_MANAGER")
    
    def _cleanup_expired_locks(self, camera_locks: Dict[str, Any]):
        """清理过期锁"""
        try:
            current_time = datetime.now()
            expired_locks = []
            
            for camera_id, lock_info in camera_locks.items():
                if not self._is_lock_valid(lock_info):
                    expired_locks.append(camera_id)
            
            # 移除过期锁
            for camera_id in expired_locks:
                lock_info = camera_locks[camera_id]
                log_warning(f"清理过期摄像头锁: {camera_id} (进程: {lock_info.get('process_name')})", "STATE_MANAGER")
                del camera_locks[camera_id]
                
        except Exception as e:
            log_error(f"清理过期锁失败: {e}", "STATE_MANAGER")
    
    def _is_lock_valid(self, lock_info: Dict[str, Any]) -> bool:
        """检查锁是否有效"""
        try:
            expires_at_str = lock_info.get('expires_at', '')
            if not expires_at_str:
                return False
            
            expires_at = datetime.fromisoformat(expires_at_str)
            return datetime.now() < expires_at
            
        except ValueError:
            return False
    
    def _get_expiry_time(self) -> str:
        """获取锁过期时间"""
        expiry_time = datetime.now() + timedelta(minutes=self.lock_timeout)
        return expiry_time.isoformat()
    
    def _release_all_camera_locks_by_process(self):
        """释放当前进程持有的所有摄像头锁"""
        try:
            camera_locks = safe_json_load(self.camera_locks_file, {})
            
            # 找到当前进程的所有锁
            cameras_to_release = []
            for camera_id, lock_info in camera_locks.items():
                if lock_info.get('process_id') == self.process_id:
                    cameras_to_release.append(camera_id)
            
            # 释放锁
            for camera_id in cameras_to_release:
                del camera_locks[camera_id]
                log_info(f"自动释放摄像头锁: {camera_id}", "STATE_MANAGER")
            
            # 保存更新后的锁状态
            if cameras_to_release:
                safe_json_dump(camera_locks, self.camera_locks_file)
                
        except Exception as e:
            log_error(f"释放进程锁失败: {e}", "STATE_MANAGER")

# 创建全局实例
state_manager = StateManager()

# 导出主要函数
def register_process(process_name: str, process_type: str) -> Dict[str, Any]:
    """注册进程"""
    return state_manager.register_process(process_name, process_type)

def unregister_process() -> Dict[str, Any]:
    """注销进程"""
    return state_manager.unregister_process()

def update_heartbeat() -> Dict[str, Any]:
    """更新进程心跳"""
    return state_manager.update_heartbeat()

def lock_camera(camera_id: str) -> Dict[str, Any]:
    """锁定摄像头"""
    return state_manager.lock_camera(camera_id)

def release_camera(camera_id: str) -> Dict[str, Any]:
    """释放摄像头锁"""
    return state_manager.release_camera(camera_id)

def check_camera_available(camera_id: str) -> Dict[str, Any]:
    """检查摄像头是否可用"""
    return state_manager.check_camera_available(camera_id)

def get_system_status() -> Dict[str, Any]:
    """获取系统状态"""
    return state_manager.get_system_status()

if __name__ == "__main__":
    # 测试状态管理器
    print("🧪 测试状态管理器")
    
    # 注册进程
    register_result = register_process("test_process", "testing")
    print(f"注册进程: {register_result['status']}")
    
    # 锁定摄像头
    lock_result = lock_camera("001")
    print(f"锁定摄像头001: {lock_result['status']}")
    
    # 检查摄像头可用性
    check_result = check_camera_available("001")
    print(f"检查摄像头001可用性: {check_result['status']}")
    if check_result['status'] == 'success':
        print(f"   可用: {check_result['data']['available']}")
    
    # 检查其他摄像头
    check_result2 = check_camera_available("002")
    print(f"检查摄像头002可用性: {check_result2['status']}")
    if check_result2['status'] == 'success':
        print(f"   可用: {check_result2['data']['available']}")
    
    # 获取系统状态
    status = get_system_status()
    print(f"获取系统状态: {status['status']}")
    if status['status'] == 'success':
        print(f"   运行进程数: {status['data']['summary']['running_processes']}")
        print(f"   锁定摄像头数: {status['data']['summary']['locked_cameras']}")
    
    # 释放摄像头
    release_result = release_camera("001")
    print(f"释放摄像头001: {release_result['status']}")
    
    # 注销进程
    unregister_result = unregister_process()
    print(f"注销进程: {unregister_result['status']}")
    
    print("✅ 状态管理器测试完成")