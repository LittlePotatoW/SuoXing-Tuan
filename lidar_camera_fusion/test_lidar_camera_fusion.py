# ============================================================
# lidar_camera_fusion/test_lidar_camera_fusion.py
# 合成数据验证脚本 — 无需真实传感器即可验证投影管线
#
# 测试内容:
#   1. 内参矩阵构建
#   2. 欧拉角 → 旋转矩阵转换（正交性检查）
#   3. 四元数 ↔ 旋转矩阵（与 SuoXing-Tuan transform.py 对齐）
#   4. pose_to_matrix / transform_points（与 SuoXing-Tuan 对齐）
#   5. extrinsic_from_pose6dof 适配器
#   6. 3D → 2D 投影（已知点验证）
#   7. 畸变校正方向正确性
#   8. 图像边界裁剪
#   9. 空点云 / 全无效点的边界情况
#  10. 点云过滤 + 颜色映射 + 融合渲染
#  11. 完整流水线（LidarCameraFusion.run）
#
# 用法:
#   python test_lidar_camera_fusion.py
# ============================================================

import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import cv2

# 确保可以导入被测模块
sys.path.insert(0, str(Path(__file__).parent))

from lidar_camera_fusion import (
    # 参数构建
    build_intrinsic_matrix,
    euler_to_rotation,
    build_extrinsic,
    # 四元数工具 — 与 SuoXing-Tuan 对齐
    quat_to_rotation,
    rotation_to_quat,
    pose_to_matrix,
    transform_points,
    build_transformation_matrix,
    extrinsic_from_pose6dof,
    # 桥接函数 — 与 reconstruction 管线联动
    CameraIntrinsics,
    compute_lidar_to_camera_extrinsic,
    points_from_flat_list,
    uv_to_depth_map,
    backproject_pixel_to_3d,
    backproject_bbox_to_3d,
    # 投影核心
    project_points_to_image,
    filter_pointcloud,
    # 可视化
    color_map_distance,
    render_fusion,
    # 主流程
    LidarCameraFusion,
    load_config,
)

# ============================================================================
# 测试工具
# ============================================================================

_passed = 0
_failed = 0


def check(name: str, condition: bool, detail: str = ""):
    """简单的测试断言。"""
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  ✓ {name}")
    else:
        _failed += 1
        print(f"  ✗ {name}  FAILED{': ' + detail if detail else ''}")


def approx(a, b, tol=1e-6):
    """浮点数近似比较。"""
    return abs(float(a) - float(b)) < tol


def approx_array(A, B, tol=1e-6):
    """数组逐元素近似比较。"""
    return np.allclose(A, B, atol=tol)


# ============================================================================
# 测试用例
# ============================================================================

def test_intrinsic_matrix():
    """测试内参矩阵构建。"""
    print("\n── 测试 1: 内参矩阵构建 ──")

    K_list = [[800.0, 0.0, 640.0],
              [0.0, 800.0, 480.0],
              [0.0, 0.0, 1.0]]
    K = build_intrinsic_matrix(K_list)

    check("shape (3,3)", K.shape == (3, 3))
    check("fx = 800", approx(K[0, 0], 800))
    check("cx = 640", approx(K[0, 2], 640))
    check("fy = 800", approx(K[1, 1], 800))
    check("cy = 480", approx(K[1, 2], 480))
    check("K[2,2] = 1", approx(K[2, 2], 1.0))

    # 错误尺寸应抛异常
    try:
        build_intrinsic_matrix([[1, 2], [3, 4]])
        check("错误尺寸应抛异常", False, "未抛出异常")
    except ValueError:
        check("错误尺寸应抛异常", True)


