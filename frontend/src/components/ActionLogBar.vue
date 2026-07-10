<!-- ============================================================ -->
<!-- frontend/src/components/ActionLogBar.vue                               -->
<!-- 底部操作日志条 — 显示最近的操作记录                                    -->
<!-- ============================================================ -->

<template>
  <div style="background:#1a1a1a;border-top:1px solid #333;padding:2px 12px;font-size:10px;color:#666;display:flex;gap:16px;overflow:hidden;height:22px;align-items:center">
    <template v-for="(entry, i) in entries.slice(-8)" :key="i">
      <span :style="{color: entry.level === 'error' ? '#f44336' : entry.level === 'success' ? '#4CAF50' : '#888'}">
        [{{ entry.time }}] {{ entry.msg }}
      </span>
    </template>
    <span v-if="entries.length === 0" style="color:#444">操作日志</span>
  </div>
</template>

<script setup lang="ts">
export interface LogEntry {
  time: string
  msg: string
  level: 'info' | 'success' | 'error'
}

defineProps<{ entries: LogEntry[] }>()
</script>
