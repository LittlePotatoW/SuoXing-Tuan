# ============================================================
# backend/common/camera.py
# 相机内参 / 外参构建 — 统一来源
# ============================================================

import math as _math
from dataclasses import dataclass

import numpy as np


@dataclass
class CameraIntrinsics:
    """相机内参（填补 CameraView 缺失的内参字段）。"""
    K: np.ndarray          # (3, 3) 内参矩阵
    dist_coeff: np.ndarray # (5,) 畸变系数 [k1, k2, p1, p2, k3]
    image_width: int
    image_height: int


# ============================================================
# 内参构建
# ============================================================

def build_intrinsic_matrix(K_list: list[list[float]]) -> np.ndarray:
    """从嵌套列表构建 3x3 内参矩阵。"""
    K = np.array(K_list, dtype=np.float64)
    if K.shape != (3, 3):
        raise ValueError(f"K must be 3x3, got {K.shape}")
    return K


# ============================================================
# 外参构建
# ============================================================

def euler_to_rotation(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """欧拉角 (ZYX 顺序, rad) → 3x3 旋转矩阵。"""
    cr, sr = _math.cos(roll), _math.sin(roll)
    cp, sp = _math.cos(pitch), _math.sin(pitch)
    cy, sy = _math.cos(yaw), _math.sin(yaw)

    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=np.float64)
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=np.float64)
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=np.float64)
    return Rz @ Ry @ Rx


def build_extrinsic(ex_cfg: dict) -> tuple[np.ndarray, np.ndarray]:
    """从配置字典构建外参 (R, T)。支持四元数 / 欧拉角 / 直接矩阵三种模式。"""
    T = np.array(ex_cfg.get("T", [0.0, 0.0, 0.0]), dtype=np.float64)

    if ex_cfg.get("use_quaternion", False):
        q = ex_cfg["quaternion"]
        from common.transform import quat_to_rotation
        R = quat_to_rotation(q["qw"], q["qx"], q["qy"], q["qz"])
    elif ex_cfg.get("use_euler", False):
        e = ex_cfg["euler"]
        R = euler_to_rotation(e["roll"], e["pitch"], e["yaw"])
    elif "R" in ex_cfg:
        R = np.array(ex_cfg["R"], dtype=np.float64)
    else:
        R = np.eye(3, dtype=np.float64)

    return R, T
