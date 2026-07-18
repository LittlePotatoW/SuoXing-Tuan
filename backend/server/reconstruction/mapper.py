# ============================================================
# backend/server/reconstruction/mapper.py
# 点云建图：多帧点云按位姿变换到世界坐标系后拼接
#
# 设计与用法:
#   导出 map_frames() 函数
#   输入: 点云列表 + 位姿列表 + config
#   输出: 世界坐标系下的合并点云 (N×3)
# ============================================================
#   坐标链: 相机 → 小车(camera_to_vehicle) → 世界(pose)
#   相机帧: Z前 X右 Y下 (OpenCV)
#   小车帧: X前 Y左 Z上 (ROS)
# ============================================================

import logging

import numpy as np

logger = logging.getLogger(__name__)


def map_frames(point_clouds: list[np.ndarray],
               positions: list[dict],
               config: dict) -> np.ndarray | None:
    """将多帧点云变换到世界坐标系后拼接

    Args:
        point_clouds: 每帧的点云 (N_i, 3), 相机坐标系, 单位米
        positions:   每帧对应的位姿 {x, y, heading(度)}
        config:      项目配置

    Returns:
        合并后的世界坐标系点云 (M, 3), 单位米; 无有效数据返回 None
    """
    if not point_clouds:
        return None

    extr = config.get('camera_to_vehicle', {})
    ext_rot = extr.get('rotation', [0.0, 0.0, 0.0])     # roll, pitch, yaw 度
    ext_trans = extr.get('translation', [0.0, 0.0, 0.0])  # x, y, z 米

    world_pcs = []
    for pc, pos in zip(point_clouds, positions):
        if pc is None or len(pc) == 0:
            continue
        try:
            transformed = _camera_to_world(pc, pos, ext_rot, ext_trans)
            world_pcs.append(transformed)
        except Exception:
            logger.exception("点云坐标变换失败")

    if not world_pcs:
        return None

    merged = np.vstack(world_pcs)
    logger.debug("map_frames: %d 帧 → %d 点", len(world_pcs), len(merged))
    return merged.astype(np.float32)


def _camera_to_world(pc: np.ndarray,
                     pose: dict,
                     ext_rot: list[float],
                     ext_trans: list[float]) -> np.ndarray:
    """单帧点云: 相机坐标系 → 世界坐标系

    pc: (N, 3) 相机坐标系 (X右 Y下 Z前, OpenCV)
    pose: {x, y, heading} 小车在世界中的位姿
    ext_rot: [roll, pitch, yaw] 度, 相机安装角(相机→小车)
    ext_trans: [x, y, z] 米,  相机安装位置(在小车坐标系中)
    """
    # Step 1: 相机坐标系 → 标准小车坐标系
    # 相机 Z前/X右/Y下 → 小车 X前/Y左/Z上
    # 即: X_v=Z_c, Y_v=-X_c, Z_v=-Y_c
    x_v = pc[:, 2]
    y_v = -pc[:, 0]
    z_v = -pc[:, 1]
    pc_vehicle = np.column_stack([x_v, y_v, z_v])

    # Step 2: 应用相机安装外参 (camera_to_vehicle)
    r, p, y = np.radians(ext_rot)
    R = _euler_to_rot(r, p, y)
    pc_vehicle = (R @ pc_vehicle.T).T
    pc_vehicle[:, 0] += ext_trans[0]
    pc_vehicle[:, 1] += ext_trans[1]
    pc_vehicle[:, 2] += ext_trans[2]

    # Step 3: 小车坐标系 → 世界坐标系 (2D 位姿)
    heading_rad = np.radians(pose['heading'])
    cos_h = np.cos(heading_rad)
    sin_h = np.sin(heading_rad)

    x_w = pose['x'] + pc_vehicle[:, 0] * cos_h - pc_vehicle[:, 1] * sin_h
    y_w = pose['y'] + pc_vehicle[:, 0] * sin_h + pc_vehicle[:, 1] * cos_h
    z_w = pc_vehicle[:, 2]  # 高度不变

    return np.column_stack([x_w, y_w, z_w])


def _euler_to_rot(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """欧拉角 → 3×3 旋转矩阵 (ZYX 顺规)"""
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)

    R = np.array([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp,     cp * sr,                cp * cr],
    ])
    return R
