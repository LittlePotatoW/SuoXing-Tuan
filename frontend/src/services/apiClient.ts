// ============================================================
// frontend/src/services/apiClient.ts
// 后端 REST API 客户端 — 推理请求、模型上传、健康检查
// ============================================================

let baseUrl = 'http://localhost:8000'
const DEFAULT_TIMEOUT_MS = 30_000

function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  return fetch(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(timer))
}

export function setHost(host: string, port: number) {
  baseUrl = `http://${host}:${port}`
}

export function getBaseUrl() {
  return baseUrl
}

export async function healthCheck() {
  const res = await fetchWithTimeout(`${baseUrl}/api/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json()
}

export async function runInference(file: File) {
  const form = new FormData()
  form.append('image', file)
  const res = await fetchWithTimeout(`${baseUrl}/api/inference`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Inference failed: ${res.status}`)
  return res.json()
}

export async function uploadModel(file: File) {
  const form = new FormData()
  form.append('model_file', file)
  const res = await fetchWithTimeout(`${baseUrl}/api/model/load`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Model load failed: ${res.status}`)
  return res.json()
}
