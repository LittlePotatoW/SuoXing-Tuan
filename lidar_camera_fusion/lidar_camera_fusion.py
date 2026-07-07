# ============================================================
# lidar_camera_fusion/lidar_camera_fusion.py
# LiDAR点云与相机图像参数对齐与融合核心模块
#
# 本模块独立于 SuoXing-Tuan 后端运行，但与以下模块对齐：
#   · backend/reconstruction/transform.py  — quat_to_rotation,
#     pose_to_matrix, transform_points（签名和公式一致）
#   · backend/reconstruction/fusion.py     — rotation_to_quat（即
#     _rotmat_to_quat，签名和公式一致）
#   · backend/reconstruction/schemas.py    — extrinsic_from_pose6dof
#     适配器桥接 Pose6DoF → (R, T)
#
# 功能:
#   1. 配置文件读取与参数解析
#   2. 激光雷达点云数据读取 (.pcd / .bin)
#   3. 图像数据读取 (.jpg / .png)
#   4. 3D 点云 → 2D 图像平面投影（相机内参 + 外参）
#   5. 融合结果可视化（JET 伪彩色 + alpha 混合）
#
# 依赖: numpy, opencv-python, pyyaml, open3d (可选)
#
# 用法:
#   from lidar_camera_fusion import LidarCameraFusion
#   fusion = LidarCameraFusion("config.yaml")
#   result = fusion.run()
#   cv2.imwrite("output.jpg", result)
# ============================================================

import os
import sys
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import numpy as np
import cv2
import yaml

# ---------------------------------------------------------------------------
# 尝试导入 open3d；若未安装则回退为纯 numpy 的 PCD 读取
# ---------------------------------------------------------------------------
try:
    import open3d as o3d
    _HAS_OPEN3D = True
except ImportError:
    _HAS_OPEN3D = False


# ============================================================================
# 1. 配置文件加载
# ============================================================================

