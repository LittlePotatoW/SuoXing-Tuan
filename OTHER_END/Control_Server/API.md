# 服务器端 API 文档（WebSocket 中转服务器）

## 1. 概述

中转服务器负责在**多台手机/设备**和小车之间转发实时控制指令和遥测数据。服务器**不存储业务数据**，仅做消息转发和超时保护。

### 通信架构

```
手机 App 1 ──┐
手机 App 2 ──┼──WebSocket──→  中转服务器  ←──WebSocket──→  ESP32/4G-DTU(含GPS)
手机 App N ──┘               (云服务器)                    (在小车上)
```

## 2. 服务器职责

| 职责 | 说明 |
|------|------|
| 房间管理 | 每个房间 = **1 台小车 + N 台手机**（N 可配置，默认 10） |
| 控制转发 | 任一手机 → 小车（控制命令） |
| 遥测广播 | 小车 → **所有手机**（遥测数据 + 定位数据） |
| 超时保护 | 300ms 内无**任何手机**消息 → 停止向小车转发 |
| 设备管理 | 自动分配 peerId，设备进出通知全房间 |
| 数据缓存 | tele/loc 自动存入环形缓冲区（各 200 条），供回放查询 |
| 日志 | 环形日志 100 行，可通过 HTTP 拉取 |

## 3. HTTP 端点（回放/调试）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/status` | GET | 服务器状态（房间数） |
| `/tele?room=<id>&limit=N` | GET | 拉取最近 N 条遥测（默认 50） |
| `/loc?room=<id>&limit=N` | GET | 拉取最近 N 条定位（默认 50） |
| `/replay/status?room=<id>` | GET | 查询缓存量 `{"tele_cached":N,"loc_cached":N}` |
| `/logs` | GET | 最近 100 条服务器日志 |

**响应格式**（与 TranspondServer 一致）:
```json
{"status":"ok","count":10,"frames":[...]}
```

## 4. WebSocket 端点

| 端点 | 客户端 | 说明 |
|------|--------|------|
| `ws://<host>:<port>/phone?room=<roomId>` | 手机/设备 | 手机控制端连接，**允许多台** |
| `ws://<host>:<port>/robot?room=<roomId>` | 小车模块 | 小车通信模块连接，**仅 1 台** |

同一 `roomId` 下的手机和小车自动配对。

**连接流程**:

```
步骤 1: 小车先连  ws://192.168.1.100:8080/robot?room=car001
步骤 2: 手机 A 连  ws://192.168.1.100:8080/phone?room=car001
步骤 3: 手机 B 连  ws://192.168.1.100:8080/phone?room=car001  （第 N 台同理）

连接成功后服务器返回 peerId:
  → {"type":"sys","code":1001,"peerId":"A3F2","msg":"已加入房间 car001, 当前 2 台设备在线"}
  
房间内其他手机收到通知:
  → {"type":"sys","code":1004,"peerId":"A3F2","msg":"新设备加入"}
```

**示例**:

```
手机 A:  ws://192.168.1.100:8080/phone?room=car001
手机 B:  ws://192.168.1.100:8080/phone?room=car001
平板:    ws://192.168.1.100:8080/phone?room=car001
小车:    ws://192.168.1.100:8080/robot?room=car001
```

## 5. 消息格式（JSON）

所有 WebSocket 消息均为 JSON 文本帧。

### 4.1 手机 → 服务器 → 小车（控制命令）

```json
{
  "type": "ctrl",
  "dir": "<方向>",
  "peerId": "A3F2",
  "ts": 1700000000123
}
```

**字段说明**:

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| type | string | 是 | 固定 `"ctrl"` |
| dir | string | 是 | 方向值，见 4.2 |
| peerId | string | 是 | 发送者的设备 ID，服务器连接时分配 |
| ts | number | 否 | 毫秒时间戳，用于调试 |

### 4.2 方向枚举值

| dir 值 | 含义 | 备注 |
|--------|------|------|
| `"up"` | 前进 | |
| `"down"` | 后退 | |
| `"left"` | 左转 | 原地左转 |
| `"right"` | 右转 | 原地右转 |
| `"up_left"` | 前进 + 左转 | 组合方向 |
| `"up_right"` | 前进 + 右转 | 组合方向 |
| `"down_left"` | 后退 + 左转 | 组合方向 |
| `"down_right"` | 后退 + 右转 | 组合方向 |
| `"stop"` | 停止 | 可选保留，超时机制已覆盖 |

