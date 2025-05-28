🎮 扑克识别系统 2.0
📋 项目简介
扑克识别系统 2.0 是一个基于计算机视觉和深度学习的智能扑克牌识别解决方案。系统支持多种识别引擎，可以准确识别扑克牌的花色和点数，并实时推送识别结果。
✨ 主要特性

🧠 多引擎识别：支持 YOLOv8、OCR、混合识别等多种算法
📷 多摄像头支持：可同时管理多个 RTSP 摄像头
⚡ 实时处理：快速拍照、裁剪、识别、推送全流程
🔧 灵活配置：通过 JSON 配置文件轻松切换识别引擎
🌐 Web 管理：提供完整的 Web 界面进行配置和监控
📡 WebSocket 推送：实时推送识别结果到外部系统
🎯 位置标记：支持扑克牌位置的可视化标记和管理

🏗️ 系统架构
扑克识别系统 2.0
├── 📷 图像采集层
│   ├── RTSP 摄像头管理
│   ├── 图像拍照控制
│   └── 图像预处理
├── 🧠 识别引擎层
│   ├── YOLOv8 深度学习引擎
│   ├── OCR 字符识别引擎
│   ├── 混合识别引擎
│   └── OpenCV 传统视觉引擎
├── 🔄 业务逻辑层
│   ├── 识别结果管理
│   ├── 配置管理
│   └── 状态管理
├── 🌐 服务接口层
│   ├── HTTP API 服务
│   ├── WebSocket 推送
│   └── 静态文件服务
└── 💾 数据存储层
    ├── 配置文件存储
    ├── 识别结果存储
    └── 历史记录存储
📁 项目结构
poker_recognition_system/
├── 📄 README.md                    # 项目说明文档
├── 🚀 main.py                      # 主程序入口（空文件）
├── 🎯 biaoji.py                    # 位置标记程序
├── 👁️ see.py                       # 识别测试程序
├── 🔄 tui.py                       # 实时推送程序
├── ⚙️ config_loader.py             # 配置加载器
├── 🔒 state_manager.py             # 状态管理器
├── 📂 src/                         # 源代码目录
│   ├── 🧠 core/                    # 核心模块
│   │   ├── utils.py               # 工具函数
│   │   ├── config_manager.py      # 配置管理
│   │   ├── mark_manager.py        # 标记管理
│   │   ├── recognition_manager.py # 识别结果管理
│   │   └── state_manager.py       # 状态管理
│   ├── 🔧 processors/             # 处理器模块
│   │   ├── photo_controller.py    # 拍照控制器
│   │   ├── image_cutter.py        # 图像裁剪器
│   │   ├── poker_recognizer.py    # YOLO识别器（兼容）
│   │   ├── poker_ocr.py          # OCR识别器（兼容）
│   │   ├── poker_paddle_ocr.py   # PaddleOCR识别器（兼容）
│   │   ├── 🔄 recognition_manager.py # 【新】识别管理器
│   │   ├── 🔗 recognition_interface.py # 【新】统一接口
│   │   ├── 🚀 engines/            # 【新】识别引擎
│   │   │   ├── base_engine.py     # 引擎基类
│   │   │   ├── yolo_engine.py     # YOLO引擎
│   │   │   ├── ocr_engine.py      # OCR引擎
│   │   │   ├── hybrid_engine.py   # 混合引擎
│   │   │   └── opencv_engine.py   # OpenCV引擎
│   │   ├── 🛠️ utils/              # 【新】处理工具
│   │   │   ├── image_preprocessor.py # 图像预处理
│   │   │   ├── result_normalizer.py  # 结果标准化
│   │   │   └── recognition_config_loader.py # 配置加载
│   │   └── ⚙️ config/             # 【新】识别配置
│   │       └── recognition_config.json # 识别引擎配置
│   ├── 🌐 servers/                # 服务器模块
│   │   ├── http_server.py         # HTTP服务器
│   │   ├── api_handler.py         # API处理器
│   │   └── static_handler.py      # 静态文件处理
│   ├── 📡 clients/                # 客户端模块
│   │   └── websocket_client.py    # WebSocket推送客户端
│   └── 🔗 workflows/              # 工作流模块
│       └── recognition_workflow.py # 识别工作流
├── 📁 config/                     # 配置文件目录
│   └── camera.json               # 摄像头配置
├── 🖼️ image/                      # 图片目录
│   └── cut/                      # 裁剪图片目录
├── 📊 result/                     # 结果目录
│   ├── history/                  # 历史记录
│   ├── logs/                     # 日志文件
│   └── state/                    # 状态文件
└── 🌐 web/                       # Web界面（如果有）
    └── templates/                # HTML模板
🚀 快速开始
1. 环境要求

Python 3.8+
FFmpeg（用于RTSP视频流处理）
可选依赖：

PyTorch + Ultralytics（YOLOv8）
PaddleOCR 或 EasyOCR
OpenCV



2. 安装依赖
bash# 基础依赖
pip install opencv-python pillow numpy

# YOLO识别引擎
pip install torch ultralytics

# OCR识别引擎（选择一个）
pip install paddlepaddle paddleocr  # PaddleOCR
pip install easyocr                 # EasyOCR

