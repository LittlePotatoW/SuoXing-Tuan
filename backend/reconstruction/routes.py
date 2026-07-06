# ============================================================
#  文件: backend/reconstruction/routes.py
#  所属: SuoXing-Tuan / V2 三维重建 API
#  职责: 接收硬件上传的数据帧 + 提供重建结果给前端
# ============================================================

# ============================================================
#  ⚙️ 可调参数
# ============================================================

# 激光雷达在小车上的安装位姿 [x, y, z, qw, qx, qy, qz]
# 需要硬件组标定后填入
LIDAR_POSE_IN_BODY = [0.0, 0.0, 0.5, 1.0, 0.0, 0.0, 0.0]

# ============================================================
#  代码
# ============================================================

import logging
import asyncio
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from common.schemas import SensorFrame
from pipeline.fusion import DataFusion
from reconstruction.engine import ReconstructionEngine

logger = logging.getLogger("reconstruction.routes")

# ── 模块级单例 ──
fusion = DataFusion(sensor_pose_in_body=LIDAR_POSE_IN_BODY)
engine = ReconstructionEngine()

# ── WebSocket 客户端 ──
_ws_clients: list[WebSocket] = []

# ── 路由 ──
router = APIRouter(prefix="/api/reconstruction", tags=["reconstruction"])


@router.post("/frame")
async def upload_frame(frame: SensorFrame):
    """
    硬件组上传一帧数据。
    请求体: SensorFrame JSON
    处理: 坐标融合 → 累积点云 → 触发表面重建（如果需要）
    """
    fused = fusion.process(frame)

    if fused is None:
        return {"status": "skipped", "reason": "invalid frame"}

    engine.add_frame(fused)

    # 如果刚刚触发了重建，推送结果给所有 WebSocket 客户端
    result = engine.get_result()
    if result.status == "completed":
        asyncio.create_task(_broadcast(result.model_dump()))

    return {
        "status": "ok",
        "frame_id": frame.frame_id,
        "total_frames": engine.frame_count,
        "rebuild_triggered": result.status == "completed",
    }


@router.get("/result")
async def get_result():
    """前端轮询获取最新重建结果。"""
    return engine.get_result().model_dump()


@router.get("/status")
async def get_status():
    """获取引擎状态。"""
    r = engine.get_result()
    return {
        "status": r.status,
        "total_frames": r.total_frames,
        "total_points": r.total_points,
    }


# ================================================================
#  WebSocket — 实时推送
# ================================================================

@router.websocket("/ws")
async def ws_reconstruction(ws: WebSocket):
    """前端连接此 WebSocket，每次重建完成后自动收到 Mesh 数据。"""
    await ws.accept()
    _ws_clients.append(ws)
    logger.info("Reconstruction WS: client connected (%d total)", len(_ws_clients))

    try:
        while True:
            data = await ws.receive_text()
            # 前端可以发送命令，预留
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        _ws_clients.remove(ws)
        logger.info("Reconstruction WS: client disconnected (%d total)", len(_ws_clients))


async def _broadcast(payload: dict) -> None:
    """向所有 WebSocket 客户端推送重建结果。"""
    dead: list[WebSocket] = []
    for ws in _ws_clients:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)
