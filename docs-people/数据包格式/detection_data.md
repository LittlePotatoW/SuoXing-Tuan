# 数据包结构文档（SensorFrame）

硬件组每次采集一帧，打包成一个 `SensorFrame` JSON 发给后端。

## 使用方式

```
POST /api/reconstruction/frame
Content-Type: application/json

{ ... SensorFrame JSON ... }
```

## 完整结构示例

```json
{
  "frame_id": "api_test_001",
  "timestamp_ns": 1718208000000000000,

  "point_cloud": {
    "points": [
      1.0, 0.0, 0.5, 1.1, 0.0, 0.5, 1.0, 0.1, 0.5, 0.9, 0.1, 0.5,
      1.0, 0.0, 0.6, 1.1, 0.0, 0.6, 1.0, 0.1, 0.6, 0.9, 0.1, 0.6
    ],
    "point_count": 8
  },

  "camera_views": [
    {
      "image_data": "/9j/4AAQSkZJRgABAQAAAQABAAD...（base64 编码的 JPEG 图片，见下方说明）",
      "width": 1920,
      "height": 1080,
      "camera_pose": {
        "position": { "x": 0.0, "y": 0.0, "z": 0.3 },
        "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
      }
    },
    {
      "image_data": "/9j/4AAQSkZJRgABAQAAAQABAAD...（第二张图的 base64）",
      "width": 1920,
      "height": 1080,
      "camera_pose": {
        "position": { "x": 0.0, "y": 1.0, "z": 0.3 },
        "rotation": { "qw": 0.707, "qx": 0.0, "qy": 0.0, "qz": 0.707 }
      }
    }
  ],

  "car_position": {
    "pose": {
      "position": { "x": 0.0, "y": 0.0, "z": 0.0 },
      "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
    },
    "timestamp_ns": 1718208000000000000
  },

  "kinematics": {
    "velocity": 0.5,
    "steering_angle": 0.0,
    "wheel_base": 1.5,
    "timestamp_ns": 1718208000000000000
  }
}
```

## 字段说明

### 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `frame_id` | string | 是 | 帧唯一标识，如 `"frame_000001"` |
| `timestamp_ns` | int | 是 | 采集时刻（纳秒 Unix 时间戳） |
| `point_cloud` | object | 是 | 激光雷达点云数据 |
| `camera_views` | array | 否 | 相机图像列表，可包含 1~N 个相机 |
| `car_position` | object | 是 | 小车在世界坐标系中的位姿 |
| `kinematics` | object | 否 | 小车运动学参数 |

### point_cloud

| 字段 | 类型 | 说明 |
|------|------|------|
| `points` | list[float] | 扁平数组 `[x0,y0,z0, x1,y1,z1, ...]`，传感器自身坐标系 |
| `point_count` | int | 点数 = `len(points) / 3` |

### camera_views[] — 每个相机的数据

| 字段 | 类型 | 说明 |
|------|------|------|
| `image_data` | string | **JPEG 图片的 Base64 编码字符串**（见下方"图片编码"） |
| `width` | int | 图片宽度（像素） |
| `height` | int | 图片高度（像素） |
| `camera_pose` | object | 相机在**车体坐标系**中的安装位姿（外参） |

#### camera_pose — 相机外参

固定值（标定后不变）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `position.x/y/z` | float | 相机在车体坐标系中的安装位置（米） |
| `rotation.qw/qx/qy/qz` | float | 四元数旋转，`[qw, qx, qy, qz]`，qw 为实部 |

### car_position — 小车世界位姿

每帧变化：

| 字段 | 类型 | 说明 |
|------|------|------|
| `pose.position.x/y/z` | float | 小车在世界坐标系中的位置（米） |
| `pose.rotation.qw/qx/qy/qz` | float | 小车的世界朝向（四元数） |
| `timestamp_ns` | int | 位姿采集时间戳 |

### kinematics — 运动学参数

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| `velocity` | float | m/s | 当前线速度 |
| `steering_angle` | float | rad | 当前转向角 |
| `wheel_base` | float | m | 轴距，一般为固定值 1.5 |
| `timestamp_ns` | int | — | 采集时间戳 |

## 图片编码

`image_data` 字段存储的是 JPEG 文件的 **Base64 编码字符串**，直接嵌入 JSON。

### Python 编码示例

```python
import base64

with open("camera_01.jpg", "rb") as f:
    image_bytes = f.read()

b64_string = base64.b64encode(image_bytes).decode("utf-8")
# 把 b64_string 填入 JSON 的 "image_data" 字段
```

### Python 解码示例

```python
import base64

b64_string = data["camera_views"][0]["image_data"]
image_bytes = base64.b64decode(b64_string)
# image_bytes 可直接写入文件或传给 cv2.imdecode
```

### 大小估算

| 分辨率 | JPEG 质量 | 文件大小 | Base64 后 |
|--------|-----------|----------|-----------|
| 1920×1080 | 85% | ~150 KB | ~200 KB |
| 640×480 | 85% | ~40 KB | ~55 KB |

建议根据网络带宽调整 JPEG 质量，单帧数据包控制在 **2 MB 以内**。

## 坐标系约定

```
车体坐标系 (body frame):
  +x → 小车正前方
  +y → 小车左侧
  +z → 上方

世界坐标系 (world frame):
  以场景原点为基准，通过 car_position 确定小车在世界中的位姿

传感器坐标系:
  激光雷达/相机自身的局部坐标系，通过外参变换到车体坐标系
```

## 多相机说明

`camera_views` 数组支持 1~N 个相机：

- **前端工业相机**：装在车体前方，朝向正前
- **侧方相机**：装在车体侧面
- 每个相机有独立的安装位姿（`camera_pose`），标定后确定
- 后端重建管线会用相机内参 + 外参将点云投影到每个图像上采样颜色
