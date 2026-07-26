import { robotState, updateRobotLocation, updateRobotTelemetry, updateRobotStatus } from './robotStore'
import type { RobotState } from './robotStore'

/**
 * WebSocket 通信层 — 对齐 API(1).md 中转服务器协议
 *
 * 端点:
 *   手机: ws://<host>/phone?room=<roomId>
 *   小车: ws://<host>/robot?room=<roomId>
 *
 * 消息类型:
 *   ctrl   — 手机→服务器→小车（控制指令，8方向+stop）
 *   tele   — 小车→服务器→手机（编码器遥测）
 *   loc    — 小车→服务器→手机（GPS定位）
 *   ping   — 手机→服务器（2秒心跳）
 *   sys    — 服务器→客户端（系统消息：加入/离开/错误）
 *   loc_cfg — 手机→服务器→小车（定位上报配置）
 */

// ---- 方向映射（8方向） ----
export const DIR_MAP: Record<string, string> = {
  forward: 'up', backward: 'down', left: 'left', right: 'right',
  forward_left: 'up_left', forward_right: 'up_right',
  backward_left: 'down_left', backward_right: 'down_right',
}

let socketTask: UniApp.SocketTask | null = null
let pingTimer: ReturnType<typeof setInterval> | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectAttempts = 0
const MAX_RECONNECT = 5

/** 连接服务器（手机端），host 格式：ip:port 或 域名:port */
export function connectRobot(host: string): void {
  if (socketTask) return

  const room = robotState.roomId
  // 开发环境用 ws，生产环境配置 SSL 后改 wss
  const protocol = host.startsWith('ws://') || host.startsWith('wss://') ? '' : 'ws://'
  const url = `${protocol}${host}/phone?room=${room}`

  robotState.mode = 'realtime'

  socketTask = uni.connectSocket({
    url,
    success() { console.log('[WS] connecting:', url) },
    fail(err) { console.error('[WS] connect failed:', err) },
  })

  socketTask.onOpen(() => {
    console.log('[WS] connected')
    robotState.connected = true
    reconnectAttempts = 0
    startPing()
  })

  socketTask.onMessage((res) => {
    try {
      const msg = JSON.parse(res.data as string)
      handleMessage(msg)
    } catch (e) { /* ignore malformed */ }
  })

  socketTask.onError((err) => {
    console.error('[WS] error:', err)
  })

  socketTask.onClose(() => {
    console.log('[WS] closed')
    robotState.connected = false
    socketTask = null
    stopPing()
    attemptReconnect(host)
  })
}

/** 断开连接 */
export function disconnectRobot(): void {
  stopPing()
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  if (socketTask) { socketTask.close({}); socketTask = null }
  robotState.connected = false
  robotState.peerId = ''
}

// ---- 消息发送 ----

/** 发送控制指令（8方向 + stop） */
export function sendCommand(dir: string): void {
  // 将内部方向映射为 API dir
  const apiDir = dir === 'stop' ? 'stop' : (DIR_MAP[dir] || dir)

  const msg = {
    type: 'ctrl',
    dir: apiDir,
    peerId: robotState.peerId,
    ts: Date.now(),
  }
  send(msg)
}

/** 发送心跳 */
function sendPing(): void {
  send({ type: 'ping', peerId: robotState.peerId })
}

/** 发送定位配置 */
export function sendLocConfig(interval: number, src: string[] = ['gps']): void {
  send({
    type: 'loc_cfg',
    peerId: robotState.peerId,
    interval,
    src,
  })
}

function send(data: Record<string, unknown>): void {
  if (socketTask && robotState.connected) {
    socketTask.send({
      data: JSON.stringify(data),
      fail(err) { console.error('[WS] send failed:', err) },
    })
  }
}

// ---- 消息处理 ----

function handleMessage(msg: Record<string, unknown>): void {
  switch (msg.type) {
    case 'sys':
      handleSys(msg)
      break
    case 'loc':
      handleLoc(msg)
      break
    case 'tele':
      handleTele(msg)
      break
    default:
      console.log('[WS] unhandled:', msg.type)
  }
}

/** 系统消息 */
function handleSys(msg: Record<string, unknown>): void {
  const code = msg.code as number
  switch (code) {
    case 1001: // 加入房间成功
      robotState.peerId = msg.peerId as string
      console.log('[WS] joined room, peerId:', robotState.peerId, msg.msg)
      // 配置定位上报间隔 2 秒
      sendLocConfig(2000, ['gps'])
      break
    case 1002: // 小车断开
      robotState.status = 'offline'
      console.log('[WS] robot disconnected')
      break
    case 1000: // 房间满
    case 1003: // 房间不存在
    case 4000: // 服务器错误
      console.warn('[WS] sys error:', code, msg.msg)
      break
    case 1004: // 新设备加入
    case 1005: // 设备离开
      console.log('[WS]', msg.msg)
      break
  }
}

/** 定位消息 */
function handleLoc(msg: Record<string, unknown>): void {
  const lat = msg.lat as number | null
  const lon = msg.lon as number | null
  const spd = msg.spd as number | undefined  // km/h
  const cog = msg.cog as number | undefined  // 航向角
  const alt = msg.alt as number | undefined
  const sat = msg.sat as number | undefined
  const fix = msg.fix as number | undefined
  const src = msg.src as string | undefined

  if (typeof lat === 'number' && typeof lon === 'number') {
    updateRobotLocation(lat, lon, cog, spd)
  }
  updateRobotStatus({
    fix: fix ?? 0,
    satellites: sat ?? 0,
    locSrc: (src as RobotState['locSrc']) ?? 'gps',
  })
  if (alt !== undefined) robotState.altitude = alt
}

/** 遥测消息 */
function handleTele(msg: Record<string, unknown>): void {
  const enc1 = msg.enc1 as number | undefined
  const enc2 = msg.enc2 as number | undefined
  const steer = msg.steer as number | undefined
  if (enc1 !== undefined && enc2 !== undefined && steer !== undefined) {
    updateRobotTelemetry(enc1, enc2, steer)
  }
  // 小车扩展字段（如果 API 后续支持）
  if (typeof msg.bat === 'number') updateRobotStatus({ battery: msg.bat as number })
  if (typeof msg.sig === 'string') updateRobotStatus({ signal: msg.sig as RobotState['signal'] })
}

// ---- 心跳 ----

function startPing(): void {
  stopPing()
  pingTimer = setInterval(sendPing, 2000)
}

function stopPing(): void {
  if (pingTimer) { clearInterval(pingTimer); pingTimer = null }
}

// ---- 重连 ----

function attemptReconnect(host: string): void {
  if (reconnectAttempts >= MAX_RECONNECT) return
  reconnectAttempts++
  const delay = Math.min(1000 * 2 ** reconnectAttempts, 30000)
  console.log(`[WS] reconnect in ${delay}ms (${reconnectAttempts}/${MAX_RECONNECT})`)
  reconnectTimer = setTimeout(() => connectRobot(host), delay)
}

import type { RobotState } from './robotStore'
