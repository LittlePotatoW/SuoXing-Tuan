// ============================================================
// frontend/src/types/api.ts
// TypeScript 类型：API 请求/响应接口，与后端 Pydantic 一一对应
// ============================================================

// ---- Vehicle ----

export interface TelemetryRequest {
  timestamp: number
  speed: number
  steering_angle: number
}

export interface FrameRequest {
  timestamp: number
  image: string        // base64 JPEG
  depth_map: string    // base64 16-bit PNG
}

export interface PositionResponse {
  timestamp: number
  x: number
  y: number
  heading: number
}

// ---- Reconstruction ----

export interface ReconstructionStatusResponse {
  status: 'idle' | 'accumulating' | 'reconstructing'
  frame_count: number
  frame_threshold: number
  last_result_timestamp: number | null
}

export interface DetectionItem {
  id: number
  class_name: string
  confidence: number
  bbox_2d: number[]   // [x1, y1, x2, y2]
  center_3d: number[]  // [x, y, z]
}

export interface ReconstructionResultResponse {
  timestamp: number
  point_cloud_url: string
  detections: DetectionItem[]
}

// ---- Detection ----

export interface ImageDetectRequest {
  image: string        // base64 JPEG
}

export interface DetectionResultResponse {
  detections: DetectionItem[]
  count: number
}

export interface DetectionAnnotatedResponse {
  detections: DetectionItem[]
  count: number
  annotated_image: string   // base64 JPEG
}
