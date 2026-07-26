// ============================================================
// frontend/src/services/data-loader/local-loader.ts
// 数据加载层 (Layer 0)：从后端 API 读取 session 数据
//
// 设计与用法:
//   导出 loadSession(name)  → Session
//   Session.telemetryList / frames
//   Session.readFrame(id)    → Frame（含 base64 编码后的 image + depth_map）
// ============================================================

import { loadSessionManifest, getSessionFileUrl } from '@/api/session'
import { fileToBase64 } from '@/services/pack-unpack/parse'
import type { Telemetry, Frame } from '@/types/data'

interface Manifest {
  start_time: number
  telemetry_interval_ms: number
  telemetry: Array<{ ts: number; speed: number; steering: number }>
  frames: Array<{ id: number; ts: number; image: string; depth: string }>
}

export interface Session {
  telemetryList: Telemetry[]
  frames: Manifest['frames']
  startTime: number
  readFrame(id: number): Promise<Frame>
}

export async function loadSession(sessionName: string): Promise<Session> {
  const manifest: Manifest = await loadSessionManifest(sessionName)

  const telemetryList: Telemetry[] = manifest.telemetry.map((t) => ({
    timestamp: manifest.start_time + t.ts,
    speed: t.speed,
    steering_angle: t.steering,
  }))

  async function readFrame(id: number): Promise<Frame> {
    const fi = manifest.frames.find((f) => f.id === id)
    if (!fi) throw new Error(`帧 ${id} 不存在`)

    const [imgResp, depResp] = await Promise.all([
      fetch(getSessionFileUrl(sessionName, fi.image)),
      fetch(getSessionFileUrl(sessionName, fi.depth)),
    ])
    const [image, depth_map] = await Promise.all([
      fileToBase64(await imgResp.blob()),
      fileToBase64(await depResp.blob()),
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
