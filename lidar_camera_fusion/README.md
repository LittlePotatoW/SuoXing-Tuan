# LiDAR-Camera Fusion

激光雷达（LiDAR）点云与相机图像数据的参数对齐与融合工具。

将 3D 点云通过相机内参和外参（旋转矩阵 R + 平移向量 T）精确投影到 2D 图像平面上，生成融合可视化结果，用于直观检验传感器标定精度。

---

## 目录结构

```
lidar_camera_fusion/
├── main.py                       # 程序入口
├── lidar_camera_fusion.py        # 核心融合模块（读取 / 投影 / 可视化）
├── config.yaml                   # 参数配置文件 ★ 所有关键参数在此调整
├── requirements.txt              # Python 依赖清单
├── test_lidar_camera_fusion.py   # 单元测试（合成数据，无需传感器）
├── README.md                     # 本文档
├── data/                         # 输入数据目录（自行创建）
│   ├── pointcloud.pcd            #   点云文件
│   └── image.jpg                 #   图像文件
└── output/                       # 输出目录（自动创建）
    └── fusion_result.jpg         #   融合结果图
```

---

## 环境要求

- **Python** ≥ 3.8
- **依赖库**：

| 库 | 用途 | 安装命令 |
|---|---|---|
| `numpy` | 矩阵运算 | `pip install numpy` |
| `opencv-python` | 图像读写、畸变校正、可视化 | `pip install opencv-python` |
| `pyyaml` | 配置文件解析 | `pip install pyyaml` |
| `open3d` *(可选)* | .pcd 点云读取、带颜色点云保存 | `pip install open3d` |

### 一键安装

```bash
pip install numpy opencv-python pyyaml open3d
```

> **注意**：若无法安装 `open3d`，程序会自动回退为纯 Python 解析 ASCII 格式的 .pcd 文件。但推荐安装以获得完整功能支持（二进制 PCD、点云保存等）。

---

## 快速开始

### 1. 修改配置文件

编辑 `config.yaml`，将以下参数替换为实际传感器的标定值：

```yaml
# 文件路径
input:
  pointcloud_path: "./data/pointcloud.pcd"
  image_path:      "./data/image.jpg"

# 相机内参（必须替换为真实值！）
camera:
  K:
    - [fx,  0, cx]      # ← 你的相机焦距和主点
    - [ 0, fy, cy]
    - [ 0,  0,  1]
  dist_coeff: [k1, k2, p1, p2, k3]   # ← 你的畸变系数

# 外参（必须替换为真实值！）
extrinsic:
  R:                    # ← LiDAR → 相机的旋转矩阵
    - [r11, r12, r13]
    - [r21, r22, r23]
    - [r31, r32, r33]
  T: [tx, ty, tz]       # ← LiDAR → 相机的平移向量 (米)
```

> **提示**：如果不确定外参矩阵的格式，也可以使用欧拉角填写（将 `use_euler` 设为 `true`）。

### 2. 准备数据

将点云文件（`.pcd` 或 `.bin`）和图像文件（`.jpg` 或 `.png`）放入 `data/` 目录。

### 3. 运行

```bash
python main.py                    # 使用默认 config.yaml
python main.py my_config.yaml     # 指定其他配置文件
```

### 4. 查看结果

打开 `output/fusion_result.jpg`，检查点云投影是否准确对齐到图像中的物体上。

---

## 配置文件说明

### 关键参数解释

| 参数 | 含义 | 注意事项 |
|---|---|---|
| `camera.K` | 相机内参矩阵 (3×3) | `fx, fy` 为焦距（像素），`cx, cy` 为主点坐标 |
| `camera.dist_coeff` | 畸变系数 `[k1, k2, p1, p2, k3]` | OpenCV 标准模型：径向 (k1, k2, k3) + 切向 (p1, p2) |
| `extrinsic.R` | 旋转矩阵 (3×3) | LiDAR 坐标系 → 相机坐标系的旋转变换 |
| `extrinsic.T` | 平移向量 `[tx, ty, tz]` | LiDAR 原点在相机坐标系中的位置 (米) |
| `lidar.max_range` | 最大探测距离 (m) | 超出此距离的点将被过滤 |
| `lidar.horizontal_fov` | 水平视场角 (°) | LT-R1 为 270° |

