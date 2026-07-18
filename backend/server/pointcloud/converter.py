# ============================================================
# backend/server/pointcloud/converter.py
# 点云转换层 (Layer 3.5)：深度图 → 三维点云（针孔模型）
#
# 设计与用法:
#   导出 depth_to_pointcloud() 函数
#   输入: base64 编码的 16-bit PNG 深度图
#   输出: N×3 numpy float32 点云数组 (相机坐标系)
# ============================================================
#   深度值单位: 原始为 mm, 除 depth_scale 得米
#   针孔模型:  X=(u-cx)*Z/fx, Y=(v-cy)*Z/fy, Z=depth/scale
# ============================================================

import base64
import logging

import numpy as np

logger = logging.getLogger(__name__)


def depth_to_pointcloud(depth_b64: str) -> np.ndarray | None:
    """将 base64 深度图转为 N×3 点云（相机坐标系）

    Args:
        depth_b64: base64 编码的 16-bit PNG 深度图, 像素值 = 深度 mm

    Returns:
        (N, 3) float32 点云, 单位为米; 解析失败返回 None
    """
    try:
        import cv2
    except ImportError:
        logger.error("opencv-python 未安装, 无法解码深度图")
        return None

    try:
        depth_bytes = base64.b64decode(depth_b64)
        depth_arr = np.frombuffer(depth_bytes, dtype=np.uint8)
        depth_img = cv2.imdecode(depth_arr, cv2.IMREAD_UNCHANGED)
        if depth_img is None:
            logger.warning("深度图解码失败")
            return None
    except Exception:
        logger.exception("深度图解码异常")
        return None

    from server.config import get_config
    cfg = get_config()
    depth_cfg = cfg.get('depth_camera', {})
    depth_proc = cfg.get('depth', {})

    fx = depth_cfg.get('fx', 0.0)
    fy = depth_cfg.get('fy', 0.0)
    cx = depth_cfg.get('cx', 0.0)
    cy = depth_cfg.get('cy', 0.0)
    depth_scale = depth_proc.get('depth_scale', 1000)
    min_depth = depth_proc.get('min_depth', 0.6)
    max_depth = depth_proc.get('max_depth', 8.0)

    if fx == 0.0 or fy == 0.0:
        logger.warning("深度相机内参未配置, 无法生成点云")
        return None

    depth_m = depth_img.astype(np.float32) / depth_scale

    mask = (depth_m > min_depth) & (depth_m < max_depth)
    v, u = np.where(mask)
    z = depth_m[v, u]

    x = (u - cx) * z / fx
    y = (v - cy) * z / fy

    return np.column_stack([x, y, z]).astype(np.float32)
