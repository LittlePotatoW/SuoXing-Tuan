// ============================================================
// frontend/src/types/data.ts
// TypeScript 类型：业务数据结构
// ============================================================

/** 小车位置 */
export interface Position {
  timestamp: number
  x: number
  y: number
  heading: number
}

/** 遥测数据 */
export interface Telemetry {
  timestamp: number
  speed: number
  steering_angle: number
}

/** 帧数据 */
export interface Frame {
  frame_id: string
  timestamp: number
  image: string
  depth_map: string
}

/** 检测结果 */
export interface Detection {
  id: number
  class_name: string
  confidence: number
  bbox_2d: [number, number, number, number]
  center_3d: [number, number, number]
}
