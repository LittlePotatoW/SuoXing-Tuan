# ============================================================
# backend/server/api/schemas/reconstruction.py
# 重建引擎的 Pydantic 请求/响应模型
#
# 设计与用法:
#   导出 ReconstructionStatusResponse / ReconstructionResultResponse
#   导出 ReconResetRequest / ReconConfigResponse
# ============================================================

from typing import Literal

from pydantic import BaseModel, Field

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


class ReconResetRequest(BaseModel):
    mode: str | None = Field(None, description="full|incremental")
    frame_threshold: int | None = None
    voxel_size: float | None = None
    yolo_enabled: bool | None = Field(None, description="是否在重建中启用 YOLO 检测")
    report_name: str | None = Field(None, description="报告名，用于实时保存标注图")


class ReconConfigResponse(BaseModel):
    mode: str
    frame_threshold: int
    voxel_size: float
    yolo_enabled: bool = True
    frame_count: int
    status: str