def test_euler_rotation():
    """测试欧拉角 → 旋转矩阵转换。"""
    print("\n── 测试 2: 欧拉角 → 旋转矩阵 ──")

    # 零旋转 → 单位阵
    R = euler_to_rotation(0.0, 0.0, 0.0)
    check("零旋转=单位阵", approx_array(R, np.eye(3)))

    # 单轴 90° 绕 Z 轴
    Rz90 = euler_to_rotation(0.0, 0.0, np.pi / 2)
    expected_z90 = np.array([[0.0, -1.0, 0.0],
                              [1.0,  0.0, 0.0],
                              [0.0,  0.0, 1.0]])
    check("Z轴+90°", approx_array(Rz90, expected_z90))

    # 旋转矩阵应为正交矩阵: R @ R^T = I
    R_arb = euler_to_rotation(0.3, -0.5, 1.2)
    should_be_I = R_arb @ R_arb.T
    check("正交性 R@R.T=I", approx_array(should_be_I, np.eye(3), tol=1e-10))

    # 行列式应为 +1 (右手系)
    check("det(R)=1", approx(np.linalg.det(R_arb), 1.0, tol=1e-10))


def test_build_extrinsic():
    """测试外参构建（矩阵模式与欧拉角模式）。"""
    print("\n── 测试 3: 外参构建 ──")

    # 矩阵模式
    cfg_matrix = {
        "use_euler": False,
        "R": [[0.0, -1.0, 0.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]],
        "T": [0.5, 0.0, -0.2],
    }
    R, T = build_extrinsic(cfg_matrix)
    check("矩阵模式 R shape", R.shape == (3, 3))
    check("矩阵模式 T", approx_array(T, [0.5, 0.0, -0.2]))

    # 欧拉角模式
    cfg_euler = {
        "use_euler": True,
        "euler": {"roll": 0.0, "pitch": 0.0, "yaw": np.pi / 2},
        "T": [0.0, 0.0, 0.0],
    }
    R_euler, T_euler = build_extrinsic(cfg_euler)
    # yaw=π/2 → Rz(90°) 同上面的 expected_z90
    expected = np.array([[0.0, -1.0, 0.0],
                          [1.0,  0.0, 0.0],
                          [0.0,  0.0, 1.0]])
    check("欧拉角模式 R", approx_array(R_euler, expected))


def test_quat_to_rotation():
    """测试四元数 → 旋转矩阵（与 SuoXing-Tuan transform.py 对齐）。"""
    print("\n── 测试 3b: 四元数 → 旋转矩阵 ──")

    # 单位四元数 → 单位阵
    R = quat_to_rotation(1.0, 0.0, 0.0, 0.0)
    check("单位四元数→单位阵", approx_array(R, np.eye(3)))

    # 绕 Z 轴 90°: q = cos(45°) + 0i + 0j + sin(45°)k
    import math
    half = math.pi / 4  # 45°
    Rz90 = quat_to_rotation(math.cos(half), 0.0, 0.0, math.sin(half))
    expected = euler_to_rotation(0.0, 0.0, math.pi / 2)
    check("四元数(Z+90°)=欧拉角(Z+90°)", approx_array(Rz90, expected, tol=1e-10))

    # 正交性
    R_arb = quat_to_rotation(0.7071, 0.2, -0.3, 0.5)
    check("四元数→R 正交", approx_array(R_arb @ R_arb.T, np.eye(3), tol=1e-10))


def test_rotation_to_quat():
    """测试旋转矩阵 → 四元数往返（与 SuoXing-Tuan fusion.py 对齐）。"""
    print("\n── 测试 3c: 旋转矩阵 ↔ 四元数往返 ──")

    # 单位阵
    q = rotation_to_quat(np.eye(3))
    check("I→quat: qw≈1", abs(q[0] - 1.0) < 1e-10)
    check("I→quat: qx≈0", abs(q[1]) < 1e-10)

    # 往返: R → quat → R' 应相等
    import math
    R_orig = euler_to_rotation(0.2, -0.5, 1.3)
    q_roundtrip = rotation_to_quat(R_orig)
    R_back = quat_to_rotation(*q_roundtrip)
    check("R→quat→R 往返", approx_array(R_orig, R_back, tol=1e-10))

    # Z 轴 90° 往返
    Rz90 = euler_to_rotation(0.0, 0.0, math.pi / 2)
    qz = rotation_to_quat(Rz90)
    Rz_back = quat_to_rotation(*qz)
    check("Z90→quat→Z90 往返", approx_array(Rz90, Rz_back, tol=1e-10))


