# ============================================================
#  文件: backend/tests/test_pipeline.py
#  所属: SuoXing-Tuan / V2 三维重建管线
#  职责: 用假数据端到端测试整个管线（数据融合 → 重建 → Mesh 输出）
#  用法: cd backend && python tests/test_pipeline.py
# ============================================================

import sys
import os
import json
import logging
import time
import math

# 确保 backend/ 在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from common.schemas import (
    SensorFrame, PointCloudData, CameraView, CarPosition, KinematicsData,
    Pose6DoF, Vector3, Quaternion,
)
from pipeline.fusion import DataFusion
from reconstruction.engine import ReconstructionEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test")


# ============================================================
#  生成假数据: 模拟小车沿一面墙行驶，激光雷达扫描墙面
# ============================================================

def make_fake_wall_point_cloud(
    car_x: float, car_y: float, car_yaw: float,
    wall_distance: float = 3.0,
    wall_width: float = 4.0,
    wall_height: float = 2.0,
    point_density: int = 2000,
) -> list[float]:
    """
    模拟激光雷达扫描一面墙。

    墙在车前方 wall_distance 米处，垂直于地面。
    返回: 传感器坐标系中的扁平点云 [x0,y0,z0, ...]
    """
    points = []

    for _ in range(point_density):
        # 墙上的随机点（在世界坐标系中，墙在 y = car_y + wall_distance）
        wx = car_x + np.random.uniform(-wall_width / 2, wall_width / 2)
        wy = car_y + wall_distance + np.random.normal(0, 0.02)  # 墙面有微小起伏
        wz = np.random.uniform(0, wall_height)

        # 加入一个凸起模拟裂缝/缺陷区域
        bump_cx = car_x + 0.5  # 凸起中心
        bump_cy = car_y + wall_distance
        dist_to_bump = math.sqrt((wx - bump_cx) ** 2 + (wz - 0.8) ** 2)
        if dist_to_bump < 0.3:
            wy += 0.05 * (1 - dist_to_bump / 0.3)  # 凸起 5cm

        # 变换到传感器坐标系: 世界 → 小车 → 传感器
        # 简化: 传感器在小车原点，所以直接做世界→小车变换
        dx = wx - car_x
        dy = wy - car_y
        # 旋转 -yaw（小车朝向）
        cos_yaw = math.cos(-car_yaw)
        sin_yaw = math.sin(-car_yaw)
        sx = dx * cos_yaw - dy * sin_yaw
        sy = dx * sin_yaw + dy * cos_yaw

        points.extend([sx, sy, wz])

    return points


def make_fake_frame(
    car_x: float, car_y: float, car_yaw: float, frame_idx: int
) -> SensorFrame:
    """生成一帧完整的假数据。"""

    # 小车世界位姿（车走直线，yaw=0 表示朝x正方向）
    frame = SensorFrame(
        frame_id=f"fake_{frame_idx:04d}",
        timestamp_ns=int(time.time_ns()),

        # 点云: 传感器坐标系
        point_cloud=PointCloudData(
            points=make_fake_wall_point_cloud(car_x, car_y, car_yaw),
        ),
        # 相机: 装在小车顶部中央
        camera_views=[
            CameraView(
                image_data=f"fake_image_{frame_idx}".encode(),
                width=1920,
                height=1080,
                camera_pose=Pose6DoF(
                    position=Vector3(x=0.0, y=0.0, z=0.3),   # 相机在车顶
                    rotation=Quaternion(),                     # 朝向正前方
                ),
            )
        ],
        # 小车全局位姿
        car_position=CarPosition(
            pose=Pose6DoF(
                position=Vector3(x=car_x, y=car_y, z=0.0),
                rotation=Quaternion(qw=1.0, qx=0.0, qy=0.0, qz=0.0),  # 无旋转
            ),
            timestamp_ns=int(time.time_ns()),
        ),
        # 运动学参数
        kinematics=KinematicsData(
            velocity=0.5,
            steering_angle=0.0,
            timestamp_ns=int(time.time_ns()),
        ),
    )

    # 自动计算 point_count
    frame.point_cloud.point_count = len(frame.point_cloud.points) // 3
    return frame


# ============================================================
#  主测试
# ============================================================

