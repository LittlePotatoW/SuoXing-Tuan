# Control Server — WebSocket 中转服务器

WebSocket 实时消息转发：手机控制端 ↔ 小车通信模块。多台手机共享 1 台小车，同一房间内自动配对。

## 编译

```bash
mkdir build && cd build
cmake .. && make -j$(nproc)
```

## 运行

```bash
./control-server --port 8080
```

## 端点

| 端点 | 客户端 | 说明 |
|------|--------|------|
| `ws://host:8080/phone?room=<id>` | 手机 | 多台手机通过此端点加入房间 |
| `ws://host:8080/robot?room=<id>` | 小车 | 小车通信模块，每房间仅 1 台 |
| `GET /status` | HTTP | 查询房间数 |

## 消息类型

| type | 方向 | 处理 |
|------|------|------|
| `ctrl` | 手机→小车 | 转发控制命令 |
| `ping` | 手机→服务器 | 刷新心跳 |
| `tele` | 小车→手机 | 广播遥测 |
| `loc` | 小车→手机 | 广播 GPS/LBS/WiFi 定位 |
| `loc_cfg` | 手机→小车 | 转发定位配置 |
| `sys` | 服务器→客户端 | 连接通知 |

详见 `API.md`。
