#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置检查工具 - 检查所有配置文件的完整性和有效性
功能:
1. 检查配置文件是否存在
2. 验证配置格式和内容
3. 测试摄像头连接
4. 检查算法依赖
5. 生成配置报告
"""

import sys
import argparse
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

# 导入模块
from config_loader import validate_all_configs, get_config_summary, get_enabled_cameras
from src.core.utils import log_info, log_success, log_error, log_warning

class ConfigChecker:
    """配置检查器"""
    
    def __init__(self):
        """初始化配置检查器"""
        self.check_results = {}
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = 0
        
    def run_all_checks(self, test_cameras: bool = False, test_algorithms: bool = False) -> bool:
        """运行所有检查"""
        print("🔍 开始系统配置检查...")
        print("=" * 60)
        
        # 基础配置检查
        self._check_basic_config()
        
        # 摄像头配置检查
        self._check_camera_config()
        
        # 如果启用，测试摄像头连接
        if test_cameras:
            self._test_camera_connections()
        
        # 如果启用，测试识别算法
        if test_algorithms:
            self._test_recognition_algorithms()
        
        # 推送配置检查
        self._check_push_config()
        
        # 生成检查报告
        self._generate_report()
        
        return self.failed_checks == 0
    
    def _check_basic_config(self):
        """检查基础配置"""
        print("\n📋 检查基础配置...")
        
        self._run_check("配置文件验证", self._validate_config_files)
        self._run_check("目录结构检查", self._check_directory_structure)
        self._run_check("依赖模块检查", self._check_dependencies)
    
    def _check_camera_config(self):
        """检查摄像头配置"""
        print("\n📷 检查摄像头配置...")
        
        self._run_check("摄像头配置格式", self._validate_camera_format)
        self._run_check("摄像头网络配置", self._validate_camera_network)
        self._run_check("标记位置配置", self._validate_mark_positions)
    
    def _check_push_config(self):
        """检查推送配置"""
        print("\n📡 检查推送配置...")
        
        self._run_check("WebSocket配置", self._validate_websocket_config)
        self._run_check("推送设置", self._validate_push_settings)
    
    def _run_check(self, check_name: str, check_function):
        """运行单个检查"""
        self.total_checks += 1
        
        try:
            result = check_function()
            
            if result['success']:
                print(f"   ✅ {check_name}: {result['message']}")
                self.passed_checks += 1
                self.check_results[check_name] = {'status': 'PASS', 'message': result['message']}
            else:
                print(f"   ❌ {check_name}: {result['message']}")
                self.failed_checks += 1
                self.check_results[check_name] = {'status': 'FAIL', 'message': result['message']}
                
        except Exception as e:
            print(f"   💥 {check_name}: 检查异常 - {str(e)}")
            self.failed_checks += 1
            self.check_results[check_name] = {'status': 'ERROR', 'message': str(e)}
    
    def _validate_config_files(self) -> dict:
        """验证配置文件"""
        try:
            validation_result = validate_all_configs()
            
            if validation_result['status'] == 'success':
                validation_data = validation_result['data']
                
                if validation_data['overall_valid']:
                    return {
                        'success': True,
                        'message': '所有配置文件格式正确'
                    }
                else:
                    invalid_configs = [
                        name for name, result in validation_data['validation_results'].items()
                        if not result['valid']
                    ]
                    return {
                        'success': False,
                        'message': f'配置文件格式错误: {", ".join(invalid_configs)}'
                    }
            else:
                return {
                    'success': False,
                    'message': validation_result['message']
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'配置验证异常: {str(e)}'
            }
    
    def _check_directory_structure(self) -> dict:
        """检查目录结构"""
        try:
            from src.core.utils import get_config_dir, get_image_dir, get_result_dir
            
            required_dirs = {
                'config': get_config_dir(),
                'image': get_image_dir(),
                'result': get_result_dir(),
                'cut': get_image_dir() / 'cut'
            }
            
            missing_dirs = []
            
            for dir_name, dir_path in required_dirs.items():
                if not dir_path.exists():
                    missing_dirs.append(f"{dir_name}({dir_path})")
                    # 尝试创建目录
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        pass
            
            if missing_dirs:
                return {
                    'success': False,
                    'message': f'缺少目录: {", ".join(missing_dirs)}'
                }
            else:
                return {
                    'success': True,
                    'message': '目录结构完整'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'目录检查异常: {str(e)}'
            }
    
    def _check_dependencies(self) -> dict:
        """检查依赖模块"""
        try:
            missing_deps = []
            optional_deps = []
            
            # 检查核心依赖
            core_deps = ['json', 'pathlib', 'datetime', 'threading']
            for dep in core_deps:
                try:
                    __import__(dep)
                except ImportError:
                    missing_deps.append(dep)
            
            # 检查可选依赖
            optional_dependencies = {
                'ultralytics': 'YOLOv8识别',
                'easyocr': 'OCR识别',
                'paddlepaddle': 'PaddleOCR识别',
                'websockets': 'WebSocket推送',
                'PIL': '图片处理',
                'cv2': '图片处理'
            }
            
            for dep, description in optional_dependencies.items():
                try:
                    __import__(dep)
                except ImportError:
                    optional_deps.append(f"{dep}({description})")
            
            if missing_deps:
                return {
                    'success': False,
                    'message': f'缺少核心依赖: {", ".join(missing_deps)}'
                }
            elif optional_deps:
                return {
                    'success': True,
                    'message': f'核心依赖完整，可选依赖缺失: {", ".join(optional_deps)}'
                }
            else:
                return {
                    'success': True,
                    'message': '所有依赖模块完整'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'依赖检查异常: {str(e)}'
            }
    
    def _validate_camera_format(self) -> dict:
        """验证摄像头配置格式"""
        try:
            cameras_result = get_enabled_cameras()
            
            if cameras_result['status'] != 'success':
                return {
                    'success': False,
                    'message': cameras_result['message']
                }
            
            cameras = cameras_result['data']['cameras']
            
            if not cameras:
                return {
                    'success': False,
                    'message': '没有配置摄像头'
                }
            
            # 检查每个摄像头的必需字段
            invalid_cameras = []
            required_fields = ['id', 'name', 'ip', 'username', 'password']
            
            for camera in cameras:
                missing_fields = []
                for field in required_fields:
                    if field not in camera or not camera[field]:
                        missing_fields.append(field)
                
                if missing_fields:
                    invalid_cameras.append(f"{camera.get('id', 'unknown')}(缺少: {', '.join(missing_fields)})")
            
            if invalid_cameras:
                return {
                    'success': False,
                    'message': f'摄像头配置不完整: {"; ".join(invalid_cameras)}'
                }
            else:
                return {
                    'success': True,
                    'message': f'{len(cameras)} 个摄像头配置格式正确'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'摄像头格式验证异常: {str(e)}'
            }
    
    def _validate_camera_network(self) -> dict:
        """验证摄像头网络配置"""
        try:
            cameras_result = get_enabled_cameras()
            
            if cameras_result['status'] != 'success':
                return {
                    'success': False,
                    'message': '无法获取摄像头配置'
                }
            
            cameras = cameras_result['data']['cameras']
            invalid_configs = []
            
            for camera in cameras:
                camera_id = camera.get('id', 'unknown')
                ip = camera.get('ip', '')
                port = camera.get('port', 554)
                
                # 简单的IP格式检查
                if not ip or not self._is_valid_ip(ip):
                    invalid_configs.append(f"{camera_id}(IP无效: {ip})")
                
                # 端口检查
                if not isinstance(port, int) or port < 1 or port > 65535:
                    invalid_configs.append(f"{camera_id}(端口无效: {port})")
            
            if invalid_configs:
                return {
                    'success': False,
                    'message': f'网络配置错误: {"; ".join(invalid_configs)}'
                }
            else:
                return {
                    'success': True,
                    'message': f'{len(cameras)} 个摄像头网络配置正确'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'网络配置验证异常: {str(e)}'
            }
    
    def _validate_mark_positions(self) -> dict:
        """验证标记位置配置"""
        try:
            cameras_result = get_enabled_cameras()
            
            if cameras_result['status'] != 'success':
                return {
                    'success': False,
                    'message': '无法获取摄像头配置'
                }
            
            cameras = cameras_result['data']['cameras']
            standard_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
            
            marked_cameras = 0
            total_marked_positions = 0
            
            for camera in cameras:
                camera_id = camera.get('id', 'unknown')
                mark_positions = camera.get('mark_positions', {})
                
                marked_positions_count = 0
                for position in standard_positions:
                    if position in mark_positions:
                        pos_data = mark_positions[position]
                        if pos_data.get('marked', False) and pos_data.get('x', 0) > 0 and pos_data.get('y', 0) > 0:
                            marked_positions_count += 1
                
                if marked_positions_count > 0:
                    marked_cameras += 1
                    total_marked_positions += marked_positions_count
            
            if marked_cameras == 0:
                return {
                    'success': False,
                    'message': '所有摄像头都没有配置标记位置'
                }
            elif marked_cameras < len(cameras):
                return {
                    'success': True,
                    'message': f'{marked_cameras}/{len(cameras)} 个摄像头已配置标记，总计 {total_marked_positions} 个位置'
                }
            else:
                return {
                    'success': True,
                    'message': f'所有摄像头已配置标记，总计 {total_marked_positions} 个位置'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'标记位置验证异常: {str(e)}'
            }
    
    def _validate_websocket_config(self) -> dict:
        """验证WebSocket配置"""
        try:
            from config_loader import load_push_config
            
            push_result = load_push_config()
            
            if push_result['status'] != 'success':
                return {
                    'success': False,
                    'message': push_result['message']
                }
            
            push_config = push_result['data']
            ws_config = push_config.get('websocket', {})
            
            if not ws_config.get('enabled', False):
                return {
                    'success': True,
                    'message': 'WebSocket推送已禁用'
                }
            
            # 检查必需配置
            server_url = ws_config.get('server_url', '')
            client_id = ws_config.get('client_id', '')
            
            if not server_url:
                return {
                    'success': False,
                    'message': 'WebSocket服务器地址未配置'
                }
            
            if not client_id:
                return {
                    'success': False,
                    'message': 'WebSocket客户端ID未配置'
                }
            
            # 简单的URL格式检查
            if not (server_url.startswith('ws://') or server_url.startswith('wss://')):
                return {
                    'success': False,
                    'message': f'WebSocket服务器地址格式错误: {server_url}'
                }
            
            return {
                'success': True,
                'message': f'WebSocket配置正确: {server_url}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'WebSocket配置验证异常: {str(e)}'
            }
    
    def _validate_push_settings(self) -> dict:
        """验证推送设置"""
        try:
            from config_loader import load_push_config
            
            push_result = load_push_config()
            
            if push_result['status'] != 'success':
                return {
                    'success': False,
                    'message': push_result['message']
                }
            
            push_config = push_result['data']
            push_settings = push_config.get('push_settings', {})
            
            # 检查推送间隔
            push_interval = push_settings.get('push_interval', 2)
            if not isinstance(push_interval, (int, float)) or push_interval <= 0:
                return {
                    'success': False,
                    'message': f'推送间隔配置错误: {push_interval}'
                }
            
            # 检查重试设置
            retry_times = push_settings.get('retry_times', 3)
            if not isinstance(retry_times, int) or retry_times < 0:
                return {
                    'success': False,
                    'message': f'重试次数配置错误: {retry_times}'
                }
            
            return {
                'success': True,
                'message': f'推送设置正确 (间隔: {push_interval}s, 重试: {retry_times}次)'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'推送设置验证异常: {str(e)}'
            }
    
    def _test_camera_connections(self):
        """测试摄像头连接"""
        print("\n🔌 测试摄像头连接...")
        
        try:
            cameras_result = get_enabled_cameras()
            
            if cameras_result['status'] != 'success':
                print(f"   ❌ 获取摄像头列表失败: {cameras_result['message']}")
                return
            
            cameras = cameras_result['data']['cameras']
            
            if not cameras:
                print("   ⚠️  没有启用的摄像头可测试")
                return
            
            # 导入拍照控制器
            try:
                from src.processors.photo_controller import test_camera_connection
            except ImportError:
                print("   ❌ 无法导入拍照控制器")
                return
            
            for camera in cameras:
                camera_id = camera['id']
                camera_name = camera.get('name', f'摄像头{camera_id}')
                
                print(f"   🔍 测试 {camera_name} ({camera_id})...", end=' ')
                
                try:
                    test_result = test_camera_connection(camera_id)
                    
                    if test_result['status'] == 'success':
                        print("✅ 连接正常")
                        self.check_results[f"摄像头连接_{camera_id}"] = {'status': 'PASS', 'message': '连接正常'}
                    else:
                        print(f"❌ 连接失败: {test_result['message']}")
                        self.check_results[f"摄像头连接_{camera_id}"] = {'status': 'FAIL', 'message': test_result['message']}
                        
                except Exception as e:
                    print(f"💥 测试异常: {str(e)}")
                    self.check_results[f"摄像头连接_{camera_id}"] = {'status': 'ERROR', 'message': str(e)}
                    
        except Exception as e:
            print(f"   ❌ 摄像头连接测试异常: {e}")
    
    def _test_recognition_algorithms(self):
        """测试识别算法"""
        print("\n🧠 测试识别算法...")
        
        # 测试YOLOv8
        print("   🎯 测试YOLOv8算法...", end=' ')
        try:
            from src.processors.poker_recognizer import load_yolov8_model
            model, model_path = load_yolov8_model()
            print("✅ YOLOv8可用")
            self.check_results['YOLOv8算法'] = {'status': 'PASS', 'message': 'YOLOv8模型加载成功'}
        except Exception as e:
            print(f"❌ YOLOv8不可用: {str(e)}")
            self.check_results['YOLOv8算法'] = {'status': 'FAIL', 'message': str(e)}
        
        # 测试EasyOCR
        print("   📝 测试EasyOCR算法...", end=' ')
        try:
            from src.processors.poker_ocr import load_easyocr_reader
            reader = load_easyocr_reader()
            print("✅ EasyOCR可用")
            self.check_results['EasyOCR算法'] = {'status': 'PASS', 'message': 'EasyOCR加载成功'}
        except Exception as e:
            print(f"❌ EasyOCR不可用: {str(e)}")
            self.check_results['EasyOCR算法'] = {'status': 'FAIL', 'message': str(e)}
        
        # 测试PaddleOCR
        print("   🔤 测试PaddleOCR算法...", end=' ')
        try:
            from src.processors.poker_paddle_ocr import load_paddle_ocr
            ocr = load_paddle_ocr()
            print("✅ PaddleOCR可用")
            self.check_results['PaddleOCR算法'] = {'status': 'PASS', 'message': 'PaddleOCR加载成功'}
        except Exception as e:
            print(f"❌ PaddleOCR不可用: {str(e)}")
            self.check_results['PaddleOCR算法'] = {'status': 'FAIL', 'message': str(e)}
    
    def _is_valid_ip(self, ip: str) -> bool:
        """检查IP地址格式是否有效"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                if not part.isdigit():
                    return False
                num = int(part)
                if num < 0 or num > 255:
                    return False
            
            return True
        except:
            return False
    
    def _generate_report(self):
        """生成检查报告"""
        print("\n📊 配置检查报告")
        print("=" * 60)
        
        print(f"📋 检查统计:")
        print(f"   总检查项: {self.total_checks}")
        print(f"   通过: {self.passed_checks} ✅")
        print(f"   失败: {self.failed_checks} ❌")
        
        if self.total_checks > 0:
            success_rate = (self.passed_checks / self.total_checks) * 100
            print(f"   通过率: {success_rate:.1f}%")
        
        # 显示失败项目
        if self.failed_checks > 0:
            print(f"\n❌ 失败项目:")
            for check_name, result in self.check_results.items():
                if result['status'] in ['FAIL', 'ERROR']:
                    status_icon = "💥" if result['status'] == 'ERROR' else "❌"
                    print(f"   {status_icon} {check_name}: {result['message']}")
        
        # 总结
        print(f"\n{'='*60}")
        if self.failed_checks == 0:
            print("🎉 所有配置检查通过！系统可以正常运行。")
        else:
            print("⚠️  发现配置问题，请根据上述信息进行修复。")
        
        print("=" * 60)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='系统配置检查工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python check_config.py                # 基础配置检查
  python check_config.py --test-cameras # 同时测试摄像头连接
  python check_config.py --test-algorithms # 同时测试识别算法
  python check_config.py --full        # 完整检查（包含所有测试）
        """
    )
    
    parser.add_argument('--test-cameras', action='store_true',
                       help='测试摄像头连接')
    parser.add_argument('--test-algorithms', action='store_true',
                       help='测试识别算法')
    parser.add_argument('--full', action='store_true',
                       help='完整检查（包含所有测试）')
    parser.add_argument('--report-file', 
                       help='保存检查报告到文件')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析参数
        args = parse_arguments()
        
        # 创建配置检查器
        checker = ConfigChecker()
        
        # 确定测试范围
        test_cameras = args.test_cameras or args.full
        test_algorithms = args.test_algorithms or args.full
        
        # 运行检查
        success = checker.run_all_checks(
            test_cameras=test_cameras,
            test_algorithms=test_algorithms
        )
        
        # 保存报告到文件
        if args.report_file:
            try:
                with open(args.report_file, 'w', encoding='utf-8') as f:
                    f.write("配置检查报告\n")
                    f.write("=" * 30 + "\n")
                    f.write(f"总检查项: {checker.total_checks}\n")
                    f.write(f"通过: {checker.passed_checks}\n")
                    f.write(f"失败: {checker.failed_checks}\n\n")
                    
                    for check_name, result in checker.check_results.items():
                        status = result['status']
                        message = result['message']
                        f.write(f"[{status}] {check_name}: {message}\n")
                
                print(f"\n📄 检查报告已保存到: {args.report_file}")
                
            except Exception as e:
                print(f"❌ 保存报告失败: {e}")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ 配置检查异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())