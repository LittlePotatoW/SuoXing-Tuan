// ============================================================
// frontend/src/services/pack-unpack/parse.ts
// 解包 (Layer 1)：原始数据 → 类型化对象
//
// 设计与用法:
//   导出 parseTelemetry()  WS 原始 JSON → Telemetry
//   导出 parseFrame()      WS 原始 JSON → Frame
//   导出 fileToBase64()    Blob → base64 字符串
// ============================================================

import type { Telemetry, Frame } from '@/types/data'

export function parseTelemetry(raw: string): Telemetry {
  const obj = JSON.parse(raw)
  return {
    timestamp: obj.timestamp ?? obj.ts ?? 0,
    speed: obj.speed ?? 0,
    steering_angle: obj.steering_angle ?? obj.steering ?? 0,
  }
}

export function parseFrame(raw: string): Frame {
  const obj = JSON.parse(raw)
  return {
    frame_id: obj.frame_id ?? '',
    timestamp: obj.timestamp ?? obj.ts ?? 0,
    image: obj.image ?? '',
    depth_map: obj.depth_map ?? obj.depth ?? '',
  }
}

export function fileToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      const comma = result.indexOf(',')
      resolve(comma >= 0 ? result.slice(comma + 1) : result)
    }
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}
