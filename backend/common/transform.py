# ============================================================
# backend/common/transform.py
# 坐标变换 + 数学工具 — 统一来源，消除代码重复
# ============================================================

import math as _math
import numpy as np


# ============================================================
# 四元数 / 旋转矩阵
# ============================================================

def quat_to_rotation(qw: float, qx: float, qy: float, qz: float) -> np.ndarray:
    """四元数 → 3x3 旋转矩阵。带归一化。"""
    norm = _math.sqrt(qw*qw + qx*qx + qy*qy + qz*qz)
    if norm > 1e-12:
        qw, qx, qy, qz = qw/norm, qx/norm, qy/norm, qz/norm
    R = np.array([
        [1 - 2*qy**2 - 2*qz**2,  2*qx*qy - 2*qz*qw,      2*qx*qz + 2*qy*qw],
        [2*qx*qy + 2*qz*qw,      1 - 2*qx**2 - 2*qz**2,  2*qy*qz - 2*qx*qw],
        [2*qx*qz - 2*qy*qw,      2*qy*qz + 2*qx*qw,      1 - 2*qx**2 - 2*qy**2],
    ], dtype=np.float64)
    return R


def rotation_to_quat(R: np.ndarray) -> list[float]:
    """3x3 旋转矩阵 → 四元数 [qw, qx, qy, qz]."""
    trace = float(np.trace(R))
    if trace > 0:
        s = _math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * s
        qx = (R[2, 1] - R[1, 2]) / s
        qy = (R[0, 2] - R[2, 0]) / s
        qz = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = _math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        qw = (R[2, 1] - R[1, 2]) / s
        qx = 0.25 * s
        qy = (R[0, 1] + R[1, 0]) / s
        qz = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = _math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        qw = (R[0, 2] - R[2, 0]) / s
        qx = (R[0, 1] + R[1, 0]) / s
        qy = 0.25 * s
        qz = (R[1, 2] + R[2, 1]) / s
    else:
        s = _math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        qw = (R[1, 0] - R[0, 1]) / s
        qx = (R[0, 2] + R[2, 0]) / s
        qy = (R[1, 2] + R[2, 1]) / s
        qz = 0.25 * s
    return [qw, qx, qy, qz]


def quat_to_yaw(qw: float, qx: float, qy: float, qz: float) -> float:
    """四元数 → yaw (绕 Z 轴旋转角, rad)."""
    siny = 2.0 * (qw * qz + qx * qy)
    cosy = 1.0 - 2.0 * (qy * qy + qz * qz)
    return _math.atan2(siny, cosy)


# ============================================================
# 位姿 / 变换矩阵
# ============================================================

def pose_to_matrix(position: list[float], rotation_quat: list[float]) -> np.ndarray:
    """位姿 (位置 + 四元数) → 4x4 齐次变换矩阵。"""
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = quat_to_rotation(*rotation_quat)
    T[:3, 3] = position
    return T


def transform_points(points: np.ndarray, T: np.ndarray) -> np.ndarray:
    """对 (N, 3) 点云做齐次坐标变换: P' = R@P + t."""
    if points.size == 0:
        return points
    ones = np.ones((points.shape[0], 1), dtype=np.float64)
    homogeneous = np.hstack([points, ones])
    transformed = (T @ homogeneous.T).T
    return transformed[:, :3]


def build_transformation_matrix(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    """构建 4x4 变换矩阵 [R t; 0 1]."""
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def extrinsic_from_pose6dof(position: tuple[float, float, float],
                            rotation_quat: tuple[float, float, float, float]
                            ) -> tuple[np.ndarray, np.ndarray]:
    """Pose6DoF → (R, T)，适配后端 schemas。"""
    R = quat_to_rotation(*rotation_quat)
    T = np.array(position, dtype=np.float64)
    return R, T


# ============================================================
# 坐标系变换 — 管线最常用
# ============================================================

def sensor_to_world(
    points_sensor: np.ndarray,
    sensor_pose_in_body: list[float],      # [x,y,z, qw,qx,qy,qz]
    car_pose_in_world: list[float],        # [x,y,z, qw,qx,qy,qz]
) -> np.ndarray:
    """一步完成: Sensor → World 坐标变换。"""
    T_SB = pose_to_matrix(sensor_pose_in_body[:3], sensor_pose_in_body[3:])
    T_BW = pose_to_matrix(car_pose_in_world[:3], car_pose_in_world[3:])
    T_SW = T_BW @ T_SB
    return transform_points(points_sensor, T_SW)


def camera_to_world(
    camera_pose_in_body: list[float],      # [x,y,z, qw,qx,qy,qz]
    car_pose_in_world: list[float],        # [x,y,z, qw,qx,qy,qz]
) -> np.ndarray:
    """计算相机在世界坐标系中的 4x4 位姿矩阵。"""
    T_BC = pose_to_matrix(camera_pose_in_body[:3], camera_pose_in_body[3:])
    T_BW = pose_to_matrix(car_pose_in_world[:3], car_pose_in_world[3:])
    return T_BW @ T_BC
