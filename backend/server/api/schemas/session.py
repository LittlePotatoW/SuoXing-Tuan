# ============================================================
# backend/server/api/schemas/session.py
# Session 保存/加载的 Pydantic 模型
# ============================================================

from pydantic import BaseModel, Field


class SessionFrame(BaseModel):
    filename: str
    data: str               # base64


class SessionSaveRequest(BaseModel):
    name: str
    manifest: dict
    frames: list[SessionFrame] = Field(default_factory=list)


class SessionListItem(BaseModel):
    name: str
    frame_count: int = 0
