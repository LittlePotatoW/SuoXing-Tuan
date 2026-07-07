# ============================================================
# lidar_camera_fusion/main.py
# LiDAR-Camera Fusion 程序入口
#
# 从 config.yaml 加载参数，执行 3D 点云 → 2D 图像投影融合。
#
# 用法:
#   python main.py                       # 读取默认 config.yaml 运行
#   python main.py --demo                # 自动生成合成数据，无需任何硬件
#   python main.py path/to/config.yaml   # 指定配置文件
#
# ★ 参数调整指南（在哪里改参数）：
#   · 相机内参/外参/雷达参数 → 编辑 config.yaml，代码无需改动
#   · 需要改投影算法细节    → 编辑 lidar_camera_fusion.py
#   · 只想快速看效果        → python main.py --demo（零配置，自动合成数据）
# ============================================================

import sys
import tempfile
from pathlib import Path

import numpy as np
import cv2

# 将当前目录加入搜索路径
sys.path.insert(0, str(Path(__file__).parent))

from lidar_camera_fusion import LidarCameraFusion


# ============================================================
# Demo 模式 — 自动生成合成数据，用户无需准备任何文件
# ============================================================
#
# ★ 以下 _generate_demo_data() 仅用于快速体验。
#   正式使用时请编辑 config.yaml 填入真实传感器参数和文件路径，
#   然后运行: python main.py
# ============================================================

def _generate_demo_data() -> str:
    """生成合成点云 + 棋盘格图像 + 临时配置，返回配置文件路径。"""
    tmp_dir = Path(tempfile.mkdtemp(prefix="lidar_demo_"))
    data_dir = tmp_dir / "data"
    out_dir = tmp_dir / "output"
    data_dir.mkdir()
    out_dir.mkdir()

    # ---- 合成点云：5m 前方 30×20 网格 + 200 个随机散点 ----
    points = []
    for x in np.linspace(-3, 3, 30):
        for y in np.linspace(-2, 2, 20):
            points.append([x, y, 5.0])
    np.random.seed(42)
    scatter = np.random.randn(200, 3) * 0.8
    scatter[:, 2] = np.abs(scatter[:, 2]) + 4.0
    points.extend(scatter.tolist())
    points_arr = np.array(points, dtype=np.float32)

    # .bin 格式: x, y, z, intensity (4 × float32)
    bin_data = np.column_stack([
        points_arr,
        np.ones(len(points_arr), dtype=np.float32) * 0.5,
    ])
    pcd_path = str(data_dir / "demo.bin")
    bin_data.tofile(pcd_path)

    # ---- 合成图像：棋盘格 + 十字线（便于肉眼判断投影位置） ----
    img = np.full((480, 640, 3), 80, dtype=np.uint8)
    for row in range(0, 480, 60):
        for col in range(0, 640, 60):
            if (row // 60 + col // 60) % 2 == 0:
                y2 = min(row + 60, 480)
                x2 = min(col + 60, 640)
                img[row:y2, col:x2] = [120, 120, 120]
    cv2.line(img, (320, 0), (320, 480), (0, 0, 255), 1)
    cv2.line(img, (0, 240), (640, 240), (0, 0, 255), 1)
    cv2.circle(img, (320, 240), 8, (0, 255, 255), 1)
    img_path = str(data_dir / "demo.jpg")
    cv2.imwrite(img_path, img)

    # ---- 临时配置文件（内嵌，无需外部 config.yaml） ----
    config_content = f"""# ★ Demo 自动生成配置 — 参数说明见正式 config.yaml
input:
  pointcloud_path: "{pcd_path.replace(chr(92), '/')}"
  image_path: "{img_path.replace(chr(92), '/')}"
output:
  result_path: "{str(out_dir / 'result.jpg').replace(chr(92), '/')}"
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
  alpha: 0.5
  show_distance_legend: true
filter:
  enable_range_filter: true
  range_min: 0.1
  range_max: 25.0
  enable_fov_filter: true
"""
    config_path = str(tmp_dir / "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    print(f"[Demo] 合成数据已生成:")
    print(f"        点云: {pcd_path}  ({len(points_arr)} 个点)")
    print(f"        图像: {img_path}  (640×480)")
    print(f"        输出: {out_dir / 'result.jpg'}\n")

    return config_path


# ============================================================
# 主入口
# ============================================================

def main():
    """
    ★ 使用说明（在哪里改参数）：

    日常使用 —— 只需编辑 config.yaml：
      · camera.K          → 替换为你的相机内参
      · camera.dist_coeff → 替换为你的畸变系数
      · extrinsic.R / .T  → 替换为 LiDAR→相机的标定结果
      · input.*_path      → 替换为你的数据文件路径
      · visualization.*   → 调整可视化效果
      然后运行: python main.py

    快速验证 —— 不需要任何硬件：
      python main.py --demo

    修改投影算法 —— 编辑 lidar_camera_fusion.py：
      · project_points_to_image() → 投影管线
      · filter_pointcloud()       → 过滤规则
      · render_fusion()           → 渲染方式
    """
    print("=" * 60)
    print("  LiDAR-Camera Fusion — 激光雷达与相机数据融合")
    print("=" * 60)

    # ---- 解析命令行 ----
    if "--demo" in sys.argv:
        config_path = _generate_demo_data()
    elif len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
        config_path = sys.argv[1]
    else:
        config_path = str(Path(__file__).parent / "config.yaml")

    if not Path(config_path).exists():
        print(f"\n错误: 配置文件不存在 → {config_path}")
        print("  用法:")
        print("    python main.py              # 使用默认 config.yaml")
        print("    python main.py --demo       # 零配置，自动合成数据运行")
        print("    python main.py my_cfg.yaml  # 指定配置文件")
        sys.exit(1)

    print(f"配置文件: {config_path}\n")

    # ---- 数据文件存在性检查（demo 模式跳过） ----
    if "--demo" not in sys.argv:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        base_dir = Path(config_path).parent

        # ★ 数据路径解析：先在 config 的 input 中找，找不到就报错
        pcd_path = Path(cfg["input"]["pointcloud_path"])
        img_path = Path(cfg["input"]["image_path"])
        if not pcd_path.is_absolute():
            pcd_path = base_dir / pcd_path
        if not img_path.is_absolute():
            img_path = base_dir / img_path

        missing = []
        if not pcd_path.exists():
            missing.append(f"点云 → {pcd_path}")
        if not img_path.exists():
            missing.append(f"图像 → {img_path}")
        if missing:
            print("  数据文件未找到:")
            for m in missing:
                print(f"    ✗ {m}")
            print(f"\n  ★ 要运行此程序，你有两个选择：")
            print(f"    1. 编辑 config.yaml 的 input 部分，指向真实文件")
            print(f"    2. 运行 'python main.py --demo' 使用合成数据")
            print(f"    3. 运行 'python test_lidar_camera_fusion.py' 执行单元测试\n")
            sys.exit(1)

    # ---- 执行融合 ----
    fusion = LidarCameraFusion(str(config_path))
    result = fusion.run()

    print("\n完成。")
    return result


if __name__ == "__main__":
    main()
