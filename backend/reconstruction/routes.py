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
# 优先从 config.yaml 读取，不存在时用默认值
try:
    from config_loader import CONFIG
    _sensors = CONFIG.get("sensors", {})
    LIDAR_POSE_IN_BODY = _sensors.get("lidar_pose_in_body", [0.0, 0.0, 0.5, 1.0, 0.0, 0.0, 0.0])
    _cameras = _sensors.get("cameras", [])
    CAMERA_INTRINSICS_CONFIG = [
        {
            "K": c["K"],
            "dist_coeff": c.get("dist_coeff", [0,0,0,0,0]),
            "image_width": c["width"],
            "image_height": c["height"],
        }
        for c in _cameras
    ] if _cameras else [{
        "K": [[640.0, 0.0, 320.0], [0.0, 640.0, 240.0], [0.0, 0.0, 1.0]],
        "dist_coeff": [0.0, 0.0, 0.0, 0.0, 0.0],
        "image_width": 640, "image_height": 480,
    }]
except Exception:
    LIDAR_POSE_IN_BODY = [0.0, 0.0, 0.5, 1.0, 0.0, 0.0, 0.0]
    CAMERA_INTRINSICS_CONFIG = [
        {
            "K": [[640.0, 0.0, 320.0], [0.0, 640.0, 240.0], [0.0, 0.0, 1.0]],
            "dist_coeff": [0.0, 0.0, 0.0, 0.0, 0.0],
            "image_width": 640, "image_height": 480,
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
_ws_lock = asyncio.Lock()

router = APIRouter(prefix="/api/reconstruction", tags=["reconstruction"])


# ============================================================
# 帧上传 (硬件模式)
# ============================================================

@router.post("/frame")
async def upload_frame(frame: SensorFrame):
    logger.info("Frame received: %s, %d cam_views, %d pts",
                frame.frame_id, len(frame.camera_views),
                frame.point_cloud.point_count if frame.point_cloud else 0)
    loop = asyncio.get_running_loop()

    def _process():
        fused = fusion.process(frame)
        if fused is None:
            return None
        engine.add_frame(fused)

        # YOLO 裂缝检测 + 2D→3D 投影
        from realtime.fusion_router import _inference_engine
        logger.info("YOLO check: engine=%s loaded=%s cam_views=%d",
                    _inference_engine is not None,
                    _inference_engine.loaded if _inference_engine else False,
                    len(frame.camera_views))
        if _inference_engine and _inference_engine.loaded:
            _run_yolo_on_frame(frame, fused, engine)

        return engine.get_result()

    result = await loop.run_in_executor(None, _process)
    if result is None:
        return {"status": "skipped", "reason": "invalid frame"}

    if result.status == "completed":
        asyncio.create_task(_broadcast({"type": "rebuild_complete", "data": result.model_dump(), "layered": engine.mode == "layered"}))

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


@router.post("/reset")
async def reset_engine(payload: dict = {}):
    """清空重建数据 + 应用新配置。"""
    global engine
    engine = ReconstructionEngine(
        mode=payload.get("mode", engine.mode),
        rebuild_interval_frames=int(payload.get("interval", engine.rebuild_interval_frames)),
    )
    return {"status": "ok"}


@router.post("/config")
async def set_config(payload: dict):
    """修改重建参数。"""
    global engine
    if "mode" in payload:
        engine.mode = payload["mode"]
    if "interval" in payload:
        engine.rebuild_interval_frames = int(payload["interval"])
    return {
        "mode": engine.mode,
        "interval": engine.rebuild_interval_frames,
    }


@router.get("/config")
async def get_config():
    """查询重建参数。"""
    return {
        "mode": engine.mode,
        "interval": engine.rebuild_interval_frames,
        "total_frames": engine.frame_count,
        "total_points": engine._total_points,
    }


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

    # 停止当前回放 + 重建引擎（继承当前配置）
    if _loader and _loader.is_running:
        _loader.stop()
    _cfg = {"mode": engine.mode, "interval": engine.rebuild_interval_frames}
    engine = ReconstructionEngine(
        mode=_cfg["mode"], rebuild_interval_frames=_cfg["interval"],
    )

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
        msg = {"type": "load_progress", "current_frame": idx + 1, "total_frames": _loader.total_frames, "layered": engine.mode == "layered"}
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
        # 从下一帧开始（当前帧已处理）
        _loader.seek(_loader.current_index + 1)

        async def on_frame(frame, idx):
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
            msg = {"type": "load_progress", "current_frame": idx + 1, "total_frames": _loader.total_frames, "layered": engine.mode == "layered"}
            if result.status == "completed":
                msg["rebuild"] = result.model_dump()
            asyncio.create_task(_broadcast(msg))

        async def on_complete():
            asyncio.create_task(_broadcast({"type": "load_complete", "total_frames": _loader.total_frames}))
        _loader.resume()
        asyncio.create_task(_loader.run(interval=0.05, on_frame=on_frame, on_complete=on_complete,
                                        from_beginning=False))
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
    async with _ws_lock:
        _ws_clients.append(ws)
    logger.info("Reconstruction WS: client connected (%d total)", len(_ws_clients))

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        async with _ws_lock:
            _ws_clients.remove(ws)
        logger.info("Reconstruction WS: client disconnected (%d total)", len(_ws_clients))


def _run_yolo_on_frame(frame, fused, eng) -> int:
    """在 SensorFrame 上跑 YOLO，检测结果投影到 3D 并存为裂缝标注。"""
    import numpy as np
    from PIL import Image
    from io import BytesIO
    from reconstruction.projector import DefectProjector
    from realtime.fusion_router import _inference_engine

    def _decode_rgb(image_data):
        try:
            # 处理 base64 编码: Pydantic bytes 字段可能是 base64 字符串
            if image_data[:2] != b'\xff\xd8':
                import base64
                try:
                    image_data = base64.b64decode(image_data)
                except Exception:
                    pass
            pil_img = Image.open(BytesIO(image_data)).convert("RGB")
            return np.array(pil_img)
        except Exception:
            return None

    # 把 CAMERA_INTRINSICS_CONFIG 转成 DefectProjector 格式
    _cam_intrinsics = {}
    for _i, _cfg in enumerate(CAMERA_INTRINSICS_CONFIG):
        _cam_intrinsics[_i] = {
            "fx": _cfg["K"][0][0], "fy": _cfg["K"][1][1],
            "cx": _cfg["K"][0][2], "cy": _cfg["K"][1][2],
            "width": _cfg["image_width"], "height": _cfg["image_height"],
            "K": np.array(_cfg["K"], dtype=np.float64),
            "dist_coeff": np.array(_cfg["dist_coeff"], dtype=np.float64),
        }
    proj = DefectProjector(camera_intrinsics=_cam_intrinsics if _cam_intrinsics else None)
    hits = 0
    car_pos = frame.car_position
    if car_pos is None:
        return hits
    cp = car_pos.pose
    car_world = {
        "position": {"x": cp.position.x, "y": cp.position.y, "z": cp.position.z},
        "rotation": {"qw": cp.rotation.qw, "qx": cp.rotation.qx, "qy": cp.rotation.qy, "qz": cp.rotation.qz},
    }

    for idx, cv in enumerate(frame.camera_views):
        if not cv.image_data:
            continue
        img = _decode_rgb(cv.image_data)
        if img is None:
            continue
        try:
            res = _inference_engine.infer(img)
        except Exception as exc:
            logger.warning("YOLO infer failed cam %d: %s", idx, exc)
            continue
        if not res or not res.detections:
            continue
        cp2 = cv.camera_pose
        cam_pose_body = {
            "position": {"x": cp2.position.x, "y": cp2.position.y, "z": cp2.position.z},
            "rotation": {"qw": cp2.rotation.qw, "qx": cp2.rotation.qx, "qy": cp2.rotation.qy, "qz": cp2.rotation.qz},
        }
        depth = proj.compute_depth_from_point_cloud(
            frame.point_cloud.points, cam_pose_body, car_world,
        )
        for det in res.detections:
            x1, y1, x2, y2 = det.bbox
            u, v = (x1 + x2) / 2, (y1 + y2) / 2
            w = proj.project_pixel_defect(
                u=float(u), v=float(v), depth=depth, camera_index=idx,
                camera_pose_in_body=cam_pose_body,
                car_pose_in_world=car_world,
            )
            if w:
                eng.add_crack(x=w["x"], y=w["y"], z=w["z"],
                              confidence=det.confidence, crack_type=det.class_name)
                hits += 1
    if hits:
        logger.info("YOLO: %d cracks found in frame %s", hits, frame.frame_id)
    return hits


async def _broadcast(payload: dict) -> None:
    async with _ws_lock:
        clients = list(_ws_clients)
    dead: list[WebSocket] = []
    for ws in clients:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    if dead:
        async with _ws_lock:
            for ws in dead:
                try:
                    _ws_clients.remove(ws)
                except ValueError:
                    pass  # already removed by disconnect handler
