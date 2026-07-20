# ============================================================
# backend/server/api/schemas/session.py
# Session 保存/加载的 Pydantic 模型
# ============================================================

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    name: str
    start_time: float
    telemetry_interval_ms: int = 100


class SessionFrameRequest(BaseModel):
    session_name: str
    frame_id: int
    image_name: str          # e.g. "00001.jpg"
    depth_name: str           # e.g. "00001.png"
    image_data: str           # base64 JPEG
    depth_data: str           # base64 PNG


class SessionSaveRequest(BaseModel):
    name: str
    manifest: dict
    frames: list = Field(default_factory=list)  # 保留兼容，但新流程为空


class SessionListItem(BaseModel):
    name: str
    frame_count: int = 0
