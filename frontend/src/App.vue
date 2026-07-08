<!-- ============================================================ -->
<!-- frontend/src/App.vue                                            -->
<!-- 根组件 — 侧边栏 + 全局连接 + router-view                        -->
<!-- ============================================================ -->

<template>
  <div style="display: flex; height: 100vh; font-family: monospace; font-size: 13px; background: #1A1A1A; color: #E0E0E0">
    <Sidebar />
    <div style="flex: 1; display: flex; flex-direction: column; overflow: hidden">
      <div style="display: flex; gap: 16px; padding: 8px 12px; align-items: center; border-bottom: 1px solid #333; min-height: 40px">
        <ConnectionBar :connected="connected" @connect="onConnect" @disconnect="onDisconnect" />
        <span v-if="error" style="color: #e74c3c; font-weight: bold">{{ error }}</span>
      </div>
      <div style="flex: 1; overflow: hidden">
        <router-view :connected="connected" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { setHost, healthCheck } from './services/apiClient'
import ConnectionBar from './components/ConnectionBar.vue'
import Sidebar from './components/Sidebar.vue'

const connected = ref(false)
const error = ref('')

async function onConnect(host: string, port: number) {
  error.value = ''
  setHost(host, port)
  try {
    await healthCheck()
    connected.value = true
  } catch (e) {
    error.value = '连接失败: ' + (e as Error).message
  }
}

function onDisconnect() {
  connected.value = false
  error.value = ''
}
</script>