### 4.3 手机 → 服务器（心跳）

```json
{
  "type": "ping",
  "peerId": "A3F2"
}
```

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| type | string | 是 | 固定 `"ping"` |
| peerId | string | 是 | 发送者的设备 ID |

每台手机空闲时每 **2 秒**发送一次，用于：
- 维持 WebSocket 连接
- 服务器区分"空闲"和"断线"
- 服务器取所有手机的 ping 中最新时间戳作为心跳

### 4.4 小车 → 服务器 → 所有手机（遥测广播）

```json
{
  "type": "tele",
  "enc1": 45,
  "enc2": -38,
  "steer": 150,
  "ts": 1700000000500
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 固定 `"tele"` |
| enc1 | integer | 电机 1 编码器脉冲数 |
| enc2 | integer | 电机 2 编码器脉冲数 |
| steer | integer | 转向舵机 PWM 值 |
| ts | number | 服务器收到遥测时打上的毫秒时间戳（**服务器添加**，小车不传） |

**转发规则**: 服务器收到小车遥测后，注入 `ts` 字段（`Date.now()`），再**广播给房间内所有已连接手机**。

### 4.5 小车 → 服务器 → 所有手机（定位数据广播）

小车通信模块（4G-DTU）集成 GPS/基站/WiFi 定位，定位数据作为独立消息类型上报。

```json
{
  "type": "loc",
  "src": "gps",
  "lat": 22.543210,
  "lon": 113.987650,
  "spd": 1.2,
  "cog": 180.5,
  "alt": 50.3,
  "sat": 12,
  "fix": 3,
  "ts": 1700000000500
}
```

**字段说明**:

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| type | string | 是 | 固定 `"loc"` |
| src | string | 是 | 定位来源：`"gps"` / `"lbs"` / `"wifi"` |
| lat | number | 否 | 纬度（十进制，WGS-84），无定位时为 `null` |
| lon | number | 否 | 经度（十进制，WGS-84），无定位时为 `null` |
| spd | number | 否 | 地面速度（km/h），仅 GPS 有效 |
| cog | number | 否 | 航向角（度，0~360，0=正北），仅 GPS 有效 |
| alt | number | 否 | 海拔高度（米），仅 GPS 有效 |
| sat | integer | 否 | 参与定位的卫星数，仅 GPS 有效 |
| fix | integer | 是 | 定位状态：`0`=未定位, `1`=2D 定位, `2`=3D 定位 |
| ts | number | 是 | 服务器收到数据时打上的毫秒时间戳（**服务器添加**） |

**三种定位来源对比**:

| src | 精度 | 适用场景 | 有效字段 |
|-----|------|---------|---------|
| `"gps"` | 1~10 米 | 室外空旷处 | 全部字段 |
| `"lbs"` | 500 米~几公里 | 室内/室外，中国大陆 | lat, lon, fix=1 |
| `"wifi"` | 10~50 米 | 有 WiFi 覆盖，中国大陆 | lat, lon, fix=1 |

**定位数据来源说明**:
- `src="gps"` 时，`lat` 和 `lon` 由 DTU 将原始 `dd.dddd`（度分）格式转换为十进制度后发送
- `src="lbs"` 时，`lat` 和 `lon` 来自基站定位服务器，DTU 直接透传
- `src="wifi"` 时，DTU 优先使用 WiFi 定位，失败后自动回退到基站定位

**坐标注意事项**:
- 所有坐标为 **WGS-84 标准**，不能直接用于百度、高德等中国地图
- 手机端/服务器端需要根据使用的地图厂商调用对应纠偏 API（百度→BD-09，高德/腾讯→GCJ-02）

**转发规则**: 服务器收到后注入 `ts`，**广播给房间内所有手机**。定位数据不经过 STM32，由通信模块直接发送。

### 4.6 手机 → 服务器 → 小车（定位配置）

手机可以调整定位上报参数。

```json
{
  "type": "loc_cfg",
  "peerId": "A3F2",
  "interval": 3000,
  "src": ["gps", "lbs"]
}
```

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| type | string | 是 | 固定 `"loc_cfg"` |
| peerId | string | 是 | 发送者的设备 ID |
| interval | integer | 否 | 定位上报间隔（毫秒），默认 3000，最小 1000 |
| src | array | 否 | 启用的定位来源，可选 `"gps"` / `"lbs"` / `"wifi"`，默认 `["gps"]` |

服务器转发此消息给小车模块，小车模块据此调整 DTU 定位上报频率和来源。

### 4.7 服务器 → 客户端（系统消息）

```json
{
  "type": "sys",
  "code": 1001,
  "peerId": "A3F2",
  "msg": "已加入房间 car001, 当前 2 台设备在线"
}
```

**状态码**:

| code | 接收方 | 说明 |
|------|--------|------|
| 1000 | 手机/小车 | 房间已满（手机数量已达上限，或已有小车） |
| 1001 | 手机/小车 | 加入房间成功（返回分配的 peerId 和当前设备数） |
| 1002 | 手机 | 小车已断开 |
| 1003 | 手机/小车 | 房间不存在 |
| 1004 | 房间内其他手机 | 新设备加入（附带新设备的 peerId） |
| 1005 | 房间内其他手机 | 设备离开（附带离开设备的 peerId） |
| 4000 | 手机/小车 | 服务器内部错误 |

## 6. 超时保护机制（核心安全功能）

### 5.1 控制超时（300ms）——多设备场景

```
服务器维护每个房间的 last_ctrl_ts 时间戳

