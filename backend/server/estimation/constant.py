# ============================================================
# backend/server/estimation/constant.py
# 位置估计策略: 匀速直线 (模式2)
#
# 设计与用法:
#   导出 ConstantStrategy 类
#   忽略 steering, 只取 speed, 纯直线前进
# ============================================================

import math


class ConstantStrategy:
    """匀速直线：忽略转向，x += speed * dt"""

    def update(self, speed: float, _steering: float,
               x: float, y: float, heading: float,
               delta_t: float) -> tuple[float, float, float]:
        if speed == 0.0:
            return x, y, heading

        heading_rad = math.radians(heading)
        new_x = x + speed * math.cos(heading_rad) * delta_t
        new_y = y + speed * math.sin(heading_rad) * delta_t
        return new_x, new_y, heading
