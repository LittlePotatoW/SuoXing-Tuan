#!/usr/bin/env python3
# ============================================================
# OTHER_END/1/astra_vehicle_server.py
# Astra Pro 深度相机 — 小车端帧采集 + WebSocket推送 + 局域网HTTP发送
#
# 设计与用法:
#   python astra_vehicle_server.py
#   深度: OpenNI2 (640x480, 16-bit mm)
#   彩色: OpenCV DirectShow UVC (640x480, BGR)
#   WS:   ws://0.0.0.0:8002
#   HTTP: POST http://{server}/api/vehicle/frame  (自动发现或手动指定)
# ============================================================

import asyncio
import json
import base64
import os
import time
import threading
import queue
import logging
import socket
import sys

import numpy as np
import cv2
import requests
from openni import openni2

# ============================================================
# 配置 (所有可调参数集中在此)
# ============================================================

# ── 路径 ──────────────────────────────────────────────────
OPENNI2_DLL_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "OpenNI2")

# ── 网络: WebSocket ───────────────────────────────────────
HOST = "0.0.0.0"                    # WS 绑定地址
WS_PORT = 8002                      # WS 端口
WS_MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # WS 最大消息 (10MB)

# ── 网络: 服务发现 & HTTP ─────────────────────────────────
DISCOVERY_PORT = 9001               # UDP 设备发现端口
DISCOVERY_TIMEOUT = 3.0             # UDP 发现等待超时 (秒)
DISCOVERY_BUFFER_SIZE = 4096        # UDP 接收缓冲区 (字节)
DISCOVERY_FALLBACK_BROADCAST = "255.255.255.255"  # UDP 广播回退地址
DEFAULT_SERVER_PORT = 8080          # 重建引擎默认端口
HTTP_FRAME_ENDPOINT = "/api/vehicle/frame"  # HTTP POST 路径

# ── 网络: 超时 ────────────────────────────────────────────
HTTP_POST_TIMEOUT = 2.0             # HTTP POST 超时 (秒)
HTTP_QUEUE_GET_TIMEOUT = 0.5        # HTTP 发送队列取帧超时 (秒)
HTTP_POSTER_JOIN_TIMEOUT = 2.0      # HTTP 发送线程停止等待超时 (秒)
CAMERA_STOP_JOIN_TIMEOUT = 3.0      # 相机线程停止等待超时 (秒)

# ── 相机参数 ──────────────────────────────────────────────
DEPTH_WIDTH = 640
DEPTH_HEIGHT = 480
COLOR_WIDTH = 640
COLOR_HEIGHT = 480
FPS_TARGET = 30
JPEG_QUALITY = 80                   # JPEG 压缩质量 (0-100)
COLOR_CAM_INDEX = 0                 # 手动指定彩色摄像头索引 (None=自动探测)
CAMERA_SCAN_MAX_INDEX = 6           # 自动探测时扫描的摄像头数量
CAMERA_VALID_MIN_MEAN = 10          # 帧有效性判断: 均值最小值
CAMERA_VALID_MIN_STD = 5            # 帧有效性判断: 标准差最小值
DEPTH_MIRROR_PROPERTY_ID = 2        # OpenNI2 镜像属性 ID
DEPTH_MIRROR_ENABLED = False        # 深度镜像 (False=对齐RGB)
DEPTH_WARMUP_FRAMES = 10            # 深度流启动预热帧数
COLOR_WARMUP_FRAMES = 5             # 彩色流启动预热帧数
COLOR_READ_MAX_RETRIES = 10         # 每帧彩色读取最大重试次数
CAPTURE_ERROR_RETRY_DELAY = 0.5     # 采集异常后重试间隔 (秒)

# ── 队列 & 性能 ───────────────────────────────────────────
FRAME_QUEUE_SIZE = 5                # 内部帧队列最大长度
HTTP_FRAME_QUEUE_SIZE = 10          # HTTP 发送队列最大长度
PERF_LOG_INTERVAL = 30              # 性能统计日志间隔 (秒)
HTTP_STATS_INTERVAL = 100           # HTTP 发送统计间隔 (帧数)
FAIL_LOG_MAX_COUNT = 3              # 失败日志最大输出次数 (超过后抑制)

