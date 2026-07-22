# ============================================================
# backend/server/estimation/rgbd_estimator.py
# RGB-D 视觉里程计估计器 —— 帧驱动 + actor 线程，完全自包含
#
# 设计与用法:
#   导出 RgbdEstimator
#     from_config(config)     工厂方法
#     update_frame(ts, img, dep)  接收帧数据驱动里程计（非阻塞，写入共享槽）
#     get_position_at(ts)     引擎获取指定时刻位置
#     get_position()          获取当前实时位置
#     get_config()            获取当前配置和状态
#     shutdown()              停止 actor 线程
#
#   无需 update_telemetry
#   路由只向此模式推送帧数据
# ============================================================

import base64
import logging
import math
import threading
import time
from bisect import bisect_left
from typing import Optional

import numpy as np

from server.estimation.base import BaseEstimator, Position

logger = logging.getLogger(__name__)


class RgbdEstimator(BaseEstimator):
    """RGB-D 里程计 —— 帧到达后写入共享槽，actor 线程异步处理"""

    def __init__(self, config: dict,
                 initial_x: float = 0.0, initial_y: float = 0.0,
                 initial_heading: float = 0.0,
                 max_history: int = 10000):
        # 相机内参
        depth_cfg = config.get('depth_camera', {})
        self._fx = depth_cfg.get('fx', 0.0)
        self._fy = depth_cfg.get('fy', 0.0)
        self._cx = depth_cfg.get('cx', 0.0)
        self._cy = depth_cfg.get('cy', 0.0)
        self._width = depth_cfg.get('width', 640)
        self._height = depth_cfg.get('height', 480)
        self._depth_scale = config.get('depth', {}).get('depth_scale', 1000)

        self._x = initial_x
        self._y = initial_y
        self._heading = initial_heading
        self._initial_x = initial_x
        self._initial_y = initial_y
        self._initial_heading = initial_heading
        self._last_ts: Optional[float] = None
        self._trajectory: list[Position] = []
        self._max_history = max_history
        self._lock = threading.Lock()

        # Open3D 初始化
        self._o3d_available = False
        self._o3d: Optional[object] = None
        self._intrinsic: Optional[object] = None
        self._option: Optional[object] = None
        self._prev_rgb: Optional[np.ndarray] = None
        self._prev_depth: Optional[np.ndarray] = None
        try:
            import open3d as o3d
            self._o3d = o3d
            self._intrinsic = o3d.camera.PinholeCameraIntrinsic(
                self._width, self._height, self._fx, self._fy, self._cx, self._cy)
            self._option = o3d.pipelines.odometry.OdometryOption()
            self._o3d_available = True
        except ImportError:
            logger.warning("open3d 未安装, RGB-D 里程计不可用")

        # actor
        est_cfg = config.get('estimation', {})
        self._frame_skip = est_cfg.get('odometry_frame_skip', 3)
        self._pending_frame: Optional[tuple] = None
        self._pending_lock = threading.Lock()
        self._actor_running = False
        self._actor_thread: Optional[threading.Thread] = None

        if self._o3d_available:
            self._start_actor()

    # ============================================================
    # 工厂
    # ============================================================

    @classmethod
    def from_config(cls, config: dict) -> 'RgbdEstimator':
        est = config.get('estimation', {})
        return cls(
            config=config,
            initial_x=est.get('initial_x', 0.0),
            initial_y=est.get('initial_y', 0.0),
            initial_heading=est.get('initial_heading', 0.0),
        )

    # ============================================================
    # 数据输入
    # ============================================================

    def update_frame(self, timestamp: float, image: str,
                     depth_map: str) -> None:
        with self._pending_lock:
            self._pending_frame = (image, depth_map, timestamp)

    # ============================================================
    # 位置读取
    # ============================================================

    def get_position_at(self, timestamp: float) -> Position:
        with self._lock:
            if not self._trajectory:
                return Position(timestamp, self._initial_x, self._initial_y, self._initial_heading)
            return self._traj_get_at(timestamp)

    def get_position(self) -> Position:
        with self._lock:
            if not self._trajectory:
                return Position(time.time(), self._initial_x, self._initial_y, self._initial_heading)
            last = self._trajectory[-1]
            return Position(time.time(), last.x, last.y, last.heading)

    # ============================================================
    # 配置
    # ============================================================

    def get_config(self) -> dict:
        return {
            'mode': 'rgbd',
            'odometry_available': self._o3d_available,
            'initial_x': self._initial_x,
            'initial_y': self._initial_y,
            'initial_heading': self._initial_heading,
            'x': self._x,
            'y': self._y,
            'heading': self._heading,
        }

    # ============================================================
    # 生命周期
    # ============================================================

    def shutdown(self) -> None:
        self._actor_running = False
        if self._actor_thread is not None:
            self._actor_thread.join(timeout=3)
            if self._actor_thread.is_alive():
                logger.warning("[Rgbd] actor 未能在 3s 内退出")
            self._actor_thread = None

    # ============================================================
    # Actor（私有）
    # ============================================================

    def _start_actor(self) -> None:
        self._actor_running = True
        self._actor_thread = threading.Thread(
            target=self._actor_loop, daemon=True, name="rgbd-actor")
        self._actor_thread.start()
        logger.warning("[Rgbd] actor 启动, frame_skip=%d", self._frame_skip)

    def _actor_loop(self) -> None:
        frame_count = 0
        error_count = 0
        odometry_count = 0
        last_processed_ts = 0.0

        while self._actor_running:
            with self._pending_lock:
                frame_data = self._pending_frame
                self._pending_frame = None

            if frame_data is None:
                time.sleep(0.05)
                continue

            image_b64, depth_b64, timestamp = frame_data
            if timestamp <= last_processed_ts:
                continue

            frame_count += 1
            if frame_count % self._frame_skip != 0:
                continue

            try:
                result = self._compute_odometry(image_b64, depth_b64)
                if result is None:
                    continue
                dx, dz, dh = result
                odometry_count += 1

                with self._lock:
                    h = math.radians(self._heading)
                    # 相机帧 (X右 Z前) → 车辆帧 (X前 Y左): veh_x=dz, veh_y=-dx
                    # 世界帧: 绕 heading 旋转
                    self._x += dz * math.cos(h) + dx * math.sin(h)
                    self._y += dz * math.sin(h) - dx * math.cos(h)
                    self._heading += dh
                    self._last_ts = timestamp
                    self._traj_append(Position(self._last_ts, self._x, self._y, self._heading))

                last_processed_ts = timestamp
                error_count = 0

            except Exception:
                error_count += 1
                logger.exception("[Rgbd] actor 里程计失败 (连续 %d)", error_count)
                if error_count >= 10:
                    logger.error("[Rgbd] 连续 10 次失败，actor 退出")
                    self._actor_running = False

        logger.warning("[Rgbd] actor 退出, 帧=%d 里程计=%d", frame_count, odometry_count)

    # ============================================================
    # 视觉里程计（自包含 Open3D + 解码）
    # ============================================================

    def _compute_odometry(self, image_b64: str, depth_b64: str
                          ) -> Optional[tuple[float, float, float]]:
        rgb = self._decode_jpeg(image_b64)
        depth = self._decode_depth(depth_b64)
        if rgb is None or depth is None:
            return None

        if self._prev_rgb is None:
            self._prev_rgb = rgb
            self._prev_depth = depth
            logger.warning("[Rgbd] 首帧已存储, %dx%d", rgb.shape[1], rgb.shape[0])
            return None

        try:
            rgbd1 = self._o3d.geometry.RGBDImage.create_from_color_and_depth(
                self._o3d.geometry.Image(self._prev_rgb),
                self._o3d.geometry.Image(self._prev_depth),
                depth_scale=self._depth_scale, convert_rgb_to_intensity=False)
            rgbd2 = self._o3d.geometry.RGBDImage.create_from_color_and_depth(
                self._o3d.geometry.Image(rgb),
                self._o3d.geometry.Image(depth),
                depth_scale=self._depth_scale, convert_rgb_to_intensity=False)

            success, T, _ = self._o3d.pipelines.odometry.compute_rgbd_odometry(
                rgbd1, rgbd2, self._intrinsic,
                odo_init=np.eye(4),
                jacobian=self._o3d.pipelines.odometry.RGBDOdometryJacobianFromHybridTerm(),
                option=self._option)

            self._prev_rgb = rgb
            self._prev_depth = depth

            if not success:
                return None

            dx = float(T[0, 3])
            dz = float(T[2, 3])
            dheading = -math.degrees(math.atan2(T[2, 0], T[2, 2]))
            return dx, dz, dheading
        except Exception:
            logger.exception("RGB-D odometry 计算失败")
            return None

    @staticmethod
    def _decode_jpeg(b64: str) -> Optional[np.ndarray]:
        try:
            import cv2
            data = base64.b64decode(b64)
            arr = np.frombuffer(data, dtype=np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception:
            return None

    @staticmethod
    def _decode_depth(b64: str, min_m: float = 0.6, max_m: float = 8.0
                      ) -> Optional[np.ndarray]:
        try:
            import cv2
            data = base64.b64decode(b64)
            arr = np.frombuffer(data, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
            if img is None:
                return None
            depth_m = img.astype(np.float32) / 1000.0
            depth_m[(depth_m < min_m) | (depth_m > max_m)] = 0.0
            return depth_m * 1000.0
        except Exception:
            return None

    # ============================================================
    # 轨迹工具（私有）
    # ============================================================

    def _traj_append(self, pos: Position) -> None:
        self._trajectory.append(pos)
        if len(self._trajectory) > self._max_history:
            self._trajectory.pop(0)

    def _traj_get_at(self, timestamp: float) -> Position:
        ts_list = [p.timestamp for p in self._trajectory]
        idx = bisect_left(ts_list, timestamp)
        if idx >= len(self._trajectory):
            return self._trajectory[-1]
        if idx == 0:
            return self._trajectory[0]
        p0, p1 = self._trajectory[idx - 1], self._trajectory[idx]
        dt = p1.timestamp - p0.timestamp
        if dt < 1e-9:
            return p0
        t = (timestamp - p0.timestamp) / dt
        return Position(
            timestamp,
            p0.x + (p1.x - p0.x) * t,
            p0.y + (p1.y - p0.y) * t,
            p0.heading + (p1.heading - p0.heading) * t,
        )