def test_pose_to_matrix():
    """测试 pose_to_matrix（与 SuoXing-Tuan transform.py 对齐）。"""
    print("\n── 测试 3d: pose_to_matrix ──")

    # 零位姿
    T = pose_to_matrix([0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0])
    check("零位姿=I_4x4", approx_array(T, np.eye(4)))

    # 有平移的位姿
    T2 = pose_to_matrix([1.0, 2.0, 3.0], [1.0, 0.0, 0.0, 0.0])
    check("平移部分正确", approx_array(T2[:3, 3], [1.0, 2.0, 3.0]))
    check("旋转部分=I", approx_array(T2[:3, :3], np.eye(3)))


def test_transform_points_func():
    """测试 transform_points（与 SuoXing-Tuan transform.py 对齐）。"""
    print("\n── 测试 3e: transform_points ──")

    # 平移变换
    T = np.eye(4)
    T[:3, 3] = [10.0, 0.0, 0.0]
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]])
    result = transform_points(pts, T)
    check("平移: [0,0,0]→[10,0,0]", approx_array(result[0], [10.0, 0.0, 0.0]))
    check("平移: [1,2,3]→[11,2,3]", approx_array(result[1], [11.0, 2.0, 3.0]))

    # 空点云
    empty = np.empty((0, 3))
    result_empty = transform_points(empty, T)
    check("空点云返回空", len(result_empty) == 0)

    # 与手动 R@P+T 对比
    R = euler_to_rotation(0.3, -0.2, 0.7)
    t = np.array([0.5, -0.3, 1.2])
    T_4x4 = build_transformation_matrix(R, t)
    pts2 = np.random.randn(100, 3)
    manual = (R @ pts2.T).T + t
    check("等价于 R@P+T", approx_array(transform_points(pts2, T_4x4), manual))


def test_extrinsic_from_pose6dof():
    """测试 Pose6DoF 适配器。"""
    print("\n── 测试 3f: extrinsic_from_pose6dof 适配器 ──")

    import math
    # 模拟 SuoXing-Tuan 的 Pose6DoF 格式
    R, T = extrinsic_from_pose6dof(
        position=[0.5, 0.0, -0.2],
        rotation_quat=[math.cos(math.pi/4), 0.0, 0.0, math.sin(math.pi/4)],
    )
    check("R shape (3,3)", R.shape == (3, 3))
    check("T = [0.5,0,-0.2]", approx_array(T, [0.5, 0.0, -0.2]))
    # 验证 R 是正交矩阵
    check("R 正交", approx_array(R @ R.T, np.eye(3), tol=1e-10))


def test_build_extrinsic_quaternion():
    """测试外参构建 — 四元数模式。"""
    print("\n── 测试 3g: 外参构建 — 四元数模式 ──")

    import math
    cfg = {
        "use_quaternion": True,
        "quaternion": {"qw": math.cos(math.pi/4), "qx": 0.0,
                       "qy": 0.0, "qz": math.sin(math.pi/4)},
        "T": [0.1, 0.2, 0.3],
    }
    R, T = build_extrinsic(cfg)
    check("四元数模式 T", approx_array(T, [0.1, 0.2, 0.3]))
    # 应该是绕 Z 轴 90° 的旋转
    expected_R = euler_to_rotation(0.0, 0.0, math.pi / 2)
    check("四元数模式 R=Z90", approx_array(R, expected_R, tol=1e-10))


def test_compute_lidar_to_camera_extrinsic():
    """测试从两个 Pose6DoF 推算 LiDAR→相机外参。"""
    print("\n── 测试 3h: compute_lidar_to_camera_extrinsic ──")

    # LiDAR 在车体原点，相机在车体前方 0.5m
    lidar_pose = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]       # 原点
    cam_pose = [0.5, 0.0, 0.3, 1.0, 0.0, 0.0, 0.0]          # 前 0.5m, 高 0.3m

    R, T = compute_lidar_to_camera_extrinsic(lidar_pose, cam_pose)

    # LiDAR 原点在相机坐标系: [0,0,0] → 相机应看到 LiDAR 在 (-0.5, 0, -0.3)
    # 即 T 应该 ≈ [-0.5, 0, -0.3]
    check("T ≈ [-0.5,0,-0.3]", approx_array(T, [-0.5, 0.0, -0.3], tol=1e-10))
    check("R = I (无旋转)", approx_array(R, np.eye(3), tol=1e-10))


