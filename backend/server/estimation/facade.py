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
#
# rgbd/fusion 模式使用 Actor 线程: HTTP 路径只交换帧数据不计算
# ============================================================
#   支持 4 种模式: bicycle / constant / rgbd / fusion
# ============================================================

import logging
import math
import threading
import time
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

# ---------- Actor 线程状态 ----------
_actor_thread: threading.Thread | None = None
_actor_running = False
_actor_error_count = 0
_actor_odometry_count = 0
_actor_skip_count = 0
# 共享槽: (image_b64, depth_b64, timestamp)
_pending_frame: tuple | None = None
_pending_lock = threading.Lock()


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
        self._odometry_skip = est.get('odometry_frame_skip', 3)
        self._odometry_frame_count = 0

        self._last_ts: float | None = time.time() if self._mode == 'constant' else None
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

        # Actor 线程：rgbd/fusion 模式下自动启动
        if self._mode in ('rgbd', 'fusion'):
            self._start_actor()

    # ============================================================
    # Actor 线程管理
    # ============================================================

    def _start_actor(self) -> None:
        global _actor_thread, _actor_running, _actor_error_count, _pending_frame
        _actor_running = True
        _actor_error_count = 0
        _actor_odometry_count = 0
        _actor_skip_count = 0
        _pending_frame = None
        _actor_thread = threading.Thread(target=self._actor_loop, daemon=True, name="odometry-actor")
        _actor_thread.start()
        logger.warning("[Actor] 线程已启动, mode=%s", self._mode)

    def _stop_actor(self) -> None:
        global _actor_running, _actor_thread
        _actor_running = False
        if _actor_thread and _actor_thread.is_alive():
            _actor_thread.join(timeout=3.0)
            if _actor_thread.is_alive():
                logger.warning("[Actor] 线程 3s 未退出, 可能卡在 odometry 中")
            else:
                logger.warning("[Actor] 线程已停止, odometry=%d, skip=%d, errors=%d",
                              _actor_odometry_count, _actor_skip_count, _actor_error_count)
        _actor_thread = None

    def _actor_loop(self) -> None:
        """后台循环: 读取共享槽 → 计算 odometry → 更新位置"""
        global _pending_frame, _actor_running, _actor_error_count, _actor_odometry_count, _actor_skip_count

        last_processed_ts = 0.0

        while _actor_running:
            # 读取共享槽
            with _pending_lock:
                frame_data = _pending_frame
                _pending_frame = None

            if frame_data is None:
                time.sleep(0.05)
                continue

            image_b64, depth_b64, timestamp = frame_data
            if timestamp <= last_processed_ts:
                _actor_skip_count += 1
                continue

            last_processed_ts = timestamp

            # 计算 odometry
            t0 = time.perf_counter()
            try:
                delta = self._rgbd.update_frame(image_b64, depth_b64)
                elapsed = (time.perf_counter() - t0) * 1000
                _actor_odometry_count += 1

                if delta:
                    dx, dz, dh = delta
                    with self._rwlock:
                        heading_rad = math.radians(self._heading)
                        self._x += -dx * math.sin(heading_rad) + dz * math.cos(heading_rad)
                        self._y += dx * math.cos(heading_rad) + dz * math.sin(heading_rad)
                        self._heading += dh
                        self._last_ts = timestamp
                        self._append()
                    logger.warning("[Actor] odometry OK #%d: %.0fms dx=%.3f dz=%.3f dh=%.2f°",
                                  _actor_odometry_count, elapsed, dx, dz, dh)
                else:
                    logger.warning("[Actor] odometry #%d: success=False, %.0fms",
                                  _actor_odometry_count, elapsed)
            except Exception:
                _actor_error_count += 1
                logger.exception("[Actor] odometry 异常 #%d", _actor_error_count)
                if _actor_error_count > 10:
                    logger.error("[Actor] 异常过多, 停止 Actor 线程")
                    _actor_running = False
                    break

    # ============================================================
    # 工厂方法
    # ============================================================

    @classmethod
    def get(cls) -> 'PositionEstimator':
        """获取当前实例。未初始化时自动用默认配置创建。"""
        global _instance
        if _instance is None:
            cls.create()
        return _instance

    @classmethod
    def create(cls, mode: str | None = None,
               config: dict | None = None) -> 'PositionEstimator':
        """创建新实例（先销毁旧的）。mode=None 则用 config 默认值。"""
        global _instance
        with _lock:
            if _instance is not None:
                _instance._stop_actor()
                with _instance._rwlock:
                    _instance._trajectory.clear()
            _instance = None

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
                _instance._stop_actor()
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
                return
            if self._last_ts is None:
                self._last_ts = timestamp
                logger.warning("[Estimator] 首条遥测, mode=%s ts=%.3f", self._mode, timestamp)
                return

            delta_t = timestamp - self._last_ts
            self._last_ts = timestamp

            if self._mode == 'constant':
                raw_speed = speed
                speed = self._constant_speed
                steering_angle = 0.0
                logger.warning("[Estimator] constant: raw=%.2f cfg=%.2f use=%.2f dt=%.3fs x=%.2f y=%.2f",
                              raw_speed, self._constant_speed, speed, delta_t, self._x, self._y)

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
        """RGB-D 帧数据入口 (模式3/4)

        rgbd 模式: 交换帧数据到 Actor 共享槽, 立即返回
        fusion 模式: 交换数据到共享槽, Actor 内部用 visual 校正
        """
        logger.warning("[Estimator] update_frame called, mode=%s ts=%.3f", self._mode, timestamp)

        if self._mode == 'rgbd':
            with _pending_lock:
                global _pending_frame
                _pending_frame = (image, depth_map, timestamp)

        elif self._mode == 'constant':
            with self._rwlock:
                if self._last_ts is None:
                    self._last_ts = timestamp
                    logger.warning("[Estimator] constant: ref_ts=%.3f speed=%.2f",
                                  self._last_ts, self._constant_speed)

        elif self._mode == 'fusion':
            result = self._fusion.update_visual(
                image, depth_map, self._x, self._y, self._heading)
            if result:
                with self._rwlock:
                    self._x, self._y, self._heading = result
                    self._last_ts = timestamp
                    self._append()

    # ============================================================
    # 位置读取
    # ============================================================

    def get_position(self) -> Position:
        with self._rwlock:
            if not self._trajectory:
                if self._mode == 'constant' and self._last_ts is not None:
                    return self._extrapolate(time.time(), self._initial_x, self._initial_y,
                                            self._initial_heading, self._last_ts)
                return Position(time.time(), self._initial_x, self._initial_y,
                                self._initial_heading)
            last = self._trajectory[-1]
            return self._extrapolate(time.time(), last.x, last.y, last.heading, last.timestamp)

    def get_position_at(self, timestamp: float) -> Position:
        with self._rwlock:
            if not self._trajectory:
                return self._extrapolate(timestamp, self._initial_x, self._initial_y,
                                        self._initial_heading, self._last_ts or 0.0)
            timestamps = [p.timestamp for p in self._trajectory]
            idx = bisect_left(timestamps, timestamp)
            if idx >= len(self._trajectory):
                last = self._trajectory[-1]
                return self._extrapolate(timestamp, last.x, last.y, last.heading, last.timestamp)
            if idx == 0:
                return self._trajectory[0]
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

    def _extrapolate(self, timestamp: float, x: float, y: float,
                      heading: float, ref_ts: float) -> Position:
        """constant 模式: 从参考点按时间差外推位置"""
        if self._mode != 'constant':
            return Position(timestamp, x, y, heading)
        dt = timestamp - ref_ts
        if dt <= 0:
            return Position(timestamp, x, y, heading)
        h = math.radians(heading)
        nx = x + self._constant_speed * math.cos(h) * dt
        ny = y + self._constant_speed * math.sin(h) * dt
        logger.warning("[Estimator] extrapolate: ref_ts=%.3f ts=%.3f dt=%.3f (%.2f,%.2f)→(%.2f,%.2f) mode=%s speed=%.2f",
                      ref_ts, timestamp, dt, x, y, nx, ny, self._mode, self._constant_speed)
        return Position(timestamp, nx, ny, heading)

    def _append(self):
        self._trajectory.append(
            Position(self._last_ts, self._x, self._y, self._heading))
        if len(self._trajectory) > self._max_history:
            self._trajectory.pop(0)