def load_config(config_path: str) -> Dict[str, Any]:
    """从 YAML 配置文件加载全部参数。

    自动将所有以 ``_path`` 结尾的相对路径字段转换为相对于
    配置文件所在目录的绝对路径，省去手动拼接的麻烦。

    Args:
        config_path: YAML 配置文件的路径。

    Returns:
        解析后的参数字典（所有路径已转为绝对路径）。
    """
    config_path = Path(config_path).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # ---- 递归解析所有以 _path 结尾的相对路径 ----
    def _resolve_paths(obj, base_dir: Path):
        """递归遍历配置树，将相对路径转为绝对路径。"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and key.endswith("_path"):
                    p = Path(value)
                    if not p.is_absolute():
                        obj[key] = str(base_dir / p)
                elif isinstance(value, (dict, list)):
                    _resolve_paths(value, base_dir)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    _resolve_paths(item, base_dir)

    _resolve_paths(config, config_path.parent)
    return config


# ============================================================================
# 2. 相机内参与外参处理
# ============================================================================

def build_intrinsic_matrix(K_list: list) -> np.ndarray:
    """将配置文件中的 K 列表转换为 3x3 numpy 数组。

    Args:
        K_list: 3x3 嵌套列表，格式 [[fx,0,cx],[0,fy,cy],[0,0,1]]

    Returns:
        (3, 3) 相机内参矩阵，dtype=float64。
    """
    K = np.array(K_list, dtype=np.float64)
    if K.shape != (3, 3):
        raise ValueError(f"内参矩阵 K 的形状必须为 (3,3)，当前为 {K.shape}")
    return K


def euler_to_rotation(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """将欧拉角 (roll, pitch, yaw) 转换为 3x3 旋转矩阵。

    旋转顺序 ZYX（yaw → pitch → roll），即：
        R = Rz(yaw) @ Ry(pitch) @ Rx(roll)

    Args:
        roll:  绕 X 轴旋转角 (rad)
        pitch: 绕 Y 轴旋转角 (rad)
        yaw:   绕 Z 轴旋转角 (rad)

    Returns:
        (3, 3) 旋转矩阵。
    """
    cr, sr = np.cos(roll), np.sin(roll)
    Rx = np.array([[1.0, 0.0,  0.0],
                   [0.0,  cr,  -sr],
                   [0.0,  sr,   cr]])

    cp, sp = np.cos(pitch), np.sin(pitch)
    Ry = np.array([[cp,  0.0,  sp],
                   [0.0, 1.0, 0.0],
                   [-sp, 0.0,  cp]])

    cy, sy = np.cos(yaw), np.sin(yaw)
    Rz = np.array([[cy, -sy, 0.0],
                   [sy,  cy, 0.0],
                   [0.0, 0.0, 1.0]])

    return Rz @ Ry @ Rx


def build_extrinsic(ex_cfg: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """根据配置构建外参旋转矩阵 R 和平移向量 T。

    支持三种输入方式（优先级：quaternion > euler > matrix）：
      - use_quaternion=true: 填写四元数 [qw, qx, qy, qz]
      - use_euler=true:      填写欧拉角 (roll, pitch, yaw)，ZYX 顺序
      - 默认:                直接填写 3x3 旋转矩阵

    Args:
        ex_cfg: 配置文件中 extrinsic 部分的字典。

    Returns:
        (R, T): R 为 (3,3) 旋转矩阵, T 为 (3,) 平移向量 (单位: 米)。
    """
    T = np.array(ex_cfg["T"], dtype=np.float64).reshape(3)

    if ex_cfg.get("use_quaternion", False):
        # ★ 四元数模式 — 与 SuoXing-Tuan backend/reconstruction/transform.py 对齐
        q = ex_cfg["quaternion"]
        R = quat_to_rotation(q["qw"], q["qx"], q["qy"], q["qz"])
    elif ex_cfg.get("use_euler", False):
        euler = ex_cfg["euler"]
        R = euler_to_rotation(euler["roll"], euler["pitch"], euler["yaw"])
    else:
        R = np.array(ex_cfg["R"], dtype=np.float64)
        if R.shape != (3, 3):
            raise ValueError(f"旋转矩阵 R 的形状必须为 (3,3)，当前为 {R.shape}")

    return R, T


# ---- 2b. 四元数工具 — 与 SuoXing-Tuan backend/reconstruction/transform.py 对齐 ----

def quat_to_rotation(qw: float, qx: float, qy: float, qz: float) -> np.ndarray:
    """四元数 → 3×3 旋转矩阵。

    签名和公式与 backend/reconstruction/transform.py:quat_to_rotation 完全一致。
    w 是实部: q = qw + qx·i + qy·j + qz·k

    Args:
        qw, qx, qy, qz: 四元数分量（w 为实部）。

    Returns:
        (3, 3) 旋转矩阵，dtype=float64。
    """
    return np.array([
        [1 - 2*qy**2 - 2*qz**2,  2*qx*qy - 2*qz*qw,      2*qx*qz + 2*qy*qw],
        [2*qx*qy + 2*qz*qw,      1 - 2*qx**2 - 2*qz**2,  2*qy*qz - 2*qx*qw],
        [2*qx*qz - 2*qy*qw,      2*qy*qz + 2*qx*qw,      1 - 2*qx**2 - 2*qy**2],
    ], dtype=np.float64)


def rotation_to_quat(R: np.ndarray) -> list:
    """3×3 旋转矩阵 → 四元数 [qw, qx, qy, qz]。

    与 backend/reconstruction/fusion.py:_rotmat_to_quat 对齐。
    用于将旋转矩阵转为 SuoXing-Tuan 的四元数格式输出。

    Args:
        R: (3, 3) 旋转矩阵。

    Returns:
        [qw, qx, qy, qz] 四元数列表。
    """
    trace = np.trace(R)
    if trace > 0:
        s = np.sqrt(trace + 1.0) * 2
        qw = 0.25 * s
        qx = (R[2, 1] - R[1, 2]) / s
        qy = (R[0, 2] - R[2, 0]) / s
        qz = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        qw = (R[2, 1] - R[1, 2]) / s
        qx = 0.25 * s
        qy = (R[0, 1] + R[1, 0]) / s
        qz = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        qw = (R[0, 2] - R[2, 0]) / s
        qx = (R[0, 1] + R[1, 0]) / s
        qy = 0.25 * s
        qz = (R[1, 2] + R[2, 1]) / s
    else:
        s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        qw = (R[1, 0] - R[0, 1]) / s
        qx = (R[0, 2] + R[2, 0]) / s
        qy = (R[1, 2] + R[2, 1]) / s
        qz = 0.25 * s
    return [qw, qx, qy, qz]


def pose_to_matrix(position: list, rotation_quat: list) -> np.ndarray:
    """位姿 (位置 + 四元数) → 4×4 齐次变换矩阵。

    与 backend/reconstruction/transform.py:pose_to_matrix 完全对齐。

    Args:
        position:      [x, y, z] (单位: 米)
        rotation_quat: [qw, qx, qy, qz]

    Returns:
        [[R, t],
         [0, 1]]  形状 (4, 4)
    """
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = quat_to_rotation(*rotation_quat)
    T[:3, 3] = position
    return T


def transform_points(points: np.ndarray, T: np.ndarray) -> np.ndarray:
    """对 (N, 3) 点云做 4×4 齐次坐标变换。

    与 backend/reconstruction/transform.py:transform_points 完全对齐。

    原理: P' = R @ P + t，等价于 [P';1] = T @ [P;1]

    Args:
        points: (N, 3) 点坐标。
        T:      4×4 齐次变换矩阵。

    Returns:
        (N, 3) 变换后的点坐标。
    """
    if points.size == 0:
        return points
    ones = np.ones((points.shape[0], 1), dtype=np.float64)
    homogeneous = np.hstack([points, ones])
    transformed = (T @ homogeneous.T).T
    return transformed[:, :3]


def build_transformation_matrix(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    """用旋转矩阵 R 和平移向量 t 构建 4×4 齐次变换矩阵。

    这是 pose_to_matrix 的矩阵版本 — 当已有 3×3 R 时使用。

    Args:
        R: (3, 3) 旋转矩阵。
        t: (3,) 平移向量。

    Returns:
        4×4 齐次变换矩阵。
    """
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


# ---- 2c. 适配器 — 桥接 SuoXing-Tuan Pydantic 数据模型 ----

def extrinsic_from_pose6dof(
    position: list,       # [x, y, z]
    rotation_quat: list,  # [qw, qx, qy, qz]
) -> Tuple[np.ndarray, np.ndarray]:
    """从 SuoXing-Tuan 的 Pose6DoF 格式提取 R 和 T。

    在 SuoXing-Tuan 中，外参以 Pose6DoF(position=Vector3, rotation=Quaternion)
    的形式存储在 CameraView.camera_pose 中。此函数将其转为我们的 (R, T) 格式。

    用法:
      from reconstruction.schemas import CameraView
      R, T = extrinsic_from_pose6dof(
          [cam.camera_pose.position.x, ...],
          [cam.camera_pose.rotation.qw, ...],
      )

    Args:
        position:     位置 [x, y, z] (m)。
        rotation_quat: 旋转四元数 [qw, qx, qy, qz]。

    Returns:
        (R, T): R (3,3), T (3,)
    """
    R = quat_to_rotation(*rotation_quat)
    T = np.array(position, dtype=np.float64)
    return R, T


# ============================================================================
# 3. 点云读取
# ============================================================================

def read_pointcloud(file_path: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """读取点云文件，返回 XYZ 坐标与可选的强度值。

    支持格式:
      - .pcd: 通过 open3d 或纯 Python 回退解析
      - .bin: KITTI 格式 (每点 4 个 float32: x, y, z, intensity)

    Args:
        file_path: 点云文件路径。

    Returns:
        (points, intensity):
          - points:    (N, 3) 点云 XYZ 坐标 (单位: 米)
          - intensity: (N,) 强度值；若格式不支持强度则为 None
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pcd":
        return _read_pcd(file_path)
    elif ext == ".bin":
        return _read_bin(file_path)
    else:
        raise ValueError(f"不支持的点云格式: {ext}（支持的格式: .pcd, .bin）")


