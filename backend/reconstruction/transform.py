"""
坐标变换 — 整个三维重建管线最底层的工具。

三套坐标系:
  Sensor  — 传感器自身（激光雷达或相机）
  Body    — 小车中心，原点在后轴中心，x前 y左 z上
  World   — 全局世界坐标系

变换链: Sensor → Body → World

使用方法:
  from common.schemas import Pose6DoF
  from common.transform import pose_to_matrix, transform_points

  # 1. 把位姿变成 4x4 矩阵
  T_SB = pose_to_matrix(sensor_pose)   # 传感器→车体
  T_BW = pose_to_matrix(car_pose)      # 车体→世界

  # 2. 把点云从传感器系变到世界系
  T_SW = T_BW @ T_SB                   # 连锁变换
  points_world = transform_points(points_sensor, T_SW)
"""

import numpy as np


def quat_to_rotation(qw: float, qx: float, qy: float, qz: float) -> np.ndarray:
    """
    四元数 → 3×3 旋转矩阵。
    输入: (qw, qx, qy, qz)，qw 是实部。
    输出: (3, 3) numpy 数组。
    """
    R = np.array([
        [1 - 2*qy**2 - 2*qz**2,  2*qx*qy - 2*qz*qw,      2*qx*qz + 2*qy*qw],
        [2*qx*qy + 2*qz*qw,      1 - 2*qx**2 - 2*qz**2,  2*qy*qz - 2*qx*qw],
        [2*qx*qz - 2*qy*qw,      2*qy*qz + 2*qx*qw,      1 - 2*qx**2 - 2*qy**2],
    ], dtype=np.float64)
    return R


def pose_to_matrix(position: list[float], rotation_quat: list[float]) -> np.ndarray:
    """
    位姿 (位置 + 四元数) → 4×4 齐次变换矩阵。

    参数:
      position:     [x, y, z]
      rotation_quat: [qw, qx, qy, qz]

    返回:
      [[R R R x],
       [R R R y],
       [R R R z],
       [0 0 0 1]]
    """
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = quat_to_rotation(*rotation_quat)
    T[:3, 3] = position
    return T


def transform_points(points: np.ndarray, T: np.ndarray) -> np.ndarray:
    """
    对 (N, 3) 点云做齐次坐标变换。

    参数:
      points: (N, 3) numpy 数组
      T:      4×4 变换矩阵

    返回:
      (N, 3) 变换后的点坐标

    原理:
      [P']   [R t]   [P]
      [1 ] = [0 1] × [1]
      对每个点做: P' = R@P + t
    """
    if points.size == 0:
        return points
    # 加一列 1，变成齐次坐标 (N, 4)
    ones = np.ones((points.shape[0], 1), dtype=np.float64)
    homogeneous = np.hstack([points, ones])
    # 矩阵乘法: (4,4) @ (4,N) → 需要转置
    transformed = (T @ homogeneous.T).T
    # 去掉最后一列，回到 (N, 3)
    return transformed[:, :3]


def sensor_to_world(
    points_sensor: np.ndarray,
    sensor_pose_in_body: list[float],    # 传感器在车体中的位姿 [x,y,z, qw,qx,qy,qz]
    car_pose_in_world: list[float],      # 小车在世界中的位姿 [x,y,z, qw,qx,qy,qz]
) -> np.ndarray:
    """
    一步完成: Sensor → World 坐标变换。

    P_world = T_BW @ T_SB @ P_sensor

    这是你最常用的函数——每收到一帧点云就调用一次。
    """
    T_SB = pose_to_matrix(sensor_pose_in_body[:3], sensor_pose_in_body[3:])
    T_BW = pose_to_matrix(car_pose_in_world[:3], car_pose_in_world[3:])
    T_SW = T_BW @ T_SB
    return transform_points(points_sensor, T_SW)


def camera_to_world(
    camera_pose_in_body: list[float],    # 相机在车体中的位姿 [x,y,z, qw,qx,qy,qz]
    car_pose_in_world: list[float],      # 小车在世界中的位姿
) -> np.ndarray:
    """
    计算相机在世界坐标系中的 4×4 位姿矩阵。

    T_camera_world = T_BW @ T_camera_body

    这个结果会传给重建引擎：它需要知道每张照片是从世界坐标的哪个位置拍的。
    """
    T_BC = pose_to_matrix(camera_pose_in_body[:3], camera_pose_in_body[3:])
    T_BW = pose_to_matrix(car_pose_in_world[:3], car_pose_in_world[3:])
    return T_BW @ T_BC