### 外参的两种填写方式

**方式一：旋转矩阵**（`use_euler: false`）
```yaml
extrinsic:
  use_euler: false
  R:
    - [ 0.0, -1.0,  0.0]
    - [ 0.0,  0.0, -1.0]
    - [ 1.0,  0.0,  0.0]
  T: [0.1, 0.0, -0.3]
```

**方式二：欧拉角**（`use_euler: true`）
```yaml
extrinsic:
  use_euler: true
  euler:
    roll:  0.0      # 弧度
    pitch: 0.0
    yaw:   1.5708   # π/2
  T: [0.1, 0.0, -0.3]
```

旋转顺序为 ZYX（yaw → pitch → roll）。

---

## 可视化选项

通过 `config.yaml` 中的 `visualization` 节点调整：

```yaml
visualization:
  point_radius: 2            # 投影点大小（像素）
  color_map: "distance"      # "distance"（按距离着色）/ "solid"（纯色）
  solid_color: [0, 255, 0]   # 纯色模式的颜色 (BGR)
  alpha: 0.6                 # 点云透明度 (0.0=全透明, 1.0=不透明)
  show_distance_legend: true # 显示距离颜色条图例
```

---

## 点云过滤

为避免噪点和无效点干扰，默认开启以下过滤：

- **距离过滤**：只保留 `range_min` ~ `range_max` 范围内的点。
- **FOV 过滤**：只保留位于相机前方（Z > 0）的点。

可在 `config.yaml` 的 `filter` 节点中关闭或调整。

---

## 支持的数据格式

| 类型 | 格式 | 说明 |
|---|---|---|
| 点云 | `.pcd` | 推荐使用 open3d 读取（支持 ASCII / 二进制）；无 open3d 时回退为纯 Python 解析 ASCII |
| 点云 | `.bin` | KITTI 格式，每点 4 个 float32 (x, y, z, intensity) |
| 图像 | `.jpg`, `.jpeg`, `.png` | 通过 OpenCV 读取，支持所有常见图像格式 |

---

## 与 SuoXing-Tuan 重建管线的联动

本模块可以**独立运行**（从文件读取数据），也可以作为**库**集成到 `backend/reconstruction/` 管线中。

### 架构位置

```
硬件层                      数据处理层                      AI推理层
══════                      ══════════                      ═══════
激光雷达 ─┐                                                 YOLO检测
          ├─ SensorFrame ─┬─ DataFusion() ─▶ 世界系点云       │
相机 ────┘                │                         2D bbox │
                          │                                  │
                          └─ project_sensor_frame() ◀────────┘
                              │   ▲
                              │   │ V3: bbox→3D 映射
                              ▼   │
                           投影结果       backproject_bbox_to_3d()
                           (uv, depth)   (3D 标注位置)
```

### 两种使用模式

**模式 1：独立模式**（从文件运行）
```bash
python main.py --demo
```

**模式 2：集成模式**（在 reconstruction 管线中调用）
```python
from lidar_camera_fusion import (
    CameraIntrinsics,           # 内参结构（补 schemas.CameraView 之缺）
    compute_lidar_to_camera_extrinsic,  # 从 Pose6DoF 推算外参
    project_sensor_frame,       # SensorFrame → 投影
    project_fused_frame_to_camera,      # FusedFrame → 投影
    uv_to_depth_map,            # 稀疏投影 → 稠密深度图
    backproject_pixel_to_3d,    # 像素+深度 → 世界3D点 (V3核心)
    backproject_bbox_to_3d,     # 2D检测框 → 3D包围盒 (V3核心)
)

# 1. 定义相机内参（当前 schemas.py 中缺失的部分）
intrinsics = CameraIntrinsics(
    K=[[1200, 0, 960], [0, 1200, 540], [0, 0, 1]],
    image_width=1920, image_height=1080,
    dist_coeff=[-0.35, 0.12, 0, 0, -0.02],
)

# 2. 对每个 SensorFrame 执行投影
lidar_pose = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]  # LiDAR在车体原点
results = project_sensor_frame(sensor_frame, intrinsics, lidar_pose)

# 3. 获取相机0的投影结果
cam0 = results[0]  # {"uv": (M,2), "depths": (M,), "proj_mask": (N,), "points_cam": (M,3)}

# 4. V3: 将 YOLO 检测框映射到 3D 空间
depth_map = uv_to_depth_map(cam0["uv"], cam0["depths"], 1920, 1080)
bbox_3d = backproject_bbox_to_3d(
    [x1, y1, x2, y2], depth_map, intrinsics.K,
    R_cam_to_world, T_cam_to_world,
)
# → [center_x, center_y, center_z, width, height, depth_meters]
```

