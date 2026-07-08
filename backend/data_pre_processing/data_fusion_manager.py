# ============================================================
#  文件: backend/data_pre_processing/data_fusion_manager.py
#  所属: SuoXing-Tuan / 数据融合与缺陷投影模块
#  职责: 数据融合管理器
#        - 实时接收 detection_data（传感器数据）和 location_data（定位数据）
#        - 融合两路数据流，输出符合 final_data.md 标准的 SensorFrame
#        - 丢弃不可信的 GPS 定位，纯靠航迹推算确定小车位姿
#
#  融合逻辑:
#    1. location_data → 缓存相机外参 + 喂 kinematics 给航迹推算引擎
#    2. detection_data → 触发融合:
#       a. 从航迹推算引擎查询当前世界位姿
#       b. 用缓存的外参覆盖 camera_views[].camera_pose
#       c. 组装 final_data（格式等同于后端 SensorFrame）
#    3. 所有字段缺失时使用 final_data.md 定义的 Fallback 策略
#
#  数据流对照:
#    location_data.car.pose        → 丢弃（不信任 GPS）
#    location_data.camera[].camera_pose → 缓存为外参池
#    location_data.car.kinematics  → 喂给 StateEstimator
#    detection_data.car_position   → 丢弃（使用航迹推算输出）
#    detection_data.kinematics     → 丢弃（使用 location 的最新值）
#    detection_data.point_cloud    → 透传（必须字段）
#    detection_data.camera_views   → 透传，camera_pose 被覆盖
# ============================================================

import logging
import math
from typing import Optional

# TODO: 替换为同事提供的正式 StateEstimator 实例时，
#       只需修改 import 路径:
#       from real_dead_reckoning import StateEstimator
from .state_estimator import StateEstimator

logger = logging.getLogger("data_pre_processing.fusion")


