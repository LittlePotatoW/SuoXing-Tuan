# ============================================================
# backend/server/engine/engine.py
# 重建引擎核心类（单例）：接收帧 → 缓存 → 触发重建 → 存储结果
#
# 设计与用法:
#   导出 ReconstructionEngine 类
#   导出 create() / stop() / push_frame() / get_status() / get_result()
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

    def __init__(self, config: dict):
        recon_cfg = config.get('reconstruction', {})
        self._mode: str = recon_cfg.get('mode', 'incremental')
        self._frame_threshold: int = recon_cfg.get('frame_threshold', 30)
        self._voxel_size: float = recon_cfg.get('voxel_size', 0.01)

        self._buffer = FrameBuffer(threshold=self._frame_threshold)
        self._latest_result: _ReconstructionResult | None = None
        self._frame_count_total: int = 0
        self._engine_lock = threading.Lock()
        self._running: bool = False

    # ============================================================
    # 工厂方法
    # ============================================================

    @classmethod
    def create(cls, config: dict | None = None) -> 'ReconstructionEngine':
        global _instance
        with _lock:
            if _instance is None:
                if config is None:
                    from server.config import get_config
                    config = get_config()
                _instance = cls(config)
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
        if since is not None and self._latest_result.timestamp <= since:
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

            logger.info("trigger reconstruction, %d frames", len(frames))

            # 获取每帧的位置
            from server.estimation import PositionEstimator
            estimator = PositionEstimator.create()

            # 深度图 → 点云 + 查询位姿
            point_clouds = []
            positions = []
            for f in frames:
                try:
                    pc = depth_to_pointcloud(f.depth_map)
                    if pc is not None and len(pc) > 0:
                        pos = estimator.get_position_at(f.timestamp)
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
            from server.config import get_config
            config = get_config()
            merged = map_frames(point_clouds, positions, config)
            if merged is None:
                return

            # 与历史结果融合(全量/增量 + 降采样)
            previous = (self._latest_result.point_cloud
                        if self._latest_result else None)
            result_pc = fuse(merged, previous,
                             mode=self._mode,
                             voxel_size=self._voxel_size)

            # 导出点云文件
            pc_url = _save_pointcloud(result_pc, config)

            logger.info("重建完成: %d 帧, %d 点 → %s",
                         len(frames), len(result_pc), pc_url or "(内存)")

            self._latest_result = _ReconstructionResult(
                timestamp=time.time(),
                point_cloud_url=pc_url or "",
                point_cloud=result_pc,  # 增量模式下次用
                detections=[],
            )


def _save_pointcloud(pc: np.ndarray, config: dict) -> str | None:
    """导出点云为 PLY 文件，返回 URL 路径"""
    output_dir = config.get('output', {}).get('point_cloud_dir', 'output')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"recon_{time.time():.0f}.ply"
    filepath = os.path.join(output_dir, filename)
    try:
        _write_ply(filepath, pc)
        return f"/{output_dir}/{filename}"
    except Exception:
        logger.exception("保存点云文件失败")
        return None


def _write_ply(filepath: str, pc: np.ndarray) -> None:
    """写 ASCII PLY 文件"""
    n = len(pc)
    with open(filepath, 'w') as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {n}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("end_header\n")
        for i in range(n):
            f.write(f"{pc[i, 0]:.6f} {pc[i, 1]:.6f} {pc[i, 2]:.6f}\n")
