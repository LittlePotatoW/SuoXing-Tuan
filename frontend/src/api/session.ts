// ============================================================
// frontend/src/api/session.ts
// Session 保存/列举/加载 API
// ============================================================

import { httpClient } from '@/network/http-client'
import type { SessionListItem } from '@/types/api'

export async function saveSession(data: {
  name: string; manifest: any; frames: { filename: string; data: string }[]
}) {
  const res = await httpClient.post('/api/session/save', data)
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

/** 获取 session 帧文件的完整 URL */
export function getSessionFileUrl(sessionName: string, filePath: string) {
  return `${httpClient.defaults.baseURL}/api/session/files/${sessionName}/${filePath}`
}
