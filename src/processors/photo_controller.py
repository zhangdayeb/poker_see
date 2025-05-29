#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单拍照工具 - 根据摄像头ID进行RTSP拍照
用法: python src/processors/photo_controller.py --camera 001
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path

def setup_project_paths():
   """设置项目路径"""
   current_file = Path(__file__).resolve()
   project_root = current_file
   while project_root.parent != project_root:
       if (project_root / "main.py").exists():
           break
       project_root = project_root.parent
   
   project_root_str = str(project_root)
   if project_root_str not in sys.path:
       sys.path.insert(0, project_root_str)
   
   return project_root

def load_camera_config(camera_id: str) -> dict:
   """加载摄像头配置"""
   try:
       project_root = setup_project_paths()
       config_file = project_root / "src" / "config" / "camera.json"
       
       if not config_file.exists():
           print(f"❌ 配置文件不存在: {config_file}")
           return None
       
       with open(config_file, 'r', encoding='utf-8') as f:
           config = json.load(f)
       
       # 查找指定摄像头
       for camera in config.get('cameras', []):
           if camera.get('id') == camera_id:
               return camera
       
       print(f"❌ 摄像头 {camera_id} 配置不存在")
       return None
       
   except Exception as e:
       print(f"❌ 读取配置失败: {e}")
       return None

def build_rtsp_url(camera_config: dict) -> str:
   """构建RTSP URL"""
   username = camera_config.get('username', 'admin')
   password = camera_config.get('password', '')
   ip = camera_config.get('ip', '')
   port = camera_config.get('port', 554)
   stream_path = camera_config.get('stream_path', '/Streaming/Channels/101')
   
   return f"rtsp://{username}:{password}@{ip}:{port}{stream_path}"

def take_photo(camera_id: str) -> bool:
   """拍照主函数"""
   print("📷 拍照工具")
   
   # 1. 加载配置
   camera_config = load_camera_config(camera_id)
   if not camera_config:
       return False
   
   # 检查摄像头是否启用
   if not camera_config.get('enabled', True):
       print(f"❌ 摄像头 {camera_id} 已禁用")
       return False
   
   camera_name = camera_config.get('name', f'摄像头{camera_id}')
   print(f"摄像头: {camera_id} ({camera_name})")
   
   # 2. 构建RTSP URL
   rtsp_url = build_rtsp_url(camera_config)
   
   # 3. 设置输出路径
   project_root = setup_project_paths()
   image_dir = project_root / "src" / "image"
   image_dir.mkdir(parents=True, exist_ok=True)
   
   filename = f"camera_{camera_id}.png"
   output_path = image_dir / filename
   
   # 4. 执行FFmpeg命令
   print("正在拍照...")
   
   cmd = [
       'ffmpeg',
       '-rtsp_transport', 'tcp',
       '-i', rtsp_url,
       '-vframes', '1',
       '-y',  # 覆盖现有文件
       str(output_path)
   ]
   
   try:
       result = subprocess.run(
           cmd,
           capture_output=True,
           text=True,
           timeout=20  # 20秒超时
       )
       
       # 5. 检查结果
       if result.returncode == 0 and output_path.exists():
           file_size = output_path.stat().st_size
           if file_size > 0:
               size_str = f"{file_size/1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB"
               print(f"✅ 拍照成功: {filename} ({size_str})")
               return True
           else:
               print("❌ 拍照文件为空")
               output_path.unlink(missing_ok=True)
               return False
       else:
           error_msg = result.stderr.strip() if result.stderr else "FFmpeg执行失败"
           print(f"❌ 拍照失败: {error_msg}")
           return False
           
   except subprocess.TimeoutExpired:
       print("❌ 拍照超时，请检查网络连接和摄像头状态")
       return False
   except FileNotFoundError:
       print("❌ ffmpeg命令不存在，请确保已安装FFmpeg")
       return False
   except Exception as e:
       print(f"❌ 拍照异常: {e}")
       return False

def main():
   """主函数"""
   parser = argparse.ArgumentParser(
       description='简单拍照工具 - 根据摄像头ID进行RTSP拍照'
   )
   parser.add_argument('--camera', type=str, required=True, 
                      help='摄像头ID (如: 001)')
   
   args = parser.parse_args()
   
   # 执行拍照
   success = take_photo(args.camera)
   
   # 根据结果退出
   sys.exit(0 if success else 1)

if __name__ == "__main__":
   main()