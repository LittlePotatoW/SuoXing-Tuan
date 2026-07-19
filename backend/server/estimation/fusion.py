# ============================================================
# backend/server/estimation/fusion.py
# 位置估计策略: EKF 融合 (模式4)
#
# 设计与用法:
#   导出 FusionStrategy 类
#   自行车模型做预测 + RGB-D 里程计做观测 → EKF 融合
# ============================================================

import logging

import numpy as np

from server.estimation.bicycle import BicycleStrategy
from server.estimation.rgbd_odometry import RgbdOdometryStrategy

logger = logging.getLogger(__name__)

# 状态: [x, y, heading]  3 维
STATE_DIM = 3


class FusionStrategy:
    """EKF 融合: 自行车模型预测 + 视觉里程计观测"""

    def __init__(self, config: dict):
        est_cfg = config.get('estimation', {})
        wheelbase = est_cfg.get('wheelbase', 2.0)
        self._weight = est_cfg.get('fusion_weight', 0.5)

        self._bicycle = BicycleStrategy(wheelbase)
        self._visual = RgbdOdometryStrategy(config)

        # 状态协方差
        self._P = np.eye(STATE_DIM) * 0.1
        # 过程噪声
        self._Q = np.diag([0.1, 0.1, 0.05])
        # 观测噪声
        self._R = np.diag([0.05, 0.05, 0.02])

    @property
    def visual_available(self) -> bool:
        return self._visual.available

    def predict(self, speed: float, steering: float,
                x: float, y: float, heading: float,
                delta_t: float) -> tuple[float, float, float, np.ndarray]:
        """自行车模型预测: 返回 (x, y, heading, P)"""
        nx, ny, nh = self._bicycle.update(
            speed, steering, x, y, heading, delta_t)

        # 雅可比（简化为单位阵）
        F = np.eye(STATE_DIM)
        self._P = F @ self._P @ F.T + self._Q * delta_t

        return nx, ny, nh, self._P

    def update_visual(self, image_b64: str, depth_b64: str,
                      x: float, y: float, heading: float
                      ) -> tuple[float, float, float] | None:
        """视觉观测 → EKF 校正"""
        delta = self._visual.update_frame(image_b64, depth_b64)
        if delta is None:
            return None

        dx, dz, dh = delta
        # 观测值 = 当前状态 + 视觉增量
        z = np.array([x + dx, y + dz, heading + dh])

        # EKF 校正
        H = np.eye(STATE_DIM)
        y_res = z - np.array([x, y, heading])
        S = H @ self._P @ H.T + self._R
        K = self._P @ H.T @ np.linalg.inv(S)
        state = np.array([x, y, heading]) + K @ y_res
        self._P = (np.eye(STATE_DIM) - K @ H) @ self._P

        return float(state[0]), float(state[1]), float(state[2])

    def weighted_fallback(self, speed: float, steering: float,
                          x: float, y: float, heading: float,
                          delta_t: float) -> tuple[float, float, float]:
        """无视觉观测时，纯自行车模型"""
        return self._bicycle.update(speed, steering, x, y, heading, delta_t)
