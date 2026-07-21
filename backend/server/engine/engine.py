# ============================================================
# backend/server/engine/engine.py
# 重建引擎核心类（单例）：接收帧 → 缓存 → 触发重建 → 存储结果
#
# 设计与用法:
#   导出 ReconstructionEngine 类
#   导出 create(mode, frame_threshold, voxel_size, config) / stop()
#   导出 push_frame() / get_status() / get_result() / get_config()
# ============================================================
#   FRAME_THRESHOLD  默认重建帧数阈值 (config.reconstruction.frame_threshold)
#   RECON_MODE       重建模式 (config.reconstruction.mode)
# ============================================================

import base64
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from server.engine.frame_buffer import FrameBuffer, FrameEntry
from server.pointcloud import decode_depth, sample_colors

# 标注图实时保存目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPORT_DATA_DIR = _PROJECT_ROOT / "Report_Data"
SESSION_DATA_DIR = _PROJECT_ROOT / "Session_Data"

# 当前 session 的报告名（开始建模时设置，停止时清空）
_current_report_name: str = ""

# Session 自动保存状态
_session_name: str = ""
_session_active: bool = False
_session_frame_idx: int = 0
_session_frame_count: int = 0
_session_last_manifest_save: int = 0
_session_start_time: float = 0.0
_session_telemetry: list = []
_session_frame_metas: list = []

def set_report_name(name: str) -> None:
    global _current_report_name
    _current_report_name = name
    if name:
        (REPORT_DATA_DIR / name / "images").mkdir(parents=True, exist_ok=True)

def clear_report_name() -> None:
    global _current_report_name
    _current_report_name = ""

def set_session_name(name: str) -> None:
    global _session_name, _session_active, _session_frame_idx
    global _session_frame_count, _session_last_manifest_save, _session_start_time
    global _session_telemetry, _session_frame_metas
    _session_name = name
    _session_active = True
    _session_frame_idx = 0
    _session_frame_count = 0
    _session_last_manifest_save = 0
    _session_start_time = time.time()
    _session_telemetry = []
    _session_frame_metas = []
    (SESSION_DATA_DIR / name / "frames").mkdir(parents=True, exist_ok=True)

def clear_session() -> None:
    global _session_active, _session_name
    _session_active = False
    _session_name = ""
from server.reconstruction import map_frames, fuse

logger = logging.getLogger(__name__)

_instance = None
_lock = threading.Lock()


@dataclass
class _ReconstructionResult:
    timestamp: float
    point_cloud_url: str
    point_cloud: np.ndarray | None = None
    detections: list = field(default_factory=list)
    mesh_data: dict | None = None
    camera_trail: list = field(default_factory=list)
    annotated_images: list = field(default_factory=list)