def test_camera_intrinsics():
    """测试 CameraIntrinsics 数据结构。"""
    print("\n── 测试 3i: CameraIntrinsics ──")

    intrinsics = CameraIntrinsics(
        K=[[800, 0, 320], [0, 800, 240], [0, 0, 1]],
        image_width=640, image_height=480,
    )
    check("K shape (3,3)", intrinsics.K.shape == (3, 3))
    check("dist_coeff 默认零", approx_array(intrinsics.dist_coeff, np.zeros(5)))
    check("image_width", intrinsics.image_width == 640)

    # 自定义畸变
    i2 = CameraIntrinsics(
        K=[[1200, 0, 960], [0, 1200, 540], [0, 0, 1]],
        image_width=1920, image_height=1080,
        dist_coeff=[-0.3, 0.1, 0, 0, 0],
    )
    check("自定义畸变", approx(i2.dist_coeff[0], -0.3))


def test_points_from_flat_list():
    """测试扁平点云列表 → numpy 数组转换。"""
    print("\n── 测试 3j: points_from_flat_list ──")

    flat = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    pts = points_from_flat_list(flat, 2)
    check("shape=(2,3)", pts.shape == (2, 3))
    check("第1点 [1,2,3]", approx_array(pts[0], [1, 2, 3]))
    check("第2点 [4,5,6]", approx_array(pts[1], [4, 5, 6]))

    # 空列表
    empty = points_from_flat_list([], 0)
    check("空列表→(0,3)", empty.shape == (0, 3))


def test_uv_to_depth_map():
    """测试稀疏投影 → 稠密深度图转换。"""
    print("\n── 测试 3k: uv_to_depth_map ──")

    uv = np.array([[100.0, 200.0], [300.0, 400.0], [100.0, 200.0]])
    depths = np.array([5.0, 10.0, 3.0])  # 第3个与第1个同像素，但更近

    depth_map = uv_to_depth_map(uv, depths, 640, 480)

    check("shape=(480,640)", depth_map.shape == (480, 640))
    # 同像素取最近值
    check("重叠像素取最小值", approx(depth_map[200, 100], 3.0))
    check("孤立像素", approx(depth_map[400, 300], 10.0))
    check("无投影处为0", approx(depth_map[0, 0], 0.0))


def test_backproject_pixel_to_3d():
    """测试反向投影：像素+深度 → 世界3D点。"""
    print("\n── 测试 3l: backproject_pixel_to_3d ──")

    K = np.array([[800.0, 0.0, 320.0],
                   [0.0, 800.0, 240.0],
                   [0.0, 0.0, 1.0]])
    R = np.eye(3)
    T = np.zeros(3)

    # 像素 (320, 240) 即光心，深度 5m → 世界 (0, 0, 5)
    p3 = backproject_pixel_to_3d(320.0, 240.0, 5.0, K, R, T)
    check("光心点→(0,0,5)", approx_array(p3, [0.0, 0.0, 5.0], tol=1e-6))

    # 偏移像素: (320+160, 240) = (480, 240), depth=5 → x = (480-320)*5/800 = 1.0
    p3_offset = backproject_pixel_to_3d(480.0, 240.0, 5.0, K, R, T)
    check("偏移点→(1,0,5)", approx_array(p3_offset, [1.0, 0.0, 5.0], tol=1e-6))

    # 带旋转: R 绕 Z 90°, 点 (0, 0, 5) → 世界 (0, 0, 5)（Z轴不变）
    Rz90 = euler_to_rotation(0.0, 0.0, np.pi / 2)
    p3_rot = backproject_pixel_to_3d(320.0, 240.0, 5.0, K, Rz90, np.zeros(3))
    # 相机系 (0,0,5) → Rz90 @ [0,0,5] = [0, 0, 5]
    check("旋转后(0,0,5)不变", approx_array(p3_rot, [0.0, 0.0, 5.0], tol=1e-6))


