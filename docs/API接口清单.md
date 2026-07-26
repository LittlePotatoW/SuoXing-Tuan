# API 接口清单

## 前端 → 后端（POST，7 个）

| 端点 | 前端调用方 | 用途 |
|------|----------|------|
| `POST /api/vehicle/telemetry` | `useConnection.ts` | WebSocket 收到遥测后转发给后端位置估计器 |
| `POST /api/vehicle/frame` | `useConnection.ts` | WebSocket 收到帧数据后转发给后端重建引擎 |
| `POST /api/vehicle/estimator/reset` | `SettingsView.vue` | 设置页"应用" → 重置位置估计器 + 切换模式 |
| `POST /api/reconstruction/reset` | `RealtimeModeling.vue` `ReplayModeling.vue` `SettingsView.vue` | 开始建模/回放时 → 重置引擎 + 传 YOLO 开关 |
| `POST /api/detection/image` | `StaticDetection.vue` | 静态检测 → 上传单张图片执行 YOLO 推理 |
| `POST /api/session/save` | `data-saver.ts` | 保存Session → 发送 manifest + 帧文件到后端写盘 |
| `POST /api/report/save` | `RealtimeModeling.vue` | 保存Report → 发送检测结果 JSON 到后端写盘 |

## 后端 → 前端（GET，11 个）

| 端点 | 前端调用方 | 用途 |
|------|----------|------|
| `GET /api/vehicle/position` | `MainView.vue` | 主页每秒轮询车辆位置 (x, y, heading) |
| `GET /api/vehicle/estimator/config` | `SettingsView.vue` | 设置页加载时读取估计器当前配置 |
| `GET /api/reconstruction/status` | `RealtimeModeling.vue` | 实时建模 → 轮询帧计数和引擎状态 |
| `GET /api/reconstruction/result` | `RealtimeModeling.vue` `ReplayModeling.vue` `useReconstruction.ts` | 轮询重建结果（点云 URL + 缺陷列表） |
| `GET /api/reconstruction/config` | `SettingsView.vue` | 设置页加载时读取引擎当前配置 |
| `GET /api/detection/result` | `StaticDetection.vue` | 查询最新检测结果 |
| `GET /api/detection/result/annotated` | `StaticDetection.vue` | 获取 YOLO 标注图（base64 JPEG） |
| `GET /api/session/list` | `ReplayModeling.vue` | 回放页加载 session 下拉列表 |
| `GET /api/session/{name}` | `data-loader.ts` | 回放时加载 session 的 manifest.json |
| `GET /api/session/files/{name}/{path}` | `data-loader.ts` | 回放时读取帧图像文件（JPEG/PNG） |
| `GET /api/report/list` | `DefectDetail.vue` | 缺陷详情页加载 report 下拉列表 |
| `GET /api/report/{filename}` | `DefectDetail.vue` | 选择 report 后加载完整 JSON |