def main():
    print("=" * 60)
    print("  端到端测试: 三维重建管线")
    print("=" * 60)

    # ── 初始化 ──
    fusion = DataFusion(sensor_pose_in_body=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0])
    engine = ReconstructionEngine(
        voxel_size=0.02,             # 测试用稍大的体素，快一点
        rebuild_interval_frames=5,   # 每 5 帧重建一次
    )

    # ── 模拟小车行驶 20 帧 ──
    total_frames = 20
    success = 0
    skip = 0
    rebuilds = 0

    for i in range(total_frames):
        # 小车从 x=-5 走到 x=5
        car_x = -5.0 + i * 0.5
        car_y = 0.0

        raw = make_fake_frame(car_x, car_y, car_yaw=0.0, frame_idx=i)
        fused = fusion.process(raw)

        if fused is None:
            skip += 1
            continue

        prev_status = engine.get_result().status
        engine.add_frame(fused)
        curr_status = engine.get_result().status

        if prev_status == "accumulating" and curr_status == "completed":
            rebuilds += 1

        success += 1
        print(f"  Frame {i:3d}: car_x={car_x:.1f}  "
              f"points={fused.point_count:5d}  status={curr_status}")

    # ── 最终重建（如果还有未处理的帧）──
    # 触发一次手动重建：加一个空帧，或者直接调内部方法
    # engine 在设计上每 N 帧自动重建，最后一组可能不满 N 帧
    # 这里直接调内部方法完成最后的合并
    if engine._point_blocks and engine._status != "running":
        engine._rebuild()

    result = engine.get_result()

    # ── 结果检查 ──
    print()
    print("=" * 60)
    print("  测试结果")
    print("=" * 60)
    print(f"  总帧数:     {total_frames}")
    print(f"  成功融合:   {success}")
    print(f"  跳过:       {skip}")
    print(f"  重建次数:   {rebuilds}")
    print(f"  总点数:     {result.total_points}")
    print(f"  最终状态:   {result.status}")
    print(f"  网格顶点数: {result.mesh.vertex_count}")
    print(f"  网格面数:   {result.mesh.face_count}")
    print(f"  相机轨迹点: {len(result.camera_trail)}")

    # ── 保存 Mesh 到文件 ──
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    if result.mesh.vertex_count > 0:
        _save_mesh_ply(result, output_dir)
        print(f"\n  ✅ Mesh 已保存到: {output_dir}/test_mesh.ply")
        print(f"     可以用 CloudCompare / MeshLab 打开查看")
    else:
        print(f"\n  ❌ 重建失败: 没有生成网格顶点")

    # ── 保存重建结果的 JSON（不含 Mesh，太大了）─
    result_json = {
        "status": result.status,
        "total_frames": result.total_frames,
        "total_points": result.total_points,
        "mesh_vertices": result.mesh.vertex_count,
        "mesh_faces": result.mesh.face_count,
        "camera_trail_points": len(result.camera_trail),
        "cracks_count": len(result.cracks),
    }
    json_path = os.path.join(output_dir, "test_result.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result_json, f, indent=2, ensure_ascii=False)
    print(f"  📄 结果摘要已保存到: {json_path}")

    # ── 断言 ──
    assert success > 0, "没有成功融合任何帧"
    assert result.total_points > 0, "没有累积任何点"
    assert result.mesh.vertex_count > 100, f"网格顶点太少 ({result.mesh.vertex_count})，重建可能有问题"
    assert result.mesh.face_count > 100, f"网格面数太少 ({result.mesh.face_count})"
    assert len(result.camera_trail) > 0, "没有记录相机轨迹"

    print()
    print("  🎉 全部断言通过！管线正常工作。")
    print("=" * 60)


def _save_mesh_ply(result, output_dir: str) -> None:
    """把 MeshData 存成 PLY 文件，方便用外部工具检查。"""
    import open3d as o3d

    verts = np.array(result.mesh.vertices, dtype=np.float64).reshape(-1, 3)
    faces = np.array(result.mesh.faces, dtype=np.int32).reshape(-1, 3)

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(verts)
    mesh.triangles = o3d.utility.Vector3iVector(faces)
    mesh.compute_vertex_normals()

    ply_path = os.path.join(output_dir, "test_mesh.ply")
    o3d.io.write_triangle_mesh(ply_path, mesh)


if __name__ == "__main__":
    main()
