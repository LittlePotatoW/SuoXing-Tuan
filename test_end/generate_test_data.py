# ============================================================
# test_end/generate_test_data.py
# 生成模拟小车匀速巡检数据: 点云 + 彩色图像 + 位姿
# 用法: cd test_end && python generate_test_data.py
# ============================================================

import json, base64, os
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).parent

CAR_SPEED = 0.5
STEERING_ANGLE = 0.0
WHEEL_BASE = 1.5
LOC_FREQ = 20
DET_FREQ = 2
DURATION = 10
CUBE_AHEAD = 3.0   # 立方体在车前方 (沿 +x, 相机朝向)
CUBE_SIZE = 0.5
CUBE_HEIGHT = 1.5
IMG_W, IMG_H = 544, 384


def make_cube_point_cloud(cx: float, cy: float, cz: float, n: int = 600) -> list[float]:
    """在 (cx, cy, cz) 生成立方体表面点云 + 地面"""
    pts = []
    h = CUBE_SIZE / 2
    for i in range(n):
        face = i % 6
        r = np.random
        if face == 0:    p = [cx+(r.random()-0.5)*CUBE_SIZE, cy-h, cz+(r.random()-0.5)*CUBE_SIZE]
        elif face == 1:  p = [cx+(r.random()-0.5)*CUBE_SIZE, cy+h, cz+(r.random()-0.5)*CUBE_SIZE]
        elif face == 2:  p = [cx-h, cy+(r.random()-0.5)*CUBE_SIZE, cz+(r.random()-0.5)*CUBE_SIZE]
        elif face == 3:  p = [cx+h, cy+(r.random()-0.5)*CUBE_SIZE, cz+(r.random()-0.5)*CUBE_SIZE]
        elif face == 4:  p = [cx+(r.random()-0.5)*CUBE_SIZE, cy+(r.random()-0.5)*CUBE_SIZE, cz-h]
        else:            p = [cx+(r.random()-0.5)*CUBE_SIZE, cy+(r.random()-0.5)*CUBE_SIZE, cz+h]
        pts.extend(p)
    for _ in range(200):
        gx = cx + np.random.uniform(-1.5, 1.5)
        gy = np.random.uniform(-1.5, 1.5)
        gz = cz - h + np.random.normal(0, 0.02)
        pts.extend([gx, gy, gz])
    return pts


def make_color_image() -> bytes:
    """彩色渐变测试图"""
    img = np.zeros((IMG_H, IMG_W, 3), dtype=np.uint8)
    for y in range(IMG_H):
        for x in range(IMG_W):
            r = int(255 * (1 - x / IMG_W) * (1 - y / IMG_H))
            g = int(255 * (x / IMG_W))
            b = int(255 * (y / IMG_H))
            img[y, x] = [r, g, b]
    buf = BytesIO()
    Image.fromarray(img).save(buf, format='JPEG', quality=85)
    return buf.getvalue()


# ── Location 序列 ──
loc_interval_ns = int(1e9 / LOC_FREQ)
location_seq = []
for i in range(DURATION * LOC_FREQ):
    t_ns = i * loc_interval_ns
    car_x = CAR_SPEED * (t_ns / 1e9)
    location_seq.append({
        "timestamp_ns": t_ns,
        "camera": [{
            "camera_pose": {
                "position": {"x": 0.0, "y": 0.0, "z": 1.0},
                "rotation": {"qw": 0.7071, "qx": 0.0, "qy": 0.7071, "qz": 0.0},
            }
        }],
        "car": {
            "kinematics": {
                "velocity": CAR_SPEED,
                "steering_angle": STEERING_ANGLE,
                "wheel_base": WHEEL_BASE,
            }
        }
    })

with open(ROOT / "location_seq.json", "w") as f:
    json.dump(location_seq, f, indent=2)
print(f"Location: {len(location_seq)} 帧 ({DURATION}s @ {LOC_FREQ}Hz)")

# ── Detection 序列 ──
jpeg_img = make_color_image()
img_b64 = base64.b64encode(jpeg_img).decode()
det_interval_ns = int(1e9 / DET_FREQ)
detection_seq = []

for i in range(DURATION * DET_FREQ):
    t_ns = i * det_interval_ns
    car_x = CAR_SPEED * (t_ns / 1e9)
    # 立方体在传感器坐标系固定位置 (LiDAR 在车体 0.5m 高处)
    pts = make_cube_point_cloud(cx=CUBE_AHEAD, cy=0.0, cz=CUBE_HEIGHT - 0.5, n=600)
    detection_seq.append({
        "frame_id": f"sim_{i:04d}",
        "timestamp_ns": t_ns,
        "point_cloud": {"points": pts, "point_count": len(pts) // 3},
        "car_position": {
            "pose": {
                "position": {"x": car_x, "y": 0.0, "z": 0.0},
                "rotation": {"qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0},
            },
            "timestamp_ns": t_ns,
        },
        "camera_views": [{
            "image_data": img_b64,
            "width": IMG_W,
            "height": IMG_H,
            "camera_pose": {
                "position": {"x": 0.0, "y": 0.0, "z": 1.0},
                "rotation": {"qw": 0.7071, "qx": 0.0, "qy": 0.7071, "qz": 0.0},
            }
        }]
    })

with open(ROOT / "detection_seq.json", "w") as f:
    json.dump(detection_seq, f, indent=2)
print(f"Detection: {len(detection_seq)} 帧 ({DURATION}s @ {DET_FREQ}Hz)")
print(f"图片: {IMG_W}x{IMG_H}, base64 {len(img_b64)} 字符")
print(f"立方体: 车前方 {CUBE_AHEAD}m, 高度 {CUBE_HEIGHT}m, 尺寸 {CUBE_SIZE}m")
print(f"Done!")
