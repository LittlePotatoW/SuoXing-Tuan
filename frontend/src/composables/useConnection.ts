// ============================================================
// frontend/src/composables/useConnection.ts
// Vue 组合式函数：管理两个 WS 数据源（遥测+帧）的 connect/disconnect
//
// 设计与用法:
//   导出 useConnection()
//     connectAll()  同时连接遥测和帧数据源
//     disconnectAll()  断开所有 WS
//     reconnectAll()  断连后重连（设备切换时使用）
//   WS 客户端为模块级单例，多次调用返回同一组连接
//   监听 settings.telemetry / settings.frame 变化自动重连
// ============================================================

import { onUnmounted, watch, shallowRef } from 'vue'
import { createWSClient } from '@/network/websocket-client'
import { parseTelemetry, parseFrame } from '@/services/pack-unpack/parse'
import { useSettingsStore } from '@/stores/settings'
import { useConnectionStore } from '@/stores/connection'
import { useVehicleStore } from '@/stores/vehicle'
import { postTelemetry, postFrame } from '@/api/vehicle'
import { useEstimationStore } from '@/stores/estimation'
import type { Telemetry, Frame } from '@/types/data'

// ---------- 模块级单例状态 ----------
let telemetryWS: ReturnType<typeof createWSClient> | null = null
let frameWS: ReturnType<typeof createWSClient> | null = null
let lastFramePostTime = 0
const FRAME_POST_INTERVAL = 100  // ms, 10fps 限流

function _canSendFrame(): boolean {
  const now = performance.now()
  if (now - lastFramePostTime >= FRAME_POST_INTERVAL) {
    lastFramePostTime = now
    return true
  }
  return false
}
let onTelemetry: ((t: Telemetry) => void) | null = null
let onFrame: ((f: Frame) => void) | null = null
let watchersSetup = false
let modelingActive = false
const latestFrame = shallowRef<Frame | null>(null)

export function setRecordingHooks(
  telemetryHook: ((t: Telemetry) => void) | null,
  frameHook: ((f: Frame) => void) | null,
) {
  onTelemetry = telemetryHook
  onFrame = frameHook
}

/** 控制是否将数据转发到后端进行重建（实时建模页面控制） */
export function setModelingActive(active: boolean) {
  modelingActive = active
}

/** 获取最新帧数据（供主界面图像预览使用） */
export function useLatestFrame() {
  return latestFrame
}

function buildURL(source: { host: string; port: number }) {
  return `ws://${source.host}:${source.port}`
}

export function useConnection() {
  const settings = useSettingsStore()
  const conn = useConnectionStore()
  const vehicle = useVehicleStore()

  function connectAll() {
    disconnectAll()

    telemetryWS = createWSClient(buildURL(settings.telemetry))
    telemetryWS.onStatusChange(conn.setTelemetryStatus)
    telemetryWS.onMessage((raw) => {
      try {
        const data = parseTelemetry(raw)
        vehicle.updateTelemetry(data.speed, data.steering_angle)
        onTelemetry?.(data)
        if (modelingActive && useEstimationStore().shouldSendTelemetry) postTelemetry(data).catch(() => {})
      } catch { /* ignore malformed */ }
    })
    telemetryWS.connect()

    frameWS = createWSClient(buildURL(settings.frame))
    frameWS.onStatusChange(conn.setFrameStatus)
    frameWS.onMessage((raw) => {
      try {
        const data = parseFrame(raw)
        latestFrame.value = data
        onFrame?.(data)
        if (modelingActive && _canSendFrame()) postFrame(data).catch(() => {})
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

  function reconnectAll() {
    disconnectAll()
    connectAll()
  }

  // 只注册一次 watcher（模块级单例）
  if (!watchersSetup) {
    watchersSetup = true

    // 模式切换（LAN ↔ 服务器）时重连
    watch(() => settings.mode, () => {
      reconnectAll()
    })

    // IP / 端口变化时自动重连（设备切换）
    watch(
      [() => ({ ...settings.telemetry }), () => ({ ...settings.frame })],
      () => {
        reconnectAll()
      },
    )
  }

  onUnmounted(() => {
    disconnectAll()
  })

  return { connectAll, disconnectAll, reconnectAll }
}
