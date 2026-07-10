#!/usr/bin/env python3
# ============================================================
# OTHER_END/Transpond_Server/测试.py
# TranspondServer 全 API 测试脚本 — 模拟小车数据 + 遍历所有接口
#
# 用法:
#   python 测试.py                        # 完整一轮测试
#   python 测试.py --stream               # 持续发送模式
#   python 测试.py --server 192.168.1.100:8001
# ============================================================

import sys
import json
import time
import math
import base64
import argparse
import traceback
from io import BytesIO
from datetime import datetime

import requests
import numpy as np
from PIL import Image

# ── 配置 ──
BASE_URL = "http://127.0.0.1:8001"
WS_URL_TEMPLATE = "ws://127.0.0.1:8001/stream"
REQUEST_TIMEOUT = 5

# ── ANSI 颜色 ──
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

# ── 全局统计 ──
PASS = FAIL = 0


def now_str():
    return datetime.now().strftime("%H:%M:%S")


def log_ok(msg):
    global PASS
    PASS += 1
    print(f"  {GREEN}[OK]{RESET}   {msg}")


def log_fail(msg):
    global FAIL
    FAIL += 1
    print(f"  {RED}[FAIL]{RESET} {msg}")


def log_info(msg):
    print(f"  {CYAN}[INFO]{RESET} {msg}")


def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# ============================================================
#  模拟数据生成
# ============================================================

def make_synthetic_jpeg(w=544, h=384) -> bytes:
    """生成 RGB 渐变测试图，返回 JPEG 字节"""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            img[y, x] = [
                int(255 * (1 - x / w)),
                int(255 * (x / w)),
                int(255 * (y / h)),
            ]
    buf = BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def make_cube_points(cx, cy, cz, size=0.5, n=300):
    """在 (cx, cy, cz) 生成立方体表面点云 + 随机地面噪点"""
    pts = []
    half = size / 2
    for i in range(n):
        face = i % 6
        r = np.random
        if face == 0:
            p = [cx + r.uniform(-half, half), cy - half, cz + r.uniform(-half, half)]
        elif face == 1:
            p = [cx + r.uniform(-half, half), cy + half, cz + r.uniform(-half, half)]
        elif face == 2:
            p = [cx - half, cy + r.uniform(-half, half), cz + r.uniform(-half, half)]
        elif face == 3:
            p = [cx + half, cy + r.uniform(-half, half), cz + r.uniform(-half, half)]
        elif face == 4:
            p = [cx + r.uniform(-half, half), cy + r.uniform(-half, half), cz - half]
        else:
            p = [cx + r.uniform(-half, half), cy + r.uniform(-half, half), cz + half]
        pts.extend(p)
    # 地面点
    for _ in range(50):
        pts.extend([
            cx + np.random.uniform(-1.5, 1.5),
            np.random.uniform(-1.5, 1.5),
            cz - half + np.random.normal(0, 0.02),
        ])
    return pts


class Car:
    """小车物理模型 — 匀速直线 + Ackermann 转向"""

    def __init__(self, velocity=0.5, wheel_base=1.5):
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.velocity = velocity
        self.steering = 0.0
        self.wheel_base = wheel_base

    def step(self, dt: float):
        if abs(self.steering) < 1e-6:
            self.x += self.velocity * math.cos(self.yaw) * dt
            self.y += self.velocity * math.sin(self.yaw) * dt
        else:
            turn_radius = self.wheel_base / math.tan(self.steering)
            omega = self.velocity / turn_radius
            self.yaw += omega * dt
            self.x += turn_radius * (math.sin(self.yaw) - math.sin(self.yaw - omega * dt))
            self.y += turn_radius * (math.cos(self.yaw - omega * dt) - math.cos(self.yaw))

    def pose(self):
        half = self.yaw / 2.0
        return {
            "position": {"x": round(self.x, 4), "y": round(self.y, 4), "z": 0.0},
            "rotation": {"qw": math.cos(half), "qx": 0.0, "qy": 0.0, "qz": math.sin(half)},
        }


