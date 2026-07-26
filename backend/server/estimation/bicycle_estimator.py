# ============================================================
# backend/server/estimation/bicycle_estimator.py
# 自行车模型估计器 —— 遥测驱动，完全自包含
#
# 设计与用法:
#   导出 BicycleEstimator
#     from_config(config)         工厂方法
#     update_telemetry(ts, spd, steer)  接收遥测数据驱动位置更新
#     get_position_at(ts)         引擎获取指定时刻位置
#     get_position()              获取当前实时位置
#     get_config()                获取当前配置和状态
#
#   无需 update_frame
#   路由只向此模式推送遥测数据
# ============================================================

import logging
import math
import threading
import time
from bisect import bisect_left
from typing import Optional

from server.estimation.base import BaseEstimator, Position

logger = logging.getLogger(__name__)


class BicycleEstimator(BaseEstimator):
    """自行车模型 —— 遥测到达时根据速度/转角/时间差更新位置"""

    def __init__(self, wheelbase: float = 2.0,
                 initial_x: float = 0.0, initial_y: float = 0.0,
                 initial_heading: float = 0.0,
                 max_history: int = 10000):
        self._wheelbase = wheelbase
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

    # ============================================================
    # 工厂
    # ============================================================

    @classmethod
    def from_config(cls, config: dict) -> 'BicycleEstimator':
        est = config.get('estimation', {})
        return cls(
            wheelbase=est.get('wheelbase', 2.0),
            initial_x=est.get('initial_x', 0.0),
            initial_y=est.get('initial_y', 0.0),
            initial_heading=est.get('initial_heading', 0.0),
        )

    # ============================================================
    # 数据输入
    # ============================================================

    def update_telemetry(self, timestamp: float, speed: float,
                         steering_angle: float) -> None:
        if speed < 0:
            speed = 0.0
        with self._lock:
            if self._last_ts is not None and timestamp <= self._last_ts:
                return
            if self._last_ts is None:
                self._last_ts = timestamp
                self._traj_append(Position(self._last_ts, self._x, self._y, self._heading))
                logger.warning("[Bicycle] 首条遥测 ts=%.3f", timestamp)
                return

            delta_t = timestamp - self._last_ts
            self._last_ts = timestamp
            self._x, self._y, self._heading = self._bicycle_step(
                speed, steering_angle, self._x, self._y, self._heading, delta_t)
            self._traj_append(Position(self._last_ts, self._x, self._y, self._heading))

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
            'mode': 'bicycle',
            'wheelbase': self._wheelbase,
            'initial_x': self._initial_x,
            'initial_y': self._initial_y,
            'initial_heading': self._initial_heading,
            'x': self._x,
            'y': self._y,
            'heading': self._heading,
        }

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
