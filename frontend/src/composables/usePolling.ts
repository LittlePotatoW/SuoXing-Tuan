// ============================================================
// frontend/src/composables/usePolling.ts
// Vue 组合式函数：通用轮询，页面销毁自动停止
//
// 设计与用法:
//   导出 usePolling(fn, intervalMs)
//     running: 是否轮询中
//     start() / stop()  启停轮询
//   组件卸载时自动 stop
// ============================================================

import { ref, onUnmounted } from 'vue'

export function usePolling(fn: () => Promise<void> | void, intervalMs: number) {
  const running = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null

  function start() {
    if (running.value) return
    running.value = true
    fn()
    timer = setInterval(fn, intervalMs)
  }

  function stop() {
    running.value = false
    if (timer) { clearInterval(timer); timer = null }
  }

  onUnmounted(stop)

  return { running, start, stop }
}