# WebSocket推送
pip install websockets

# HTTP服务器（使用内置库，无需额外安装）
3. 配置系统
配置摄像头
编辑 config/camera.json：
json{
  "cameras": [
    {
      "id": "001",
      "name": "百家乐1号",
      "ip": "192.168.1.100",
      "username": "admin",
      "password": "password",
      "enabled": true
    }
  ]
}
配置识别引擎
编辑 src/processors/config/recognition_config.json：
json{
  "recognition": {
    "default_engine": "hybrid",
    "engines": {
      "yolo": {
        "enabled": true,
        "model_path": "src/config/yolov8/best.pt"
      },
      "ocr": {
        "enabled": true,
        "provider": "paddle"
      },
      "hybrid": {
        "enabled": true,
        "primary_engine": "yolo",
        "secondary_engine": "ocr"
      }
    }
  }
}
4. 运行程序
标记位置
bashpython biaoji.py
# 在Web界面中标记扑克牌位置
# 访问: http://localhost:8000/biaoji.html
测试识别
bashpython see.py
# 单次完整测试流程：拍照→裁剪→识别→显示结果

python see.py --auto --interval 5
# 自动循环测试，间隔5秒
实时推送
bashpython tui.py
# 实时循环：拍照→裁剪→识别→推送

python tui.py --interval 3 --no-websocket
# 3秒间隔，禁用WebSocket推送
🔧 识别引擎配置
引擎类型

YOLOv8引擎 (yolo)

基于深度学习的端到端识别
高准确率，适合完整扑克牌识别
需要预训练模型文件


OCR引擎 (ocr)

基于光学字符识别
适合识别扑克牌点数
支持PaddleOCR和EasyOCR


混合引擎 (hybrid)

结合YOLO和OCR的优势
YOLO识别花色，OCR识别点数
最高准确率的推荐方案


OpenCV引擎 (opencv)

传统计算机视觉方法
基于模板匹配、轮廓检测
轻量级，无需深度学习模型



引擎切换
通过修改 recognition_config.json 中的 default_engine 字段：
json{
  "recognition": {
    "default_engine": "hybrid",  // yolo, ocr, hybrid, opencv
    "fallback_engine": "yolo"
  }
}
🌐 Web API 接口
启动HTTP服务器
bashpython -m src.servers.http_server
# 访问: http://localhost:8000
主要API接口
接口方法描述/api/camerasGET获取摄像头列表/api/take_photoPOST拍照/api/camera/{id}/marksPOST保存位置标记/api/recognition_resultGET获取识别结果/api/recognition_resultPOST接收识别结果/api/push/configGET/POST推送配置管理
示例调用
bash# 拍照
curl -X POST http://localhost:8000/api/take_photo \
  -H "Content-Type: application/json" \
  -d '{"camera_id": "001"}'

# 获取识别结果
curl http://localhost:8000/api/recognition_result
📡 WebSocket 推送
系统支持将识别结果实时推送到外部WebSocket服务器：
json{
  "type": "recognition_result_update",
  "camera_id": "001",
  "positions": {
    "zhuang_1": {"suit": "hearts", "rank": "A"},
    "zhuang_2": {"suit": "spades", "rank": "K"},
    "xian_1": {"suit": "diamonds", "rank": "Q"}
  },
  "timestamp": "2025-05-28T12:00:00"
}
🎯 使用场景
1. 位置标记 (biaoji.py)

使用Web界面标记扑克牌位置
支持6个标准位置：庄1、庄2、庄3、闲1、闲2、闲3
标记数据自动保存到配置文件

2. 识别测试 (see.py)

完整测试识别流程
支持单次测试和循环测试
详细显示每个步骤的耗时和结果

3. 实时推送 (tui.py)

生产环境使用的实时识别系统
轮询处理多个摄像头
自动推送结果到外部系统
支持状态监控和统计

🔍 故障排除
常见问题

FFmpeg不可用
bash# Windows: 下载FFmpeg并添加到PATH
# Linux: sudo apt-get install ffmpeg
# macOS: brew install ffmpeg

RTSP连接失败

检查摄像头IP地址和端口
验证用户名和密码
确认网络连接


识别准确率低

调整摄像头角度和位置
重新标记扑克牌位置
尝试不同的识别引擎
调整引擎参数


WebSocket推送失败

检查服务器地址和端口
验证网络连接
查看推送日志



日志文件
系统日志保存在以下位置：

识别日志：result/logs/recognition.log
系统日志：控制台输出
错误日志：result/logs/error.log

🤝 贡献指南
欢迎提交Issue和Pull Request来改进项目！
开发环境搭建
bashgit clone <项目地址>
cd poker_recognition_system
pip install -r requirements.txt
添加新的识别引擎

在 src/processors/engines/ 下创建新引擎文件
继承 BaseEngine 类
实现 recognize() 方法
在配置文件中添加引擎配置
注册到引擎管理器

📄 许可证
本项目采用 MIT 许可证，详见 LICENSE 文件。
📞 联系方式
如有问题或建议，请通过以下方式联系：

提交 Issue
发送邮件
项目讨论区


🎮 扑克识别系统 2.0 - 让AI识别扑克牌变得简单高效！