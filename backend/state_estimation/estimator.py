# ============================================================
# backend/state_estimation/estimator.py
# 小车状态估计器 — 根据运动学参数持续估算小车位置
#
# 模型: 自行车模型 (Bicycle Model)
#   dx/dt = v * cos(θ)
#   dy/dt = v * sin(θ)
#   dθ/dt = v * tan(δ) / L
#   v=速度, θ=航向角, δ=转向角, L=轴距
#
# 用法:
#   estimator = StateEstimator(wheel_base=1.5)
#   state = estimator.update_kinematics(velocity=0.5, steering_angle=0.0, timestamp_ns=...)
#   state = estimator.get_position(timestamp_ns=...)
# ============================================================

# ============================================================
#  ⚙️ 可调参数
# ============================================================

# 最大合理加速度 (m/s²)。超过此值视为传感器异常，钳制。
MAX_ACCEL = 5.0

# 最大合理减速度 (m/s²)
MAX_DECEL = 8.0

# 中值滤波窗口大小 (必须是奇数)
MEDIAN_WINDOW = 5

# 速度突然归零的阈值: v_prev > 此值 且 v_new == 0 → 判定为传输错误
MIN_SPEED_FOR_ZERO_CHECK = 0.1    # m/s

# 最大转向角 (rad)
MAX_STEERING = 0.8    # ~45°

# ============================================================
#  代码
# ============================================================

import bisect
from collections import deque
from dataclasses import dataclass
import logging
import math

logger = logging.getLogger("state_estimation.estimator")


@dataclass
class CarState:
    """小车在某一时刻的状态"""
    timestamp_ns: int      # 时间戳 (纳秒)
    x: float = 0.0         # 世界坐标 X (m)
    y: float = 0.0         # 世界坐标 Y (m)
    z: float = 0.0         # 世界坐标 Z (m)
    yaw: float = 0.0       # 航向角 (rad)
    velocity: float = 0.0  # 当前速度 (m/s)
    steering: float = 0.0  # 当前转向角 (rad)


