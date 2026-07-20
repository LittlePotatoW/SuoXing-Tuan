# ============================================================
# backend/server/pointcloud/converter.py
# 点云转换层 (Layer 3.5)：深度图 → 三维点云（针孔模型）
#
# 设计与用法:
#   导出 decode_depth() — 解码深度图，返回有序+无序点云 (给 YOLO 3D 映射用)
#   导出 depth_to_pointcloud() — 向后兼容，返回 N×3 无序点云
#   输入: base64 编码的 16-bit PNG 深度图
# ============================================================
#   深度值单位: 原始为 mm, 除 depth_scale 得米
#   针孔模型:  X=(u-cx)*Z/fx, Y=(v-cy)*Z/fy, Z=depth/scale
# ============================================================

import base64
import logging

import numpy as np

logger = logging.getLogger(__name__)


def decode_depth(depth_b64: str, subsample: int = 1) -> tuple | None:
    """解码深度图，返回有序和无序点云

    Args:
        depth_b64: base64 编码的 16-bit PNG 深度图
        subsample: 采样步长

    Returns:
        (ordered_pc, depth_m, pc) 或 None:
            ordered_pc: (H, W, 3) float32  有序点云, 无效区域为 NaN
            depth_m:    (H, W)    float32  深度值(米), 无效区域为 0
            pc:         (N, 3)    float32  无序有效点云
    """
    if not depth_b64:
        return None

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
            return None
    except Exception:
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

    if subsample > 1:
        depth_img = depth_img[::subsample, ::subsample]

    H, W = depth_img.shape
    depth_m = depth_img.astype(np.float32) / depth_scale

    # 有序点云 (H, W, 3)，无效区域填 NaN
    u_grid, v_grid = np.meshgrid(np.arange(W), np.arange(H))
    z = depth_m
    x = (u_grid * subsample - cx) * z / fx
    y = (v_grid * subsample - cy) * z / fy
    ordered_pc = np.stack([x, y, z], axis=-1).astype(np.float32)

    # 有效范围外的区域设 NaN
    invalid = (z <= min_depth) | (z >= max_depth) | (z == 0)
    ordered_pc[invalid] = np.nan
    depth_m[invalid] = 0.0

    # 无序有效点云
    mask = ~invalid
    vs, us = np.where(mask)
    pc = ordered_pc[vs, us, :]
    pc = pc[np.isfinite(pc).all(axis=1)]

    return ordered_pc, depth_m, pc


def sample_colors(image_b64: str, depth_m: np.ndarray) -> np.ndarray | None:
    """从 RGB 图中采样有效像素的颜色，对齐 decode_depth 输出的 pc

    Args:
        image_b64: base64 JPEG RGB 图像
        depth_m: (H, W) float32 深度图（来自 decode_depth，0=无效）

    Returns:
        (N, 3) uint8 RGB 颜色数组，与 decode_depth 的 pc 对齐; 失败返回 None
    """
    if not image_b64 or depth_m is None:
        return None

    try:
        import cv2
    except ImportError:
        return None

    try:
        img_bytes = base64.b64decode(image_b64)
        img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return None
    except Exception:
        return None

    Hd, Wd = depth_m.shape
    Hb, Wb = bgr.shape[:2]

    # 如果 RGB 和深度图尺寸一致（都是 subsample 后的），直接采样
    if Hb == Hd and Wb == Wd:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        mask_valid = depth_m > 0
        rows, cols = np.where(mask_valid)
        return rgb[rows, cols, :].astype(np.uint8)

    # 尺寸不一致：把 RGB resize 到深度图尺寸
    rgb_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgb_resized = cv2.resize(rgb_full, (Wd, Hd))
    mask_valid = depth_m > 0
    rows, cols = np.where(mask_valid)
    return rgb_resized[rows, cols, :].astype(np.uint8)


def depth_to_pointcloud(depth_b64: str, subsample: int = 1) -> np.ndarray | None:
    """将 base64 深度图转为 N×3 无序点云（向后兼容）

    Args:
        depth_b64:  base64 编码的 16-bit PNG 深度图
        subsample: 采样步长

    Returns:
        (N, 3) float32 点云, 单位为米; 解析失败返回 None
    """
    decoded = decode_depth(depth_b64, subsample)
    if decoded is None:
        return None
    _, _, pc = decoded
    return pc
