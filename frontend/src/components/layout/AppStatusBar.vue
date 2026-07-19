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
    <div v-if="mode === 'lan'" class="scan-wrap">
      <button class="btn" @click="showScan = !showScan">扫描设备 ▾</button>
      <div v-if="showScan" class="scan-dropdown">
        <div v-for="d in mockDevices" :key="d.ip" class="scan-item"
          @click="selectedIP = d.ip; showScan = false">
          {{ d.ip }}
        </div>
      </div>
    </div>

    <!-- 当前连接目标 -->
    <span v-if="mode === 'lan' && selectedIP" class="target-info">
      遥测源: {{ selectedIP }}  |  帧数据源: {{ selectedIP }}
    </span>
    <span v-if="mode === 'server'" class="target-info">
      遥测源: telemetry.example.com  |  帧数据源: frame.example.com
    </span>

    <span class="spacer"></span>
    <span class="mode-label">{{ mode === 'lan' ? '局域网直连' : '服务器中转' }}</span>
    <button class="btn" @click="toggleMode">切换</button>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const connected = ref(false)
const mode = ref<'lan' | 'server'>('lan')
const showScan = ref(false)
const selectedIP = ref('')
function toggleMode() {
  mode.value = mode.value === 'lan' ? 'server' : 'lan'
  selectedIP.value = ''
}

const mockDevices = [
  { ip: '192.168.1.100', telemetry: true, frame: true },
  { ip: '192.168.1.101', telemetry: true, frame: false },
  { ip: '192.168.1.105', telemetry: false, frame: true },
]
</script>

<style scoped>
.status-bar {
  height: 36px; background: #2c2c3e; display: flex; align-items: center;
  padding: 0 12px; color: #ccc; font-size: 13px; gap: 10px;
}
.dot { width: 9px; height: 9px; border-radius: 50%; }
.dot.red { background: #e74c3c; }
.dot.green { background: #2ecc71; }
.btn {
  background: #3a3a5c; color: #ddd; border: none; padding: 3px 10px;
  border-radius: 3px; cursor: pointer; font-size: 12px;
}
.btn:hover { background: #4a4a7c; }
.btn.sm { padding: 1px 6px; font-size: 11px; }
.spacer { flex: 1; }
.mode-label { color: #888; font-size: 12px; }
.target-info { color: #fff; font-size: 12px; }
.scan-wrap { position: relative; }
.scan-dropdown {
  position: absolute; top: 100%; left: 0; margin-top: 4px;
  background: #333; border: 1px solid #555; border-radius: 4px;
  padding: 4px 0; z-index: 100;
}
.scan-item {
  display: flex; align-items: center; gap: 8px; padding: 4px 6px;
  font-size: 12px;
}
.scan-item:hover { background: #444; }
.scan-item .green { color: #2ecc71; }
.scan-item .red { color: #e74c3c; }
</style>