class DataFusionManager:
    """
    数据融合管理器。

    核心职责:
      1. 维护外参缓存池：持续从 location_data 接收 camera_pose（标定值）
      2. 维护运动学状态：持续将 kinematics 喂给 StateEstimator
      3. 触发融合：收到 detection_data 时输出 final_data

    使用方式:
      mgr = DataFusionManager(dead_reckoning_engine)

      # 持续接收 location_data
      mgr.feed_location_data(location_dict)

      # 收到 detection_data 时触发融合
      final_frame = mgr.process_detection(detection_dict)
      if final_frame:
          # final_frame 可直接用于构造 SensorFrame(**final_frame)
          ...
    """

    def __init__(self, dead_reckoning_engine: StateEstimator):
        """
        初始化融合管理器。

        参数:
          dead_reckoning_engine: 航迹推算引擎实例（依赖注入）。
            该引擎需实现:
              - feed_kinematics(kinematics: dict, timestamp_ns: int) -> None
              - get_pose(timestamp_ns: int) -> dict
        """
        # ── 依赖注入：航迹推算引擎 ──
        # TODO: 替换为同事提供的正式 StateEstimator 实例
        self._dr_engine: StateEstimator = dead_reckoning_engine

        # ── 外参缓存池: {camera_index: camera_pose_dict} ──
        # 从 location_data.camera[] 提取，按数组索引存储
        self._extrinsic_cache: dict[int, dict] = {}

        # ── 最新运动学参数（来自 location_data） ──
        self._latest_kinematics: Optional[dict] = None

        # ── 最新定位时间戳 ──
        self._last_location_timestamp_ns: Optional[int] = None

        # ── 统计数据 ──
        self._location_count: int = 0
        self._detection_count: int = 0
        self._fusion_count: int = 0
        self._skip_count: int = 0

        logger.info("DataFusionManager 初始化完成")

    # ================================================================
    #  对外接口: 接收 location_data
    # ================================================================

    def feed_location_data(self, location_data: dict) -> None:
        """
        接收一帧定位数据（location_data）。

        处理逻辑（按 final_data.md 协议）:
          1. 提取 camera[] 数组，按索引缓存 camera_pose（外参）
          2. 提取 car.kinematics，喂给 StateEstimator
          3. 丢弃 car.pose（不信任 GPS）

        参数:
          location_data: 定位数据字典，结构见 location_data.md

        容错:
          - camera[] 缺失 → 跳过，保留已有缓存
          - car.kinematics 缺失 → 使用默认值 (0, 0, 1.5)
          - car 整字段缺失 → 仅更新外参缓存
        """
        try:
            timestamp_ns = location_data.get("timestamp_ns", 0)

            # ── 1. 缓存相机外参 ──
            cameras = location_data.get("camera", [])
            if cameras:
                for idx, cam in enumerate(cameras):
                    camera_pose = cam.get("camera_pose")
                    if camera_pose is not None:
                        # 验证位姿结构完整性
                        if self._validate_pose(camera_pose):
                            self._extrinsic_cache[idx] = camera_pose
                        else:
                            logger.warning("location_data camera[%d].camera_pose 结构不完整，跳过", idx)
                logger.debug("外参缓存池更新: %d 个相机", len(self._extrinsic_cache))
            else:
                logger.debug("location_data 无 camera[] 字段，外参缓存保持不变 (%d 个相机)",
                            len(self._extrinsic_cache))

            # ── 2. 提取运动学参数并喂给航迹推算引擎 ──
            car = location_data.get("car", {})
            if car:
                kinematics = car.get("kinematics")
                if kinematics:
                    # 补全可能缺失的字段
                    kin = {
                        "velocity": float(kinematics.get("velocity", 0.0)),
                        "steering_angle": float(kinematics.get("steering_angle", 0.0)),
                        "wheel_base": float(kinematics.get("wheel_base", 1.5)),
                    }
                    self._dr_engine.update_kinematics(
                        velocity=kin["velocity"],
                        steering_angle=kin["steering_angle"],
                        timestamp_ns=timestamp_ns,
                    )
                    self._latest_kinematics = kin
                else:
                    logger.debug("location_data.car 中无 kinematics 字段")

                # car.pose 明确丢弃（final_data.md 规定）
                # 不读取 car.pose 字段
            else:
                logger.debug("location_data 中无 car 字段")

            self._last_location_timestamp_ns = timestamp_ns
            self._location_count += 1

        except Exception as e:
            logger.error("feed_location_data 异常: %s，丢弃本帧", e, exc_info=True)
            # 不崩溃，丢弃本帧继续

    # ================================================================
    #  对外接口: 接收 detection_data 并触发融合
    # ================================================================

    def process_detection(self, detection_data: dict) -> Optional[dict]:
        """
        接收一帧检测数据（detection_data），触发融合输出 final_data。

        处理逻辑（按 final_data.md 协议）:
          1. 校验 point_cloud → 缺失则丢弃整帧
          2. 提取 timestamp_ns，从 StateEstimator 查询世界位姿
          3. 遍历 camera_views，用外参缓存池覆盖 camera_pose
          4. 组装 final_data，应用所有 Fallback 策略

        参数:
          detection_data: 检测数据字典，结构见 detection_data.md

        返回:
          dict 或 None: 融合后的 final_data（格式等同于后端 SensorFrame），
                        point_cloud 缺失时返回 None

        字段来源对照（final_data.md）:
          frame_id       ← detection（缺失自动生成 "auto_{timestamp}"）
          timestamp_ns   ← detection 透传
          point_cloud    ← detection 透传（缺失 → 丢弃整帧）
          camera_views   ← detection（camera_pose 被 location 缓存覆盖）
          car_position   ← StateEstimator.get_pose()
          kinematics     ← location_data 最新值（fallback: detection 自带）
        """
        try:
            self._detection_count += 1

            # ── 1. frame_id ──
            frame_id = detection_data.get("frame_id")
            timestamp_ns = detection_data.get("timestamp_ns", 0)
            if not frame_id:
                frame_id = f"auto_{timestamp_ns}"
                logger.info("frame_id 缺失，自动生成: %s", frame_id)

            # ── 2. 校验 point_cloud（必须字段） ──
            # final_data.md: point_cloud 是唯一必须字段，缺失则丢弃整帧
            point_cloud = detection_data.get("point_cloud")
            if point_cloud is None:
                logger.warning("Frame %s: point_cloud 缺失 → 丢弃整帧", frame_id)
                self._skip_count += 1
                return None

            # 额外校验: point_cloud 内部点数组有效性
            points = point_cloud.get("points", [])
            if not points or len(points) < 3:
                logger.warning("Frame %s: point_cloud.points 为空或点数不足 → 丢弃整帧", frame_id)
                self._skip_count += 1
                return None

            # 确保 point_count 与 points 长度一致
            point_count = point_cloud.get("point_count", len(points) // 3)
            if point_count != len(points) // 3:
                logger.debug("Frame %s: point_count 与 points 长度不一致，以实际为准", frame_id)
                point_count = len(points) // 3

            # ── 3. 从航迹推算引擎查询世界位姿 ──
            car_state = self._dr_engine.get_position(timestamp_ns)
            if car_state is None:
                logger.warning("Frame %s: 航迹推算引擎无数据 → 丢弃整帧", frame_id)
                self._skip_count += 1
                return None
            # CarState → dict（兼容下游）
            half = car_state.yaw / 2.0
            car_pose = {
                "position": {"x": car_state.x, "y": car_state.y, "z": car_state.z},
                "rotation": {"qw": math.cos(half), "qx": 0.0, "qy": 0.0,
                             "qz": math.sin(half)},
            }

            # ── 4. 处理 camera_views ──
            # final_data.md: camera_views 缺失 → []
            camera_views_out = []
            raw_camera_views = detection_data.get("camera_views", [])
            if raw_camera_views is None:
                raw_camera_views = []

            for idx, cam_view in enumerate(raw_camera_views):
                # ── 外参: location 缓存优先 → detection fallback ──
                camera_pose = self._get_camera_pose(idx, cam_view)

                # ── 图片: 缺失 → null（跳过该相机，不参与颜色采样） ──
                image_data = cam_view.get("image_data", None)

                # ── 分辨率: 缺失默认 640×480 ──
                width = cam_view.get("width", 640)
                height = cam_view.get("height", 480)

                camera_view_out = {
                    "image_data": image_data,
                    "width": width,
                    "height": height,
                    "camera_pose": camera_pose,
                }
                camera_views_out.append(camera_view_out)

            # ── 5. kinematics ──
            # 优先使用 location_data 最新值，fallback 到 detection 自带
            kinematics = self._latest_kinematics
            if kinematics is None:
                det_kin = detection_data.get("kinematics")
                if det_kin:
                    kinematics = {
                        "velocity": float(det_kin.get("velocity", 0.0)),
                        "steering_angle": float(det_kin.get("steering_angle", 0.0)),
                        "wheel_base": float(det_kin.get("wheel_base", 1.5)),
                        "timestamp_ns": det_kin.get("timestamp_ns", timestamp_ns),
                    }
                else:
                    kinematics = {
                        "velocity": 0.0,
                        "steering_angle": 0.0,
                        "wheel_base": 1.5,
                        "timestamp_ns": timestamp_ns,
                    }
            else:
                # 更新 timestamp_ns 为当前帧时间
                kinematics = dict(kinematics)
                kinematics["timestamp_ns"] = timestamp_ns

            # ── 6. 组装最终输出 ──
            final_data = {
                "frame_id": frame_id,
                "timestamp_ns": timestamp_ns,
                "point_cloud": {
                    "points": points,
                    "point_count": point_count,
                },
                "camera_views": camera_views_out,
                "car_position": {
                    "pose": {
                        "position": car_pose["position"],
                        "rotation": car_pose["rotation"],
                    },
                    "timestamp_ns": timestamp_ns,
                },
                "kinematics": kinematics,
            }

            self._fusion_count += 1
            logger.info("Frame %s: 融合完成, %d 点, %d 相机, pos=(%.3f, %.3f)",
                        frame_id, point_count, len(camera_views_out),
                        car_pose["position"]["x"], car_pose["position"]["y"])
            return final_data

        except Exception as e:
            logger.error("process_detection 异常: %s，丢弃本帧", e, exc_info=True)
            self._skip_count += 1
            return None

    # ================================================================
    #  内部辅助方法
    # ================================================================

    def _get_camera_pose(self, camera_index: int, cam_view: dict) -> dict:
        """
        获取指定索引的相机外参。

        优先级:
          1. 外参缓存池 (location_data.camera[].camera_pose) — 标定值，优先使用
          2. detection_data.camera_views[].camera_pose — fallback
          3. 默认值（原点，无旋转）

        参数:
          camera_index: 相机在数组中的索引
          cam_view: detection_data 中的 camera_view 对象

        返回:
          {"position": {"x":, "y":, "z":}, "rotation": {"qw":, "qx":, "qy":, "qz":}}
        """
        # ── 优先从外参缓存池取 ──
        if camera_index in self._extrinsic_cache:
            logger.debug("camera[%d] 使用 location 缓存外参", camera_index)
            return self._extrinsic_cache[camera_index]

        # ── Fallback: 使用 detection 自带的 camera_pose ──
        det_pose = cam_view.get("camera_pose")
        if det_pose and self._validate_pose(det_pose):
            logger.debug("camera[%d] 外参缓存缺失，fallback 到 detection camera_pose", camera_index)
            return det_pose

        # ── 最终 Fallback: 默认值 ──
        logger.warning("camera[%d] 无可用外参，使用默认值（原点）", camera_index)
        return {
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "rotation": {"qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0},
        }

    @staticmethod
    def _validate_pose(pose: dict) -> bool:
        """
        验证位姿字典结构完整性。

        检查 position (x,y,z) 和 rotation (qw,qx,qy,qz) 字段是否存在。
        """
        if not isinstance(pose, dict):
            return False
        position = pose.get("position")
        rotation = pose.get("rotation")
        if not isinstance(position, dict) or not isinstance(rotation, dict):
            return False
        # 检查 position 的 x/y/z 字段
        for key in ("x", "y", "z"):
            if key not in position:
                return False
        # 检查 rotation 的四元数字段
        for key in ("qw", "qx", "qy", "qz"):
            if key not in rotation:
                return False
        return True

    # ================================================================
    #  状态查询
    # ================================================================

    @property
    def stats(self) -> dict:
        """返回融合统计信息。"""
        return {
            "location_count": self._location_count,
            "detection_count": self._detection_count,
            "fusion_count": self._fusion_count,
            "skip_count": self._skip_count,
            "cached_cameras": len(self._extrinsic_cache),
            "has_kinematics": self._latest_kinematics is not None,
        }

    @property
    def extrinsic_cache(self) -> dict:
        """返回外参缓存池的只读副本。"""
        return dict(self._extrinsic_cache)