# ── WebSocket 心跳 & 流控 ─────────────────────────────────
WS_HEARTBEAT_INTERVAL = 30          # WS 心跳间隔 (秒)
WS_HEARTBEAT_SEND_TIMEOUT = 2.0     # 心跳发送超时 (秒)
WS_FRAME_POLL_TIMEOUT = 0.2         # 帧队列轮询超时 (秒)
WS_IDLE_SLEEP = 0.01                # 无帧时休眠时间 (秒)
WS_FRAME_SEND_TIMEOUT = 2.0         # 帧发送超时 (秒)
WS_RECV_TIMEOUT = 10.0              # 接收命令超时 (秒)
DEFAULT_EXPOSURE_VALUE = 500        # 默认曝光值
DEFAULT_GAIN_VALUE = 10             # 默认增益值

# ============================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("astra-vehicle")


# ─── LAN 设备发现 ───────────────────────────────────────

def discover_server(timeout=DISCOVERY_TIMEOUT):
    """UDP 广播发现局域网内的重建引擎服务器, 返回 (host, port) 或 None"""
    log.info("正在发现局域网内的重建引擎 (UDP 广播:%d)...", DISCOVERY_PORT)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    msg = json.dumps({"type": "astra_discover"}).encode()

    # 获取本机局域网广播地址
    targets = [DISCOVERY_FALLBACK_BROADCAST]
    try:
        # 尝试获取实际广播地址
        import netifaces
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for a in addrs[netifaces.AF_INET]:
                    if a.get('broadcast') and a['broadcast'] != DISCOVERY_FALLBACK_BROADCAST:
                        targets.append(a['broadcast'])
    except ImportError:
        pass  # netifaces 未安装, 只用 255.255.255.255

    for target in set(targets):
        try:
            sock.sendto(msg, (target, DISCOVERY_PORT))
        except Exception:
            pass

    # 等待响应
    try:
        while True:
            data, addr = sock.recvfrom(DISCOVERY_BUFFER_SIZE)
            try:
                resp = json.loads(data.decode())
                if resp.get("type") == "astra_server":
                    host = resp.get("host", addr[0])
                    port = resp.get("port", DEFAULT_SERVER_PORT)
                    log.info("发现重建引擎: %s:%d", host, port)
                    sock.close()
                    return host, port
            except json.JSONDecodeError:
                continue
    except socket.timeout:
        pass

    sock.close()
    log.warning("未发现重建引擎")
    return None


def start_discovery_responder(port):
    """启动 UDP 响应服务 (重建引擎端使用, 这里留空 — 由远端服务器自己实现)"""
    pass  # 小车端不需要 — 远端服务器监听 UDP:9001, 收到 astra_discover 后回复 astra_server


# ─── HTTP 帧发送 ────────────────────────────────────────