def test_backproject_bbox_to_3d():
    """测试 2D bbox → 3D 包围盒。"""
    print("\n── 测试 3m: backproject_bbox_to_3d ──")

    # 构造一个简单的深度图：中心区域深度 = 5m
    depth_map = np.zeros((480, 640), dtype=np.float64)
    depth_map[200:280, 280:360] = 5.0  # bbox 中心 80×80 区域

    K = np.array([[800.0, 0.0, 320.0],
                   [0.0, 800.0, 240.0],
                   [0.0, 0.0, 1.0]])
    R = np.eye(3)
    T = np.zeros(3)

    bbox_3d = backproject_bbox_to_3d([280, 200, 360, 280], depth_map, K, R, T)

    check("返回6个值", len(bbox_3d) == 6)
    if len(bbox_3d) == 6:
        check("centerZ≈5", abs(bbox_3d[2] - 5.0) < 0.1,
              f"got {bbox_3d[2]:.2f}")
        check("width>0", bbox_3d[3] > 0)
        check("height>0", bbox_3d[4] > 0)

    # 空 bbox（无有效深度）
    empty = backproject_bbox_to_3d([0, 0, 10, 10], depth_map, K, R, T)
    check("无有效深度→空", empty == [])


def test_projection_no_distortion():
    """测试无畸变投影：已知点应落在预期像素位置。"""
    print("\n── 测试 4: 无畸变投影基本正确性 ──")

    # 针孔相机: fx=800, fy=800, cx=640, cy=480, 图像 1280x960
    K = np.array([[800.0, 0.0, 640.0],
                   [0.0, 800.0, 480.0],
                   [0.0, 0.0, 1.0]])
    dist = np.zeros(5)             # 无畸变
    R = np.eye(3)                   # LiDAR = 相机坐标系
    T = np.array([0.0, 0.0, 0.0])

    # 点 (0, 0, 5) — 正前方 5m，应投影到图像中心 (640, 480)
    points = np.array([[0.0, 0.0, 5.0]])
    uv, d, mask = project_points_to_image(points, K, R, T, dist, 1280, 960)

    check("正前方点投影成功", len(uv) == 1)
    if len(uv) == 1:
        check("u ≈ 640", abs(uv[0, 0] - 640.0) < 1.0,
              f"got {uv[0, 0]:.2f}")
        check("v ≈ 480", abs(uv[0, 1] - 480.0) < 1.0,
              f"got {uv[0, 1]:.2f}")
        check("深度 = 5.0", approx(d[0], 5.0))

    # 点 (0.8, 0.6, 2) — u=640+800*0.8/2=960, v=480+800*0.6/2=720
    points2 = np.array([[0.8, 0.6, 2.0]])
    uv2, d2, _ = project_points_to_image(points2, K, R, T, dist, 1280, 960)
    check("偏移点投影成功", len(uv2) == 1)
    if len(uv2) == 1:
        check("u ≈ 960", abs(uv2[0, 0] - 960.0) < 1.0,
              f"got {uv2[0, 0]:.2f}")
        check("v ≈ 720", abs(uv2[0, 1] - 720.0) < 1.0,
              f"got {uv2[0, 1]:.2f}")


def test_projection_behind_camera():
    """测试相机后方点被正确剔除。"""
    print("\n── 测试 5: 相机后方点过滤 ──")

    K = np.eye(3); K[0, 0] = K[1, 1] = 800
    K[0, 2] = 640; K[1, 2] = 480
    dist = np.zeros(5)
    R = np.eye(3)
    T = np.array([0.0, 0.0, 0.0])

    # 混合前方和后方的点
    points = np.array([
        [0.0, 0.0, 5.0],    # 前方 ✓
        [1.0, 0.0, -1.0],   # 后方 ✗
        [0.0, 1.0, 0.0],    # Z=0 (在相机平面上) ✗
        [-1.0, 0.0, 3.0],   # 前方 ✓
    ])
    uv, d, mask = project_points_to_image(points, K, R, T, dist, 1280, 960)

    check("2个点投影成功", len(uv) == 2)
    check("mask[0] True (前方5m)", mask[0])
    check("mask[1] False (后方-1m)", not mask[1])
    check("mask[2] False (Z=0)", not mask[2])
    check("mask[3] True (前方3m)", mask[3])


