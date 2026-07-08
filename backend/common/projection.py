# ============================================================
# backend/common/projection.py
# 投影 / 反投影 / 桥接函数 — 统一来源
# ============================================================

from typing import Optional, Tuple

import numpy as np

from common.transform import pose_to_matrix, extrinsic_from_pose6dof, build_transformation_matrix
from common.camera import CameraIntrinsics


# ============================================================
# 数据格式转换
# ============================================================

def points_from_flat_list(flat: list[float], point_count: int) -> np.ndarray:
    """扁平列表 [x0,y0,z0,...] → (N, 3) numpy 数组。"""
    return np.array(flat, dtype=np.float64).reshape(point_count, 3)


# ============================================================
# 核心投影
# ============================================================

def project_points_to_image(
    points: np.ndarray,          # (N, 3) LiDAR 系点云
    K: np.ndarray,               # (3, 3) 内参
    R: np.ndarray,               # (3, 3) LiDAR→相机 旋转
    T: np.ndarray,               # (3,)   LiDAR→相机 平移
    dist_coeff: np.ndarray,      # (5,)   畸变 [k1,k2,p1,p2,k3]
    image_width: int, image_height: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    3D 点云 → 2D 图像投影。

    返回:
      uv_valid:   (M, 2) 有效投影像素坐标
      depths:     (M,)   相机系深度
      valid_mask: (N,)   布尔掩码
    """
    # 1. LiDAR → 相机坐标系
    pts_cam = points @ R.T + T  # (N, 3)
    x, y, z = pts_cam[:, 0], pts_cam[:, 1], pts_cam[:, 2]

    # 2. 过滤相机后方点 (Z <= 0)
    front = z > 0
    if not np.any(front):
        return np.empty((0, 2)), np.empty((0,)), front

    x_f, y_f, z_f = x[front], y[front], z[front]
    x_norm = x_f / z_f
    y_norm = y_f / z_f
    r2 = x_norm * x_norm + y_norm * y_norm

    # 3. 畸变校正
    k1, k2, p1, p2, k3 = (float(dist_coeff[i]) for i in range(5))
    radial = 1.0 + k1 * r2 + k2 * r2 * r2 + k3 * r2 * r2 * r2
    x_dist = x_norm * radial + 2.0 * p1 * x_norm * y_norm + p2 * (r2 + 2.0 * x_norm * x_norm)
    y_dist = y_norm * radial + p1 * (r2 + 2.0 * y_norm * y_norm) + 2.0 * p2 * x_norm * y_norm

    # 4. 内参映射
    fx, fy, cx, cy = float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2])
    u = fx * x_dist + cx
    v = fy * y_dist + cy

    # 5. 边界裁剪
    in_bounds = (u >= 0) & (u < image_width) & (v >= 0) & (v < image_height)
    mask_idx = np.where(front)[0]
    final_idx = mask_idx[in_bounds]

    valid_mask = np.zeros(len(points), dtype=bool)
    valid_mask[final_idx] = True

    uv_valid = np.column_stack([u[in_bounds], v[in_bounds]])
    depths = z_f[in_bounds]

    return uv_valid, depths, valid_mask


def filter_pointcloud(
    points: np.ndarray, filter_cfg: dict, R: np.ndarray, T: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """范围 + FOV 过滤。返回 (filtered_points, keep_mask)。"""
    keep = np.ones(len(points), dtype=bool)

    if filter_cfg.get("enable_range_filter", False):
        dists = np.linalg.norm(points, axis=1)
        r_min = filter_cfg.get("range_min", 0.0)
        r_max = filter_cfg.get("range_max", float("inf"))
        keep &= (dists >= r_min) & (dists <= r_max)

    if filter_cfg.get("enable_fov_filter", False):
        pts_cam = points @ R.T + T
        keep &= pts_cam[:, 2] > 0

    return points[keep], keep


def uv_to_depth_map(uv: np.ndarray, depths: np.ndarray,
                    width: int, height: int) -> np.ndarray:
    """稀疏投影 → 密集深度图。多点同像素取最小深度。"""
    depth_map = np.full((height, width), np.inf, dtype=np.float32)
    for j in range(len(uv)):
        u, v = int(round(uv[j, 0])), int(round(uv[j, 1]))
        if 0 <= u < width and 0 <= v < height:
            if depths[j] < depth_map[v, u]:
                depth_map[v, u] = depths[j]
    return depth_map


# ============================================================
# 桥接函数 — 连接 schemas 与 projection
# ============================================================

def compute_lidar_to_camera_extrinsic(
    lidar_pose_in_body: tuple[float, float, float, float, float, float, float],
    camera_pose_in_body: tuple[float, float, float, float, float, float, float],
) -> Tuple[np.ndarray, np.ndarray]:
    """从两个 Pose6DoF 体学位姿计算 LiDAR→Camera 外参 (R, T)。"""
    R_lb = extrinsic_from_pose6dof(lidar_pose_in_body[:3], lidar_pose_in_body[3:])[0]
    T_lb = np.array(lidar_pose_in_body[:3], dtype=np.float64)
    T_body_lidar = build_transformation_matrix(R_lb, T_lb)

    R_cb = extrinsic_from_pose6dof(camera_pose_in_body[:3], camera_pose_in_body[3:])[0]
    T_cb = np.array(camera_pose_in_body[:3], dtype=np.float64)
    T_body_camera = build_transformation_matrix(R_cb, T_cb)

    try:
        T_lidar_camera = np.linalg.inv(T_body_camera) @ T_body_lidar
    except np.linalg.LinAlgError:
        return np.eye(3, dtype=np.float64), np.zeros(3, dtype=np.float64)

    return T_lidar_camera[:3, :3], T_lidar_camera[:3, 3]


def project_sensor_frame(
    sensor_frame,        # SensorFrame (Pydantic model)
    intrinsics: CameraIntrinsics,
    lidar_pose_in_body: Optional[list[float]] = None,
) -> dict:
    """
    将 SensorFrame 的 LiDAR 点云投影到所有相机。

    返回: {cam_idx: {"uv": (M,2), "depths": (M,), "proj_mask": (N,), "points_cam": (M,3)}}
    """
    from common.schemas import Pose6DoF

    if lidar_pose_in_body is None:
        lidar_pose_in_body = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]

    points = points_from_flat_list(
        sensor_frame.point_cloud.points,
        sensor_frame.point_cloud.point_count,
    )
    results = {}
    for cam_idx, cam_view in enumerate(sensor_frame.camera_views):
        if cam_view.image_data is None:
            continue
        cp = cam_view.camera_pose
        cam_pose_in_body = (
            cp.position.x, cp.position.y, cp.position.z,
            cp.rotation.qw, cp.rotation.qx, cp.rotation.qy, cp.rotation.qz,
        )
        R, T = compute_lidar_to_camera_extrinsic(
            tuple(lidar_pose_in_body), cam_pose_in_body,
        )
        uv, depths, mask = project_points_to_image(
            points, intrinsics.K, R, T, intrinsics.dist_coeff,
            intrinsics.image_width, intrinsics.image_height,
        )
        results[cam_idx] = {"uv": uv, "depths": depths, "proj_mask": mask,
                            "points_cam": points[mask] if mask.any() else np.empty((0, 3))}
    return results


def project_fused_frame_to_camera(
    fused_frame,          # FusedFrame (Pydantic model)
    intrinsics: CameraIntrinsics,
    camera_world_pose,    # Pose6DoF
) -> dict:
    """将世界系融合点云投影到指定相机。"""
    points_world = points_from_flat_list(
        fused_frame.points_world, fused_frame.point_count,
    )
    pos = [camera_world_pose.position.x, camera_world_pose.position.y, camera_world_pose.position.z]
    rot = [camera_world_pose.rotation.qw, camera_world_pose.rotation.qx,
           camera_world_pose.rotation.qy, camera_world_pose.rotation.qz]
    T_cw = pose_to_matrix(pos, rot)
    try:
        T_wc = np.linalg.inv(T_cw)
    except np.linalg.LinAlgError:
        return {}
    uv, depths, mask = project_points_to_image(
        points_world, intrinsics.K, T_wc[:3, :3], T_wc[:3, 3],
        intrinsics.dist_coeff, intrinsics.image_width, intrinsics.image_height,
    )
    return {"uv": uv, "depths": depths, "proj_mask": mask}


# ============================================================
# 反投影 — 2D → 3D
# ============================================================

def backproject_pixel_to_3d(
    u: float, v: float, depth: float,
    K: np.ndarray,
    R_cam_to_world: np.ndarray, T_cam_to_world: np.ndarray,
    dist_coeff: Optional[np.ndarray] = None,
) -> np.ndarray:
    """单像素反投影: 像素(u,v) + 深度 → 世界系 3D 点。"""
    if dist_coeff is not None and np.any(dist_coeff != 0):
        pts_undist = np.array([[[u, v]]], dtype=np.float32)
        pts_undist = _cv_undistort(pts_undist, K, dist_coeff)
        u_n, v_n = pts_undist[0, 0, 0], pts_undist[0, 0, 1]
    else:
        fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
        u_n, v_n = (u - cx) / fx, (v - cy) / fy

    point_cam = np.array([u_n * depth, v_n * depth, depth], dtype=np.float64)
    point_world = R_cam_to_world @ point_cam + T_cam_to_world
    return point_world


def backproject_bbox_to_3d(
    bbox_2d: list[float],          # [x1, y1, x2, y2]
    depth_map: np.ndarray,         # (H, W) 深度图
    K: np.ndarray,
    R_cam_to_world: np.ndarray, T_cam_to_world: np.ndarray,
    dist_coeff: Optional[np.ndarray] = None,
) -> list[float]:
    """
    2D 检测框 → 3D 缺陷位置估算。

    返回: [cx, cy, cz, width, height, depth] 或空列表
    """
    x1, y1, x2, y2 = [int(round(v)) for v in bbox_2d]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(depth_map.shape[1] - 1, x2), min(depth_map.shape[0] - 1, y2)
    if x2 <= x1 or y2 <= y1:
        return []

    roi = depth_map[y1:y2+1, x1:x2+1]
    valid = roi[np.isfinite(roi)]
    if len(valid) == 0:
        return []

    depth = float(np.median(valid))
    cu, cv = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    center_3d = backproject_pixel_to_3d(cu, cv, depth, K, R_cam_to_world, T_cam_to_world, dist_coeff)

    corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
    corner_3ds = [backproject_pixel_to_3d(c[0], c[1], depth, K, R_cam_to_world, T_cam_to_world, dist_coeff) for c in corners]
    w = float(max(abs(c[0] - center_3d[0]) for c in corner_3ds) * 2)
    h = float(max(abs(c[1] - center_3d[1]) for c in corner_3ds) * 2)

    return [float(center_3d[0]), float(center_3d[1]), float(center_3d[2]), w, h, depth]


def _cv_undistort(pts, K, dist_coeff):
    import cv2
    return cv2.undistortPoints(pts, K, dist_coeff, None, None, K)
