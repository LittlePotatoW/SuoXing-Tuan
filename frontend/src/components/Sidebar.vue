<!-- ============================================================ -->
<!-- frontend/src/components/Sidebar.vue                              -->
<!-- 侧边栏导航 — 使用 vue-router                                     -->
<!-- ============================================================ -->

<template>
  <div style="width: 140px; min-width: 140px; background: #1e1e1e; display: flex; flex-direction: column; border-right: 1px solid #333">
    <div style="padding: 14px 12px; font-size: 15px; font-weight: bold; color: #4FC3F7; border-bottom: 1px solid #333">
      SuoXing-Tuan
    </div>
    <div style="flex: 1; padding-top: 8px">
      <div v-for="item in items" :key="item.path"
        :style="linkStyle(item)"
        @click="$router.push(item.path)"
      >
        {{ item.label }}
      </div>
    </div>
    <div style="padding: 12px 16px; font-size: 11px; color: #555; border-top: 1px solid #333">
      v0.2.0
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
const items = [
  { path: '/', label: '2D 检测', name: 'detection' },
  { path: '/reconstruction', label: '3D 重建', name: 'reconstruction' },
  { path: '/page2', label: 'Page 2', name: 'page2' },
  { path: '/page3', label: 'Page 3', name: 'page3' },
  { path: '/page4', label: 'Page 4', name: 'page4' },
]

function linkStyle(item: typeof items[0]) {
  const active = route.path === item.path
  return {
    padding: '10px 16px', cursor: 'pointer',
    color: active ? '#E0E0E0' : '#888',
    background: active ? '#2D2D2D' : 'transparent',
    borderLeft: active ? '3px solid #4FC3F7' : '3px solid transparent',
    fontSize: '13px',
  }
}
</script>
