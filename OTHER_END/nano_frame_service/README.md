# nano_frame_service/ — Nano 相机采集推流服务

运行在 **Jetson Nano (Linux/ROS)** 上的 Astra Pro 深度相机帧采集与 WebSocket 推流服务。

## 目录

| 文件 | 说明 |
|------|------|
| `scripts/frame_sender.py` | 帧采集主程序 |
| `scripts/ws_stream_server.py` | WebSocket 流媒体服务 |
| `scripts/frame_bridge.py` | 帧数据桥接中间件 |
| `scripts/depth_colorizer.py` | 深度图彩色化 |
| `scripts/startup.sh` | 开机自启脚本 |
| `scripts/start_camera.sh` | 相机启停脚本 |
| `config/params.yaml` | 全局参数配置 |
| `launch/` | ROS launch 启动文件 |
| `astra-frame-sender.service` | systemd 服务文件 |

## 部署

1. 安装依赖：`pip install -r requirements.txt`（如存在）
2. 配置参数：编辑 `config/params.yaml`
3. ROS 启动：`roslaunch launch/auto_start.launch`
4. 或 systemd 自启：`sudo cp astra-frame-sender.service /etc/systemd/system/ && sudo systemctl enable astra-frame-sender`

## 协议

推流格式：JSON，包含 `timestamp`、`image` (Base64 JPEG)、`depth_map` (Base64 PNG)
