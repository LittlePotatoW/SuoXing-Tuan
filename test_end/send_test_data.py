# ============================================================
# test_end/send_test_data.py
# 向 TranspondServer 发送测试数据 — 绕过系统代理
#
# 用法: python send_test_data.py [--server 39.105.129.111:8001] [--count 20]
# ============================================================

import requests, time, base64, argparse, numpy as np
from PIL import Image
from io import BytesIO

NO_PROXY = {"http": None, "https": None}

parser = argparse.ArgumentParser()
parser.add_argument("--server", default="39.105.129.111:8001")
parser.add_argument("--count", type=int, default=20)
args = parser.parse_args()

BASE = f"http://{args.server}"
N = args.count

# 合成测试图
img = np.zeros((384, 544, 3), dtype=np.uint8)
for y in range(384):
    for x in range(544):
        img[y, x] = [int(255 * (1 - x / 544)), int(255 * (x / 544)), int(255 * (y / 384))]
buf = BytesIO()
Image.fromarray(img).save(buf, format="JPEG", quality=50)
jpeg_b64 = base64.b64encode(buf.getvalue()).decode()

print(f"Server: {BASE}, frames: {N}")

for i in range(N):
    ts = int(time.time() * 1e9) + i * 200_000_000
    r = requests.post(f"{BASE}/location", json={
        "timestamp_ns": ts,
        "camera": [{"camera_pose": {"position": {"x": 0, "y": 0, "z": 1},
                     "rotation": {"qw": 0.7071, "qx": 0, "qy": 0.7071, "qz": 0}}}],
        "car": {"kinematics": {"velocity": 0.5, "steering_angle": 0, "wheel_base": 1.5}},
    }, proxies=NO_PROXY, timeout=10)
    time.sleep(0.1)

for i in range(N):
    ts = int(time.time() * 1e9) + i * 500_000_000
    pts = []
    for _ in range(300):
        pts.extend([i * 0.1 + np.random.uniform(-0.25, 0.25),
                     np.random.uniform(-0.25, 0.25),
                     1.5 + np.random.uniform(-0.25, 0.25)])
    r = requests.post(f"{BASE}/frames", json={
        "count": 1, "frames": [{
            "frame_id": f"test_{i:04d}", "timestamp_ns": ts,
            "point_cloud": {"points": pts, "point_count": 300},
            "camera_views": [{"image_data": jpeg_b64, "width": 544, "height": 384,
                "camera_pose": {"position": {"x": 0, "y": 0, "z": 1},
                                "rotation": {"qw": 0.7071, "qx": 0, "qy": 0.7071, "qz": 0}}}],
            "car_position": {"pose": {"position": {"x": i * 0.1, "y": 0, "z": 0},
                                       "rotation": {"qw": 1, "qx": 0, "qy": 0, "qz": 0}},
                              "timestamp_ns": ts},
            "kinematics": {"velocity": 0.5, "steering_angle": 0, "wheel_base": 1.5, "timestamp_ns": ts},
        }]
    }, proxies=NO_PROXY, timeout=10)
    time.sleep(0.1)

s = requests.get(f"{BASE}/status", proxies=NO_PROXY, timeout=10).json()
print(f"Done: loc={s['location_cached']} sensor={s['sensor_cached']}")
