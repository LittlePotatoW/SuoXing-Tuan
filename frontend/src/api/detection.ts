// ============================================================
// frontend/src/api/detection.ts
// 检测服务 API：结果查询、单张图像静态检测
// ============================================================

import { httpClient } from '@/network/http-client'
import type {
  ImageDetectRequest, DetectionResultResponse,
} from '@/types/api'

/** 查询最新检测结果 */
export async function getDetectionResult() {
  const res = await httpClient.get('/api/detection/result')
  return res.data as DetectionResultResponse
}

/** 上传单张图像执行 YOLO 静态检测 */
export async function postDetectionImage(data: ImageDetectRequest) {
  const res = await httpClient.post('/api/detection/image', data)
  return res.data as DetectionResultResponse
}
