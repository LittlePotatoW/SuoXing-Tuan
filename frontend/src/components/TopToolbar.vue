<!-- ============================================================ -->
<!-- frontend/src/components/TopToolbar.vue                                -->
<!-- 顶部工具栏 — 启动/停止、模式选择、YOLO/重建开关、统计                   -->
<!-- ============================================================ -->

<template>
  <div style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:#1e1e1e;border-bottom:1px solid #333;flex-wrap:wrap">
    <span style="font-size:14px;font-weight:bold;color:#4FC3F7">实时融合</span>

    <!-- 启动/停止 -->
    <button @click="$emit('toggleRunning')"
      :style="{ background: running ? '#f44336' : '#4CAF50', color: '#fff', border: 'none', padding: '3px 12px', fontSize: '11px', borderRadius: '3px', cursor: 'pointer', fontWeight: 'bold' }">
      {{ running ? '停止' : '启动' }}
    </button>

    <!-- 模式: 被动/主动 -->
    <button @click="$emit('switchMode', mode === 'passive' ? 'active' : 'passive')"
      :style="{ background: mode === 'active' ? '#4CAF50' : '#2196F3', color: '#fff', border: 'none', padding: '3px 10px', fontSize: '11px', borderRadius: '3px', cursor: 'pointer' }">
      {{ mode === 'passive' ? '被动' : '主动' }}
    </button>

    <!-- 主动子模式选择 -->
    <template v-if="mode === 'active'">
      <div style="display:flex;border-radius:3px;overflow:hidden;border:1px solid #555">
        <button v-for="s in subModes" :key="s.value"
          @click="$emit('update:subMode', s.value)"
          :style="{ background: subMode === s.value ? '#4FC3F7' : '#2a2a2a', color: subMode === s.value ? '#1a1a1a' : '#ccc', border: 'none', padding: '2px 8px', fontSize: '10px', cursor: 'pointer', fontWeight: subMode === s.value ? 'bold' : 'normal' }">
          {{ s.label }}
        </button>
      </div>
    </template>

    <div style="width:1px;height:20px;background:#444;margin:0 2px" />

    <label style="display:flex;align-items:center;gap:4px;color:#ccc;font-size:11px;cursor:pointer">
      <input type="checkbox" :checked="yoloOn" @change="$emit('toggleYolo')" />YOLO
    </label>
    <label style="display:flex;align-items:center;gap:4px;color:#ccc;font-size:11px;cursor:pointer">
      <input type="checkbox" :checked="reconOn" @change="$emit('toggleRecon')" />重建
    </label>
    <button @click="$emit('clearAll')" style="background:#555;color:#fff;border:none;padding:3px 10px;font-size:10px;cursor:pointer;border-radius:3px">清除</button>

    <div style="flex:1" />
    <span style="color:#888;font-size:10px">loc:{{ stats.location }} det:{{ stats.detection }} 重建:{{ meshFrames }}</span>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'

const subModes = [
  { label: '中继', value: 'relay' as const },
  { label: '回放', value: 'replay' as const },
  { label: '手动', value: 'manual' as const },
]

defineProps({
  running: { type: Boolean, required: true },
  mode: { type: String as PropType<'passive' | 'active'>, required: true },
  subMode: { type: String as PropType<'relay' | 'replay' | 'manual'>, default: 'relay' },
  yoloOn: { type: Boolean, required: true },
  reconOn: { type: Boolean, required: true },
  stats: { type: Object as PropType<{ location: number; detection: number }>, required: true },
  meshFrames: { type: Number, default: 0 },
})

defineEmits<{
  toggleRunning: []
  switchMode: [m: 'passive' | 'active']
  'update:subMode': [v: 'relay' | 'replay' | 'manual']
  toggleYolo: []
  toggleRecon: []
  clearAll: []
}>()
</script>
