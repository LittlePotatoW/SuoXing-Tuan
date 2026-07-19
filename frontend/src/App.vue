<!-- ============================================================ -->
<!-- frontend/src/App.vue                                           -->
<!-- 根组件：状态栏 + 侧边栏 + 页面区                              -->
<!-- ============================================================ -->
<template>
  <div class="app">
    <AppStatusBar />
    <div class="app-body">
      <AppSidebar />
      <main class="app-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppStatusBar from '@/components/layout/AppStatusBar.vue'
import { useConnection } from '@/composables/useConnection'

const { connectAll } = useConnection()
onMounted(() => {
  connectAll()
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app, .app { height: 100%; }
.app { display: flex; flex-direction: column; font-family: sans-serif; }
.app-body { display: flex; flex: 1; overflow: hidden; }
.app-main { flex: 1; padding: 20px; overflow-y: auto; background: #f5f5f5; }
</style>
