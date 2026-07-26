// ============================================================
// frontend/src/stores/estimation.ts
// 位置估计器参数共享状态 — 供 Settings / Modeling / useConnection 使用
//
// 设计与用法:
//   导出 useEstimationStore()
//     setConfig(cfg)         开始建模时写入当前参数
//     clear()                停止建模时清空
//     shouldSendTelemetry    计算属性：bicycle/fusion 才为 true
//     mode / wheelbase / constantSpeed 等响应式字段
// ============================================================

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useEstimationStore = defineStore('estimation', () => {
  const mode = ref<string>('bicycle')
  const wheelbase = ref<number>(2.0)
  const constantSpeed = ref<number>(1.0)

  function setConfig(cfg: Record<string, any>) {
    mode.value = cfg.mode || 'bicycle'
    wheelbase.value = cfg.wheelbase ?? 2.0
    constantSpeed.value = cfg.constant_speed ?? 1.0
  }

  function clear() {
    mode.value = 'bicycle'
    wheelbase.value = 2.0
    constantSpeed.value = 1.0
  }

  const shouldSendTelemetry = computed(() =>
    mode.value === 'bicycle' || mode.value === 'fusion',
  )

  return { mode, wheelbase, constantSpeed, setConfig, clear, shouldSendTelemetry }
})
