// ============================================================
// frontend/src/services/config.ts
// 配置文件加载器 — 从 public/config.yaml 读取，无硬编码兜底
// ============================================================

import { load } from 'js-yaml'

interface FrontendConfig {
  backend: { host: string; port: number }
  transpond: { host: string; port: number }
}

let _config: FrontendConfig | null = null

export async function loadConfig(): Promise<FrontendConfig> {
  if (_config) return _config

  const resp = await fetch('/config.yaml')
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
  }
  return _config
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
