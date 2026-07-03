# 缩星团 — 工业检测平台

基于 AI 的工业视觉检测与三维重建平台，集成硬件通信、实时推理、3D Gaussian Splatting 重建和桌面端可视化。

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python · FastAPI · NATS/Redis Streams · ONNX/TensorRT |
| **前端** | Electron · Vue 3 · WebGL/WebGPU |
| **模型训练** | PyTorch · ONNX · TensorRT |
| **通信** | REST API · WebSocket · gRPC |

## 项目结构

```
SuoXing-Tuan/
├── backend/               # Python 后端（硬件通信、数据处理、AI推理、三维重建、API网关）
├── frontend/              # Electron + Vue 3 桌面应用
├── model-training/        # 模型训练模块（独立于运行时）
└── docs/                  # 架构设计与项目文档
```

## 核心功能

- **多传感器接入** — 统一接口接入工业相机、激光雷达等硬件，消息队列解耦上下游
- **AI 缺陷检测** — 支持 YOLO / Transformer / 多模态模型热插拔切换，无需重启服务
- **三维重建** — 基于 3D Gaussian Splatting 的实时场景重建与渲染
- **实时推送** — WebSocket 低延迟推送检测结果与三维场景更新到前端
- **离线回放** — 前端可直接加载本地数据包，离线模式下后端无需启动

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn gateway.main:app --reload

# 前端
cd frontend
npm install
npm run dev

# 模型训练
cd model-training
pip install -r requirements.txt
python training/train.py --config configs/default.yaml
```

## 文档

- [系统架构设计](docs/ARCHITECTURE.md)
- [项目结构说明](docs/PROJECT_STRUCTURE.md)
