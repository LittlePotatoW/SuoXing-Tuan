# ============================================================
# backend/reconstruction/coloring.py
# 从相机图像为世界系点云采样颜色，供重建管线使用
# ============================================================

import logging
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger("reconstruction.coloring")


def decode_image(image_bytes: bytes) -> Optional[np.ndarray]:
    """JPEG bytes → BGR uint8 数组 (H, W, 3)。解码失败返回 None。"""
    from io import BytesIO
    from PIL import Image

    try:
        pil_img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img = np.array(pil_img)  # (H, W, 3) RGB
        return img[:, :, ::-1].copy()  # RGB → BGR
    except Exception:
        return None


def sample_bilinear(img: np.ndarray, u: float, v: float) -> np.ndarray:
    """浮点像素坐标双线性插值，返回 (3,) uint8 BGR。"""
    h, w = img.shape[:2]
    u = float(np.clip(u, 0.0, w - 1.001))
    v = float(np.clip(v, 0.0, h - 1.001))

    u0 = int(np.floor(u))
    v0 = int(np.floor(v))
    u1 = min(u0 + 1, w - 1)
    v1 = min(v0 + 1, h - 1)

    du = u - u0
    dv = v - v0

    top = (img[v0, u0].astype(np.float32) * (1.0 - du) +
           img[v0, u1].astype(np.float32) * du)
    bottom = (img[v1, u0].astype(np.float32) * (1.0 - du) +
              img[v1, u1].astype(np.float32) * du)
    color = top * (1.0 - dv) + bottom * dv
    return np.round(color).astype(np.uint8)


