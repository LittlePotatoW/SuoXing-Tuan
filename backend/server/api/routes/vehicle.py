# ============================================================
# backend/server/api/routes/vehicle.py
# 小车数据接口：遥测、帧、位置、估计器管理
#
# 设计与用法:
#   导出 router (APIRouter)
#   POST /telemetry          上报速度+转向
#   POST /frame              上报深度相机帧数据
#   GET  /position           查询当前位置
#   POST /estimator/reset    重置位置估计器
#   GET  /estimator/config   查询估计器配置
# ============================================================

from fastapi import APIRouter

import uuid

from server.api.schemas.vehicle import (
    TelemetryRequest, PositionResponse, FrameRequest,
    EstimatorResetRequest, EstimatorConfigResponse,
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
    """接收一帧深度相机数据 (RGB + 深度图), 推入重建引擎 + 位置估计器"""
    frame_id = uuid.uuid4().hex[:12]

    # 位置估计器 (模式3/4 需要帧数据)
    est = PositionEstimator.create()
    est.update_frame(body.timestamp, body.image, body.depth_map)

    # 重建引擎
    from server.engine import ReconstructionEngine
    engine = ReconstructionEngine.create()
    engine.push_frame(frame_id, body.timestamp, body.image, body.depth_map)
    return {"status": "ok", "frame_id": frame_id}


# ============================================================
# 位置估计器管理
# ============================================================

@router.post("/estimator/reset", status_code=200)
def reset_estimator(body: EstimatorResetRequest):
    """重置位置估计器，可选切换模式和参数"""
    PositionEstimator.stop()
    est = PositionEstimator.create(mode=body.mode)
    if body.wheelbase is not None:
        est._wheelbase = body.wheelbase
    if body.constant_speed is not None:
        est._constant_speed = body.constant_speed
    if body.initial_x is not None:
        est._initial_x = body.initial_x
        est._x = body.initial_x
    if body.initial_y is not None:
        est._initial_y = body.initial_y
        est._y = body.initial_y
    if body.initial_heading is not None:
        est._initial_heading = body.initial_heading
        est._heading = body.initial_heading
    return {"status": "ok", "mode": est._mode}


@router.get("/estimator/config", response_model=EstimatorConfigResponse)
def get_estimator_config() -> EstimatorConfigResponse:
    """查询位置估计器当前配置和状态"""
    est = PositionEstimator.create()
    cfg = est.get_config()
    return EstimatorConfigResponse(**cfg)
