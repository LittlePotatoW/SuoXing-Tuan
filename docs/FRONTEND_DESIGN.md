# 前端设计文档

## 技术栈

Vue 3 + TypeScript + Vite + Three.js + vue-router

## 页面

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | DetectionView | 2D YOLO 图像检测 |
| `/reconstruction` | ReconstructionView | 离线场景 3D 重建 |
| `/realtime` | RealtimeView | 实时融合（被动/主动双模式） |

## 实时融合页 (RealtimeView)

- **被动模式**：WebSocket 接收后端推送
- **主动模式**：轮询数据中继站，主动拉数据喂后端
- **测试定位**：生成匀速直线 location 覆盖帧内 car_position
- **YOLO/重建开关**：独立控制

## 3D 查看器 (ReconstructionViewer)

- Three.js WebGL 渲染
- 彩色 Mesh + 缺陷标注球 (addCracks)
- OrbitControls 旋转/缩放
- Taubin 平滑后处理
