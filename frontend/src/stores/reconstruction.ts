// ============================================================
// frontend/src/stores/reconstruction.ts
// Pinia: 重建状态与结果缓存
//
// 设计与用法:
//   导出 useReconstructionStore()
//     status / latestResult (响应式)
//     updateStatus() / updateResult()  更新数据
// ============================================================

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ReconstructionStatusResponse, ReconstructionResultResponse } from '@/types/api'

export const useReconstructionStore = defineStore('reconstruction', () => {
  const status = ref<ReconstructionStatusResponse | null>(null)
  const latestResult = ref<ReconstructionResultResponse | null>(null)

  function updateStatus(s: ReconstructionStatusResponse) {
    status.value = s
  }

  function updateResult(r: ReconstructionResultResponse) {
    latestResult.value = r
  }

  return { status, latestResult, updateStatus, updateResult }
})
