# 项目文件结构

```
SuoXing-Tuan/
├── CLAUDE.md                          # 项目规则
├── .gitignore
├── backend/                           # Python 后端
│   ├── main.py                        # FastAPI 入口
│   ├── common/                        # 共享基础库
│   ├── inference/                     # AI 推理
│   ├── fusion/                        # 数据融合
│   ├── reconstruction/                # 三维重建
│   ├── state_estimation/              # 航迹推算
│   ├── realtime/                      # 实时融合调度
│   ├── loader/                        # 离线加载
│   ├── models/                        # .pt 模型
│   ├── test_data/                     # 测试数据
│   └── tests/                         # 测试
├── frontend/                          # Vue3 前端
├── model-training/                    # YOLO 训练
├── test_end/                          # 数据包模拟器
├── docs/                              # 项目文档
├── docs-people/                       # 数据包结构文档
├── referrence-local/                  # 本地参考资料
├── script/                            # 启动脚本
└── lidar_camera_fusion/               # LiDAR-Camera 融合模块 (独立)
```
