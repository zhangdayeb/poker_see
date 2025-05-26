#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速创建 __init__.py 文件的脚本
用于修复 Python 包导入问题
"""

import os
from pathlib import Path

def create_init_files(project_root=None):
    """
    在指定目录及其子目录中创建 __init__.py 文件
    """
    if project_root is None:
        project_root = Path.cwd()
    else:
        project_root = Path(project_root)
    
    print(f"🔧 在项目根目录创建 __init__.py 文件: {project_root}")
    
    # 需要创建 __init__.py 的目录
    directories_to_check = [
        "src",
        "src/core", 
        "src/servers",
        "src/websocket",
        "src/processors",
        "src/workflows",
        "src/tests"
    ]
    
    # 基础 __init__.py 内容
    basic_init_content = '''# -*- coding: utf-8 -*-
"""
Python 包初始化文件
"""
'''
    
    # 特殊目录的 __init__.py 内容
    special_init_contents = {
        "src": '''# -*- coding: utf-8 -*-
"""
扑克识别系统
Poker Recognition System
"""

__version__ = "2.1.0"
''',
        
        "src/core": '''# -*- coding: utf-8 -*-
"""
核心功能模块
Core functionality modules
"""

# 导入常用功能（根据实际情况调整）
try:
    from .utils import get_timestamp, log_info, log_success, log_error, log_warning
    from .config_manager import get_config_status
    
    __all__ = [
        'get_timestamp', 'log_info', 'log_success', 'log_error', 'log_warning',
        'get_config_status'
    ]
except ImportError:
    # 如果模块还不存在，跳过导入
    pass
''',
        
        "src/servers": '''# -*- coding: utf-8 -*-
"""
服务器模块
Server modules
"""

# 导入服务器功能（根据实际情况调整）
try:
    from .http_server import start_http_server, stop_http_server
    from .websocket_server import start_websocket_server, stop_websocket_server
    
    __all__ = [
        'start_http_server', 'stop_http_server',
        'start_websocket_server', 'stop_websocket_server'
    ]
except ImportError:
    # 如果模块还不存在，跳过导入
    pass
''',
        
        "src/websocket": '''# -*- coding: utf-8 -*-
"""
WebSocket功能模块
WebSocket functionality modules
"""

# 导入WebSocket功能（根据实际情况调整）
try:
    from .connection_manager import cleanup_all_connections, get_connection_stats
    
    __all__ = [
        'cleanup_all_connections', 'get_connection_stats'
    ]
except ImportError:
    # 如果模块还不存在，跳过导入
    pass
'''
    }
    
    created_count = 0
    skipped_count = 0
    
    for dir_path in directories_to_check:
        full_dir_path = project_root / dir_path
        
        # 检查目录是否存在
        if not full_dir_path.exists():
            print(f"⚠️  目录不存在，跳过: {dir_path}")
            continue
        
        # __init__.py 文件路径
        init_file_path = full_dir_path / "__init__.py"
        
        # 如果文件已存在，跳过
        if init_file_path.exists():
            print(f"✅ 已存在，跳过: {init_file_path}")
            skipped_count += 1
            continue
        
        # 选择内容
        if dir_path in special_init_contents:
            content = special_init_contents[dir_path]
        else:
            content = basic_init_content
        
        # 创建文件
        try:
            with open(init_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已创建: {init_file_path}")
            created_count += 1
        except Exception as e:
            print(f"❌ 创建失败 {init_file_path}: {e}")
    
    print(f"\n🎉 完成！创建了 {created_count} 个文件，跳过了 {skipped_count} 个已存在的文件")
    
    # 如果没有创建任何文件，给出建议
    if created_count == 0:
        print("\n💡 建议:")
        print("1. 检查项目目录结构是否正确")
        print("2. 确保在正确的项目根目录运行此脚本")
        print("3. 如果需要，手动创建缺少的目录")

def auto_discover_and_create(project_root=None):
    """
    自动发现 src 目录下的所有子目录并创建 __init__.py
    """
    if project_root is None:
        project_root = Path.cwd()
    else:
        project_root = Path(project_root)
    
    src_dir = project_root / "src"
    if not src_dir.exists():
        print("❌ 未找到 src 目录")
        return
    
    print(f"🔍 自动发现 src 目录下的包: {src_dir}")
    
    # 先为 src 本身创建
    src_init = src_dir / "__init__.py"
    if not src_init.exists():
        with open(src_init, 'w', encoding='utf-8') as f:
            f.write('''# -*- coding: utf-8 -*-
"""
扑克识别系统
"""

__version__ = "2.1.0"
''')
        print(f"✅ 已创建: {src_init}")
    
    # 遍历所有子目录
    created_count = 0
    for item in src_dir.rglob("*/"):
        if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('__'):
            init_file = item / "__init__.py"
            if not init_file.exists():
                try:
                    with open(init_file, 'w', encoding='utf-8') as f:
                        f.write(f'''# -*- coding: utf-8 -*-
"""
{item.name} 模块
"""
''')
                    print(f"✅ 已创建: {init_file}")
                    created_count += 1
                except Exception as e:
                    print(f"❌ 创建失败 {init_file}: {e}")
    
    print(f"\n🎉 自动创建完成！共创建了 {created_count} 个 __init__.py 文件")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="创建 Python 包的 __init__.py 文件")
    parser.add_argument("--path", default=".", help="项目根目录路径（默认为当前目录）")
    parser.add_argument("--auto", action="store_true", help="自动发现所有子目录并创建 __init__.py")
    
    args = parser.parse_args()
    
    if args.auto:
        auto_discover_and_create(args.path)
    else:
        create_init_files(args.path)

if __name__ == "__main__":
    main()