def test_projection_boundary():
    """测试图像边界裁剪。"""
    print("\n── 测试 6: 图像边界裁剪 ──")

    K = np.array([[800.0, 0.0, 640.0],
                   [0.0, 800.0, 480.0],
                   [0.0, 0.0, 1.0]])
    dist = np.zeros(5)
    R = np.eye(3)
    T = np.array([0.0, 0.0, 0.0])

    # 生成稀疏网格覆盖视场角
    points = []
    for x in np.linspace(-5, 5, 11):
        for y in np.linspace(-5, 5, 11):
            points.append([x, y, 3.0])
    points = np.array(points)

    uv, d, mask = project_points_to_image(points, K, R, T, dist, 1280, 960)

    # 确保所有返回的 uv 都在图像边界内
    if len(uv) > 0:
        check("所有u在[0,1280)内",
              np.all(uv[:, 0] >= 0) and np.all(uv[:, 0] < 1280))
        check("所有v在[0,960)内",
              np.all(uv[:, 1] >= 0) and np.all(uv[:, 1] < 960))


def test_projection_with_distortion():
    """测试畸变校正方向正确性。"""
    print("\n── 测试 7: 畸变校正方向 ──")

    K = np.array([[800.0, 0.0, 640.0],
                   [0.0, 800.0, 480.0],
                   [0.0, 0.0, 1.0]])

    # 正畸变(k1>0)：枕形畸变，边缘点被"推离"中心
    # OpenCV 模型: x' = x * (1 + k1*r² + ...), k1>0 时放大率增大 → u 增大
    dist_pos = np.array([0.5, 0.0, 0.0, 0.0, 0.0])  # k1 > 0
    dist_zero = np.zeros(5)

    # 取一个偏离光轴的点
    point = np.array([[1.6, 0.0, 2.0]])  # 无畸变: u=640+800*1.6/2=1280 (恰好右边缘)
    uv_no, _, _ = project_points_to_image(point, K, np.eye(3), np.zeros(3),
                                           dist_zero, 2000, 960)
    uv_k1, _, _ = project_points_to_image(point, K, np.eye(3), np.zeros(3),
                                           dist_pos, 2000, 960)

    if len(uv_no) == 1 and len(uv_k1) == 1:
        # k1 > 0 → 枕形畸变 → 边缘点被推离中心 → u 增大
        check("k1>0 枕形畸变向外推", uv_k1[0, 0] > uv_no[0, 0],
              f"no dist u={uv_no[0,0]:.1f}, k1=0.5 u={uv_k1[0,0]:.1f}")


def test_empty_and_edge_cases():
    """测试边界情况。"""
    print("\n── 测试 8: 边界情况 ──")

    K = np.eye(3); K[0, 0] = K[1, 1] = 800
    K[0, 2] = 640; K[1, 2] = 480
    dist = np.zeros(5)
    R = np.eye(3)
    T = np.zeros(3)

    # 空点云
    uv, d, mask = project_points_to_image(
        np.empty((0, 3)), K, R, T, dist, 1280, 960
    )
    check("空点云返回空uv", len(uv) == 0)
    check("空点云返回空d", len(d) == 0)

    # 全部在相机后方
    points_behind = np.array([[1.0, 0.0, -1.0], [0.0, 1.0, -2.0]])
    uv2, d2, mask2 = project_points_to_image(
        points_behind, K, R, T, dist, 1280, 960
    )
    check("全后方点返回空uv", len(uv2) == 0)
    check("全后方点mask全False", not np.any(mask2))


