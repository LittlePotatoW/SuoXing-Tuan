# ============================================================
# backend/server/api/schemas/vehicle.py
# 小车数据上报的 Pydantic 请求/响应模型
#
# 设计与用法:
#   导出 TelemetryRequest / PositionResponse
# ============================================================

from pydantic import BaseModel, Field


class TelemetryRequest(BaseModel):
    timestamp: float
    speed: float = Field(ge=0, description="当前速度 (m/s)")
    steering_angle: float = Field(description="当前车轮转角 (度), 正=左转")


class PositionResponse(BaseModel):
    timestamp: float
    x: float
    y: float
    heading: float
