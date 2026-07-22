# ============================================================
# backend/server/estimation/fusion_estimator.py
# EKF 融合估计器 —— 遥测预测 + RGB-D 修正 + actor 线程，完全自包含
#
# 设计与用法:
#   导出 FusionEstimator
#     from_config(config)         工厂方法
#     update_telemetry(ts, spd, steer)  遥测 → EKF 预测步（同步、轻量）
#     update_frame(ts, img, dep)        帧 → 写入槽 → actor 消费 → EKF 修正
#     get_position_at(ts)         引擎获取指定时刻位置
#     get_position()              获取当前实时位置
#     get_config()                获取当前配置和状态
#     shutdown()                  停止 actor 线程
#
#   路由同时向此模式推送遥测和帧数据
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

STATE_DIM = 3


class FusionEstimator(BaseEstimator):
    """EKF 融合 —— 遥测做预测，actor 中做 RGB-D 里程计修正"""

    def __init__(self, config: dict,
                 initial_x: float = 0.0, initial_y: float = 0.0,
                 initial_heading: float = 0.0,
                 max_history: int = 10000):
        est_cfg = config.get('estimation', {})
        self._wheelbase = est_cfg.get('wheelbase', 2.0)
        self._fusion_weight = est_cfg.get('fusion_weight', 0.5)

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

        # EKF 状态
        self._P = np.eye(STATE_DIM) * 0.1
        self._Q = np.diag([0.1, 0.1, 0.05])
        self._R = np.diag([0.05, 0.05, 0.02])

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
            logger.warning("open3d 未安装, 视觉里程计不可用")

        # actor
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
    def from_config(cls, config: dict) -> 'FusionEstimator':
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

    def update_telemetry(self, timestamp: float, speed: float,
                         steering_angle: float) -> None:
        """EKF 预测步（同步、轻量）"""
        if speed < 0:
            speed = 0.0
        with self._lock:
            if self._last_ts is not None and timestamp <= self._last_ts:
                return
            if self._last_ts is None:
                self._last_ts = timestamp
                self._traj_append(Position(self._last_ts, self._x, self._y, self._heading))
                logger.warning("[Fusion] 首条遥测 ts=%.3f", timestamp)
                return

            delta_t = timestamp - self._last_ts
            self._last_ts = timestamp

            # 自行车模型预测
            nx, ny, nh = self._bicycle_step(
                speed, steering_angle, self._x, self._y, self._heading, delta_t)
            # EKF 协方差传播
            F = np.eye(STATE_DIM)
            self._P = F @ self._P @ F.T + self._Q * delta_t

            self._x, self._y, self._heading = nx, ny, nh
            self._traj_append(Position(self._last_ts, self._x, self._y, self._heading))

    def update_frame(self, timestamp: float, image: str,
                     depth_map: str) -> None:
        """写入共享槽供 actor 消费"""
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
            'mode': 'fusion',
            'wheelbase': self._wheelbase,
            'fusion_weight': self._fusion_weight,
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
                logger.warning("[Fusion] actor 未能在 3s 内退出")
            self._actor_thread = None

    # ============================================================
    # 自行车运动学（自包含）
    # ============================================================

    def _bicycle_step(self, speed: float, steering_angle: float,
                      x: float, y: float, heading: float,
                      delta_t: float) -> tuple[float, float, float]:
        if speed == 0.0:
            return x, y, heading
        steering_rad = math.radians(steering_angle)
        if abs(steering_rad) < 1e-6:
            omega = 0.0
        else:
            turn_radius = self._wheelbase / math.tan(steering_rad)
            omega = speed / turn_radius
        heading_rad = math.radians(heading)
        new_heading = heading + math.degrees(omega * delta_t)
        new_x = x + speed * math.cos(heading_rad) * delta_t
        new_y = y + speed * math.sin(heading_rad) * delta_t
        return new_x, new_y, new_heading

    # ============================================================
    # Actor（私有）
    # ============================================================

    def _start_actor(self) -> None:
        self._actor_running = True
        self._actor_thread = threading.Thread(
            target=self._actor_loop, daemon=True, name="fusion-actor")
        self._actor_thread.start()
        logger.warning("[Fusion] actor 启动, frame_skip=%d", self._frame_skip)

    def _actor_loop(self) -> None:
        frame_count = 0
        error_count = 0
        correction_count = 0

        while self._actor_running:
            with self._pending_lock:
                frame_data = self._pending_frame
                self._pending_frame = None

            if frame_data is None:
                time.sleep(0.05)
                continue

            image_b64, depth_b64, timestamp = frame_data
            frame_count += 1
            if frame_count % self._frame_skip != 0:
                continue

            try:
                delta = self._compute_odometry(image_b64, depth_b64)
                if delta is None:
                    continue

                dx, dz, dh = delta
                with self._lock:
                    # EKF 修正: 相机帧→车辆帧→世界帧
                    h = math.radians(self._heading)
                    obs_x = self._x + dz * math.cos(h) + dx * math.sin(h)
                    obs_y = self._y + dz * math.sin(h) - dx * math.cos(h)
                    z = np.array([obs_x, obs_y, self._heading + dh])
                    H = np.eye(STATE_DIM)
                    y_res = z - np.array([self._x, self._y, self._heading])
                    S = H @ self._P @ H.T + self._R
                    K = self._P @ H.T @ np.linalg.inv(S)
                    state = np.array([self._x, self._y, self._heading]) + K @ y_res
                    self._P = (np.eye(STATE_DIM) - K @ H) @ self._P
                    self._x, self._y, self._heading = float(state[0]), float(state[1]), float(state[2])
                    self._last_ts = timestamp
                    self._traj_append(Position(self._last_ts, self._x, self._y, self._heading))

                correction_count += 1
                error_count = 0

            except Exception:
                error_count += 1
                logger.exception("[Fusion] actor EKF 修正失败 (连续 %d)", error_count)
                if error_count >= 10:
                    logger.error("[Fusion] 连续 10 次失败，actor 退出")
                    self._actor_running = False

        logger.warning("[Fusion] actor 退出, 帧=%d 修正=%d", frame_count, correction_count)

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
            logger.warning("[Fusion] 首帧已存储, %dx%d", rgb.shape[1], rgb.shape[0])
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
            logger.exception("[Fusion] RGB-D odometry 计算失败")
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
