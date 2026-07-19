// ============================================================
// frontend/src/composables/useConnection.ts
// Vue 组合式函数：管理两个 WS 数据源（遥测+帧）的 connect/disconnect
//
// 设计与用法:
//   导出 useConnection()
//     connectAll()  同时连接遥测和帧数据源
//     disconnectAll()  断开所有 WS
//   监听 settings.mode 变化自动重连
// ============================================================

import { onUnmounted, watch } from 'vue'
import { createWSClient } from '@/network/websocket-client'
import { parseTelemetry, parseFrame } from '@/services/pack-unpack/parse'
import { useSettingsStore } from '@/stores/settings'
import { useConnectionStore } from '@/stores/connection'
import { useVehicleStore } from '@/stores/vehicle'
import { postTelemetry, postFrame } from '@/api/vehicle'
import type { Telemetry, Frame } from '@/types/data'

let onTelemetry: ((t: Telemetry) => void) | null = null
let onFrame: ((f: Frame) => void) | null = null

export function setRecordingHooks(
  telemetryHook: ((t: Telemetry) => void) | null,
  frameHook: ((f: Frame) => void) | null,
) {
  onTelemetry = telemetryHook
  onFrame = frameHook
}

export function useConnection() {
  const settings = useSettingsStore()
  const conn = useConnectionStore()
  const vehicle = useVehicleStore()

  let telemetryWS: ReturnType<typeof createWSClient> | null = null
  let frameWS: ReturnType<typeof createWSClient> | null = null

  function buildURL(source: { host: string; port: number }) {
    return `ws://${source.host}:${source.port}`
  }

  function connectAll() {
    disconnectAll()

    telemetryWS = createWSClient(buildURL(settings.telemetry))
    telemetryWS.onStatusChange(conn.setTelemetryStatus)
    telemetryWS.onMessage((raw) => {
      try {
        const data = parseTelemetry(raw)
        vehicle.updateTelemetry(data.speed, data.steering_angle)
        onTelemetry?.(data)
        // 转发给后端 API
        postTelemetry(data).catch(() => {})
      } catch { /* ignore malformed */ }
    })
    telemetryWS.connect()

    frameWS = createWSClient(buildURL(settings.frame))
    frameWS.onStatusChange(conn.setFrameStatus)
    frameWS.onMessage((raw) => {
      try {
        const data = parseFrame(raw)
        onFrame?.(data)
        postFrame(data).catch(() => {})
      } catch { /* ignore malformed */ }
    })
    frameWS.connect()
  }

  function disconnectAll() {
    telemetryWS?.close()
    frameWS?.close()
    telemetryWS = null
    frameWS = null
  }

  // 网络模式切换时自动重连
  watch(() => settings.mode, () => {
    connectAll()
  })

  onUnmounted(() => {
    disconnectAll()
  })

  return { connectAll, disconnectAll }
}
