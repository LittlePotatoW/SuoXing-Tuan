// ============================================================
// frontend/src/stores/connection.ts
// Pinia: 连接状态 — 遥测/帧数据源的 WebSocket 状态
//
// 设计与用法:
//   导出 useConnectionStore()
//     telemetryStatus / frameStatus / overall / color (响应式)
//     setTelemetryStatus() / setFrameStatus()  更新 WS 状态
// ============================================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WSStatus } from '@/network/websocket-client'

export const useConnectionStore = defineStore('connection', () => {
  const telemetryStatus = ref<WSStatus>('disconnected')
  const frameStatus = ref<WSStatus>('disconnected')

  const overall = computed(() => {
    if (telemetryStatus.value === 'connected' && frameStatus.value === 'connected') return 'connected'
    if (telemetryStatus.value === 'reconnecting' || frameStatus.value === 'reconnecting') return 'reconnecting'
    if (telemetryStatus.value === 'connecting' || frameStatus.value === 'connecting') return 'connecting'
    return 'disconnected'
  })

  const color = computed(() => {
    switch (overall.value) {
      case 'connected': return 'green'
      case 'connecting':
      case 'reconnecting': return 'yellow'
      default: return 'red'
    }
  })

  function setTelemetryStatus(s: WSStatus) { telemetryStatus.value = s }
  function setFrameStatus(s: WSStatus) { frameStatus.value = s }

  return { telemetryStatus, frameStatus, overall, color, setTelemetryStatus, setFrameStatus }
})
