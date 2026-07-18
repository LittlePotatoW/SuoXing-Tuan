<!-- ============================================================ -->
<!-- frontend/src/components/layout/AppSidebar.vue                -->
<!-- 左侧导航栏：logo + 菜单                                     -->
<!-- ============================================================ -->
<template>
  <aside class="sidebar">
    <div class="logo">SuoXing-Tuan</div>
    <nav>
      <router-link v-for="item in menu" :key="item.path" :to="item.path"
        class="nav-item" active-class="active">
        {{ item.label }}
      </router-link>
    </nav>
  </aside>
</template>

<script setup lang="ts">
const menu = [
  { path: '/',          label: '主界面' },
  { path: '/realtime',  label: '实时建模' },
  { path: '/replay',    label: '回放建模' },
  { path: '/defects',   label: '缺陷详情' },
  { path: '/detection', label: '静态检测' },
  { path: '/settings',  label: '配置' },
]
</script>

<style scoped>
.sidebar { width: 160px; background: #1a1a2e; color: #eee; display: flex; flex-direction: column; }
.logo { padding: 16px; font-size: 16px; font-weight: bold; border-bottom: 1px solid #333; }
.nav-item { display: block; padding: 12px 16px; color: #aaa; text-decoration: none; font-size: 14px; }
.nav-item:hover { background: #16213e; color: #fff; }
.nav-item.active { background: #0f3460; color: #fff; }
</style>
