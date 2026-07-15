<!-- ============================================================ -->
<!-- frontend/src/components/StatusPanel.vue                              -->
<!-- 状态面板 — 连接状态、发送/缓存计数                                    -->
<!-- ============================================================ -->

<template>
  <div style="font-size:11px;color:#ccc;line-height:1.8">
    <div style="font-size:12px;font-weight:bold;color:#ccc;margin-bottom:6px">连接状态</div>
    <div><span :style="{color: backendConnected ? '#4CAF50' : '#f44336'}">&#9679;</span> 后端: {{ backendConnected ? '已连接' : '未连接' }}</div>
    <div><span :style="{color: transpondConnected ? '#4CAF50' : '#f44336'}">&#9679;</span> Transpond: {{ transpondConnected ? '已连接' : '未连接' }}</div>
    <div style="margin-top:8px;font-size:12px;font-weight:bold;color:#ccc;margin-bottom:6px">数据统计</div>
    <div style="color:#888">已发送: <span style="color:#4FC3F7">Loc={{ stats.location }}</span> <span style="color:#4FC3F7">Det={{ stats.detection }}</span></div>
    <div style="color:#888">融合重建: <span style="color:#4FC3F7">{{ meshFrames }} 次</span></div>
    <div v-if="relayCache" style="color:#888;margin-top:4px">Transpond 缓存: <span style="color:#4FC3F7">Loc={{ relayCache.location }}</span> <span style="color:#4FC3F7">Sen={{ relayCache.sensor }}</span></div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  backendConnected: boolean
  transpondConnected: boolean
  stats: { location: number; detection: number }
  meshFrames: number
  relayCache?: { location: number; sensor: number } | null
}>()
</script>