def make_location_data(ts_ns: int, car: Car):
    return {
        "timestamp_ns": ts_ns,
        "camera": [{
            "camera_pose": {
                "position": {"x": 0.0, "y": 0.0, "z": 1.0},
                "rotation": {"qw": 0.7071, "qx": 0.0, "qy": 0.7071, "qz": 0.0},
            }
        }],
        "car": {
            "kinematics": {
                "velocity": car.velocity,
                "steering_angle": car.steering,
                "wheel_base": car.wheel_base,
            }
        },
    }


def make_detection_data(frame_id: str, ts_ns: int, car: Car, img_b64: str):
    pose = car.pose()
    pts = make_cube_points(cx=car.x + 3.0, cy=0.0, cz=1.0, size=0.5, n=300)
    return {
        "frame_id": frame_id,
        "timestamp_ns": ts_ns,
        "point_cloud": {"points": pts, "point_count": len(pts) // 3},
        "camera_views": [{
            "image_data": img_b64,
            "width": 544,
            "height": 384,
            "camera_pose": {
                "position": {"x": 0.0, "y": 0.0, "z": 1.0},
                "rotation": {"qw": 0.7071, "qx": 0.0, "qy": 0.7071, "qz": 0.0},
            },
        }],
        "car_position": {
            "pose": pose,
            "timestamp_ns": ts_ns,
        },
        "kinematics": {
            "velocity": car.velocity,
            "steering_angle": car.steering,
            "wheel_base": car.wheel_base,
            "timestamp_ns": ts_ns,
        },
    }


# ============================================================
#  API 测试函数
# ============================================================

def api(url, method="get", json_data=None, timeout=REQUEST_TIMEOUT):
    """统一 HTTP 请求，返回 (status, json|None, error_str|None)"""
    try:
        if method == "get":
            resp = requests.get(url, timeout=timeout)
        else:
            resp = requests.post(url, json=json_data, timeout=timeout)
        try:
            body = resp.json()
        except Exception:
            body = None
        return resp.status_code, body, None
    except Exception as e:
        return None, None, str(e)


def test_clear():
    print(f"\n[{now_str()}] POST /debug  clear")
    code, body, err = api(f"{BASE_URL}/debug", "post", {"action": "clear"})
    if code == 200 and body and body.get("status") == "ok":
        log_ok("缓存已清空")
        return True
    log_fail(f"清空失败  code={code} body={body} err={err}")
    return False


def test_debug_status():
    print(f"\n[{now_str()}] POST /debug  status")
    code, body, err = api(f"{BASE_URL}/debug", "post", {"action": "status"})
    if code == 200 and body and "location_cached" in body and "sensor_cached" in body:
        log_ok(f"location_cached={body['location_cached']}  sensor_cached={body['sensor_cached']}")
        return True
    log_fail(f"code={code} body={body} err={err}")
    return False


def test_get_status():
    print(f"\n[{now_str()}] GET  /status")
    code, body, err = api(f"{BASE_URL}/status", "get")
    if code == 200 and body and "location_cached" in body and "sensor_cached" in body:
        log_ok(f"location_cached={body['location_cached']}  sensor_cached={body['sensor_cached']}")
        return True
    log_fail(f"code={code} body={body} err={err}")
    return False


def test_post_location(data: dict):
    ts = data["timestamp_ns"]
    print(f"\n[{now_str()}] POST /location  ts={ts}")
    code, body, err = api(f"{BASE_URL}/location", "post", data)
    if code == 200 and body and body.get("status") == "ok":
        log_ok(f"cached={body.get('cached')}")
        return True
    log_fail(f"code={code} body={body} err={err}")
    return False


def test_post_frames(data: dict):
    count = data.get("count", 0)
    print(f"\n[{now_str()}] POST /frames  count={count}")
    code, body, err = api(f"{BASE_URL}/frames", "post", data)
    if code == 200 and body and body.get("status") == "ok":
        log_ok(f"received={body.get('received')}  cached={body.get('cached')}")
        return True
    log_fail(f"code={code} body={body} err={err}")
    return False


def test_get_location(after=None, limit=None):
    params = []
    if after is not None:
        params.append(f"after={after}")
    if limit is not None:
        params.append(f"limit={limit}")
    qs = ("?" + "&".join(params)) if params else ""
    print(f"\n[{now_str()}] GET  /location{qs}")
    code, body, err = api(f"{BASE_URL}/location{qs}", "get")
    if code == 200 and body and body.get("status") == "ok":
        c = body.get("count", 0)
        log_ok(f"返回 {c} 条")
        if c > 0 and body.get("frames"):
            frame0 = body["frames"][0]
            log_info(f"首帧 ts={frame0.get('timestamp_ns')}")
        return True
    log_fail(f"code={code} body={body} err={err}")
    return False


def test_get_sensor(after=None, limit=None):
    params = []
    if after is not None:
        params.append(f"after={after}")
    if limit is not None:
        params.append(f"limit={limit}")
    qs = ("?" + "&".join(params)) if params else ""
    print(f"\n[{now_str()}] GET  /sensor{qs}")
    code, body, err = api(f"{BASE_URL}/sensor{qs}", "get")
    if code == 200 and body and body.get("status") == "ok":
        c = body.get("count", 0)
        log_ok(f"返回 {c} 条")
        if c > 0 and body.get("frames"):
            frame0 = body["frames"][0]
            log_info(f"首帧 id={frame0.get('frame_id')} ts={frame0.get('timestamp_ns')}")
        return True
    log_fail(f"code={code} body={body} err={err}")
    return False


def test_websocket(mode="all", timeout_s=5):
    try:
        import websocket
    except ImportError:
        log_fail("跳过 WebSocket: 未安装 websocket-client")
        return False

    ws_url = f"{WS_URL_TEMPLATE}?mode={mode}"
    print(f"\n[{now_str()}] WS   {ws_url}")
    try:
        ws = websocket.create_connection(ws_url, timeout=timeout_s)
        log_ok("WebSocket 连接成功")
        ws.settimeout(timeout_s)
        received = 0
        for _ in range(3):
            try:
                msg = ws.recv()
                data = json.loads(msg)
                log_info(f"收到 {data.get('type')} count={data.get('count')}")
                received += 1
            except websocket.WebSocketTimeoutException:
                if received == 0:
                    log_info("暂无推送数据（服务端缓存可能为空）")
                break
        ws.close()
        log_ok(f"WebSocket 关闭 (收到 {received} 条消息)")
        return True
    except Exception as e:
        log_fail(f"WebSocket 错误: {e}")
        return False


# ============================================================
#  批量发送
# ============================================================

def send_batch_locations(n: int, car: Car, dt: float):
    """发送 n 条连续 trajectory 的 location 数据"""
    ok_count = 0
    ts_base = int(time.time() * 1e9)
    for i in range(n):
        ts = ts_base + int(i * dt * 1e9)
        car.step(dt)
        data = make_location_data(ts, car)
        code, body, err = api(f"{BASE_URL}/location", "post", data)
        if code == 200 and body and body.get("status") == "ok":
            ok_count += 1
        else:
            log_fail(f"location #{i} code={code} err={err}")
    print(f"\n[{now_str()}] 批量 location: {ok_count}/{n} 成功  (cached={body.get('cached','?') if body else '?'})")
    return ok_count == n


def send_batch_frames(n: int, car: Car, dt: float, img_b64: str):
    """发送 n 帧 sensor 数据"""
    ok_count = 0
    ts_base = int(time.time() * 1e9)
    frames = []
    for i in range(n):
        ts = ts_base + int(i * dt * 1e9)
        car.step(dt)
        frames.append(make_detection_data(f"test_{i:04d}", ts, car, img_b64))
    data = {"count": len(frames), "frames": frames}
    code, body, err = api(f"{BASE_URL}/frames", "post", data)
    if code == 200 and body and body.get("status") == "ok":
        ok_count = len(frames)
    else:
        log_fail(f"batch frames code={code} err={err}")
    print(f"\n[{now_str()}] 批量 frames: {ok_count}/{n} 成功  (received={body.get('received','?') if body else '?'})")
    return ok_count == n


# ============================================================
#  持续发送模式 (--stream)
# ============================================================

def stream_mode():
    print(f"{CYAN}持续发送模式 — Ctrl+C 停止{RESET}")
    car = Car(velocity=0.5)
    img_b64 = base64.b64encode(make_synthetic_jpeg()).decode()
    loc_ns = int(time.time() * 1e9)
    det_ns = loc_ns
    frame_idx = 0
    loc_count = 0
    det_count = 0
    last_status = 0

    try:
        while True:
            # 每 200ms 发 location
            loc_ns += 200_000_000
            car.step(0.2)
            loc_data = make_location_data(loc_ns, car)
            code, body, err = api(f"{BASE_URL}/location", "post", loc_data)
            if code == 200:
                loc_count += 1

            # 每 1s 发 sensor
            frame_idx += 1
            if frame_idx % 5 == 0:
                det_ns += 1_000_000_000
                det_data = make_detection_data(f"sim_{det_count:05d}", det_ns, car, img_b64)
                code, body, err = api(f"{BASE_URL}/frames", "post",
                    {"count": 1, "frames": [det_data]})
                if code == 200:
                    det_count += 1

            # 每 5s 打印状态
            if time.time() - last_status > 5:
                last_status = time.time()
                _, status, _ = api(f"{BASE_URL}/status", "get")
                lc = status.get("location_cached", "?") if status else "?"
                sc = status.get("sensor_cached", "?") if status else "?"
                print(f"  [{now_str()}] loc_sent={loc_count} det_sent={det_count}  server: loc={lc} sens={sc}")

            time.sleep(0.01)  # ~100Hz loop, sleep minimal
    except KeyboardInterrupt:
        print(f"\n{YELLOW}已停止。共发送: location={loc_count} sensor={det_count}{RESET}")


# ============================================================
#  主流程
# ============================================================

def main():
    global BASE_URL, WS_URL_TEMPLATE

    parser = argparse.ArgumentParser(description="TranspondServer API 测试")
    parser.add_argument("--stream", action="store_true", help="持续发送模式")
    parser.add_argument("--server", type=str, default="127.0.0.1:8001", help="服务器地址 (默认 127.0.0.1:8001)")
    args = parser.parse_args()

    BASE_URL = f"http://{args.server}"
    WS_URL_TEMPLATE = f"ws://{args.server}/stream"

    print(f" TranspondServer API 测试")
    print(f" 服务器: {BASE_URL}")
    print(f" 时间:   {now_str()}")

    if args.stream:
        stream_mode()
        return

    # ── 完整一轮测试 ──
    section("1. 初始化 — 清空 + 状态")
    test_clear()
    test_get_status()

    # ── 预生成图像（只生成一次，复用 base64） ──
    log_info("生成测试图片...")
    jpeg_bytes = make_synthetic_jpeg(544, 384)
    img_b64 = base64.b64encode(jpeg_bytes).decode()
    log_ok(f"图片 {len(jpeg_bytes)//1024} KB  base64 {len(img_b64)} 字符")

    # ── 发送 location ──
    section("2. POST /location — 发送 10 条连续轨迹")
    car = Car(velocity=0.5)
    ok = send_batch_locations(10, car, dt=0.05)
    if ok:
        log_ok("location 批量发送全部成功")

    # ── 发送 sensor ──
    section("3. POST /frames — 发送 5 帧传感器数据")
    car2 = Car(velocity=0.5)
    ok = send_batch_frames(5, car2, dt=0.5, img_b64=img_b64)
    if ok:
        log_ok("sensor 批量发送全部成功")

    # ── 查询 ──
    section("4. GET /location — 查询验证")
    test_get_location(limit=5)
    test_get_location(after=0)
    test_get_location(limit=2)

    section("5. GET /sensor — 查询验证")
    test_get_sensor(limit=3)
    test_get_sensor(after=0)

    # ── 缓存状态 ──
    section("6. 缓存状态")
    test_get_status()
    test_debug_status()

    # ── WebSocket ──
    section("7. WebSocket /stream")
    test_websocket(mode="all", timeout_s=5)
    test_websocket(mode="location", timeout_s=3)

    # ── 清理 ──
    section("8. 清理")
    test_clear()
    test_get_status()

    # ── 摘要 ──
    total = PASS + FAIL
    print(f"\n{'='*55}")
    print(f"  测试摘要: {GREEN}{PASS} 通过{RESET}  /  {RED}{FAIL} 失败{RESET}  /  {total} 总计")
    print(f"{'='*55}\n")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
