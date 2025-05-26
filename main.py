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
import os
from pathlib import Path

# 路径设置 - 使用更稳健的方法
def setup_project_paths():
    """设置项目路径"""
    # 获取当前文件的绝对路径
    current_file = Path(__file__).resolve()
    project_root = current_file.parent
    
    # 将项目根目录添加到Python路径（如果还没有添加）
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    # 确保src目录也在路径中（如果存在）
    src_dir = project_root / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    return project_root

# 设置项目路径
PROJECT_ROOT = setup_project_paths()

# 导入模块时使用try-except处理导入错误
def safe_import():
    """安全导入所有需要的模块"""
    try:
        from src.core.utils import (
            get_timestamp, ensure_dirs_exist, get_config_dir, get_image_dir, get_result_dir,
            log_info, log_success, log_error, log_warning
        )
        from src.servers.http_server import start_http_server, stop_http_server, get_server_info
        from src.servers.websocket_server import start_websocket_server, stop_websocket_server, get_websocket_server_info
        from src.websocket.connection_manager import cleanup_all_connections, get_connection_stats
        from src.core.config_manager import get_config_status
        
        return {
            'utils': {
                'get_timestamp': get_timestamp,
                'ensure_dirs_exist': ensure_dirs_exist,
                'get_config_dir': get_config_dir,
                'get_image_dir': get_image_dir,
                'get_result_dir': get_result_dir,
                'log_info': log_info,
                'log_success': log_success,
                'log_error': log_error,
                'log_warning': log_warning
            },
            'http_server': {
                'start_http_server': start_http_server,
                'stop_http_server': stop_http_server,
                'get_server_info': get_server_info
            },
            'websocket_server': {
                'start_websocket_server': start_websocket_server,
                'stop_websocket_server': stop_websocket_server,
                'get_websocket_server_info': get_websocket_server_info
            },
            'connection_manager': {
                'cleanup_all_connections': cleanup_all_connections,
                'get_connection_stats': get_connection_stats
            },
            'config_manager': {
                'get_config_status': get_config_status
            }
        }
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        print(f"📁 当前工作目录: {os.getcwd()}")
        print(f"📁 项目根目录: {PROJECT_ROOT}")
        print(f"🔍 Python路径: {sys.path[:3]}...")  # 只显示前3个路径避免过长
        
        # 检查关键目录是否存在
        src_dir = PROJECT_ROOT / "src"
        if not src_dir.exists():
            print(f"❌ src目录不存在: {src_dir}")
        else:
            print(f"✅ src目录存在: {src_dir}")
            
            # 检查子目录
            subdirs = ['core', 'servers', 'websocket']
            for subdir in subdirs:
                subdir_path = src_dir / subdir
                if subdir_path.exists():
                    print(f"✅ {subdir}目录存在: {subdir_path}")
                else:
                    print(f"❌ {subdir}目录不存在: {subdir_path}")
        
        raise ImportError(f"无法导入必要的模块，请检查项目结构: {e}")

