# ============================================================
# backend/realtime/fusion_router.py
# 实时融合路由 — 调度层
# 接收两路数据 → 融合 → 送入重建管线
# ============================================================

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter

from state_estimation.estimator import StateEstimator
from fusion.manager import DataFusionManager

logger = logging.getLogger("realtime.fusion")

# ── 开关 ──
yolo_enabled: bool = True
reconstruction_enabled: bool = True
location_count: int = 0
detection_count: int = 0
fusion_count: int = 0
_state_lock = asyncio.Lock()

# ── 可注入的外部依赖 ──
_inference_engine = None

# ── 单例 ──
estimator = StateEstimator()
fusion_manager = DataFusionManager(dead_reckoning_engine=estimator)

router = APIRouter(prefix="/api/realtime", tags=["realtime"])


def set_inference_engine(eng):
    global _inference_engine
    _inference_engine = eng


@router.get("/status")
async def get_status():
    s = estimator.state
    return {
        "yolo_enabled": yolo_enabled,
        "reconstruction_enabled": reconstruction_enabled,
        "estimator": {"x": round(s.x, 4), "y": round(s.y, 4), "yaw": round(s.yaw, 4)},
        "counts": {"location": location_count, "detection": detection_count, "fusion": fusion_count},
        "estimator_stats": estimator.stats,
    }


@router.post("/toggle")
async def toggle(payload: dict):
    global yolo_enabled, reconstruction_enabled
    async with _state_lock:
        if "yolo" in payload:
            yolo_enabled = bool(payload["yolo"])
        if "reconstruction" in payload:
            reconstruction_enabled = bool(payload["reconstruction"])
    return {"yolo_enabled": yolo_enabled, "reconstruction_enabled": reconstruction_enabled}


@router.post("/feed/location")
async def feed_location(payload: dict):
    global location_count
    try:
        # feed_location_data 内部已调用 StateEstimator.update_kinematics()，此处不重复
        fusion_manager.feed_location_data(payload)
        async with _state_lock:
            location_count += 1
        return {"status": "ok", "count": location_count}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/feed/detection")