def test_filter_pointcloud():
    """测试点云过滤功能。"""
    print("\n── 测试 9: 点云过滤 ──")

    R = np.eye(3)
    T = np.array([0.0, 0.0, 0.0])

    # 混合点: 近、中、远、极远
    points = np.array([
        [0.0, 0.0, 0.5],     # 在范围内
        [0.0, 0.0, 10.0],    # 在范围内
        [0.0, 0.0, 30.0],    # 超出 max_range (25m)
        [0.0, 0.0, 0.05],    # 低于 min_range (0.1m)
    ])

    filter_cfg = {
        "enable_range_filter": True,
        "range_min": 0.1,
        "range_max": 25.0,
        "enable_fov_filter": True,
    }

    filtered, keep = filter_pointcloud(points, filter_cfg, R, T)

    check("保留2个点", len(filtered) == 2)
    check("第1个点保留", keep[0])
    check("第2个点保留", keep[1])
    check("第3个点剔除(>25m)", not keep[2])
    check("第4个点剔除(<0.1m)", not keep[3])

    # Z<0 点应被 FOV 过滤剔除
    points_fov = np.array([
        [0.0, 0.0, 5.0],     # 前方 ✓
        [1.0, 0.0, -5.0],    # 后方 ✗
    ])
    filtered2, keep2 = filter_pointcloud(points_fov, filter_cfg, R, T)
    check("FOV: 仅保留前方", len(filtered2) == 1 and keep2[0] and not keep2[1])


def test_color_map():
    """测试距离颜色映射。"""
    print("\n── 测试 10: 距离颜色映射 ──")

    depths = np.array([1.0, 5.0, 10.0, 20.0])
    colors = color_map_distance(depths, d_min=1.0, d_max=20.0)

    check("返回(N,3)形状", colors.shape == (4, 3))
    check("数据类型 uint8", colors.dtype == np.uint8)
    check("值域 [0,255]", colors.min() >= 0 and colors.max() <= 255)

    # 最近和最远的颜色应不同
    check("近≠远颜色", not np.allclose(colors[0], colors[-1]))


def test_render_fusion():
    """测试融合渲染输出尺寸和格式正确。"""
    print("\n── 测试 11: 融合渲染 ──")

    # 创建一张纯色测试图
    image = np.full((480, 640, 3), 128, dtype=np.uint8)

    # 几个投影点
    uv = np.array([[320.0, 240.0], [100.0, 100.0], [500.0, 400.0]])
    depths = np.array([2.0, 8.0, 15.0])

    vis_cfg = {
        "color_map": "distance",
        "point_radius": 2,
        "alpha": 0.5,
        "show_distance_legend": True,
    }

    result = render_fusion(image, uv, depths, vis_cfg)

    check("输出尺寸不变", result.shape == image.shape)
    check("数据类型 uint8", result.dtype == np.uint8)
    check("不是纯色图(有点被绘制)", not np.allclose(result, image))

    # 纯色模式
    vis_cfg2 = {"color_map": "solid", "solid_color": [0, 255, 0],
                "point_radius": 1, "alpha": 0.8,
                "show_distance_legend": False}
    result2 = render_fusion(image, uv, depths, vis_cfg2)
    check("纯色模式输出尺寸不变", result2.shape == image.shape)


