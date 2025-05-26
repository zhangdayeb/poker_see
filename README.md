# 扑克识别系统 (Poker Recognition System)

## 项目结构

```
POKER/
├── config/
│   ├── yolov8/
│   │   └── best.pt                    # YOLO模型权重文件
│   └── camera.json                    # 摄像头配置文件
│
├── data/
│   ├── images/                        # 图像数据
│   │   ├── cut/                      # 裁剪后的图像
│   │   └── raw/                      # 原始图像
│   ├── logs/                         # 日志文件
│   ├── results/                      # 识别结果
│   └── script_backup/                # 脚本备份
│       ├── cut.py
│       └── see.py
│
├── src/                              # 源代码目录
│
├── core/                             # 核心模块
│   ├── __init__.py
│   ├── config_manager.py             # 配置管理器
│   ├── mark_manager.py               # 标记管理器
│   ├── recognition_manager.py        # 识别管理器
│   └── utils.py                      # 工具函数
│
├── processors/                       # 处理器模块
│   ├── __init__.py
│   ├── image_cutter.py              # 图像裁剪处理器
│   ├── photo_controller.py          # 照片控制器
│   └── poker_recognizer.py          # 扑克识别器
│
├── servers/                          # 服务器模块
│   ├── __init__.py
│   ├── api_handler.py               # API处理器
│   ├── http_server.py               # HTTP服务器
│   ├── static_handler.py            # 静态文件处理器
│   └── websocket_server.py          # WebSocket服务器
│
├── websocket/                        # WebSocket相关
│   ├── __init__.py
│   ├── connection_manager.py        # 连接管理器
│   └── dealer_websocket.py          # 发牌员WebSocket
│
├── workflows/                        # 工作流模块
│   ├── __init__.py
│   ├── recognition_workflow.py      # 识别工作流
│   └── __init__.py
│
├── tests/                           # 测试模块
│   ├── __init__.py
│   └── web/                        # Web测试
│
├── static/                          # 静态资源
│   ├── css/                        # CSS样式文件
│   ├── images/                     # 静态图像资源
│   └── js/                         # JavaScript文件
│
├── templates/                       # 模板文件
│   ├── biuoji.html                 # 标记页面模板
│   └── index.html                  # 主页模板
│
├── main.py                         # 主程序入口
├── README.md                       # 项目说明文档
└── requirements.txt                # Python依赖包列表
```

pip install -r requirements.txt

## 系统架构说明

### 核心功能模块

1. **配置管理** (`config_manager.py`)
   - 管理摄像头配置
   - 系统参数设置
   - 调试模式控制

2. **图像处理** (`processors/`)
   - `image_cutter.py`: 图像裁剪和预处理
   - `photo_controller.py`: 照片拍摄控制
   - `poker_recognizer.py`: 扑克牌识别核心

3. **识别管理** (`recognition_manager.py`)
   - 协调各个识别组件
   - 管理识别流程
   - 结果验证和处理

4. **网络服务** (`servers/`)
   - HTTP服务器提供Web界面
   - WebSocket实现实时通信
   - API接口处理外部请求

5. **工作流管理** (`workflows/`)
   - 识别工作流程编排
   - 自动化处理流程

### 配置文件说明

**camera.json** 主要配置项：
- `system`: 系统级设置（FFmpeg路径、超时、重试等）
- `output`: 输出配置（目录、格式、质量等）
- `debug`: 调试选项（日志级别、保存选项等）
- `cameras`: 摄像头配置（IP、用户名、密码、流地址等）

### 数据流向

```
摄像头输入 → 图像预处理 → YOLO识别 → 结果验证 → WebSocket推送 → 前端显示
     ↓
  图像保存 → 日志记录 → 结果存储
```

### 主要技术栈

- **后端**: Python
- **机器学习**: YOLOv8
- **Web服务**: HTTP + WebSocket
- **前端**: HTML + JavaScript + CSS
- **图像处理**: OpenCV (推测)
- **配置管理**: JSON

## 快速开始

1. 安装依赖：`pip install -r requirements.txt`
2. 配置摄像头：编辑 `config/camera.json`
3. 运行主程序：`python main.py`
4. 访问Web界面进行操作

## 开发说明

- 核心业务逻辑在 `core/` 目录
- 新增处理器请在 `processors/` 目录添加
- Web相关功能在 `servers/` 和 `templates/` 目录
- 测试文件统一放在 `tests/` 目录

---

*此文档基于项目目录结构生成，如需详细了解具体模块功能，请查看对应源代码文件。*