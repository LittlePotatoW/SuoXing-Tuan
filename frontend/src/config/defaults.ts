// ============================================================
// frontend/src/config/defaults.ts
// 前端运行时配置，从 ../config.yaml 加载
//
// 设计与用法:
//   导出 NETWORK_MODE 枚举
//   导出 telemetrySource / frameSource / backendSource
//   导出 DEFAULT_POLL_INTERVAL / preprocess / save
// ============================================================

import { load as parseYaml } from 'js-yaml'
import configRaw from '../../config.yaml?raw'

interface Config {
  network: { mode: string }
  telemetry: { lan: { host: string; port: number }; server: { host: string; port: number } }
  frame: { lan: { host: string; port: number }; server: { host: string; port: number } }
  backend: { lan: { host: string; port: number }; server: { host: string; port: number } }
  poll_interval: number
  preprocess: {
    image: { flip: string; crop: any; resize: any; quality: number }
    depth: { flip: string; crop: any }
  }
  save: { path: string; auto_save: boolean }
}

const _config: Config = parseYaml(configRaw) as Config

export const NETWORK_MODE = { LAN: 'lan', SERVER: 'server' } as const
export type NetworkMode = typeof NETWORK_MODE[keyof typeof NETWORK_MODE]

export const telemetrySource = _config.telemetry
export const frameSource = _config.frame
export const backendSource = _config.backend
export const DEFAULT_POLL_INTERVAL = _config.poll_interval
export const preprocess = _config.preprocess
export const save = _config.save
