import { reactive } from 'vue'

/** m/s ↔ km/h 换算因子 */
export const MS_TO_KMH = 3.6

/**
 * 机器人实时状态 — 模块级 reactive 单例
 * 数据结构对齐 API(1).md 中转服务器 WebSocket 协议
 */

export interface RobotState {
  // ---- 连接 ----
  connected: boolean
  mode: 'simulation' | 'realtime'
  roomId: string
  peerId: string

  // ---- 定位（对齐 API loc 消息，WGS-84 原始坐标） ----
  robotId: string
  latitude: number       // WGS-84
  longitude: number      // WGS-84
  speedKmh: number       // km/h（API 原始值）
  heading: number        // 航向角 cog 0-360（0=正北）
  altitude: number       // 海拔 m
  satellites: number     // 参与定位卫星数
  fix: number            // 0=未定位 1=2D 2=3D
  locSrc: string         // gps / lbs / wifi

  // ---- 遥测（对齐 API tele 消息） ----
  enc1: number           // 电机1编码器脉冲
  enc2: number           // 电机2编码器脉冲
  steer: number          // 转向舵机 PWM

  // ---- 派生/UI 字段（API 暂无，模拟或小车扩展） ----
  battery: number        // 电量 0-100（需小车扩展 tele.bat）
  signal: string         // 信号（需小车扩展 tele.sig）
  status: 'online' | 'offline' | 'running' | 'error'
  mileage: number        // 累计里程 km
  controlDirection: string
  controlSpeed: number   // m/s（UI 显示用）

  // ---- 巡检路线 ----
  path: Array<{ latitude: number; longitude: number }>
  nextPoint: string
}

export const robotState = reactive<RobotState>({
  connected: false,
  mode: 'simulation',
  roomId: 'car001',
  peerId: '',

  robotId: 'A-03',
  latitude: 39.9923,
  longitude: 116.3265,
  speedKmh: 0,
  heading: 0,
  altitude: 50,
  satellites: 0,
  fix: 0,
  locSrc: 'gps',

  enc1: 0,
  enc2: 0,
  steer: 150,

  battery: 85,
  signal: '强',
  status: 'running',
  mileage: 2.8,
  controlDirection: '',
  controlSpeed: 0,

  path: [
    { latitude: 39.9908, longitude: 116.3248 },
    { latitude: 39.9923, longitude: 116.3265 },
    { latitude: 39.9941, longitude: 116.3282 },
    { latitude: 39.9935, longitude: 116.3301 },
  ],
  nextPoint: 'K12+450',
})

/** 更新定位（API loc 消息） */
export function updateRobotLocation(lat: number, lng: number, cog?: number, spdKmh?: number): void {
  robotState.latitude = lat
  robotState.longitude = lng
  if (cog !== undefined) robotState.heading = cog
  if (spdKmh !== undefined) {
    robotState.speedKmh = spdKmh
    robotState.controlSpeed = +(spdKmh / MS_TO_KMH).toFixed(2) // km/h → m/s
  }
}

/** 更新遥测（API tele 消息） */
export function updateRobotTelemetry(enc1: number, enc2: number, steer: number): void {
  robotState.enc1 = enc1
  robotState.enc2 = enc2
  robotState.steer = steer
}

/** 更新扩展状态 */
export function updateRobotStatus(
  partial: Partial<Pick<RobotState, 'battery' | 'signal' | 'status' | 'mileage' | 'fix' | 'satellites' | 'locSrc'>>,
): void {
  Object.assign(robotState, partial)
}

export function setRobotMode(mode: 'simulation' | 'realtime'): void {
  robotState.mode = mode
}