多台手机同时在线时:
  - 任一手机发送 ctrl → 更新 last_ctrl_ts
  - 任一手机发送 ping → 更新 last_ctrl_ts（保持连接活跃，但不触发控制）

超时定时器每 50ms 检查一次 → 如果 now - last_ctrl_ts > 300ms:
    → 不向小车转发任何控制数据（小车端 STM32 200ms 超时自停）
```

**多设备控制冲突处理**:
- 不设"主控设备"，任何手机均可发送控制命令
- 最后一条 ctrl 命令立即覆盖前一条
- 多台手机同时操作时，由实际使用者自行协调

### 5.2 小车断线处理

```
WebSocket 断开 / 心跳丢失 → 广播通知所有手机 {"type":"sys","code":1002,"msg":"小车已断开"}
```

### 5.3 手机断线处理

```
某台手机 WebSocket 断开 → 广播通知房间内其他手机
  {"type":"sys","code":1005,"peerId":"A3F2","msg":"设备 A3F2 已离开"}
```

### 5.4 安全链路分层

```
第 1 层: 所有手机松手不发送                  → 0ms 响应
第 2 层: 服务器 300ms 超时不转发              → 300ms 兜底
第 3 层: STM32 200ms 超时停车                 → 500ms 最终兜底
```

**任何单点故障在 500ms 内必定停车。**

## 7. 服务器行为伪代码

```
房间管理:
  room = {
    phone_map: Map<peerId, WebSocket>,   // 多台手机
    robot_ws: null | WebSocket,          // 仅 1 台小车
    last_ctrl_ts: 0,                     // 最后一次 ctrl 消息时间
    watchdog_timer: null,
    max_phones: 10
  }

连接处理:
  onConnect(ws, path):
    roomId = parseQuery(path).room

    if path == "/phone":
      if room.phone_map.size >= room.max_phones:
        ws.send({type:"sys", code:1000, msg:"房间已满"})
        ws.close()
        return
      peerId = generatePeerId()           // 如 "A3F2"
      room.phone_map.set(peerId, ws)
      ws.send({type:"sys", code:1001, peerId, msg:"已加入房间"})
      broadcastToRoom(room, {type:"sys", code:1004, peerId, msg:"新设备加入"}, exclude=peerId)

    if path == "/robot":
      if room.robot_ws:
        ws.send({type:"sys", code:1000, msg:"房间已有小车"})
        ws.close()
        return
      room.robot_ws = ws
      ws.send({type:"sys", code:1001, msg:"配对成功"})

控制消息处理（任一手机 → 小车）:
  onMessage(ws, msg):
    case msg.type == "ctrl":
      if !isPhone(ws) return
      room.last_ctrl_ts = now()
      if room.robot_ws:
        room.robot_ws.send(JSON.stringify(msg))   // 转发给小车
      resetWatchdog(room)

    case msg.type == "ping":
      // 仅刷新时间戳，不触发控制转发
      room.last_ctrl_ts = now()    // 重要: 也刷新 ping 时间
      resetWatchdog(room)