class FramePoster:
    """在独立线程中将帧 POST 到重建引擎"""

    def __init__(self, server_url):
        self.server_url = server_url.rstrip("/") + HTTP_FRAME_ENDPOINT
        self.queue = queue.Queue(maxsize=HTTP_FRAME_QUEUE_SIZE)
        self.running = False
        self.thread = None
        self.success_count = 0
        self.fail_count = 0

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._post_loop, daemon=True)
        self.thread.start()
        log.info("HTTP 发送线程已启动 → %s", self.server_url)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=HTTP_POSTER_JOIN_TIMEOUT)
        log.info("HTTP 发送已停止 (成功=%d 失败=%d)", self.success_count, self.fail_count)

    def send_frame(self, frame_data):
        """非阻塞入队"""
        try:
            self.queue.put_nowait(frame_data)
        except queue.Full:
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(frame_data)
            except queue.Empty:
                pass

    def _post_loop(self):
        while self.running:
            try:
                frame_data = self.queue.get(timeout=HTTP_QUEUE_GET_TIMEOUT)
            except queue.Empty:
                continue

            payload = {
                "timestamp": frame_data["timestamp"],
                "image": frame_data["image_b64"],
                "depth_map": frame_data["depth_b64"],
            }

            try:
                resp = requests.post(
                    self.server_url,
                    json=payload,
                    timeout=HTTP_POST_TIMEOUT,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    self.success_count += 1
                else:
                    self.fail_count += 1
                    if self.fail_count <= FAIL_LOG_MAX_COUNT:
                        log.warning("HTTP POST 失败: %d %s", resp.status_code, resp.text[:100])
            except requests.exceptions.Timeout:
                self.fail_count += 1
            except requests.exceptions.ConnectionError:
                self.fail_count += 1
                if self.fail_count == 1:
                    log.error("无法连接到 %s", self.server_url)
            except Exception as e:
                self.fail_count += 1
                if self.fail_count <= FAIL_LOG_MAX_COUNT:
                    log.error("HTTP POST 异常: %s", e)

            # 定期报告
            total = self.success_count + self.fail_count
            if total > 0 and total % HTTP_STATS_INTERVAL == 0:
                log.info("HTTP 发送统计: 成功=%d 失败=%d", self.success_count, self.fail_count)


# ─── 摄像头采集 ──────────────────────────────────────────

def list_cameras():
    cams = []
    for i in range(CAMERA_SCAN_MAX_INDEX):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, COLOR_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, COLOR_HEIGHT)
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                cams.append((i, w, h))
                log.info("摄像头 %d: %dx%d 可用", i, w, h)
            cap.release()
        else:
            cap.release()
    return cams


def find_astra_camera_index(cams):
    if not cams:
        raise RuntimeError("未找到可用摄像头!")
    if COLOR_CAM_INDEX is not None:
        log.info("使用手动指定的摄像头 %d", COLOR_CAM_INDEX)
        return COLOR_CAM_INDEX
    valid = []
    for idx, w, h in cams:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, COLOR_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, COLOR_HEIGHT)
            ret, frame = cap.read()
            if ret and frame is not None:
                m, s = frame.mean(), frame.std()
                if m > CAMERA_VALID_MIN_MEAN and s > CAMERA_VALID_MIN_STD:
                    valid.append((idx, w, h))
                    log.info("摄像头 %d: %dx%d 有效 (mean=%.0f std=%.0f)", idx, w, h, m, s)
                else:
                    log.info("摄像头 %d: %dx%d 无效 (mean=%.0f std=%.0f) — 跳过", idx, w, h, m, s)
            cap.release()
    if not valid:
        raise RuntimeError("所有摄像头画面均无效!")
    best = max(valid, key=lambda c: (c[1] * c[2], c[0]))
    return best[0]


