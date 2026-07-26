# ============================================================
# backend/server/api/schemas/detection.py
# 检测服务的 Pydantic 请求/响应模型
#
# 设计与用法:
#   导出 ImageDetectRequest / DetectionItem
#   导出 DetectionResultResponse (元数据)
#   导出 DetectionAnnotatedResponse (元数据 + 标注图)
# ============================================================

from pydantic import BaseModel, Field


class ImageDetectRequest(BaseModel):
    image: str = Field(description="Base64 编码的 JPEG 图像")


class DetectionItem(BaseModel):
    id: int
    class_name: str
    confidence: float
    bbox_2d: list[float]  # [x1, y1, x2, y2]
    center_3d: list[float] | None = None  # [x, y, z], 仅重建流程填充


class DetectionResultResponse(BaseModel):
    detections: list[DetectionItem]
    count: int


class DetectionAnnotatedResponse(BaseModel):
    detections: list[DetectionItem]
    count: int
    annotated_image: str = ""   # base64 JPEG, YOLOv8 风格标注图
