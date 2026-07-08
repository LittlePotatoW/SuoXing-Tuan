# ============================================================
#  文件: backend/data_pre_processing/kinematics_api.py
#  所属: SuoXing-Tuan / 数据融合与缺陷投影模块
#  职责: 航迹推算引擎（Dead Reckoning Engine）
#        - 基于自行车模型的运动学积分
#        - 对外提供 get_pose(timestamp_ns) 查询接口
#        - 仅绕Z轴运动（平面运动，z 恒为 0）
#
#  注意: 当前为 Mock 实现，用于本地测试。
#        TODO: 替换为同事提供的正式 DeadReckoningEngine 实例。
#        同事版本预计会:
#          1. 内部维护订阅机制，自动接收 location_data 流
#          2. 提供更精确的传感器融合（IMU + 轮速计）
#          3. 支持回环检测消除累积漂移
# ============================================================

import math
import logging
from typing import Optional

logger = logging.getLogger("data_pre_processing.kinematics")


class DeadReckoningEngine:
    """
    航迹推算引擎 — 基于自行车模型的运动学积分。

    职责:
      持续接收小车运动学参数（velocity, steering_angle, wheel_base），
      通过自行车模型积分维护小车在世界坐标系中的位姿估计。

    坐标系约定:
      世界坐标系: 初始位置为原点，z=0（平面运动）
      车体朝向: 仅绕Z轴旋转（Yaw角），四元数仅有 qw 和 qz 非零

    自行车模型:
      ω = (v / L) * tan(δ)      角速度
      Δθ = ω * Δt              朝向变化量
      Δx = v * cos(θ) * Δt     X 位移
      Δy = v * sin(θ) * Δt     Y 位移

    边界处理:
      - velocity = 0 → 位置不变
      - steering_angle = 0 → 直线运动，ω = 0
      - 静止 (v=0) 超过 5 秒 → 保持 theta 不变
      - dt > 2s（长时间无数据） → 标记重置，θ 保持，v 置 0
    """

    def __init__(self, initial_x: float = 0.0, initial_y: float = 0.0,
                 initial_yaw: float = 0.0):
        """
        初始化航迹推算引擎。

        参数:
          initial_x: 初始世界X坐标（米）
          initial_y: 初始世界Y坐标（米）
          initial_yaw: 初始朝向角（弧度，绕Z轴）
        """
        # ── 状态变量 ──
        self._x: float = initial_x
        self._y: float = initial_y
        self._theta: float = initial_yaw  # Yaw 角（弧度）

        # ── 时间追踪 ──
        self._last_timestamp_ns: Optional[int] = None

        # ── 上一帧运动学参数（用于插值） ──
        self._last_velocity: float = 0.0
        self._last_steering_angle: float = 0.0
        self._last_wheel_base: float = 1.5

        # ── 统计 ──
        self._integration_count: int = 0
        self._total_distance: float = 0.0
        self._reset_count: int = 0

        # ── 最大允许的积分间隔（纳秒），超过则标记重置 ──
        self._max_dt_ns: int = 2_000_000_000  # 2 秒

        logger.info("DeadReckoningEngine 初始化: x=%.3f, y=%.3f, yaw=%.4f rad",
                    self._x, self._y, self._theta)

    # ================================================================
    #  对外接口
    # ================================================================

    def feed_kinematics(self, kinematics: dict, timestamp_ns: int) -> None:
        """
        喂入一帧运动学数据，触发积分更新。

        参数:
          kinematics: 运动学参数字典，预期包含:
            - velocity (float, m/s): 线速度
            - steering_angle (float, rad): 转向角
            - wheel_base (float, m): 轴距
          timestamp_ns: 该帧数据的时间戳（纳秒）

        容错:
          - 缺失字段使用默认值（velocity=0.0, steering_angle=0.0, wheel_base=1.5）
          - 第一帧数据跳过积分（无历史dt），仅记录状态
        """
        # ── 提取参数（带 fallback） ──
        v = float(kinematics.get("velocity", 0.0))
        delta = float(kinematics.get("steering_angle", 0.0))
        L = float(kinematics.get("wheel_base", 1.5))

        # ── 存储最新值（用于后续 get_pose 的推测） ──
        self._last_velocity = v
        self._last_steering_angle = delta
        self._last_wheel_base = L

        # ── 第一帧：只记录时间戳，不积分 ──
        if self._last_timestamp_ns is None:
            self._last_timestamp_ns = timestamp_ns
            logger.debug("首帧 kinematics 到达，时间戳=%d ns，等待下一帧开始积分", timestamp_ns)
            return

        # ── 计算时间差 ──
        dt_ns = timestamp_ns - self._last_timestamp_ns

        if dt_ns <= 0:
            logger.warning("时间戳乱序或重复: current=%d, last=%d, dt=%d ns → 跳过",
                           timestamp_ns, self._last_timestamp_ns, dt_ns)
            return

        # ── 长时间无数据：标记重置 ──
        if dt_ns > self._max_dt_ns:
            logger.warning("长时间无数据: dt=%.2f s > 2s → 标记重置，保持朝向",
                           dt_ns / 1e9)
            self._reset_count += 1
            # θ 保持不变，v 置 0（保守策略）
            v = 0.0

        dt_s = dt_ns / 1e9  # ns → s

        # ── 自行车模型积分 ──
        if abs(v) < 1e-9:
            # 静止：位置和朝向不变
            pass
        elif abs(delta) < 1e-9:
            # 直线运动
            self._x += v * math.cos(self._theta) * dt_s
            self._y += v * math.sin(self._theta) * dt_s
            self._total_distance += abs(v) * dt_s
        else:
            # 阿克曼转向（自行车模型）
            omega = (v / L) * math.tan(delta)
            self._theta += omega * dt_s
            self._x += v * math.cos(self._theta) * dt_s
            self._y += v * math.sin(self._theta) * dt_s
            self._total_distance += abs(v) * dt_s

        # ── 归一化 theta 到 [-π, π] ──
        self._theta = math.atan2(math.sin(self._theta), math.cos(self._theta))

        # ── 更新时间戳 ──
        self._last_timestamp_ns = timestamp_ns
        self._integration_count += 1

    def get_pose(self, timestamp_ns: int) -> dict:
        """
        查询指定时刻的小车世界位姿。

        参数:
          timestamp_ns: 查询时刻（纳秒）

        返回:
          dict: {
            "position": {"x": float, "y": float, "z": float},
            "rotation": {"qw": float, "qx": 0.0, "qy": 0.0, "qz": float}
          }
          注意: z 恒为 0（平面运动），qx/qy 恒为 0（仅绕Z轴旋转）

        若从未收到任何 kinematics 数据，返回原点位姿。
        """
        # ── 若有最新数据且查询时间晚于最后积分时间，做短时推测 ──
        # 注意: 这是简化实现；同事正式版可能使用更复杂的插值/外推
        x, y, theta = self._x, self._y, self._theta

        if self._last_timestamp_ns is not None and timestamp_ns > self._last_timestamp_ns:
            dt_s = (timestamp_ns - self._last_timestamp_ns) / 1e9
            v = self._last_velocity
            delta = self._last_steering_angle
            L = self._last_wheel_base

            # 仅在 dt < 0.5s 时做短时推测（避免长时间无数据后的错误推断）
            if dt_s < 0.5 and abs(v) > 1e-9:
                if abs(delta) < 1e-9:
                    x += v * math.cos(theta) * dt_s
                    y += v * math.sin(theta) * dt_s
                else:
                    omega = (v / L) * math.tan(delta)
                    theta += omega * dt_s
                    x += v * math.cos(theta) * dt_s
                    y += v * math.sin(theta) * dt_s

        # ── Yaw → 四元数（仅绕Z轴） ──
        half_theta = theta / 2.0
        qw = math.cos(half_theta)
        qz = math.sin(half_theta)

        return {
            "position": {"x": x, "y": y, "z": 0.0},
            "rotation": {"qw": qw, "qx": 0.0, "qy": 0.0, "qz": qz},
        }

    # ================================================================
    #  状态查询（调试用）
    # ================================================================

    @property
    def state(self) -> dict:
        """返回当前所有内部状态，方便调试。"""
        return {
            "x": self._x,
            "y": self._y,
            "theta_rad": self._theta,
            "theta_deg": math.degrees(self._theta),
            "total_distance_m": self._total_distance,
            "integration_count": self._integration_count,
            "reset_count": self._reset_count,
            "last_timestamp_ns": self._last_timestamp_ns,
        }

    def reset(self, x: float = 0.0, y: float = 0.0, yaw: float = 0.0) -> None:
        """重置状态到指定位置和朝向。"""
        self._x = x
        self._y = y
        self._theta = yaw
        self._last_timestamp_ns = None
        self._total_distance = 0.0
        logger.info("DeadReckoningEngine 重置: x=%.3f, y=%.3f, yaw=%.4f rad", x, y, yaw)
