<!-- ============================================================ -->
<!-- frontend/src/components/layout/AppStatusBar.vue               -->
<!-- 顶部状态栏：连接状态 + 模式切换 + 设备扫描                   -->
<!-- ============================================================ -->
<template>
  <header class="status-bar">
    <span class="dot" :class="connected ? 'green' : 'red'"></span>
    <span class="text">{{ connected ? '已连接' : '未连接' }}</span>

    <button class="btn" @click="connected = !connected">
      {{ connected ? '断开' : '连接' }}
    </button>

    <!-- 局域网模式: 扫描设备按钮 -->
    <div v-if="settings.mode === 'lan'" class="scan-wrap">
      <button class="btn" @click="toggleScan" :disabled="scanning">
        {{ scanning ? '扫描中...' : '扫描设备 ▾' }}
      </button>
      <div v-if="showScan" class="scan-dropdown">
        <!-- 扫描进度 -->
        <div v-if="scanning" class="scan-status">
          扫描 {{ subnet }}.x ({{ progress }}/254)
        </div>
        <!-- 扫描完成无结果 -->
        <div v-else-if="mockDevices.length === 0" class="scan-empty">
          未发现设备
        </div>
        <!-- 设备列表 -->
        <div
          v-for="d in mockDevices"
          :key="d.ip"
          class="scan-item"
          @click="onSelectDevice(d)"
        >
          <span class="scan-ip">{{ d.ip }}</span>
          <span class="scan-ports">
            <span :class="d.telemetry ? 'port-ok' : 'port-fail'">T</span>
            <span :class="d.frame ? 'port-ok' : 'port-fail'">F</span>
          </span>
        </div>
      </div>
    </div>

    <!-- 当前连接目标 -->
    <span class="target-info">
      遥测: {{ settings.telemetry.host }}:{{ settings.telemetry.port }}
      | 帧: {{ settings.frame.host }}:{{ settings.frame.port }}
    </span>

    <span class="spacer"></span>
    <span class="mode-label">{{ modeLabel }}</span>
    <button class="btn" @click="toggleMode">切换</button>
  </header>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useConnection } from '@/composables/useConnection'
import { useConnectionStore } from '@/stores/connection'
import { useSettingsStore } from '@/stores/settings'
import { useLanScan } from '@/composables/useLanScan'
import type { LanDevice } from '@/composables/useLanScan'

const settings = useSettingsStore()
const connStore = useConnectionStore()
const { connectAll, disconnectAll } = useConnection()
const { devices, scanning, progress, subnet, scan } = useLanScan()

const modeLabel = computed(() => {
  switch (settings.mode) {
    case 'lan': return '局域网直连'
    case 'server': return '服务器中转'
    case 'direct': return '本地直连'
    default: return settings.mode
  }
})

const connected = ref(false)
const showScan = ref(false)
const mockDevices = ref<LanDevice[]>([])

watch(() => connStore.overall, (v) => { connected.value = v === 'connected' }, { immediate: true })
watch(connected, (v) => { v ? connectAll() : disconnectAll() })

async function toggleScan() {
  showScan.value = !showScan.value
  if (showScan.value) {
    await scan()
    mockDevices.value = devices.value
  }
}

function onSelectDevice(d: LanDevice) {
  settings.applyDevice(d)
  showScan.value = false
}

function toggleMode() {
  const order: Array<'lan' | 'server' | 'direct'> = ['lan', 'server', 'direct']
  const idx = order.indexOf(settings.mode)
  settings.switchMode(order[(idx + 1) % order.length])
}
</script>

<style scoped>
.status-bar { height: 36px; background: #2c2c3e; display: flex; align-items: center; padding: 0 12px; color: #ccc; font-size: 13px; gap: 10px; }
.dot { width: 9px; height: 9px; border-radius: 50%; }
.dot.red { background: #e74c3c; }
.dot.green { background: #2ecc71; }
.btn { background: #3a3a5c; color: #ddd; border: none; padding: 3px 10px; border-radius: 3px; cursor: pointer; font-size: 12px; }
.btn:hover { background: #4a4a7c; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.spacer { flex: 1; }
.mode-label { color: #888; font-size: 12px; }
.target-info { color: #fff; font-size: 12px; }
.scan-wrap { position: relative; }
.scan-dropdown { position: absolute; top: 100%; left: 0; margin-top: 4px; background: #333; border: 1px solid #555; border-radius: 4px; padding: 4px 0; z-index: 100; min-width: 200px; max-height: 280px; overflow-y: auto; }
.scan-item { padding: 4px 10px; font-size: 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.scan-item:hover { background: #444; }
.scan-ip { color: #fff; }
.scan-ports { display: flex; gap: 4px; font-size: 10px; }
.port-ok { color: #2ecc71; background: rgba(46,204,113,0.15); padding: 1px 4px; border-radius: 2px; }
.port-fail { color: #e74c3c; background: rgba(231,76,60,0.1); padding: 1px 4px; border-radius: 2px; text-decoration: line-through; }
.scan-status { padding: 6px 10px; font-size: 12px; color: #f1c40f; border-bottom: 1px solid #555; }
.scan-empty { padding: 8px 10px; font-size: 12px; color: #888; }
</style>
