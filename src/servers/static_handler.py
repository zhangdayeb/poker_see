#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态文件处理模块 - 处理HTML、图片等静态资源的服务
功能:
1. HTML文件服务 (biaoji.html, simple_biaoji.html)
2. 图片文件服务 (/image/ 路径下的文件)
3. 文件类型识别和Content-Type设置
4. 缓存控制和文件流传输
5. 文件权限和安全检查
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from utils import (
    get_image_dir, get_content_type, get_file_size, file_exists,
    log_info, log_success, log_error, log_warning, safe_encode
)

class StaticHandler:
    """静态文件处理器"""
    
    def __init__(self):
        """初始化静态文件处理器"""
        # 设置目录路径
        self.pycontroller_dir = Path(__file__).parent
        self.image_dir = get_image_dir()
        
        # 支持的文件类型
        self.supported_extensions = {
            '.html', '.htm', '.css', '.js', '.json', '.txt',
            '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
            '.pdf', '.zip'
        }
        
        # 图片文件扩展名
        self.image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico'}
        
        log_info("静态文件处理器初始化完成", "STATIC")
    
    def serve_html_file(self, filename: str) -> Dict[str, Any]:
        """
        服务HTML文件
        
        Args:
            filename: HTML文件名
            
        Returns:
            文件服务结果
        """
        try:
            # 安全检查：只允许特定的HTML文件
            allowed_html_files = ['biaoji.html', 'simple_biaoji.html', 'index.html']
            if filename not in allowed_html_files:
                return {
                    'success': False,
                    'error': f'不允许访问的HTML文件: {filename}',
                    'status_code': 403
                }
            
            # 构建文件路径
            file_path = self.pycontroller_dir / filename
            
            # 检查文件是否存在
            if not file_path.exists():
                log_warning(f"HTML文件不存在: {filename}", "STATIC")
                return {
                    'success': False,
                    'error': f'HTML文件不存在: {filename}',
                    'status_code': 404
                }
            
            # 读取文件内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_size = len(content.encode('utf-8'))
                
                log_success(f"HTML文件服务成功: {filename} ({file_size} bytes)", "STATIC")
                
                return {
                    'success': True,
                    'content': content,
                    'content_type': 'text/html; charset=utf-8',
                    'file_size': file_size,
                    'cache_control': 'no-cache',
                    'filename': filename
                }
                
            except UnicodeDecodeError as e:
                log_error(f"HTML文件编码错误 {filename}: {e}", "STATIC")
                return {
                    'success': False,
                    'error': f'文件编码错误: {str(e)}',
                    'status_code': 500
                }
                
        except Exception as e:
            log_error(f"服务HTML文件失败 {filename}: {e}", "STATIC")
            return {
                'success': False,
                'error': f'服务文件失败: {str(e)}',
                'status_code': 500
            }
    
    def serve_image_file(self, filename: str) -> Dict[str, Any]:
        """
        服务图片文件
        
        Args:
            filename: 图片文件名
            
        Returns:
            文件服务结果
        """
        try:
            # 安全检查：验证文件名
            if not self._is_safe_filename(filename):
                return {
                    'success': False,
                    'error': f'不安全的文件名: {filename}',
                    'status_code': 403
                }
            
            # 检查文件扩展名
            file_path = self.image_dir / filename
            if file_path.suffix.lower() not in self.image_extensions:
                return {
                    'success': False,
                    'error': f'不支持的图片格式: {file_path.suffix}',
                    'status_code': 415
                }
            
            # 检查文件是否存在
            if not file_path.exists():
                log_warning(f"图片文件不存在: {filename}", "STATIC")
                return {
                    'success': False,
                    'error': f'图片文件不存在: {filename}',
                    'status_code': 404
                }
            
            # 获取文件信息
            file_size = get_file_size(file_path)
            content_type = get_content_type(file_path)
            
            # 验证文件大小
            if file_size == 0:
                log_error(f"图片文件为空: {filename}", "STATIC")
                return {
                    'success': False,
                    'error': f'图片文件为空: {filename}',
                    'status_code': 500
                }
            
            # 读取文件内容（二进制模式）
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # 验证读取的内容
                if len(content) == 0:
                    log_error(f"读取图片文件内容为空: {filename}", "STATIC")
                    return {
                        'success': False,
                        'error': f'读取图片文件内容为空: {filename}',
                        'status_code': 500
                    }
                
                # 简单验证PNG文件格式
                if filename.lower().endswith('.png') and not content.startswith(b'\x89PNG'):
                    log_warning(f"可能不是有效的PNG文件: {filename}", "STATIC")
                    # 但仍然尝试发送，让浏览器处理
                
                log_success(f"图片文件服务成功: {filename} ({file_size} bytes)", "STATIC")
                
                return {
                    'success': True,
                    'content': content,
                    'content_type': content_type,
                    'file_size': file_size,
                    'cache_control': 'no-cache, no-store, must-revalidate',
                    'filename': filename,
                    'is_binary': True
                }
                
            except IOError as e:
                log_error(f"读取图片文件失败 {filename}: {e}", "STATIC")
                return {
                    'success': False,
                    'error': f'读取文件失败: {str(e)}',
                    'status_code': 500
                }
                
        except Exception as e:
            log_error(f"服务图片文件失败 {filename}: {e}", "STATIC")
            return {
                'success': False,
                'error': f'服务文件失败: {str(e)}',
                'status_code': 500
            }
    
    def serve_static_file(self, file_path: str) -> Dict[str, Any]:
        """
        通用静态文件服务
        
        Args:
            file_path: 文件路径（如 /image/xxx.png）
            
        Returns:
            文件服务结果
        """
        try:
            # 解析文件路径
            if file_path.startswith('/'):
                file_path = file_path[1:]  # 移除开头的斜杠
            
            path_parts = file_path.split('/')
            
            if len(path_parts) < 2:
                return {
                    'success': False,
                    'error': '无效的文件路径',
                    'status_code': 400
                }
            
            directory = path_parts[0]
            filename = '/'.join(path_parts[1:])
            
            # 根据目录类型分发处理
            if directory == 'image':
                return self.serve_image_file(filename)
            else:
                return {
                    'success': False,
                    'error': f'不支持的目录: {directory}',
                    'status_code': 404
                }
                
        except Exception as e:
            log_error(f"服务静态文件失败 {file_path}: {e}", "STATIC")
            return {
                'success': False,
                'error': f'服务文件失败: {str(e)}',
                'status_code': 500
            }
    
    def _is_safe_filename(self, filename: str) -> bool:
        """
        检查文件名是否安全
        
        Args:
            filename: 文件名
            
        Returns:
            是否安全
        """
        try:
            # 基本安全检查
            if not filename or len(filename) > 255:
                return False
            
            # 检查危险字符
            dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
            for char in dangerous_chars:
                if char in filename:
                    return False
            
            # 检查是否为隐藏文件
            if filename.startswith('.'):
                return False
            
            # 检查文件扩展名
            file_path = Path(filename)
            if file_path.suffix.lower() not in self.supported_extensions:
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息
        """
        try:
            # 解析路径
            if file_path.startswith('/'):
                file_path = file_path[1:]
            
            if file_path.startswith('image/'):
                filename = file_path[6:]  # 移除 'image/' 前缀
                full_path = self.image_dir / filename
            else:
                # HTML文件在pycontroller目录
                full_path = self.pycontroller_dir / file_path
            
            if not full_path.exists():
                return {
                    'exists': False,
                    'error': '文件不存在'
                }
            
            stat = full_path.stat()
            
            return {
                'exists': True,
                'filename': full_path.name,
                'file_size': stat.st_size,
                'modified_time': stat.st_mtime,
                'content_type': get_content_type(full_path),
                'is_image': full_path.suffix.lower() in self.image_extensions,
                'extension': full_path.suffix.lower()
            }
            
        except Exception as e:
            log_error(f"获取文件信息失败 {file_path}: {e}", "STATIC")
            return {
                'exists': False,
                'error': f'获取文件信息失败: {str(e)}'
            }
    
    def list_image_files(self, limit: int = 50) -> Dict[str, Any]:
        """
        列出图片文件
        
        Args:
            limit: 返回数量限制
            
        Returns:
            图片文件列表
        """
        try:
            if not self.image_dir.exists():
                return {
                    'success': True,
                    'files': [],
                    'total_count': 0,
                    'message': '图片目录不存在'
                }
            
            # 获取所有图片文件
            image_files = []
            for ext in self.image_extensions:
                image_files.extend(self.image_dir.glob(f'*{ext}'))
            
            # 按修改时间排序
            image_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # 限制数量
            image_files = image_files[:limit]
            
            # 构建文件信息
            files_info = []
            for file_path in image_files:
                file_info = {
                    'filename': file_path.name,
                    'file_size': get_file_size(file_path),
                    'modified_time': file_path.stat().st_mtime,
                    'url': f'/image/{file_path.name}',
                    'content_type': get_content_type(file_path)
                }
                files_info.append(file_info)
            
            return {
                'success': True,
                'files': files_info,
                'total_count': len(files_info),
                'limit': limit
            }
            
        except Exception as e:
            log_error(f"列出图片文件失败: {e}", "STATIC")
            return {
                'success': False,
                'error': f'列出文件失败: {str(e)}',
                'files': []
            }
    
    def generate_directory_listing(self, directory_path: str) -> str:
        """
        生成目录列表HTML
        
        Args:
            directory_path: 目录路径
            
        Returns:
            HTML内容
        """
        try:
            if directory_path == '/image' or directory_path == '/image/':
                # 图片目录列表
                files_result = self.list_image_files(100)
                files = files_result.get('files', [])
                
                html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📸 图片目录 - 扑克识别系统</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
        .file-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
        .file-item {{ border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: #fafafa; }}
        .file-name {{ font-weight: bold; color: #333; margin-bottom: 8px; }}
        .file-info {{ color: #666; font-size: 0.9em; }}
        .file-preview {{ text-align: center; margin: 10px 0; }}
        .file-preview img {{ max-width: 200px; max-height: 150px; border-radius: 4px; }}
        .no-files {{ text-align: center; color: #999; padding: 40px; }}
        .back-link {{ display: inline-block; margin-bottom: 20px; color: #007bff; text-decoration: none; }}
        .back-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← 返回首页</a>
        <h1>📸 图片目录</h1>
        
        {"<div class='no-files'>暂无图片文件</div>" if not files else ""}
        
        <div class="file-grid">
"""
                
                for file_info in files:
                    filename = file_info['filename']
                    file_size = file_info['file_size']
                    modified_time = file_info['modified_time']
                    url = file_info['url']
                    
                    # 格式化文件大小
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024*1024:
                        size_str = f"{file_size/1024:.1f} KB"
                    else:
                        size_str = f"{file_size/(1024*1024):.1f} MB"
                    
                    html_content += f"""
            <div class="file-item">
                <div class="file-name">{filename}</div>
                <div class="file-preview">
                    <img src="{url}" alt="{filename}" loading="lazy">
                </div>
                <div class="file-info">
                    大小: {size_str}<br>
                    <a href="{url}" target="_blank">查看原图</a>
                </div>
            </div>"""
                
                html_content += """
        </div>
    </div>
</body>
</html>"""
                
                return html_content
            
            else:
                # 默认目录列表
                return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>目录不存在</title>
