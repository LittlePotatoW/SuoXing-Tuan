# ============================================================
# backend/reconstruction/projector.py
# 缺陷坐标投影器 — 2D 检测框 → 3D 世界坐标
# ============================================================
#
#  坐标转换链:
#    2D 像素 (u, v)
#      → 相机局部 3D (利用内参 + 深度)
#      → 车体坐标系 (利用相机外参逆变换)
#      → 世界坐标系 (利用 car_position.pose)
#
#  对 SuoXing-Tuan 其他分支模块的整合:
#    - 使用 reconstruction.transform 中的一致变换约定
#    - 输出世界坐标可直接喂给 ReconstructionEngine.add_crack()
#    - 相机外参来自 location_data 的标定值
#    - 车体位姿来自 DataFusionManager 输出的航迹推算结果
# ============================================================

import math
import logging
from typing import Optional

import numpy as np
import cv2

logger = logging.getLogger("data_pre_processing.projector")


class DefectProjector:
    """
    缺陷投影器 — 将 AI 检测结果投影到世界坐标系。

    支持两种输入:
      1. 2D 像素坐标 (u, v) + 深度: 利用相机内参反算到局部3D
      2. 传感器局部 3D 坐标 (x, y, z): 直接做坐标系变换

    坐标系约定 (与 reconstruction/transform.py 一致):
      相机坐标系: +z 为光轴方向，+x 向右，+y 向下
      车体坐标系: +x 前，+y 左，+z 上
      世界坐标系: 全局基准

    对外接口:
      - project_pixel_defect(): 2D 像素 → 世界坐标
      - project_3d_defect(): 传感器局部 3D → 世界坐标
      - compute_world_coordinate(): 通用链式变换
    """

    def __init__(self, camera_intrinsics: Optional[dict[int, dict]] = None):
        """
        初始化缺陷投影器。

        参数:
          camera_intrinsics: 相机内参字典，按 camera_index 索引:
            {
              0: {"fx": 1000.0, "fy": 1000.0, "cx": 960.0, "cy": 540.0, "width": 1920, "height": 1080},
              1: {...},
            }
            若未提供，后续可调用 set_intrinsics() 设置。
            典型内参值（需硬件组标定后填入）:
              fx, fy: 焦距（像素单位）
              cx, cy: 主点坐标（像素单位）
              width, height: 图像分辨率
        """
        # ── 相机内参 {camera_index: {fx, fy, cx, cy, width, height}} ──
        self._intrinsics: dict[int, dict] = camera_intrinsics or {}

        # ── 默认内参（标定前的 fallback，后续用实际标定值覆盖） ──
        self._default_intrinsics = {
            "fx": 1000.0,
            "fy": 1000.0,
            "cx": 960.0,
            "cy": 540.0,
            "width": 1920,
            "height": 1080,
            "K": np.array([[1000.0, 0.0, 960.0],
                           [0.0, 1000.0, 540.0],
                           [0.0, 0.0, 1.0]], dtype=np.float64),
            "dist_coeff": np.zeros(5, dtype=np.float64),
        }

        logger.info("DefectProjector 初始化完成, %d 个相机内参已配置",
                    len(self._intrinsics))

    # ================================================================
    #  配置接口
    # ================================================================

    def set_intrinsics(self, camera_index: int, fx: float, fy: float,
                       cx: float, cy: float, width: int = 1920,
                       height: int = 1080,
                       K: np.ndarray | None = None,
                       dist_coeff: np.ndarray | None = None) -> None:
        """
        设置/更新指定相机的内参。

        参数:
          camera_index: 相机索引
          fx, fy: 焦距（像素）
          cx, cy: 主点（像素）
          width, height: 图像分辨率
          K: 3x3 相机内参矩阵（可选，默认从 fx/fy/cx/cy 构建）
          dist_coeff: 畸变系数 [k1,k2,p1,p2,k3]（可选，默认全零）
        """
        default_K = np.array([[fx, 0.0, cx],
                              [0.0, fy, cy],
                              [0.0, 0.0, 1.0]], dtype=np.float64)
        self._intrinsics[camera_index] = {
            "fx": fx, "fy": fy,
            "cx": cx, "cy": cy,
            "width": width, "height": height,
            "K": K if K is not None else default_K,
            "dist_coeff": dist_coeff if dist_coeff is not None else np.zeros(5, dtype=np.float64),
        }
        logger.info("camera[%d] 内参已设置: fx=%.1f, fy=%.1f, cx=%.1f, cy=%.1f",
                    camera_index, fx, fy, cx, cy)

    def _get_intrinsics(self, camera_index: int) -> dict:
        """获取指定相机的内参，不存在则返回默认值。"""
        if camera_index in self._intrinsics:
            return self._intrinsics[camera_index]
        logger.warning("camera[%d] 内参未配置，使用默认值", camera_index)
        return dict(self._default_intrinsics)

    # ================================================================
    #  对外接口: 2D 像素 → 世界坐标
    # ================================================================

    def _undistort_pixel(self, u: float, v: float, camera_index: int) -> tuple[float, float]:
        """
        对像素坐标做镜头畸变校正。

        畸变为零时退化为恒等变换（不调用 cv2）。
        """
        K = self._get_intrinsics(camera_index)
        camK = K.get("K")
        dist = K.get("dist_coeff")
        if camK is None or dist is None:
            return u, v
        if np.allclose(dist, 0.0):
            return u, v
        try:
            src = np.array([[[u, v]]], dtype=np.float32)
            out = cv2.undistortPoints(src, camK, dist, P=camK)
            return float(out[0, 0, 0]), float(out[0, 0, 1])
        except Exception:
            return u, v

    def project_pixel_defect(
        self, u: float, v: float, depth: float,
        camera_index: int,
        camera_pose_in_body: dict,
        car_pose_in_world: dict,
    ) -> Optional[dict]:
        """
        将 2D 像素坐标投影到世界坐标系。

        转换链:
          像素 (u, v) + 深度 d
          → 相机局部 3D: P_cam = pixel_to_camera_3d(u, v, d, K)
          → 车体坐标:    P_body = inv(T_body→cam) @ P_cam
          → 世界坐标:    P_world = T_body→world @ P_body

        参数:
          u, v: 像素坐标（以图像左上角为原点）
          depth: 该像素对应的深度值（米）
          camera_index: 相机索引（用于查找内参）
          camera_pose_in_body: 相机在车体中的外参，
            {"position": {"x","y","z"}, "rotation": {"qw","qx","qy","qz"}}
          car_pose_in_world: 小车在世界中的位姿（来自航迹推算），
            {"position": {"x","y","z"}, "rotation": {"qw","qx","qy","qz"}}

        返回:
          {"x": float, "y": float, "z": float} 或 None（转换失败时）
        """
        try:
            # ── Step 0: 镜头畸变校正（零畸变时恒等） ──
            u_undist, v_undist = self._undistort_pixel(u, v, camera_index)

            # ── Step 1: 像素 → 相机局部 3D ──
            K = self._get_intrinsics(camera_index)
            p_cam = self._pixel_to_camera_3d(u_undist, v_undist, depth, K)
            if p_cam is None:
                return None

            # ── Step 2-3: 相机局部 → 车体 → 世界 ──
            return self._sensor_to_world(p_cam, camera_pose_in_body, car_pose_in_world)

        except Exception as e:
            logger.error("project_pixel_defect 异常: %s", e, exc_info=True)
            return None

    # ================================================================
    #  对外接口: 传感器局部 3D → 世界坐标
    # ================================================================

    def project_3d_defect(
        self, point_sensor: list[float],
        camera_pose_in_body: dict,
        car_pose_in_world: dict,
    ) -> Optional[dict]:
        """
        将传感器局部 3D 坐标投影到世界坐标系。

        适用于 AI 模型直接输出 3D 检测结果（如 3D 目标检测）。

        转换链:
          P_body = inv(T_body→sensor) @ P_sensor
          P_world = T_body→world @ P_body

        参数:
          point_sensor: 传感器局部坐标 [x, y, z]（米）
          camera_pose_in_body: 传感器在车体中的外参
          car_pose_in_world: 小车在世界中的位姿

        返回:
          {"x": float, "y": float, "z": float} 或 None
        """
        try:
            return self._sensor_to_world(point_sensor, camera_pose_in_body, car_pose_in_world)
        except Exception as e:
            logger.error("project_3d_defect 异常: %s", e, exc_info=True)
            return None

    # ================================================================
    #  对外接口: 批量投影
    # ================================================================

    def project_defects_batch(
        self, defect_list: list[dict],
        camera_pose_in_body: dict,
        car_pose_in_world: dict,
    ) -> list[dict]:
        """
        批量投影多个缺陷（每个缺陷可来自不同相机）。

        参数:
          defect_list: 缺陷列表，每项包含:
            {
              "defect_id": str,
              "type": str,                # 缺陷类型（裂缝/渗水/脱落等）
              "confidence": float,        # 置信度 [0,1]
              "camera_index": int,        # 来源相机索引
              "source": "2d" | "3d",      # 输入类型
              "pixel_uv": [u, v],         # 2D 输入（source=="2d" 时必填）
              "depth": float,             # 深度（source=="2d" 时必填）
              "point_3d": [x, y, z],      # 3D 输入（source=="3d" 时必填）
            }

        返回:
          成功投影的缺陷列表，每项包含世界坐标:
            {
              "defect_id": str,
              "type": str,
              "world_coord": {"x": float, "y": float, "z": float},
              "confidence": float,
              "timestamp_ns": int,
              "frame_id": str,
            }
        """
        results = []
        for defect in defect_list:
            try:
                camera_index = defect.get("camera_index", 0)
                source = defect.get("source", "3d")
                timestamp_ns = defect.get("timestamp_ns", 0)
                frame_id = defect.get("frame_id", "")

                # ── 根据输入类型计算世界坐标 ──
                if source == "2d":
                    uv = defect.get("pixel_uv", [0, 0])
                    depth = defect.get("depth", 1.0)
                    world_coord = self.project_pixel_defect(
                        uv[0], uv[1], depth,
                        camera_index,
                        camera_pose_in_body,
                        car_pose_in_world,
                    )
                else:  # "3d"
                    p3d = defect.get("point_3d", [0, 0, 0])
                    world_coord = self.project_3d_defect(
                        p3d, camera_pose_in_body, car_pose_in_world,
                    )

                if world_coord is None:
                    logger.warning("缺陷 %s 投影失败，跳过", defect.get("defect_id", "?"))
                    continue

                results.append({
                    "defect_id": defect.get("defect_id", "unknown"),
                    "type": defect.get("type", "unknown"),
                    "world_coord": world_coord,
                    "confidence": defect.get("confidence", 0.0),
                    "timestamp_ns": timestamp_ns,
                    "frame_id": frame_id,
                })

            except Exception as e:
                logger.error("批量投影缺陷 %s 异常: %s",
                            defect.get("defect_id", "?"), e)
                continue

        logger.info("批量投影完成: %d/%d 个缺陷成功投影到世界坐标系",
                    len(results), len(defect_list))
        return results

    # ================================================================
    #  坐标转换内部实现
    # ================================================================

    @staticmethod
    def _pixel_to_camera_3d(u: float, v: float, depth: float, K: dict) -> Optional[list[float]]:
        """
        2D 像素坐标 → 相机局部 3D 坐标。

        针孔相机模型反算:
          X = (u - cx) * depth / fx
          Y = (v - cy) * depth / fy
          Z = depth

        参数:
          u, v: 像素坐标
          depth: 深度值（米），需 > 0
          K: 相机内参 {"fx","fy","cx","cy"}

        返回:
          [x, y, z] 或 None（depth ≤ 0 时）
        """
        if depth <= 0:
            logger.warning("无效深度值 depth=%.3f，无法反算 3D 坐标", depth)
            return None

        fx = K.get("fx", 1000.0)
        fy = K.get("fy", 1000.0)
        cx = K.get("cx", 960.0)
        cy = K.get("cy", 540.0)

        x = (u - cx) * depth / fx
        y = (v - cy) * depth / fy
        z = depth

        return [x, y, z]

    @staticmethod
    def _sensor_to_world(
        point_sensor: list[float],
        camera_pose_in_body: dict,
        car_pose_in_world: dict,
    ) -> Optional[dict]:
        """
        将传感器局部坐标变换到世界坐标系。

        变换链:
          T_BW = pose_to_matrix(car_pose_in_world)     # 车体→世界
          T_SB = pose_to_matrix(camera_pose_in_body)    # 传感器→车体
          T_SW = T_BW @ T_SB                            # 传感器→世界
          P_world = T_SW @ P_sensor

        参数:
          point_sensor: [x, y, z] 传感器坐标系下的点
          camera_pose_in_body: 传感器在车体中的外参
          car_pose_in_world: 小车在世界中的位姿

        返回:
          {"x": float, "y": float, "z": float}
        """
        # ── 构建变换矩阵 ──
        T_SB = DefectProjector._pose_to_matrix(camera_pose_in_body)    # 4×4
        T_BW = DefectProjector._pose_to_matrix(car_pose_in_world)      # 4×4
        T_SW = T_BW @ T_SB                                             # 链式变换

        # ── 齐次坐标变换 ──
        p_homo = np.array([point_sensor[0], point_sensor[1], point_sensor[2], 1.0], dtype=np.float64)
        p_world_homo = T_SW @ p_homo

        return {
            "x": float(p_world_homo[0]),
            "y": float(p_world_homo[1]),
            "z": float(p_world_homo[2]),
        }

    # ================================================================
    #  底层变换工具（与 reconstruction/transform.py 一致）
    # ================================================================

    @staticmethod
    def _quat_to_rotation(qw: float, qx: float, qy: float, qz: float) -> np.ndarray:
        """
        四元数 → 3×3 旋转矩阵。

        与 reconstruction.transform.quat_to_rotation 保持一致。
        """
        R = np.array([
            [1 - 2*qy**2 - 2*qz**2,  2*qx*qy - 2*qz*qw,      2*qx*qz + 2*qy*qw],
            [2*qx*qy + 2*qz*qw,      1 - 2*qx**2 - 2*qz**2,  2*qy*qz - 2*qx*qw],
            [2*qx*qz - 2*qy*qw,      2*qy*qz + 2*qx*qw,      1 - 2*qx**2 - 2*qy**2],
        ], dtype=np.float64)
        return R

    @staticmethod
    def _pose_to_matrix(pose_dict: dict) -> np.ndarray:
        """
        位姿字典 → 4×4 齐次变换矩阵。

        与 reconstruction.transform.pose_to_matrix 接口一致。

        参数:
          pose_dict: {"position": {"x","y","z"}, "rotation": {"qw","qx","qy","qz"}}

        返回:
          4×4 numpy array [[R, t], [0, 1]]
        """
        pos = pose_dict["position"]
        rot = pose_dict["rotation"]

        T = np.eye(4, dtype=np.float64)
        T[:3, :3] = DefectProjector._quat_to_rotation(
            rot["qw"], rot["qx"], rot["qy"], rot["qz"]
        )
        T[:3, 3] = [pos["x"], pos["y"], pos["z"]]
        return T

    @staticmethod
    def _inverse_pose(T: np.ndarray) -> np.ndarray:
        """
        求齐次变换矩阵的逆。

        用于: 相机外参 T_body→cam 的逆 = T_cam→body

        原理: [R t; 0 1]⁻¹ = [Rᵀ -Rᵀt; 0 1]
        """
        R = T[:3, :3]
        t = T[:3, 3]
        T_inv = np.eye(4, dtype=np.float64)
        T_inv[:3, :3] = R.T
        T_inv[:3, 3] = -R.T @ t
        return T_inv

    # ================================================================
    #  从点云计算深度（替代硬编码 3.0）
    # ================================================================

    def compute_depth_from_point_cloud(
        self, points_flat: list[float],
        camera_pose_in_body: dict,
        car_pose_in_world: dict,
        max_samples: int = 100,
    ) -> float:
        """
        从世界坐标系点云计算该相机视角的代表性深度。

        抽样变换到相机坐标系，取中位数正深度。无有效点时 fallback 3.0。
        """
        pts = np.array(points_flat, dtype=np.float64)
        if pts.size < 3:
            return 3.0
        pts = pts.reshape(-1, 3)
        if len(pts) > max_samples:
            idxs = np.linspace(0, len(pts) - 1, max_samples, dtype=int)
            pts = pts[idxs]

        T_BW = self._pose_to_matrix(car_pose_in_world)
        T_CB = self._pose_to_matrix(camera_pose_in_body)
        T_WC = self._inverse_pose(T_BW) @ T_CB

        ones = np.ones((len(pts), 1), dtype=np.float64)
        cam_pts = (T_WC @ np.hstack([pts, ones]).T).T
        depths = cam_pts[:, 2]
        valid = depths[depths > 0]
        return float(np.median(valid)) if valid.size > 0 else 3.0

    # ================================================================
    #  3D Gaussian Splatting 模型标注（预留接口）
    # ================================================================

    def project_to_3dgs(
        self, defect_world_coords: list[dict],
        gaussian_model=None,  # 3DGS 模型对象，类型待定
    ) -> list[dict]:
        """
        将缺陷世界坐标映射到 3D Gaussian Splatting 模型上。

        此为预留接口，实际对接时需传入 3DGS 模型对象。

        参数:
          defect_world_coords: 世界坐标系中的缺陷列表
          gaussian_model: 3DGS 模型（待定义接口）

        返回:
          标注点列表，每项包含 3DGS 中的最近高斯体索引
        """
        # TODO: 对接实际的 3DGS 模型
        # 预期逻辑:
        #   1. 对每个缺陷世界坐标，在 3DGS 模型中查找最近的高斯体
        #   2. 关联缺陷属性到该高斯体（颜色、不透明度标记）
        #   3. 返回标注后的模型引用
        logger.warning("project_to_3dgs: 3DGS 模型未连接，返回原始世界坐标")
        return defect_world_coords
