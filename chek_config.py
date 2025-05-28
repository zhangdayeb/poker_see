#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的配置检查工具 - 更直观的检测输出和效果展示
功能:
1. 美观的控制台输出界面
2. 实时进度显示
3. 详细的检测结果
4. 彩色状态指示
5. 生成详细报告
"""

import sys
import argparse
import time
import threading
from pathlib import Path
from datetime import datetime
import subprocess

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

# 导入模块
from config_loader import validate_all_configs, get_config_summary, get_enabled_cameras
from src.core.utils import log_info, log_success, log_error, log_warning

class Colors:
    """控制台颜色定义"""
    RED = '\033[91m'
    GREEN = '\033[92m' 
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    # 背景色
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'
    BG_BLUE = '\033[104m'

class ProgressIndicator:
    """进度指示器"""
    
    def __init__(self, message="处理中"):
        self.message = message
        self.running = False
        self.thread = None
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.current_char = 0
    
    def start(self):
        """开始显示进度"""
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()
    
    def stop(self):
        """停止显示进度"""
        self.running = False
        if self.thread:
            self.thread.join()
        # 清除进度显示
        print(f"\r{' ' * (len(self.message) + 5)}\r", end='', flush=True)
    
    def _spin(self):
        """旋转进度指示"""
        while self.running:
            char = self.spinner_chars[self.current_char]
            print(f"\r{Colors.CYAN}{char}{Colors.END} {self.message}...", end='', flush=True)
            self.current_char = (self.current_char + 1) % len(self.spinner_chars)
            time.sleep(0.1)

class OptimizedConfigChecker:
    """优化的配置检查器"""
    
    def __init__(self):
        """初始化配置检查器"""
        self.check_results = {}
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = 0
        self.warning_checks = 0
        
        # 检查统计
        self.stats = {
            'start_time': datetime.now(),
            'end_time': None,
            'duration': 0,
            'system_info': {},
            'performance_metrics': {}
        }
        
        self.project_root = setup_project_paths()
        
    def print_header(self):
        """打印美观的标题"""
        print(f"\n{Colors.CYAN}{'=' * 80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.WHITE}🔍 扑克识别系统 - 配置检查工具 v2.0{Colors.END}")
        print(f"{Colors.CYAN}{'=' * 80}{Colors.END}")
        print(f"{Colors.YELLOW}⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{Colors.YELLOW}📁 项目目录: {self.project_root}{Colors.END}")
        print(f"{Colors.CYAN}{'=' * 80}{Colors.END}\n")
    
    def print_section_header(self, title, icon="📋"):
        """打印章节标题"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{icon} {title}{Colors.END}")
        print(f"{Colors.BLUE}{'-' * (len(title) + 4)}{Colors.END}")
    
    def run_all_checks(self, test_cameras: bool = False, test_algorithms: bool = False, 
                      test_performance: bool = False, test_photo: bool = False) -> bool:
        """运行所有检查"""
        self.print_header()
        
        start_time = time.time()
        
        try:
            # 1. 系统环境检查
            self.print_section_header("系统环境检查", "🖥️")
            self._check_system_environment()
            
            # 2. 基础配置检查
            self.print_section_header("基础配置检查", "📋")
            self._check_basic_config()
            
            # 3. 摄像头配置检查
            self.print_section_header("摄像头配置检查", "📷")
            self._check_camera_config()
            
            # 4. 算法依赖检查
            if test_algorithms:
                self.print_section_header("识别算法检查", "🤖")
                self._test_recognition_algorithms()
            
            # 5. 摄像头连接测试 (使用实际模块)
            if test_cameras:
                self.print_section_header("摄像头连接测试", "🔌")
                self._test_camera_connections()
            
            # 6. 实际拍照测试 (可选)
            if test_photo:
                self.print_section_header("实际拍照测试", "📸")
                self._test_actual_photo_capture()
            
            # 7. 性能测试
            if test_performance:
                self.print_section_header("性能基准测试", "⚡")
                self._test_system_performance()
            
            # 8. 推送配置检查
            self.print_section_header("推送配置检查", "📡")
            self._check_push_config()
            
            # 计算检查时长
            self.stats['end_time'] = datetime.now()
            self.stats['duration'] = time.time() - start_time
            
            # 生成检查报告
            self._generate_detailed_report()
            
            return self.failed_checks == 0
        
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}⚠️  检查被用户中断{Colors.END}")
            return False
        except Exception as e:
            print(f"\n{Colors.RED}💥 检查过程异常: {e}{Colors.END}")
            return False
    
    def _check_system_environment(self):
        """检查系统环境"""
        import platform
        import os
        
        # 系统信息
        self.stats['system_info'] = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': platform.python_version(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'hostname': platform.node()
        }
        
        sys_info = self.stats['system_info']
        
        print(f"  🖥️  操作系统: {Colors.GREEN}{sys_info['platform']} {sys_info['architecture']}{Colors.END}")
        print(f"  🐍 Python版本: {Colors.GREEN}{sys_info['python_version']}{Colors.END}")
        print(f"  💻 处理器: {Colors.GREEN}{sys_info['processor'][:50]}...{Colors.END}")
        print(f"  🏠 主机名: {Colors.GREEN}{sys_info['hostname']}{Colors.END}")
        
        # 检查Python版本
        python_version = tuple(map(int, sys_info['python_version'].split('.')[:2]))
        if python_version >= (3, 8):
            self._record_check("Python版本", True, f"Python {sys_info['python_version']} (兼容)")
        else:
            self._record_check("Python版本", False, f"Python {sys_info['python_version']} (建议3.8+)")
    
    def _check_basic_config(self):
        """检查基础配置"""
        # 配置文件验证
        progress = ProgressIndicator("验证配置文件")
        progress.start()
        
        try:
            validation_result = validate_all_configs()
            progress.stop()
            
            if validation_result['status'] == 'success':
                validation_data = validation_result['data']
                
                if validation_data['overall_valid']:
                    self._record_check("配置文件验证", True, "所有配置文件格式正确")
                    
                    # 详细显示各配置状态
                    for config_name, result in validation_data['validation_results'].items():
                        status_icon = "✅" if result['valid'] else "❌"
                        status_color = Colors.GREEN if result['valid'] else Colors.RED
                        config_display_name = {
                            'camera_config': '摄像头配置',
                            'recognition_config': '识别算法配置', 
                            'push_config': '推送配置'
                        }.get(config_name, config_name)
                        
                        print(f"    {status_icon} {config_display_name}: {status_color}{result['message']}{Colors.END}")
                else:
                    invalid_configs = [
                        name for name, result in validation_data['validation_results'].items()
                        if not result['valid']
                    ]
                    self._record_check("配置文件验证", False, f"配置文件错误: {', '.join(invalid_configs)}")
            else:
                self._record_check("配置文件验证", False, validation_result['message'])
                
        except Exception as e:
            progress.stop()
            self._record_check("配置文件验证", False, f"验证异常: {str(e)}")
        
        # 目录结构检查
        self._check_directory_structure()
        
        # 关键文件检查
        self._check_critical_files()
    
    def _check_directory_structure(self):
        """检查目录结构"""
        required_dirs = {
            'src/config': self.project_root / "src" / "config",
            'src/config/yolov8': self.project_root / "src" / "config" / "yolov8",
            'image': self.project_root / "image",
            'image/cut': self.project_root / "image" / "cut", 
            'result': self.project_root / "result",
            'result/recognition': self.project_root / "result" / "recognition",
            'result/history': self.project_root / "result" / "history"
        }
        
        missing_dirs = []
        existing_dirs = []
        created_dirs = []
        
        for dir_name, dir_path in required_dirs.items():
            if not dir_path.exists():
                missing_dirs.append(dir_name)
                # 尝试创建目录
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(dir_name)
                    print(f"    🔧 已创建目录: {Colors.YELLOW}{dir_name}{Colors.END}")
                except Exception as e:
                    print(f"    ❌ 创建目录失败 {dir_name}: {Colors.RED}{e}{Colors.END}")
            else:
                existing_dirs.append(dir_name)
                # 显示目录状态
                try:
                    files_count = len(list(dir_path.iterdir()))
                    dir_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                    size_mb = dir_size / 1024 / 1024
                    print(f"    ✅ {dir_name}: {Colors.GREEN}{files_count} 个文件, {size_mb:.1f}MB{Colors.END}")
                except:
                    print(f"    ✅ {dir_name}: {Colors.GREEN}存在{Colors.END}")
        
        if created_dirs:
            self._record_check("目录结构", True, f"结构完整，已创建 {len(created_dirs)} 个缺失目录")
        elif missing_dirs:
            self._record_check("目录结构", False, f"缺少目录: {', '.join(missing_dirs)}")
        else:
            self._record_check("目录结构", True, f"所有 {len(existing_dirs)} 个目录完整")
    
    def _check_critical_files(self):
        """检查关键文件"""
        critical_files = {
            'YOLOv8模型': self.project_root / "src" / "config" / "yolov8" / "best.pt",
            '摄像头配置': self.project_root / "src" / "config" / "camera.json",
            '主程序': self.project_root / "main.py",
            '标记程序': self.project_root / "biaoji.py",
            '识别程序': self.project_root / "see.py",
            '推送程序': self.project_root / "tui.py"
        }
        
        missing_files = []
        existing_files = []
        
        print(f"    📄 关键文件检查:")
        
        for file_name, file_path in critical_files.items():
            if file_path.exists():
                file_size = file_path.stat().st_size
                if file_size > 0:
                    size_display = self._format_file_size(file_size)
                    print(f"      ✅ {file_name}: {Colors.GREEN}{size_display}{Colors.END}")
                    existing_files.append(file_name)
                else:
                    print(f"      ⚠️  {file_name}: {Colors.YELLOW}文件为空{Colors.END}")
                    self._warning_checks += 1
            else:
                print(f"      ❌ {file_name}: {Colors.RED}不存在{Colors.END}")
                missing_files.append(file_name)
        
        if missing_files:
            self._record_check("关键文件", False, f"缺少文件: {', '.join(missing_files)}")
        else:
            self._record_check("关键文件", True, f"所有 {len(existing_files)} 个关键文件完整")
    
    def _check_camera_config(self):
        """检查摄像头配置"""
        try:
            cameras_result = get_enabled_cameras()
            
            if cameras_result['status'] != 'success':
                self._record_check("摄像头配置", False, cameras_result['message'])
                return
            
            cameras = cameras_result['data']['cameras']
            total_cameras = cameras_result['data']['all_count']
            enabled_cameras = len(cameras)
            
            print(f"    📊 摄像头统计:")
            print(f"      📷 总数量: {Colors.CYAN}{total_cameras}{Colors.END}")
            print(f"      ✅ 已启用: {Colors.GREEN}{enabled_cameras}{Colors.END}")
            print(f"      ❌ 已禁用: {Colors.YELLOW}{total_cameras - enabled_cameras}{Colors.END}")
            
            if not cameras:
                self._record_check("摄像头配置", False, "没有启用的摄像头")
                return
            
            # 详细检查每个摄像头
            print(f"    📋 摄像头详情:")
            
            valid_cameras = 0
            invalid_cameras = []
            
            for camera in cameras:
                camera_id = camera.get('id', 'unknown')
                camera_name = camera.get('name', f'摄像头{camera_id}')
                
                # 检查必需字段
                required_fields = ['id', 'name', 'ip', 'username', 'password']
                missing_fields = []
                
                for field in required_fields:
                    if field not in camera or not camera[field]:
                        missing_fields.append(field)
                
                # 检查标记位置
                mark_positions = camera.get('mark_positions', {})
                marked_positions = sum(1 for pos_data in mark_positions.values() 
                                     if pos_data.get('marked', False))
                total_positions = len(mark_positions)
                
                if missing_fields:
                    print(f"      ❌ {camera_name} ({camera_id}): {Colors.RED}缺少字段 {missing_fields}{Colors.END}")
                    invalid_cameras.append(camera_id)
                else:
                    ip = camera.get('ip', 'N/A')
                    port = camera.get('port', 554)
                    completion = (marked_positions / total_positions * 100) if total_positions > 0 else 0
                    
                    status_color = Colors.GREEN if completion > 80 else Colors.YELLOW if completion > 50 else Colors.RED
                    print(f"      ✅ {camera_name} ({camera_id}): {Colors.CYAN}{ip}:{port}{Colors.END} "
                          f"标记: {status_color}{marked_positions}/{total_positions} ({completion:.0f}%){Colors.END}")
                    valid_cameras += 1
            
            if invalid_cameras:
                self._record_check("摄像头配置", False, f"配置错误的摄像头: {', '.join(invalid_cameras)}")
            else:
                self._record_check("摄像头配置", True, f"{valid_cameras} 个摄像头配置正确")
                
        except Exception as e:
            self._record_check("摄像头配置", False, f"检查异常: {str(e)}")
    
    def _test_recognition_algorithms(self):
        """测试识别算法"""
        algorithms = {
            'YOLOv8 (ultralytics)': self._test_yolo_import,
            'EasyOCR': self._test_easyocr_import,
            'PaddleOCR': self._test_paddleocr_import,
            'OpenCV': self._test_opencv_import,
            'PIL/Pillow': self._test_pil_import,
            'WebSocket客户端': self._test_websocket_import
        }
        
        available_algorithms = []
        unavailable_algorithms = []
        
        for algo_name, test_func in algorithms.items():
            progress = ProgressIndicator(f"测试 {algo_name}")
            progress.start()
            
            try:
                result = test_func()
                progress.stop()
                
                if result['available']:
                    print(f"    ✅ {algo_name}: {Colors.GREEN}{result['version']}{Colors.END}")
                    available_algorithms.append(algo_name)
                else:
                    print(f"    ❌ {algo_name}: {Colors.RED}{result['error']}{Colors.END}")
                    unavailable_algorithms.append(algo_name)
                    
            except Exception as e:
                progress.stop()
                print(f"    💥 {algo_name}: {Colors.RED}测试异常 - {str(e)}{Colors.END}")
                unavailable_algorithms.append(algo_name)
        
        # 整体评估
        if len(available_algorithms) >= 4:  # 至少需要核心算法
            self._record_check("识别算法", True, f"{len(available_algorithms)}/{len(algorithms)} 个算法可用")
        elif len(available_algorithms) >= 2:
            self._record_check("识别算法", True, f"{len(available_algorithms)}/{len(algorithms)} 个算法可用 (基本功能正常)", warning=True)
        else:
            self._record_check("识别算法", False, f"仅 {len(available_algorithms)}/{len(algorithms)} 个算法可用")
    
    def _test_yolo_import(self):
        """测试YOLO导入"""
        try:
            from ultralytics import YOLO
            import ultralytics
            
            # 测试模型加载
            model_path = self.project_root / "src" / "config" / "yolov8" / "best.pt"
            if model_path.exists():
                model_size = self._format_file_size(model_path.stat().st_size)
                return {
                    'available': True,
                    'version': f"v{ultralytics.__version__}, 模型: {model_size}"
                }
            else:
                return {
                    'available': False,
                    'error': "模型文件不存在"
                }
        except ImportError as e:
            return {'available': False, 'error': f"导入失败: {str(e)}"}
    
    def _test_easyocr_import(self):
        """测试EasyOCR导入"""
        try:
            import easyocr
            return {
                'available': True,
                'version': f"v{easyocr.__version__}"
            }
        except ImportError as e:
            return {'available': False, 'error': f"导入失败: {str(e)}"}
        except AttributeError:
            return {
                'available': True,
                'version': "已安装 (版本未知)"
            }
    
    def _test_paddleocr_import(self):
        """测试PaddleOCR导入"""
        try:
            import paddleocr
            return {
                'available': True,
                'version': "已安装"
            }
        except ImportError as e:
            return {'available': False, 'error': f"导入失败: {str(e)}"}
    
    def _test_opencv_import(self):
        """测试OpenCV导入"""
        try:
            import cv2
            return {
                'available': True,
                'version': f"v{cv2.__version__}"
            }
        except ImportError as e:
            return {'available': False, 'error': f"导入失败: {str(e)}"}
    
    def _test_pil_import(self):
        """测试PIL导入"""
        try:
            from PIL import Image, __version__
            return {
                'available': True,
                'version': f"v{__version__}"
            }
        except ImportError as e:
            return {'available': False, 'error': f"导入失败: {str(e)}"}
    
    def _test_websocket_import(self):
        """测试WebSocket导入"""
        try:
            import websockets
            return {
                'available': True,
                'version': f"v{websockets.__version__}"
            }
        except ImportError as e:
            return {'available': False, 'error': f"导入失败: {str(e)}"}
    
    def _test_camera_connections(self):
        """测试摄像头连接 - 调用实际模块"""
        try:
            # 导入实际的拍照控制器和配置管理器
            try:
                from src.processors.photo_controller import integrated_photo_controller, test_camera_connection
                from src.core.config_manager import get_camera_by_id
                controller_available = True
            except ImportError as e:
                print(f"    ❌ 无法导入拍照控制器: {Colors.RED}{str(e)}{Colors.END}")
                self._record_check("摄像头连接", False, "拍照控制器模块不可用")
                return
            
            cameras_result = get_enabled_cameras()
            
            if cameras_result['status'] != 'success':
                print(f"    ❌ 获取摄像头列表失败: {Colors.RED}{cameras_result['message']}{Colors.END}")
                return
            
            cameras = cameras_result['data']['cameras']
            
            if not cameras:
                print(f"    ⚠️  没有启用的摄像头可测试")
                return
            
            print(f"    🔌 测试 {len(cameras)} 个摄像头连接 (使用实际模块):")
            
            successful_connections = 0
            failed_connections = 0
            connection_details = []
            
            for camera in cameras:
                camera_id = camera['id']
                camera_name = camera.get('name', f'摄像头{camera_id}')
                ip = camera.get('ip', '')
                
                print(f"      🔍 {camera_name} ({camera_id}) - {ip}")
                
                # Step 1: 网络连通性测试
                print(f"        📡 网络测试...", end=' ')
                network_result = self._test_network_connectivity(ip)
                
                if network_result['success']:
                    print(f"{Colors.GREEN}✅ 连通{Colors.END}")
                else:
                    print(f"{Colors.RED}❌ {network_result['error']}{Colors.END}")
                    failed_connections += 1
                    connection_details.append({
                        'camera_id': camera_id,
                        'camera_name': camera_name,
                        'network': False,
                        'rtsp': False,
                        'error': f"网络不通: {network_result['error']}"
                    })
                    continue
                
                # Step 2: 获取实际配置 (使用与拍照程序相同的方法)
                print(f"        📋 获取配置...", end=' ')
                try:
                    config_result = get_camera_by_id(camera_id)
                    if config_result['status'] != 'success':
                        print(f"{Colors.RED}❌ 配置错误{Colors.END}")
                        failed_connections += 1
                        connection_details.append({
                            'camera_id': camera_id,
                            'camera_name': camera_name,
                            'network': True,
                            'rtsp': False,
                            'error': f"配置获取失败: {config_result['message']}"
                        })
                        continue
                    
                    camera_config = config_result['data']['camera']
                    print(f"{Colors.GREEN}✅ 成功{Colors.END}")
                    
                    # Step 3: 构建实际RTSP URL (使用实际模块的方法)
                    print(f"        🔗 构建RTSP URL...", end=' ')
                    try:
                        rtsp_url = integrated_photo_controller._build_rtsp_url(camera_config)
                        print(f"{Colors.GREEN}✅ {rtsp_url}{Colors.END}")
                    except Exception as e:
                        print(f"{Colors.RED}❌ URL构建失败: {str(e)}{Colors.END}")
                        failed_connections += 1
                        connection_details.append({
                            'camera_id': camera_id,
                            'camera_name': camera_name,
                            'network': True,
                            'rtsp': False,
                            'error': f"URL构建失败: {str(e)}"
                        })
                        continue
                        
                except Exception as e:
                    print(f"{Colors.RED}❌ 异常: {str(e)}{Colors.END}")
                    failed_connections += 1
                    connection_details.append({
                        'camera_id': camera_id,
                        'camera_name': camera_name,
                        'network': True,
                        'rtsp': False,
                        'error': f"配置处理异常: {str(e)}"
                    })
                    continue
                
                # Step 4: 使用实际模块的连接测试
                print(f"        🎥 RTSP连接测试...", end=' ')
                try:
                    connection_result = test_camera_connection(camera_id)
                    
                    if connection_result['status'] == 'success':
                        print(f"{Colors.GREEN}✅ 连接正常{Colors.END}")
                        successful_connections += 1
                        connection_details.append({
                            'camera_id': camera_id,
                            'camera_name': camera_name,
                            'network': True,
                            'rtsp': True,
                            'rtsp_url': rtsp_url,
                            'success': True
                        })
                    else:
                        print(f"{Colors.YELLOW}⚠️  连接失败: {connection_result['message']}{Colors.END}")
                        failed_connections += 1
                        connection_details.append({
                            'camera_id': camera_id,
                            'camera_name': camera_name,
                            'network': True,
                            'rtsp': False,
                            'rtsp_url': rtsp_url,
                            'error': connection_result['message']
                        })
                        
                except Exception as e:
                    print(f"{Colors.RED}❌ 测试异常: {str(e)}{Colors.END}")
                    failed_connections += 1
                    connection_details.append({
                        'camera_id': camera_id,
                        'camera_name': camera_name,
                        'network': True,
                        'rtsp': False,
                        'error': f"连接测试异常: {str(e)}"
                    })
            
            # 显示详细连接信息
            if connection_details:
                print(f"\n    📋 连接详情:")
                for detail in connection_details:
                    status_icon = "✅" if detail.get('success', False) else "❌"
                    print(f"      {status_icon} {detail['camera_name']} ({detail['camera_id']})")
                    if detail.get('rtsp_url'):
                        print(f"        🔗 RTSP: {detail['rtsp_url']}")
                    if detail.get('error'):
                        print(f"        ❌ 错误: {Colors.RED}{detail['error']}{Colors.END}")
            
            # 记录整体结果
            if failed_connections == 0:
                self._record_check("摄像头连接", True, f"所有 {successful_connections} 个摄像头连接正常")
            elif successful_connections > 0:
                self._record_check("摄像头连接", True, f"{successful_connections}/{len(cameras)} 个摄像头连接正常", warning=True)
            else:
                self._record_check("摄像头连接", False, f"所有摄像头连接失败")
                
        except Exception as e:
            self._record_check("摄像头连接", False, f"测试异常: {str(e)}")
    
    def _test_network_connectivity(self, ip: str, timeout: int = 3):
        """测试网络连通性"""
        try:
            import platform
            system = platform.system().lower()
            
            if system == "windows":
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), ip]
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), ip]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
            
            if result.returncode == 0:
                return {'success': True}
            else:
                return {'success': False, 'error': '无响应'}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '超时'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_rtsp_connection(self, camera: dict):
        """测试RTSP连接 - 已弃用，改用实际模块测试"""
        # 此方法已被 _test_camera_connections 中的实际模块调用替代
        return {'success': False, 'error': '已改用实际模块测试'}
    
    def _test_actual_photo_capture(self):
        """可选：测试实际拍照功能"""
        try:
            from src.processors.photo_controller import take_photo_by_id
            from src.core.config_manager import get_camera_by_id
            
            print(f"    📸 实际拍照测试 (可选):")
            
            cameras_result = get_enabled_cameras()
            if cameras_result['status'] != 'success':
                return
            
            cameras = cameras_result['data']['cameras']
            if not cameras:
                return
            
            # 只测试第一个摄像头，避免过度占用资源
            test_camera = cameras[0]
            camera_id = test_camera['id']
            camera_name = test_camera.get('name', f'摄像头{camera_id}')
            
            print(f"      🎯 测试摄像头: {camera_name} ({camera_id})")
            print(f"        📸 执行拍照...", end=' ')
            
            # 执行实际拍照
            photo_result = take_photo_by_id(camera_id)
            
            if photo_result['status'] == 'success':
                photo_data = photo_result['data']
                file_size = photo_data.get('file_size', 0)
                filename = photo_data.get('filename', '')
                duration = photo_data.get('duration', 0)
                
                print(f"{Colors.GREEN}✅ 成功{Colors.END}")
                print(f"        📄 文件: {filename}")
                print(f"        📊 大小: {self._format_file_size(file_size)}")
                print(f"        ⏱️  耗时: {duration:.2f}秒")
                
                # 检查文件质量
                if file_size > 50 * 1024:  # 大于50KB认为正常
                    print(f"        ✅ 文件大小正常")
                    self._record_check("实际拍照测试", True, f"拍照成功，文件大小: {self._format_file_size(file_size)}")
                else:
                    print(f"        ⚠️  文件偏小，可能有问题")
                    self._record_check("实际拍照测试", True, f"拍照成功但文件偏小: {self._format_file_size(file_size)}", warning=True)
                    
            else:
                print(f"{Colors.RED}❌ 失败: {photo_result['message']}{Colors.END}")
                self._record_check("实际拍照测试", False, f"拍照失败: {photo_result['message']}")
                
        except ImportError as e:
            print(f"      ❌ 无法导入拍照模块: {str(e)}")
            self._record_check("实际拍照测试", False, "拍照模块不可用")
        except Exception as e:
            print(f"      ❌ 拍照测试异常: {str(e)}")
            self._record_check("实际拍照测试", False, f"拍照测试异常: {str(e)}")
    
    def _test_system_performance(self):
        """测试系统性能"""
        import psutil
        
        print(f"    📊 系统性能指标:")
        
        # CPU信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        print(f"      🖥️  CPU使用率: {Colors.CYAN}{cpu_percent:.1f}%{Colors.END}")
        print(f"      🔢 CPU核心数: {Colors.CYAN}{cpu_count}{Colors.END}")
        if cpu_freq:
            print(f"      ⚡ CPU频率: {Colors.CYAN}{cpu_freq.current:.0f}MHz{Colors.END}")
        
        # 内存信息
        memory = psutil.virtual_memory()
        memory_gb = memory.total / 1024 / 1024 / 1024
        memory_used_percent = memory.percent
        
        print(f"      💾 内存总量: {Colors.CYAN}{memory_gb:.1f}GB{Colors.END}")
        print(f"      📈 内存使用: {Colors.CYAN}{memory_used_percent:.1f}%{Colors.END}")
        
        # 磁盘信息
        disk = psutil.disk_usage(str(self.project_root))
        disk_total_gb = disk.total / 1024 / 1024 / 1024
        disk_used_percent = (disk.used / disk.total) * 100
        
        print(f"      💿 磁盘总量: {Colors.CYAN}{disk_total_gb:.1f}GB{Colors.END}")
        print(f"      📊 磁盘使用: {Colors.CYAN}{disk_used_percent:.1f}%{Colors.END}")
        
        # 性能评估
        performance_score = 0
        issues = []
        
        if cpu_percent < 80:
            performance_score += 25
        else:
            issues.append("CPU使用率过高")
        
        if memory_used_percent < 80:
            performance_score += 25
        else:
            issues.append("内存使用率过高")
        
        if disk_used_percent < 90:
            performance_score += 25
        else:
            issues.append("磁盘空间不足")
        
        if memory_gb >= 4:
            performance_score += 25
        else:
            issues.append("内存容量较小")
        
        if performance_score >= 75:
            self._record_check("系统性能", True, f"性能良好 (评分: {performance_score}/100)")
        elif performance_score >= 50:
            self._record_check("系统性能", True, f"性能一般 (评分: {performance_score}/100): {', '.join(issues)}", warning=True)
        else:
            self._record_check("系统性能", False, f"性能较差 (评分: {performance_score}/100): {', '.join(issues)}")
    
    def _check_push_config(self):
        """检查推送配置"""
        try:
            from config_loader import load_push_config
            
            push_result = load_push_config()
            
            if push_result['status'] != 'success':
                self._record_check("推送配置", False, push_result['message'])
                return
            
            push_config = push_result['data']
            ws_config = push_config.get('websocket', {})
            
            print(f"    📡 WebSocket配置:")
            
            # 检查WebSocket配置
            enabled = ws_config.get('enabled', False)
            server_url = ws_config.get('server_url', '')
            client_id = ws_config.get('client_id', '')
            
            status_color = Colors.GREEN if enabled else Colors.YELLOW
            print(f"      🔄 状态: {status_color}{'启用' if enabled else '禁用'}{Colors.END}")
            
            if enabled:
                print(f"      🌐 服务器: {Colors.CYAN}{server_url}{Colors.END}")
                print(f"      🆔 客户端ID: {Colors.CYAN}{client_id}{Colors.END}")
                
                # 检查URL格式
                if server_url.startswith(('ws://', 'wss://')) and client_id:
                    self._record_check("推送配置", True, "WebSocket配置正确")
                else:
                    issues = []
                    if not server_url.startswith(('ws://', 'wss://')):
                        issues.append("服务器URL格式错误")
                    if not client_id:
                        issues.append("客户端ID为空")
                    
                    self._record_check("推送配置", False, f"配置问题: {', '.join(issues)}")
            else:
                self._record_check("推送配置", True, "WebSocket推送已禁用", warning=True)
                
        except Exception as e:
            self._record_check("推送配置", False, f"检查异常: {str(e)}")
    
    def _record_check(self, check_name: str, success: bool, message: str, warning: bool = False):
        """记录检查结果"""
        self.total_checks += 1
        
        if success and not warning:
            self.passed_checks += 1
            status = 'PASS'
            icon = '✅'
            color = Colors.GREEN
        elif success and warning:
            self.warning_checks += 1
            status = 'WARN'
            icon = '⚠️'
            color = Colors.YELLOW
        else:
            self.failed_checks += 1
            status = 'FAIL'
            icon = '❌'
            color = Colors.RED
        
        self.check_results[check_name] = {
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        # 实时显示结果
        print(f"  {icon} {Colors.BOLD}{check_name}{Colors.END}: {color}{message}{Colors.END}")
    
    def _generate_detailed_report(self):
        """生成详细报告"""
        self.print_section_header("检查报告汇总", "📋")
        
        # 基本统计
        total_time = self.stats['duration']
        success_rate = (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0
        
        print(f"  ⏱️  检查耗时: {Colors.CYAN}{total_time:.2f} 秒{Colors.END}")
        print(f"  📊 检查项目: {Colors.CYAN}{self.total_checks} 项{Colors.END}")
        print(f"  ✅ 通过: {Colors.GREEN}{self.passed_checks} 项{Colors.END}")
        print(f"  ⚠️  警告: {Colors.YELLOW}{self.warning_checks} 项{Colors.END}")
        print(f"  ❌ 失败: {Colors.RED}{self.failed_checks} 项{Colors.END}")
        print(f"  📈 通过率: {Colors.CYAN}{success_rate:.1f}%{Colors.END}")
        
        # 整体状态
        print(f"\n  🎯 {Colors.BOLD}整体评估:{Colors.END}")
        
        if self.failed_checks == 0:
            if self.warning_checks == 0:
                print(f"  {Colors.BG_GREEN}{Colors.WHITE} 🎉 完美！所有检查项目都通过了！ {Colors.END}")
                overall_status = "EXCELLENT"
            else:
                print(f"  {Colors.BG_YELLOW}{Colors.WHITE} 👍 良好！系统基本正常，有少量警告项目 {Colors.END}")
                overall_status = "GOOD"
        elif self.failed_checks <= 2:
            print(f"  {Colors.BG_YELLOW}{Colors.WHITE} ⚠️  一般！发现少量问题，建议修复 {Colors.END}")
            overall_status = "FAIR"
        else:
            print(f"  {Colors.BG_RED}{Colors.WHITE} 🚨 需要修复！发现多个严重问题 {Colors.END}")
            overall_status = "POOR"
        
        # 显示失败和警告项目
        if self.failed_checks > 0:
            print(f"\n  🔥 {Colors.BOLD}{Colors.RED}需要修复的问题:{Colors.END}")
            for check_name, result in self.check_results.items():
                if result['status'] == 'FAIL':
                    print(f"    ❌ {check_name}: {result['message']}")
        
        if self.warning_checks > 0:
            print(f"\n  ⚠️  {Colors.BOLD}{Colors.YELLOW}警告项目:{Colors.END}")
            for check_name, result in self.check_results.items():
                if result['status'] == 'WARN':
                    print(f"    ⚠️  {check_name}: {result['message']}")
        
        # 建议
        print(f"\n  💡 {Colors.BOLD}建议:{Colors.END}")
        if overall_status == "EXCELLENT":
            print(f"    🚀 系统状态完美，可以开始使用扑克识别功能！")
        elif overall_status == "GOOD":
            print(f"    👌 系统基本就绪，可以开始测试，注意警告项目")
        elif overall_status == "FAIR":
            print(f"    🔧 建议先修复标记的问题，然后重新检查")
        else:
            print(f"    🆘 请按照错误提示逐项修复问题后重新检查")
        
        # 底部分隔线
        print(f"\n{Colors.CYAN}{'=' * 80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.WHITE}🎯 检查完成 - {datetime.now().strftime('%H:%M:%S')}{Colors.END}")
        print(f"{Colors.CYAN}{'=' * 80}{Colors.END}\n")
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='优化的系统配置检查工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Colors.CYAN}使用示例:{Colors.END}
  python check_config.py                    # 基础配置检查
  python check_config.py --test-cameras    # 包含摄像头连接测试(使用实际模块)
  python check_config.py --test-algorithms # 包含算法依赖测试
  python check_config.py --test-photo      # 包含实际拍照测试
  python check_config.py --full            # 完整检查(包含所有测试)
  python check_config.py --performance     # 包含性能测试
        """
    )
    
    parser.add_argument('--test-cameras', action='store_true',
                       help='测试摄像头连接(使用实际模块,需要网络)')
    parser.add_argument('--test-algorithms', action='store_true',
                       help='测试识别算法库')
    parser.add_argument('--test-photo', action='store_true',
                       help='测试实际拍照功能(会占用摄像头)')
    parser.add_argument('--performance', action='store_true',
                       help='包含系统性能测试')
    parser.add_argument('--full', action='store_true',
                       help='完整检查(包含所有可选测试)')
    parser.add_argument('--no-color', action='store_true',
                       help='禁用彩色输出')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析参数
        args = parse_arguments()
        
        # 禁用颜色输出
        if args.no_color:
            for attr in dir(Colors):
                if not attr.startswith('_'):
                    setattr(Colors, attr, '')
        
        # 创建检查器
        checker = OptimizedConfigChecker()
        
        # 确定测试范围
        test_cameras = args.test_cameras or args.full
        test_algorithms = args.test_algorithms or args.full
        test_performance = args.performance or args.full
        test_photo = args.test_photo or args.full
        
        # 运行检查
        success = checker.run_all_checks(
            test_cameras=test_cameras,
            test_algorithms=test_algorithms,
            test_performance=test_performance,
            test_photo=test_photo
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  检查被用户中断{Colors.END}")
        return 1
    except Exception as e:
        print(f"{Colors.RED}❌ 程序异常: {e}{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())