# ============================================================
# backend/server/estimation/rgbd_odometry.py
# 位置估计策略: Open3D RGB-D 视觉里程计 (模式3)
#
# 设计与用法:
#   导出 RgbdOdometryStrategy 类
#   update_frame(rgb_b64, depth_b64, timestamp) → (x, y, heading)
#   基于 Open3D compute_rgbd_odometry, 不需要 speed/steering
# ============================================================

import base64
import logging
import math

import numpy as np

logger = logging.getLogger(__name__)


class RgbdOdometryStrategy:
    """RGB-D 视觉里程计：连续两帧 RGB-D → 相对位姿 → 累积位置"""

    def __init__(self, config: dict):
        depth_cfg = config.get('depth_camera', {})
        self._fx = depth_cfg.get('fx', 0.0)
        self._fy = depth_cfg.get('fy', 0.0)
        self._cx = depth_cfg.get('cx', 0.0)
        self._cy = depth_cfg.get('cy', 0.0)
        self._width = depth_cfg.get('width', 640)
        self._height = depth_cfg.get('height', 480)
        self._depth_scale = config.get('depth', {}).get('depth_scale', 1000)

        self._prev_rgb: np.ndarray | None = None
        self._prev_depth: np.ndarray | None = None
        self._available = False

        try:
            import open3d as o3d
            self._o3d = o3d
            self._intrinsic = o3d.camera.PinholeCameraIntrinsic(
                self._width, self._height, self._fx, self._fy, self._cx, self._cy)
            self._option = o3d.pipelines.odometry.OdometryOption()
            self._available = True
        except ImportError:
            logger.warning("open3d 未安装, RGB-D 里程计不可用. pip install open3d")

    @property
    def available(self) -> bool:
        return self._available

    def update_frame(self, image_b64: str, depth_b64: str
                     ) -> tuple[float, float, float] | None:
        """返回 (dx, dy, dheading) 相对位移，None 表示无法计算"""
        if not self._available:
            return None

        try:
            import cv2
            rgb = _decode_jpeg(image_b64)
            depth = _decode_depth(depth_b64)
            if rgb is None or depth is None:
                logger.warning("[RGBD-O] 解码失败")
                return None

            if self._prev_rgb is None:
                self._prev_rgb = rgb
                self._prev_depth = depth
                logger.warning("[RGBD-O] 首帧已存储, {}x{}, depth range={:.2f}-{:.2f}m".format(
                    rgb.shape[1], rgb.shape[0], depth.min(), depth.max()))
                return None

            rgbd1 = self._o3d.geometry.RGBDImage.create_from_color_and_depth(
                self._o3d.geometry.Image(self._prev_rgb),
                self._o3d.geometry.Image(self._prev_depth),
                depth_scale=self._depth_scale, convert_rgb_to_intensity=False)
            rgbd2 = self._o3d.geometry.RGBDImage.create_from_color_and_depth(
                self._o3d.geometry.Image(rgb),
                self._o3d.geometry.Image(depth),
                depth_scale=self._depth_scale, convert_rgb_to_intensity=False)

            success, T, _ = self._o3d.pipelines.odometry.compute_rgbd_odometry(
                rgbd1, rgbd2, self._intrinsic,
                odo_init=np.eye(4),
                jacobian=self._o3d.pipelines.odometry.RGBDOdometryJacobianFromHybridTerm(),
                option=self._option)

            self._prev_rgb = rgb
            self._prev_depth = depth

            if not success:
                logger.warning("[RGBD-O] odometry success=False")
                return None

            dx = float(T[0, 3])
            dz = float(T[2, 3])
            dheading = -math.degrees(math.atan2(T[2, 0], T[2, 2]))
            logger.warning("[RGBD-O] odometry OK: dx={:.3f} dz={:.3f} dh={:.2f}°".format(dx, dz, dheading))
            return dx, dz, dheading

        except Exception:
            logger.exception("RGB-D odometry 计算失败")
            return None


def _decode_jpeg(b64: str) -> np.ndarray | None:
    try:
        import cv2
        data = base64.b64decode(b64)
        arr = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def _decode_depth(b64: str, min_m: float = 0.6, max_m: float = 8.0) -> np.ndarray | None:
    try:
        import cv2
        data = base64.b64decode(b64)
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        if img is None:
            return None
        depth_m = img.astype(np.float32) / 1000.0  # mm → m
        depth_m[(depth_m < min_m) | (depth_m > max_m)] = 0.0
        return depth_m * 1000.0  # 回退到 mm（Open3D depth_scale=1000 需要）
    except Exception:
        return None
