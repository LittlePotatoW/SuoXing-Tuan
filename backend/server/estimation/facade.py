# ============================================================
# backend/server/estimation/facade.py
# 位置估计器 facade: 根据 config.estimation.mode 选择策略
#
# 设计与用法:
#   导出 PositionEstimator 类 (单例)
#   导出 create(mode, config) / stop()
#   导出 update_telemetry() / update_frame()
#   导出 get_position() / get_position_at() / get_config()
#   导出 Position namedtuple
# ============================================================
#   支持 4 种模式: bicycle / constant / rgbd / fusion
# ============================================================

import logging
import math
import threading
from bisect import bisect_left
from collections import namedtuple

from server.estimation.bicycle import BicycleStrategy
from server.estimation.constant import ConstantStrategy
from server.estimation.rgbd_odometry import RgbdOdometryStrategy
from server.estimation.fusion import FusionStrategy

logger = logging.getLogger(__name__)

Position = namedtuple('Position', ['timestamp', 'x', 'y', 'heading'])

_instance = None
_lock = threading.Lock()


class PositionEstimator:
    """位置估计器（单例），根据 mode 使用不同策略"""

    def __init__(self, config: dict, mode: str | None = None):
        est = config.get('estimation', {})
        self._mode = mode or est.get('mode', 'bicycle')
        self._wheelbase = est.get('wheelbase', 2.0)
        self._constant_speed = est.get('constant_speed', 1.0)

        self._initial_x = est.get('initial_x', 0.0)
        self._initial_y = est.get('initial_y', 0.0)
        self._initial_heading = est.get('initial_heading', 0.0)
        self._max_history = est.get('max_history', 10000)

        self._last_ts: float | None = None
        self._x = self._initial_x
        self._y = self._initial_y
        self._heading = self._initial_heading
        self._trajectory: list[Position] = []
        self._rwlock = threading.Lock()

        # 策略实例
        wheelbase = est.get('wheelbase', 2.0)
        self._bicycle = BicycleStrategy(wheelbase)
        self._constant = ConstantStrategy()
        self._rgbd = RgbdOdometryStrategy(config)
        self._fusion = FusionStrategy(config)

        logger.info("位置估计器模式: %s", self._mode)

    # ============================================================
    # 工厂方法
    # ============================================================

    @classmethod
    def create(cls, mode: str | None = None,
               config: dict | None = None) -> 'PositionEstimator':
        global _instance
        with _lock:
            if _instance is None:
                if config is None:
                    from server.config import get_config
                    config = get_config()
                _instance = cls(config, mode=mode)
            return _instance

    @classmethod
    def stop(cls) -> None:
        global _instance
        with _lock:
            if _instance is not None:
                with _instance._rwlock:
                    _instance._trajectory.clear()
                    _instance._last_ts = None
                    _instance._x = _instance._initial_x
                    _instance._y = _instance._initial_y
                    _instance._heading = _instance._initial_heading
            _instance = None

    # ============================================================
    # 数据写入
    # ============================================================

    def update_telemetry(self, timestamp: float,
                         speed: float,
                         steering_angle: float) -> None:
        if speed < 0:
            speed = 0.0

        with self._rwlock:
            if self._last_ts is not None and timestamp <= self._last_ts:
                logger.warning("时间戳回退, 丢弃")
                return
            if self._last_ts is None:
                self._last_ts = timestamp
                return

            delta_t = timestamp - self._last_ts
            self._last_ts = timestamp

            if self._mode == 'constant':
                speed = self._constant_speed
                steering_angle = 0.0

            if self._mode in ('bicycle', 'constant'):
                self._x, self._y, self._heading = self._bicycle.update(
                    speed, steering_angle,
                    self._x, self._y, self._heading, delta_t)

            elif self._mode == 'fusion':
                self._x, self._y, self._heading, _ = self._fusion.predict(
                    speed, steering_angle,
                    self._x, self._y, self._heading, delta_t)

            self._append()

    def update_frame(self, timestamp: float,
                     image: str, depth_map: str) -> None:
        """RGB-D 帧数据入口 (模式3/4)"""
        with self._rwlock:
            if self._mode == 'rgbd':
                self._last_ts = timestamp
                delta = self._rgbd.update_frame(image, depth_map)
                if delta:
                    dx, dz, dh = delta
                    heading_rad = math.radians(self._heading)
                    # dx=相机右(X), dz=相机前(Z)。旋转到世界: 右=(-sin,cos), 前=(cos,sin)
                    self._x += -dx * math.sin(heading_rad) + dz * math.cos(heading_rad)
                    self._y +=  dx * math.cos(heading_rad) + dz * math.sin(heading_rad)
                    self._heading += dh
                    self._append()

            elif self._mode == 'fusion':
                result = self._fusion.update_visual(
                    image, depth_map, self._x, self._y, self._heading)
                if result:
                    self._x, self._y, self._heading = result
                    self._append()

    # ============================================================
    # 位置读取
    # ============================================================

    def get_position(self) -> Position:
        with self._rwlock:
            if not self._trajectory:
                return Position(0.0, self._initial_x, self._initial_y,
                                self._initial_heading)
            return self._trajectory[-1]

    def get_position_at(self, timestamp: float) -> Position:
        with self._rwlock:
            if not self._trajectory:
                return Position(0.0, self._initial_x, self._initial_y,
                                self._initial_heading)
            timestamps = [p.timestamp for p in self._trajectory]
            idx = bisect_left(timestamps, timestamp)
            if idx == 0:
                return self._trajectory[0]
            if idx >= len(self._trajectory):
                return self._trajectory[-1]
            p0, p1 = self._trajectory[idx - 1], self._trajectory[idx]
            dt = p1.timestamp - p0.timestamp
            if dt < 1e-9:
                return p0
            t = (timestamp - p0.timestamp) / dt
            return Position(
                timestamp, p0.x + (p1.x - p0.x) * t,
                p0.y + (p1.y - p0.y) * t,
                p0.heading + (p1.heading - p0.heading) * t)

    def get_config(self) -> dict:
        return {
            'mode': self._mode,
            'wheelbase': self._wheelbase,
            'constant_speed': self._constant_speed,
            'initial_x': self._initial_x,
            'initial_y': self._initial_y,
            'initial_heading': self._initial_heading,
            'x': self._x,
            'y': self._y,
            'heading': self._heading,
        }

    # ============================================================
    # 内部
    # ============================================================

    def _append(self):
        self._trajectory.append(
            Position(self._last_ts, self._x, self._y, self._heading))
        if len(self._trajectory) > self._max_history:
            self._trajectory.pop(0)
