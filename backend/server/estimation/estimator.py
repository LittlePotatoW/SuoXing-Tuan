# ============================================================
# backend/server/estimation/estimator.py
# 位置估计器核心类（单例）：根据速度、转向和时间戳推算小车位置
#
# 设计与用法:
#   导出 PositionEstimator 类
#   导出 create() / stop() 工厂方法
#   导出 update_telemetry() / get_position() / get_position_at() 方法
#   导出 Position namedtuple
# ============================================================
#   _instance        单例实例
#   _lock            线程锁
#   _trajectory      轨迹列表 [(timestamp, x, y, heading), ...]
# ============================================================

import math
import threading
from bisect import bisect_left
from collections import namedtuple
import logging

logger = logging.getLogger(__name__)

Position = namedtuple('Position', ['timestamp', 'x', 'y', 'heading'])

_instance = None
_lock = threading.Lock()


class PositionEstimator:
    """位置估计器（单例），自行车模型航位推算"""

    def __init__(self, config: dict):
        est = config.get('estimation', {})
        self._initial_x = est.get('initial_x', 0.0)
        self._initial_y = est.get('initial_y', 0.0)
        self._initial_heading = est.get('initial_heading', 0.0)
        self._wheelbase = est.get('wheelbase', 2.0)
        self._max_history = est.get('max_history', 10000)

        self._last_ts: float | None = None
        self._x: float = self._initial_x
        self._y: float = self._initial_y
        self._heading: float = self._initial_heading  # 度
        self._trajectory: list[Position] = []
        self._rwlock = threading.Lock()

    # ============================================================
    # 工厂方法
    # ============================================================

    @classmethod
    def create(cls, config: dict | None = None) -> 'PositionEstimator':
        """获取或创建单例实例"""
        global _instance
        with _lock:
            if _instance is None:
                if config is None:
                    from server.config import get_config
                    config = get_config()
                _instance = cls(config)
            return _instance

    @classmethod
    def stop(cls) -> None:
        """清空轨迹数据，释放单例"""
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
        """接收一条遥测数据，积分更新位置

        Args:
            timestamp: Unix 时间戳（秒）
            speed: 当前速度 (m/s)
            steering_angle: 当前车轮转角（度），正=左转
        """
        if speed < 0:
            logger.warning("speed 不能为负值, 已置为 0: %s", speed)
            speed = 0.0

        with self._rwlock:
            if self._last_ts is not None and timestamp <= self._last_ts:
                logger.warning("时间戳回退: %.3f <= %.3f, 丢弃数据",
                               timestamp, self._last_ts)
                return

            if self._last_ts is None:
                self._last_ts = timestamp
                return

            delta_t = timestamp - self._last_ts
            self._last_ts = timestamp

            if speed == 0.0:
                return

            # 自行车模型
            steering_rad = math.radians(steering_angle)
            if abs(steering_rad) < 1e-6:
                omega = 0.0
            else:
                turn_radius = self._wheelbase / math.tan(steering_rad)
                omega = speed / turn_radius

            heading_rad = math.radians(self._heading)
            self._heading += math.degrees(omega * delta_t)
            self._x += speed * math.cos(heading_rad) * delta_t
            self._y += speed * math.sin(heading_rad) * delta_t

            self._trajectory.append(
                Position(timestamp, self._x, self._y, self._heading)
            )
            if len(self._trajectory) > self._max_history:
                self._trajectory.pop(0)

    # ============================================================
    # 位置读取
    # ============================================================

    def get_position(self) -> Position:
        """返回最新位置。无数据时返回原点"""
        with self._rwlock:
            if not self._trajectory:
                return Position(0.0, self._initial_x, self._initial_y,
                                self._initial_heading)
            return self._trajectory[-1]

    def get_position_at(self, timestamp: float) -> Position:
        """在轨迹中插值，返回指定时刻的位置

        用于重建引擎为每帧点云获取精确的采集位置。
        无数据时返回原点，timestamp 超出范围时返回最近点。
        """
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

            p0 = self._trajectory[idx - 1]
            p1 = self._trajectory[idx]
            dt = p1.timestamp - p0.timestamp
            if dt < 1e-9:
                return p0

            t = (timestamp - p0.timestamp) / dt
            return Position(
                timestamp=timestamp,
                x=p0.x + (p1.x - p0.x) * t,
                y=p0.y + (p1.y - p0.y) * t,
                heading=p0.heading + (p1.heading - p0.heading) * t,
            )