async def feed_detection(payload: dict):
    global detection_count, fusion_count
    try:
        ts = payload.get("timestamp_ns", 0)
        final = fusion_manager.process_detection(payload)
        async with _state_lock:
            detection_count += 1
        if not final:
            return {"status": "skipped", "reason": "no point_cloud"}

        from realtime.preprocessor import preprocess
        final = preprocess(final)

        if not reconstruction_enabled:
            return {"status": "ok", "reconstruction": "disabled"}

        sf = _build_sensor_frame(final, ts)

        import asyncio
        import reconstruction.routes as _routes
        loop = asyncio.get_running_loop()

        def _proc():
            fused = _routes.fusion.process(sf)
            if fused is None: return None
            _routes.engine.add_frame(fused)
            return _routes.engine.get_result()

        result = await loop.run_in_executor(None, _proc)
        async with _state_lock:
            fusion_count += 1

        # YOLO
        yolo_hits = 0
        if yolo_enabled and _inference_engine and _inference_engine.loaded:
            yolo_hits = _run_yolo(final, _routes.engine, _routes.CAMERA_INTRINSICS_CONFIG)

        if result and result.status == "completed":
            from reconstruction.routes import _broadcast
            asyncio.create_task(_broadcast({"type": "rebuild_complete", "data": result.model_dump(), "layered": _routes.engine.mode == "layered"}))

        return {"status": "ok", "fusion_count": fusion_count, "yolo_detections": yolo_hits, "final": final}

    except Exception as e:
        logger.error("feed_detection: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


@router.post("/feed/fusion")
async def feed_fusion(payload: dict):
    """手动模式回放: 接收预融合数据包, 补全 camera_pose 后直接走管线。"""
    try:
        # 从 config.yaml 补全 camera_pose (LiDAR/相机位姿对齐)
        try:
            from config_loader import CONFIG
            _cameras = CONFIG.get("sensors", {}).get("cameras", [])
            _cp = _cameras[0].get("pose_in_body", {}) if _cameras else {}
            _dft_pos = _cp.get("position", [0, 0, 1])
            _dft_rot = _cp.get("rotation", [0.7071, 0, 0.7071, 0])
        except Exception:
            _dft_pos = [0, 0, 1]
            _dft_rot = [0.7071, 0, 0.7071, 0]

        for cv in payload.get("camera_views", []):
            if "camera_pose" not in cv:
                cv["camera_pose"] = {
                    "position": {"x": _dft_pos[0], "y": _dft_pos[1], "z": _dft_pos[2]},
                    "rotation": {"qw": _dft_rot[0], "qx": _dft_rot[1], "qy": _dft_rot[2], "qz": _dft_rot[3]},
                }

        ts = payload.get("timestamp_ns", 0)
        sf = _build_sensor_frame(payload, ts)

        import reconstruction.routes as _routes
        loop = asyncio.get_running_loop()

        def _proc():
            fused = _routes.fusion.process(sf)
            if fused is None: return None
            _routes.engine.add_frame(fused)
            return _routes.engine.get_result()

        result = await loop.run_in_executor(None, _proc)

        if result and result.status == "completed":
            from reconstruction.routes import _broadcast
            asyncio.create_task(_broadcast({"type": "rebuild_complete", "data": result.model_dump(), "layered": _routes.engine.mode == "layered"}))

        return {"status": "ok"}
    except Exception as e:
        logger.error("feed_fused: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


def _build_sensor_frame(final: dict, ts: int):
    from common.schemas import (
        SensorFrame, PointCloudData, CarPosition, Pose6DoF, Vector3, Quaternion, CameraView,
    )
    cp = final["car_position"]
    pc = final["point_cloud"]
    return SensorFrame(
        frame_id=final.get("frame_id", f"det_{ts}"),
        timestamp_ns=ts,
        point_cloud=PointCloudData(points=pc["points"], point_count=pc["point_count"]),
        car_position=CarPosition(
            pose=Pose6DoF(
                position=Vector3(x=cp["pose"]["position"]["x"], y=cp["pose"]["position"]["y"], z=cp["pose"]["position"]["z"]),
                rotation=Quaternion(qw=cp["pose"]["rotation"]["qw"], qx=cp["pose"]["rotation"]["qx"], qy=cp["pose"]["rotation"]["qy"], qz=cp["pose"]["rotation"]["qz"]),
            ), timestamp_ns=ts,
        ),
        camera_views=[
            CameraView(
                image_data=cv.get("image_data"),
                width=cv.get("width", 640), height=cv.get("height", 480),
                camera_pose=Pose6DoF(
                    position=Vector3(x=cv["camera_pose"]["position"]["x"], y=cv["camera_pose"]["position"]["y"], z=cv["camera_pose"]["position"]["z"]),
                    rotation=Quaternion(qw=cv["camera_pose"]["rotation"]["qw"], qx=cv["camera_pose"]["rotation"]["qx"], qy=cv["camera_pose"]["rotation"]["qy"], qz=cv["camera_pose"]["rotation"]["qz"]),
                ),
            ) for cv in final.get("camera_views", [])
        ],
    )


def _run_yolo(final: dict, eng, camera_intrinsics_config: list = None) -> int:
    import numpy as np
    from PIL import Image
    from io import BytesIO
    from reconstruction.projector import DefectProjector

    def _decode_rgb(image_data):
        try:
            if isinstance(image_data, str):
                import base64
                image_data = base64.b64decode(image_data)
            elif isinstance(image_data, bytes) and image_data[:2] != b'\xff\xd8':
                import base64
                image_data = base64.b64decode(image_data)
            pil_img = Image.open(BytesIO(image_data)).convert("RGB")
            return np.array(pil_img)
        except Exception:
            return None

    _proj_intrinsics = {}
    if camera_intrinsics_config:
        for _i, _cfg in enumerate(camera_intrinsics_config):
            _proj_intrinsics[_i] = {
                "fx": _cfg["K"][0][0], "fy": _cfg["K"][1][1],
                "cx": _cfg["K"][0][2], "cy": _cfg["K"][1][2],
                "width": _cfg["image_width"], "height": _cfg["image_height"],
                "K": np.array(_cfg["K"], dtype=np.float64),
                "dist_coeff": np.array(_cfg["dist_coeff"], dtype=np.float64),
            }
    proj = DefectProjector(camera_intrinsics=_proj_intrinsics if _proj_intrinsics else None)
    hits = 0
    car_pose = final["car_position"]["pose"]
    car_world = {"position": car_pose["position"], "rotation": car_pose["rotation"]}
    for idx, cv in enumerate(final.get("camera_views", [])):
        if not cv.get("image_data"): continue
        img = _decode_rgb(cv["image_data"])
        if img is None: continue
        try:
            res = _inference_engine.infer(img)
        except Exception as exc:
            logger.warning("YOLO inference failed for camera %d: %s", idx, exc)
            continue
        if not res or not res.detections: continue

        cam_pose_body = {
            "position": cv.get("camera_pose", {}).get("position", {"x": 0, "y": 0, "z": 0}),
            "rotation": cv.get("camera_pose", {}).get("rotation", {"qw": 1, "qx": 0, "qy": 0, "qz": 0}),
        }
        depth = proj.compute_depth_from_point_cloud(
            final["point_cloud"]["points"], cam_pose_body, car_world,
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
                eng.add_crack(x=w["x"], y=w["y"], z=w["z"], confidence=det.confidence, crack_type=det.class_name)
                hits += 1
    return hits
