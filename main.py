#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克识别系统 - 简化版主程序入口
解决模块导入问题的版本
"""

import sys
import time
import signal
import argparse
import os
from pathlib import Path

# 路径设置
def setup_project_paths():
    """设置项目路径"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent
    
    # 将项目根目录添加到Python路径
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    # 确保src目录也在路径中
    src_dir = project_root / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    return project_root

# 设置项目路径
PROJECT_ROOT = setup_project_paths()

# 安全导入模块
def safe_import_modules():
    """安全导入所有需要的模块"""
    modules = {}
    
    # 导入工具模块
    try:
        from src.core.utils import (
            get_timestamp, ensure_dirs_exist, get_config_dir, get_image_dir, get_result_dir,
            log_info, log_success, log_error, log_warning
        )
        modules['utils'] = {
            'get_timestamp': get_timestamp,
            'ensure_dirs_exist': ensure_dirs_exist,
            'get_config_dir': get_config_dir,
            'get_image_dir': get_image_dir,
            'get_result_dir': get_result_dir,
            'log_info': log_info,
            'log_success': log_success,
            'log_error': log_error,
            'log_warning': log_warning
        }
        print("✅ 工具模块加载成功")
    except ImportError as e:
        print(f"❌ 工具模块导入失败: {e}")
        return None
    
    # 导入HTTP服务器模块
    try:
        from src.servers.http_server import start_http_server, stop_http_server, get_server_info
        modules['http_server'] = {
            'start_http_server': start_http_server,
            'stop_http_server': stop_http_server,
            'get_server_info': get_server_info
        }
        print("✅ HTTP服务器模块加载成功")
    except ImportError as e:
        print(f"❌ HTTP服务器模块导入失败: {e}")
        modules['http_server'] = None
    
    # 导入配置管理模块
    try:
        from src.core.config_manager import get_config_status, get_all_cameras
        modules['config_manager'] = {
            'get_config_status': get_config_status,
            'get_all_cameras': get_all_cameras
        }
        print("✅ 配置管理模块加载成功")
    except ImportError as e:
        print(f"❌ 配置管理模块导入失败: {e}")
        modules['config_manager'] = None
    
    # 导入识别管理模块 - 分步导入以便调试
    try:
        # 先尝试导入模块
        import src.core.recognition_manager as rec_mgr
        
        # 然后尝试获取具体函数
        functions_to_import = [
            'get_latest_recognition',
            'get_push_config', 
            'get_push_status',
            'get_system_statistics',
            'receive_recognition_data'
        ]
        
        recognition_funcs = {}
        for func_name in functions_to_import:
            if hasattr(rec_mgr, func_name):
                recognition_funcs[func_name] = getattr(rec_mgr, func_name)
                print(f"  ✅ {func_name} 导入成功")
            else:
                print(f"  ❌ {func_name} 不存在")
                recognition_funcs[func_name] = None
        
        modules['recognition_manager'] = recognition_funcs
        print("✅ 识别管理模块加载成功")
        
    except ImportError as e:
        print(f"❌ 识别管理模块导入失败: {e}")
        modules['recognition_manager'] = None
    
    # 导入WebSocket客户端模块
    try:
        from src.clients.websocket_client import (
            start_push_client, stop_push_client, get_push_client_status
        )
        modules['websocket_client'] = {
            'start_push_client': start_push_client,
            'stop_push_client': stop_push_client,
            'get_push_client_status': get_push_client_status,
            'available': True
        }
        print("✅ WebSocket客户端模块加载成功")
    except ImportError as e:
        print(f"⚠️  WebSocket客户端模块导入失败: {e}")
        modules['websocket_client'] = {
            'start_push_client': None,
            'stop_push_client': None,
            'get_push_client_status': None,
            'available': False
        }
    
    return modules

