// ============================================================
// frontend/src/api/report.ts
// Report 保存/列举/加载 API
// ============================================================

import { httpClient } from '@/network/http-client'
import type { ReportListItem } from '@/types/api'

export async function saveReport(data: { filename: string; data: any }) {
  const res = await httpClient.post('/api/report/save', data)
  return res.data as { status: string; filename: string }
}

export async function listReports() {
  const res = await httpClient.get('/api/report/list')
  return res.data as ReportListItem[]
}

export async function loadReport(filename: string) {
  const res = await httpClient.get(`/api/report/${filename}`)
  return res.data as any
}

export async function startReportSignal(taskName?: string) {
  const res = await httpClient.post('/api/report/start', { task_name: taskName || '' }, { timeout: 10000 })
  return res.data as { status: string; name: string }
}

export async function stopReportSignal() {
  const res = await httpClient.post('/api/report/stop', null, { timeout: 10000 })
  return res.data as { status: string }
}

export async function exportReport(filename: string, format: 'md' | 'xlsx') {
  const res = await httpClient.post(`/api/report/${filename}/export`, null, {
    params: { format },
    timeout: 30000,
  })
  return res.data as { status: string; path: string }
}
