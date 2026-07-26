# 索性途安

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

北京科技大学 索性途安实践团 — 隧道缺陷智能检测与三维重建系统。

## 技术栈

| 端 | 技术 |
|------|------|
| Windows 主项目 | Vue 3 + Vite + Pinia + Three.js / FastAPI + WebSocket + OpenCV |
| 移动端 APP | uni-app (Vue 3) |
| 检测端 (Jetson Nano) | YOLO / OpenCV |
| 三维重建 | Open3D / TSDF / Poisson |
| 深度相机 | 奥比中光 Astra Pro |

## 架构

```
小车（控制端 + 检测端） ←── APP（手机端）
         │
    Windows 主项目
```