# 导入模块
modules = safe_import()

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
        
        modules['utils']['log_info']("扑克识别系统初始化", "MAIN")
    
    def initialize_system(self) -> bool:
        """初始化系统"""
        try:
            print("🎮 扑克识别系统启动中...")
            print("=" * 60)
            
            # 检查和创建必要目录
            modules['utils']['log_info']("检查系统目录...", "MAIN")
            required_dirs = [
                modules['utils']['get_config_dir'](), 
                modules['utils']['get_image_dir'](), 
                modules['utils']['get_result_dir']()
            ]
            modules['utils']['ensure_dirs_exist'](*required_dirs)
            
            # 检查配置文件状态
            config_status = modules['config_manager']['get_config_status']()
            if config_status['status'] == 'success':
                data = config_status['data']
                modules['utils']['log_success'](f"配置检查完成: {data['total_cameras']} 个摄像头", "MAIN")
            else:
                modules['utils']['log_warning']("配置文件检查失败，将使用默认配置", "MAIN")
            
            # 显示系统信息
            self._display_system_info()
            
            return True
            
        except Exception as e:
            modules['utils']['log_error'](f"系统初始化失败: {e}", "MAIN")
            return False
    
    def start_services(self, http_only: bool = False) -> bool:
        """启动服务"""
        try:
            # 启动HTTP服务器
            modules['utils']['log_info']("启动HTTP服务器...", "MAIN")
            http_result = modules['http_server']['start_http_server'](
                self.config['http_host'], 
                self.config['http_port']
            )
            
            if http_result:
                self.http_server_running = True
                modules['utils']['log_success'](
                    f"HTTP服务器启动成功: http://{self.config['http_host']}:{self.config['http_port']}", 
                    "MAIN"
                )
            else:
                modules['utils']['log_error']("HTTP服务器启动失败", "MAIN")
                return False
            
            # 启动WebSocket服务器（如果需要）
            if not http_only and self.config['auto_start_websocket']:
                modules['utils']['log_info']("启动WebSocket服务器...", "MAIN")
                ws_result = modules['websocket_server']['start_websocket_server'](
                    self.config['websocket_host'], 
                    self.config['websocket_port']
                )
                
                if ws_result['status'] == 'success':
                    self.websocket_server_running = True
                    modules['utils']['log_success'](
                        f"WebSocket服务器启动成功: ws://{self.config['websocket_host']}:{self.config['websocket_port']}", 
                        "MAIN"
                    )
                else:
                    modules['utils']['log_warning'](
                        f"WebSocket服务器启动失败: {ws_result.get('message', 'Unknown error')}", 
                        "MAIN"
                    )
                    modules['utils']['log_warning']("系统将以HTTP模式运行", "MAIN")
            
            return True
            
        except Exception as e:
            modules['utils']['log_error'](f"启动服务失败: {e}", "MAIN")
            return False
    
    def _display_system_info(self):
        """显示系统信息"""
        print("📊 系统信息")
        print("-" * 30)
        print(f"🕐 启动时间: {modules['utils']['get_timestamp']()}")
        print(f"📁 项目根目录: {PROJECT_ROOT}")
        print(f"📁 配置目录: {modules['utils']['get_config_dir']()}")
        print(f"🖼️  图片目录: {modules['utils']['get_image_dir']()}")
        print(f"📊 结果目录: {modules['utils']['get_result_dir']()}")
        print(f"🔧 Python版本: {sys.version.split()[0]}")
        print(f"💻 当前工作目录: {os.getcwd()}")
        
        # 检查依赖库
        deps_status = self._check_dependencies()
        print(f"📦 依赖检查: {deps_status}")
        print()
    
    def _check_dependencies(self) -> str:
        """检查依赖库"""
        try:
            missing_deps = []
            versions = {}
            
            # 检查websockets库
            try:
                import websockets
                versions['websockets'] = websockets.__version__
            except ImportError:
                missing_deps.append("websockets")
            
            # 检查其他关键库
            try:
                import asyncio
                versions['asyncio'] = "内置"
            except ImportError:
                missing_deps.append("asyncio")
            
            try:
                from pathlib import Path
                versions['pathlib'] = "内置"
            except ImportError:
                missing_deps.append("pathlib")
            
            if missing_deps:
                return f"缺少依赖: {', '.join(missing_deps)}"
            else:
                version_info = ', '.join([f"{k}: {v}" for k, v in versions.items()])
                return f"完整 ({version_info})"
                
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
            
            modules['utils']['log_info']("系统运行中，等待服务请求...", "MAIN")
            
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
            modules['utils']['log_error'](f"主循环异常: {e}", "MAIN")
            self.shutdown_requested = True
    
    def _check_services_health(self):
        """检查服务健康状态"""
        try:
            # 检查HTTP服务器
            if self.http_server_running:
                http_info = modules['http_server']['get_server_info']()
                if not http_info.get('running', False):
                    modules['utils']['log_warning']("HTTP服务器状态异常", "MAIN")
            
            # 检查WebSocket服务器
            if self.websocket_server_running:
                ws_info = modules['websocket_server']['get_websocket_server_info']()
                if ws_info['status'] != 'success' or not ws_info['data'].get('running', False):
                    modules['utils']['log_warning']("WebSocket服务器状态异常", "MAIN")
            
            # 检查连接统计（仅记录，不输出到控制台）
            conn_stats = modules['connection_manager']['get_connection_stats']()
            if conn_stats['status'] == 'success':
                active_connections = conn_stats['data'].get('current_active', 0)
                if active_connections > 0:
                    modules['utils']['log_info'](f"活跃连接: {active_connections}", "MAIN")
                    
        except Exception as e:
            modules['utils']['log_error'](f"健康检查失败: {e}", "MAIN")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        modules['utils']['log_info'](f"接收到信号 {signum}，准备关闭系统...", "MAIN")
        self.shutdown_requested = True
    
    def shutdown_system(self):
        """关闭系统"""
        try:
            print("\n🔄 正在关闭系统...")
            
            # 关闭WebSocket服务器
            if self.websocket_server_running:
                modules['utils']['log_info']("关闭WebSocket服务器...", "MAIN")
                ws_result = modules['websocket_server']['stop_websocket_server']()
                if ws_result['status'] == 'success':
                    modules['utils']['log_success']("WebSocket服务器已关闭", "MAIN")
                else:
                    modules['utils']['log_warning'](
                        f"WebSocket服务器关闭异常: {ws_result.get('message', 'Unknown')}", 
                        "MAIN"
                    )
                self.websocket_server_running = False
            
            # 关闭HTTP服务器
            if self.http_server_running:
                modules['utils']['log_info']("关闭HTTP服务器...", "MAIN")
                http_result = modules['http_server']['stop_http_server']()
                if http_result:
                    modules['utils']['log_success']("HTTP服务器已关闭", "MAIN")
                else:
                    modules['utils']['log_warning']("HTTP服务器关闭异常", "MAIN")
                self.http_server_running = False
            
            # 清理连接
            modules['utils']['log_info']("清理系统资源...", "MAIN")
            modules['connection_manager']['cleanup_all_connections']()
            
            modules['utils']['log_success']("系统关闭完成", "MAIN")
            print("👋 扑克识别系统已安全关闭")
            
        except Exception as e:
            modules['utils']['log_error'](f"关闭系统时出错: {e}", "MAIN")
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
  python main.py --check-paths           # 检查路径配置
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
    parser.add_argument('--check-paths', action='store_true',
                       help='检查路径配置并退出')
    parser.add_argument('--version', action='version', version='扑克识别系统 v2.1')
    
    return parser.parse_args()