class SimplePokerRecognitionSystem:
    """简化版扑克识别系统"""
    
    def __init__(self):
        """初始化系统"""
        self.modules = safe_import_modules()
        
        if not self.modules:
            raise ImportError("核心模块导入失败")
        
        self.shutdown_requested = False
        self.services_running = {
            'http_server': False,
            'websocket_client': False
        }
        
        # 系统配置
        self.config = {
            'http_host': 'localhost',
            'http_port': 8000,
            'websocket_server': 'ws://bjl_heguan_wss.yhyule666.com:8001',
            'websocket_client_id': 'python_client_001',
            'auto_start_websocket': True
        }
    
    def initialize_system(self) -> bool:
        """初始化系统"""
        try:
            print("🎮 扑克识别系统启动中...")
            print("=" * 60)
            
            # 检查必要目录
            if self.modules['utils']:
                dirs = [
                    self.modules['utils']['get_config_dir'](),
                    self.modules['utils']['get_image_dir'](),
                    self.modules['utils']['get_result_dir']()
                ]
                self.modules['utils']['ensure_dirs_exist'](*dirs)
                print("✅ 系统目录检查完成")
            
            # 检查摄像头配置
            if self.modules['config_manager']:
                self._check_camera_config()
            
            return True
            
        except Exception as e:
            print(f"❌ 系统初始化失败: {e}")
            return False
    
    def _check_camera_config(self):
        """检查摄像头配置"""
        try:
            config_status = self.modules['config_manager']['get_config_status']()
            cameras_result = self.modules['config_manager']['get_all_cameras']()
            
            if config_status['status'] == 'success' and cameras_result['status'] == 'success':
                config_data = config_status['data']
                cameras_data = cameras_result['data']
                
                print(f"📷 摄像头配置: {cameras_data['total_cameras']} 个摄像头")
                print(f"📍 标记完成率: {config_data['completion_rate']}%")
            else:
                print("⚠️  摄像头配置检查失败")
                
        except Exception as e:
            print(f"❌ 检查摄像头配置失败: {e}")
    
    def start_services(self) -> bool:
        """启动服务"""
        success_count = 0
        
        # 启动HTTP服务器
        if self.modules['http_server']:
            try:
                print("🌐 启动HTTP服务器...")
                result = self.modules['http_server']['start_http_server'](
                    self.config['http_host'], 
                    self.config['http_port']
                )
                
                if result:
                    self.services_running['http_server'] = True
                    success_count += 1
                    print(f"✅ HTTP服务器启动成功: http://{self.config['http_host']}:{self.config['http_port']}")
                else:
                    print("❌ HTTP服务器启动失败")
                    
            except Exception as e:
                print(f"❌ HTTP服务器启动异常: {e}")
        
        # 启动WebSocket客户端
        if (self.config['auto_start_websocket'] and 
            self.modules['websocket_client']['available'] and
            self.modules['websocket_client']['start_push_client']):
            
            try:
                print("📡 启动WebSocket推送客户端...")
                result = self.modules['websocket_client']['start_push_client'](
                    self.config['websocket_server'],
                    self.config['websocket_client_id']
                )
                
                if result['status'] == 'success':
                    self.services_running['websocket_client'] = True
                    success_count += 1
                    print(f"✅ WebSocket客户端启动成功: {self.config['websocket_server']}")
                else:
                    print(f"❌ WebSocket客户端启动失败: {result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ WebSocket客户端启动异常: {e}")
        else:
            print("⚠️  WebSocket客户端未启动 (模块不可用或已禁用)")
        
        return success_count > 0
    
    def display_running_info(self):
        """显示运行信息"""
        print("\n🚀 服务运行信息")
        print("=" * 60)
        
        if self.services_running['http_server']:
            print(f"🌐 HTTP服务器: http://{self.config['http_host']}:{self.config['http_port']}")
            print(f"   📋 主页: /")
            print(f"   🎯 标记工具: /biaoji.html")
            print(f"   📚 API文档: /api-docs")
        
        if self.services_running['websocket_client']:
            print(f"📡 WebSocket推送: {self.config['websocket_server']}")
            print(f"   🆔 客户端ID: {self.config['websocket_client_id']}")
        
        print(f"\n💡 主要功能:")
        print("1. 📷 RTSP摄像头拍照")
        print("2. 🎯 扑克位置标记")
        print("3. 🧠 识别结果处理")
        print("4. 📡 实时推送")
        print("5. 按 Ctrl+C 停止服务")
        print("=" * 60)
    
    def run_main_loop(self):
        """运行主循环"""
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            print("✨ 系统运行中，等待服务请求...")
            
            while not self.shutdown_requested:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.shutdown_requested = True
        except Exception as e:
            print(f"❌ 主循环异常: {e}")
            self.shutdown_requested = True
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n📡 接收到信号 {signum}，准备关闭系统...")
        self.shutdown_requested = True
    
    def shutdown_system(self):
        """关闭系统"""
        try:
            print("\n🔄 正在关闭系统...")
            
            # 关闭WebSocket客户端
            if (self.services_running['websocket_client'] and 
                self.modules['websocket_client']['stop_push_client']):
                
                print("📡 关闭WebSocket客户端...")
                result = self.modules['websocket_client']['stop_push_client']()
                if result['status'] == 'success':
                    print("✅ WebSocket客户端已关闭")
                else:
                    print("⚠️  WebSocket客户端关闭异常")
            
            # 关闭HTTP服务器
            if (self.services_running['http_server'] and 
                self.modules['http_server']):
                
                print("🌐 关闭HTTP服务器...")
                result = self.modules['http_server']['stop_http_server']()
                if result:
                    print("✅ HTTP服务器已关闭")
                else:
                    print("⚠️  HTTP服务器关闭异常")
            
            print("👋 扑克识别系统已安全关闭")
            
        except Exception as e:
            print(f"❌ 关闭系统时出错: {e}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='扑克识别系统')
    
    parser.add_argument('--host', default='localhost', help='HTTP服务器地址')
    parser.add_argument('--http-port', type=int, default=8000, help='HTTP端口')
    parser.add_argument('--websocket-server', 
                       default='ws://bjl_heguan_wss.yhyule666.com:8001',
                       help='WebSocket服务器地址')
    parser.add_argument('--no-websocket', action='store_true', help='禁用WebSocket')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析参数
        args = parse_arguments()
        
        # 创建系统实例
        system = SimplePokerRecognitionSystem()
        
        # 更新配置
        system.config.update({
            'http_host': args.host,
            'http_port': args.http_port,
            'websocket_server': args.websocket_server,
            'auto_start_websocket': not args.no_websocket
        })
        
        # 初始化系统
        if not system.initialize_system():
            return 1
        
        # 启动服务
        if not system.start_services():
            print("❌ 服务启动失败")
            return 1
        
        # 显示运行信息
        system.display_running_info()
        
        # 运行主循环
        system.run_main_loop()
        
        # 关闭系统
        system.shutdown_system()
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())