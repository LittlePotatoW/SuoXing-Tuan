# 控制端设计文档

## 目录结构

```
backend/
├── main.py                          # FastAPI 入口
├── common/                          # 共享基础库
│   ├── schemas.py                   # Pydantic 数据模型
│   ├── transform.py                 # 坐标变换数学工具
│   ├── camera.py                    # 相机内参/外参
│   └── projection.py               # 投影/反投影函数
├── inference/                       # AI 推理
│   ├── engine.py                    # YOLO InferenceEngine
│   └── schemas.py                   # DetectionResult
├── fusion/                          # 数据融合
│   ├── datafusion.py               # SensorFrame→FusedFrame
│   ├── coloring.py                  # 点云颜色采样
│   └── manager.py                   # DataFusionManager
├── reconstruction/                  # 三维重建
│   ├── engine.py                    # Poisson 重建引擎
│   ├── routes.py                    # /api/reconstruction/*
│   ├── projector.py                 # DefectProjector
│   └── defect_table.py             # 缺陷汇总
├── state_estimation/                # 航迹推算
│   ├── estimator.py                 # StateEstimator (自行车模型)
│   └── router.py                    # /api/preprocessing/*
├── realtime/                        # 实时融合
│   ├── fusion_router.py            # 调度层 API
│   └── preprocessor.py             # 预处理 (占位)
├── loader/                          # 离线数据
│   └── scene_loader.py             # SceneLoader
├── models/                          # .pt 模型文件 (gitignored)
├── test_data/                       # 测试数据 (gitignored)
└── tests/                           # 测试
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/inference` | YOLO 图像推理 |
| POST | `/api/model/load` | 模型热加载 |
| POST | `/api/reconstruction/frame` | 上传单帧 SensorFrame |
| GET | `/api/reconstruction/result` | 获取重建结果 |
| GET | `/api/reconstruction/status` | 重建状态 |
| POST | `/api/reconstruction/load` | 加载离线场景 |
| POST | `/api/reconstruction/control` | 回放控制 (pause/resume/stop/seek) |
| POST | `/api/reconstruction/reset` | 重置重建引擎 |
| WS | `/api/reconstruction/ws` | 重建结果实时推送 |
| POST | `/api/preprocessing/kinematics` | 运动学参数 |
| GET | `/api/preprocessing/estimator/stats` | 状态估计器统计 |
| POST | `/api/preprocessing/reset` | 重置航迹推算 |
| POST | `/api/realtime/feed/location` | 喂入定位数据 |
| POST | `/api/realtime/feed/detection` | 喂入检测数据 |
| GET | `/api/realtime/status` | 实时融合状态 |
| POST | `/api/realtime/toggle` | 开关 YOLO/重建 |
