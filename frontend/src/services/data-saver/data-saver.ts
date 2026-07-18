// ============================================================
// frontend/src/services/data-saver/data-saver.ts
// 数据保存层 (Layer 0.5)：录制 session，内存缓存后导出下载
//
// 设计与用法:
//   导出 createSession()  → Session
//   Session.recordTelemetry(t) / recordFrame(f) / finalize() / cancel()
// ============================================================

import type { Telemetry, Frame } from '@/types/data'

interface ManifestEntry {
  telemetry: Array<{ ts: number; speed: number; steering: number }>
  frames: Array<{ id: number; ts: number; image: string; depth: string }>
}

export interface Session {
  recordTelemetry(t: Telemetry): void
  recordFrame(f: Frame): void
  finalize(): Promise<void>
  cancel(): void
}

export function createSession(): Session {
  const startTime = Date.now() / 1000
  const telemetry: ManifestEntry['telemetry'] = []
  const frames: ManifestEntry['frames'] = []
  const imageBlobs: Map<number, Blob> = new Map()
  const depthBlobs: Map<number, Blob> = new Map()

  function recordTelemetry(t: Telemetry): void {
    telemetry.push({
      ts: t.timestamp - startTime,
      speed: t.speed,
      steering: t.steering_angle,
    })
  }

  function recordFrame(f: Frame): void {
    const id = frames.length + 1
    const imageName = `${String(id).padStart(5, '0')}.jpg`
    const depthName = `${String(id).padStart(5, '0')}.png`

    frames.push({
      id,
      ts: f.timestamp - startTime,
      image: `frames/${imageName}`,
      depth: `frames/${depthName}`,
    })

    // base64 → Blob
    imageBlobs.set(id, _b64ToBlob(f.image, 'image/jpeg'))
    depthBlobs.set(id, _b64ToBlob(f.depth_map, 'image/png'))
  }

  async function finalize(): Promise<void> {
    const manifest = {
      version: 1,
      start_time: startTime,
      end_time: Date.now() / 1000,
      frame_count: frames.length,
      telemetry_interval_ms: 100,
      telemetry,
      frames,
    }

    const manifestBlob = new Blob(
      [JSON.stringify(manifest, null, 2)],
      { type: 'application/json' },
    )

    // 打包下载：用 JSZip 或逐个下载
    _downloadBlob(manifestBlob, 'manifest.json')

    for (const [id, blob] of imageBlobs) {
      const fi = frames.find((f) => f.id === id)
      if (fi) _downloadBlob(blob, fi.image.split('/').pop()!)
    }
    for (const [id, blob] of depthBlobs) {
      const fi = frames.find((f) => f.id === id)
      if (fi) _downloadBlob(blob, fi.depth.split('/').pop()!)
    }
  }

  function cancel(): void {
    telemetry.length = 0
    frames.length = 0
    imageBlobs.clear()
    depthBlobs.clear()
  }

  return { recordTelemetry, recordFrame, finalize, cancel }
}

function _b64ToBlob(b64: string, mime: string): Blob {
  const byteChars = atob(b64)
  const bytes = new Uint8Array(byteChars.length)
  for (let i = 0; i < byteChars.length; i++) {
    bytes[i] = byteChars.charCodeAt(i)
  }
  return new Blob([bytes], { type: mime })
}

function _downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