class CameraCapture:
    """深度=OpenNI2 + 彩色=OpenCV"""

    def __init__(self):
        self.running = False
        self.device = None
        self.depth_stream = None
        self.color_cap = None
        self.frame_queue = queue.Queue(maxsize=FRAME_QUEUE_SIZE)
        self.http_poster = None
        self.thread = None

    def set_http_poster(self, poster: FramePoster):
        self.http_poster = poster

    def start(self):
        # Depth: OpenNI2
        openni2.initialize(OPENNI2_DLL_DIR)
        self.device = openni2.Device.open_any()
        log.info("深度设备: %s", self.device.get_device_info())

        self.depth_stream = self.device.create_depth_stream()
        dvm = self.depth_stream.get_video_mode()
        dvm.resolutionX = DEPTH_WIDTH
        dvm.resolutionY = DEPTH_HEIGHT
        dvm.fps = FPS_TARGET
        self.depth_stream.set_video_mode(dvm)
        # 关闭深度镜像 (默认开启, 会导致深度图与RGB左右翻转)
        if self.depth_stream.is_property_supported(DEPTH_MIRROR_PROPERTY_ID):
            self.depth_stream.set_mirroring_enabled(DEPTH_MIRROR_ENABLED)
            log.info("深度镜像已关闭 (对齐RGB)")
        log.info("深度流(OpenNI2): %dx%d @%dfps", dvm.resolutionX, dvm.resolutionY, dvm.fps)
        self.depth_stream.start()

        # Color: OpenCV
        cams = list_cameras()
        cam_idx = find_astra_camera_index(cams)
        self.color_cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        self.color_cap.set(cv2.CAP_PROP_FRAME_WIDTH, COLOR_WIDTH)
        self.color_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, COLOR_HEIGHT)
        self.color_cap.set(cv2.CAP_PROP_FPS, FPS_TARGET)
        if not self.color_cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 {cam_idx}")
        log.info("彩色流(OpenCV): 摄像头 %d", cam_idx)

        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        log.info("采集线程已启动")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=CAMERA_STOP_JOIN_TIMEOUT)
        if self.color_cap:
            self.color_cap.release()
        try:
            if self.depth_stream:
                self.depth_stream.stop()
        except Exception:
            pass
        try:
            if self.device:
                self.device.close()
        except Exception:
            pass
        try:
            openni2.unload()
        except Exception:
            pass
        log.info("相机已释放")

    def _capture_loop(self):
        for _ in range(DEPTH_WARMUP_FRAMES):
            self.depth_stream.read_frame()
        for _ in range(COLOR_WARMUP_FRAMES):
            self.color_cap.read()

        last_log = time.time()
        frame_count = 0

        while self.running:
            try:
                depth_frame = self.depth_stream.read_frame()
                depth_raw = depth_frame.get_buffer_as_uint16()
                depth_arr = np.frombuffer(
                    bytes(depth_raw), dtype=np.uint16
                ).reshape((DEPTH_HEIGHT, DEPTH_WIDTH)).copy()

                color_arr = None
                for _ in range(COLOR_READ_MAX_RETRIES):
                    ret, frame = self.color_cap.read()
                    if not ret:
                        break
                    color_arr = frame

                if color_arr is None:
                    continue

                ts = time.time()
                _, jpeg_bytes = cv2.imencode(
                    ".jpg", color_arr,
                    [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
                )
                _, png_bytes = cv2.imencode(".png", depth_arr)

                image_b64 = base64.b64encode(jpeg_bytes).decode("ascii")
                depth_b64 = base64.b64encode(png_bytes).decode("ascii")

                frame_data = {
                    "image_b64": image_b64,
                    "depth_b64": depth_b64,
                    "timestamp": ts,
                }

                # 放入 WS 队列
                try:
                    self.frame_queue.put_nowait(frame_data)
                except queue.Full:
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame_data)
                    except queue.Empty:
                        pass

                # 帧数据仅通过 WS 推送，前端负责转发给后端

                frame_count += 1
                now = time.time()
                if now - last_log >= PERF_LOG_INTERVAL:
                    fps = frame_count / max(now - last_log, 0.001)
                    log.info(
                        "采集: %d帧 %.1ffps JPEG=%.1fKB PNG=%.1fKB 深度[%d,%d]",
                        frame_count, fps,
                        len(jpeg_bytes) / 1024, len(png_bytes) / 1024,
                        int(depth_arr.min()), int(depth_arr.max()),
                    )
                    frame_count = 0
                    last_log = now

            except Exception as cap_err:
                log.error("采集失败: %s", cap_err)
                import traceback
                traceback.print_exc()
                time.sleep(CAPTURE_ERROR_RETRY_DELAY)

    def get_frame(self, timeout=None):
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def set_exposure(self, value):
        try:
            self.color_cap.set(cv2.CAP_PROP_EXPOSURE, value)
            log.info("曝光= %d", value)
        except Exception as e:
            log.warning("设置曝光失败: %s", e)

    def set_gain(self, value):
        try:
            self.color_cap.set(cv2.CAP_PROP_GAIN, value)
            log.info("增益= %d", value)
        except Exception as e:
            log.warning("设置增益失败: %s", e)


