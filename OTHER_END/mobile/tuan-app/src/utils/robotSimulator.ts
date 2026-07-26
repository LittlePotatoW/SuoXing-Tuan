import { robotState, MS_TO_KMH, updateRobotLocation, updateRobotStatus, updateRobotTelemetry } from './robotStore'
import type { RobotState } from './robotStore'

/**
 * 机器人 GPS 模拟器（对齐 API 协议）
 * - 自动模式：沿巡检路线 polyline 匀速移动
 * - 手动模式：响应遥控页面摇杆，8方向自由移动
 * - 遥测：生成 enc1/enc2/steer 编码器数据
 * - 定位：生成 loc 格式 GPS 数据（速度 km/h）
 */

const M_PER_DEG_LAT = 111000
const TICK_MS = 1000
const M_TO_KM = 1000
const DEFAULT_AUTO_SPEED_MS = 1.5
const ENCODER_PULSE_RATE = 65
const STEER_CENTER = 150
const BATTERY_TICK_INTERVAL = 60
const SIGNAL_TICK_INTERVAL = 30
const BATTERY_MIN = 5

/** 8方向航向角映射 */
const HEADING_ANGLES: Record<string, number> = {
  forward: 0, backward: 180, left: 270, right: 90,
  forward_left: 315, forward_right: 45,
  backward_left: 225, backward_right: 135,
}

/** 随机刷新信号强度 */
function randomizeSignal(): void {
  const signals: Array<RobotState['signal']> = ['强', '强', '强', '中', '弱']
  updateRobotStatus({ signal: signals[Math.floor(Math.random() * signals.length)] })
}

let timer: ReturnType<typeof setInterval> | null = null
let pathIndex = 0
let forward = true
let progress = 0
let elapsed = 0
let pulseCount = 0 // 模拟编码器脉冲累计

// ---- 工具 ----

function distMeters(a: { latitude: number; longitude: number }, b: { latitude: number; longitude: number }): number {
  const dLat = (b.latitude - a.latitude) * M_PER_DEG_LAT
  const dLng = (b.longitude - a.longitude) * M_PER_DEG_LAT * Math.cos(((a.latitude + b.latitude) / 2) * (Math.PI / 180))
  return Math.sqrt(dLat * dLat + dLng * dLng)
}

function interpolate(a: { latitude: number; longitude: number }, b: { latitude: number; longitude: number }, t: number) {
  return { latitude: a.latitude + (b.latitude - a.latitude) * t, longitude: a.longitude + (b.longitude - a.longitude) * t }
}

// ---- 主 tick ----

function tick(): void {
  elapsed++
  if (robotState.controlDirection) {
    tickManual()
  } else {
    tickAuto()
  }
  tickTelemetry()
  tickBattery()
}

/** 手动遥控：8方向移动 */
function tickManual(): void {
  const dir = robotState.controlDirection
  const head = HEADING_ANGLES[dir] ?? 0
  const rad = (head * Math.PI) / 180
  const speedMs = robotState.controlSpeed // m/s
  const dist = speedMs
  const cosLat = Math.cos((robotState.latitude * Math.PI) / 180)

  const dLat = (dist * Math.cos(rad)) / M_PER_DEG_LAT
  const dLng = (dist * Math.sin(rad)) / (M_PER_DEG_LAT * cosLat)

  // 更新为 WGS-84 坐标（模拟器直接生成，无需转换）
  updateRobotLocation(
    robotState.latitude + dLat,
    robotState.longitude + dLng,
    head,
    +(speedMs * MS_TO_KMH).toFixed(1),
  )
  updateRobotStatus({ mileage: +(robotState.mileage + dist / M_TO_KM).toFixed(2) })
  updateRobotStatus({ fix: 3, satellites: 12, locSrc: 'gps' })

  // 编码器模拟
  pulseCount += Math.round(speedMs * 100)
  updateRobotTelemetry(pulseCount, pulseCount + Math.round(Math.random() * 5), STEER_CENTER)
}

/** 自动巡航：沿 polyline 移动 */
function tickAuto(): void {
  const path = robotState.path
  if (path.length < 2) return

  const nextIndex = forward ? pathIndex + 1 : pathIndex - 1
  if (nextIndex < 0 || nextIndex >= path.length) {
    forward = !forward
    pathIndex = forward ? 0 : path.length - 1
    return
  }

  const from = path[pathIndex]
  const to = path[nextIndex]
  const segDist = distMeters(from, to)
  const speedMs = robotState.controlDirection ? robotState.controlSpeed : DEFAULT_AUTO_SPEED_MS
  const stepRatio = segDist > 0 ? speedMs / segDist : 0
  progress += stepRatio

  if (progress >= 1) {
    progress = 0
    pathIndex = nextIndex
    robotState.nextPoint = `K12+${300 + (forward ? pathIndex : path.length - 1 - pathIndex) * 150}`
  }

  const pos = interpolate(from, to, Math.min(progress, 1))
  const rawHeading = (Math.atan2((to.longitude - from.longitude) * (forward ? 1 : -1), (to.latitude - from.latitude) * (forward ? 1 : -1)) * 180) / Math.PI + 90
  const heading = ((rawHeading % 360) + 360) % 360

  updateRobotLocation(pos.latitude, pos.longitude, heading, +(speedMs * MS_TO_KMH).toFixed(1))
  updateRobotStatus({ mileage: +(robotState.mileage + speedMs / M_TO_KM).toFixed(2) })

  if (elapsed % SIGNAL_TICK_INTERVAL === 0) {
    randomizeSignal()
  }
}

/** 编码器遥测 */
function tickTelemetry(): void {
  pulseCount += Math.round(robotState.controlSpeed * ENCODER_PULSE_RATE)
  const enc1 = pulseCount
  const isTurningLeft = robotState.controlDirection.includes('left')
  const isTurningRight = robotState.controlDirection.includes('right')
  const enc2 = pulseCount + (isTurningLeft ? -20 : isTurningRight ? 20 : Math.round(Math.random() * 5))
  const steer = isTurningLeft ? 120 : isTurningRight ? 180 : STEER_CENTER
  updateRobotTelemetry(enc1, enc2, steer)
}

function tickBattery(): void {
  if (elapsed % BATTERY_TICK_INTERVAL === 0 && robotState.battery > BATTERY_MIN) {
    updateRobotStatus({ battery: robotState.battery - 1 })
  }
  if (elapsed % SIGNAL_TICK_INTERVAL === 0) {
    randomizeSignal()
  }
}

// ---- 公开 API ----

export function startSimulation(): void {
  if (timer) return
  robotState.connected = true
  robotState.mode = 'simulation'
  robotState.status = 'running'
  robotState.controlSpeed = DEFAULT_AUTO_SPEED_MS
  pathIndex = 0; progress = 0; forward = true; elapsed = 0
  tick()
  timer = setInterval(tick, TICK_MS)
}

export function stopSimulation(): void {
  if (timer) { clearInterval(timer); timer = null }
  robotState.connected = false
  robotState.controlSpeed = 0
  robotState.status = 'online'
  updateRobotTelemetry(0, 0, 150)
}

/** 遥控方向（8方向 + stop） */
export function simSetDirection(dir: string): void {
  if (dir === 'stop' || dir === '') {
    robotState.controlDirection = ''
    robotState.controlSpeed = 0
    robotState.speedKmh = 0
    updateRobotTelemetry(pulseCount, pulseCount, 150)
  } else {
    robotState.controlDirection = dir
    robotState.controlSpeed = 0.8 + Math.random() * 0.6
    robotState.speedKmh = +(robotState.controlSpeed * 3.6).toFixed(1)
  }
}
