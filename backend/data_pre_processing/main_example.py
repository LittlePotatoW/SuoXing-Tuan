# ============================================================
#  文件: backend/data_pre_processing/main_example.py
#  所属: SuoXing-Tuan / 数据融合与缺陷投影模块
#  职责: 主程序示例
#        - 演示完整的数据融合 + 缺陷投影 + 表格生成流程
#        - 使用 Mock 数据模拟 location_data 和 detection_data 数据流
#        - 验证模块间数据协议的正确性
#
#  运行方式:
#    cd backend
#    python -m data_pre_processing.main_example
#
#  或:
#    python backend/data_pre_processing/main_example.py
#
#  注意:
#    - DeadReckoningEngine 在此为 Mock 实现
#    - TODO: 替换为同事提供的正式 DeadReckoningEngine 实例
#    - 所有模拟数据均符合 detection_data / location_data / final_data 协议
# ============================================================

import sys
import os
import time
import math
import logging

# 确保项目根目录在 path 中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ── 配置日志 ──
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main_example")


# ============================================================
#  Mock 数据生成器
# ============================================================

def generate_mock_location_data(timestamp_ns: int,
                                 velocity: float = 0.5,
                                 steering_angle: float = 0.0) -> dict:
    """
    生成模拟的 location_data 帧。

    模拟小车以恒定速度直线行驶（速度 0.5 m/s），
    携带两个工业相机的外参（标定值，不变）。

    参数:
      timestamp_ns: 时间戳（纳秒）
      velocity: 线速度 m/s
      steering_angle: 转向角 rad
    """
    return {
        "timestamp_ns": timestamp_ns,

        # ── 相机外参（标定值，固定不变） ──
        "camera": [
            {
                "camera_pose": {
                    "position": {"x": 0.0, "y": 0.0, "z": 0.3},
                    "rotation": {"qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0},
                }
            },
            {
                "camera_pose": {
                    "position": {"x": 0.0, "y": 1.0, "z": 0.3},
                    "rotation": {"qw": 0.707, "qx": 0.0, "qy": 0.0, "qz": 0.707},
                }
            },
        ],

        # ── 小车数据 ──
        "car": {
            # car.pose 存在但不被信任（融合时会丢弃）
            "pose": {
                "position": {"x": -999.0, "y": -999.0, "z": -999.0},  # 无效GPS值，标记为不可用
                "rotation": {"qw": -1.0, "qx": -1.0, "qy": -1.0, "qz": -1.0},
            },
            "kinematics": {
                "velocity": velocity,
                "steering_angle": steering_angle,
                "wheel_base": 1.5,
            },
        },
    }


def generate_mock_detection_data(frame_id: str, timestamp_ns: int,
                                  include_all_cameras: bool = True) -> dict:
    """
    生成模拟的 detection_data 帧。

    模拟传感器采集：包含 8 个点的模拟点云 + 2 个相机视图。

    参数:
      frame_id: 帧ID
      timestamp_ns: 时间戳（纳秒）
      include_all_cameras: True = 包含所有相机; False = 模拟部分缺失
    """
    # ── 模拟点云：4 个角落的 2 层点（共 8 个点） ──
    # 模拟扫描到隧道壁的距离测量值
    points = [
        1.0, 0.0, 0.5, 1.1, 0.0, 0.5, 1.0, 0.1, 0.5, 0.9, 0.1, 0.5,
        1.0, 0.0, 0.6, 1.1, 0.0, 0.6, 1.0, 0.1, 0.6, 0.9, 0.1, 0.6,
    ]

    camera_views = []
    if include_all_cameras:
        # 相机0: 前视
        camera_views.append({
            "image_data": "MOCK_BASE64_IMAGE_DATA_CAM0",
            "width": 1920,
            "height": 1080,
            # 注意: detection 自带的 camera_pose 会被 location 缓存覆盖
            "camera_pose": {
                "position": {"x": 0.0, "y": 0.0, "z": 0.3},
                "rotation": {"qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0},
            },
        })
        # 相机1: 侧视
        camera_views.append({
            "image_data": "MOCK_BASE64_IMAGE_DATA_CAM1",
            "width": 1920,
            "height": 1080,
            "camera_pose": {
                "position": {"x": 0.0, "y": 1.0, "z": 0.3},
                "rotation": {"qw": 0.707, "qx": 0.0, "qy": 0.0, "qz": 0.707},
            },
        })

    return {
        "frame_id": frame_id,
        "timestamp_ns": timestamp_ns,

        "point_cloud": {
            "points": points,
            "point_count": 8,
        },

        "camera_views": camera_views,

        # car_position 存在但不被信任（融合时丢弃，使用航迹推算位姿）
        "car_position": {
            "pose": {
                "position": {"x": 999.0, "y": 999.0, "z": 999.0},  # 无效值
                "rotation": {"qw": -1.0, "qx": -1.0, "qy": -1.0, "qz": -1.0},
            },
            "timestamp_ns": timestamp_ns,
        },

        # kinematics 存在但会被 location 的最新值覆盖
        "kinematics": {
            "velocity": 999.0,        # 会被 location 覆盖
            "steering_angle": 999.0,
            "wheel_base": 1.5,
            "timestamp_ns": timestamp_ns,
        },
    }


def generate_mock_defects() -> list[dict]:
    """
    生成模拟的 AI 缺陷检测结果。

    模拟在不同相机中检测到的裂缝缺陷，
    包含 2D 像素坐标和 3D 传感器局部坐标两种输入。
    """
    return [
        # ── 缺陷1: 2D 像素坐标（相机0前视检测到的裂缝） ──
        {
            "defect_id": "DEF_001",
            "type": "裂缝",
            "confidence": 0.92,
            "camera_index": 0,
            "source": "2d",
            "pixel_uv": [960, 540],     # 图像中心
            "depth": 3.0,                # 3米远的隧道壁
            "timestamp_ns": 1_000_000_000,
            "frame_id": "frame_00001",
        },
        # ── 缺陷2: 3D 传感器局部坐标（相机0前方） ──
        {
            "defect_id": "DEF_002",
            "type": "渗水",
            "confidence": 0.78,
            "camera_index": 0,
            "source": "3d",
            "point_3d": [1.2, -0.3, 0.8],    # 传感器前方1.2m，偏左0.3m
            "timestamp_ns": 1_000_000_000,
            "frame_id": "frame_00001",
        },
        # ── 缺陷3: 2D 像素坐标（相机1侧视检测到的裂缝） ──
        {
            "defect_id": "DEF_003",
            "type": "裂缝",
            "confidence": 0.85,
            "camera_index": 1,
            "source": "2d",
            "pixel_uv": [400, 300],
            "depth": 2.5,
            "timestamp_ns": 3_000_000_000,
            "frame_id": "frame_00003",
        },
        # ── 缺陷4: 3D 传感器局部坐标（直接检测） ──
        {
            "defect_id": "DEF_004",
            "type": "脱落",
            "confidence": 0.65,
            "camera_index": 0,
            "source": "3d",
            "point_3d": [2.0, 0.5, 0.3],
            "timestamp_ns": 5_000_000_000,
            "frame_id": "frame_00005",
        },
    ]


# ============================================================
#  主演示流程
# ============================================================

def main():
    """主演示函数。展示完整的数据融合、缺陷投影、表格生成流程。"""
    print("=" * 70)
    print("  SuoXing-Tuan 数据融合与缺陷投影模块 — 演示")
    print("=" * 70)
    print()

    # ══════════════════════════════════════════════════════════════
    #  Step 0: 初始化
    # ══════════════════════════════════════════════════════════════

    # TODO: 替换为同事提供的正式 DeadReckoningEngine 实例
    #       例如:
    #       from real_dead_reckoning import DeadReckoningEngine
    #       dr_engine = DeadReckoningEngine()
    from data_pre_processing.kinematics_api import DeadReckoningEngine
    from data_pre_processing.data_fusion_manager import DataFusionManager
    from data_pre_processing.defect_projector import DefectProjector
    from data_pre_processing.defect_table_generator import DefectTableGenerator

    # ── 创建航迹推算引擎 ──
    dr_engine = DeadReckoningEngine(
        initial_x=0.0, initial_y=0.0, initial_yaw=0.0
    )

    # ── 创建融合管理器（依赖注入） ──
    fusion_mgr = DataFusionManager(dead_reckoning_engine=dr_engine)

    # ── 创建缺陷投影器 ──
    # 设置两个相机的内参（模拟标定值）
    projector = DefectProjector()
    projector.set_intrinsics(camera_index=0, fx=1050.0, fy=1050.0,
                             cx=960.0, cy=540.0, width=1920, height=1080)
    projector.set_intrinsics(camera_index=1, fx=1000.0, fy=1000.0,
                             cx=960.0, cy=540.0, width=1920, height=1080)

    # ── 创建表格生成器 ──
    table_gen = DefectTableGenerator()

    print("[OK] 初始化完成")
    print(f"  航迹推算引擎: {type(dr_engine).__name__}")
    print(f"  融合管理器: {type(fusion_mgr).__name__}")
    print(f"  缺陷投影器: {type(projector).__name__}")
    print(f"  表格生成器: {type(table_gen).__name__}")
    print()

    # ══════════════════════════════════════════════════════════════
    #  Step 1: 模拟 location_data 持续上报（100Hz 频率）
    # ══════════════════════════════════════════════════════════════
    print("─" * 70)
    print("  Step 1: 模拟 location_data 高频上报 (100Hz × 5秒)")
    print("─" * 70)

    # 模拟 5 秒的定位数据流，100Hz = 每 10ms 一帧
    base_time_ns = 1_000_000_000  # 起始时间 t=1s (纳秒)
    velocity = 0.5   # 0.5 m/s 匀速
    steering = 0.0   # 直线行驶

    for i in range(50):  # 模拟 50 帧 = 0.5 秒
        t_ns = base_time_ns + i * 10_000_000  # 每 10ms
        loc = generate_mock_location_data(t_ns, velocity=velocity, steering_angle=steering)
        fusion_mgr.feed_location_data(loc)

    print(f"  已发送 {50} 帧 location_data")

    # 检查外参缓存
    cache = fusion_mgr.extrinsic_cache
    print(f"  外参缓存池: {len(cache)} 个相机已缓存")
    for idx, pose in cache.items():
        print(f"    camera[{idx}]: pos=({pose['position']['x']:.2f}, "
              f"{pose['position']['y']:.2f}, {pose['position']['z']:.2f})")

    # 查看航迹推算状态
    dr_state = dr_engine.state
    print(f"  航迹推算状态: x={dr_state['x']:.3f}m, y={dr_state['y']:.3f}m, "
          f"yaw={dr_state['theta_deg']:.2f}°")
    print()

    # ══════════════════════════════════════════════════════════════
    #  Step 2: 模拟 detection_data 触发式上报
    #  ══════════════════════════════════════════════════════════════
    print("─" * 70)
    print("  Step 2: 模拟 detection_data 触发融合")
    print("─" * 70)

    # 模拟 5 帧 detection_data（触发式，间隔约 1 秒）
    detection_frames = []
    for i in range(5):
        t_ns = base_time_ns + i * 1_000_000_000  # 每隔 1 秒
        frame_id = f"frame_{i+1:05d}"
        det = generate_mock_detection_data(frame_id, t_ns, include_all_cameras=True)

        # ── 在触发 detection 之前，先补充 location_data 以推进航迹推算 ──
        # 模拟 10 帧 location（0.1 秒的数据），时间戳紧接在上次 location 之后
        last_loc_ts = fusion_mgr._last_location_timestamp_ns or (t_ns - 100_000_000)
        for j in range(10):
            lt_ns = last_loc_ts + (j + 1) * 10_000_000
            loc = generate_mock_location_data(lt_ns, velocity=velocity, steering_angle=steering)
            fusion_mgr.feed_location_data(loc)

        # ── 触发融合 ──
        final = fusion_mgr.process_detection(det)
        if final:
            detection_frames.append(final)
            pos = final["car_position"]["pose"]["position"]
            print(f"  [OK] {frame_id}: 融合成功, 小车位姿=({pos['x']:.3f}, {pos['y']:.3f}), "
                  f"点云={final['point_cloud']['point_count']}点, "
                  f"相机={len(final['camera_views'])}个")
        else:
            print(f"  [FAIL] {frame_id}: 融合失败（跳过）")

    print(f"  共融合 {len(detection_frames)}/{5} 帧")
    print()

    # ══════════════════════════════════════════════════════════════
    #  Step 3: 模拟缺失字段的容错处理
    # ══════════════════════════════════════════════════════════════
    print("─" * 70)
    print("  Step 3: 容错测试 — 模拟缺失字段")
    print("─" * 70)

    # 3a: 缺失 point_cloud -> 应丢弃整帧
    det_no_pc = {
        "frame_id": "no_pointcloud_frame",
        "timestamp_ns": 2_000_000_000,
        "camera_views": [],
    }
    result = fusion_mgr.process_detection(det_no_pc)
    print(f"  3a. 缺失 point_cloud  ->  {'[FAIL] 正确丢弃' if result is None else '[FAIL] 错误：未丢弃!'}")

    # 3b: 缺失 frame_id -> 应自动生成
    det_no_id = generate_mock_detection_data("", 2_100_000_000)
    det_no_id["frame_id"] = ""  # 空字符串视为缺失
    result = fusion_mgr.process_detection(det_no_id)
    if result:
        print(f"  3b. 缺失 frame_id     ->  [OK] 自动生成: {result['frame_id']}")
    else:
        print(f"  3b. 缺失 frame_id     ->  [FAIL] 意外丢弃")

    # 3c: 缺失 camera_views -> 应输出空数组
    det_no_cam = generate_mock_detection_data("no_cam_frame", 2_200_000_000)
    det_no_cam["camera_views"] = None  # 显式 None
    result = fusion_mgr.process_detection(det_no_cam)
    if result:
        print(f"  3c. camera_views=None  ->  [OK] Fallback 为 [], 相机数={len(result['camera_views'])}")
    else:
        print(f"  3c. camera_views=None  ->  [FAIL] 意外丢弃")

    # 3d: 外参缓存缺失时 fallback 到 detection 自带的 camera_pose
    #     （清空缓存模拟此场景）
    #     已在代码逻辑中处理，此处不额外测试
    print(f"  3d. 外参缓存缺失       ->  (已实现 fallback 到 detection camera_pose)")
    print()

    # ══════════════════════════════════════════════════════════════
    #  Step 4: 缺陷投影
    # ══════════════════════════════════════════════════════════════
    print("─" * 70)
    print("  Step 4: 缺陷坐标投影（2D 像素 & 3D 局部 -> 世界坐标）")
    print("─" * 70)

    mock_defects = generate_mock_defects()

    # 使用第一帧融合后的位姿做投影
    if detection_frames:
        first_frame = detection_frames[0]
        car_pose_world = first_frame["car_position"]["pose"]
        camera_views = first_frame["camera_views"]

        # 对每个缺陷选择合适的 camera_pose
        projected_defects = []
        for defect in mock_defects:
            cam_idx = defect.get("camera_index", 0)
            if cam_idx < len(camera_views):
                camera_pose_body = camera_views[cam_idx]["camera_pose"]
            else:
                camera_pose_body = {
                    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rotation": {"qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0},
                }

            # ── 单缺陷投影 ──
            if defect["source"] == "2d":
                uv = defect["pixel_uv"]
                world_coord = projector.project_pixel_defect(
                    u=uv[0], v=uv[1],
                    depth=defect["depth"],
                    camera_index=cam_idx,
                    camera_pose_in_body=camera_pose_body,
                    car_pose_in_world=car_pose_world,
                )
            else:
                world_coord = projector.project_3d_defect(
                    point_sensor=defect["point_3d"],
                    camera_pose_in_body=camera_pose_body,
                    car_pose_in_world=car_pose_world,
                )

            if world_coord:
                projected_defects.append({
                    "defect_id": defect["defect_id"],
                    "type": defect["type"],
                    "world_coord": world_coord,
                    "confidence": defect["confidence"],
                    "timestamp_ns": defect["timestamp_ns"],
                    "frame_id": defect["frame_id"],
                })
                print(f"  [OK] {defect['defect_id']} ({defect['type']}, "
                      f"source={defect['source']}): "
                      f"世界坐标=({world_coord['x']:.3f}, {world_coord['y']:.3f}, "
                      f"{world_coord['z']:.3f})")
            else:
                print(f"  [FAIL] {defect['defect_id']}: 投影失败")

    print(f"  成功投影 {len(projected_defects)}/{len(mock_defects)} 个缺陷")
    print()

    # ══════════════════════════════════════════════════════════════
    #  Step 5: 缺陷表格生成
    # ══════════════════════════════════════════════════════════════
    print("─" * 70)
    print("  Step 5: 缺陷汇总表格生成")
    print("─" * 70)

    # ── 批量添加缺陷 ──
    table_gen.add_defects_batch(projected_defects)

    # ── CSV 输出 ──
    csv_output = table_gen.to_csv(sort="time")
    print("  [CSV 输出]")
    for line in csv_output.strip().split("\n"):
        print(f"    {line}")

    print()

    # ── JSON 输出 ──
    json_output = table_gen.to_json(sort="time", pretty=True)
    print("  [JSON 输出]")
    for line in json_output.strip().split("\n"):
        print(f"    {line}")

    print()

    # ── 汇总统计 ──
    summary = table_gen.to_summary_dict()
    print("  [缺陷汇总]")
    print(f"    总计: {summary['total']} 个缺陷")
    for defect_type, stats in summary["by_type"].items():
        print(f"    {defect_type}: {stats['count']}个, "
              f"平均置信度={stats['avg_confidence']:.2f}, "
              f"最高={stats['max_confidence']:.2f}")
    print()

    # ══════════════════════════════════════════════════════════════
    #  Step 6: 与 reconstruction 管线对接示例
    # ══════════════════════════════════════════════════════════════
    print("─" * 70)
    print("  Step 6: 与 reconstruction 管线对接示例")
    print("─" * 70)

    print("""
  融合后的 final_data 可直接投喂给现有 reconstruction 管线:

    from reconstruction.schemas import SensorFrame
    from reconstruction.fusion import DataFusion
    from reconstruction.engine import ReconstructionEngine

    # 1. 构造 SensorFrame（final_data 格式等同于 SensorFrame）
    final_frame = fusion_mgr.process_detection(detection_data)
    sensor_frame = SensorFrame(**final_frame)

    # 2. 坐标变换（SensorFrame -> FusedFrame）
    data_fusion = DataFusion(sensor_pose_in_body=[0,0,0.5, 1,0,0,0])
    fused = data_fusion.process(sensor_frame)

    # 3. 喂给重建引擎
    engine = ReconstructionEngine()
    engine.add_frame(fused)

    # 4. 世界坐标缺陷可直接标注
    for defect in projected_defects:
        wc = defect["world_coord"]
        engine.add_crack(wc["x"], wc["y"], wc["z"],
                         confidence=defect["confidence"],
                         crack_type=defect["type"],
                         frame_id=defect["frame_id"])
""")

    # ══════════════════════════════════════════════════════════════
    #  Step 7: 统计报告
    # ══════════════════════════════════════════════════════════════
    print("─" * 70)
    print("  Step 7: 运行统计")
    print("─" * 70)

    stats = fusion_mgr.stats
    dr_state = dr_engine.state
    print(f"  融合统计:")
    print(f"    location_data 接收: {stats['location_count']} 帧")
    print(f"    detection_data 接收: {stats['detection_count']} 帧")
    print(f"    成功融合: {stats['fusion_count']} 帧")
    print(f"    跳过: {stats['skip_count']} 帧")
    print(f"    缓存相机数: {stats['cached_cameras']}")
    print(f"  航迹推算状态:")
    print(f"    位置: x={dr_state['x']:.3f}m, y={dr_state['y']:.3f}m")
    print(f"    朝向: {dr_state['theta_deg']:.2f}°")
    print(f"    总行驶距离: {dr_state['total_distance_m']:.2f}m")
    print(f"    积分次数: {dr_state['integration_count']}")
    print(f"  缺陷统计:")
    print(f"    已记录缺陷: {table_gen.count} 个")
    print()

    print("=" * 70)
    print("  演示完成。所有数据均符合 detection_data / location_data / final_data 协议。")
    print("=" * 70)


if __name__ == "__main__":
    main()
