# SuoXing-Tuan — 隧道病害检测平台

基于 AI 的隧道表面缺陷检测与三维重建平台，支持实时数据采集、YOLO 裂缝识别、LiDAR-相机融合重建和 Web 端可视化。

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python · FastAPI · Open3D (Poisson 重建) · YOLO (ultralytics) |
| **前端** | Vue 3 · TypeScript · Vite · Three.js |
| **C++ 服务** | C++17 · cpp-httplib · WebSocket |
| **通信** | REST API · WebSocket |

## 项目结构

```
SuoXing-Tuan/
├── backend/                    # FastAPI 后端（YOLO 推理、LiDAR-相机融合、三维重建）
├── frontend/                   # Vue 3 前端（检测/重建/实时融合/监控/配置）
├── OTHER_END/                  # C++ 服务端
│   ├── Transpond_Server/       # 数据中继站（接收硬件数据、缓存、转发）
│   ├── Control_Server/         # 控制中转（手机-小车 WebSocket 房间配对）
│   └── Car_detection_end/      # 车端采集（LiDAR + 相机数据发送）
├── model-training/             # YOLO 裂缝检测模型训练
├── test_end/                   # 传感器数据模拟器（离线测试用）
├── script/                     # 启停脚本
├── data_captures/              # 采集的调试数据
└── docs/                       # 项目文档
```

## 硬件架构

```
Livox Mid-40 激光雷达
    ↕
Jetson Nano B01 上位机（数据采集 + 上传）

STM32F103RC 运动控制板（底盘控制）
```

- **Livox Mid-40** — 固态激光雷达，采集隧道表面点云
- **Jetson Nano B01** — 上位机，运行 `Car_detection_end`，读取雷达+相机数据并上传到 Transpond_Server
- **STM32F103RC** — 运动控制板，独立控制小车底盘运动

## 核心功能

- **YOLO 裂缝检测** — 实时图像推理，支持模型热加载切换
- **LiDAR-相机融合** — 点云与图像颜色采样，生成彩色三维场景
- **Poisson 三维重建** — 累积多帧点云，表面重建 + 缺陷反投影标注
- **航迹推算** — 自行车模型实时估计小车位姿 (x, y, yaw)
- **实时融合页面** — 被动/主动双模式（中继拉取 / 回放 / 手动推送）
- **手机远程控制** — WebSocket 房间模型，手机控制小车 + 接收遥测
- **离线回放** — 加载历史数据包，离线模式下后端独立运行

## 文档

| 文档 | 说明 |
|------|------|
| [系统架构](docs/架构设计/系统架构.md) | 整体架构、子系统清单、推荐从这里开始 |
| [后端设计](docs/架构设计/后端设计.md) | 后端模块目录、数据流、全部 API 端点 |
| [三维重建管线](docs/功能模块/三维重建管线.md) | 重建数据流、投影公式、算法细节 |
| [实时融合设计](docs/功能模块/实时融合设计.md) | 实时融合页布局、双模式数据流 |
| [实时融合 API](docs/API参考/实时融合API.md) | 接口 JSON Schema 详解 |

完整索引见 [docs/README.md](docs/README.md)。
