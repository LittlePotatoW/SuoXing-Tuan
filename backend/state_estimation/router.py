# ============================================================
#  文件: backend/data_pre_processing/kinematics_api.py
#  所属: SuoXing-Tuan / 数据融合与缺陷投影模块
#  职责: 运动学数据预处理 API
#        - 接收 kinematics 数据 → 喂入 StateEstimator
#        - 对外提供 /kinematics /position /estimator/stats 端点
#        - 提供 quat_to_yaw 工具函数
# ============================================================

import logging

from fastapi import APIRouter

from state_estimation.estimator import StateEstimator

logger = logging.getLogger("state_estimation.router")

# ── 模块级单例 ──
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
            "velocity": 0.5,
            "steering_angle": 0.0,
            "timestamp_ns": 1718208000000000000
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

    返回: { x, y, z, yaw, velocity, steering }
    """
    state = estimator.get_position(timestamp_ns)
    if state is None:
        return {"status": "no_data", "message": "No state estimate yet"}
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
    s = estimator.state
    return {
        "state": {
            "x": round(s.x, 4),
            "y": round(s.y, 4),
            "yaw": round(s.yaw, 4),
            "velocity": round(s.velocity, 2),
        },
        "stats": estimator.stats,
    }


# ============================================================
#  工具函数
# ============================================================

from common.transform import quat_to_yaw
