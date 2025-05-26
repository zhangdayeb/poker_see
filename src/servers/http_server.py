#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP服务器核心模块 - 基于BaseHTTPRequestHandler的HTTP服务器
功能:
1. HTTP服务器启动和管理
2. 路由分发和请求处理
3. 静态文件服务集成
4. API接口服务集成
5. 错误处理和日志记录
6. CORS支持和编码处理
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
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional

# 导入工具模块
try:
    from src.core.utils import (
        safe_encode, safe_decode, get_content_type,
        log_info, log_success, log_error, log_warning, get_timestamp
    )
except ImportError:
    # 如果导入失败，创建临时的日志函数
    def log_info(msg, tag="INFO"):
        print(f"[{tag}] {msg}")
    def log_success(msg, tag="SUCCESS"):
        print(f"[{tag}] {msg}")
    def log_error(msg, tag="ERROR"):
        print(f"[{tag}] {msg}")
    def log_warning(msg, tag="WARNING"):
        print(f"[{tag}] {msg}")
    def get_timestamp():
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    def safe_encode(text):
        return text.encode('utf-8') if isinstance(text, str) else text
    def safe_decode(data):
        return data.decode('utf-8') if isinstance(data, bytes) else data
    def get_content_type(file_path):
        return 'text/html; charset=utf-8'

# 导入 API 处理器
try:
    from src.servers.api_handler import handle_api_request, get_api_documentation
    log_info("✅ API handler 导入成功", "STATIC")
except ImportError as e:
    log_info(f"❌ API handler 导入失败: {e}", "STATIC")
    # 创建临时的 API 处理函数
    def handle_api_request(method, path, query_params=None, post_data=None):
        return {
            'status': 'error',
            'message': 'API handler not available',
            'timestamp': get_timestamp()
        }
    def get_api_documentation():
        return {
            'status': 'success',
            'data': {
                'api_info': {
                    'name': 'Poker Recognition API',
                    'version': '2.0',
                    'description': '扑克识别系统API接口'
                },
                'endpoints': {
                    'GET /api/status': '获取系统状态',
                    'POST /api/test': '测试接口'
                }
            }
        }

# 导入静态文件处理器
try:
    from src.servers.static_handler import serve_html_file, serve_static_file, generate_directory_listing
except ImportError:
    # 创建临时的静态文件处理函数
    def serve_html_file(filename):
        return {
            'success': False,
            'error': 'Static handler not available',
            'status_code': 500
        }
    def serve_static_file(path):
        return {
            'success': False,
            'error': 'Static handler not available',
            'status_code': 500
        }
    def generate_directory_listing(directory_path):
        return f"""
        <html>
        <head><title>Directory Listing</title></head>
        <body>
            <h1>Directory: {directory_path}</h1>
            <p>Static handler not available</p>
            <a href="/">Back to Home</a>
        </body>
        </html>
        """

class HTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def __init__(self, *args, **kwargs):
        """初始化请求处理器"""
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            log_info(f"GET {path}", "HTTP")
            
            # 路由分发
            if path == '/':
                # 主页
                self._serve_index_page()
            elif path in ['/biaoji.html', '/simple_biaoji.html']:
                # HTML页面
                self._serve_html_page(path[1:])  # 移除开头的斜杠
            elif path.startswith('/api/'):
                # API接口
                self._handle_api_request('GET', path, query_params)
            elif path.startswith('/image/'):
                # 静态图片文件
                self._serve_static_file(path)
            elif path == '/api-docs':
                # API文档页面
                self._serve_api_docs()
            elif path in ['/image', '/image/']:
                # 图片目录列表
                self._serve_directory_listing('/image/')
            else:
                # 404 未找到
                self._send_404_error(f"页面不存在: {path}")
                
        except Exception as e:
            log_error(f"GET请求处理失败: {e}", "HTTP")
            self._send_500_error(f"服务器内部错误: {str(e)}")
    
    def do_POST(self):
        """处理POST请求"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            log_info(f"POST {path}", "HTTP")
            
            # 读取POST数据
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = None
            
            if content_length > 0:
                post_data = self.rfile.read(content_length)
            
            # API接口处理
            if path.startswith('/api/'):
                self._handle_api_request('POST', path, query_params, post_data)
            else:
                self._send_404_error(f"POST接口不存在: {path}")
                
        except Exception as e:
            log_error(f"POST请求处理失败: {e}", "HTTP")
            self._send_500_error(f"服务器内部错误: {str(e)}")
    
    def do_PUT(self):
        """处理PUT请求"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            log_info(f"PUT {path}", "HTTP")
            
            # 读取PUT数据
            content_length = int(self.headers.get('Content-Length', 0))
            put_data = None
            
            if content_length > 0:
                put_data = self.rfile.read(content_length)
            
            # API接口处理
            if path.startswith('/api/'):
                self._handle_api_request('PUT', path, query_params, put_data)
            else:
                self._send_404_error(f"PUT接口不存在: {path}")
                
        except Exception as e:
            log_error(f"PUT请求处理失败: {e}", "HTTP")
            self._send_500_error(f"服务器内部错误: {str(e)}")
    
    def do_DELETE(self):
        """处理DELETE请求"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            log_info(f"DELETE {path}", "HTTP")
            
            # API接口处理
            if path.startswith('/api/'):
                self._handle_api_request('DELETE', path, query_params)
            else:
                self._send_404_error(f"DELETE接口不存在: {path}")
                
        except Exception as e:
            log_error(f"DELETE请求处理失败: {e}", "HTTP")
            self._send_500_error(f"服务器内部错误: {str(e)}")
    
    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self._send_cors_headers()
        self.send_response(200)
        self.end_headers()
    
    def _handle_api_request(self, method: str, path: str, query_params: Dict[str, Any] = None, 
                           post_data: bytes = None):
        """处理API请求"""
        try:
            # 调用API处理器
            api_response = handle_api_request(method, path, query_params, post_data)
            
            # 发送JSON响应
            self._send_json_response(api_response)
            
        except Exception as e:
            log_error(f"API请求处理失败: {e}", "HTTP")
            error_response = {
                'status': 'error',
                'message': f'API处理失败: {str(e)}',
                'timestamp': get_timestamp()
            }
            self._send_json_response(error_response, 500)
    
    def _serve_index_page(self):
        """服务主页"""
        try:
            html_content = self._generate_index_html()
            self._send_html_response(html_content)
            
        except Exception as e:
            log_error(f"服务主页失败: {e}", "HTTP")
            self._send_500_error("无法加载主页")
    
    def _serve_html_page(self, filename: str):
        """服务HTML页面"""
        try:
            result = serve_html_file(filename)
            
            if result['success']:
                self._send_html_response(result['content'])
            else:
                status_code = result.get('status_code', 404)
                if status_code == 404:
                    self._send_404_error(result['error'])
                else:
                    self._send_500_error(result['error'])
                    
        except Exception as e:
            log_error(f"服务HTML页面失败 {filename}: {e}", "HTTP")
            self._send_500_error(f"无法加载页面: {filename}")
    
    def _serve_static_file(self, path: str):
        """服务静态文件"""
        try:
            result = serve_static_file(path)
            
            if result['success']:
                content = result['content']
                content_type = result['content_type']
                is_binary = result.get('is_binary', False)
                
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', result.get('cache_control', 'no-cache'))
                self._send_cors_headers()
                self.end_headers()
                
                if is_binary:
                    self.wfile.write(content)
                else:
                    self.wfile.write(safe_encode(content))
                    
                log_success(f"静态文件服务成功: {path}", "HTTP")
            else:
                status_code = result.get('status_code', 404)
                if status_code == 404:
                    self._send_404_error(result['error'])
                else:
                    self._send_500_error(result['error'])
                    
        except Exception as e:
            log_error(f"服务静态文件失败 {path}: {e}", "HTTP")
            self._send_500_error(f"无法加载文件: {path}")
    
    def _serve_directory_listing(self, directory_path: str):
        """服务目录列表"""
        try:
            html_content = generate_directory_listing(directory_path)
            self._send_html_response(html_content)
            
        except Exception as e:
            log_error(f"服务目录列表失败 {directory_path}: {e}", "HTTP")
            self._send_500_error(f"无法生成目录列表: {directory_path}")
    
    def _serve_api_docs(self):
        """服务API文档页面"""
        try:
            docs_result = get_api_documentation()
            
            if docs_result['status'] == 'success':
                docs_data = docs_result['data']
                html_content = self._generate_api_docs_html(docs_data)
                self._send_html_response(html_content)
            else:
                self._send_500_error("无法获取API文档")
                
        except Exception as e:
            log_error(f"服务API文档失败: {e}", "HTTP")
            self._send_500_error("API文档生成失败")
    
    def _send_json_response(self, data: Dict[str, Any], status_code: int = 200):
        """发送JSON响应"""
        try:
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            json_bytes = safe_encode(json_data)
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(json_bytes)))
            self._send_cors_headers()
            self.end_headers()
            
            self.wfile.write(json_bytes)
            
        except Exception as e:
            log_error(f"发送JSON响应失败: {e}", "HTTP")
    
    def _send_html_response(self, html_content: str, status_code: int = 200):
        """发送HTML响应"""
        try:
            html_bytes = safe_encode(html_content)
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html_bytes)))
            self._send_cors_headers()
            self.end_headers()
            
            self.wfile.write(html_bytes)
            
        except Exception as e:
            log_error(f"发送HTML响应失败: {e}", "HTTP")
    
    def _send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def _send_404_error(self, message: str):
        """发送404错误"""
        html_content = self._generate_error_html(404, "页面未找到", message)
        self._send_html_response(html_content, 404)
    
    def _send_500_error(self, message: str):
        """发送500错误"""
        html_content = self._generate_error_html(500, "服务器内部错误", message)
        self._send_html_response(html_content, 500)
    
    def _generate_index_html(self) -> str:
        """生成主页HTML"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎮 扑克识别系统</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        .content {{
            padding: 40px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            border-left: 4px solid #667eea;
            transition: transform 0.3s ease;
        }}
        .card:hover {{
            transform: translateY(-5px);
        }}
        .card h3 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3rem;
        }}
        .card a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        .card a:hover {{
            text-decoration: underline;
        }}
        .api-list {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }}
        .api-item {{
            display: flex;
            align-items: center;
            padding: 10px;
            margin-bottom: 10px;
            background: white;
            border-radius: 5px;
            border-left: 3px solid #667eea;
        }}
        .api-method {{
            background: #667eea;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-right: 15px;
            min-width: 60px;
            text-align: center;
        }}
        .api-path {{
            font-family: 'Consolas', monospace;
            color: #333;
        }}
        .status {{
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #c3e6cb;
            text-align: center;
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 扑克识别系统</h1>
            <p>HTTP服务器 v2.0 - 运行于端口 8000</p>
        </div>
        
        <div class="content">
            <div class="status">
                ✅ 服务器运行正常 | 🕐 启动时间: {get_timestamp()} | 📡 API接口: 19个
            </div>
            
            <div class="section">
                <h2>📋 功能页面</h2>
                <div class="cards">
                    <div class="card">
                        <h3>🎯 位置标记</h3>
                        <p>配置摄像头的扑克牌位置标记</p>
                        <p><a href="/biaoji.html">标记页面 (biaoji.html)</a></p>
                    </div>
                    <div class="card">
                        <h3>🎲 简单标记</h3>
                        <p>简化版的位置标记工具</p>
                        <p><a href="/simple_biaoji.html">简单标记 (simple_biaoji.html)</a></p>
                    </div>
                    <div class="card">
                        <h3>🖼️ 图片管理</h3>
                        <p>查看和管理拍摄的图片文件</p>
                        <p><a href="/image/">图片目录</a></p>
                    </div>
                    <div class="card">
                        <h3>📚 API文档</h3>
                        <p>完整的API接口文档和测试</p>
                        <p><a href="/api-docs">API文档</a></p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>🔗 主要API接口</h2>
                <div class="api-list">
                    <div class="api-item">
                        <span class="api-method">GET</span>
                        <span class="api-path">/api/cameras</span>
                    </div>
                    <div class="api-item">
                        <span class="api-method">GET</span>
                        <span class="api-path">/api/recognition_result</span>
                    </div>
                    <div class="api-item">
                        <span class="api-method">POST</span>
                        <span class="api-path">/api/take_photo</span>
                    </div>
                    <div class="api-item">
                        <span class="api-method">POST</span>
                        <span class="api-path">/api/camera/{{id}}/marks</span>
                    </div>
                    <div class="api-item">
                        <span class="api-method">POST</span>
                        <span class="api-path">/api/recognition_result</span>
                    </div>
                </div>
                <p style="text-align: center; margin-top: 20px;">
                    <a href="/api-docs">查看完整API文档 →</a>
                </p>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    def _generate_api_docs_html(self, docs_data: Dict[str, Any]) -> str:
        """生成API文档HTML"""
        api_info = docs_data.get('api_info', {})
        endpoints = docs_data.get('endpoints', {})
        
        endpoints_html = ""
        for endpoint, description in endpoints.items():
            method = endpoint.split(' ')[0]
            path = endpoint.split(' ', 1)[1] if ' ' in endpoint else endpoint
            
            method_color = {
                'GET': '#28a745',
                'POST': '#007bff', 
                'PUT': '#ffc107',
                'DELETE': '#dc3545'
            }.get(method, '#6c757d')
            
            endpoints_html += f"""
            <div class="api-endpoint">
                <span class="method" style="background-color: {method_color}">{method}</span>
                <code class="path">{path}</code>
                <span class="description">{description}</span>
            </div>"""
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📚 API文档 - 扑克识别系统</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
        .api-info {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .api-endpoint {{ display: flex; align-items: center; padding: 15px; margin-bottom: 10px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #ccc; }}
        .method {{ color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; margin-right: 15px; min-width: 80px; text-align: center; }}
        .path {{ font-family: 'Consolas', monospace; background: #e9ecef; padding: 8px 12px; border-radius: 4px; margin-right: 15px; }}
        .description {{ color: #666; }}
        .back-link {{ display: inline-block; margin-bottom: 20px; color: #007bff; text-decoration: none; }}
        .back-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← 返回首页</a>
        <h1>📚 {api_info.get('name', 'API文档')}</h1>
        
        <div class="api-info">
            <h3>API信息</h3>
            <p><strong>版本:</strong> {api_info.get('version', 'N/A')}</p>
            <p><strong>描述:</strong> {api_info.get('description', 'N/A')}</p>
            <p><strong>总接口数:</strong> {len(endpoints)} 个</p>
        </div>
        
        <h2>📡 API接口列表</h2>
        {endpoints_html}
    </div>
</body>
</html>"""
    
    def _generate_error_html(self, code: int, title: str, message: str) -> str:
        """生成错误页面HTML"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>错误 {code}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 40px; text-align: center; background: #f5f5f5; }}
        .error-container {{ max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .error-code {{ font-size: 4rem; color: #e74c3c; font-weight: bold; margin-bottom: 20px; }}
        .error-title {{ font-size: 1.5rem; color: #333; margin-bottom: 15px; }}
        .error-message {{ color: #666; margin-bottom: 30px; }}
        .back-link {{ color: #3498db; text-decoration: none; font-weight: 500; }}
        .back-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">{code}</div>
        <div class="error-title">{title}</div>
        <div class="error-message">{message}</div>
        <a href="/" class="back-link">← 返回首页</a>
    </div>
</body>
</html>"""
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        return  # 禁用默认日志，使用我们自己的日志系统

class HTTPServerManager:
    """HTTP服务器管理器"""
    
    def __init__(self, host: str = 'localhost', port: int = 8000):
        """初始化HTTP服务器管理器"""
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
        
        log_info("HTTP服务器管理器初始化完成", "HTTP")
    
    def start_server(self):
        """启动HTTP服务器"""
        try:
            # 创建服务器实例
            self.server = HTTPServer((self.host, self.port), HTTPRequestHandler)
            
            # 在单独线程中运行服务器
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.running = True
            self.server_thread.start()
            
            log_success(f"HTTP服务器启动成功: http://{self.host}:{self.port}", "HTTP")
            return True
            
        except Exception as e:
            log_error(f"HTTP服务器启动失败: {e}", "HTTP")
            return False
    
    def _run_server(self):
        """运行服务器"""
        try:
            self.server.serve_forever()
        except Exception as e:
            if self.running:
                log_error(f"HTTP服务器运行异常: {e}", "HTTP")
    
    def stop_server(self):
        """停止HTTP服务器"""
        try:
            if self.server:
                self.running = False
                self.server.shutdown()
                self.server.server_close()
                
                if self.server_thread and self.server_thread.is_alive():
                    self.server_thread.join(timeout=5)
                
                log_success("HTTP服务器已停止", "HTTP")
                return True
        except Exception as e:
            log_error(f"停止HTTP服务器失败: {e}", "HTTP")
            return False
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        return {
            'host': self.host,
            'port': self.port,
            'running': self.running,
            'url': f"http://{self.host}:{self.port}",
            'thread_alive': self.server_thread.is_alive() if self.server_thread else False
        }

# 创建全局服务器实例
http_server_manager = HTTPServerManager()

# 导出主要函数
def start_http_server(host: str = 'localhost', port: int = 8000) -> bool:
    """启动HTTP服务器"""
    global http_server_manager
    http_server_manager = HTTPServerManager(host, port)
    return http_server_manager.start_server()

def stop_http_server() -> bool:
    """停止HTTP服务器"""
    return http_server_manager.stop_server()

def get_server_info() -> Dict[str, Any]:
    """获取服务器信息"""
    return http_server_manager.get_server_info()

def run_server_blocking(host: str = 'localhost', port: int = 8000):
    """以阻塞模式运行服务器"""
    try:
        server = HTTPServer((host, port), HTTPRequestHandler)
        
        print("🚀 扑克识别系统 HTTP 服务器")
        print("=" * 50)
        print(f"📡 服务地址: http://{host}:{port}")
        print(f"🏠 主页: http://{host}:{port}/")
        print(f"📋 标记页面: http://{host}:{port}/biaoji.html")
        print(f"🎯 API文档: http://{host}:{port}/api-docs")
        print(f"🖼️ 图片目录: http://{host}:{port}/image/")
        print("=" * 50)
        print("💡 功能说明:")
        print("1. 浏览器访问主页查看所有功能")
        print("2. API接口支持GET/POST/PUT/DELETE")
        print("3. 自动处理CORS跨域请求")
        print("4. 按 Ctrl+C 停止服务器")
        print("=" * 50)
        
        log_success(f"HTTP服务器启动成功: http://{host}:{port}", "HTTP")
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        server.shutdown()
        server.server_close()
    except Exception as e:
        log_error(f"HTTP服务器运行失败: {e}", "HTTP")

if __name__ == "__main__":
    # 直接运行HTTP服务器
    import sys
    
    host = 'localhost'
    port = 8000
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ 端口号格式错误，使用默认端口 8000")
    
    if len(sys.argv) > 2:
        host = sys.argv[2]
    
    # 运行服务器
    try:
        run_server_blocking(host, port)
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)