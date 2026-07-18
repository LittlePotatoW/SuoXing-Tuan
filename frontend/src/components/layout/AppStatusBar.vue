<!-- ============================================================ -->
<!-- frontend/src/components/layout/AppStatusBar.vue               -->
<!-- 顶部状态栏：连接状态指示灯                                   -->
<!-- ============================================================ -->
<template>
  <header class="status-bar">
    <span class="dot"></span>
    <span class="text">未连接</span>
  </header>
</template>

<style scoped>
.status-bar {
  height: 32px; background: #2c2c3e; display: flex; align-items: center;
  padding: 0 16px; color: #aaa; font-size: 13px; gap: 8px;
}
.dot {
  width: 8px; height: 8px; border-radius: 50%; background: #e74c3c;
}
</style>
