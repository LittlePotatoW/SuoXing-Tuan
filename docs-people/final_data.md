# 最终融合数据包结构文档（FinalData / SensorFrame）

`final_data` 是定位数据（`lacation_data`）和检测数据（`detection_data`）融合后的产物，**格式等同于后端的 `SensorFrame`**，可直接 `POST /api/reconstruction/frame`。

## 核心设计决策

1. **不使用 GPS/定位**：小车定位不准，不信任 `lacation_data` 里的 `car.pose`。小车世界位姿**纯靠运动学航迹推算**（velocity + steering_angle 积分）。
2. **允许缺字段**：小车上行数据不稳定，每个字段都可能缺失。融合模块对所有字段有 fallback 默认值。
3. **仅取外参**：`lacation_data` 只用来拿 `camera[].camera_pose`（标定值，固定不变），以及 `kinematics`（速度/转向角）。

## 数据融合流程

```
lacation_data (持续上报)              detection_data (事件触发上报)
┌──────────────────────┐              ┌──────────────────────┐
│ camera[].camera_pose │              │ frame_id             │
│ car.kinematics       │              │ timestamp_ns         │
│                      │              │ point_cloud          │
│ (car.pose 不使用!)    │              │ camera_views[]       │
└──────────┬───────────┘              │   ├─ image_data(b64) │
           │                          │   ├─ width, height   │
           │                          │   └─ camera_pose     │
           ▼                          └──────────┬───────────┘
   ┌───────────────────┐                         │
   │  航迹推算引擎       │                         │
   │                    │                         │
   │  收到 kinematics   │                         │
   │  → 积分速度+转向角  │                         │
   │  → 维护 (x,y,yaw)  │                         │
   │                    │                         │
   │  收到 camera[]     │                         │
   │  → 缓存相机外参     │                         │
   └─────────┬─────────┘                         │
             │                                   │
             │   收到 detection_data 时            │
             │   取当前推算位姿 + 缓存的外参        │
             │◄──────────────────────────────────┘
             │
             ▼
      ┌──────────────────────┐
      │     final_data       │
      │  (即 SensorFrame)    │
      └──────────────────────┘
```

- **lacation_data**：高频上报（如 100Hz），只取 `camera[].camera_pose` 和 `car.kinematics`
- **detection_data**：触发式上报，携带点云和图片
- **航迹推算引擎**：持续接收 kinematics 积分，维护小车当前位姿的估计值
- **融合输出**：收到 detection_data 时，用当前推算位姿 + 缓存外参，拼出 final_data

## 航迹推算（Dead Reckoning）

定位不可靠，小车世界位姿完全通过**自行车模型**对速度/转向角积分得到。

### 自行车模型

```
         δ (steering_angle)
         │
    ┌────┴────┐
    │  后轮   │─── L (wheel_base) ───│  前轮   │
    └─────────┘                      └─────────┘
         │                                │
         └──────── v (velocity) ──────────┘

    ω = (v / L) * tan(δ)          ← 角速度
    Δθ = ω * Δt                   ← 朝向变化
    Δx = v * cos(θ) * Δt          ← x 位移
    Δy = v * sin(θ) * Δt          ← y 位移
```

### 积分公式

每收到一帧 `lacation_data`（或有 kinematics 字段的任何数据包）：

```python
dt = (t_current - t_prev) / 1e9    # ns → s

v = kinematics.get("velocity", 0.0)
delta = kinematics.get("steering_angle", 0.0)
L = kinematics.get("wheel_base", 1.5)

omega = (v / L) * math.tan(delta)   # 角速度
theta += omega * dt                 # 积分朝向
x += v * math.cos(theta) * dt       # 积分 x
y += v * math.sin(theta) * dt       # 积分 y

# 朝向 → 四元数 (仅 yaw，绕 z 轴)
qw = math.cos(theta / 2)
qz = math.sin(theta / 2)
```

### 边界处理

| 场景 | 处理 |
|------|------|
| velocity = 0 | 位置不变，朝向不变（静止） |
| steering_angle = 0 | 直线运动，ω = 0 |
| 第一帧没有历史 dt | 跳过积分，从下一帧开始 |
| dt > 2s（长时间无数据） | 标记重置，θ 保持、v 置 0 |

## 缺字段 Fallback 策略

小车可能无法传输所有字段。融合模块对每个字段设定 fallback：

### detection_data 缺字段

| 缺失字段 | Fallback | 影响 |
|----------|----------|------|
| `frame_id` | 自动生成 `"auto_{timestamp}"` | 无影响 |
| `point_cloud` | **跳过整帧**（点云是必须的） | 丢弃此 detection |
| `camera_views` | `[]` 空数组 | 该帧无图像，重建无颜色 |
| `camera_views[i].image_data` | `null` → 跳过该相机 | 该相机不参与颜色采样 |
| `camera_views[i].width/height` | `640 / 480` | 投影可能不准 |
| `camera_views[i].camera_pose` | 从 location 缓存取 | 正常 |