def test_full_pipeline_with_temp_config():
    """使用临时配置文件测试完整流水线。"""
    print("\n── 测试 12: 完整流水线（临时配置） ──")

    # 创建临时目录
    tmp_dir = Path(tempfile.mkdtemp(prefix="lidar_fusion_test_"))
    data_dir = tmp_dir / "data"
    out_dir = tmp_dir / "output"
    data_dir.mkdir()
    out_dir.mkdir()

    # 生成合成点云（一个简单平面网格）
    points_xyz = []
    for x in np.linspace(-3, 3, 20):
        for y in np.linspace(-2, 2, 15):
            points_xyz.append([x, y, 5.0])   # 5m 前方的平面
    points_xyz = np.array(points_xyz, dtype=np.float32)

    # 保存为 .bin 格式 (KITTI: x, y, z, intensity)
    bin_data = np.column_stack([
        points_xyz,
        np.ones(len(points_xyz), dtype=np.float32) * 0.5  # 强度
    ])
    pcd_path = str(data_dir / "test.bin")
    bin_data.tofile(pcd_path)

    # 生成合成图像
    img = np.full((480, 640, 3), 100, dtype=np.uint8)
    # 画一个十字线便于判断对齐
    cv2.line(img, (320, 0), (320, 480), (200, 200, 200), 1)
    cv2.line(img, (0, 240), (640, 240), (200, 200, 200), 1)
    img_path = str(data_dir / "test.jpg")
    cv2.imwrite(img_path, img)

    # 生成临时配置文件（使用正斜杠避免 Windows 路径中的反斜杠被 YAML 误解析）
    config_content = f"""# 测试用临时配置
input:
  pointcloud_path: "{Path(pcd_path).as_posix()}"
  image_path: "{Path(img_path).as_posix()}"
output:
  result_path: "{out_dir.as_posix()}/result.jpg"
  save_colored_pcd: false
camera:
  image_width: 640
  image_height: 480
  K:
    - [800.0, 0.0, 320.0]
    - [0.0, 800.0, 240.0]
    - [0.0, 0.0, 1.0]
  dist_coeff: [0.0, 0.0, 0.0, 0.0, 0.0]
lidar:
  model: "LT-R1"
  laser_wavelength: 905
  max_range: 25.0
  min_range: 0.1
  horizontal_fov: 270.0
  scan_frequency: 10.0
  angle_resolution: 0.12
  distance_accuracy: 0.02
  data_rate: 30000
extrinsic:
  use_euler: false
  R:
    - [1.0, 0.0, 0.0]
    - [0.0, 1.0, 0.0]
    - [0.0, 0.0, 1.0]
  T: [0.0, 0.0, 0.0]
visualization:
  point_radius: 1
  color_map: "distance"
  solid_color: [0, 255, 0]
  alpha: 0.6
  show_distance_legend: false
filter:
  enable_range_filter: true
  range_min: 0.1
  range_max: 25.0
  enable_fov_filter: true
"""
    config_path = str(tmp_dir / "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    # 运行完整流水线
    try:
        fusion = LidarCameraFusion(config_path)
        result = fusion.run()

        check("流水线返回图像", isinstance(result, np.ndarray))
        check("输出尺寸 480×640", result.shape == (480, 640, 3))
        check("结果文件已生成", (out_dir / "result.jpg").exists())

        # 验证结果图上的确有投影点（不完全等于原始底图）
        # 点应该投射到图像中心附近
        check("有投影点渲染", not np.allclose(result, img, atol=5))
    except Exception as e:
        check(f"流水线不应抛异常", False, str(e))

    # 清理
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================================
# 主入口
# ============================================================================

def main():
    print("=" * 60)
    print("  LiDAR-Camera Fusion — 单元测试")
    print("=" * 60)

    tests = [
        ("内参矩阵构建", test_intrinsic_matrix),
        ("欧拉角→旋转矩阵", test_euler_rotation),
        ("外参构建 (矩阵/欧拉角)", test_build_extrinsic),
        ("四元数→旋转矩阵", test_quat_to_rotation),
        ("旋转矩阵↔四元数往返", test_rotation_to_quat),
        ("pose_to_matrix", test_pose_to_matrix),
        ("transform_points", test_transform_points_func),
        ("extrinsic_from_pose6dof", test_extrinsic_from_pose6dof),
        ("外参构建 (四元数模式)", test_build_extrinsic_quaternion),
        ("推算 LiDAR→相机外参", test_compute_lidar_to_camera_extrinsic),
        ("CameraIntrinsics", test_camera_intrinsics),
        ("points_from_flat_list", test_points_from_flat_list),
        ("uv_to_depth_map", test_uv_to_depth_map),
        ("backproject_pixel_to_3d", test_backproject_pixel_to_3d),
        ("backproject_bbox_to_3d", test_backproject_bbox_to_3d),
        ("无畸变投影正确性", test_projection_no_distortion),
        ("相机后方点过滤", test_projection_behind_camera),
        ("图像边界裁剪", test_projection_boundary),
        ("畸变校正方向", test_projection_with_distortion),
        ("边界情况 (空点云/全后方)", test_empty_and_edge_cases),
        ("点云过滤", test_filter_pointcloud),
        ("距离颜色映射", test_color_map),
        ("融合渲染", test_render_fusion),
        ("完整流水线 (临时配置)", test_full_pipeline_with_temp_config),
    ]

    for name, fn in tests:
        fn()

    # ---- 总结 ----
    print("\n" + "=" * 60)
    total = _passed + _failed
    print(f"  总计: {total}  |  通过: {_passed}  |  失败: {_failed}")
    if _failed == 0:
        print("  全部通过 ✓")
    else:
        print(f"  有 {_failed} 项未通过 ✗")
    print("=" * 60)

    return _failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
