# SuoXing-Tuan 系统架构

## 整体架构

```
硬件层                    控制端 (FastAPI)                   前端 (Vue3+Three.js)
┌──────────┐    ┌──────────────────────────────┐    ┌──────────────────────┐
│ 工业相机  │───→│ inference/ (YOLO AI 推理)     │───→│ DetectionView        │
│ 激光雷达  │───→│ fusion/ (数据融合+颜色采样)    │───→│ ReconstructionView   │
│ 传感器    │───→│ reconstruction/ (三维重建)     │───→│ RealtimeView         │
│          │    │ state_estimation/ (航迹推算)   │    │                      │
│          │    │ realtime/ (实时调度层)         │    │                      │
│          │    │ loader/ (离线回放)             │    │                      │
└──────────┘    └──────────────────────────────┘    └──────────────────────┘
                          │
                    ┌─────┴─────┐
                    │ 数据中继站  │
                    │ RELAY_API  │
                    └───────────┘
```

## 控制端模块

| 模块 | 职责 | 关键文件 |
|------|------|----------|
| `common/` | 共享基础库（数据模型、坐标变换、投影） | schemas.py, transform.py, camera.py, projection.py |
| `inference/` | YOLO AI 推理 | engine.py |
| `fusion/` | 数据融合 + LiDAR-Camera 颜色采样 | datafusion.py, coloring.py, manager.py |
| `reconstruction/` | 三维表面重建 + 缺陷投影 | engine.py, routes.py, projector.py, defect_table.py |
| `state_estimation/` | 自行车模型航迹推算 | estimator.py, router.py |
| `realtime/` | 实时融合调度层 | fusion_router.py, preprocessor.py |
| `loader/` | 离线场景加载器 | scene_loader.py |

## 前端页面

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | DetectionView | 2D YOLO 图像检测 |
| `/reconstruction` | ReconstructionView | 离线 3D 场景重建 |
| `/realtime` | RealtimeView | 实时融合检测（被动/主动双模式） |
