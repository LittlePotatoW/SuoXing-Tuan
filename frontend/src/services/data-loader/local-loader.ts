// ============================================================
// frontend/src/services/data-loader/local-loader.ts
// 数据加载层 (Layer 0)：读取本地 session 目录（回放模式）
//
// 设计与用法:
//   导出 loadSession(dirHandle)  → Session
//   Session.telemetryList / frameIndex
//   Session.readFrame(id)        → Frame（含 base64 编码后的 image + depth_map）
// ============================================================

import type { Telemetry, Frame } from '@/types/data'
import { fileToBase64 } from '@/services/pack-unpack/parse'

// manifest.json 结构
interface Manifest {
  start_time: number
  telemetry_interval_ms: number
  telemetry: Array<{ ts: number; speed: number; steering: number }>
  frames: Array<{ id: number; ts: number; image: string; depth: string }>
}

export interface Session {
  /** 遥测数组（相对时间偏移） */
  telemetryList: Telemetry[]
  /** 帧索引 */
  frames: Manifest['frames']
  /** 录制开始时间 */
  startTime: number
  /** 读取一帧的图像和深度图（base64） */
  readFrame(id: number): Promise<Frame>
}

export async function loadSession(dirHandle: FileSystemDirectoryHandle): Promise<Session> {
  // 读 manifest.json
  const manifestFile = await dirHandle.getFileHandle('manifest.json')
  const file = await manifestFile.getFile()
  const text = await file.text()
  const manifest: Manifest = JSON.parse(text)

  // 遥测：相对 ts → 绝对时间戳
  const telemetryList: Telemetry[] = manifest.telemetry.map((t) => ({
    timestamp: manifest.start_time + t.ts,
    speed: t.speed,
    steering_angle: t.steering,
  }))

  async function readFrame(id: number): Promise<Frame> {
    const fi = manifest.frames.find((f) => f.id === id)
    if (!fi) throw new Error(`帧 ${id} 不存在`)

    const imgFile = await dirHandle.getFileHandle(fi.image)
    const depFile = await dirHandle.getFileHandle(fi.depth)
    const [image, depth_map] = await Promise.all([
      fileToBase64(await imgFile.getFile()),
      fileToBase64(await depFile.getFile()),
    ])

    return {
      frame_id: String(fi.id),
      timestamp: manifest.start_time + fi.ts,
      image,
      depth_map,
    }
  }

  return { telemetryList, frames: manifest.frames, startTime: manifest.start_time, readFrame }
}
