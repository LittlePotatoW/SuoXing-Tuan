# ============================================================
# backend/server/api/schemas/report.py
# Report 保存/加载的 Pydantic 模型
# ============================================================

from pydantic import BaseModel, Field


class ReportSaveRequest(BaseModel):
    filename: str
    data: dict


class ReportListItem(BaseModel):
    filename: str
