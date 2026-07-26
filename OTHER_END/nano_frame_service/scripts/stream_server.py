#!/usr/bin/env python3
"""
Astra Pro Live Stream Server
=============================
Captures RGB (UVC) + Depth (OpenNI2) from Astra Pro and streams
them via WebSocket to a browser-based viewer.

Usage:
    python3 stream_server.py [--port 8765] [--fps 30]

Client connects to: ws://<jetson-ip>:8765
Receives JSON: {"type":"rgb", "ts":..., "data":"<base64 jpeg>"}
               {"type":"depth", "ts":..., "data":"<base64 16bit png>"}
"""

import asyncio
import base64
import ctypes
import json
import os
import signal
import sys
import time
import argparse

import cv2
import numpy as np
import websockets

# ==========================================================================
# OpenNI2 / Depth Camera Setup (via bundled libOpenNI2.so)
# ==========================================================================

# Path to ros_astra_camera's bundled ARM64 OpenNI2 redist
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_OPENNI2_REDIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR))),
    "ros_astra_camera", "include", "openni2_redist", "arm64"
)

# Fallback: try relative to catkin workspace
if not os.path.isdir(_OPENNI2_REDIST):
    _OPENNI2_REDIST = "/home/jetson/catkin_ws/src/ros_astra_camera/include/openni2_redist/arm64"

OPENNI2_SO = os.path.join(_OPENNI2_REDIST, "libOpenNI2.so")
OPENNI2_DRIVERS = os.path.join(_OPENNI2_REDIST, "OpenNI2", "Drivers")
OPENNI2_CONFIG = os.path.join(_OPENNI2_REDIST, "OpenNI.ini")

# ==========================================================================
# OpenNI2 C API definitions (minimal — just what we need for depth streaming)
# ==========================================================================

class OniDeviceInfo(ctypes.Structure):
    pass  # opaque, we don't need to inspect it

class OniVideoStream(ctypes.Structure):
    pass  # opaque handle

class OniDevice(ctypes.Structure):
    pass  # opaque handle

class OniSensorInfo(ctypes.Structure):
    _fields_ = [
        ("sensorType", ctypes.c_int),
        ("numSupportedVideoModes", ctypes.c_int),
        ("pSupportedVideoModes", ctypes.c_void_p),
    ]

class OniVideoMode(ctypes.Structure):
    _fields_ = [
        ("pixelFormat", ctypes.c_int),
        ("resolutionX", ctypes.c_int),
        ("resolutionY", ctypes.c_int),
        ("fps", ctypes.c_int),
    ]

# Pixel formats
ONI_PIXEL_FORMAT_DEPTH_1_MM = 100
ONI_PIXEL_FORMAT_DEPTH_100_UM = 101

# Sensor types
ONI_SENSOR_DEPTH = 1
ONI_SENSOR_COLOR = 2

# Status
ONI_STATUS_OK = 0

# ==========================================================================
# Depth reader using ctypes (bypasses ROS entirely)
# ==========================================================================

