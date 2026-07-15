# ============================================================
# backend/inference/schemas.py
# 推理响应数据模型
# ============================================================

from dataclasses import dataclass, field


@dataclass
class DetectionResult:
    """单条检测结果"""
    class_name: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]


@dataclass
class InferenceResponse:
    """推理响应 — 前后端统一格式"""
    detections: list[DetectionResult] = field(default_factory=list)
    inference_time_ms: float = 0.0
    image_width: int = 0
    image_height: int = 0
