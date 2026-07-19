# ============================================================
# backend/server/estimation/bicycle.py
# 位置估计策略: 自行车模型 (模式1)
#
# 设计与用法:
#   导出 BicycleStrategy 类
#   导出 update(speed, steering, heading, wheelbase, delta_t) → (new_x, new_y, new_heading)
# ============================================================

import math


class BicycleStrategy:
    """自行车模型：speed + steering_angle → 位移"""

    def __init__(self, wheelbase: float = 2.0):
        self._wheelbase = wheelbase

    def update(self, speed: float, steering_angle: float,
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