def check_project_structure():
    """检查项目结构"""
    print("🔍 检查项目结构...")
    print("=" * 50)
    
    print(f"📁 项目根目录: {PROJECT_ROOT}")
    print(f"💻 当前工作目录: {os.getcwd()}")
    print(f"🐍 Python可执行文件: {sys.executable}")
    print(f"🔍 Python路径前5个: {sys.path[:5]}")
    
    # 检查关键目录和文件
    structure_checks = [
        ("src", "源代码目录"),
        ("src/core", "核心模块目录"),
        ("src/servers", "服务器模块目录"),
        ("src/websocket", "WebSocket模块目录"),
        ("src/core/utils.py", "工具模块"),
        ("src/core/config_manager.py", "配置管理模块"),
        ("src/servers/http_server.py", "HTTP服务器模块"),
        ("src/servers/websocket_server.py", "WebSocket服务器模块"),
        ("src/websocket/connection_manager.py", "连接管理模块"),
    ]
    
    print("\n📋 目录结构检查:")
    for path_str, desc in structure_checks:
        path = PROJECT_ROOT / path_str
        if path.exists():
            print(f"✅ {desc}: {path}")
        else:
            print(f"❌ {desc}: {path} (不存在)")
    
    print("=" * 50)

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 如果只是检查路径，执行检查后退出
        if args.check_paths:
            check_project_structure()
            return 0
        
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
        print(f"📍 异常位置: {type(e).__name__}")
        try:
            modules['utils']['log_error'](f"主程序异常: {e}", "MAIN")
        except:
            # 如果连日志都无法记录，直接输出
            print(f"无法记录日志: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())