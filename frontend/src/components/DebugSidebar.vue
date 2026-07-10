<!-- ============================================================ -->
<!-- frontend/src/components/DebugSidebar.vue                             -->
<!-- 右侧调试面板 — 标签页形式组织 [调试] [缺陷列表] [状态]                -->
<!-- ============================================================ -->

<template>
  <div style="width:280px;background:#1e1e1e;border-left:1px solid #333;display:flex;flex-direction:column;overflow:hidden">
    <!-- 标签栏 -->
    <div style="display:flex;border-bottom:1px solid #333;flex-shrink:0">
      <button v-for="t in tabs" :key="t.key"
        @click="$emit('update:activeTab', t.key)"
        :style="{ flex: 1, background: activeTab === t.key ? '#2a2a2a' : '#1e1e1e', color: activeTab === t.key ? '#4FC3F7' : '#888', border: 'none', padding: '6px 0', fontSize: '11px', cursor: 'pointer', borderBottom: activeTab === t.key ? '2px solid #4FC3F7' : '2px solid transparent', fontWeight: activeTab === t.key ? 'bold' : 'normal' }">
        {{ t.label }}
      </button>
    </div>

    <!-- 内容区 -->
    <div style="flex:1;overflow-y:auto;padding:8px 10px">
      <slot :name="activeTab" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'

const tabs = [
  { key: 'debug' as const, label: '调试' },
  { key: 'defects' as const, label: '缺陷列表' },
  { key: 'status' as const, label: '状态' },
]

defineProps({
  activeTab: { type: String as PropType<'debug' | 'defects' | 'status'>, default: 'debug' },
})

defineEmits<{
  'update:activeTab': [v: 'debug' | 'defects' | 'status']
}>()
</script>
