# ============================================================
# backend/server/api/routes/vehicle.py
# 小车数据上报接口：遥测上报、位置查询
#
# 设计与用法:
#   导出 router (APIRouter)
#   POST /telemetry  上报速度+转向
#   GET  /position   查询当前位置
# ============================================================

from fastapi import APIRouter

import uuid

from server.api.schemas.vehicle import (
    TelemetryRequest, PositionResponse, FrameRequest,
)
from server.estimation import PositionEstimator, Position

router = APIRouter(prefix="/api/vehicle", tags=["vehicle"])


@router.post("/telemetry", status_code=200)
def post_telemetry(body: TelemetryRequest):
    """上报一条遥测数据（速度+转向），更新位置估计器"""
    est = PositionEstimator.create()
    est.update_telemetry(
        timestamp=body.timestamp,
        speed=body.speed,
        steering_angle=body.steering_angle,
    )
    return {"status": "ok"}


@router.get("/position", response_model=PositionResponse)
def get_position() -> PositionResponse:
    """查询当前位置"""
    est = PositionEstimator.create()
    pos: Position = est.get_position()
    return PositionResponse(
        timestamp=pos.timestamp,
        x=pos.x,
        y=pos.y,
        heading=pos.heading,
    )


@router.post("/frame", status_code=200)
def post_frame(body: FrameRequest):
    """接收一帧深度相机数据 (RGB + 深度图), 推入重建引擎"""
    frame_id = uuid.uuid4().hex[:12]
    from server.engine import ReconstructionEngine
    engine = ReconstructionEngine.create()
    engine.push_frame(frame_id, body.timestamp, body.image, body.depth_map)
    return {"status": "ok", "frame_id": frame_id}
