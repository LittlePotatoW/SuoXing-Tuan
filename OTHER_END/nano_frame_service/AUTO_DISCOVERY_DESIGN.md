# Astra Pro 局域网自动发现 & 断线重连 改造方案

## 1. 当前架构

```
Jetson Nano (172.20.10.11)
├─ roscore + astra_camera (ROS)
├─ frame_bridge.py  (Py2)  ROS topic → TCP 127.0.0.1:8004  每帧 JSON Line
└─ ws_stream_server.py (Py3)  TCP:8004 → WebSocket 0.0.0.0:8002  wzm 协议

PC (浏览器)
└─ viewer.html  手动输入 IP → WebSocket 连接 → 显示 RGB + Depth
```

**问题**：viewer 需要手动填 IP，不知道 Jetson 的地址。

---

## 2. 改造目标

1. Jetson 开机后自动广播自己的存在（UDP 信标）
2. viewer 打开后自动扫描局域网找到 Jetson，自动连接
3. 连接断开后自动重连
4. 支持多台 PC 同时连接观看

---

## 3. 改造方案：UDP 信标 + 前端自动扫描

### 整体流程

```
Jetson 端（新增）                       PC 端（改造 viewer.html）
───────────────                         ──────────────────────────
启动时：                                 打开页面时：
  │                                       │
  ├─ 启动 UDP 信标线程                     ├─ 获取本机 IP（WebRTC 技巧）
  │   每 3 秒广播一包                      ├─ 提取子网前缀（如 172.20.10）
  │   {"type":"astra_beacon",              ├─ 启动子网扫描
  │    "host":"172.20.10.11",              │   对子网内每个 IP 尝试 TCP 连接 :8002
  │    "ws_port":8002,                     │   超时 800ms/个，并行 10 个
  │    "device":"jetson_nano"}             │
  │                                        ├─ 找到第一个响应的 IP
  └─ WS 服务继续在 :8002 运行（不变）       ├─ 自动填入 URL 并连接
                                           ├─ 连接成功 → 停止扫描
                                           ├─ 连接断开 → 等 3 秒 → 重连（不重新扫描，用上次 IP）
                                           └─ 重连失败超过 5 次 → 重新扫描子网
```

### 为什么用 TCP 端口探测而不是 UDP？

浏览器 JavaScript **不能发 UDP 包**（安全限制）。所以 viewer 不能直接收 UDP 信标。

**替代方案**：viewer 用 `new WebSocket()` 快速尝试子网内每个 IP 的 8002 端口，哪个先连上就是 Jetson。

UDP 信标给**原生客户端**用（Python 脚本、手机 App 等），浏览器走 TCP 扫描。

---

## 4. Jetson 端改动

### 4.1 新增文件：`scripts/discovery_beacon.py`（Python 3）

一个小型后台进程，开机自启。功能：

```
每 3 秒 → UDP 广播 255.255.255.255:9001
包内容（JSON）：
{
  "type": "astra_beacon",
  "host": "<本机实际 LAN IP>",
  "ws_port": 8002,
  "device": "jetson_nano",
  "camera": "astra_pro"
}
```

**自动获取本机 LAN IP 的方法**：
```python
import socket
def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip
```

**完整代码骨架**（约 40 行）：
```python
#!/usr/bin/env python3
"""UDP beacon: broadcasts Jetson IP every 3s for auto-discovery."""
import socket
import json
import time

BEACON_PORT = 9001
INTERVAL = 3  # 秒

def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.5)

    while True:
        ip = get_lan_ip()
        msg = json.dumps({
            "type": "astra_beacon",
            "host": ip,
            "ws_port": 8002,
            "device": "jetson_nano"
        })
        try:
            sock.sendto(msg.encode(), ("255.255.255.255", BEACON_PORT))
        except:
            pass
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
```

### 4.2 修改文件：`scripts/start_camera.sh`

在第 4 步（WS Server）之后加一步：

```bash
# 5. UDP 信标（局域网发现）
echo "[5/5] Starting UDP discovery beacon..."
nohup python3 "${SCRIPT_DIR}/discovery_beacon.py" > /tmp/beacon.log 2>&1 &
echo "      Beacon started (UDP broadcast :9001 every 3s)"
```

### 4.3 自启动配置

