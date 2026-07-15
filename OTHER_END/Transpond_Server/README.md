# TranspondServer

C++17 中继服务器 — 接收小车定位/传感器数据，提供 HTTP 查询 + WebSocket 实时推送。

## 快速开始

### 编译

```bash
# 需要: CMake 3.20+, MSVC / GCC / Clang (C++17)
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
```

产物: `build/Release/transpond-server.exe` (Windows) 或 `build/transpond-server` (Linux)

### 运行

```bash
./transpond-server --port 8001 --max-loc 2000 --max-sensor 200
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | 8001 | 监听端口 |
| `--max-loc` | 2000 | 定位数据缓存上限（条） |
| `--max-sensor` | 200 | 传感器数据缓存上限（条） |

启动后服务端控制台会打印每个请求的日志，方便调试。

---

## API 文档

### 接口总览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/location` | 上传定位数据 |
| POST | `/frames` | 上传传感器数据（批量） |
| POST | `/debug` | 调试指令（清空/查看缓存） |
| GET | `/status` | 查询缓存量 |
| GET | `/location` | 查询定位数据 |
| GET | `/sensor` | 查询传感器数据 |
| WS | `/stream` | 实时推送（WebSocket） |

---

### POST /location

上传一帧定位数据。

```bash
curl -X POST http://localhost:8001/location \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp_ns": 1783581801179000000,
    "camera": [{
      "camera_pose": {
        "position": {"x": 0.0, "y": 0.0, "z": 0.3},
        "rotation": {"qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0}
      }
    }],
    "car": {
      "kinematics": {
        "velocity": 0.5,
        "steering_angle": 0.0,
        "wheel_base": 1.5
      }
    }
  }'
```

响应: `{"status":"ok","cached":5}`

---

### POST /frames

上传批量传感器数据（1~N 帧）。

```bash
curl -X POST http://localhost:8001/frames \
  -H "Content-Type: application/json" \
  -d '{
    "count": 1,
    "frames": [{
      "frame_id": "f000039",
      "timestamp_ns": 1783586485847000000,
      "point_cloud": {"points": [2.044, -0.231, 0.682], "point_count": 1},
      "camera_views": [{
        "image_data": "",
        "width": 1280, "height": 720,
        "camera_pose": {
          "position": {"x": 0.0, "y": 0.0, "z": 0.3},
          "rotation": {"qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0}
        }
      }],
      "car_position": {
        "pose": {
          "position": {"x": 0.0, "y": 0.0, "z": 0.0},
          "rotation": {"qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0}
        },
        "timestamp_ns": 1783586485847000000
      },
      "kinematics": {
        "velocity": 0.0, "steering_angle": 0.0,
        "wheel_base": 1.5, "timestamp_ns": 1783586485847000000
      }
    }]
  }'
```

响应: `{"status":"ok","received":1,"cached":5}`

---

### POST /debug

```bash
# 查看当前缓存量
curl -X POST http://localhost:8001/debug \
  -H "Content-Type: application/json" \
  -d '{"action":"status"}'

# 清空全部缓存
curl -X POST http://localhost:8001/debug \
  -H "Content-Type: application/json" \
  -d '{"action":"clear"}'
```

---

### GET /status

```bash
curl http://localhost:8001/status
```

响应: `{"status":"ok","location_cached":6,"sensor_cached":40}`

---

### GET /location

```bash
# 全部定位数据
curl http://localhost:8001/location

# 最近 5 条
curl "http://localhost:8001/location?limit=5"

# 指定时间戳之后的数据
curl "http://localhost:8001/location?after=1783586485000000000"
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `after` | u64 | 只返回 `timestamp_ns > after` 的数据 |
| `limit` | usize | 最多返回 N 条（取最新） |

---

### GET /sensor

参数同上。

```bash
curl "http://localhost:8001/sensor?limit=10&after=1783586485000000000"
```

---

### WS /stream

WebSocket 实时推送端点。有新数据到达时自动推送，每 200ms 检查一次。

**连接示例（Python）**:

```python
import websocket
ws = websocket.create_connection("ws://localhost:8001/stream?mode=all")
while True:
    msg = ws.recv()
    print(msg)
```

**连接示例（JavaScript 浏览器）**:

```js
const ws = new WebSocket("ws://localhost:8001/stream?mode=all");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `mode` | `all` | `all` / `location` / `sensor` |

**推送消息格式**:

```json
{"type":"location","count":2,"frames":[...]}
{"type":"sensor","count":1,"frames":[...]}
```

location 和 sensor 分别作为独立消息发送。

---

## 测试

项目自带 Python 测试脚本，覆盖全部接口：

```bash
# 安装依赖
pip install requests websocket-client

# 修改 测试.py 中的 SERVER_IP 和 SERVER_PORT，然后运行
python 测试.py
```

---

## 项目结构

```
Transpond_Server/
├── CMakeLists.txt         # CMake 构建配置
├── main.cpp               # 入口 + 路由注册 + WebSocket handler
├── handlers.h             # Handler 声明 + AppState 结构体
├── handlers.cpp           # 6 个 HTTP handler 实现
├── store.h                # 数据模型 + RingStore 环形缓冲区
├── 测试.py                # API 测试脚本
└── README.md
```

## 技术栈

C++17 · [cpp-httplib](https://github.com/yhirose/cpp-httplib) v0.18.5 · [nlohmann/json](https://github.com/nlohmann/json) v3.11.3
