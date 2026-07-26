// ============================================================
// frontend/src/api/vehicle.ts
// 小车数据 API (Layer 2)：遥测上报、帧数据上报、位置查询
//
// 设计与用法:
//   导出 postTelemetry(data)    POST   /api/vehicle/telemetry   → { status }
//   导出 postFrame(data)        POST   /api/vehicle/frame       → { status, frame_id }
//   导出 getPosition()          GET    /api/vehicle/position    → PositionResponse
// ============================================================

import { httpClient } from '@/network/http-client'
import type {
  TelemetryRequest, FrameRequest, PositionResponse,
  EstimatorResetRequest, EstimatorConfigResponse,
} from '@/types/api'

/** 上报遥测 (speed + steering) */
export async function postTelemetry(data: TelemetryRequest) {
  const res = await httpClient.post('/api/vehicle/telemetry', data)
  return res.data as { status: string }
}

/** 上报一帧深度相机数据 (RGB + 深度图) */
export async function postFrame(data: FrameRequest) {
  const res = await httpClient.post('/api/vehicle/frame', data)
  return res.data as { status: string; frame_id: string }
}

/** 查询小车当前位置 */
export async function getPosition() {
  const res = await httpClient.get('/api/vehicle/position')
  return res.data as PositionResponse
}

/** 重置位置估计器（切换模式/参数） */
export async function resetEstimator(data: EstimatorResetRequest) {
  const res = await httpClient.post('/api/vehicle/estimator/reset', data)
  return res.data as { status: string; mode: string }
}

/** 查询估计器当前配置 */
export async function getEstimatorConfig() {
  const res = await httpClient.get('/api/vehicle/estimator/config')
  return res.data as EstimatorConfigResponse
}