class DepthReader:
    """Reads depth frames from Astra Pro using bundled libOpenNI2.so via ctypes."""

    def __init__(self):
        self._lib = None
        self._device = None
        self._depth_stream = None
        self._running = False

    def start(self):
        # Set up environment so libOpenNI2 finds its drivers
        os.environ["OPENNI2_DRIVERS_PATH"] = OPENNI2_DRIVERS
        os.environ["OPENNI2_CONFIG_PATH"] = OPENNI2_CONFIG

        # Load library
        self._lib = ctypes.CDLL(OPENNI2_SO, mode=ctypes.RTLD_GLOBAL)

        # Define function signatures
        self._lib.oniInitialize.restype = ctypes.c_int
        self._lib.oniInitialize.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                             ctypes.c_void_p, ctypes.c_void_p,
                                             ctypes.c_void_p, ctypes.c_void_p]

        self._lib.oniDeviceOpen.restype = ctypes.c_int
        self._lib.oniDeviceOpen.argtypes = [ctypes.c_char_p, ctypes.c_void_p,
                                             ctypes.POINTER(ctypes.c_void_p)]

        self._lib.oniDeviceCreateStream.restype = ctypes.c_int
        self._lib.oniDeviceCreateStream.argtypes = [ctypes.c_void_p,
                                                      ctypes.c_int,
                                                      ctypes.POINTER(ctypes.c_void_p)]

        self._lib.oniStreamStart.restype = ctypes.c_int
        self._lib.oniStreamStart.argtypes = [ctypes.c_void_p]

        self._lib.oniStreamReadFrame.restype = ctypes.c_int
        self._lib.oniStreamReadFrame.argtypes = [ctypes.c_void_p,
                                                   ctypes.POINTER(ctypes.c_void_p)]

        self._lib.oniFrameGetData.restype = ctypes.POINTER(ctypes.c_uint16)
        self._lib.oniFrameGetData.argtypes = [ctypes.c_void_p]

        self._lib.oniFrameGetWidth.restype = ctypes.c_int
        self._lib.oniFrameGetWidth.argtypes = [ctypes.c_void_p]

        self._lib.oniFrameGetHeight.restype = ctypes.c_int
        self._lib.oniFrameGetHeight.argtypes = [ctypes.c_void_p]

        self._lib.oniFrameRelease.restype = None
        self._lib.oniFrameRelease.argtypes = [ctypes.c_void_p]

        # Initialize OpenNI2
        rc = self._lib.oniInitialize(2, None, None, None, None, None)  # 2 = API version
        if rc != ONI_STATUS_OK:
            raise RuntimeError(f"oniInitialize failed with code {rc}")

        # Open any device
        device_handle = ctypes.c_void_p()
        rc = self._lib.oniDeviceOpen(None, None, ctypes.byref(device_handle))
        if rc != ONI_STATUS_OK:
            raise RuntimeError(f"oniDeviceOpen failed with code {rc}. Is camera plugged in?")
        self._device = device_handle

        # Create depth stream
        stream_handle = ctypes.c_void_p()
        rc = self._lib.oniDeviceCreateStream(self._device, ONI_SENSOR_DEPTH,
                                               ctypes.byref(stream_handle))
        if rc != ONI_STATUS_OK:
            raise RuntimeError(f"oniDeviceCreateStream failed with code {rc}")
        self._depth_stream = stream_handle

        # Start stream
        rc = self._lib.oniStreamStart(self._depth_stream)
        if rc != ONI_STATUS_OK:
            raise RuntimeError(f"oniStreamStart failed with code {rc}")

        self._running = True
        print(f"[DepthReader] started | driver: {OPENNI2_DRIVERS}")

    def read_frame(self):
        """Read one depth frame. Returns (timestamp, numpy_uint16_array) or None."""
        if not self._running:
            return None

        frame_handle = ctypes.c_void_p()
        rc = self._lib.oniStreamReadFrame(self._depth_stream, ctypes.byref(frame_handle))
        if rc != ONI_STATUS_OK:
            return None

        w = self._lib.oniFrameGetWidth(frame_handle)
        h = self._lib.oniFrameGetHeight(frame_handle)
        data_ptr = self._lib.oniFrameGetData(frame_handle)

        # Copy to numpy array (uint16, millimeters)
        size = w * h
        arr = np.ctypeslib.as_array(ctypes.cast(data_ptr, ctypes.POINTER(ctypes.c_uint16)),
                                     shape=(h, w)).copy()

        ts = time.time()
        self._lib.oniFrameRelease(frame_handle)
        return (ts, arr)

    def stop(self):
        self._running = False
        if self._lib:
            self._lib.oniShutdown()


# ==========================================================================
# RGB Reader using OpenCV VideoCapture (UVC)
# ==========================================================================

