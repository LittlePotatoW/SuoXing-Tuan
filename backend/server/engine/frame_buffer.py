# ============================================================
# backend/server/engine/frame_buffer.py
# 帧缓冲区：缓存帧数据，达到阈值后供重建引擎消费
#
# 设计与用法:
#   导出 FrameBuffer 类 / FrameEntry dataclass
#   导出 push() / flush() / __len__() / is_ready() 方法
# ============================================================
#   BUFFER_CAPACITY  缓冲区最大帧数（默认 100）
# ============================================================

import threading
from dataclasses import dataclass, field

import numpy as np


@dataclass
class FrameEntry:
    """一帧数据，含预计算点云和 per-frame 检测结果"""
    frame_id: str
    timestamp: float
    image: str
    depth_map: str
    point_cloud: np.ndarray | None = None      # Poisson 用 (N,3)
    point_colors: np.ndarray | None = None      # (N,3) uint8 RGB
    depth_m: np.ndarray | None = None           # TSDF 用 (H,W) float32 深度米
    detections: list = field(default_factory=list)
    annotated_image: str = ''


class FrameBuffer:
    """线程安全的帧缓冲区"""

    def __init__(self, threshold: int = 30, capacity: int = 100):
        self._threshold = threshold
        self._capacity = capacity
        self._frames: list[FrameEntry] = []
        self._lock = threading.Lock()

    def push(self, entry: FrameEntry) -> None:
        """推入一帧。超出容量时丢弃最旧帧"""
        with self._lock:
            self._frames.append(entry)
            if len(self._frames) > self._capacity:
                self._frames.pop(0)

    def flush(self) -> list[FrameEntry]:
        """取出所有帧并清空缓冲区"""
        with self._lock:
            frames = list(self._frames)
            self._frames.clear()
            return frames

    def is_ready(self) -> bool:
        """帧数是否达到重建阈值"""
        with self._lock:
            return len(self._frames) >= self._threshold

    def __len__(self) -> int:
        with self._lock:
            return len(self._frames)

    @property
    def threshold(self) -> int:
        return self._threshold
