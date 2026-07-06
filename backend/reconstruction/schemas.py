"""
V2 数据模型 — 三维重建管线的全部数据结构。

坐标系说明：详见 reconstruction/transform.py 顶部的注释。
"""

import time
import uuid
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# 1. 基础几何类型 — 所有位姿/向量的砖块
# ============================================================

class Vector3(BaseModel):
    """三维向量，带 to_list() 方便序列化"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]


class Quaternion(BaseModel):
    """四元数 (w, x, y, z)，表示旋转。w 是实部"""
    qw: float = 1.0
    qx: float = 0.0
    qy: float = 0.0
    qz: float = 0.0


class Pose6DoF(BaseModel):
    """六自由度位姿 = 位置 + 旋转"""
    position: Vector3 = Field(default_factory=Vector3)
    rotation: Quaternion = Field(default_factory=Quaternion)


# ============================================================
# 2. 传感器原始数据 — 硬件组上传的每一帧包含以下内容
# ============================================================

class PointCloudData(BaseModel):
    """
    单帧点云（激光雷达一帧的数据）。
    points: 扁平数组 [x0, y0, z0, x1, y1, z1, ...]
    坐标系: 传感器自身坐标系（后面会变换到世界系）
    """
    points: list[float] = Field(default_factory=list)
    point_count: int = 0           # = len(points) // 3


class CameraView(BaseModel):
    """
    单个相机的一帧: 图片 + 这个相机在车上的安装位姿。
    因为你有两个工业相机，所以每帧会有两个 CameraView。
    """
    image_data: Optional[bytes] = Field(default=None)   # JPEG 编码的图片
    width: int = 0
    height: int = 0
    # 相机在车体坐标系中的位姿（外参，由标定确定，通常是不变的）
    camera_pose: Pose6DoF = Field(default_factory=Pose6DoF)


class CarPosition(BaseModel):
    """小车在世界坐标系中的位姿"""
    pose: Pose6DoF = Field(default_factory=Pose6DoF)
    timestamp_ns: int = 0


class KinematicsData(BaseModel):
    """
    小车运动学参数。
    - velocity:       线速度 (m/s)
    - steering_angle: 转向角 (rad)
    - wheel_base:     轴距 (m)，航迹推算用
    """
    velocity: float = 0.0
    steering_angle: float = 0.0
    wheel_base: float = 1.5
    timestamp_ns: int = 0


# ============================================================
# 3. 上传帧 — 一次采集时刻打包所有传感器数据
# ============================================================

class SensorFrame(BaseModel):
    """
    硬件组每采集一次，就打包一个 SensorFrame 发给后端。
    包含：
      - 一帧点云
      - 两帧相机图像（两个工业相机）
      - 小车当前世界位姿
      - 运动学参数
    """
    frame_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp_ns: int = Field(default_factory=lambda: time.time_ns())

    point_cloud: Optional[PointCloudData] = None
    camera_views: list[CameraView] = Field(default_factory=list)  # 1个工业相机（可扩展多个）
    car_position: Optional[CarPosition] = None
    kinematics: Optional[KinematicsData] = None


# ============================================================
# 4. 融合帧 — Pipeline 输出，所有坐标已统一到世界系
# ============================================================

class FusedFrame(BaseModel):
    """
    坐标系统一后的数据帧，直接喂给重建引擎。
    点云和相机位姿都已经变换到了世界坐标系。
    """
    frame_id: str = ""
    timestamp_ns: int = 0

    # 世界坐标系中的点云（扁平 N*3）
    points_world: list[float] = Field(default_factory=list)
    point_count: int = 0

    # 世界坐标系中的相机（每个相机的外参 × 小车位姿 = 世界中的相机位姿）
    cameras_world: list[Pose6DoF] = Field(default_factory=list)
    images: list[bytes] = Field(default_factory=list)


# ============================================================
# 5. 表面重建结果 — 推送给前端渲染
# ============================================================

class MeshData(BaseModel):
    """三角网格 — 前端用 Three.js 渲染"""
    vertices: list[float] = Field(default_factory=list)   # 扁平 [x0,y0,z0, ...] N*3
    faces: list[int] = Field(default_factory=list)         # 扁平 [i0,i1,i2, ...] M*3
    vertex_count: int = 0
    face_count: int = 0


class CrackAnnotation(BaseModel):
    """裂缝标注 — 世界坐标系中的 3D 位置"""
    position: Vector3 = Field(default_factory=Vector3)
    confidence: float = 0.0
    crack_type: str = ""          # 裂缝类型
    image_frame_id: str = ""      # 从哪帧图像检出的


class ReconstructionResult(BaseModel):
    """
    推送给前端的完整重建结果。
    包含: 表面网格 + 裂缝标注列表 + 相机轨迹
    """
    status: str = "updating"

    # 表面重建的网格
    mesh: MeshData = Field(default_factory=MeshData)

    # 裂缝标注列表
    cracks: list[CrackAnnotation] = Field(default_factory=list)

    # 相机移动轨迹 [[x,y,z], [x,y,z], ...]
    camera_trail: list[list[float]] = Field(default_factory=list)

    # 简单统计
    total_frames: int = 0
    total_points: int = 0
