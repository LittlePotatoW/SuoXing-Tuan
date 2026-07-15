# 定位数据包结构文档（Location/Pose Data）

定位模块每次上报一帧位姿数据，打包成 JSON 发给后端。

## 完整结构示例

```json
{
  "timestamp_ns": 1718208000000000000,

  "camera": [
    {
      "camera_pose": {
        "position": { "x": 0.0, "y": 0.0, "z": 0.3 },
        "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
      }
    },
    {
      "camera_pose": {
        "position": { "x": 0.0, "y": 1.0, "z": 0.3 },
        "rotation": { "qw": 0.707, "qx": 0.0, "qy": 0.0, "qz": 0.707 }
      }
    }
  ],

  "car": {
    "pose": {
      "position": { "x": 0.0, "y": 0.0, "z": 0.0 },
      "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
    },
    "kinematics": {
      "velocity": 0.5,
      "steering_angle": 0.0,
      "wheel_base": 1.5
    }
  }
}
```

## 字段说明

### 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timestamp_ns` | int | 是 | 采集时刻（纳秒 Unix 时间戳） |
| `camera` | array | 是 | 多个相机的外参列表 |
| `car` | object | 是 | 小车的位姿和运动学参数 |

### camera[] — 相机外参列表

数组中每个元素代表一个相机在车体上的固定安装位姿（标定后不变）。支持 1~N 个相机。

| 字段 | 类型 | 说明 |
|------|------|------|
| `camera_pose` | object | 该相机在**车体坐标系**中的安装位姿 |

#### camera_pose — 位姿

| 字段 | 类型 | 说明 |
|------|------|------|
| `position.x` | float | 安装位置 X（米），车体前方为正 |
| `position.y` | float | 安装位置 Y（米），车体左侧为正 |
| `position.z` | float | 安装位置 Z（米），上方为正 |
| `rotation.qw` | float | 四元数实部，默认 `1.0`（无旋转） |
| `rotation.qx` | float | 四元数 X 分量 |
| `rotation.qy` | float | 四元数 Y 分量 |
| `rotation.qz` | float | 四元数 Z 分量 |

**典型配置示例**（2 个工业相机）：

| 相机 | position | rotation | 说明 |
|------|----------|----------|------|
| 前视 | `[0.0, 0.0, 0.3]` | `[1, 0, 0, 0]` | 车顶中央，朝正前 |
| 侧视 | `[0.0, 1.0, 0.3]` | `[0.707, 0, 0, 0.707]` | 车体左侧，朝左（绕 Z 轴 90°） |

### car — 小车位姿与运动学

#### car.pose — 小车世界位姿（每帧变化）

| 字段 | 类型 | 说明 |
|------|------|------|
| `position.x` | float | 小车在世界坐标系 X 位置（米） |
| `position.y` | float | 小车在世界坐标系 Y 位置（米） |
| `position.z` | float | 小车在世界坐标系 Z 位置（米） |
| `rotation.qw/qx/qy/qz` | float | 小车世界朝向（四元数） |

#### car.kinematics — 运动学参数（每帧变化）

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| `velocity` | float | m/s | 当前线速度 |
| `steering_angle` | float | rad | 当前转向角 |
| `wheel_base` | float | m | 轴距，一般为固定值 1.5 |

## 与 detection_data 的关系

```
定位数据 (lacation_data)              检测数据 (detection_data)
┌──────────────────────┐              ┌──────────────────────┐
│ car.pose             │              │ point_cloud          │
│ car.kinematics       │              │ camera_views[]       │
│ camera[].camera_pose │              │   ├─ image_data(b64) │
│                      │              │   ├─ width, height   │
│                      │              │   └─ camera_pose     │
│                      │              │ car_position         │
│                      │              │ kinematics           │
└──────────────────────┘              └──────────────────────┘
   外参（固定，标定后不变）               传感器数据（每帧上传）
```

- **lacation_data**：侧重定位信息，`camera[]` 存的是相机外参（标定值，通常不变）
- **detection_data**：侧重传感器数据，`camera_views[]` 带图片，同时嵌有相机外参和车体位姿
- 两者可以独立上报，后端根据 `timestamp_ns` 做时间对齐

## 坐标系约定

```
车体坐标系 (body frame):
  +x → 正前方
  +y → 左侧
  +z → 上方

世界坐标系 (world frame):
  原点在场景基准点
  小车位姿 car.pose 描述 车体 → 世界 的变换
```