遥测消息处理（小车 → 所有手机）:
  onMessage(ws, msg):
    case msg.type == "tele":
      if !isRobot(ws) return
      room.last_robot_ts = now()
      msg.ts = Date.now()
      broadcastToAllPhones(room, msg)

    case msg.type == "loc":
      if !isRobot(ws) return
      msg.ts = Date.now()                     // 服务器注入时间戳
      broadcastToAllPhones(room, msg)

定位配置（手机 → 小车）:
  onMessage(ws, msg):
    case msg.type == "loc_cfg":
      if !isPhone(ws) return
      if room.robot_ws:
        room.robot_ws.send(JSON.stringify(msg))  // 转发给小车模块

广播辅助函数:
  broadcastToAllPhones(room, msg):
    room.phone_map.forEach((phone_ws, peerId) => {
      phone_ws.send(JSON.stringify(msg))
    })

超时看门狗:
  resetWatchdog(room):
    clearTimeout(room.watchdog_timer)
    room.watchdog_timer = setTimeout(() => {
      if now() - room.last_ctrl_ts >= 300:
        // 不转发，让 STM32 端的 200ms 超时生效
        pass
    }, 300)

断线处理:
  onClose(ws):
    if isRobot(ws):
      closeRoom(room)    // 小车断线，通知所有手机并清空房间
    if isPhone(ws):
      peerId = findPeerId(room, ws)
      room.phone_map.delete(peerId)
      // 通知房间内剩余手机
      broadcastToRoom(room, {type:"sys", code:1005, peerId, msg:"设备已离开"})

    closeRoom(room):
      broadcastToRoom(room, {type:"sys", code:1002, msg:"小车已断开"})
      room.phone_map.forEach((ws) => ws.close())
      room.robot_ws?.close()
```

## 8. 方向到电控命令的映射表

服务器收到手机方向后，转发 JSON 给小车模块。**方向到串口命令的映射在小车模块（ESP32）上完成**，不在服务器上。

| 手机 dir | 串口命令 | 说明 |
|----------|---------|------|
| `up` | `@M,80,150\r\n` | 全速前进，直行 |
| `down` | `@M,-80,150\r\n` | 全速后退，直行 |
| `left` | `@M,40,120\r\n` | 左转（差速） |
| `right` | `@M,40,180\r\n` | 右转（差速） |
| `up_left` | `@M,80,130\r\n` | 前进 + 左转 |
| `up_right` | `@M,80,170\r\n` | 前进 + 右转 |
| `down_left` | `@M,-80,130\r\n` | 后退 + 左转 |
| `down_right` | `@M,-80,170\r\n` | 后退 + 右转 |
| `stop` | `@M,0,150\r\n` | 停车，回正 |

## 9. 多设备场景示例

### 8.1 两台手机同时在线（含定位）

```
时间线:
  T=0s   手机 A 加入 room=car001 → peerId="A001"
  T=1s   手机 B 加入 room=car001 → peerId="B002"
         A 收到通知: {code:1004, peerId:"B002", msg:"新设备加入"}

  T=2s   手机 A 按下 ↑ → ctrl{peerId:"A001", dir:"up"} → 小车前进
  T=2.0s 小车遥测(enc1,enc2,steer) → 广播给 A 和 B
  T=2.5s 小车 GPS 定位(lat,lon,spd,fix=3) → 广播给 A 和 B

  T=3s   手机 B 按下 ← → ctrl{peerId:"B002", dir:"left"} → 小车左转（覆盖 A 的命令）
  T=3.0s 小车遥测 → 广播给 A 和 B

  T=5s   A 和 B 都松手 → 300ms 后服务器停止转发 → STM32 200ms 超时停车
  T=5.5s GPS 继续上报（控制停止不影响定位广播）

  T=10s  手机 B 断开 → A 收到通知: {code:1005, peerId:"B002", msg:"设备已离开"}
  T=15s  手机 A 发送 loc_cfg{interval:5000, src:["gps"]} → 服务器转发给小车模块，调整定位上报频率
```
