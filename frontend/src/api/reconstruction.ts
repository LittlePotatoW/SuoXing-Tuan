// ============================================================
// frontend/src/api/reconstruction.ts
// 重建引擎 API：状态查询、结果获取
// ============================================================

import { httpClient } from '@/network/http-client'
import type {
  ReconstructionStatusResponse, ReconstructionResultResponse,
} from '@/types/api'

/** 查询重建引擎状态 */
export async function getReconstructionStatus() {
  const res = await httpClient.get('/api/reconstruction/status')
  return res.data as ReconstructionStatusResponse
}

/** 获取重建结果，since 为增量查询时间戳 (可选) */
export async function getReconstructionResult(since?: number) {
  const params = since !== undefined ? { since } : {}
  const res = await httpClient.get('/api/reconstruction/result', { params })
  return res.data as ReconstructionResultResponse
}
