<!-- ============================================================ -->
<!-- frontend/src/views/SettingsView.vue                              -->
<!-- 全局配置页 — 重建参数 + 预留其他配置                                 -->
<!-- ============================================================ -->

<template>
  <div style="padding: 20px; color: #ccc; font-size: 13px; max-width: 600px">
    <h3 style="color: #4FC3F7; margin-bottom: 16px">配置</h3>

    <!-- 三维重建 -->
    <div style="background: #252525; border: 1px solid #333; border-radius: 6px; padding: 16px; margin-bottom: 16px">
      <div style="font-weight: bold; margin-bottom: 12px; color: #4FC3F7">三维重建</div>

      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px">
        <span style="color: #888; width: 60px">模式:</span>
        <label style="cursor: pointer; margin-right: 12px">
          <input type="radio" value="cumulative" v-model="mode" /> 全量累积
        </label>
        <label style="cursor: pointer">
          <input type="radio" value="layered" v-model="mode" /> 逐层累积
        </label>
      </div>

      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px">
        <span style="color: #888; width: 60px">重建间隔:</span>
        <input v-model.number="interval" type="number" min="1" max="50"
          style="width: 60px; background: #1a1a1a; color: #ccc; border: 1px solid #555; padding: 3px 6px; font-size: 12px; text-align: center" />
        <span style="color: #888; font-size: 12px">帧</span>

      </div>

      <div style="font-size: 11px; color: #666; margin-bottom: 12px">
        状态: {{ status.frames }}帧 | {{ status.points?.toLocaleString() }}点
      </div>

      <div style="display: flex; gap: 8px">
        <button @click="applyAndReset" style="background: #1976D2; color: #fff; border: none; padding: 5px 16px; font-size: 12px; cursor: pointer; border-radius: 3px">切换配置</button>
        <span v-if="msg" :style="{ color: msgColor, fontSize: '12px' }">{{ msg }}</span>
      </div>
    </div>

    <!-- 其他配置预留 -->
    <div style="background: #252525; border: 1px solid #333; border-radius: 6px; padding: 16px; color: #555; font-size: 12px">
      其他配置 (预留)
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getBaseUrl } from '../services/apiClient'

const mode = ref('cumulative')
const interval = ref(10)
const status = ref({ frames: 0, points: 0 })
const msg = ref('')
const msgColor = ref('#4CAF50')

async function fetchConfig() {
  try {
    const r = await fetch(getBaseUrl() + '/api/reconstruction/config')
    const d = await r.json()
    mode.value = d.mode
    interval.value = d.interval
    status.value = { frames: d.total_frames, points: d.total_points }
  } catch { /* ignore */ }
}

async function applyAndReset() {
  try {
    await fetch(getBaseUrl() + '/api/reconstruction/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: mode.value, interval: interval.value }),
    })
    msg.value = '已切换'
    msgColor.value = '#4CAF50'
    status.value = { frames: 0, points: 0 }
  } catch {
    msg.value = '切换失败'
    msgColor.value = '#f44336'
  }
}

onMounted(fetchConfig)
</script>