def project_points_to_camera(
    points_world: np.ndarray,
    K: np.ndarray,
    R_wc: np.ndarray,
    t_wc: np.ndarray,
    dist_coeff: np.ndarray,
    width: int,
    height: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    世界系点云 → 图像平面投影。

    参数:
        points_world: (N, 3) 世界坐标系点云
        K:             (3, 3) 相机内参矩阵
        R_wc:          (3, 3) 世界→相机旋转矩阵
        t_wc:          (3,)   世界→相机平移向量
        dist_coeff:    (5,)   畸变系数 [k1,k2,p1,p2,k3]
        width, height: 图像尺寸

    返回:
        uv_valid:   (M, 2) 有效投影像素坐标
        depths:     (M,)   相机系深度 Z_cam
        valid_mask: (N,)   布尔掩码，标记成功投影的原始点
    """
    # 1. 世界 → 相机坐标系
    pts_cam = points_world @ R_wc.T + t_wc  # (N, 3)
    x = pts_cam[:, 0]
    y = pts_cam[:, 1]
    z = pts_cam[:, 2]

    # 2. 过滤相机后方点
    front = z > 0
    if not np.any(front):
        return np.empty((0, 2)), np.empty((0,)), front

    x_f, y_f, z_f = x[front], y[front], z[front]
    x_norm = x_f / z_f
    y_norm = y_f / z_f
    r2 = x_norm * x_norm + y_norm * y_norm

    # 3. 畸变校正
    k1, k2, p1, p2, k3 = dist_coeff[0], dist_coeff[1], dist_coeff[2], dist_coeff[3], dist_coeff[4]
    radial = 1.0 + k1 * r2 + k2 * r2 * r2 + k3 * r2 * r2 * r2
    x_dist = x_norm * radial + 2.0 * p1 * x_norm * y_norm + p2 * (r2 + 2.0 * x_norm * x_norm)
    y_dist = y_norm * radial + p1 * (r2 + 2.0 * y_norm * y_norm) + 2.0 * p2 * x_norm * y_norm

    # 4. 内参映射
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]
    u = fx * x_dist + cx
    v = fy * y_dist + cy

    # 5. 边界裁剪
    in_bounds = (u >= 0) & (u < width) & (v >= 0) & (v < height)
    mask_idx = np.where(front)[0]
    final_idx = mask_idx[in_bounds]

    valid_mask = np.zeros(len(points_world), dtype=bool)
    valid_mask[final_idx] = True

    uv_valid = np.column_stack([u[in_bounds], v[in_bounds]])
    depths = z_f[in_bounds]

    return uv_valid, depths, valid_mask


def sample_colors_from_cameras(
    points_world: np.ndarray,
    cameras_world: list,
    images: list,
    intrinsics_list: list,
) -> Optional[np.ndarray]:
    """
    从多相机图像为世界系点云采样颜色。

    多相机融合策略: "最近相机优先" — 深度更小的投影覆盖深度更大的。

    返回:
        (N, 3) uint8 BGR 颜色数组，或 None（无有效相机时）
    """
    n = points_world.shape[0]
    if n == 0:
        return None

    # 需要 transform 模块的 pose_to_matrix
    from reconstruction.transform import pose_to_matrix

    best_colors = np.full((n, 3), 128, dtype=np.uint8)
    best_depths = np.full(n, np.inf)
    any_success = False

    for i in range(len(cameras_world)):
        # 校验数据完整性
        if i >= len(images) or i >= len(intrinsics_list):
            continue
        img_bytes = images[i]
        intrinsics = intrinsics_list[i]
        if img_bytes is None or intrinsics is None:
            continue

        img = decode_image(img_bytes)
        if img is None:
            continue

        cam_pose = cameras_world[i]
        pos = [cam_pose.position.x, cam_pose.position.y, cam_pose.position.z]
        rot = [cam_pose.rotation.qw, cam_pose.rotation.qx,
               cam_pose.rotation.qy, cam_pose.rotation.qz]

        # 相机世界位姿 → 世界→相机变换
        T_cam_world = pose_to_matrix(pos, rot)
        try:
            T_world_cam = np.linalg.inv(T_cam_world)
        except np.linalg.LinAlgError:
            continue
        R_wc = T_world_cam[:3, :3]
        t_wc = T_world_cam[:3, 3]

        uv, depths, valid = project_points_to_camera(
            points_world,
            intrinsics.K,
            R_wc,
            t_wc,
            getattr(intrinsics, 'dist_coeff', np.zeros(5, dtype=np.float64)),
            getattr(intrinsics, 'image_width', 640),
            getattr(intrinsics, 'image_height', 480),
        )

        if len(uv) == 0:
            continue

        # 对每个有效投影点，深度更近则覆盖
        valid_indices = np.where(valid)[0]
        for j in range(len(uv)):
            orig_idx = valid_indices[j]
            d = depths[j]
            if d < best_depths[orig_idx]:
                u, v = float(uv[j, 0]), float(uv[j, 1])
                best_colors[orig_idx] = sample_bilinear(img, u, v)
                best_depths[orig_idx] = d
                any_success = True

    if not any_success:
        return None

    # BGR → RGB
    colors_rgb = best_colors[:, ::-1].copy()

    # 填充未投影点 (灰色 128): 用最近已投影点的颜色
    gray_mask = np.all(colors_rgb == 128, axis=1)
    if gray_mask.any() and not gray_mask.all():
        _fill_gray_colors(points_world, colors_rgb, gray_mask)

    return colors_rgb


def _fill_gray_colors(
    points: np.ndarray,
    colors: np.ndarray,
    gray_mask: np.ndarray,
) -> None:
    """将未投影的灰色点用最近已投影点的颜色填充（原地修改 colors）。"""
    valid_mask = ~gray_mask
    valid_pts = points[valid_mask]       # (K, 3)
    valid_cols = colors[valid_mask]       # (K, 3)
    gray_pts = points[gray_mask]          # (M, 3)
    gray_indices = np.where(gray_mask)[0]

    # 分块处理避免内存溢出（每块最多 2000 个灰色点）
    chunk = 2000
    for start in range(0, len(gray_pts), chunk):
        end = min(start + chunk, len(gray_pts))
        gpts_chunk = gray_pts[start:end]
        # (M_chunk, K, 3) 距离平方
        diff = gpts_chunk[:, np.newaxis, :] - valid_pts[np.newaxis, :, :]
        dist2 = np.sum(diff * diff, axis=2)  # (M_chunk, K)
        nn = np.argmin(dist2, axis=1)        # (M_chunk,)
        colors[gray_indices[start:end]] = valid_cols[nn]