def _read_pcd(file_path: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """读取 .pcd 文件（优先使用 open3d，失败时回退为纯 Python 解析）。"""
    if _HAS_OPEN3D:
        pcd = o3d.io.read_point_cloud(file_path)
        points = np.asarray(pcd.points, dtype=np.float64)
        if len(points) == 0:
            raise RuntimeError(f"open3d 未能从文件中读取到任何点: {file_path}")

        # 尝试读取强度/颜色信息
        intensity = None
        if pcd.has_colors():
            # 将 RGB 颜色转为灰度作为伪强度
            colors = np.asarray(pcd.colors, dtype=np.float64)
            intensity = 0.299 * colors[:, 0] + 0.587 * colors[:, 1] + 0.114 * colors[:, 2]
        return points, intensity
    else:
        # 纯 Python 回退：仅支持 ASCII PCD 且包含 x y z 字段
        points = _read_pcd_fallback(file_path)
        return points, None


def _read_pcd_fallback(file_path: str) -> np.ndarray:
    """纯 Python 解析 ASCII PCD 文件（无 open3d 时的回退方案）。

    仅处理 FIELDS 包含 x y z 的 ASCII 格式。
    """
    points = []
    in_data = False
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DATA"):
                in_data = True
                continue
            if in_data and line and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 3:
                    points.append([float(parts[0]), float(parts[1]), float(parts[2])])

    if not points:
        raise RuntimeError(
            f"纯 Python 回退无法解析该 PCD 文件: {file_path}\n"
            f"建议安装 open3d: pip install open3d"
        )
    return np.array(points, dtype=np.float64)


def _read_bin(file_path: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """读取 KITTI 格式 .bin 点云文件，每点 4 个 float32 (x, y, z, intensity)。"""
    data = np.fromfile(file_path, dtype=np.float32)
    if len(data) % 4 != 0:
        raise ValueError(f".bin 文件大小不是 4×float32 的整数倍: {file_path}")
    points = data.reshape(-1, 4)
    return points[:, :3].astype(np.float64), points[:, 3].astype(np.float64)


# ============================================================================
# 4. 图像读取
# ============================================================================

def read_image(file_path: str) -> np.ndarray:
    """读取图像文件，返回 BGR 格式的 numpy 数组。

    Args:
        file_path: 图像文件路径 (.jpg, .png 等)。

    Returns:
        (H, W, 3) BGR 图像。
    """
    img = cv2.imread(file_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"无法读取图像文件: {file_path}")
    return img


# ============================================================================
# 5. 点云过滤
# ============================================================================

def filter_pointcloud(
    points: np.ndarray,
    filter_cfg: Dict[str, Any],
    R: np.ndarray,
    T: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """根据配置过滤点云中的无效点，同时返回掩码以同步关联数据。

    过滤规则:
      1. 距离过滤：仅保留 range_min ~ range_max 范围内的点。
      2. FOV 过滤：仅保留位于相机前方的点 (Z_cam > 0)。

    Args:
        points:     (N, 3) 点云 (LiDAR 坐标系)。
        filter_cfg: 过滤参数字典。
        R:          外参旋转矩阵。
        T:          外参平移向量。

    Returns:
        (filtered_points, keep_mask):
          - filtered_points: (M, 3) 过滤后点云
          - keep_mask:       (N,) 布尔掩码，用于同步过滤强度等关联数据
    """
    N = len(points)
    mask = np.ones(N, dtype=bool)

    # --- 距离过滤（基于 LiDAR 坐标系原点） ---
    if filter_cfg.get("enable_range_filter", True):
        r_min = filter_cfg["range_min"]
        r_max = filter_cfg["range_max"]
        distances = np.linalg.norm(points, axis=1)
        mask &= (distances >= r_min) & (distances <= r_max)

    # --- FOV 过滤：仅保留相机前方 Z > 0 的点 ---
    if filter_cfg.get("enable_fov_filter", True):
        # 变换到相机坐标系后检查 Z 分量
        T_lidar_to_cam = build_transformation_matrix(R, T)
        points_cam = transform_points(points, T_lidar_to_cam)
        mask &= points_cam[:, 2] > 0.0

    return points[mask], mask


# ============================================================================
# 6. 点云投影（核心算法）
# ============================================================================

def project_points_to_image(
    points: np.ndarray,
    K: np.ndarray,
    R: np.ndarray,
    T: np.ndarray,
    dist_coeff: np.ndarray,
    image_width: int,
    image_height: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """将 LiDAR 坐标系下的 3D 点投影到 2D 图像平面上。

    投影管线（4 步）:
      1. 刚体变换:  P_cam = R @ P_lidar + T    (LiDAR → 相机坐标系)
      2. 透视投影:  (x_norm, y_norm) = (X/Z, Y/Z)   (归一化平面)
      3. 畸变校正:  对归一化坐标施加径向+切向畸变 (OpenCV 标准模型)
      4. 内参映射:  (u, v) = (fx*x_dist + cx, fy*y_dist + cy)

    关于 Z > 0 的说明：
      虽然 filter_pointcloud 的 FOV 过滤已剔除 Z ≤ 0 的点，但本函数
      仍保留 Z > 0 检查作为安全网 —— 当用户关闭 FOV 过滤时依然正确。

    Args:
        points:       (N, 3) LiDAR 坐标系下的点云（建议预先过滤）。
        K:            (3, 3) 相机内参矩阵。
        R:            (3, 3) 旋转矩阵 (LiDAR → 相机)。
        T:            (3,)   平移向量 (LiDAR → 相机)，单位: 米。
        dist_coeff:   (5,) 畸变系数 [k1, k2, p1, p2, k3]。
        image_width:  图像宽度 (像素)。
        image_height: 图像高度 (像素)。

    Returns:
        (uv_valid, depths_valid, valid_mask):
          - uv_valid:     (M, 2) 落在图像范围内的像素坐标 (u, v)
          - depths_valid: (M,)   对应的深度值 Z (相机坐标系)
          - valid_mask:   (N,)   布尔掩码，标记所有成功投影的点
                           （Z>0 且 落在图像内）
    """
    # ---- 步骤 1: 刚体变换 LiDAR → 相机坐标系 ----
    # 使用与 SuoXing-Tuan backend/reconstruction/transform.py 对齐的
    # transform_points() → 内部等价于 P_cam = R @ P_lidar + T
    T_lidar_to_cam = build_transformation_matrix(R, T)
    points_cam = transform_points(points, T_lidar_to_cam)  # (N, 3)
    X = points_cam[:, 0]
    Y = points_cam[:, 1]
    Z_cam = points_cam[:, 2]

    # ---- 步骤 2: 安全网 — 仅保留相机前方的点 ----
    front = Z_cam > 0.0
    if not np.any(front):
        return np.empty((0, 2)), np.empty(0), np.zeros(len(points), dtype=bool)

    # 只对前方点继续计算（减少后续运算量）
    X_f, Y_f, Z_f = X[front], Y[front], Z_cam[front]
    front_indices = np.where(front)[0]

    # ---- 步骤 3: 归一化平面投影 ----
    x_norm = X_f / Z_f
    y_norm = Y_f / Z_f

    # ---- 步骤 4: 畸变校正 (OpenCV 标准模型) ----
    k1, k2, p1, p2, k3 = dist_coeff
    r2 = x_norm ** 2 + y_norm ** 2
    r4 = r2 * r2
    r6 = r4 * r2

    # 径向畸变: 1 + k1*r^2 + k2*r^4 + k3*r^6
    radial = 1.0 + k1 * r2 + k2 * r4 + k3 * r6

    # 切向畸变
    two_p1_xy = 2.0 * p1 * x_norm * y_norm
    two_p2_xy = 2.0 * p2 * x_norm * y_norm
    x_dist = x_norm * radial + two_p1_xy + p2 * (r2 + 2.0 * x_norm ** 2)
    y_dist = y_norm * radial + p1 * (r2 + 2.0 * y_norm ** 2) + two_p2_xy

    # ---- 步骤 5: 内参映射到像素坐标 ----
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]

    u = fx * x_dist + cx
    v = fy * y_dist + cy

    # ---- 步骤 6: 边界裁剪 ----
    in_img = (u >= 0.0) & (u < image_width) & (v >= 0.0) & (v < image_height)

    # 构造最终结果
    final_indices = front_indices[in_img]
    valid_mask = np.zeros(len(points), dtype=bool)
    valid_mask[final_indices] = True

    uv_valid = np.column_stack([u[in_img], v[in_img]])
    depths_valid = Z_f[in_img]

    return uv_valid, depths_valid, valid_mask


# ============================================================================
# 7. 可视化
# ============================================================================

def color_map_distance(
    depths: np.ndarray,
    d_min: Optional[float] = None,
    d_max: Optional[float] = None,
) -> np.ndarray:
    """根据深度值生成 JET 伪彩色 (BGR)，用于按距离着色。

    近处 (红) → 远处 (蓝)。

    Args:
        depths: (N,) 深度值数组。
        d_min:  最小深度 (None 则取 5% 分位数)。
        d_max:  最大深度 (None 则取 95% 分位数)。

    Returns:
        (N, 3) uint8 BGR 颜色数组。
    """
    d_min = d_min if d_min is not None else np.percentile(depths, 5)
    d_max = d_max if d_max is not None else np.percentile(depths, 95)

    # 归一化到 0-1，clip 处理离群值
    norm = np.clip((depths - d_min) / max(d_max - d_min, 1e-8), 0.0, 1.0)

    # JET 色图: H ∈ [0, 120], 红(0) → 绿(60) → 蓝(120)
    hue = ((1.0 - norm) * 120.0).astype(np.uint8)
    hsv = np.zeros((len(depths), 3), dtype=np.uint8)
    hsv[:, 0] = hue
    hsv[:, 1] = 255
    hsv[:, 2] = 200

    # HSV → BGR (OpenCV 要求 H×W×3 输入)
    bgr = cv2.cvtColor(hsv.reshape(1, -1, 3), cv2.COLOR_HSV2BGR)
    return bgr.reshape(-1, 3)


# ---- 7b. 高效的散点绘制 ----

def _scatter_points(
    image: np.ndarray,
    uv: np.ndarray,
    colors: np.ndarray,
    radius: int,
) -> np.ndarray:
    """将带颜色的点高效地绘制到图像叠加层上。

    根据半径大小选择策略：
      - radius ≤ 1: 直接 numpy 数组索引（瞬时完成，适合数十万点）
      - radius > 1: 预计算圆形 kernel 后逐点 stamp（比 cv2.circle 循环
        快约 3-5 倍，因为省去 Python 级函数调用的开销）

    Args:
        image:  (H, W, 3) 目标图像。
        uv:     (M, 2) 像素坐标 (u, v)，应为整数。
        colors: (M, 3) uint8 BGR 颜色。
        radius: 绘制半径 (像素)。

    Returns:
        绘制后的图像（直接修改传入的 image 副本）。
    """
    h, w = image.shape[:2]
    overlay = image.copy()

    # 四舍五入取整
    u_arr = np.round(uv[:, 0]).astype(int)
    v_arr = np.round(uv[:, 1]).astype(int)

    # 边界裁剪（安全网，正常情况下调用方已过滤）
    valid = (u_arr >= 0) & (u_arr < w) & (v_arr >= 0) & (v_arr < h)
    if not np.any(valid):
        return overlay

    u_arr = u_arr[valid]
    v_arr = v_arr[valid]
    colors = colors[valid]

    # ---- 小半径: 直接像素赋值（瞬时 O(N)） ----
    if radius <= 1:
        overlay[v_arr, u_arr] = colors
        return overlay

    # ---- 大半径: 预计算圆形 kernel，逐点 stamp ----
    r = radius
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    inside = (xx ** 2 + yy ** 2) <= r ** 2
    cy, cx = yy[inside], xx[inside]  # 相对中心坐标

    for i in range(len(u_arr)):
        uc, vc = u_arr[i], v_arr[i]
        py = vc + cy
        px = uc + cx
        in_bounds = (py >= 0) & (py < h) & (px >= 0) & (px < w)
        if np.any(in_bounds):
            overlay[py[in_bounds], px[in_bounds]] = colors[i]

    return overlay


def render_fusion(
    image: np.ndarray,
    uv: np.ndarray,
    depths: np.ndarray,
    vis_cfg: Dict[str, Any],
) -> np.ndarray:
    """将投影后的点云叠加到图像上，生成融合可视化结果。

    Args:
        image:   (H, W, 3) 原始 BGR 图像。
        uv:      (M, 2) 投影点像素坐标。
        depths:  (M,) 每个投影点对应的深度。
        vis_cfg: 可视化参数字典。

    Returns:
        融合后的 BGR 图像。
    """
    color_mode = vis_cfg.get("color_map", "distance")
    alpha = float(vis_cfg.get("alpha", 0.6))
    radius = int(vis_cfg.get("point_radius", 2))

    # ---- 根据着色模式选择颜色表 ----
    if color_mode == "distance":
        colors = color_map_distance(depths)
    elif color_mode == "intensity":
        # 强度模式：沿用深度着色作为 fallback（强度通过外部传入）
        colors = color_map_distance(depths)
    elif color_mode == "solid":
        solid_bgr = vis_cfg.get("solid_color", [0, 255, 0])
        colors = np.tile(np.array(solid_bgr, dtype=np.uint8), (len(uv), 1))
    else:
        # 默认 fallback
        colors = color_map_distance(depths)

    # ---- 使用向量化绘制叠加层 ----
    overlay = _scatter_points(image, uv, colors, radius)

    # ---- Alpha 混合 ----
    fused = cv2.addWeighted(overlay, alpha, image, 1.0 - alpha, 0.0)

    # ---- 距离颜色图例 ----
    if vis_cfg.get("show_distance_legend", True) and color_mode in ("distance", "intensity"):
        fused = _draw_distance_legend(fused, depths)

    return fused


def _draw_distance_legend(image: np.ndarray, depths: np.ndarray) -> np.ndarray:
    """在图像右上角绘制深度颜色条图例。

    Args:
        image:  输入 BGR 图像（原地修改后返回）。
        depths: 深度数组（用于获取范围）。

    Returns:
        带图例的 BGR 图像。
    """
    h, w = image.shape[:2]
    bar_w, bar_h = 20, 200
    margin = 30

    x0 = w - margin - bar_w - 60
    y0 = margin
    d_min = np.percentile(depths, 5)
    d_max = np.percentile(depths, 95)

    # 绘制渐变色条（从远(蓝)到近(红)）
    for dy in range(bar_h):
        norm = dy / bar_h               # 0=远(蓝), 1=近(红)
        hue = int(norm * 120)           # 蓝(0) → 红(120)
        color_bgr = cv2.cvtColor(
            np.uint8([[[hue, 255, 200]]]), cv2.COLOR_HSV2BGR
        ).flatten()
        cv2.line(image, (x0, y0 + dy), (x0 + bar_w, y0 + dy),
                 color_bgr.tolist(), 1)

    # 标签
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(image, f"{d_max:.1f}m", (x0 + bar_w + 5, y0 + 12),
                font, 0.45, (200, 200, 200), 1)
    cv2.putText(image, f"{d_min:.1f}m", (x0 + bar_w + 5, y0 + bar_h),
                font, 0.45, (200, 200, 200), 1)
    cv2.putText(image, "Depth", (x0, y0 - 8),
                font, 0.5, (200, 200, 200), 1)

    return image


# ============================================================================
# 8. 主流程封装
# ============================================================================

class LidarCameraFusion:
    """LiDAR-相机融合处理流水线。

    使用方法::

        fusion = LidarCameraFusion("config.yaml")
        result_img = fusion.run()
        cv2.imwrite("output.jpg", result_img)

    也可以分步调用::

        fusion = LidarCameraFusion("config.yaml")
        points, intensity = fusion.load_pointcloud()
        image = fusion.load_image()
        points_f, mask = filter_pointcloud(points, cfg["filter"], fusion.R, fusion.T)
        uv, depths, proj_mask = project_points_to_image(points_f, ...)
        result = render_fusion(image, uv, depths, cfg["visualization"])
    """

    def __init__(self, config_path: str):
        """初始化融合流水线，加载并解析所有参数。

        Args:
            config_path: YAML 配置文件路径。
        """
        self.config = load_config(config_path)
        self._setup()

    def _setup(self):
        """从配置字典中解析各模块参数。"""
        cfg = self.config

        # 相机内参
        self.K = build_intrinsic_matrix(cfg["camera"]["K"])
        self.dist_coeff = np.array(cfg["camera"]["dist_coeff"], dtype=np.float64)
        self.img_w = cfg["camera"]["image_width"]
        self.img_h = cfg["camera"]["image_height"]

        # 外参
        self.R, self.T = build_extrinsic(cfg["extrinsic"])

        # 参数合法性校验
        if len(self.dist_coeff) != 5:
            raise ValueError(
                "dist_coeff 必须包含 5 个参数: [k1, k2, p1, p2, k3]"
            )

    # ---- 分步接口（方便调试与复用） ----

    def load_pointcloud(self) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """读取配置文件指定的点云文件。

        Returns:
            (points, intensity): points 为 (N,3) XYZ 坐标，intensity 可能为 None。
        """
        path = self.config["input"]["pointcloud_path"]
        print(f"[1/4] 读取点云: {path}")
        points, intensity = read_pointcloud(path)
        print(f"      读取到 {len(points)} 个点")
        return points, intensity

    def load_image(self) -> np.ndarray:
        """读取配置文件指定的图像文件。

        Returns:
            (H, W, 3) BGR 图像。
        """
        path = self.config["input"]["image_path"]
        print(f"[2/4] 读取图像: {path}")
        img = read_image(path)
        print(f"      图像尺寸: {img.shape[1]} x {img.shape[0]}")
        return img

    def run(self) -> np.ndarray:
        """执行完整的 LiDAR-相机融合流程。

        步骤:
          1. 读取点云 + 图像
          2. 过滤无效点
          3. 3D → 2D 投影
          4. 渲染融合结果并保存

        Returns:
            融合后的 BGR 图像。
        """
        cfg = self.config

        # 确保输出目录存在
        out_dir = Path(cfg["output"]["result_path"]).parent
        out_dir.mkdir(parents=True, exist_ok=True)

        # ---- 步骤 1: 读取数据 ----
        points, intensity = self.load_pointcloud()
        image = self.load_image()

        # ---- 步骤 2: 过滤 ----
        print("[3/4] 过滤无效点...")
        points, keep_mask = filter_pointcloud(
            points, cfg["filter"], self.R, self.T,
        )
        print(f"      过滤后剩余 {len(points)} 个点")
        if intensity is not None:
            intensity = intensity[keep_mask]

        if len(points) == 0:
            print("[警告] 过滤后无有效点，请检查过滤参数或外参配置。")
            return image

        # ---- 步骤 3: 投影 ----
        print("[4/4] 投影点云到图像平面...")
        uv, depths, proj_mask = project_points_to_image(
            points, self.K, self.R, self.T,
            self.dist_coeff, self.img_w, self.img_h,
        )
        print(f"      有效投影点: {len(uv)}")

        if len(uv) == 0:
            print("[警告] 未找到任何落在图像范围内的投影点，请检查内外参配置。")
            return image

        # ---- 步骤 4: 渲染 ----
        result = render_fusion(image, uv, depths, cfg["visualization"])

        # 保存结果
        out_path = cfg["output"]["result_path"]
        cv2.imwrite(out_path, result)
        print(f"\n融合结果已保存至: {out_path}")

        # 可选：保存带颜色的点云
        if cfg["output"].get("save_colored_pcd", False) and _HAS_OPEN3D:
            self._save_colored_pcd(points, proj_mask, depths, intensity)

        return result

    def _save_colored_pcd(
        self,
        points: np.ndarray,
        proj_mask: np.ndarray,
        depths: np.ndarray,
        intensity: Optional[np.ndarray] = None,
    ):
        """保存带有投影颜色信息的点云文件（需要 open3d）。

        投影成功的点按距离着色，未投影成功的点保留灰色。
        若有强度数据则优先使用强度着色。

        Args:
            points:     (N, 3) 过滤后的点云。
            proj_mask:  (N,) 布尔掩码，标记投影成功的点。
            depths:     (M,) 投影成功的点的深度值。
            intensity:  (N,) 或 None，点云强度值。
        """
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)

        # 默认灰色（未投影点）
        all_colors = np.full((len(points), 3), 0.5, dtype=np.float64)

        if proj_mask.any():
            if intensity is not None:
                # 用强度值做灰度着色
                i_vals = intensity[proj_mask]
                i_norm = np.clip(
                    (i_vals - i_vals.min()) / max(i_vals.max() - i_vals.min(), 1e-8),
                    0.0, 1.0,
                )
                colors_for_proj = np.column_stack([i_norm, i_norm, i_norm])
            else:
                # 按距离着色 (BGR → RGB)
                bgr = color_map_distance(depths)
                colors_for_proj = bgr[:, ::-1] / 255.0  # BGR→RGB, 0-255→0-1
            all_colors[proj_mask] = colors_for_proj

        pcd.colors = o3d.utility.Vector3dVector(all_colors)

        out_pcd = Path(self.config["output"]["result_path"]).with_suffix(".pcd")
        o3d.io.write_point_cloud(str(out_pcd), pcd)
        print(f"带颜色的点云已保存至: {out_pcd}")


# ============================================================================
# 命令行入口
# ============================================================================

def main():
    """命令行入口：从首个参数获取配置文件路径并执行融合。

    用法::

        python lidar_camera_fusion.py                    # 使用 ./config.yaml
        python lidar_camera_fusion.py path/to/config.yaml # 指定配置文件
    """
    if len(sys.argv) < 2:
        config_path = Path(__file__).parent / "config.yaml"
    else:
        config_path = sys.argv[1]

    print("=" * 60)
    print("  LiDAR-Camera Fusion — 激光雷达与相机数据融合")
    print("=" * 60)
    print(f"配置文件: {config_path}\n")

    fusion = LidarCameraFusion(str(config_path))
    fusion.run()

    print("\n完成。")


if __name__ == "__main__":
    main()
