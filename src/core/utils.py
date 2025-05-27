#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具模块 - 提供通用的辅助函数
功能:
1. 时间戳处理
2. 文件和目录操作
3. JSON安全操作
4. 响应格式化
5. 编码处理
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
import os

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union
import logging

class Utils:
    """工具类 - 包含所有通用工具函数"""
    
    @staticmethod
    def get_timestamp() -> str:
        """获取当前时间戳 ISO格式"""
        return datetime.now().isoformat()
    
    @staticmethod
    def get_formatted_time() -> str:
        """获取格式化的时间字符串"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def ensure_dirs_exist(*dir_paths: Union[str, Path]) -> None:
        """确保目录存在，如果不存在则创建"""
        for dir_path in dir_paths:
            path = Path(dir_path)
            path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def safe_json_load(file_path: Union[str, Path], default: Any = None) -> Any:
        """安全加载JSON文件"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return default
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            print(f"❌ JSON加载失败 {file_path}: {e}")
            return default
    
    @staticmethod
    def safe_json_dump(data: Any, file_path: Union[str, Path], indent: int = 2) -> bool:
        """安全保存JSON文件"""
        try:
            file_path = Path(file_path)
            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            return True
        except Exception as e:
            print(f"❌ JSON保存失败 {file_path}: {e}")
            return False
    
    @staticmethod
    def parse_json_string(json_str: str, default: Any = None) -> Any:
        """安全解析JSON字符串"""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON字符串解析失败: {e}")
            return default
    
    @staticmethod
    def format_success_response(message: str = "操作成功", data: Any = None, **kwargs) -> Dict[str, Any]:
        """格式化成功响应"""
        response = {
            'status': 'success',
            'message': message,
            'timestamp': Utils.get_timestamp()
        }
        
        if data is not None:
            response['data'] = data
        
        # 添加额外的键值对
        response.update(kwargs)
        return response
    
    @staticmethod
    def format_error_response(message: str = "操作失败", error_code: str = None, **kwargs) -> Dict[str, Any]:
        """格式化错误响应"""
        response = {
            'status': 'error',
            'message': message,
            'timestamp': Utils.get_timestamp()
        }
        
        if error_code:
            response['error_code'] = error_code
        
        # 添加额外的键值对
        response.update(kwargs)
        return response
    
    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """获取文件大小（字节）"""
        try:
            return Path(file_path).stat().st_size
        except (FileNotFoundError, OSError):
            return 0
    
    @staticmethod
    def file_exists(file_path: Union[str, Path]) -> bool:
        """检查文件是否存在"""
        return Path(file_path).exists()
    
    @staticmethod
    def get_project_root() -> Path:
        """获取项目根目录"""
        # 假设这个文件在 pycontroller 目录下
        current_file = Path(__file__).absolute()
        pycontroller_dir = current_file.parent
        project_root = pycontroller_dir.parent
        return project_root
    
    @staticmethod
    def get_config_dir() -> Path:
        """获取配置目录"""
        return Utils.get_project_root() / "config"
    
    @staticmethod
    def get_image_dir() -> Path:
        """获取图片目录"""
        return Utils.get_project_root() / "src" / "image"
    
    @staticmethod
    def get_result_dir() -> Path:
        """获取结果目录"""
        return Utils.get_project_root() / "result"
    
    @staticmethod
    def validate_camera_id(camera_id: str) -> bool:
        """验证摄像头ID格式"""
        if not camera_id:
            return False
        # 简单验证：非空字符串，长度在1-20之间
        return len(camera_id.strip()) > 0 and len(camera_id) <= 20
    
    @staticmethod
    def validate_mark_position(position_data: Dict[str, Any]) -> bool:
        """验证标记位置数据格式"""
        if not isinstance(position_data, dict):
            return False
        
        # 检查必需的字段
        required_fields = ['x', 'y']
        for field in required_fields:
            if field not in position_data:
                return False
            
            # 检查坐标值是否为数字
            try:
                float(position_data[field])
            except (ValueError, TypeError):
                return False
        
        return True
    
    @staticmethod
    def log_info(message: str, module: str = "SYSTEM") -> None:
        """记录信息日志"""
        timestamp = Utils.get_formatted_time()
        print(f"[{timestamp}] [{module}] ℹ️  {message}")
    
    @staticmethod
    def log_success(message: str, module: str = "SYSTEM") -> None:
        """记录成功日志"""
        timestamp = Utils.get_formatted_time()
        print(f"[{timestamp}] [{module}] ✅ {message}")
    
    @staticmethod
    def log_error(message: str, module: str = "SYSTEM") -> None:
        """记录错误日志"""
        timestamp = Utils.get_formatted_time()
        print(f"[{timestamp}] [{module}] ❌ {message}")
    
    @staticmethod
    def log_warning(message: str, module: str = "SYSTEM") -> None:
        """记录警告日志"""
        timestamp = Utils.get_formatted_time()
        print(f"[{timestamp}] [{module}] ⚠️  {message}")
    
    @staticmethod
    def safe_encode(text: str, encoding: str = 'utf-8') -> bytes:
        """安全编码文本"""
        try:
            return text.encode(encoding)
        except UnicodeEncodeError as e:
            Utils.log_error(f"编码失败: {e}")
            return text.encode(encoding, errors='replace')
    
    @staticmethod
    def safe_decode(data: bytes, encoding: str = 'utf-8') -> str:
        """安全解码数据"""
        try:
            return data.decode(encoding)
        except UnicodeDecodeError as e:
            Utils.log_error(f"解码失败: {e}")
            return data.decode(encoding, errors='replace')
    
    @staticmethod
    def get_content_type(file_path: Union[str, Path]) -> str:
        """根据文件扩展名获取Content-Type"""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        content_types = {
            '.html': 'text/html; charset=utf-8',
            '.htm': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.txt': 'text/plain; charset=utf-8',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.pdf': 'application/pdf',
            '.zip': 'application/zip'
        }
        
        return content_types.get(extension, 'application/octet-stream')
    
    @staticmethod
    def cleanup_old_files(directory: Union[str, Path], max_files: int = 100, pattern: str = "*") -> int:
        """清理旧文件，保留最新的指定数量"""
        try:
            directory = Path(directory)
            if not directory.exists():
                return 0
            
            # 获取所有匹配的文件，按修改时间排序
            files = list(directory.glob(pattern))
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # 删除超出数量的文件
            deleted_count = 0
            for file_to_delete in files[max_files:]:
                try:
                    file_to_delete.unlink()
                    deleted_count += 1
                except OSError as e:
                    Utils.log_error(f"删除文件失败 {file_to_delete}: {e}")
            
            if deleted_count > 0:
                Utils.log_info(f"清理了 {deleted_count} 个旧文件")
            
            return deleted_count
            
        except Exception as e:
            Utils.log_error(f"清理文件失败: {e}")
            return 0

