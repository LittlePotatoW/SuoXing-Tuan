// ============================================================
// frontend/src/router/index.ts
// Vue Router 路由：6 个界面
//
// 设计与用法:
//   导出 router (Vue Router 实例)
//   路由: / /realtime /replay /defects /detection /settings
// ============================================================

import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/',             name: 'main',      component: () => import('@/views/MainView.vue') },
    { path: '/realtime',     name: 'realtime',  component: () => import('@/views/RealtimeModeling.vue') },
    { path: '/replay',       name: 'replay',    component: () => import('@/views/ReplayModeling.vue') },
    { path: '/defects',      name: 'defects',   component: () => import('@/views/DefectDetail.vue') },
    { path: '/detection',    name: 'detection', component: () => import('@/views/StaticDetection.vue') },
    { path: '/settings',     name: 'settings',  component: () => import('@/views/SettingsView.vue') },
  ],
})

export default router
