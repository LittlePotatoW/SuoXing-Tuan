# TranspondServer API 文档

**默认端口**: 8001（可通过 `--port` 修改）

---

## 接口总览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/location` | 上传定位数据 |
| POST | `/frames` | 上传传感器数据（批量） |
| POST | `/debug` | 调试指令 |
| GET | `/status` | 查询缓存量 |
| GET | `/location` | 查询定位数据 |
| GET | `/sensor` | 查询传感器数据 |
| WS | `/stream` | 实时推送 |

---

## POST /location

上传一帧定位数据（`lacation_data` 格式）。

**请求体**:

```json
{
  "timestamp_ns": 1783581801179000000,
  "camera": [
    {
      "camera_pose": {
        "position": { "x": 0.0, "y": 0.0, "z": 0.3 },
        "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
      }
    }
  ],
  "car": {
    "kinematics": {
      "velocity": 0.5,
      "steering_angle": 0.0,
      "wheel_base": 1.5
    }
  }
}
```

**响应 (200)**:

```json
{"status": "ok", "cached": 5}
```

---

## POST /frames

上传批量传感器数据（`new_detection_data` 格式，1~N 帧）。

**请求体**:

```json
{
  "count": 2,
  "frames": [
    {
      "frame_id": "f000039",
      "timestamp_ns": 1783586485847000000,
      "point_cloud": {
        "points": [2.044, -0.231, 0.682],
        "point_count": 1
      },
      "camera_views": [
        {
          "image_data": "/9j/4AAQSkZJRg...base64...",
          "width": 1280,
          "height": 720,
          "camera_pose": {
            "position": { "x": 0.0, "y": 0.0, "z": 0.3 },
            "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
          }
        }
      ],
      "car_position": {
        "pose": {
          "position": { "x": 0.0, "y": 0.0, "z": 0.0 },
          "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
        },
        "timestamp_ns": 1783586485847000000
      },
      "kinematics": {
        "velocity": 0.0,
        "steering_angle": 0.0,
        "wheel_base": 1.5,
        "timestamp_ns": 1783586485847000000
      }
    }
  ]
}
```

**响应 (200)**:

```json
{"status": "ok", "received": 2, "cached": 5}
```

---

## POST /debug

调试指令（预留）。

**请求体**:

```json
{"action": "clear"}
```

| action | 说明 |
|--------|------|
| `clear` | 清空 location + sensor 缓存 |
| `status` | 返回当前缓存量 |

---

## GET /status

查询缓存量。

**响应 (200)**:

```json
{"status": "ok", "location_cached": 6, "sensor_cached": 40}
```

---

## GET /location

查询定位数据。

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `?after=ts` | u64 | 只返回 timestamp_ns > ts 的数据 |
| `?limit=N` | usize | 只返回最近 N 条 |

**示例**:

```
GET /location                       # 全部
GET /location?limit=5               # 最近 5 条
GET /location?after=1783586485000000000  # 指定时间之后
```

**响应 (200)**:

```json
{
  "status": "ok",
  "count": 2,
  "frames": [
    { "timestamp_ns": 1000, "camera": [], "car": {...} }
  ]
}
```

---

## GET /sensor

查询传感器数据。参数同上。

**示例**:

```
GET /sensor?limit=10&after=1783586485000000000
```

---

## WS /stream

实时推送。连接后，有新数据到达时自动推送。

**查询参数**:

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `?mode=all` | all | `all` / `location` / `sensor` |

**推送消息格式**:

```json
{"type": "location", "count": 2, "frames": [...]}
{"type": "sensor",   "count": 1, "frames": [...]}
```

每 200ms 检查一次，有新数据即推送。

---

## 命令行参数

```
transpond-server --port 8001 --max-loc 2000 --max-sensor 200
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--port` | 8001 | 监听端口 |
| `--max-loc` | 2000 | location 缓存上限 |
| `--max-sensor` | 200 | sensor 缓存上限 |

## 部署

```bash
# 编译
cargo build --release

# 产物: target/release/transpond-server (单文件 ~8MB)

# 部署
scp target/release/transpond-server user@server:/opt/
ssh user@server "/opt/transpond-server --port 8001"
```
