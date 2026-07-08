# ============================================================
# backend/reconstruction/routes.py
# 三维重建 API — 接收帧 + 文件夹回放 + 实时推送
# ============================================================

import logging
import asyncio
from typing import Optional

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from common.schemas import SensorFrame
from common.camera import CameraIntrinsics
from fusion.datafusion import DataFusion
from reconstruction.engine import ReconstructionEngine
from loader.scene_loader import SceneLoader

logger = logging.getLogger("reconstruction.routes")

# ── 可调参数 ──
LIDAR_POSE_IN_BODY = [0.0, 0.0, 0.5, 1.0, 0.0, 0.0, 0.0]

# ── 相机内参配置（每个相机一个条目，与 CameraView 顺序对应）──
# 实际部署时替换为标定值；设空列表则禁用颜色渲染
CAMERA_INTRINSICS_CONFIG = [
    {
        "K": [[600.0, 0.0, 272.0],
              [0.0, 600.0, 192.0],
              [0.0, 0.0, 1.0]],
        "dist_coeff": [0.0, 0.0, 0.0, 0.0, 0.0],  # 无镜头畸变
        "image_width": 544,
        "image_height": 384,
    },
]


def _build_intrinsics(config: list[dict]) -> list[CameraIntrinsics]:
    result: list[CameraIntrinsics] = []
    for cfg in config:
        result.append(CameraIntrinsics(
            K=np.array(cfg["K"], dtype=np.float64),
            dist_coeff=np.array(cfg["dist_coeff"], dtype=np.float64),
            image_width=cfg["image_width"],
            image_height=cfg["image_height"],
        ))
    return result


# ── 模块级单例 ──
fusion = DataFusion(
    sensor_pose_in_body=LIDAR_POSE_IN_BODY,
    camera_intrinsics_list=_build_intrinsics(CAMERA_INTRINSICS_CONFIG),
)
engine = ReconstructionEngine()
_loader: Optional[SceneLoader] = None
_ws_clients: list[WebSocket] = []

router = APIRouter(prefix="/api/reconstruction", tags=["reconstruction"])


# ============================================================
# 帧上传 (硬件模式)
# ============================================================

@router.post("/frame")
async def upload_frame(frame: SensorFrame):
    loop = asyncio.get_running_loop()

    def _process():
        fused = fusion.process(frame)
        if fused is None:
            return None
        engine.add_frame(fused)
        return engine.get_result()

    result = await loop.run_in_executor(None, _process)
    if result is None:
        return {"status": "skipped", "reason": "invalid frame"}

    if result.status == "completed":
        asyncio.create_task(_broadcast({"type": "rebuild_complete", "data": result.model_dump()}))

    return {
        "status": "ok",
        "frame_id": frame.frame_id,
        "total_frames": engine.frame_count,
        "rebuild_triggered": result.status == "completed",
    }


@router.get("/result")
async def get_result():
    return engine.get_result().model_dump()


@router.get("/status")
async def get_status():
    r = engine.get_result()
    return {"status": r.status, "total_frames": r.total_frames, "total_points": r.total_points}


# ============================================================
# 文件夹回放 (离线模式)
# ============================================================

@router.post("/load")
async def load_scene(payload: dict):
    """加载场景文件夹，启动离线回放（每次重置引擎）"""
    global _loader, engine
    scene_path = payload.get("scene_path", "")
    interval = float(payload.get("interval", 0.05))

    if not scene_path:
        return {"status": "error", "message": "scene_path required"}

    # 停止当前回放 + 重建引擎
    if _loader and _loader.is_running:
        _loader.stop()
    engine = ReconstructionEngine()

    try:
        _loader = SceneLoader(scene_path)
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}

    asyncio.create_task(_broadcast({"type": "load_started", "total_frames": _loader.total_frames}))

    async def on_frame(frame: SensorFrame, idx: int):
        loop = asyncio.get_running_loop()

        def _process():
            fused = fusion.process(frame)
            if fused is None:
                return None
            engine.add_frame(fused)
            return engine.get_result()

        result = await loop.run_in_executor(None, _process)
        if result is None:
            return
        msg = {"type": "load_progress", "current_frame": idx + 1, "total_frames": _loader.total_frames}
        if result.status == "completed":
            msg["rebuild"] = result.model_dump()
        asyncio.create_task(_broadcast(msg))

    async def on_complete():
        asyncio.create_task(_broadcast({"type": "load_complete", "total_frames": _loader.total_frames}))

    asyncio.create_task(_loader.run(interval=interval, on_frame=on_frame, on_complete=on_complete))
    return {"status": "ok", "total_frames": _loader.total_frames}


@router.post("/control")
async def control_playback(payload: dict):
    """控制离线回放: pause / resume / stop / seek"""
    global _loader
    if _loader is None:
        return {"status": "error", "message": "no active scene"}

    action = payload.get("action", "")
    if action == "pause":
        _loader.pause()
    elif action == "resume":
        async def on_frame(frame, idx):
            loop = asyncio.get_running_loop()

            def _process():
                fused = fusion.process(frame)
                if fused:
                    engine.add_frame(fused)

            await loop.run_in_executor(None, _process)
            asyncio.create_task(_broadcast({
                "type": "load_progress", "current_frame": idx + 1, "total_frames": _loader.total_frames
            }))
        async def on_complete():
            asyncio.create_task(_broadcast({"type": "load_complete"}))
        _loader.resume()
        asyncio.create_task(_loader.run(interval=0.05, on_frame=on_frame, on_complete=on_complete))
    elif action == "stop":
        _loader.stop()
    elif action == "seek":
        idx = int(payload.get("frame", 0))
        _loader.seek(idx)
    else:
        return {"status": "error", "message": f"unknown action: {action}"}

    return {"status": "ok", "action": action, "current_frame": _loader.current_index}


# ============================================================
# WebSocket — 实时推送
# ============================================================

@router.websocket("/ws")
async def ws_reconstruction(ws: WebSocket):
    await ws.accept()
    _ws_clients.append(ws)
    logger.info("Reconstruction WS: client connected (%d total)", len(_ws_clients))

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        _ws_clients.remove(ws)
        logger.info("Reconstruction WS: client disconnected (%d total)", len(_ws_clients))


async def _broadcast(payload: dict) -> None:
    dead: list[WebSocket] = []
    for ws in _ws_clients:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)
