# 批量 Detection 数据包接口文档

硬件组一次可发送 1-N 帧检测数据，后端批量接收后逐帧处理。

## 端点

```
POST /api/reconstruction/frames/batch
Content-Type: application/json
```

## 请求体

```json
{
  "count": 10,
  "frames": [
    {
      "frame_id": "f000005",
      "timestamp_ns": 1783581801179000000,

      "point_cloud": {
        "points": [2.044, -0.231, 0.682, 2.046, -0.23, 0.683],
        "point_count": 2
      },

      "camera_views": [
        {
          "image_data": "/9j/4AAQSkZJRg...（JPEG 的 Base64 编码）",
          "width": 1280,
          "height": 720,
          "camera_pose": {
            "position": { "x": 0.0, "y": 0.0, "z": 0.3 },
            "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
          }
        }
      ],

      "car_position": {
        "pose": {
          "position": { "x": 0.0, "y": 0.0, "z": 0.0 },
          "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
        },
        "timestamp_ns": 1783581801179000000
      },

      "kinematics": {
        "velocity": 0.0,
        "steering_angle": 0.0,
        "wheel_base": 1.5,
        "timestamp_ns": 1783581801179000000
      }
    }
  ]
}
```

## 字段说明

### 顶层

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `count` | int | 是 | 本批次包含的帧数 |
| `frames` | array | 是 | 帧数组，每元素为一个完整 SensorFrame |

> **注意**：帧内字段必须严格匹配，不允许出现 `send_time`、`send_time_ms` 等额外字段。

### frames[i]

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `frame_id` | string | 是 | 帧唯一标识 |
| `timestamp_ns` | int | 是 | 采集时刻（纳秒） |
| `point_cloud` | object | 是 | 激光雷达点云 |
| `camera_views` | array | 是 | 相机图像列表（1~N 个） |
| `car_position` | object | 是 | 小车世界位姿 |
| `kinematics` | object | 是 | 运动学参数 |

### point_cloud

| 字段 | 类型 | 说明 |
|------|------|------|
| `points` | list[float] | 扁平数组 `[x0,y0,z0, x1,y1,z1, ...]` |
| `point_count` | int | = len(points) / 3 |

### camera_views[i]

| 字段 | 类型 | 说明 |
|------|------|------|
| `image_data` | string | JPEG 图片的 Base64 字符串 |
| `width` | int | 图片宽度（像素） |
| `height` | int | 图片高度（像素） |
| `camera_pose` | object | 相机在车体坐标系中的安装位姿 |

### camera_pose / car_position.pose

| 字段 | 类型 | 说明 |
|------|------|------|
| `position.x` | float | X 坐标 |
| `position.y` | float | Y 坐标 |
| `position.z` | float | Z 坐标 |
| `rotation.qw` | float | 四元数实部 |
| `rotation.qx` | float | 四元数 X |
| `rotation.qy` | float | 四元数 Y |
| `rotation.qz` | float | 四元数 Z |

### kinematics

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| `velocity` | float | m/s | 线速度 |
| `steering_angle` | float | rad | 转向角 |
| `wheel_base` | float | m | 轴距 |
| `timestamp_ns` | int | — | 时间戳 |

## 与现有真实数据的差异

对比 `sensor_data(2).json`，需要硬件端修改：

| 字段 | sensor_data(2).json | 接口要求 | 操作 |
|------|---------------------|----------|:---:|
| 顶层 | ✅ `count`, `status`, `frames` | `count`, `frames`（`status` 可选） | 无需改动 |
| 帧内 | `send_time` `send_time_ms` | 不允许 | 去掉 |
