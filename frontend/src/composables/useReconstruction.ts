// ============================================================
// frontend/src/composables/useReconstruction.ts
// 重建流程状态管理：轮询结果 + since 增量查询
//
// 设计与用法:
//   导出 useReconstruction()
//     startPolling(intervalMs, onResult) / stopPolling()
//     running / frameCount (响应式)
// ============================================================

import { ref } from 'vue'
import { getReconstructionResult } from '@/api/reconstruction'

export function useReconstruction() {
  const running = ref(false)
  const frameCount = ref(0)
  let timer: ReturnType<typeof setInterval> | null = null
  let lastTimestamp = 0

  async function poll(onResult: (url: string, detections: any[]) => void) {
    try {
      const r = await getReconstructionResult(lastTimestamp || undefined)
      if (r.timestamp > 0 && r.point_cloud_url) {
        lastTimestamp = r.timestamp
        frameCount.value++
        onResult(r.point_cloud_url, r.detections || [])
      }
    } catch { /* backend unreachable */ }
  }

  function startPolling(
    intervalMs: number,
    onResult: (url: string, detections: any[]) => void,
  ) {
    if (running.value) return
    running.value = true
    lastTimestamp = 0
    frameCount.value = 0
    poll(onResult)
    timer = setInterval(() => poll(onResult), intervalMs)
  }

  function stopPolling() {
    running.value = false
    if (timer) { clearInterval(timer); timer = null }
  }

  return { running, frameCount, startPolling, stopPolling }
}