class ReconstructionEngine:
    """重建引擎（单例），帧累积 → 触发重建"""

    def __init__(self, config: dict,
                 mode: str | None = None,
                 frame_threshold: int | None = None,
                 voxel_size: float | None = None,
                 method: str | None = None,
                 yolo_enabled: bool = True):
        recon_cfg = config.get('reconstruction', {})
        self._mode: str = mode or recon_cfg.get('mode', 'incremental')
        self._frame_threshold: int = (frame_threshold
                                      if frame_threshold is not None
                                      else recon_cfg.get('frame_threshold', 30))
        self._voxel_size: float = (voxel_size
                                   if voxel_size is not None
                                   else recon_cfg.get('voxel_size', 0.01))
        self._method: str = method or recon_cfg.get('method', 'poisson')
        self._yolo_enabled: bool = yolo_enabled

        self._buffer = FrameBuffer(threshold=self._frame_threshold)
        self._latest_result: _ReconstructionResult | None = None
        self._frame_count_total: int = 0
        self._engine_lock = threading.Lock()
        self._running: bool = False
        self._cumulative_defects: list = []  # 跨批累积缺陷列表

    # ============================================================
    # 工厂方法
    # ============================================================

    @classmethod
    def create(cls, mode: str | None = None,
               frame_threshold: int | None = None,
               voxel_size: float | None = None,
               method: str | None = None,
               yolo_enabled: bool = True,
               config: dict | None = None) -> 'ReconstructionEngine':
        global _instance
        with _lock:
            if _instance is None:
                if config is None:
                    from server.config import get_config
                    config = get_config()
                _instance = cls(config, mode=mode,
                               frame_threshold=frame_threshold,
                               voxel_size=voxel_size,
                               method=method,
                               yolo_enabled=yolo_enabled)
                _instance._running = True
            return _instance

    @classmethod
    def stop(cls) -> None:
        global _instance
        with _lock:
            if _instance is not None:
                _instance._running = False
                _instance._buffer.flush()
            _instance = None

    # ============================================================
    # 帧数据入口
    # ============================================================

    def push_frame(self, frame_id: str, timestamp: float,
                   image: str, depth_map: str) -> None:
        """接收一帧数据（RGB + 深度图 base64），解码 + per-frame YOLO，缓存后检查是否触发重建"""
        # 1. 解码深度图（一次性），拿到有序和无序点云
        decoded = decode_depth(depth_map)
        if decoded is None:
            return
        ordered_pc, depth_m, pc = decoded

        # 2. YOLO per-frame（如果开启）— 2D 检测 + NMS + 3D 映射
        dets = []
        anno_img = ''
        if self._yolo_enabled:
            try:
                from server.detection import Detector, apply_nms, map_to_3d
                detector = Detector.create()
                if detector.available:
                    fd = detector.detect(image)
                    if fd:
                        fd = apply_nms(fd)                         # per-frame NMS
                        fd = map_to_3d(fd, ordered_pc, depth_m)    # 2D→3D，有序点云 ✓
                        dets = fd
                    # 全局唯一 id + 标注图实时写盘（同一帧共享）
                    anno = detector.latest_annotated()
                    anno_img_url = ''
                    anno_b64 = anno.get('annotated_image', '')
                    if dets and anno_b64 and _current_report_name:
                        try:
                            img_dir = REPORT_DATA_DIR / _current_report_name / "images"
                            img_dir.mkdir(parents=True, exist_ok=True)
                            fname = f"{frame_id}.jpg"
                            filepath = img_dir / fname
                            filepath.write_bytes(base64.b64decode(anno_b64))
                            anno_img_url = f"images/{fname}"
                        except Exception:
                            logger.exception("标注图写盘失败 frame=%s", frame_id)
                    for i, d in enumerate(dets):
                        d['id'] = f"{frame_id}_{i}"
                        d['annotated_image'] = anno_img_url
            except Exception:
                logger.exception("YOLO per-frame 失败, frame=%s", frame_id)

        # 2.5 将 center_3d 从相机坐标变换到世界坐标（对齐 mesh 坐标系）
        if dets:
            try:
                from server.estimation import PositionEstimator
                estimator = PositionEstimator.create()
                pos = estimator.get_position_at(timestamp)
                from server.config import get_config
                ext_cfg = get_config().get('camera_to_vehicle', {})
                ext_rot = ext_cfg.get('rotation', [0.0, 0.0, 0.0])
                ext_trans = ext_cfg.get('translation', [0.0, 0.0, 0.0])
                from server.reconstruction.mapper import _camera_to_world
                import numpy as np
                for d in dets:
                    c3 = np.array(d['center_3d'], dtype=np.float32).reshape(1, 3)
                    w3 = _camera_to_world(c3, {'x': pos.x, 'y': pos.y, 'heading': pos.heading},
                                          ext_rot, ext_trans)
                    d['center_3d'] = w3[0].tolist()
            except Exception:
                logger.exception("center_3d 坐标变换失败")

        # 2.6 从 RGB 图采样颜色（与点云对齐）
        pc_colors = None
        if pc is not None and len(pc) > 0:
            pc_colors = sample_colors(image, depth_m)

        # 3. 存 buffer（带预计算点云和检测结果）
        entry = FrameEntry(
            frame_id=frame_id, timestamp=timestamp,
            image=image, depth_map=depth_map,
            point_cloud=pc if self._method != 'tsdf' else None,
            point_colors=pc_colors,
            depth_m=depth_m if self._method == 'tsdf' else None,
            detections=dets,
            annotated_image=anno_img,
        )
        self._buffer.push(entry)
        self._frame_count_total += 1

        # Session 自动保存：帧文件直接写盘
        global _session_active, _session_frame_idx, _session_frame_count, _session_last_manifest_save
        if _session_active and _session_name:
            _session_frame_idx += 1
            _session_frame_count += 1
            frames_dir = SESSION_DATA_DIR / _session_name / "frames"
            try:
                img_name = f"{str(_session_frame_idx).zfill(5)}.jpg"
                dep_name = f"{str(_session_frame_idx).zfill(5)}.png"
                (frames_dir / img_name).write_bytes(base64.b64decode(image))
                (frames_dir / dep_name).write_bytes(base64.b64decode(depth_map))
                _session_frame_metas.append({
                    "id": _session_frame_idx, "ts": timestamp - _session_start_time,
                    "image": f"frames/{img_name}", "depth": f"frames/{dep_name}",
                })
                # 每 10 帧更新一次 manifest
                if _session_frame_count - _session_last_manifest_save >= 10:
                    _write_session_manifest()
                    _session_last_manifest_save = _session_frame_count
            except Exception:
                logger.exception("Session 帧写盘失败 frame=%s", frame_id)

        logger.debug("push frame %s, buffer=%d/%d, dets=%d",
                     frame_id, len(self._buffer), self._buffer.threshold, len(dets))

        if self._buffer.is_ready():
            self._trigger()

    # ============================================================
    # 查询接口
    # ============================================================

    def get_config(self) -> dict:
        return {
            'method': self._method,
            'mode': self._mode,
            'frame_threshold': self._frame_threshold,
            'voxel_size': self._voxel_size,
            'yolo_enabled': self._yolo_enabled,
            'frame_count': len(self._buffer),
            'status': self._current_status(),
        }

    def get_status(self) -> dict:
        return {
            "status": self._current_status(),
            "frame_count": len(self._buffer),
            "frame_threshold": self._frame_threshold,
            "last_result_timestamp": (
                self._latest_result.timestamp
                if self._latest_result else None
            ),
        }

    def get_result(self, since: float | None = None) -> dict | None:
        """获取最新重建结果。since 为增量查询时间戳"""
        if self._latest_result is None:
            return None
        if since is not None and self._latest_result.timestamp < since:
            return None
        return {
            "timestamp": self._latest_result.timestamp,
            "point_cloud_url": self._latest_result.point_cloud_url,
            "detections": self._latest_result.detections,
            "mesh_data": self._latest_result.mesh_data,
            "camera_trail": self._latest_result.camera_trail,
            "annotated_images": self._latest_result.annotated_images,
        }

    # ============================================================
    # 内部
    # ============================================================

    def _current_status(self) -> str:
        if not self._running:
            return "idle"
        if len(self._buffer) >= self._frame_threshold:
            return "reconstructing"
        return "accumulating"

    def _trigger(self) -> None:
        """触发一次重建"""
        with self._engine_lock:
            frames = self._buffer.flush()
            if not frames:
                return

            t0 = time.perf_counter()
            from server.config import get_config
            config = get_config()

            # 获取每帧的位置 + 直接用预计算点云（push_frame 已解码）
            from server.estimation import PositionEstimator
            estimator = PositionEstimator.create()

            positions = []
            camera_trail = []
            for f in frames:
                try:
                    pos = estimator.get_position_at(f.timestamp)
                    positions.append({
                        'x': pos.x, 'y': pos.y,
                        'heading': pos.heading,
                    })
                    camera_trail.append([pos.x, pos.y, 0.0])
                except Exception:
                    logger.exception("处理帧 %s 失败", f.frame_id)

            is_tsdf = (self._method == 'tsdf')

            if is_tsdf:
                result_pc = None
                result_colors = None
            else:
                # Poisson: 收集点云+颜色 → 世界坐标拼接 → 融合
                point_clouds = []
                color_blocks = []
                raw_points = 0
                for f in frames:
                    pc = f.point_cloud
                    if pc is not None and len(pc) > 0:
                        raw_points += len(pc)
                        point_clouds.append(pc)
                        if f.point_colors is not None and len(f.point_colors) == len(pc):
                            color_blocks.append(f.point_colors)
                if not point_clouds:
                    logger.warning("无有效点云，跳过此次重建")
                    return
                MAX_POINTS = 2_000_000
                if raw_points > MAX_POINTS:
                    keep = max(1, raw_points // (MAX_POINTS // 2))
                    for i in range(len(point_clouds)):
                        if len(point_clouds[i]) > 0:
                            point_clouds[i] = point_clouds[i][::keep]
                    for i in range(len(color_blocks)):
                        if len(color_blocks[i]) > 0:
                            color_blocks[i] = color_blocks[i][::keep]
                    logger.warning("compact: %d → ~%d 点", raw_points, raw_points // keep)
                merged = map_frames(point_clouds, positions, config)
                result_colors = np.vstack(color_blocks) if color_blocks else None
                if merged is None:
                    return
                previous = (self._latest_result.point_cloud
                            if self._latest_result else None)
                result_pc = fuse(merged, previous,
                                 mode=self._mode,
                                 voxel_size=self._voxel_size)

            # 收集 per-frame YOLO 结果（每个 defect 自带 annotated_image）+ center_3d 空间去重
            detections = []
            if self._yolo_enabled:
                all_dets = []
                for f in frames:
                    all_dets.extend(f.detections)
                if all_dets:
                    # center_3d 空间去重
                    dedup_r = config.get('reconstruction', {}).get('crack_dedup_radius', 0.3)
                    unique: list[dict] = []
                    for d in all_dets:
                        c3 = d.get('center_3d')
                        if not c3 or len(c3 or []) < 3:
                            unique.append(d)
                            continue
                        dup = False
                        for u in unique:
                            uc = u.get('center_3d')
                            if uc and len(uc) >= 3:
                                if np.linalg.norm(np.array(c3) - np.array(uc)) < dedup_r:
                                    dup = True
                                    break
                        if not dup:
                            unique.append(d)
                    logger.info("YOLO 去重: %d → %d (radius=%.2fm)", len(all_dets), len(unique), dedup_r)
                    detections = unique

            # 跨批累积 + 去重
            cross_dedup_r = config.get('reconstruction', {}).get('crack_dedup_radius', 0.3)
            if detections:
                for d in detections:
                    c3 = d.get("center_3d")
                    dup = False
                    if c3 and len(c3) >= 3:
                        for e in self._cumulative_defects:
                            ec = e.get("center_3d")
                            if ec and len(ec) >= 3:
                                if np.linalg.norm(np.array(c3) - np.array(ec)) < cross_dedup_r:
                                    dup = True
                                    break
                    if not dup:
                        self._cumulative_defects.append(d)
                logger.info("累积缺陷: %d (本批 %d)", len(self._cumulative_defects), len(detections))

            # 删除孤儿图（去重后不再被引用的标注图）
            if _current_report_name:
                try:
                    surviving = set()
                    for d in self._cumulative_defects:
                        img = d.get('annotated_image', '')
                        if img:
                            surviving.add(Path(img).name)
                    img_dir = REPORT_DATA_DIR / _current_report_name / "images"
                    if img_dir.exists():
                        for f in img_dir.iterdir():
                            if f.is_file() and f.name not in surviving:
                                f.unlink()
                except Exception:
                    pass

            # 自动写 Report metadata（后端驱动）
            if _current_report_name and self._cumulative_defects:
                try:
                    _write_report_metadata(_current_report_name, self._cumulative_defects)
                except Exception:
                    pass

            # 表面重建 / TSDF
            surface_result = None
            if is_tsdf:
                try:
                    from server.reconstruction import reconstruct_tsdf
                    surface_result = reconstruct_tsdf(frames, positions, config)
                except Exception:
                    logger.exception("TSDF 重建失败，回退到点云")
            else:
                surface_cfg = config.get('reconstruction', {}).get('surface', {})
                if surface_cfg.get('enabled', False):
                    try:
                        from server.reconstruction import reconstruct_surface
                        # result_pc: fused 几何 (点数可能与颜色不匹配)
                        # merged:   pre-fuse 点云, 与 result_colors 对齐
                        surface_result = reconstruct_surface(
                            result_pc, config,
                            colors=result_colors, color_ref=merged,
                        )
                    except Exception:
                        logger.exception("表面重建失败，回退到点云")

            if surface_result:
                pc_url = surface_result["url"]
                mesh_data = surface_result["mesh"]
            elif result_pc is not None:
                pc_url = _save_pointcloud(result_pc, config)
                mesh_data = _build_pointcloud_data(result_pc, result_colors)
            else:
                logger.warning("重建失败: 无 mesh 无点云")
                return

            elapsed = (time.perf_counter() - t0) * 1000
            output_type = "mesh" if surface_result else "point-cloud"
            n_frames = len(frames)
            n_result = len(result_pc) if result_pc is not None else 0
            logger.info(
                "=== 重建完成 (%.0fms) ===\n"
                "  帧数: %d, 方法=%s, 模式=%s\n"
                "  结果: %d 点, 输出: %s, YOLO: %d\n"
                "  文件: %s",
                elapsed, n_frames, self._method, self._mode,
                n_result, output_type, len(detections),
                pc_url or "(内存)",
            )

            self._latest_result = _ReconstructionResult(
                timestamp=time.time(),
                point_cloud_url=pc_url or "",
                point_cloud=result_pc,
                detections=detections,
                mesh_data=mesh_data,
                camera_trail=camera_trail,
            )


def _save_pointcloud(pc: np.ndarray, config: dict) -> str | None:
    """导出点云为二进制 PLY 文件（通过 Open3D），返回 URL 路径"""
    output_dir = config.get('output', {}).get('point_cloud_dir', 'output')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"recon_{time.time():.0f}.ply"
    filepath = os.path.join(output_dir, filename)
    try:
        import open3d as o3d
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pc.astype(np.float64))
        o3d.io.write_point_cloud(filepath, pcd, write_ascii=False)
        logger.info("二进制 PLY 已保存: %s (%d 点)", filename, len(pc))
    except Exception:
        logger.warning("Open3D PLY 写入失败, 回退到 ASCII")
        _write_ply_ascii(filepath, pc)
    return f"/{output_dir}/{filename}"


def _build_pointcloud_data(pc: np.ndarray, colors: np.ndarray | None = None) -> dict:
    """从点云构建 mesh_data dict（用于 WebSocket 直接推送）"""
    verts = pc.astype(np.float32)
    vc: list = []
    if colors is not None and len(colors) == len(verts):
        vc = colors.astype(np.uint8).ravel().tolist()
    return {
        "vertices": verts.ravel().tolist(),
        "faces": [],
        "vertex_count": int(len(verts)),
        "face_count": 0,
        "vertex_colors": vc,
    }


def _write_ply_ascii(filepath: str, pc: np.ndarray) -> None:
    """写 ASCII PLY 文件 (fallback)"""
    n = len(pc)
    with open(filepath, 'w') as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {n}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("end_header\n")
        for i in range(n):
            f.write(f"{pc[i, 0]:.6f} {pc[i, 1]:.6f} {pc[i, 2]:.6f}\n")


# ---------- Session / Report 写盘辅助 ----------

def _write_session_manifest() -> None:
    """增量写 manifest.json（追加模式）"""
    global _session_name, _session_start_time, _session_telemetry, _session_frame_metas, _session_frame_count
    if not _session_name:
        return
    manifest = {
        "version": 1,
        "start_time": _session_start_time,
        "end_time": time.time(),
        "frame_count": _session_frame_count,
        "telemetry_interval_ms": 100,
        "telemetry": _session_telemetry,
        "frames": _session_frame_metas,
    }
    p = SESSION_DATA_DIR / _session_name / "manifest.json"
    p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def finalize_session() -> None:
    """停止 Session：写最终 manifest 并重置状态"""
    global _session_active, _session_name
    if _session_active:
        _write_session_manifest()
    _session_active = False
    _session_name = ""


def finalize_report() -> None:
    """停止 Report：清标志位（目录和图片由引擎维护）"""
    clear_report_name()


def _write_report_metadata(name: str, defects: list, point_cloud_url: str = "") -> None:
    """写 Report metadata.json"""
    # 字段规范化: annotated_image → image（DefectDetail 读 image 字段）
    normalized = []
    for d in defects:
        dd = dict(d)
        ai = dd.pop('annotated_image', None) or dd.pop('annotatedImage', None)
        if ai:
            dd['image'] = ai
        normalized.append(dd)

    meta = {
        "task_name": name.replace("report_", "").split("_")[0] if name else "",
        "date": "",
        "point_cloud_url": point_cloud_url,
        "defects": normalized,
    }
    p = REPORT_DATA_DIR / name / "metadata.json"
    p.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