# ─── WebSocket 服务 ──────────────────────────────────────

class VehicleServer:
    """WS 端口 8002"""

    def __init__(self, camera: CameraCapture):
        self.camera = camera
        self.clients = set()

    async def handle_client(self, websocket):
        peer = websocket.remote_address
        log.info("WS 客户端连接: %s:%s", *peer)
        self.clients.add(websocket)

        try:
            await websocket.send(json.dumps({"type": "status", "message": "camera_ready"}))

            send_task = asyncio.create_task(self._send_frames(websocket))
            recv_task = asyncio.create_task(self._receive_commands(websocket))

            done, pending = await asyncio.wait(
                [send_task, recv_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error("WS 客户端异常: %s", e)
        finally:
            self.clients.discard(websocket)
            log.info("WS 客户端断开: %s:%s", *peer)

    async def _send_frames(self, websocket):
        last_heartbeat = time.time()
        while True:
            now = time.time()
            if now - last_heartbeat >= WS_HEARTBEAT_INTERVAL:
                try:
                    await asyncio.wait_for(
                        websocket.send(json.dumps({"type": "ping"})),
                        timeout=WS_HEARTBEAT_SEND_TIMEOUT,
                    )
                    last_heartbeat = now
                except Exception:
                    return

            frame = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.camera.get_frame(timeout=WS_FRAME_POLL_TIMEOUT)
            )
            if frame is None:
                await asyncio.sleep(WS_IDLE_SLEEP)
                continue

            msg = json.dumps({
                "type": "frame",
                "timestamp": frame["timestamp"],
                "image": frame["image_b64"],
                "depth_map": frame["depth_b64"],
            })

            try:
                await asyncio.wait_for(websocket.send(msg), timeout=WS_FRAME_SEND_TIMEOUT)
            except asyncio.TimeoutError:
                continue
            except Exception:
                return

    async def _receive_commands(self, websocket):
        while True:
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=WS_RECV_TIMEOUT)
                msg = json.loads(raw)
                t = msg.get("type", "")
                if t == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
                elif t == "control":
                    cmd = msg.get("command", "")
                    if cmd == "set_exposure":
                        self.camera.set_exposure(msg.get("value", DEFAULT_EXPOSURE_VALUE))
                    elif cmd == "set_gain":
                        self.camera.set_gain(msg.get("value", DEFAULT_GAIN_VALUE))
                    else:
                        log.info("未知命令: %s", cmd)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception:
                return

    async def serve(self):
        log.info("WS 服务启动: ws://%s:%d", HOST, WS_PORT)
        async with websockets.serve(self.handle_client, HOST, WS_PORT,
                                     max_size=WS_MAX_MESSAGE_SIZE):
            await asyncio.Future()


# ─── 主入口 ──────────────────────────────────────────────

async def main():
    camera = CameraCapture()

    try:
        camera.start()
    except Exception as e:
        log.error("无法启动相机: %s", e)
        log.error("请确认:")
        log.error("  1. Astra Pro USB 已连接")
        log.error("  2. OrbbecViewer.exe 未占用相机")
        return

    server = VehicleServer(camera)

    try:
        await server.serve()
    except KeyboardInterrupt:
        log.info("收到中断信号")
    finally:
        camera.stop()
        log.info("服务已停止")


if __name__ == "__main__":
    import websockets
    print("=" * 55)
    print("  Astra Pro 小车端 — WS 帧推送服务")
    print(f"  深度: OpenNI2 {DEPTH_WIDTH}x{DEPTH_HEIGHT} @{FPS_TARGET}fps")
    print(f"  彩色: OpenCV  {COLOR_WIDTH}x{COLOR_HEIGHT} @{FPS_TARGET}fps")
    print(f"  帧数据: ws://{HOST}:{WS_PORT}")
    print("  按 Ctrl+C 停止")
    print("=" * 55)
    asyncio.run(main())
