// ============================================================
// frontend/src/api/reconstruction.ts
// 重建引擎 API (Layer 2)：状态查询、结果获取
//
// 设计与用法:
//   导出 getReconstructionStatus()        GET  /api/reconstruction/status       → ReconstructionStatusResponse
//   导出 getReconstructionResult(since?)   GET  /api/reconstruction/result?since= → ReconstructionResultResponse
// ============================================================

import { httpClient } from '@/network/http-client'
import type {
  ReconstructionStatusResponse, ReconstructionResultResponse,
  ReconResetRequest, ReconConfigResponse,
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

/** 重置重建引擎（切换参数） */
export async function resetReconstruction(data: ReconResetRequest) {
  const res = await httpClient.post('/api/reconstruction/reset', data)
  return res.data as { status: string; mode: string }
}

/** 查询重建引擎当前配置 */
export async function getReconConfig() {
  const res = await httpClient.get('/api/reconstruction/config')
  return res.data as ReconConfigResponse
}
