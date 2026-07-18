# ============================================================
# backend/server/api/schemas/reconstruction.py
# 重建引擎的 Pydantic 请求/响应模型
#
# 设计与用法:
#   导出 ReconstructionStatusResponse / ReconstructionResultResponse
# ============================================================

from typing import Literal

from pydantic import BaseModel

from server.api.schemas.detection import DetectionItem


class ReconstructionStatusResponse(BaseModel):
    status: Literal["idle", "accumulating", "reconstructing"]
    frame_count: int
    frame_threshold: int
    last_result_timestamp: float | None = None


class ReconstructionResultResponse(BaseModel):
    timestamp: float
    point_cloud_url: str
    detections: list[DetectionItem]
