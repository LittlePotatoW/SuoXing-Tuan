# ============================================================
# backend/server/estimation/manager.py
# 位置估计器管理器 —— 路由类，统一管理四个模式类的创建、切换、数据路由和销毁
#
# 设计与用法:
#   导出 EstimatorManager
#     create(mode, overrides)         工厂创建 + 切换（先 stop 旧的）
#     stop()                          停止当前估计器
#     get_position_at(ts)             引擎获取指定时刻位置（透传）
#     get_position()                  获取当前实时位置（透传）
#     get_config()                    获取当前配置（透传）
#     handle_telemetry(ts, spd, steer) 按模式转发遥测（bicycle/fusion）
#     handle_frame(ts, img, dep)       按模式转发帧（rgbd/fusion）
# ============================================================

import threading
from typing import Optional

from server.estimation.base import BaseEstimator, Position
from server.estimation.bicycle_estimator import BicycleEstimator
from server.estimation.constant_estimator import ConstantEstimator
from server.estimation.rgbd_estimator import RgbdEstimator
from server.estimation.fusion_estimator import FusionEstimator


class EstimatorManager:
    """统一管理四个模式类的生命周期和数据路由"""

    def __init__(self):
        self._estimator: Optional[BaseEstimator] = None
        self._mode: str = ''
        self._lock = threading.RLock()

    # ============================================================
    # 引擎接口（透传）
    # ============================================================

    def get_position_at(self, timestamp: float) -> Position:
        return self._get_est().get_position_at(timestamp)

    # ============================================================
    # 前端接口（透传）
    # ============================================================

    def get_position(self) -> Position:
        return self._get_est().get_position()

    def get_config(self) -> dict:
        return self._get_est().get_config()

    # ============================================================
    # 数据路由（模式感知）
    # ============================================================

    def handle_telemetry(self, timestamp: float, speed: float,
                         steering_angle: float) -> None:
        """bicycle / fusion → 转发；constant / rgbd → 忽略"""
        if self._mode in ('bicycle', 'fusion'):
            self._get_est().update_telemetry(timestamp, speed, steering_angle)

    def handle_frame(self, timestamp: float, image: str,
                     depth_map: str) -> None:
        """rgbd / fusion → 转发；bicycle / constant → 忽略"""
        if self._mode in ('rgbd', 'fusion'):
            self._get_est().update_frame(timestamp, image, depth_map)

    # ============================================================
    # 生命周期
    # ============================================================

    def create(self, mode: str, overrides: Optional[dict] = None) -> None:
        """工厂创建 + 覆写参数 + stop 旧的"""
        from server.config import get_config
        config = get_config()

        if mode == 'bicycle':
            est = BicycleEstimator.from_config(config)
        elif mode == 'constant':
            est = ConstantEstimator.from_config(config)
        elif mode == 'rgbd':
            est = RgbdEstimator.from_config(config)
        elif mode == 'fusion':
            est = FusionEstimator.from_config(config)
        else:
            raise ValueError(f"未知估计模式: {mode}")

        if overrides:
            self._apply_overrides(est, overrides)

        with self._lock:
            if self._estimator is not None:
                self._estimator.shutdown()
            self._estimator = est
            self._mode = mode

    def stop(self) -> None:
        with self._lock:
            if self._estimator is not None:
                self._estimator.shutdown()
                self._estimator = None
            self._mode = ''

    # ============================================================
    # 内部
    # ============================================================

    def _get_est(self) -> BaseEstimator:
        """懒初始化：首次调用时用默认模式创建"""
        if self._estimator is None:
            with self._lock:
                if self._estimator is None:
                    from server.config import get_config
                    cfg = get_config()
                    mode = cfg.get('estimation', {}).get('mode', 'bicycle')
                    self.create(mode)
        return self._estimator  # type: ignore[return-value]

    @staticmethod
    def _apply_overrides(est, overrides: dict) -> None:
        if overrides.get('wheelbase') is not None and hasattr(est, '_wheelbase'):
            est._wheelbase = overrides['wheelbase']
        if overrides.get('constant_speed') is not None and hasattr(est, '_speed'):
            est._speed = overrides['constant_speed']
        if overrides.get('fusion_weight') is not None and hasattr(est, '_fusion_weight'):
            est._fusion_weight = overrides['fusion_weight']
        if overrides.get('initial_x') is not None:
            if hasattr(est, '_initial_x'):
                est._initial_x = overrides['initial_x']
            if hasattr(est, '_x'):
                est._x = overrides['initial_x']
        if overrides.get('initial_y') is not None:
            if hasattr(est, '_initial_y'):
                est._initial_y = overrides['initial_y']
            if hasattr(est, '_y'):
                est._y = overrides['initial_y']
        if overrides.get('initial_heading') is not None:
            if hasattr(est, '_initial_heading'):
                est._initial_heading = overrides['initial_heading']
            if hasattr(est, '_heading'):
                est._heading = overrides['initial_heading']