### 接口对照表

| 本模块函数 | reconstruction 管线中的位置 | 用途 |
|-----------|---------------------------|------|
| `quat_to_rotation()` | = `transform.py:quat_to_rotation` | 四元数→矩阵 |
| `pose_to_matrix()` | = `transform.py:pose_to_matrix` | 位姿→4×4 |
| `transform_points()` | = `transform.py:transform_points` | 齐次变换 |
| `compute_lidar_to_camera_extrinsic()` | ✨ 新增，管线中缺失 | 推算 LiDAR→相机外参 |
| `project_sensor_frame()` | ✨ 新增，管线中缺失 | SensorFrame→投影结果 |
| `backproject_pixel_to_3d()` | ✨ 新增，V3 刚需 | 2D→3D 映射 |

---

## 示例输出

运行成功后将看到类似如下输出：

```
============================================================
  LiDAR-Camera Fusion — 激光雷达与相机数据融合
============================================================
配置文件: config.yaml

[1/4] 读取点云: ./data/pointcloud.pcd
      读取到 124800 个点
[2/4] 读取图像: ./data/image.jpg
      图像尺寸: 1920 x 1080
[3/4] 过滤无效点...
      过滤后剩余 98700 个点
[4/4] 投影点云到图像平面...
      有效投影点: 45632

融合结果已保存至: ./output/fusion_result.jpg

完成。
```

---

## 运行测试

项目包含一个完整的单元测试脚本，使用**合成数据**验证投影管线的正确性，无需真实传感器即可运行。

```bash
# 安装依赖（含测试所需）
pip install -r requirements.txt

# 运行全部 12 项测试
python test_lidar_camera_fusion.py
```

### 测试覆盖范围

| 测试项 | 验证内容 |
|--------|----------|
| 内参矩阵构建 | K 矩阵 shape、值正确性、异常输入检测 |
| 欧拉角→旋转矩阵 | 单位阵、90°旋转、正交性 (R·Rᵀ=I)、行列式=1 |
| 外参构建 | 矩阵模式 / 欧拉角模式切换 |
| 无畸变投影 | 已知 3D 点 → 预期像素坐标（精度 <1px） |
| 相机后方过滤 | Z≤0 点被剔除 |
| 边界裁剪 | 投影点不超出图像范围 |
| 畸变校正方向 | 正/负畸变对点位置的影响方向 |
| 边界情况 | 空点云、全后方点 |
| 点云过滤 | 距离过滤 + FOV 过滤 |
| 颜色映射 | 输出格式/值域 |
| 融合渲染 | 输出尺寸、纯色模式 |
| **完整流水线** | 从临时配置文件到输出结果的全链路 |

> 所有测试纯 CPU 运行，无需 GPU。

---

## 常见问题

**Q: 投影点全部偏了 / 不在正确位置？**
A: 检查外参 R 和 T 的数值是否正确，注意坐标系方向约定。确保点云和图像的采集时刻是同步的。

**Q: 提示 `No module named 'open3d'`？**
A: open3d 是可选的。若无则程序会自动回退，但对二进制 .pcd 文件可能无法解析。建议执行 `pip install open3d`。

**Q: 图片上只有很少的点？**
A: 检查点云过滤参数，尝试放宽 `range_max` 或关闭 FOV 过滤排查。也可能是外参偏差较大，导致点投影到图像范围之外。
