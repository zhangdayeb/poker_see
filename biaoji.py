#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标记功能入口程序 - 专门用于扑克位置标记
功能:
1. 启动HTTP服务器提供标记界面
2. 摄像头拍照功能
3. 位置标记和保存
4. 标记数据管理
5. 批量标记支持
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
    
    return project_root

# 设置项目路径
PROJECT_ROOT = setup_project_paths()

# 导入系统模块
from config_loader import (
    load_camera_config, get_enabled_cameras, get_camera_by_id, 
    validate_all_configs, get_config_summary
)
from state_manager import (
    register_process, unregister_process, update_heartbeat,
    lock_camera, release_camera, check_camera_available
)

# 导入核心模块
from src.core.utils import (
    get_timestamp, ensure_dirs_exist, get_config_dir, get_image_dir, get_result_dir,
    log_info, log_success, log_error, log_warning
)

class BiaojiSystem:
    """标记系统"""
    
    def __init__(self):
        """初始化标记系统"""
        self.process_name = "biaoji"
        self.process_type = "marking"
        self.shutdown_requested = False
        self.http_server_running = False
        
        # 系统配置
        self.config = {
            'http_host': 'localhost',
            'http_port': 8000,
            'auto_take_photo': True,
            'backup_marks': True
        }
        
        # 服务组件
        self.http_server = None
        
        log_info("标记系统初始化完成", "BIAOJI")
    
    def initialize_system(self) -> bool:
        """初始化系统"""
        try:
            print("🎯 扑克位置标记系统启动中...")
            print("=" * 60)
            
            # 注册进程
            register_result = register_process(self.process_name, self.process_type)
            if register_result['status'] != 'success':
                print(f"❌ 进程注册失败: {register_result['message']}")
                return False
            
            # 检查配置
            if not self._check_system_config():
                return False
            
            # 检查目录
            self._ensure_directories()
            
            # 显示系统信息
            self._display_system_info()
            
            return True
            
        except Exception as e:
            log_error(f"系统初始化失败: {e}", "BIAOJI")
            print(f"❌ 系统初始化失败: {e}")
            return False
    
    def _check_system_config(self) -> bool:
        """检查系统配置"""
        try:
            print("📋 检查系统配置...")
            
            # 验证所有配置
            validation_result = validate_all_configs()
            if validation_result['status'] != 'success':
                print(f"❌ 配置验证失败: {validation_result['message']}")
                return False
            
            validation_data = validation_result['data']
            if not validation_data['overall_valid']:
                print("❌ 配置文件存在问题:")
                for config_name, config_result in validation_data['validation_results'].items():
                    if not config_result['valid']:
                        print(f"   - {config_name}: {config_result['message']}")
                return False
            
            # 获取摄像头配置
            camera_result = get_enabled_cameras()
            if camera_result['status'] != 'success':
                print(f"❌ 获取摄像头配置失败: {camera_result['message']}")
                return False
            
            camera_count = camera_result['data']['total_count']
            if camera_count == 0:
                print("⚠️  没有找到启用的摄像头，请先配置摄像头")
                print("   您可以修改 src/config/camera.json 文件添加摄像头配置")
                return False
            
            print(f"✅ 配置检查完成: {camera_count} 个启用摄像头")
            return True
            
        except Exception as e:
            log_error(f"配置检查失败: {e}", "BIAOJI")
            print(f"❌ 配置检查失败: {e}")
            return False
    
    def _ensure_directories(self):
        """确保必要目录存在"""
        try:
            dirs = [
                get_config_dir(),
                get_image_dir(),
                get_result_dir()
            ]
            ensure_dirs_exist(*dirs)
            print("✅ 系统目录检查完成")
        except Exception as e:
            log_error(f"目录检查失败: {e}", "BIAOJI")
    
    def _display_system_info(self):
        """显示系统信息"""
        try:
            # 获取配置摘要
            summary_result = get_config_summary()
            if summary_result['status'] == 'success':
                summary_data = summary_result['data']
                camera_summary = summary_data.get('camera_summary', {})
                
                print("📊 系统信息:")
                print(f"   总摄像头数: {camera_summary.get('total_cameras', 0)}")
                print(f"   启用摄像头: {camera_summary.get('enabled_cameras', 0)}")
                print(f"   禁用摄像头: {camera_summary.get('disabled_cameras', 0)}")
                
        except Exception as e:
            log_warning(f"显示系统信息失败: {e}", "BIAOJI")
    
    def start_http_server(self) -> bool:
        """启动HTTP服务器"""
        try:
            print("🌐 启动HTTP服务器...")
            
            # 导入HTTP服务器模块
            from src.servers.http_server import start_http_server
            
            result = start_http_server(self.config['http_host'], self.config['http_port'])
            
            if result:
                self.http_server_running = True
                print(f"✅ HTTP服务器启动成功")
                print(f"   地址: http://{self.config['http_host']}:{self.config['http_port']}")
                print(f"   标记页面: http://{self.config['http_host']}:{self.config['http_port']}/biaoji.html")
                return True
            else:
                print("❌ HTTP服务器启动失败")
                return False
                
        except Exception as e:
            log_error(f"HTTP服务器启动失败: {e}", "BIAOJI")
            print(f"❌ HTTP服务器启动失败: {e}")
            return False
    
    def display_usage_info(self):
        """显示使用说明"""
        print("\n🎯 标记系统使用说明")
        print("=" * 60)
        print("1. 📱 打开浏览器访问标记页面")
        print(f"   URL: http://{self.config['http_host']}:{self.config['http_port']}/biaoji.html")
        print("")
        print("2. 🎮 标记操作流程:")
        print("   - 选择摄像头")
        print("   - 点击拍照获取图片")
        print("   - 选择要标记的位置（庄1、庄2、庄3、闲1、闲2、闲3）")
        print("   - 在图片上拖拽选择区域")
        print("   - 保存标记数据")
        print("")
        print("3. ⚡ 快捷功能:")
        print("   - 支持拖拽调整标记框大小")
        print("   - 双击删除标记")
        print("   - 批量重置所有标记") 
        print("   - 实时显示标记状态")
        print("")
        print("4. 💡 使用提示:")
        print("   - 标记时尽量精确框选扑克牌位置")
        print("   - 建议按顺序完成所有位置标记")
        print("   - 及时保存标记数据避免丢失")
        print("   - 可以随时重新拍照更新图片")
        print("=" * 60)
        print("📝 按 Ctrl+C 退出标记系统")
    
    def run_main_loop(self):
        """运行主循环"""
        try:
            # 设置信号处理
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            print("✨ 标记系统运行中...")
            
            # 心跳更新循环
            last_heartbeat = time.time()
            heartbeat_interval = 30  # 30秒更新一次心跳
            
            while not self.shutdown_requested:
                # 更新心跳
                current_time = time.time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    update_heartbeat()
                    last_heartbeat = current_time
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.shutdown_requested = True
        except Exception as e:
            log_error(f"主循环异常: {e}", "BIAOJI")
            self.shutdown_requested = True
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n📡 接收到信号 {signum}，准备关闭标记系统...")
        self.shutdown_requested = True
    
    def shutdown_system(self):
        """关闭系统"""
        try:
            print("\n🔄 正在关闭标记系统...")
            
            # 关闭HTTP服务器
            if self.http_server_running:
                try:
                    from src.servers.http_server import stop_http_server
                    result = stop_http_server()
                    if result:
                        print("✅ HTTP服务器已关闭")
                    else:
                        print("⚠️  HTTP服务器关闭异常")
                except Exception as e:
                    log_error(f"关闭HTTP服务器失败: {e}", "BIAOJI")
            
            # 注销进程
            unregister_result = unregister_process()
            if unregister_result['status'] == 'success':
                print("✅ 进程注销成功")
            else:
                print("⚠️  进程注销异常")
            
            print("👋 标记系统已安全关闭")
            
        except Exception as e:
            log_error(f"关闭系统失败: {e}", "BIAOJI")
            print(f"❌ 关闭系统时出错: {e}")
    
    def test_camera_connections(self):
        """测试摄像头连接"""
        try:
            print("\n🔍 测试摄像头连接...")
            
            # 获取启用的摄像头
            cameras_result = get_enabled_cameras()
            if cameras_result['status'] != 'success':
                print("❌ 获取摄像头列表失败")
                return
            
            cameras = cameras_result['data']['cameras']
            
            # 导入拍照控制器
            from src.processors.photo_controller import test_camera_connection
            
            for camera in cameras:
                camera_id = camera['id']
                camera_name = camera.get('name', f'摄像头{camera_id}')
                
                print(f"   测试 {camera_name} ({camera_id})...", end=' ')
                
                # 检查摄像头可用性
                availability = check_camera_available(camera_id)
                if availability['status'] == 'success' and not availability['data']['available']:
                    print("⚠️  被其他进程占用")
                    continue
                
                # 测试连接
                test_result = test_camera_connection(camera_id)
                if test_result['status'] == 'success':
                    print("✅ 连接正常")
                else:
                    print(f"❌ 连接失败: {test_result['message']}")
                    
        except Exception as e:
            log_error(f"测试摄像头连接失败: {e}", "BIAOJI")
            print(f"❌ 测试摄像头连接失败: {e}")
    
    def interactive_camera_test(self):
        """交互式摄像头测试"""
        try:
            # 获取启用的摄像头
            cameras_result = get_enabled_cameras()
            if cameras_result['status'] != 'success':
                print("❌ 获取摄像头列表失败")
                return
            
            cameras = cameras_result['data']['cameras']
            if not cameras:
                print("❌ 没有可用的摄像头")
                return
            
            print("\n📷 可用摄像头列表:")
            for i, camera in enumerate(cameras):
                print(f"   {i+1}. {camera.get('name', f'摄像头{camera['id']}')} ({camera['id']})")
            
            while True:
                try:
                    choice = input("\n请选择要测试的摄像头 (输入序号，q退出): ").strip()
                    
                    if choice.lower() == 'q':
                        break
                    
                    index = int(choice) - 1
                    if 0 <= index < len(cameras):
                        camera = cameras[index]
                        camera_id = camera['id']
                        
                        print(f"\n🔍 测试摄像头 {camera['name']} ({camera_id})")
                        
                        # 锁定摄像头
                        lock_result = lock_camera(camera_id)
                        if lock_result['status'] != 'success':
                            print(f"❌ 无法锁定摄像头: {lock_result['message']}")
                            continue
                        
                        try:
                            # 测试拍照
                            from src.processors.photo_controller import take_photo_by_id
                            
                            print("📸 正在拍照...")
                            photo_result = take_photo_by_id(camera_id)
                            
                            if photo_result['status'] == 'success':
                                print("✅ 拍照成功!")
                                print(f"   图片: {photo_result['data']['filename']}")
                                print(f"   大小: {photo_result['data']['file_size']/1024:.1f} KB")
                                print(f"   URL: http://{self.config['http_host']}:{self.config['http_port']}{photo_result['data']['image_url']}")
                            else:
                                print(f"❌ 拍照失败: {photo_result['message']}")
                        
                        finally:
                            # 释放摄像头
                            release_result = release_camera(camera_id)
                            if release_result['status'] == 'success':
                                print("🔓 摄像头已释放")
                    else:
                        print("❌ 无效的选择")
                        
                except ValueError:
                    print("❌ 请输入有效的数字")
                except KeyboardInterrupt:
                    print("\n👋 退出测试")
                    break
                    
        except Exception as e:
            log_error(f"交互式摄像头测试失败: {e}", "BIAOJI")
            print(f"❌ 交互式测试失败: {e}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='扑克位置标记系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python biaoji.py                    # 正常启动标记系统
  python biaoji.py --host 0.0.0.0    # 允许外部访问
  python biaoji.py --port 8080       # 使用8080端口
  python biaoji.py --test-cameras    # 测试摄像头连接
  python biaoji.py --interactive     # 交互式摄像头测试
        """
    )
    
    parser.add_argument('--host', default='localhost', 
                       help='HTTP服务器地址 (默认: localhost)')
    parser.add_argument('--port', type=int, default=8000, 
                       help='HTTP服务器端口 (默认: 8000)')
    parser.add_argument('--test-cameras', action='store_true',
                       help='测试所有摄像头连接后退出')
    parser.add_argument('--interactive', action='store_true',
                       help='交互式摄像头测试模式')
    parser.add_argument('--no-auto-photo', action='store_true',
                       help='禁用自动拍照功能')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试模式')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析参数
        args = parse_arguments()
        
        # 创建标记系统实例
        system = BiaojiSystem()
        
        # 更新配置
        system.config.update({
            'http_host': args.host,
            'http_port': args.port,
            'auto_take_photo': not args.no_auto_photo,
            'debug_mode': args.debug
        })
        
        # 如果是测试模式
        if args.test_cameras:
            print("🧪 摄像头连接测试模式")
            if not system.initialize_system():
                return 1
            system.test_camera_connections()
            return 0
        
        # 如果是交互式测试模式
        if args.interactive:
            print("🎮 交互式摄像头测试模式")
            if not system.initialize_system():
                return 1
            system.interactive_camera_test()
            return 0
        
        # 正常模式 - 初始化系统
        if not system.initialize_system():
            return 1
        
        # 启动HTTP服务器
        if not system.start_http_server():
            return 1
        
        # 显示使用说明
        system.display_usage_info()
        
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