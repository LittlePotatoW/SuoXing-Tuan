// ============================================================
// frontend/src/services/config.ts
// 配置文件加载器 — 从 public/config.yaml 读取，无硬编码兜底
// ============================================================

import { load } from 'js-yaml'

interface FrontendConfig {
  backend: { host: string; port: number }
  transpond: { host: string; port: number }
  control?: { host: string; port: number }
  timeout?: { backend_ms: number; transpond_ms: number }
}

let _config: FrontendConfig | null = null

export async function loadConfig(): Promise<FrontendConfig> {
  if (_config) return _config

  try {
    const resp = await fetch('/config.yaml')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const text = await resp.text()
    const parsed = load(text) as any

    _config = {
      backend: {
        host: parsed?.backend?.host || 'localhost',
        port: parsed?.backend?.port || 8000,
      },
      transpond: {
        host: parsed?.transpond?.host || 'localhost',
        port: parsed?.transpond?.port || 8001,
      },
      control: {
        host: parsed?.control?.host || '127.0.0.1',
        port: parsed?.control?.port || 8080,
      },
      timeout: {
        backend_ms: parsed?.timeout?.backend_ms || 30000,
        transpond_ms: parsed?.timeout?.transpond_ms || 30000,
      },
    }
  } catch (e) {
    console.warn('[Config] load failed, using defaults:', e)
    _config = {
      backend: { host: 'localhost', port: 8000 },
      transpond: { host: 'localhost', port: 8001 },
      control: { host: '127.0.0.1', port: 8080 },
      timeout: { backend_ms: 30000, transpond_ms: 30000 },
    }
  }
  return _config
}

export function getControlUrl(): string {
  const c = cfg()
  if (!c.control) return 'http://127.0.0.1:8080'
  return `http://${c.control.host}:${c.control.port}`
}

export function getTimeout() {
  const c = cfg()
  return c.timeout || { backend_ms: 30000, transpond_ms: 30000 }
}

export function getConfig(): FrontendConfig {
  if (!_config) throw new Error('config not loaded — call loadConfig() first')
  return _config
}

function cfg(): FrontendConfig { return getConfig() }

export function getBackendUrl(): string {
  const c = cfg()
  return `http://${c.backend.host}:${c.backend.port}`
}

export function getTranspondUrl(): string {
  const c = cfg()
  return `http://${c.transpond.host}:${c.transpond.port}`
}
