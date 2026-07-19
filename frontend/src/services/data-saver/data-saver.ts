// ============================================================
// frontend/src/services/data-saver/data-saver.ts
// 数据保存层 (Layer 0.5)：录制 session → POST 到后端写盘
// ============================================================

import { saveSession } from '@/api/session'
import type { Telemetry, Frame } from '@/types/data'

export interface Session {
  recordTelemetry(t: Telemetry): void
  recordFrame(f: Frame): void
  finalize(): Promise<void>
  cancel(): void
}

export function createSession(): Session {
  const startTime = Date.now() / 1000
  const telemetry: Array<{ ts: number; speed: number; steering: number }> = []
  const frameEntries: Array<{
    id: number; ts: number; imageName: string; depthName: string
    imageB64: string; depthB64: string
  }> = []

  function recordTelemetry(t: Telemetry): void {
    telemetry.push({ ts: t.timestamp - startTime, speed: t.speed, steering: t.steering_angle })
  }

  function recordFrame(f: Frame): void {
    const id = frameEntries.length + 1
    frameEntries.push({
      id, ts: f.timestamp - startTime,
      imageName: `${String(id).padStart(5, '0')}.jpg`,
      depthName: `${String(id).padStart(5, '0')}.png`,
      imageB64: f.image, depthB64: f.depth_map,
    })
  }

  async function finalize(): Promise<void> {
    const dt = new Date()
    const name = `session_${dt.getFullYear()}${pad(dt.getMonth() + 1)}${pad(dt.getDate())}_${pad(dt.getHours())}${pad(dt.getMinutes())}${pad(dt.getSeconds())}`

    const manifest = {
      version: 1,
      start_time: startTime,
      end_time: Date.now() / 1000,
      frame_count: frameEntries.length,
      telemetry_interval_ms: 100,
      telemetry,
      frames: frameEntries.map((f) => ({
        id: f.id, ts: f.ts,
        image: `frames/${f.imageName}`,
        depth: `frames/${f.depthName}`,
      })),
    }

    const frames = [
      ...frameEntries.map((f) => ({ filename: `frames/${f.imageName}`, data: f.imageB64 })),
      ...frameEntries.map((f) => ({ filename: `frames/${f.depthName}`, data: f.depthB64 })),
    ]

    await saveSession({ name, manifest, frames })
  }

  function cancel(): void { telemetry.length = 0; frameEntries.length = 0 }

  return { recordTelemetry, recordFrame, finalize, cancel }
}

function pad(n: number) { return String(n).padStart(2, '0') }
