// ============================================================
// frontend/src/api/detection.ts
// 检测服务 API (Layer 2)：结果查询、单张图像静态检测
//
// 设计与用法:
//   导出 getDetectionResult()          GET   /api/detection/result            → DetectionResultResponse
//   导出 getDetectionResultAnnotated()  GET   /api/detection/result/annotated  → DetectionAnnotatedResponse
//   导出 postDetectionImage(data)      POST  /api/detection/image             → DetectionResultResponse
// ============================================================

import { httpClient } from '@/network/http-client'
import type {
  ImageDetectRequest, DetectionResultResponse, DetectionAnnotatedResponse,
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

/** 查询最新检测结果（含 YOLOv8 风格标注图） */
export async function getDetectionResultAnnotated() {
  const res = await httpClient.get('/api/detection/result/annotated')
  return res.data as DetectionAnnotatedResponse
}
