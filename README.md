# 🎮 扑克识别系统 (Poker Recognition System)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.1.0-orange.svg)](CHANGELOG.md)

一个完整的扑克牌识别系统，支持RTSP摄像头拍照、位置标记、图像识别、结果推送等功能。

## 📋 功能特性

### 🎯 核心功能
- **RTSP摄像头拍照** - 支持海康威视等主流网络摄像头
- **智能位置标记** - 可视化标记6个扑克牌位置（庄1-3，闲1-3）
- **多种识别算法** - 支持YOLOv8、EasyOCR、PaddleOCR识别
- **实时结果推送** - 通过WebSocket推送识别结果
- **Web管理界面** - 完整的HTTP服务和管理页面

### 🛠️ 技术特性
- **RESTful API** - 19个完整的API接口
- **模块化架构** - 清晰的代码结构，易于扩展
- **配置管理** - JSON配置文件，支持热重载
- **日志系统** - 完整的操作日志和错误追踪
- **数据持久化** - 识别历史和配置数据保存

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Windows/Linux/macOS
- 网络摄像头（可选）

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/your-repo/poker-recognition-system.git
   cd poker-recognition-system
   ```

2. **安装依赖**
   ```bash
   # 基础依赖
   pip install -r requirements.txt
   
   # 识别功能依赖（可选）
   pip install ultralytics  # YOLOv8支持
   pip install easyocr      # EasyOCR支持
   pip install paddlepaddle paddleocr  # PaddleOCR支持
   
   # WebSocket推送依赖（可选）
   pip install websockets
   ```

3. **启动系统**
   ```bash
   python main.py
   ```

4. **访问界面**
   - 主页：http://localhost:8000/
   - 标记页面：http://localhost:8000/biaoji.html
   - API文档：http://localhost:8000/api-docs

## 📖 使用指南

### 基本配置

1. **摄像头配置** (`src/config/camera.json`)
   ```json
   {
     "cameras": [
       {
         "id": "001",
         "name": "主桌摄像头",
         "ip": "192.168.1.100",
         "username": "admin",
         "password": "your-password",
         "port": 554,
         "stream_path": "/Streaming/Channels/101"
       }
     ]
   }
   ```

2. **推送配置** (`result/push_config.json`)
   ```json
   {
     "websocket": {
       "enabled": true,
       "server_url": "ws://localhost:8001",
       "client_id": "python_client_001"
     }
   }
   ```

### 位置标记

1. 访问标记页面：http://localhost:8000/biaoji.html
2. 选择摄像头并拍照
3. 点击位置按钮（庄1-3，闲1-3）
4. 在图片上拖拽选择扑克牌区域
5. 保存标记数据

### API使用

```bash
# 获取所有摄像头
curl http://localhost:8000/api/cameras

# 拍照
curl -X POST http://localhost:8000/api/take_photo \
  -H "Content-Type: application/json" \
  -d '{"camera_id": "001"}'

# 保存标记
curl -X POST http://localhost:8000/api/camera/001/marks \
  -H "Content-Type: application/json" \
  -d '{"marks": {"zhuang_1": {"x": 100, "y": 150, "width": 60, "height": 80}}}'

