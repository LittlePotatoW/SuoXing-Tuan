// ============================================================
// frontend/src/stores/config.ts
// 全局配置 store — 服务器地址、连接状态
// ============================================================

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getConfig, loadConfig } from '../services/config'

export const useConfigStore = defineStore('config', () => {
  const backendHost = ref('localhost')
  const backendPort = ref(8000)
  const transpondHost = ref('localhost')
  const transpondPort = ref(8001)
  const controlHost = ref('127.0.0.1')
  const controlPort = ref(8080)
  const loaded = ref(false)

  async function init() {
    await loadConfig()
    const cfg = getConfig()
    backendHost.value = cfg.backend.host
    backendPort.value = cfg.backend.port
    transpondHost.value = cfg.transpond.host
    transpondPort.value = cfg.transpond.port
    if (cfg.control) {
      controlHost.value = cfg.control.host
      controlPort.value = cfg.control.port
    }
    loaded.value = true
  }

  return {
    backendHost, backendPort,
    transpondHost, transpondPort,
    controlHost, controlPort,
    loaded, init,
  }
})
