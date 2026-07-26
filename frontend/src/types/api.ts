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
  center_3d?: number[]  // [x, y, z], 仅重建流程有值
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

// ---- Estimator 管理 ----

export interface EstimatorResetRequest {
  mode?: string | null
  wheelbase?: number | null
  constant_speed?: number | null
  fusion_weight?: number | null
  initial_x?: number | null
  initial_y?: number | null
  initial_heading?: number | null
}

export interface EstimatorConfigResponse {
  mode: string
  wheelbase: number
  constant_speed: number
  fusion_weight: number
  initial_x: number
  initial_y: number
  initial_heading: number
  x: number
  y: number
  heading: number
}

// ---- Reconstruction 管理 ----

export interface ReconResetRequest {
  mode?: string | null
  frame_threshold?: number | null
  voxel_size?: number | null
  yolo_enabled?: boolean | null
  report_name?: string | null
  method?: string | null
}

export interface ReconConfigResponse {
  mode: string
  frame_threshold: number
  voxel_size: number
  frame_count: number
  status: string
}

// ---- Session ----

export interface SessionListItem {
  name: string
  frame_count: number
}

// ---- Report ----

export interface ReportListItem {
  filename: string
}