class StateEstimator:
    """
    小车状态估计器。

    输入: 运动学参数 (速度, 转向角, 时间戳)  — 可以有噪声、有突变
    输出: 平滑后的小车位置轨迹

    鲁棒性:
      - 加速度钳制: 超过物理极限的值被限制
      - 中值滤波: 平滑速度/转向角的随机噪声
      - 零速检测: 识别传输错误导致的异常归零
      - 自行车模型积分: 根据运动学推算位置变化
    """

    def __init__(self, wheel_base: float = 1.5):
        """
        参数:
          wheel_base: 小车轴距 (米)
        """
        self.wheel_base = wheel_base

        # 当前状态
        self._state = CarState(timestamp_ns=0, x=0, y=0, z=0, yaw=0)

        # 中值滤波窗口
        self._vel_window: deque[float] = deque(maxlen=MEDIAN_WINDOW)
        self._steer_window: deque[float] = deque(maxlen=MEDIAN_WINDOW)

        # 上一条有效值 (用于检测跳变)
        self._last_valid_vel: float = 0.0
        self._last_vel: float = 0.0
        self._last_timestamp_ns: int = 0

        # 历史轨迹 (用于查询任意时刻的位置)，限制大小防止内存泄漏
        self._history: list[CarState] = []
        self._history_max: int = 10_000

        # 统计
        self._update_count: int = 0
        self._rejected_count: int = 0

    # ================================================================
    #  对外接口
    # ================================================================

    def update_kinematics(
        self, velocity: float, steering_angle: float, timestamp_ns: int,
        wheel_base: float | None = None,
    ) -> CarState:
        """
        接收一帧运动学参数，更新小车状态。

        参数:
          velocity:       线速度 (m/s)
          steering_angle: 转向角 (rad)
          timestamp_ns:   时间戳 (纳秒)

        返回: 更新后的 CarState
        """
        # 步骤 1: 异常检测
        velocity = self._validate_velocity(velocity, timestamp_ns)
        steering_angle = self._clamp(steering_angle, -MAX_STEERING, MAX_STEERING)
        if wheel_base is not None:
            self.wheel_base = wheel_base

        # 步骤 2: 中值滤波
        self._vel_window.append(velocity)
        self._steer_window.append(steering_angle)

        v_filtered = _median(self._vel_window)
        s_filtered = _median(self._steer_window)

        # 步骤 3: 时间差
        if self._last_timestamp_ns == 0:
            dt = 0.0
        else:
            dt = (timestamp_ns - self._last_timestamp_ns) / 1e9  # ns → s
            dt = self._clamp(dt, 0.0, 1.0)

        # 步骤 4: 自行车模型积分
        if dt > 0:
            x, y, yaw = _bicycle_step(
                self._state.x, self._state.y, self._state.yaw,
                v_filtered, s_filtered, self.wheel_base, dt,
            )
        else:
            x, y, yaw = self._state.x, self._state.y, self._state.yaw

        # 步骤 5: 更新状态
        self._state = CarState(
            timestamp_ns=timestamp_ns,
            x=x, y=y, z=self._state.z,
            yaw=yaw,
            velocity=v_filtered,
            steering=s_filtered,
        )
        bisect.insort(self._history, self._state, key=lambda s: s.timestamp_ns)
        if len(self._history) > self._history_max:
            self._history = self._history[-self._history_max // 2:]
        self._last_vel = v_filtered
        self._last_timestamp_ns = timestamp_ns
        self._update_count += 1

        return self._state

    def update_position(
        self, x: float, y: float, z: float, yaw: float, timestamp_ns: int
    ) -> CarState:
        """
        用外部定位数据修正小车位置（如果有 GPS/IMU/视觉定位等）。
        这会把运动学累积的漂移拉回来。
        """
        self._state.x = x
        self._state.y = y
        self._state.z = z
        self._state.yaw = yaw
        self._state.timestamp_ns = timestamp_ns
        bisect.insort(self._history, self._state, key=lambda s: s.timestamp_ns)
        if len(self._history) > self._history_max:
            self._history = self._history[-self._history_max // 2:]
        return self._state

    def get_position(self, timestamp_ns: int) -> CarState | None:
        """
        查询小车在某个时刻的位置。
        用于给点云帧/照片打时间戳，对应到轨迹上的位置。

        如果查询的时刻在两个已知状态之间，做线性插值。
        """
        if not self._history:
            return None

        # 精确匹配
        for s in reversed(self._history):
            if s.timestamp_ns == timestamp_ns:
                return s

        # 插值: 找最近的前后两个状态
        if timestamp_ns <= self._history[0].timestamp_ns:
            return self._history[0]
        if timestamp_ns >= self._history[-1].timestamp_ns:
            return self._history[-1]

        before, after = None, None
        for i, s in enumerate(self._history):
            if s.timestamp_ns <= timestamp_ns:
                before = s
            if s.timestamp_ns >= timestamp_ns and after is None:
                after = s
                break

        if before is None or after is None or before is after:
            return before or after

        # 线性插值
        t_range = after.timestamp_ns - before.timestamp_ns
        if t_range == 0:
            return before
        alpha = (timestamp_ns - before.timestamp_ns) / t_range

        return CarState(
            timestamp_ns=timestamp_ns,
            x=before.x + alpha * (after.x - before.x),
            y=before.y + alpha * (after.y - before.y),
            z=before.z + alpha * (after.z - before.z),
            yaw=_angle_lerp(before.yaw, after.yaw, alpha),
            velocity=before.velocity + alpha * (after.velocity - before.velocity),
            steering=before.steering + alpha * (after.steering - before.steering),
        )

    @property
    def state(self) -> CarState:
        return self._state

    @property
    def history(self) -> list[CarState]:
        return self._history

    def reset(self) -> None:
        """重置估计器内部状态。"""
        self._state = CarState(timestamp_ns=0)
        self._vel_window.clear()
        self._steer_window.clear()
        self._last_valid_vel = 0.0
        self._last_vel = 0.0
        self._last_timestamp_ns = 0
        self._history.clear()
        self._update_count = 0
        self._rejected_count = 0

    @property
    def stats(self) -> dict:
        return {
            "updates": self._update_count,
            "rejected": self._rejected_count,
            "history_points": len(self._history),
        }

    # ================================================================
    #  内部: 异常检测
    # ================================================================

    def _validate_velocity(self, v: float, timestamp_ns: int) -> float:
        """
        检测并修复异常速度值。

        规则:
          1. 加速度超限 → 钳制到物理极限
          2. 速度从非零突然归零 → 判定为传输错误，沿用上一个值
        """
        if v < 0:
            v = 0.0

        # 零速检测
        if self._last_valid_vel > MIN_SPEED_FOR_ZERO_CHECK and v == 0.0:
            logger.debug("Zero-speed anomaly: v_prev=%.2f, v_cur=0 → using last valid", self._last_valid_vel)
            self._rejected_count += 1
            return self._last_valid_vel

        # 加速度检测
        if self._last_timestamp_ns > 0 and self._last_vel > 0:
            dt = max((timestamp_ns - self._last_timestamp_ns) / 1e9, 0.001)
            if dt > 0:
                accel = (v - self._last_vel) / dt

                if accel > MAX_ACCEL:
                    v = self._last_vel + MAX_ACCEL * dt
                    logger.debug("Accel spike +%.1f m/s² → clamped to %.2f", accel, v)
                    self._rejected_count += 1
                elif accel < -MAX_DECEL:
                    v = self._last_vel - MAX_DECEL * dt
                    logger.debug("Decel spike %.1f m/s² → clamped to %.2f", accel, v)
                    self._rejected_count += 1

        self._last_valid_vel = v
        return v

    @staticmethod
    def _clamp(val: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, val))


# ================================================================
#  数学工具
# ================================================================

def _bicycle_step(
    x: float, y: float, yaw: float,
    v: float, steer: float, wheel_base: float, dt: float,
) -> tuple[float, float, float]:
    """
    自行车模型一步积分。

    直线运动: x += v*cos(yaw)*dt, y += v*sin(yaw)*dt
    转弯: 绕瞬时旋转中心 (ICR) 做圆弧运动
    """
    if abs(steer) < 1e-6:
        x += v * math.cos(yaw) * dt
        y += v * math.sin(yaw) * dt
    else:
        turn_radius = wheel_base / math.tan(steer)
        angular_vel = v / turn_radius
        yaw_new = yaw + angular_vel * dt
        x += turn_radius * (math.sin(yaw_new) - math.sin(yaw))
        y += turn_radius * (math.cos(yaw) - math.cos(yaw_new))
        yaw = yaw_new

    return x, y, yaw


def _angle_lerp(a: float, b: float, t: float) -> float:
    """角度线性插值，处理 ±π 环绕。"""
    diff = b - a
    while diff > math.pi:
        diff -= 2 * math.pi
    while diff < -math.pi:
        diff += 2 * math.pi
    return a + diff * t


def _median(window: deque) -> float:
    """中值滤波: 返回排序后的中间值。"""
    if not window:
        return 0.0
    vals = sorted(window)
    n = len(vals)
    if n % 2 == 1:
        return vals[n // 2]
    return (vals[n // 2 - 1] + vals[n // 2]) / 2
