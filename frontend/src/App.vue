<!-- ============================================================ -->
<!-- frontend/src/App.vue                                            -->
<!-- 根组件 — 侧边栏 + 全局连接 + 多页面切换                          -->
<!-- ============================================================ -->

<template>
  <div style="display: flex; height: 100vh; font-family: monospace; font-size: 13px; background: #1A1A1A; color: #E0E0E0">
    <!-- 侧边栏 -->
    <Sidebar :items="menuItems" :currentPage="currentPage" @navigate="currentPage = $event" />

    <!-- 右侧主体 -->
    <div style="flex: 1; display: flex; flex-direction: column; overflow: hidden">
      <!-- 全局连接栏 -->
      <div style="display: flex; gap: 16px; padding: 8px 12px; align-items: center; border-bottom: 1px solid #333; min-height: 40px">
        <ConnectionBar :connected="connected" @connect="onConnect" @disconnect="onDisconnect" />
        <span v-if="error" style="color: #e74c3c; font-weight: bold">{{ error }}</span>
      </div>

      <!-- 页面内容 -->
      <div style="flex: 1; overflow: hidden">
        <CrackDetection v-if="currentPage === 'page1'" :connected="connected" />
        <Page2 v-else-if="currentPage === 'page2'" />
        <Page3 v-else-if="currentPage === 'page3'" />
        <Page4 v-else-if="currentPage === 'page4'" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { setHost, healthCheck } from './services/apiClient'
import ConnectionBar from './components/ConnectionBar.vue'
import Sidebar from './components/Sidebar.vue'
import type { SidebarItem } from './components/Sidebar.vue'
import CrackDetection from './views/CrackDetection.vue'
import Page2 from './views/Page2.vue'
import Page3 from './views/Page3.vue'
import Page4 from './views/Page4.vue'

const menuItems: SidebarItem[] = [
  { id: 'page1', label: '单张检测' },
  { id: 'page2', label: 'Page 2' },
  { id: 'page3', label: 'Page 3' },
  { id: 'page4', label: 'Page 4' },
]

const currentPage = ref('page1')
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
