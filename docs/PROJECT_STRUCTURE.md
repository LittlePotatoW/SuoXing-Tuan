# 工业检测平台 — 项目结构

```
SuoXing-Tuan/
├── backend/                         # Python 后端
│   ├── communication/               # 硬件通信层（相机、激光雷达、串口）
│   ├── pipeline/                    # 数据处理（图像预处理、点云处理、多传感器融合）
│   ├── inference/                   # AI 推理引擎
│   ├── reconstruction/              # 三维重建
│   ├── gateway/                     # API 网关（FastAPI，前端唯一入口）
│   ├── common/                      # 内部工具库（日志、配置加载、类型、消息队列）
│   ├── config/                      # 配置文件（YAML）
│   └── tests/                       # 测试
│
├── frontend/                        # Electron + Vue 3 桌面应用
│   ├── electron/                    # Electron 主进程（窗口、系统托盘、IPC）
│   └── src/                         # Vue 3 渲染进程（界面）
│
├── model-training/                  # 模型训练（独立于运行时）
│   ├── data/                        # 数据集管理
│   ├── models/                      # 模型定义（PyTorch）
│   ├── training/                    # 训练脚本
│   ├── evaluation/                  # 模型评估
│   ├── export/                      # 模型导出（ONNX / TensorRT）
│   ├── configs/                     # 实验配置
│   └── registry/                    # 模型仓库
│
└── docs/                            # 项目文档
```

## 目录说明

### `backend/`
Python 后端，平台的"大脑"。`communication/` 对接硬件拿数据，`pipeline/` 处理数据（去噪、对齐、融合），`inference/` 跑 AI 模型做检测，`reconstruction/` 做三维重建，`gateway/` 是前端唯一入口（REST + WebSocket）。模块间通过消息队列异步解耦。详见 [README-PEOPLE.md](../backend/README-PEOPLE.md)。

### `frontend/`
Electron + Vue 3 桌面应用。`electron/` 管桌面窗口和系统交互，`src/` 管界面。三维渲染用 WebGL/WebGPU，通过 WebSocket 接收后端实时数据。详见 [README-PEOPLE.md](../frontend/README-PEOPLE.md)。

### `model-training/`
和运行时分离的模型训练模块。负责数据管理、模型训练、评估、导出（ONNX/TensorRT）。产出的模型放 `registry/`，后端 `inference/` 从这里加载。详见 [README-PEOPLE.md](../model-training/README-PEOPLE.md)。

### `docs/`
项目文档，包含架构设计和结构说明。详见 [README-PEOPLE.md](../docs/README-PEOPLE.md)。
