# Car Detection End

车端数据采集程序 — LiDAR + 相机 → 后端重建管线。

## 架构

```
LiDAR (Livox Mid-40) ──→ lidar_stdout ──→ 管道 ──┐
                                                   ├──→ main → HTTP → 后端
USB 相机 ──→ V4L2 MJPEG ─────────────────────────┘
```

三线程：定位线程（200ms）+ 检测线程（1s）+ 看门狗。

## 快速开始

```bash
# 1. 编译
bash build.sh

# 2. 运行 (默认连接 127.0.0.1:8001)
./build/car_detection

# 指定服务器
./build/car_detection --host 192.168.1.100 --port 8001 --jpeg-quality 50
```

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | `127.0.0.1` | 服务器 IP |
| `--port` | `8001` | 服务器端口 |
| `--jpeg-quality` | `50` | JPEG 压缩质量 1-100 |
| `--cam-w` | `640` | 相机宽度 |
| `--cam-h` | `480` | 相机高度 |

## 配置

编辑 `config.json`：

```json
{
  "server": {
    "base_url": "http://127.0.0.1:8000"   // 后端地址
  },
  "camera": {
    "device": "/dev/video0",
    "width": 640,
    "height": 480
  },
  "vehicle": {
    "wheel_base": 1.5,
    "camera_pose": { ... }                 // 相机外参
  },
  "timing": {
    "location_interval_ms": 200,           // 定位发送间隔
    "detection_interval_ms": 1000          // 检测发送间隔
  }
}
```

## 依赖

- C++17 编译器
- CMake ≥ 3.14
- libv4l-dev（相机）
- Livox SDK v2（LiDAR，可选，无 SDK 时使用模拟模式）

HTTP 和 JSON 库已自带（`third_party/`），无需额外安装。

## 开机自启

```bash
sudo cp car-camera.service /etc/systemd/system/
sudo systemctl enable car-camera
sudo systemctl start car-camera
journalctl -u car-camera -f   # 查看日志
```

## 发送的数据格式

| 接口 | 用途 | 间隔 |
|------|------|------|
| `POST /location` | 运动学定位 (lacation_data 格式) | 200ms |
| `POST /frames` | 点云 + 图像 (批量 SensorFrame) | 1s |

格式与 Transpond_Server 完全匹配。