利用已有的 systemd 服务 `astra-frame-sender.service`（之前配的）：
- 确保它调用的是更新后的 `start_camera.sh`
- 开机自动启动整个管线（core + camera + bridge + ws + beacon）

**不需要改 systemd 配置**，只要 `start_camera.sh` 包含所有步骤即可。

---

## 5. 前端（viewer.html）改动

### 5.1 新增功能

| 功能 | 实现方式 |
|------|---------|
| 获取本机 LAN IP | WebRTC `RTCPeerConnection` 创建 offer 拿 local candidate |
| 子网扫描 | 对 `IP前缀.1-254` 并行尝试 WebSocket 连接，800ms 超时 |
| 自动连接 | 扫描到第一个可达 IP 后自动填入并连接 |
| 断线重连 | `onclose` 后 3 秒自动重连（用上次成功的 IP，不重新扫描） |
| 兜底重扫描 | 连续重连失败 5 次 → 重新扫描子网（IP 可能变了） |
| 扫描进度提示 | 状态栏显示 "正在扫描 172.20.10.x (45/254)" |
| 手动覆盖 | 输入框仍可手动填 IP，填了就不再自动扫描 |

### 5.2 核心逻辑伪代码

```javascript
// ========== 状态机 ==========
const State = { IDLE:0, SCANNING:1, CONNECTING:2, CONNECTED:3, WAITING:4 };
let state = State.IDLE;
let foundIP = null;       // 上次成功连接的 IP
let reconnectCount = 0;   // 连续重连失败次数
const MAX_RECONNECT = 5;  // 超过此次数重新扫描
const RECONNECT_DELAY = 3000;  // 重连间隔 ms
const SCAN_TIMEOUT = 800;      // 每个 IP 的超时 ms

// ========== 启动流程 ==========
window.onload = async function() {
  // 1. 如果用户手动填了非默认 IP，直接连接
  let url = document.getElementById('url').value.trim();
  if (url && url !== defaultURL) {
    connect(url); return;
  }

  // 2. 获取本机 IP
  let myIP = await getLocalIP();   // 如 "172.20.10.2"
  let prefix = myIP.split('.').slice(0,3).join('.');  // "172.20.10"

  // 3. 扫描子网
  state = State.SCANNING;
  await scanSubnet(prefix, 8002);  // 异步扫描，找到后自动连接
};

// ========== 子网扫描 ==========
async function scanSubnet(prefix, port) {
  // 优先扫描常见 IP (.1, .11, .100-.110)
  let priority = [1, 11, 100,101,102,103,104,105,106,107,108,109,110];
  let all = [...priority];
  for (let i=1; i<=254; i++) {
    if (!priority.includes(i)) all.push(i);
  }

  for (let i=0; i<all.length && state===State.SCANNING; i++) {
    let ip = prefix + '.' + all[i];
    updateScanStatus('正在扫描 ' + ip + ' (' + (i+1) + '/' + all.length + ')');

    let ok = await tryConnect(ip, port);  // Promise, 800ms 超时
    if (ok) {
      foundIP = ip;
      document.getElementById('url').value = 'ws://' + ip + ':' + port;
      connect();  // 正式连接
      return;
    }
  }
  // 没找到 → 等 5 秒重新扫描
  updateScanStatus('未找到设备，5秒后重试...');
  setTimeout(() => scanSubnet(prefix, port), 5000);
}

// ========== 尝试连接（带超时）==========
function tryConnect(ip, port) {
  return new Promise(resolve => {
    let ws = new WebSocket('ws://' + ip + ':' + port);
    let timer = setTimeout(() => { ws.close(); resolve(false); }, SCAN_TIMEOUT);
    ws.onopen = () => { clearTimeout(timer); ws.close(); resolve(true); };
    ws.onerror = () => { clearTimeout(timer); resolve(false); };
  });
}

// ========== 断线重连 ==========
// 在 onclose 回调中：
ws.onclose = (e) => {
  if (state === State.CONNECTED) {
    reconnectCount++;
    if (reconnectCount >= MAX_RECONNECT) {
      // 重新扫描子网
      reconnectCount = 0;
      foundIP = null;
      startScan();
    } else {
      // 用上次 IP 重连
      updateStatus('断开，' + (RECONNECT_DELAY/1000) + '秒后重连...');
      setTimeout(() => connect(), RECONNECT_DELAY);
    }
  }
};
```

