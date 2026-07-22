# ============================================================
# backend/server/estimation/constant_estimator.py
# 匀速直线估计器 —— 完全自治，不依赖任何外部数据
#
# 设计与用法:
#   导出 ConstantEstimator
#     from_config(config)  工厂方法
#     get_position_at(ts)  引擎获取指定时刻位置
#     get_position()       前端获取当前位置
#     get_config()         前端读取配置
#
#   无需 update_telemetry / update_frame
#   路由不会向此模式推送任何数据
# ============================================================

import logging
import math
import threading
import time

from server.estimation.base import BaseEstimator, Position

logger = logging.getLogger(__name__)


class ConstantEstimator(BaseEstimator):
    """匀速直线 —— 构造时即开始计时，之后所有位置查询均为纯数学计算"""

    def __init__(self, constant_speed: float = 1.0,
                 initial_x: float = 0.0, initial_y: float = 0.0,
                 initial_heading: float = 0.0):
        self._speed = constant_speed
        self._x = initial_x
        self._y = initial_y
        self._heading = initial_heading
        self._initial_x = initial_x
        self._initial_y = initial_y
        self._initial_heading = initial_heading
        self._start_ts = time.time()
        self._lock = threading.Lock()
        logger.warning("[Constant] 初始化 start_ts=%.3f speed=%.2f heading=%.1f°",
                       self._start_ts, self._speed, self._heading)

    # ============================================================
    # 工厂
    # ============================================================

    @classmethod
    def from_config(cls, config: dict) -> 'ConstantEstimator':
        est = config.get('estimation', {})
        return cls(
            constant_speed=est.get('constant_speed', 1.0),
            initial_x=est.get('initial_x', 0.0),
            initial_y=est.get('initial_y', 0.0),
            initial_heading=est.get('initial_heading', 0.0),
        )

    # ============================================================
    # 位置读取（纯计算，不依赖轨迹或外部数据）
    # ============================================================

    def get_position_at(self, timestamp: float) -> Position:
        with self._lock:
            # 回放模式：帧时间戳远早于构造时间 → 自动校准 start_ts
            if timestamp < self._start_ts - 10:
                self._start_ts = timestamp
            dt = timestamp - self._start_ts
            if dt <= 0:
                return Position(timestamp, self._initial_x,
                                self._initial_y, self._initial_heading)
            h = math.radians(self._initial_heading)
            nx = self._initial_x + self._speed * math.cos(h) * dt
            ny = self._initial_y + self._speed * math.sin(h) * dt
            return Position(timestamp, nx, ny, self._initial_heading)

    def get_position(self) -> Position:
        return self.get_position_at(time.time())

    # ============================================================
    # 配置
    # ============================================================

    def get_config(self) -> dict:
        return {
            'mode': 'constant',
            'constant_speed': self._speed,
            'initial_x': self._initial_x,
            'initial_y': self._initial_y,
            'initial_heading': self._initial_heading,
            'x': self._x,
            'y': self._y,
            'heading': self._heading,
        }
