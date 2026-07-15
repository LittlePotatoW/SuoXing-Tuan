<!-- ============================================================ -->
<!-- frontend/src/components/DefectPanel.vue                             -->
<!-- 缺陷列表面板 — 显示检测到的缺陷及其置信度                             -->
<!-- ============================================================ -->

<template>
  <div>
    <div style="font-size:12px;font-weight:bold;color:#ccc;margin-bottom:6px">缺陷 ({{ list.length }})</div>
    <div v-if="list.length === 0" style="font-size:10px;color:#666;padding:8px 0">暂无缺陷</div>
    <div v-for="(c,i) in list" :key="i"
      style="font-size:10px;color:#ccc;padding:4px 6px;margin-bottom:3px;background:#2a2a2a;border-radius:3px">
      <div :style="{color: crackColor(c.crack_type)}">&#9679; {{ c.crack_type || '缺陷' }}</div>
      <div style="color:#888">{{ pct(c.confidence) }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
const CRACK_COLORS: Record<string, string> = {
  '裂缝': '#ef5350', '渗漏': '#42a5f5', '剥落': '#ffa726',
  'crack': '#ef5350', 'leakage': '#42a5f5', 'spalling': '#ffa726',
}

defineProps<{ list: any[] }>()

function crackColor(t: string): string { return CRACK_COLORS[t] || '#ccc' }
function pct(v: number): string { return ((v || 0) * 100).toFixed(0) + '%' }
</script>