</head>
<body>
    <h1>404 - 目录不存在</h1>
    <p><a href="/">返回首页</a></p>
</body>
</html>"""
                
        except Exception as e:
            log_error(f"生成目录列表失败: {e}", "STATIC")
            return f"<html><body><h1>生成目录列表失败: {str(e)}</h1></body></html>"

# 创建全局实例
static_handler = StaticHandler()

# 导出主要函数
def serve_html_file(filename: str) -> Dict[str, Any]:
    """服务HTML文件"""
    return static_handler.serve_html_file(filename)

def serve_image_file(filename: str) -> Dict[str, Any]:
    """服务图片文件"""
    return static_handler.serve_image_file(filename)

def serve_static_file(file_path: str) -> Dict[str, Any]:
    """服务静态文件"""
    return static_handler.serve_static_file(file_path)

def get_file_info(file_path: str) -> Dict[str, Any]:
    """获取文件信息"""
    return static_handler.get_file_info(file_path)

def list_image_files(limit: int = 50) -> Dict[str, Any]:
    """列出图片文件"""
    return static_handler.list_image_files(limit)

def generate_directory_listing(directory_path: str) -> str:
    """生成目录列表HTML"""
    return static_handler.generate_directory_listing(directory_path)

if __name__ == "__main__":
    # 测试静态文件处理器
    print("🧪 测试静态文件处理器")
    
    # 测试HTML文件服务
    html_result = serve_html_file("biaoji.html")
    print(f"HTML文件服务: {html_result.get('success', False)}")
    
    # 测试图片文件列表
    images = list_image_files(10)
    print(f"图片文件列表: {images}")
    
    # 测试文件信息获取
    file_info = get_file_info("image/camera_001.png")
    print(f"文件信息: {file_info}")
    
    # 测试目录列表生成
    dir_html = generate_directory_listing("/image/")
    print(f"目录列表HTML长度: {len(dir_html)}")
    
    print("✅ 静态文件处理器测试完成")