### lacation_data 缺字段

| 缺失字段 | Fallback | 影响 |
|----------|----------|------|
| `camera[]` 整数组 | 从 detection 的 camera_pose 取 | 外参可能不准 |
| `camera[i].camera_pose` | 上一个已知值 | 外参不变 |
| `car.kinematics.velocity` | `0.0` | 航迹推算暂停 |
| `car.kinematics.steering_angle` | `0.0` | 直线运动 |
| `car.kinematics.wheel_base` | `1.5` | 用默认轴距 |

### 分级降级

```
Level 1 (完整): 所有字段齐全 → 最优重建
Level 2 (无图): camera_views 为空 → 无颜色重建（纯几何）
Level 3 (无定位): 缺 kinematics → 位姿不更新，停在上一位置
Level 4 (仅点云): 只有 point_cloud → 以 (0,0,0) 无旋转位姿处理
```

## 完整结构示例

```json
{
  "frame_id": "fusion_20260707_001",
  "timestamp_ns": 1718208001500000000,

  "point_cloud": {
    "points": [
      1.0, 0.0, 0.5, 1.1, 0.0, 0.5, 1.0, 0.1, 0.5, 0.9, 0.1, 0.5,
      1.0, 0.0, 0.6, 1.1, 0.0, 0.6, 1.0, 0.1, 0.6, 0.9, 0.1, 0.6
    ],
    "point_count": 8
  },

  "camera_views": [
    {
      "image_data": "/9j/4AAQSkZJRgABAQAAAQABAAD...（base64 JPEG）",
      "width": 1920,
      "height": 1080,
      "camera_pose": {
        "position": { "x": 0.0, "y": 0.0, "z": 0.3 },
        "rotation": { "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0 }
      }
    }
  ],

  "car_position": {
    "pose": {
      "position": { "x": 1.25, "y": 0.02, "z": 0.0 },
      "rotation": { "qw": 0.999, "qx": 0.0, "qy": 0.0, "qz": 0.045 }
    },
    "timestamp_ns": 1718208001500000000
  },

  "kinematics": {
    "velocity": 0.52,
    "steering_angle": 0.03,
    "wheel_base": 1.5,
    "timestamp_ns": 1718208001500000000
  }
}
```

## 字段来源对照

| final_data 字段 | 来源 | 说明 |
|-----------------|------|------|
| `frame_id` | detection | 缺失时自动生成 |
| `timestamp_ns` | detection | 直接透传 |
| `point_cloud` | detection | **唯一必须字段**，缺失则丢弃帧 |
| `camera_views[].image_data` | detection | 缺失则该相机跳过 |
| `camera_views[].width/height` | detection | 缺失默认 640×480 |
| `camera_views[].camera_pose` | **location**（优先）→ detection fallback | 外参，标定后不变 |
| `car_position.pose` | **航迹推算** | 纯运动学积分，不用 GPS |
| `kinematics` | location（当前值） | 直接透传最新已知值 |

## 字段说明

### 顶层

| 字段 | 类型 | 必填 | 来源 | 说明 |
|------|------|------|------|------|
| `frame_id` | string | 否 | detection | 帧标识，缺则自动生成 |
| `timestamp_ns` | int | 是 | detection | 采集时刻 |
| `point_cloud` | object | **是** | detection | 激光雷达点云，缺则丢弃帧 |
| `camera_views` | array | 否 | detection + location | 0~N 个相机 |
| `car_position` | object | 是 | **航迹推算** | 积分得到的世界位姿 |
| `kinematics` | object | 否 | location | 最新运动学参数 |

### point_cloud

| 字段 | 类型 | 说明 |
|------|------|------|
| `points` | list[float] | 扁平 `[x0,y0,z0, ...]`，传感器坐标系 |
| `point_count` | int | = len(points) / 3 |

### camera_views[]

| 字段 | 类型 | 来源 | Fallback |
|------|------|------|----------|
| `image_data` | string | detection | `null`（跳过该相机） |
| `width` | int | detection | `640` |
| `height` | int | detection | `480` |
| `camera_pose` | object | location → detection | 上个已知值 |

### car_position（航迹推算输出）

| 字段 | 类型 | 说明 |
|------|------|------|
| `pose.position.x/y/z` | float | 积分得到的世界位置（z 恒为 0，平面运动） |
| `pose.rotation.qw/qx/qy/qz` | float | 积分得到的朝向（仅 yaw，qw/qz 非零） |
| `timestamp_ns` | int | detection 的时间戳 |

### kinematics

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| `velocity` | float | m/s | 当前线速度 |
| `steering_angle` | float | rad | 当前转向角 |
| `wheel_base` | float | m | 轴距，默认 1.5 |
| `timestamp_ns` | int | — | 取值时刻 |
