// ============================================================
// frontend/src/services/transpondClient.ts
// TranspondServer API 客户端 — 封装全部 REST + WebSocket 接口
// ============================================================

export interface TranspondStatus {
  location_cached: number
  sensor_cached: number
}

export interface TranspondQueryParams {
  after?: number
  limit?: number
}

export type StreamMode = 'all' | 'location' | 'sensor'

const DEFAULT_TIMEOUT = 30000

export function createTranspondClient(baseUrl: string, timeout = DEFAULT_TIMEOUT) {
  const url = (path: string, params?: Record<string, string | number>) => {
    const u = baseUrl.replace(/\/+$/, '') + path
    if (!params) return u
    const qs = Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null)
      .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
      .join('&')
    return qs ? u + '?' + qs : u
  }

  const request = async (method: string, path: string, body?: unknown, params?: Record<string, string | number>) => {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeout)
    try {
      const resp = await fetch(url(path, params), {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      })
      const json = await resp.json()
      return { status: resp.status, data: json, error: null }
    } catch (e: any) {
      return { status: null, data: null, error: e.message || String(e) }
    } finally {
      clearTimeout(timer)
    }
  }

  return {
    // POST /location — 上传定位数据
    postLocation(loc: unknown) {
      return request('POST', '/location', loc)
    },

    // POST /frames — 上传批量传感器数据
    postFrames(batch: { count: number; frames: unknown[] }) {
      return request('POST', '/frames', batch)
    },

    // POST /debug — 调试指令
    postDebug(action: 'clear' | 'status') {
      return request('POST', '/debug', { action })
    },

    // GET /status — 查询缓存量
    getStatus() {
      return request('GET', '/status')
    },

    // GET /location — 查询定位数据
    getLocations(params?: TranspondQueryParams) {
      return request('GET', '/location', undefined, params as Record<string, string | number>)
    },

    // GET /sensor — 查询传感器数据
    getSensors(params?: TranspondQueryParams) {
      return request('GET', '/sensor', undefined, params as Record<string, string | number>)
    },

    // WS /stream — 实时推送
    connectStream(mode: StreamMode, onMessage: (msg: unknown) => void): WebSocket {
      const wsUrl = baseUrl.replace(/^http/, 'ws').replace(/\/+$/, '') + `/stream?mode=${mode}`
      const ws = new WebSocket(wsUrl)
      ws.onmessage = (e) => {
        try { onMessage(JSON.parse(e.data)) } catch { /* ignore parse errors */ }
      }
      return ws
    },
  }
}

export type TranspondClient = ReturnType<typeof createTranspondClient>
