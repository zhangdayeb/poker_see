#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扑克识别系统 - 主程序入口
功能:
1. 启动HTTP服务器和WebSocket服务器
2. 系统初始化和配置检查
3. 服务间协调和数据共享
4. 优雅关闭和资源清理
5. 命令行参数处理
"""

import sys
import time
import signal
import argparse
from pathlib import Path
from typing import Dict, Any

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from utils import (
    get_timestamp, ensure_dirs_exist, get_config_dir, get_image_dir, get_result_dir,
    log_info, log_success, log_error, log_warning
)
from http_server import start_http_server, stop_http_server, get_server_info
from websocket_server import start_websocket_server, stop_websocket_server, get_websocket_server_info
from connection_manager import cleanup_all_connections, get_connection_stats
from config_manager import get_config_status

class PokerRecognitionSystem:
    """扑克识别系统主类"""
    
    def __init__(self):
        """初始化系统"""
        self.http_server_running = False
        self.websocket_server_running = False
        self.shutdown_requested = False
        
        # 默认配置
        self.config = {
            'http_host': 'localhost',
            'http_port': 8000,
            'websocket_host': 'localhost',
            'websocket_port': 8001,
            'auto_start_websocket': True,
            'log_level': 'INFO'
        }
        
        log_info("扑克识别系统初始化", "MAIN")
    
    def initialize_system(self) -> bool:
        """初始化系统"""
        try:
            print("🎮 扑克识别系统启动中...")
            print("=" * 60)
            
            # 检查和创建必要目录
            log_info("检查系统目录...", "MAIN")
            required_dirs = [get_config_dir(), get_image_dir(), get_result_dir()]
            ensure_dirs_exist(*required_dirs)
            
            # 检查配置文件状态
            config_status = get_config_status()
            if config_status['status'] == 'success':
                data = config_status['data']
                log_success(f"配置检查完成: {data['total_cameras']} 个摄像头", "MAIN")
            else:
                log_warning("配置文件检查失败，将使用默认配置", "MAIN")
            
            # 显示系统信息
            self._display_system_info()
            
            return True
            
        except Exception as e:
            log_error(f"系统初始化失败: {e}", "MAIN")
            return False
    
    def start_services(self, http_only: bool = False) -> bool:
        """启动服务"""
        try:
            # 启动HTTP服务器
            log_info("启动HTTP服务器...", "MAIN")
            http_result = start_http_server(self.config['http_host'], self.config['http_port'])
            
            if http_result:
                self.http_server_running = True
                log_success(f"HTTP服务器启动成功: http://{self.config['http_host']}:{self.config['http_port']}", "MAIN")
            else:
                log_error("HTTP服务器启动失败", "MAIN")
                return False
            
            # 启动WebSocket服务器（如果需要）
            if not http_only and self.config['auto_start_websocket']:
                log_info("启动WebSocket服务器...", "MAIN")
                ws_result = start_websocket_server(self.config['websocket_host'], self.config['websocket_port'])
                
                if ws_result['status'] == 'success':
                    self.websocket_server_running = True
                    log_success(f"WebSocket服务器启动成功: ws://{self.config['websocket_host']}:{self.config['websocket_port']}", "MAIN")
                else:
                    log_warning(f"WebSocket服务器启动失败: {ws_result.get('message', 'Unknown error')}", "MAIN")
                    log_warning("系统将以HTTP模式运行", "MAIN")
            
            return True
            
        except Exception as e:
            log_error(f"启动服务失败: {e}", "MAIN")
            return False
    
    def _display_system_info(self):
        """显示系统信息"""
        print("📊 系统信息")
        print("-" * 30)
        print(f"🕐 启动时间: {get_timestamp()}")
        print(f"📁 配置目录: {get_config_dir()}")
        print(f"🖼️  图片目录: {get_image_dir()}")
        print(f"📊 结果目录: {get_result_dir()}")
        print(f"🔧 Python版本: {sys.version.split()[0]}")
        
        # 检查依赖库
        deps_status = self._check_dependencies()
        print(f"📦 依赖检查: {deps_status}")
        print()
    
    def _check_dependencies(self) -> str:
        """检查依赖库"""
        try:
            missing_deps = []
            
            # 检查websockets库
            try:
                import websockets
                websockets_version = websockets.__version__
            except ImportError:
                missing_deps.append("websockets")
                websockets_version = "未安装"
            
            if missing_deps:
                return f"缺少依赖: {', '.join(missing_deps)}"
            else:
                return f"完整 (websockets: {websockets_version})"
                
        except Exception as e:
            return f"检查失败: {e}"
    
    def display_running_info(self):
        """显示运行信息"""
        print("🚀 服务运行信息")
        print("=" * 60)
        
        # HTTP服务器信息
        if self.http_server_running:
            print(f"🌐 HTTP服务器: http://{self.config['http_host']}:{self.config['http_port']}")
            print(f"   📋 主页: http://{self.config['http_host']}:{self.config['http_port']}/")
            print(f"   📚 API文档: http://{self.config['http_host']}:{self.config['http_port']}/api-docs")
            print(f"   🎯 标记页面: http://{self.config['http_host']}:{self.config['http_port']}/biaoji.html")
        
        # WebSocket服务器信息
        if self.websocket_server_running:
            print(f"🔌 WebSocket服务器: ws://{self.config['websocket_host']}:{self.config['websocket_port']}")
            print(f"   🤵 荷官端连接地址: ws://{self.config['websocket_host']}:{self.config['websocket_port']}")
        
        print("\n💡 使用说明:")
        print("1. 浏览器访问HTTP服务器进行配置和管理")
        print("2. 荷官端通过WebSocket连接获取识别结果")
        print("3. API接口支持扑克识别结果的接收和查询")
        print("4. 按 Ctrl+C 优雅停止所有服务")
        print("=" * 60)
    
    def run_main_loop(self):
        """运行主循环"""
        try:
            # 设置信号处理
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            log_info("系统运行中，等待服务请求...", "MAIN")
            
            # 主循环
            while not self.shutdown_requested:
                try:
                    time.sleep(1)
                    
                    # 定期检查服务状态（每30秒）
                    if int(time.time()) % 30 == 0:
                        self._check_services_health()
                        
                except KeyboardInterrupt:
                    self.shutdown_requested = True
                    break
                    
        except Exception as e:
            log_error(f"主循环异常: {e}", "MAIN")
            self.shutdown_requested = True
    
    def _check_services_health(self):
        """检查服务健康状态"""
        try:
            # 检查HTTP服务器
            if self.http_server_running:
                http_info = get_server_info()
                if not http_info.get('running', False):
                    log_warning("HTTP服务器状态异常", "MAIN")
            
            # 检查WebSocket服务器
            if self.websocket_server_running:
                ws_info = get_websocket_server_info()
                if ws_info['status'] != 'success' or not ws_info['data'].get('running', False):
                    log_warning("WebSocket服务器状态异常", "MAIN")
            
            # 检查连接统计（仅记录，不输出到控制台）
            conn_stats = get_connection_stats()
            if conn_stats['status'] == 'success':
                active_connections = conn_stats['data'].get('current_active', 0)
                if active_connections > 0:
                    log_info(f"活跃连接: {active_connections}", "MAIN")
                    
        except Exception as e:
            log_error(f"健康检查失败: {e}", "MAIN")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        log_info(f"接收到信号 {signum}，准备关闭系统...", "MAIN")
        self.shutdown_requested = True
    
    def shutdown_system(self):
        """关闭系统"""
        try:
            print("\n🔄 正在关闭系统...")
            
            # 关闭WebSocket服务器
            if self.websocket_server_running:
                log_info("关闭WebSocket服务器...", "MAIN")
                ws_result = stop_websocket_server()
                if ws_result['status'] == 'success':
                    log_success("WebSocket服务器已关闭", "MAIN")
                else:
                    log_warning(f"WebSocket服务器关闭异常: {ws_result.get('message', 'Unknown')}", "MAIN")
                self.websocket_server_running = False
            
            # 关闭HTTP服务器
            if self.http_server_running:
                log_info("关闭HTTP服务器...", "MAIN")
                http_result = stop_http_server()
                if http_result:
                    log_success("HTTP服务器已关闭", "MAIN")
                else:
                    log_warning("HTTP服务器关闭异常", "MAIN")
                self.http_server_running = False
            
            # 清理连接
            log_info("清理系统资源...", "MAIN")
            cleanup_all_connections()
            
            log_success("系统关闭完成", "MAIN")
            print("👋 扑克识别系统已安全关闭")
            
        except Exception as e:
            log_error(f"关闭系统时出错: {e}", "MAIN")
            print(f"⚠️ 系统关闭过程中出现错误: {e}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='扑克识别系统 - 提供HTTP API和WebSocket服务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                          # 使用默认配置启动
  python main.py --http-port 8080        # 指定HTTP端口
  python main.py --websocket-port 8002   # 指定WebSocket端口
  python main.py --http-only             # 仅启动HTTP服务器
  python main.py --host 0.0.0.0          # 监听所有网络接口
        """
    )
    
    parser.add_argument('--host', default='localhost', 
                       help='服务器监听地址 (默认: localhost)')
    parser.add_argument('--http-port', type=int, default=8000,
                       help='HTTP服务器端口 (默认: 8000)')
    parser.add_argument('--websocket-port', type=int, default=8001,
                       help='WebSocket服务器端口 (默认: 8001)')
    parser.add_argument('--http-only', action='store_true',
                       help='仅启动HTTP服务器，不启动WebSocket服务器')
    parser.add_argument('--no-websocket', action='store_true',
                       help='禁用WebSocket服务器')
    parser.add_argument('--version', action='version', version='扑克识别系统 v2.0')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 创建系统实例
        system = PokerRecognitionSystem()
        
        # 更新配置
        system.config.update({
            'http_host': args.host,
            'http_port': args.http_port,
            'websocket_host': args.host,
            'websocket_port': args.websocket_port,
            'auto_start_websocket': not (args.http_only or args.no_websocket)
        })
        
        # 初始化系统
        if not system.initialize_system():
            print("❌ 系统初始化失败")
            return 1
        
        # 启动服务
        if not system.start_services(http_only=args.http_only):
            print("❌ 服务启动失败")
            return 1
        
        # 显示运行信息
        system.display_running_info()
        
        # 进入主循环
        system.run_main_loop()
        
        # 关闭系统
        system.shutdown_system()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，正在关闭...")
        return 0
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        log_error(f"主程序异常: {e}", "MAIN")
        return 1

if __name__ == "__main__":
    sys.exit(main())