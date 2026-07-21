// ============================================================
// frontend/src/api/session.ts
// Session 保存/列举/加载 API
// ============================================================

import { httpClient } from '@/network/http-client'
import type { SessionListItem } from '@/types/api'

/** 发送开始信号 → 后端引擎自动逐帧写盘 */
export async function startSessionSignal() {
  const res = await httpClient.post('/api/session/start', null, { timeout: 10000 })
  return res.data as { status: string; name: string }
}

/** 发送停止信号 → 后端写最终 manifest */
export async function stopSessionSignal() {
  const res = await httpClient.post('/api/session/stop', null, { timeout: 10000 })
  return res.data as { status: string }
}

export async function createSession(name: string, startTime: number, telemetryInterval = 100) {
  const res = await httpClient.post('/api/session/create', {
    name, start_time: startTime, telemetry_interval_ms: telemetryInterval,
  }, { timeout: 10000 })
  return res.data as { status: string; name: string }
}

export async function saveSessionFrame(data: {
  session_name: string; frame_id: number
  image_name: string; depth_name: string
  image_data: string; depth_data: string
}) {
  const res = await httpClient.post('/api/session/frame', data, { timeout: 30000 })
  return res.data as { status: string; frame_id: number }
}

export async function saveSessionManifest(name: string, manifest: any) {
  const res = await httpClient.post('/api/session/save', { name, manifest, frames: [] }, { timeout: 10000 })
  return res.data as { status: string; name: string; frame_count: number }
}

export async function listSessions() {
  const res = await httpClient.get('/api/session/list')
  return res.data as SessionListItem[]
}

export async function loadSessionManifest(name: string) {
  const res = await httpClient.get(`/api/session/${name}`)
  return res.data as any
}

export function getSessionFileUrl(sessionName: string, filePath: string) {
  return `${httpClient.defaults.baseURL}/api/session/files/${sessionName}/${filePath}`
}
