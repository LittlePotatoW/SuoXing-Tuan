# ============================================================
# backend/fusion/datafusion.py
# 数据融合管线 — 坐标变换 + 打包，SensorFrame → FusedFrame
# ============================================================
"""
数据流:
  SensorFrame (传感器坐标系)
      │
      ├─ 点云: sensor_to_world()  → 世界坐标系
      ├─ 相机: camera_to_world()  → 世界坐标系中的相机位姿
      └─ 图片: 透传
      │
      ▼
  FusedFrame (世界坐标系，直接喂给重建引擎)
"""

import logging
import numpy as np

from common.schemas import SensorFrame, FusedFrame, Pose6DoF, Vector3, Quaternion
from common.transform import sensor_to_world, camera_to_world

logger = logging.getLogger("fusion.datafusion")


class DataFusion:
    """
    数据融合器。
    每收到一个 SensorFrame → 变换坐标 → 输出一个 FusedFrame。
    """

    def __init__(self, sensor_pose_in_body: list[float] | None = None,
                 camera_intrinsics_list: list | None = None):
        """
        参数:
          sensor_pose_in_body: 激光雷达在小车上的安装位姿 [x,y,z, qw,qx,qy,z]
                               如果为 None，默认为原点（雷达装在车体原点）
          camera_intrinsics_list: 相机内参列表，每个元素需提供 .K, .dist_coeff,
                                  .image_width, .image_height。空列表或不传则跳过颜色采样
        """
        # 雷达外参: 雷达在车体坐标系中的位姿
        self.sensor_pose = sensor_pose_in_body or [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
        self.camera_intrinsics_list = camera_intrinsics_list or []

    def process(self, raw: SensorFrame) -> FusedFrame | None:
        """
        处理一帧原始数据 → 输出融合后的世界坐标系数据。

        返回 None 表示这一帧数据不完整，跳过。
        """
        # ── 校验 ──
        if raw.point_cloud is None or raw.car_position is None:
            logger.warning("Frame %s: missing point_cloud or car_position, skip", raw.frame_id)
            return None

        if raw.point_cloud.point_count == 0:
            logger.warning("Frame %s: empty point cloud, skip", raw.frame_id)
            return None

        # ── 取小车全局位姿 ──
        car_pose = raw.car_position.pose
        car_pos_list = [car_pose.position.x, car_pose.position.y, car_pose.position.z]
        car_rot_list = [car_pose.rotation.qw, car_pose.rotation.qx,
                        car_pose.rotation.qy, car_pose.rotation.qz]

        # ── 点云: 传感器 → 世界 ──
        points_np = np.array(raw.point_cloud.points, dtype=np.float64).reshape(-1, 3)
        points_world = sensor_to_world(points_np, self.sensor_pose, car_pos_list + car_rot_list)

        # ── 相机: 车体 → 世界 ──
        cameras_world: list[Pose6DoF] = []
        images: list[bytes] = []

        for cam_view in raw.camera_views:
            cam_pose = cam_view.camera_pose
            cam_pos = [cam_pose.position.x, cam_pose.position.y, cam_pose.position.z]
            cam_rot = [cam_pose.rotation.qw, cam_pose.rotation.qx,
                       cam_pose.rotation.qy, cam_pose.rotation.qz]

            T_cam_world = camera_to_world(cam_pos + cam_rot, car_pos_list + car_rot_list)

            # 从 4x4 矩阵提取位置和旋转
            cam_world_pos = T_cam_world[:3, 3].tolist()
            cam_world_rot_mat = T_cam_world[:3, :3]
            cam_world_quat = _rotmat_to_quat(cam_world_rot_mat)

            cameras_world.append(Pose6DoF(
                position=Vector3(x=cam_world_pos[0], y=cam_world_pos[1], z=cam_world_pos[2]),
                rotation=Quaternion(qw=cam_world_quat[0], qx=cam_world_quat[1],
                                    qy=cam_world_quat[2], qz=cam_world_quat[3]),
            ))

            if cam_view.image_data is not None:
                images.append(cam_view.image_data)
            else:
                images.append(None)  # 保持 images 和 cameras_world 索引对齐

        # ── 颜色采样: 世界系点云反投影到相机图像 ──
        point_colors: list[int] = []
        if self.camera_intrinsics_list and cameras_world and images:
            try:
                from fusion.coloring import sample_colors_from_cameras
                # 只用相机1 (与 LiDAR 对齐)
                colors_np = sample_colors_from_cameras(
                    points_world, cameras_world[:1], images[:1], self.camera_intrinsics_list[:1],
                )
                if colors_np is not None:
                    point_colors = colors_np.ravel().tolist()
                    logger.debug("Color sampling OK: %d points, %d colors",
                                 len(points_world), len(point_colors) // 3)
                else:
                    logger.warning("Color sampling returned None for frame %s (no points projected)", raw.frame_id)
            except Exception as exc:
                logger.warning("Color sampling failed for frame %s: %s", raw.frame_id, exc)
        else:
            if not self.camera_intrinsics_list:
                logger.debug("Color sampling skipped: no camera intrinsics configured")

        # ── 打包 FusedFrame ──
        fused = FusedFrame(
            frame_id=raw.frame_id,
            timestamp_ns=raw.timestamp_ns,
            points_world=points_world.ravel().tolist(),
            point_count=points_world.shape[0],
            cameras_world=cameras_world,
            images=images,
            point_colors=point_colors,
        )

        logger.debug("Frame %s: %d points → world, %d cameras",
                     raw.frame_id, fused.point_count, len(cameras_world))
        return fused


def _rotmat_to_quat(R: np.ndarray) -> list[float]:
    """
    3×3 旋转矩阵 → 四元数 [qw, qx, qy, qz]。
    用于从 4×4 矩阵中提取旋转。
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
