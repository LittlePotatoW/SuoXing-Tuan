<!-- ============================================================ -->
<!-- frontend/src/components/Sidebar.vue                               -->
<!-- 侧边栏导航 — 4 个页面入口，高亮当前页                              -->
<!-- ============================================================ -->

<template>
  <div style="width: 180px; min-width: 180px; height: 100vh; display: flex; flex-direction: column; border-right: 1px solid #333">
    <!-- 项目标题 -->
    <div style="padding: 16px 12px; font-size: 16px; font-weight: bold; color: #4FC3F7; border-bottom: 1px solid #333">
      SuoXing-Tuan
    </div>

    <!-- 菜单 -->
    <div style="flex: 1; padding-top: 8px">
      <div
        v-for="item in items"
        :key="item.id"
        :style="{
          padding: '10px 16px',
          cursor: 'pointer',
          color: currentPage === item.id ? '#E0E0E0' : '#888',
          background: currentPage === item.id ? '#2D2D2D' : 'transparent',
          borderLeft: currentPage === item.id ? '3px solid #4FC3F7' : '3px solid transparent',
          fontSize: '13px',
        }"
        @click="$emit('navigate', item.id)"
      >
        {{ item.label }}
      </div>
    </div>

    <!-- 底部版本 -->
    <div style="padding: 12px 16px; font-size: 11px; color: #555; border-top: 1px solid #333">
      版本 v0.1.0
    </div>
  </div>
</template>

<script setup lang="ts">
export interface SidebarItem {
  id: string
  label: string
}

defineProps<{
  items: SidebarItem[]
  currentPage: string
}>()

defineEmits<{ navigate: [id: string] }>()
</script>
