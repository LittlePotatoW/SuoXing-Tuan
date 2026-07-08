# ============================================================
# backend/data_pre_processing/kinematics_api.py
# 运动学数据预处理 — 独立 API 端点，接收速度/转向角
#
# 用法: 在 main.py 中挂载:
#   from data_pre_processing.kinematics_api import router as kinematics_router
#   app.include_router(kinematics_router)
# ============================================================

import logging
import math

from fastapi import APIRouter

from data_pre_processing.state_estimator import StateEstimator

logger = logging.getLogger("data_pre_processing.kinematics")

# 模块级单例，与 reconstruction 共享同一个估计器
estimator = StateEstimator()

router = APIRouter(prefix="/api/preprocessing", tags=["preprocessing"])


# ============================================================
#  API 端点
# ============================================================

@router.post("/kinematics")
async def upload_kinematics(payload: dict):
    """
    接收运动学参数（与点云/照片分开传输，高频上报）。

    请求体:
        {
            "velocity": 0.5,           // 线速度 (m/s)
            "steering_angle": 0.0,     // 转向角 (rad)
            "timestamp_ns": 171820...  // 纳秒时间戳
        }
    """
    velocity = float(payload.get("velocity", 0.0))
    steering_angle = float(payload.get("steering_angle", 0.0))
    timestamp_ns = int(payload.get("timestamp_ns", 0))

    state = estimator.update_kinematics(
        velocity=velocity,
        steering_angle=steering_angle,
        timestamp_ns=timestamp_ns,
    )
    return {
        "status": "ok",
        "x": round(state.x, 4),
        "y": round(state.y, 4),
        "yaw": round(state.yaw, 4),
        "velocity": round(state.velocity, 2),
        "updates": estimator.stats["updates"],
        "rejected": estimator.stats["rejected"],
    }


@router.get("/position")
async def get_position(timestamp_ns: int):
    """
    查询小车在指定时刻的估计位置。

    返回: { x, y, z, yaw, velocity, steering } 或 null
    """
    state = estimator.get_position(timestamp_ns)
    if state is None:
        return {"status": "no_data", "message": "No state estimate yet — send /kinematics first"}
    return {
        "status": "ok",
        "timestamp_ns": state.timestamp_ns,
        "x": round(state.x, 4),
        "y": round(state.y, 4),
        "z": round(state.z, 4),
        "yaw": round(state.yaw, 4),
        "velocity": round(state.velocity, 2),
        "steering": round(state.steering, 2),
    }


@router.get("/estimator/stats")
async def get_estimator_stats():
    """返回状态估计器的统计信息。"""
    return {
        "state": {
            "x": round(estimator.state.x, 4),
            "y": round(estimator.state.y, 4),
            "yaw": round(estimator.state.yaw, 4),
            "velocity": round(estimator.state.velocity, 2),
        },
        "stats": estimator.stats,
    }


# ============================================================
#  工具函数
# ============================================================

def quat_to_yaw(qw: float, qx: float, qy: float, qz: float) -> float:
    """四元数 → yaw (绕 Z 轴旋转角, rad)。"""
    siny = 2.0 * (qw * qz + qx * qy)
    cosy = 1.0 - 2.0 * (qy * qy + qz * qz)
    return math.atan2(siny, cosy)
