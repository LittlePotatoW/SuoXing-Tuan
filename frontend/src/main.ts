// ============================================================
// frontend/src/main.ts
// Vue 3 应用入口 — 注册 router + 挂载 App
// ============================================================

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { loadConfig } from './services/config'

async function bootstrap() {
  await loadConfig()
  createApp(App).use(router).mount('#app')
}

bootstrap()
