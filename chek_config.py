#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的配置检查工具 - 修复显示问题，更准确的状态判断
功能:
1. 修复摄像头测试结果显示问题
2. 更准确的整体评估逻辑
3. 优化的错误统计和报告
4. 更清晰的成功/失败判断
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

class ImprovedConfigChecker:
    """改进的配置检查器"""
    
    def __init__(self):
        """初始化配置检查器"""
        self.check_results = {}
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = 0
        self.warning_checks = 0
        self.critical_checks = 0  # 关键检查项数量
        self.critical_passed = 0  # 关键检查项通过数量
        
        # 检查统计
        self.stats = {
            'start_time': datetime.now(),
            'end_time': None,
            'duration': 0,
            'system_info': {},
            'camera_test_results': []
        }
        
        self.project_root = setup_project_paths()
        
        # 定义关键检查项（这些项目失败会影响系统正常使用）
        self.critical_check_names = [
            '配置文件验证',
            '摄像头配置',
            '关键文件',
            '目录结构'
        ]
        
    def print_header(self):
        """打印美观的标题"""
        print(f"\n{Colors.CYAN}{'=' * 80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.WHITE}🔍 扑克识别系统 - 改进配置检查工具 v2.1{Colors.END}")
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
            
            # 5. 摄像头连接测试
            if test_cameras:
                self.print_section_header("摄像头连接测试", "🔌")
                self._test_camera_connections_improved()
            
            # 6. 实际拍照测试
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
            
            # 生成改进的检查报告
            self._generate_improved_report()
            
            # 改进的成功判断逻辑
            return self._is_system_ready()
        
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}⚠️  检查被用户中断{Colors.END}")
            return False
        except Exception as e:
            print(f"\n{Colors.RED}💥 检查过程异常: {e}{Colors.END}")
            return False
    
    def _test_camera_connections_improved(self):
        """改进的摄像头连接测试 - 更准确的结果统计"""
        try:
            # 导入实际的拍照控制器和配置管理器
            try:
                from src.processors.photo_controller import test_camera_connection
                from src.core.config_manager import get_camera_by_id
                controller_available = True
            except ImportError as e:
                print(f"    ❌ 无法导入拍照控制器: {Colors.RED}{str(e)}{Colors.END}")
                self._record_check("摄像头连接", False, "拍照控制器模块不可用", critical=True)
                return
            
            cameras_result = get_enabled_cameras()
            
            if cameras_result['status'] != 'success':
                print(f"    ❌ 获取摄像头列表失败: {Colors.RED}{cameras_result['message']}{Colors.END}")
                self._record_check("摄像头连接", False, f"获取摄像头列表失败: {cameras_result['message']}", critical=True)
                return
            
            cameras = cameras_result['data']['cameras']
            
            if not cameras:
                print(f"    ⚠️  没有启用的摄像头可测试")
                self._record_check("摄像头连接", False, "没有启用的摄像头", critical=True)
                return
            
            print(f"    🔌 测试 {len(cameras)} 个摄像头连接:")
            
            successful_connections = 0
            failed_connections = 0
            connection_details = []
            
            for camera in cameras:
                camera_id = camera['id']
                camera_name = camera.get('name', f'摄像头{camera_id}')
                ip = camera.get('ip', '')
                
                print(f"      🔍 {camera_name} ({camera_id}) - {ip}")
                
                # 使用实际模块的连接测试
                print(f"        📡 连接测试...", end=' ')
                try:
                    connection_result = test_camera_connection(camera_id)
                    
                    if connection_result['status'] == 'success':
                        print(f"{Colors.GREEN}✅ 连接正常{Colors.END}")
                        successful_connections += 1
                        connection_details.append({
                            'camera_id': camera_id,
                            'camera_name': camera_name,
                            'success': True,
                            'ip': ip
                        })
                    else:
                        print(f"{Colors.RED}❌ 连接失败: {connection_result['message']}{Colors.END}")
                        failed_connections += 1
                        connection_details.append({
                            'camera_id': camera_id,
                            'camera_name': camera_name,
                            'success': False,
                            'error': connection_result['message'],
                            'ip': ip
                        })
                        
                except Exception as e:
                    print(f"{Colors.RED}❌ 测试异常: {str(e)}{Colors.END}")
                    failed_connections += 1
                    connection_details.append({
                        'camera_id': camera_id,
                        'camera_name': camera_name,
                        'success': False,
                        'error': f"测试异常: {str(e)}",
                        'ip': ip
                    })
            
            # 保存测试结果到统计信息
            self.stats['camera_test_results'] = connection_details
            
            # 显示汇总结果
            print(f"\n    📊 连接测试汇总:")
            print(f"      ✅ 成功: {Colors.GREEN}{successful_connections}{Colors.END}")
            print(f"      ❌ 失败: {Colors.RED}{failed_connections}{Colors.END}")
            print(f"      📈 成功率: {Colors.CYAN}{(successful_connections/len(cameras)*100):.1f}%{Colors.END}")
            
            # 改进的结果记录逻辑
            if successful_connections == len(cameras):
                # 所有摄像头都连接成功
                self._record_check("摄像头连接", True, f"所有 {successful_connections} 个摄像头连接正常")
            elif successful_connections > 0:
                # 部分摄像头连接成功
                success_rate = successful_connections / len(cameras) * 100
                if success_rate >= 50:
                    self._record_check("摄像头连接", True, 
                                     f"{successful_connections}/{len(cameras)} 个摄像头连接正常 ({success_rate:.1f}%)", 
                                     warning=True)
                else:
                    self._record_check("摄像头连接", False, 
                                     f"仅 {successful_connections}/{len(cameras)} 个摄像头连接正常 ({success_rate:.1f}%)")
            else:
                # 所有摄像头都连接失败
                self._record_check("摄像头连接", False, "所有摄像头连接失败")
                
        except Exception as e:
            self._record_check("摄像头连接", False, f"测试异常: {str(e)}")
    
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
            self._record_check("Python版本", False, f"Python {sys_info['python_version']} (建议3.8+)", critical=True)
    
    def _check_basic_config(self):
        """检查基础配置"""
        # 配置文件验证
        try:
            validation_result = validate_all_configs()
            
            if validation_result['status'] == 'success':
                validation_data = validation_result['data']
                
                if validation_data['overall_valid']:
                    self._record_check("配置文件验证", True, "所有配置文件格式正确", critical=True)
                    
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
                    self._record_check("配置文件验证", False, f"配置文件错误: {', '.join(invalid_configs)}", critical=True)
            else:
                self._record_check("配置文件验证", False, validation_result['message'], critical=True)
                
        except Exception as e:
            self._record_check("配置文件验证", False, f"验证异常: {str(e)}", critical=True)
        
        # 目录结构检查
        self._check_directory_structure()
        
        # 关键文件检查
        self._check_critical_files()
    
    def _check_directory_structure(self):
        """检查目录结构"""
        required_dirs = {
            'src/config': self.project_root / "src" / "config",
            'image': self.project_root / "image",
            'result': self.project_root / "result"
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
                print(f"    ✅ {dir_name}: {Colors.GREEN}存在{Colors.END}")
        
        if created_dirs:
            self._record_check("目录结构", True, f"结构完整，已创建 {len(created_dirs)} 个缺失目录", critical=True)
        elif missing_dirs:
            self._record_check("目录结构", False, f"缺少目录: {', '.join(missing_dirs)}", critical=True)
        else:
            self._record_check("目录结构", True, f"所有 {len(existing_dirs)} 个目录完整", critical=True)
    
    def _check_critical_files(self):
        """检查关键文件"""
        critical_files = {
            '摄像头配置': self.project_root / "src" / "config" / "camera.json",
            '主程序': self.project_root / "main.py",
            '标记程序': self.project_root / "biaoji.py",
            '识别程序': self.project_root / "see.py"
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
            else:
                print(f"      ❌ {file_name}: {Colors.RED}不存在{Colors.END}")
                missing_files.append(file_name)
        
        if missing_files:
            self._record_check("关键文件", False, f"缺少文件: {', '.join(missing_files)}", critical=True)
        else:
            self._record_check("关键文件", True, f"所有 {len(existing_files)} 个关键文件完整", critical=True)
    
    def _check_camera_config(self):
        """检查摄像头配置"""
        try:
            cameras_result = get_enabled_cameras()
            
            if cameras_result['status'] != 'success':
                self._record_check("摄像头配置", False, cameras_result['message'], critical=True)
                return
            
            cameras = cameras_result['data']['cameras']
            total_cameras = cameras_result['data']['all_count']
            enabled_cameras = len(cameras)
            
            print(f"    📊 摄像头统计:")
            print(f"      📷 总数量: {Colors.CYAN}{total_cameras}{Colors.END}")
            print(f"      ✅ 已启用: {Colors.GREEN}{enabled_cameras}{Colors.END}")
            print(f"      ❌ 已禁用: {Colors.YELLOW}{total_cameras - enabled_cameras}{Colors.END}")
            
            if not cameras:
                self._record_check("摄像头配置", False, "没有启用的摄像头", critical=True)
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
                
                if missing_fields:
                    print(f"      ❌ {camera_name} ({camera_id}): {Colors.RED}缺少字段 {missing_fields}{Colors.END}")
                    invalid_cameras.append(camera_id)
                else:
                    ip = camera.get('ip', 'N/A')
                    port = camera.get('port', 554)
                    print(f"      ✅ {camera_name} ({camera_id}): {Colors.CYAN}{ip}:{port}{Colors.END}")
                    valid_cameras += 1
            
            if invalid_cameras:
                self._record_check("摄像头配置", False, f"配置错误的摄像头: {', '.join(invalid_cameras)}", critical=True)
            else:
                self._record_check("摄像头配置", True, f"{valid_cameras} 个摄像头配置正确", critical=True)
                
        except Exception as e:
            self._record_check("摄像头配置", False, f"检查异常: {str(e)}", critical=True)
    
    def _test_recognition_algorithms(self):
        """测试识别算法"""
        algorithms = {
            'YOLOv8 (ultralytics)': self._test_yolo_import,
            'OpenCV': self._test_opencv_import,
            'PIL/Pillow': self._test_pil_import
        }
        
        available_algorithms = []
        unavailable_algorithms = []
        
        for algo_name, test_func in algorithms.items():
            try:
                result = test_func()
                
                if result['available']:
                    print(f"    ✅ {algo_name}: {Colors.GREEN}{result['version']}{Colors.END}")
                    available_algorithms.append(algo_name)
                else:
                    print(f"    ❌ {algo_name}: {Colors.RED}{result['error']}{Colors.END}")
                    unavailable_algorithms.append(algo_name)
                    
            except Exception as e:
                print(f"    💥 {algo_name}: {Colors.RED}测试异常 - {str(e)}{Colors.END}")
                unavailable_algorithms.append(algo_name)
        
        # 整体评估
        if len(available_algorithms) >= 2:  # 至少需要基本算法
            self._record_check("识别算法", True, f"{len(available_algorithms)}/{len(algorithms)} 个算法可用")
        else:
            self._record_check("识别算法", False, f"仅 {len(available_algorithms)}/{len(algorithms)} 个算法可用")
    
    def _test_yolo_import(self):
        """测试YOLO导入"""
        try:
            from ultralytics import YOLO
            import ultralytics
            return {
                'available': True,
                'version': f"v{ultralytics.__version__}"
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
    
    def _test_actual_photo_capture(self):
        """测试实际拍照功能"""
        try:
            from src.processors.photo_controller import take_photo_by_id
            
            print(f"    📸 实际拍照测试:")
            
            cameras_result = get_enabled_cameras()
            if cameras_result['status'] != 'success':
                self._record_check("实际拍照测试", False, "无法获取摄像头列表")
                return
            
            cameras = cameras_result['data']['cameras']
            if not cameras:
                self._record_check("实际拍照测试", False, "没有可用摄像头")
                return
            
            # 测试第一个连接成功的摄像头
            test_camera = None
            for camera_detail in self.stats.get('camera_test_results', []):
                if camera_detail.get('success', False):
                    camera_id = camera_detail['camera_id']
                    test_camera = next((c for c in cameras if c['id'] == camera_id), None)
                    break
            
            if not test_camera:
                test_camera = cameras[0]  # 如果没有连接测试结果，使用第一个
            
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
                    self._record_check("实际拍照测试", True, f"拍照成功，文件大小: {self._format_file_size(file_size)}")
                else:
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
        try:
            import psutil
            
            print(f"    📊 系统性能指标:")
            
            # CPU信息
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            print(f"      🖥️  CPU使用率: {Colors.CYAN}{cpu_percent:.1f}%{Colors.END}")
            print(f"      🔢 CPU核心数: {Colors.CYAN}{cpu_count}{Colors.END}")
            
            # 内存信息
            memory = psutil.virtual_memory()
            memory_gb = memory.total / 1024 / 1024 / 1024
            memory_used_percent = memory.percent
            
            print(f"      💾 内存总量: {Colors.CYAN}{memory_gb:.1f}GB{Colors.END}")
            print(f"      📈 内存使用: {Colors.CYAN}{memory_used_percent:.1f}%{Colors.END}")
            
            # 性能评估
            issues = []
            
            if cpu_percent > 80:
                issues.append("CPU使用率过高")
            
            if memory_used_percent > 80:
                issues.append("内存使用率过高")
            
            if memory_gb < 4:
                issues.append("内存容量较小")
            
            if not issues:
                self._record_check("系统性能", True, "性能良好")
            else:
                self._record_check("系统性能", True, f"性能一般: {', '.join(issues)}", warning=True)
                
        except ImportError:
            self._record_check("系统性能", False, "psutil库不可用")
        except Exception as e:
            self._record_check("系统性能", False, f"性能测试异常: {str(e)}")
    
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
    
    def _record_check(self, check_name: str, success: bool, message: str, warning: bool = False, critical: bool = False):
        """记录检查结果"""
        self.total_checks += 1
        
        # 统计关键检查项
        if critical or check_name in self.critical_check_names:
            self.critical_checks += 1
            if success and not warning:
                self.critical_passed += 1
        
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
            'timestamp': datetime.now().isoformat(),
            'critical': critical or check_name in self.critical_check_names
        }
        
        # 实时显示结果
        print(f"  {icon} {Colors.BOLD}{check_name}{Colors.END}: {color}{message}{Colors.END}")
    
    def _is_system_ready(self) -> bool:
        """改进的系统就绪判断逻辑"""
        # 关键检查项必须全部通过
        if self.critical_checks > 0 and self.critical_passed < self.critical_checks:
            return False
        
        # 如果没有失败项，系统就绪
        if self.failed_checks == 0:
            return True
        
        # 如果失败项很少且不涉及关键功能，也认为基本就绪
        if self.failed_checks <= 1 and self.passed_checks >= 5:
            return True
        
        return False
    
    def _generate_improved_report(self):
        """生成改进的检查报告"""
        self.print_section_header("检查报告汇总", "📋")
        
        # 基本统计
        total_time = self.stats['duration']
        success_rate = (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0
        critical_success_rate = (self.critical_passed / self.critical_checks * 100) if self.critical_checks > 0 else 100
        
        print(f"  ⏱️  检查耗时: {Colors.CYAN}{total_time:.2f} 秒{Colors.END}")
        print(f"  📊 检查项目: {Colors.CYAN}{self.total_checks} 项{Colors.END}")
        print(f"  ✅ 通过: {Colors.GREEN}{self.passed_checks} 项{Colors.END}")
        print(f"  ⚠️  警告: {Colors.YELLOW}{self.warning_checks} 项{Colors.END}")
        print(f"  ❌ 失败: {Colors.RED}{self.failed_checks} 项{Colors.END}")
        print(f"  📈 通过率: {Colors.CYAN}{success_rate:.1f}%{Colors.END}")
        print(f"  🔑 关键项通过率: {Colors.CYAN}{critical_success_rate:.1f}%{Colors.END} ({self.critical_passed}/{self.critical_checks})")
        
        # 摄像头测试详情
        camera_results = self.stats.get('camera_test_results', [])
        if camera_results:
            successful_cameras = sum(1 for r in camera_results if r.get('success', False))
            total_cameras = len(camera_results)
            print(f"  📷 摄像头连接: {Colors.CYAN}{successful_cameras}/{total_cameras} 成功{Colors.END}")
        
        # 改进的整体评估
        system_ready = self._is_system_ready()
        
        print(f"\n  🎯 {Colors.BOLD}整体评估:{Colors.END}")
        
        if system_ready:
            if self.failed_checks == 0 and self.warning_checks == 0:
                print(f"  {Colors.BG_GREEN}{Colors.WHITE} 🎉 完美！系统完全就绪，可以开始使用！ {Colors.END}")
                overall_status = "READY"
            elif self.failed_checks == 0:
                print(f"  {Colors.BG_GREEN}{Colors.WHITE} 👍 就绪！系统基本正常，可以开始使用 {Colors.END}")
                overall_status = "READY"
            else:
                print(f"  {Colors.BG_YELLOW}{Colors.WHITE} ✅ 基本就绪！有少量非关键问题，但不影响使用 {Colors.END}")
                overall_status = "MOSTLY_READY"
        else:
            print(f"  {Colors.BG_RED}{Colors.WHITE} 🚨 未就绪！请修复关键问题后再使用 {Colors.END}")
            overall_status = "NOT_READY"
        
        # 显示问题和建议
        if self.failed_checks > 0:
            print(f"\n  🔥 {Colors.BOLD}{Colors.RED}需要修复的问题:{Colors.END}")
            for check_name, result in self.check_results.items():
                if result['status'] == 'FAIL':
                    critical_mark = " 🔑" if result.get('critical', False) else ""
                    print(f"    ❌ {check_name}{critical_mark}: {result['message']}")
        
        if self.warning_checks > 0:
            print(f"\n  ⚠️  {Colors.BOLD}{Colors.YELLOW}警告项目:{Colors.END}")
            for check_name, result in self.check_results.items():
                if result['status'] == 'WARN':
                    print(f"    ⚠️  {check_name}: {result['message']}")
        
        # 建议
        print(f"\n  💡 {Colors.BOLD}使用建议:{Colors.END}")
        if overall_status == "READY":
            print(f"    🚀 系统已就绪，建议按以下顺序开始使用:")
            print(f"       1️⃣  运行标记程序: python biaoji.py")
            print(f"       2️⃣  完成位置标记后，运行识别测试: python see.py")
            print(f"       3️⃣  测试正常后，可运行生产模式: python tui.py")
        elif overall_status == "MOSTLY_READY":
            print(f"    👌 系统基本可用，建议:")
            print(f"       1️⃣  可以开始测试基本功能")
            print(f"       2️⃣  关注标记的警告项目，有时间时修复")
        else:
            print(f"    🆘 请优先修复标记为 🔑 的关键问题")
            print(f"    🔧 修复完成后重新运行检查: python check_config.py")
        
        # 底部分隔线
        print(f"\n{Colors.CYAN}{'=' * 80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.WHITE}🎯 检查完成 - {datetime.now().strftime('%H:%M:%S')} - 系统状态: {overall_status}{Colors.END}")
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
        description='改进的系统配置检查工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Colors.CYAN}使用示例:{Colors.END}
  python improved_check_config.py                    # 基础配置检查
  python improved_check_config.py --test-cameras    # 包含摄像头连接测试
  python improved_check_config.py --test-algorithms # 包含算法依赖测试
  python improved_check_config.py --test-photo      # 包含实际拍照测试
  python improved_check_config.py --full            # 完整检查(包含所有测试)
        """
    )
    
    parser.add_argument('--test-cameras', action='store_true',
                       help='测试摄像头连接(使用实际模块)')
    parser.add_argument('--test-algorithms', action='store_true',
                       help='测试识别算法库')
    parser.add_argument('--test-photo', action='store_true',
                       help='测试实际拍照功能')
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
        checker = ImprovedConfigChecker()
        
        # 确定测试范围
        test_cameras = args.test_cameras or args.full
        test_algorithms = args.test_algorithms or args.full
        test_performance = args.performance or args.full
        test_photo = args.test_photo or args.full
        
        # 运行检查
        system_ready = checker.run_all_checks(
            test_cameras=test_cameras,
            test_algorithms=test_algorithms,
            test_performance=test_performance,
            test_photo=test_photo
        )
        
        return 0 if system_ready else 1
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  检查被用户中断{Colors.END}")
        return 1
    except Exception as e:
        print(f"{Colors.RED}❌ 程序异常: {e}{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())