# 获取识别结果
curl http://localhost:8000/api/recognition_result
```

## 🏗️ 项目结构

```
poker-recognition-system/
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖清单
├── README.md              # 项目说明
├── config/                # 配置文件目录
│   └── camera.json        # 摄像头配置
├── src/                   # 源代码目录
│   ├── core/              # 核心模块
│   │   ├── utils.py       # 工具函数
│   │   ├── config_manager.py    # 配置管理
│   │   ├── mark_manager.py      # 标记管理
│   │   └── recognition_manager.py # 识别管理
│   ├── processors/        # 处理器模块
│   │   ├── photo_controller.py  # 拍照控制
│   │   ├── image_cutter.py      # 图像裁剪
│   │   ├── poker_recognizer.py  # YOLO识别
│   │   ├── poker_ocr.py         # EasyOCR识别
│   │   └── poker_paddle_ocr.py  # PaddleOCR识别
│   ├── servers/           # 服务器模块
│   │   ├── http_server.py       # HTTP服务器
│   │   ├── api_handler.py       # API处理
│   │   └── static_handler.py    # 静态文件
│   ├── clients/           # 客户端模块
│   │   └── websocket_client.py  # WebSocket客户端
│   └── workflows/         # 工作流模块
├── web/templates/         # 网页模板
│   └── biaoji.html        # 标记页面
├── image/                 # 图片存储目录
├── result/                # 结果存储目录
└── logs/                  # 日志文件目录
```

## 🔧 API文档

### 摄像头管理
- `GET /api/cameras` - 获取所有摄像头
- `GET /api/camera/{id}` - 获取指定摄像头
- `POST /api/camera/add` - 添加摄像头
- `PUT /api/camera/{id}` - 更新摄像头
- `DELETE /api/camera/{id}` - 删除摄像头

### 拍照功能
- `POST /api/take_photo` - 摄像头拍照
- `GET /api/photo/status` - 获取拍照状态
- `GET /api/photos` - 列出图片文件

### 标记管理
- `POST /api/camera/{id}/marks` - 保存摄像头标记
- `POST /api/save_marks` - 批量保存标记
- `GET /api/marks/statistics` - 获取标记统计

### 识别结果
- `GET /api/recognition_result` - 获取最新识别结果
- `POST /api/recognition_result` - 接收识别结果
- `POST /api/push/manual` - 手动推送结果

### 系统管理
- `GET /api/system/info` - 获取系统信息
- `GET /api/system/statistics` - 获取系统统计
- `GET /api/config/status` - 获取配置状态

## 🧪 开发与测试

### 开发环境设置
```bash
# 开发模式启动
python main.py --host 0.0.0.0 --http-port 8080

# 检查项目结构
python main.py --check-paths

# 查看帮助
python main.py --help
```

### 单元测试
```bash
# 测试各个模块
python src/core/config_manager.py
python src/core/mark_manager.py
python src/processors/photo_controller.py
python src/servers/api_handler.py
```

### 识别功能测试
```bash
# YOLOv8识别测试
python src/processors/poker_recognizer.py image/camera_001.png

# OCR识别测试
python src/processors/poker_ocr.py image/cut/camera_001_zhuang_1_left.png

# 图像裁剪测试
python src/processors/image_cutter.py image/camera_001.png
```

## 🔍 故障排除

### 常见问题

1. **模块导入错误**
   ```bash
   # 检查Python路径
   python main.py --check-paths
   ```

2. **摄像头连接失败**
   - 检查IP地址和端口
   - 验证用户名密码
   - 确认网络连通性

3. **FFmpeg未找到**
   ```bash
   # Windows
   # 下载FFmpeg并添加到PATH环境变量
   
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # CentOS/RHEL
   sudo yum install ffmpeg
   ```

4. **识别库安装问题**
   ```bash
   # 如果CUDA可用，安装GPU版本
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

### 日志查看
```bash
# 实时查看日志
tail -f logs/system.log

# 查看错误日志
grep "ERROR" logs/system.log
```

## 🚀 部署说明

### Docker部署
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "main.py", "--host", "0.0.0.0"]
```

### 生产环境
```bash
# 使用gunicorn部署（需要额外配置）
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📝 更新日志

### v2.1.0 (2025-05-28)
- ✨ 新增WebSocket推送功能
- 🔧 优化模块化架构
- 🐛 修复标记数据保存问题
- 📚 完善API文档

### v2.0.0 (2025-05-25)
- 🎯 重构整体架构
- ✨ 新增多种识别算法支持
- 🌐 完善Web管理界面
- 🔧 优化配置管理系统

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 项目主页: [GitHub Repository](https://github.com/your-repo/poker-recognition-system)
- 问题报告: [Issues](https://github.com/your-repo/poker-recognition-system/issues)
- 技术文档: [Wiki](https://github.com/your-repo/poker-recognition-system/wiki)

## 🙏 致谢

- [YOLOv8](https://github.com/ultralytics/ultralytics) - 目标检测模型
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - 文字识别库
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - 飞桨OCR工具
- [FFmpeg](https://ffmpeg.org/) - 多媒体处理框架

---

⭐ 如果这个项目对你有帮助，请给它一个星标！