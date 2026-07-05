# 后端设计文档

## 1. 概述

后端是平台的"计算核心"。V1 阶段只负责 **AI 推理**（缺陷检测）。三维重建在 V2 实现。

**核心原则**：前端是纯展示层，不加载模型、不运行推理。所有计算都在后端完成。

## 2. 技术选型

| 技术 | 用途 |
|------|------|
| Python 3.10+ | 主语言 |
| FastAPI | API 网关 (REST + WebSocket) |
| Ultralytics YOLO | 推理引擎 (支持 .pt / .onnx / .engine) |
| NumPy / Pillow | 图像处理 |

## 3. 目录结构（V1 极简）

```
backend/
├── main.py           # FastAPI 应用（全部路由 + WebSocket 都在这一个文件）
├── inference.py      # YOLO 推理引擎（加载、推理、卸载）
├── requirements.txt  # Python 依赖
└── models/           # 上传的 .pt 模型文件存放（gitignored）
```

后续功能增加时再拆分目录。

## 4. API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 + 已加载模型信息 |
| POST | `/api/inference` | 上传图片，后端推理，返回检测结果 |
| POST | `/api/model/load` | 上传 .pt 文件，后端热加载模型 |
| WS | `/ws/realtime` | WebSocket 实时通信 |

### 推理请求流程

```
前端 POST /api/inference (image file)
  → 后端读取图片 → numpy 数组 (BGR)
  → engine.infer(image_array)
  → 返回 InferenceResponse JSON
```

### 模型热加载流程

```
前端 POST /api/model/load (model file)
  → 后端保存到 models/ 目录
  → engine.load(model_path)  # 自动卸载旧模型
  → 返回加载状态
```

## 5. 推理引擎

`inference.py` 中的 `InferenceEngine` 类：
- `load(path, conf, iou)` — 加载模型（拔插式：自动卸载旧模型）
- `infer(image_array)` — 推理单张图像，返回 `InferenceResponse`
- `unload()` — 卸载模型释放显存
- 支持 .pt / .onnx / .engine 格式

## 6. V2 计划

- 多模型注册表（同时管理多个引擎）
- 三维重建引擎 (Gaussian Splatting)
- 硬件通信层（工业相机、激光雷达接入）
- 内部消息队列解耦