# 创建工具函数的快捷访问方式
get_timestamp = Utils.get_timestamp
get_formatted_time = Utils.get_formatted_time
ensure_dirs_exist = Utils.ensure_dirs_exist
safe_json_load = Utils.safe_json_load
safe_json_dump = Utils.safe_json_dump
parse_json_string = Utils.parse_json_string
format_success_response = Utils.format_success_response
format_error_response = Utils.format_error_response
get_file_size = Utils.get_file_size
file_exists = Utils.file_exists
get_project_root = Utils.get_project_root
get_config_dir = Utils.get_config_dir
get_image_dir = Utils.get_image_dir
get_result_dir = Utils.get_result_dir
validate_camera_id = Utils.validate_camera_id
validate_mark_position = Utils.validate_mark_position
log_info = Utils.log_info
log_success = Utils.log_success
log_error = Utils.log_error
log_warning = Utils.log_warning
safe_encode = Utils.safe_encode
safe_decode = Utils.safe_decode
get_content_type = Utils.get_content_type
cleanup_old_files = Utils.cleanup_old_files

if __name__ == "__main__":
    # 测试工具函数
    print("🧪 测试工具模块")
    
    # 测试时间戳
    print(f"当前时间戳: {get_timestamp()}")
    print(f"格式化时间: {get_formatted_time()}")
    
    # 测试路径
    print(f"项目根目录: {get_project_root()}")
    print(f"配置目录: {get_config_dir()}")
    print(f"图片目录: {get_image_dir()}")
    
    # 测试响应格式化
    success_resp = format_success_response("测试成功", {"test": "data"})
    print(f"成功响应: {success_resp}")
    
    error_resp = format_error_response("测试错误", "TEST_ERROR")
    print(f"错误响应: {error_resp}")
    
    # 测试日志
    log_info("这是一条信息日志", "TEST")
    log_success("这是一条成功日志", "TEST")
    log_warning("这是一条警告日志", "TEST")
    log_error("这是一条错误日志", "TEST")
    
    print("✅ 工具模块测试完成")