### 5.3 获取本机 LAN IP 的实现

```javascript
function getLocalIP() {
  return new Promise((resolve, reject) => {
    let pc = new RTCPeerConnection({ iceServers: [] });
    pc.createDataChannel('');
    pc.createOffer().then(offer => pc.setLocalDescription(offer));
    pc.onicecandidate = (e) => {
      if (!e.candidate) return;
      let ip = e.candidate.candidate.match(/(\d+\.\d+\.\d+\.\d+)/);
      if (ip && !ip[1].startsWith('127.')) {
        resolve(ip[1]);
        pc.close();
      }
    };
    setTimeout(() => reject(new Error('timeout')), 3000);
  });
}
```

---

## 6. 协议总结

### WebSocket 帧格式（不变，与 wzm 兼容）

```json
// 服务端 → 客户端
{"type":"frame","timestamp":1784634907.7,"image":"<base64 JPEG>","depth_map":"<base64 16-bit PNG>"}
{"type":"status","message":"camera_ready"}
{"type":"ping"}

// 客户端 → 服务端
{"type":"pong"}
```

### UDP 信标（新增）

端口：`9001`
方向：Jetson → `255.255.255.255:9001`（广播）
频率：每 3 秒
```json
{"type":"astra_beacon","host":"172.20.10.11","ws_port":8002,"device":"jetson_nano"}
```

---

## 7. 文件改动清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/discovery_beacon.py` | **新增** | UDP 信标进程（约 40 行 Python3） |
| `scripts/start_camera.sh` | 修改 | 增加启动 beacon 的步骤 |
| `viewer.html` | 修改 | 增加自动扫描 + 断线重连逻辑 |

**Jetson 端其他文件无需改动**：`frame_bridge.py`、`ws_stream_server.py`、systemd 配置都不变。

---

## 8. 时序图

```
Jetson 开机                        PC 打开 viewer
─────────                          ──────────────
roscore 启动                         │
camera 驱动启动                      │
frame_bridge 启动                    │
ws_stream_server 启动                │
beacon 启动 ──UDP广播──┐             │
                       │ (浏览器收不到UDP，忽略)
                       │             │
                       │    ┌─────── 获取本机 IP: 172.20.10.2
                       │    ├─────── 扫描 172.20.10.1-254
                       │    ├──WS──▶ 172.20.10.1 (超时)
                       │    ├──WS──▶ 172.20.10.2 (超时)
                       │    ├──WS──▶ ...
                       │    ├──WS──▶ 172.20.10.11 ◀─ 通！
                       │    │           │
                       │    │    ┌──────┤ 自动填入 ws://172.20.10.11:8002
                       │    │    │ 连接成功！
                       │    │    │      │
                       │    │    │ ◀─ frame ─▶ RGB + Depth 显示
                       │    │    │
                       │    │    │ (网络闪断)
                       │    │    │ 断开 → 3s后重连 → 成功
                       │    │    │
                       │    │    │ (Jetson 关机)
                       │    │    │ 断开 → 5次重连失败 → 重新扫描子网
                       │    │    │ 不断扫描直到 Jetson 重新上线
```

---

## 9. 给后端 AI 的检查清单

- [ ] `discovery_beacon.py` 正确获取本机 LAN IP（用 UDP connect 8.8.8.8 技巧）
- [ ] `discovery_beacon.py` 用 `SO_BROADCAST` 发 UDP 包到 `255.255.255.255:9001`
- [ ] `start_camera.sh` 中 beacon 在 ws_server 之后启动
- [ ] `viewer.html` 中 `getLocalIP()` 返回的 IP 过滤掉 `127.x.x.x`
- [ ] `viewer.html` 中扫描优先覆盖常见 DHCP 分配的 IP（.1, .11, .100-.110）
- [ ] `viewer.html` 中 `tryConnect()` 必须 set 超时，不然会卡住整个扫描
- [ ] 每个 IP 的扫描用独立的 WebSocket 对象，用完立即 close
- [ ] 连续重连失败 5 次后才触发重新扫描（避免 IP 没变时浪费时间扫描）
- [ ] 手动填入 IP 后跳过自动扫描（用户主动控制优先）
