// ============================================================
// frontend/src/stores/settings.ts
// Pinia: 用户配置 — 网络模式、三组 IP/端口
//
// 设计与用法:
//   导出 useSettingsStore()
//     mode / telemetry / frame / backend (响应式状态)
//     switchMode()  切换 LAN ↔ Server
//     applyBackendURL()  更新 HTTP 连接地址
//     applyDevice(device)  选中设备一键填入 LAN 地址
// ============================================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { NETWORK_MODE, telemetrySource, frameSource, backendConfig } from '@/config/defaults'
import { setBaseURL } from '@/network/http-client'
import type { NetworkMode } from '@/config/defaults'
import type { LanDevice } from '@/composables/useLanScan'

export const useSettingsStore = defineStore('settings', () => {
  const mode = ref<NetworkMode>(NETWORK_MODE.LAN)

  const telemetry = ref({ ...telemetrySource.lan })
  const frame = ref({ ...frameSource.lan })
  const backend = ref({ ...backendConfig })

  const sources = computed(() => ({
    lan: { telemetry: telemetrySource.lan, frame: frameSource.lan },
    server: { telemetry: telemetrySource.server, frame: frameSource.server },
    direct: { telemetry: telemetrySource.direct, frame: frameSource.direct },
  }))

  function applyBackendURL() {
    setBaseURL(backend.value.host, backend.value.port)
  }

  function switchMode(newMode: NetworkMode) {
    mode.value = newMode
    const cfg = sources.value[newMode]
    telemetry.value = { ...cfg.telemetry }
    frame.value = { ...cfg.frame }
    // backend 永远不变，不随模式切换
    applyBackendURL()
  }

  function applyDevice(device: LanDevice) {
    mode.value = NETWORK_MODE.LAN
    telemetry.value = { host: device.ip, port: telemetry.value.port }
    frame.value = { host: device.ip, port: frame.value.port }
  }

  applyBackendURL()

  return { mode, telemetry, frame, backend, sources,
           switchMode, applyBackendURL, applyDevice }
})
