// ============================================================
// frontend/src/services/data-saver/data-saver.ts
// 数据保存层: 录制 session → 10帧批量 POST 到后端写盘
// ============================================================

import { createSession as apiCreate, saveSessionFrame, saveSessionManifest } from '@/api/session'
import type { Telemetry, Frame } from '@/types/data'

const BATCH_SIZE = 10 // 每批帧数

export interface Session {
  recordTelemetry(t: Telemetry): void
  recordFrame(f: Frame): Promise<void>
  finalize(): Promise<void>
  cancel(): void
}

export function createSession(): Session {
  const startTime = Date.now() / 1000
  const telemetry: Array<{ ts: number; speed: number; steering: number }> = []
  const frameMetas: Array<{ id: number; ts: number; image: string; depth: string }> = []
  const pendingFrames: Array<{ id: number; image_name: string; depth_name: string; image_data: string; depth_data: string }> = []
  let frameIdx = 0
  let sessionName = ''
  let cancelled = false
  let created = false

  async function ensureCreated() {
    if (created || cancelled) return
    const dt = new Date()
    sessionName = `session_${dt.getFullYear()}${pad(dt.getMonth() + 1)}${pad(dt.getDate())}_${pad(dt.getHours())}${pad(dt.getMinutes())}${pad(dt.getSeconds())}`
    await apiCreate(sessionName, startTime, 100)
    created = true
  }

  function recordTelemetry(t: Telemetry): void {
    if (cancelled) return
    telemetry.push({ ts: t.timestamp - startTime, speed: t.speed, steering: t.steering_angle })
  }

  async function recordFrame(f: Frame): Promise<void> {
    if (cancelled) return
    await ensureCreated()
    if (cancelled) return

    frameIdx++
    const id = frameIdx
    const imageName = `${String(id).padStart(5, '0')}.jpg`
    const depthName = `${String(id).padStart(5, '0')}.png`

    frameMetas.push({
      id, ts: f.timestamp - startTime,
      image: `frames/${imageName}`,
      depth: `frames/${depthName}`,
    })

    pendingFrames.push({
      id, image_name: imageName, depth_name: depthName,
      image_data: f.image, depth_data: f.depth_map,
    })

    if (pendingFrames.length >= BATCH_SIZE) await flushBatch()
  }

  async function flushBatch() {
    if (!pendingFrames.length) return
    const batch = pendingFrames.splice(0)
    try {
      await saveSessionFrame({ session_name: sessionName, frames: batch })
    } catch { /* 单批失败不中断 */ }
  }

  async function finalize(): Promise<void> {
    if (cancelled || !created) return
    await flushBatch()
    await saveSessionManifest(sessionName, {
      version: 1,
      start_time: startTime,
      end_time: Date.now() / 1000,
      frame_count: frameMetas.length,
      telemetry_interval_ms: 100,
      telemetry,
      frames: frameMetas,
    })
  }

  function cancel(): void {
    cancelled = true
    telemetry.length = 0
    frameMetas.length = 0
    pendingFrames.length = 0
  }

  return { recordTelemetry, recordFrame, finalize, cancel }
}

function pad(n: number) { return String(n).padStart(2, '0') }
