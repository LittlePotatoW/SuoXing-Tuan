# 实时融合页面（Page 3）API 接口文档

## 概述

实时融合页接收小车发送的两路数据，实时进行三维重建 + 缺陷检测。

```
小车 ──→ POST /api/preprocessing/kinematics  (定位数据, 高频)
小车 ──→ POST /api/reconstruction/frame      (检测数据, 触发式)
前端 ←── WS   /api/reconstruction/ws          (重建结果推送)
前端 ──→ GET  /api/realtime/status            (状态轮询)
前端 ──→ POST /api/realtime/toggle            (开关控制)
```

---

## 接口列表

### 1. 上传运动学数据

```
POST /api/preprocessing/kinematics
```

小车高频上报运动学参数，后端持续积分推算位姿。

**请求体**：

```json
{
  "velocity": 0.5,
  "steering_angle": 0.0,
  "wheel_base": 1.5,
  "timestamp_ns": 1200000000
}
```

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| `velocity` | float | m/s | 线速度 |
| `steering_angle` | float | rad | 转向角 |
| `wheel_base` | float | m | 轴距，默认 1.5 |
| `timestamp_ns` | int | ns | 时间戳 |

**响应**：

```json
{
  "status": "ok",
  "x": 0.3,
  "y": 0.0,
  "yaw": 0.0,
  "velocity": 0.5,
  "updates": 23,
  "rejected": 0
}
```

---

### 2. 上传检测数据

```
POST /api/reconstruction/frame
```

小车触发式上报点云 + 图像，后端进行融合重建。

**请求体**：

```json
{
  "frame_id": "frame_0001",
  "timestamp_ns": 2000000000,
  "point_cloud": {
    "points": "<float32×3 base64>",
    "encoding": "float32_base64",
    "point_count": 10000
  },
  "car_position": {
    "pose": {
      "position": { "x": 0.3, "y": 0.0, "z": 0.0 },
      "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
    },
    "timestamp_ns": 2000000000
  },
  "camera_views": [
    {
      "image_data": "<base64 JPEG>",
      "width": 544,
      "height": 384,
      "camera_pose": {
        "position": { "x": 0.0, "y": 0.0, "z": 1.0 },
        "rotation": { "qw": 0.7071, "qx": 0.0, "qy": 0.7071, "qz": 0.0 }
      }
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `frame_id` | string | 否 | 帧标识 |
| `timestamp_ns` | int | 是 | 时间戳 (ns) |
| `point_cloud.points` | string | 是 | float32×3 二进制 base64 编码 |
| `point_cloud.encoding` | string | 否 | `"float32_base64"`，缺失时为旧 JSON 数组格式 |
| `point_cloud.point_count` | int | 否 | 点数 |
| `car_position.pose.position` | object | 是 | 小车世界坐标 {x,y,z} |
| `car_position.pose.rotation` | object | 是 | 朝向四元数 {qw,qx,qy,qz} |
| `camera_views[]` | array | 否 | 相机图像列表 |
| `camera_views[].image_data` | string | 否 | JPEG base64 编码 |
| `camera_views[].width/height` | int | 否 | 图像分辨率 |
| `camera_views[].camera_pose` | object | 否 | 相机在车体上的安装位姿 |

**响应**：

```json
{
  "status": "ok",
  "frame_id": "frame_0001",
  "total_frames": 5,
  "rebuild_triggered": true
}
```

---

### 3. 重建结果推送（WebSocket）

```
WS /api/reconstruction/ws
```

前端连接此 WebSocket，每次重建完成时收到推送。

**推送消息格式**：

```json
{
  "type": "rebuild_complete",
  "data": {
    "status": "completed",
    "total_frames": 15,
    "total_points": 4500,
    "mesh": {
      "vertices": [0.1, 0.2, 1.5, ...],
      "faces": [0, 1, 2, ...],
      "vertex_count": 45000,
      "face_count": 89000,
      "vertex_colors": [145, 141, 138, ...]
    },
    "cracks": [
      {
        "position": { "x": 1.25, "y": 0.02, "z": 1.50 },
        "confidence": 0.92,
        "crack_type": "裂缝",
        "image_frame_id": "frame_0003"
      }
    ],
    "camera_trail": [[0.0, 0.0, 1.0], [0.1, 0.0, 1.0], ...]
  }
}
```

| 字段 | 说明 |
|------|------|
| `mesh.vertices` | 扁平顶点坐标 [x,y,z,...], N*3 |
| `mesh.faces` | 扁平三角面索引 [i0,i1,i2,...], M*3 |
| `mesh.vertex_colors` | 顶点颜色 [r,g,b,...], N*3, uint8 |
| `cracks[]` | 缺陷标注列表 |
| `cracks[].position` | 缺陷世界坐标 |
| `cracks[].crack_type` | 裂缝/渗漏/剥落 |
| `camera_trail` | 相机移动轨迹 |

---

### 4. 查询融合状态

```
GET /api/realtime/status
```

前端轮询获取实时统计。

**响应**：

```json
{
  "yolo_enabled": true,
  "reconstruction_enabled": true,
  "estimator": {
    "x": 0.3,
    "y": 0.0,
    "yaw": 0.0
  },
  "counts": {
    "location": 50,
    "detection": 5,
    "fusion": 5
  },
  "estimator_stats": {
    "updates": 50,
    "rejected": 2,
    "history_points": 50
  }
}
```

---

### 5. 开关控制

```
POST /api/realtime/toggle
```

前端控制 YOLO 检测和三维重建的启用/禁用。

**请求体**：

```json
{ "yolo": true }
```
或
```json
{ "reconstruction": false }
```

**响应**：

```json
{ "yolo_enabled": true, "reconstruction_enabled": false }
```

---

## 数据流时序

```
time ──────────────────────────────────────→

小车:
  [loc][loc][loc][loc][loc][det][loc][loc][loc][loc][loc][det]...
   ↑ 200ms 间隔         ↑ 触发式

后端:
  定位数据 → StateEstimator 积分 → (x, y, yaw)
  检测数据 → DataFusion 融合 → ReconstructionEngine 累积
          → 每 10 帧触发 Poisson 重建 → WebSocket 推送

前端:
  WebSocket 收到 rebuild_complete → 3D 模型更新
  GET /realtime/status 每秒轮询 → 状态栏刷新
```

---

## 主动模式 — 数据中继站 (TranspondServer)

主动模式不依赖模拟器推送，前端直接从中继站拉取数据。

```
硬件 ──→ TranspondServer (:8001) ←── 控制端主动拉取
         POST /location               GET /location?limit=10
         POST /frames                 GET /sensor?limit=20
         WS /stream (可选)            WS /stream (实时推送)
```

中继站 API 详见 [OTHER_END/Transpond_Server/API.md](../../OTHER_END/Transpond_Server/API.md)。
