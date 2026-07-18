// ============================================================
// frontend/src/main.ts
// Vue 应用入口
//
// 设计与用法:
//   创建 Vue 应用 → 注册 Pinia / Router → 挂载到 #app
// ============================================================

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
