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

import logging
import os
import threading
import time
from dataclasses import dataclass, field

import numpy as np

from server.engine.frame_buffer import FrameBuffer, FrameEntry
from server.pointcloud import depth_to_pointcloud
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


class ReconstructionEngine:
    """重建引擎（单例），帧累积 → 触发重建"""

    def __init__(self, config: dict,
                 mode: str | None = None,
                 frame_threshold: int | None = None,
                 voxel_size: float | None = None,
                 yolo_enabled: bool = True):
        recon_cfg = config.get('reconstruction', {})
        self._mode: str = mode or recon_cfg.get('mode', 'incremental')
        self._frame_threshold: int = (frame_threshold
                                      if frame_threshold is not None
                                      else recon_cfg.get('frame_threshold', 30))
        self._voxel_size: float = (voxel_size
                                   if voxel_size is not None
                                   else recon_cfg.get('voxel_size', 0.01))
        self._yolo_enabled: bool = yolo_enabled

        self._buffer = FrameBuffer(threshold=self._frame_threshold)
        self._latest_result: _ReconstructionResult | None = None
        self._frame_count_total: int = 0
        self._engine_lock = threading.Lock()
        self._running: bool = False

    # ============================================================
    # 工厂方法
    # ============================================================

    @classmethod
    def create(cls, mode: str | None = None,
               frame_threshold: int | None = None,
               voxel_size: float | None = None,
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
        """接收一帧数据（RGB + 深度图 base64），缓存后检查是否触发重建"""
        entry = FrameEntry(
            frame_id=frame_id,
            timestamp=timestamp,
            image=image,
            depth_map=depth_map,
        )
        self._buffer.push(entry)
        self._frame_count_total += 1

        logger.debug("push frame %s, buffer=%d/%d",
                     frame_id, len(self._buffer), self._buffer.threshold)

        if self._buffer.is_ready():
            self._trigger()

    # ============================================================
    # 查询接口
    # ============================================================

    def get_config(self) -> dict:
        return {
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

            subsample = config.get('depth', {}).get('subsample', 1)
            surface_enabled = config.get('reconstruction', {}).get('surface', {}).get('enabled', False)

            # 获取每帧的位置
            from server.estimation import PositionEstimator
            estimator = PositionEstimator.create()

            # 深度图 → 点云 + 查询位姿
            point_clouds = []
            positions = []
            raw_points = 0
            for f in frames:
                try:
                    pc = depth_to_pointcloud(f.depth_map, subsample=subsample)
                    if pc is not None and len(pc) > 0:
                        pos = estimator.get_position_at(f.timestamp)
                        raw_points += len(pc)
                        point_clouds.append(pc)
                        positions.append({
                            'x': pos.x, 'y': pos.y,
                            'heading': pos.heading,
                        })
                except Exception:
                    logger.exception("处理帧 %s 失败", f.frame_id)

            if not point_clouds:
                logger.warning("无有效点云，跳过此次重建")
                return

            # 多帧点云 → 世界坐标拼接
            merged = map_frames(point_clouds, positions, config)
            if merged is None:
                return

            # 与历史结果融合(全量/增量 + 降采样)，始终降采样避免点云无限膨胀
            previous = (self._latest_result.point_cloud
                        if self._latest_result else None)
            result_pc = fuse(merged, previous,
                             mode=self._mode,
                             voxel_size=self._voxel_size)

            # YOLO 检测（如果开启）
            detections = []
            if self._yolo_enabled:
                try:
                    from server.detection import Detector, apply_nms
                    detector = Detector.create()
                    if detector.available:
                        all_dets = []
                        for f in frames:
                            try:
                                fd = detector.detect(f.image)
                                all_dets.extend(fd)
                            except Exception:
                                logger.exception("检测帧 %s 失败", f.frame_id)
                        if all_dets:
                            all_dets = apply_nms(all_dets)
                            # TODO: 3D 映射需要有序点云 (H,W,3) + 深度图，
                            # 当前 depth_to_pointcloud 返回无序 (N,3)，
                            # 需重构点云数据流后再启用 map_to_3d
                        detections = all_dets
                except Exception:
                    logger.exception("YOLO 检测管线异常")

            # 表面重建（可选，由 config 控制；失败自动回退到点云）
            mesh_url = None
            surface_cfg = config.get('reconstruction', {}).get('surface', {})
            if surface_cfg.get('enabled', False):
                try:
                    from server.reconstruction import reconstruct_surface
                    mesh_url = reconstruct_surface(result_pc, config)
                except Exception:
                    logger.exception("表面重建失败，回退到点云模式")

            # 导出文件（mesh PLY 或 点云 PLY）
            pc_url = mesh_url or _save_pointcloud(result_pc, config)

            elapsed = (time.perf_counter() - t0) * 1000
            output_type = "mesh" if mesh_url else "point-cloud"
            logger.info(
                "=== 重建完成 (%.0fms) ===\n"
                "  帧数: %d (成功), subsample=%d, 模式=%s\n"
                "  原始点云: %d 点 → 拼接: %d 点 → 降采样: %d 点\n"
                "  输出类型: %s, YOLO缺陷: %d\n"
                "  文件: %s",
                elapsed, len(point_clouds), subsample, self._mode,
                raw_points, len(merged), len(result_pc),
                output_type, len(detections),
                pc_url or "(内存)",
            )

            self._latest_result = _ReconstructionResult(
                timestamp=time.time(),
                point_cloud_url=pc_url or "",
                point_cloud=result_pc,  # 增量模式下次用
                detections=detections,
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