class RGBReader:
    """Reads RGB frames from Astra Pro's UVC color camera via OpenCV."""

    def __init__(self, device_id=0):
        self._device_id = device_id
        self._cap = None

    def start(self):
        # Try different backends
        for api in [cv2.CAP_V4L2, cv2.CAP_ANY]:
            self._cap = cv2.VideoCapture(self._device_id, api)
            if self._cap.isOpened():
                # Configure for 640x480
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self._cap.set(cv2.CAP_PROP_FPS, 30)
                # Discard first few frames (auto-exposure settling)
                for _ in range(5):
                    self._cap.read()
                print(f"[RGBReader] started | device=/dev/video{self._device_id} "
                      f"api={api} {int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
                      f"{int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
                return
        raise RuntimeError(f"Cannot open RGB camera /dev/video{self._device_id}")

    def read_frame(self):
        if self._cap is None:
            return None
        ret, frame = self._cap.read()
        if not ret:
            return None
        return (time.time(), frame)  # BGR format

    def stop(self):
        if self._cap:
            self._cap.release()


# ==========================================================================
# WebSocket Stream Server
# ==========================================================================

class StreamServer:
    def __init__(self, port=8765, fps=30):
        self.port = port
        self.target_fps = fps
        self._clients = set()
        self._rgb = RGBReader(device_id=0)
        self._depth = DepthReader()
        self._frame_interval = 1.0 / fps if fps > 0 else 0

    async def _handler(self, websocket, path):
        self._clients.add(websocket)
        addr = websocket.remote_address
        print(f"[+] client connected: {addr}  (total: {len(self._clients)})")
        try:
            async for _ in websocket:
                pass  # client messages ignored
        except Exception:
            pass
        finally:
            self._clients.discard(websocket)
            print(f"[-] client disconnected: {addr}  (total: {len(self._clients)})")

    async def _broadcast(self, msg_json):
        if not self._clients:
            return
        dead = set()
        for ws in self._clients:
            try:
                await ws.send(msg_json)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    async def _stream_loop(self):
        print(f"[StreamServer] streaming at {self.target_fps} fps to {self.port}")
        last_send = 0
        rgb_count = 0
        depth_count = 0

        while True:
            now = time.time()

            # Rate limit
            if now - last_send < self._frame_interval:
                await asyncio.sleep(0.001)
                continue

            # Read RGB frame
            rgb_frame = self._rgb.read_frame()
            if rgb_frame is not None:
                ts, bgr_img = rgb_frame
                # Encode JPEG
                _, jpeg_buf = cv2.imencode(".jpg", bgr_img,
                                            [cv2.IMWRITE_JPEG_QUALITY, 80])
                rgb_b64 = base64.b64encode(jpeg_buf).decode("ascii")
                rgb_msg = json.dumps({"type": "rgb", "ts": ts, "data": rgb_b64})
                await self._broadcast(rgb_msg)
                rgb_count += 1

            # Read depth frame
            depth_frame = self._depth.read_frame()
            if depth_frame is not None:
                ts, depth_img = depth_frame
                # Encode 16-bit PNG
                _, png_buf = cv2.imencode(".png", depth_img,
                                            [cv2.IMWRITE_PNG_COMPRESSION, 1])
                depth_b64 = base64.b64encode(png_buf).decode("ascii")
                depth_msg = json.dumps({"type": "depth", "ts": ts, "data": depth_b64})
                await self._broadcast(depth_msg)
                depth_count += 1

            last_send = now

            # Periodic stats
            if (rgb_count + depth_count) % 100 == 0:
                print(f"  sent: rgb={rgb_count} depth={depth_count} "
                      f"clients={len(self._clients)}")

    def start(self):
        print("=" * 50)
        print("Astra Pro Live Stream Server")
        print(f"  RGB:  UVC /dev/video0")
        print(f"  Depth: OpenNI2 (libOpenNI2.so)")
        print(f"  Port: {self.port}")
        print("=" * 50)

        self._rgb.start()
        self._depth.start()
        print("[StreamServer] Both cameras ready, starting WebSocket server...")

        loop = asyncio.get_event_loop()
        server = websockets.serve(self._handler, "0.0.0.0", self.port)
        loop.run_until_complete(server)

        try:
            loop.run_until_complete(self._stream_loop())
        except KeyboardInterrupt:
            print("\n[StreamServer] Shutting down...")
        finally:
            self._rgb.stop()
            self._depth.stop()


# ==========================================================================
# Main
# ==========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Astra Pro Live Stream Server")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--fps", type=int, default=30, help="Stream frame rate")
    args = parser.parse_args()

    srv = StreamServer(port=args.port, fps=args.fps)
    srv.start()
