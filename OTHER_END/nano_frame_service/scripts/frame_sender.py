#!/usr/bin/env python3
"""
Astra Pro Frame Collector & Uploader (Resilient Edition)
=========================================================
Synchronizes RGB + Depth frames, encodes and POSTs to reconstruction server.

Features:
  - 3-way FPS mode switch (0=idle, 1=1fps, 2=10fps, 3=20fps) at runtime
  - Auto-detect camera disconnect → pause upload → resume when camera back
  - Auto-detect network disconnect → pause upload → resume when network back
  - Status published as ROS topic for external monitoring

State machine:
  STARTING     → waiting for first camera frames + network
  RUNNING      → healthy, sending frames
  CAMERA_LOST  → no frames for >5s, pausing
  NETWORK_LOST → server unreachable, pausing
  PAUSED       → fps_mode=0, user idle
"""

import base64
import json
import socket
import threading
import time
import sys

import numpy as np
import cv2
import requests
import rospy

from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
from std_msgs.msg import String
from message_filters import ApproximateTimeSynchronizer, Subscriber


# ---------------------------------------------------------------------------
FPS_MODE_MAP = {0: 0.0, 1: 1.0, 2: 10.0, 3: 20.0}

# Timeouts (seconds)
CAMERA_TIMEOUT = 5.0       # consider camera lost if no frame for this long
NETWORK_FAIL_THRESHOLD = 3  # consecutive POST failures to declare net lost
NETWORK_RECHECK_INTERVAL = 5.0  # how often to probe server when net lost
HEALTH_CHECK_TIMEOUT = 3.0     # timeout for TCP health check


class FrameSender:
    """Resilient frame collector with state-machine health management."""

    # Possible states
    STARTING, RUNNING, CAMERA_LOST, NETWORK_LOST, PAUSED = (
        "STARTING", "RUNNING", "CAMERA_LOST", "NETWORK_LOST", "PAUSED"
    )

    def __init__(self):
        rospy.init_node("astra_frame_sender", anonymous=False)

        # --- Parameters ---------------------------------------------------
        self.server_url = rospy.get_param(
            "~server_url", "http://121.199.173.166:8001/api/vehicle/frame"
        )
        self._parse_server_host_port()
        self.fps_mode = rospy.get_param("~fps_mode", 1)
        self.jpeg_quality = rospy.get_param("~jpeg_quality", 85)
        self.png_compression = rospy.get_param("~png_compression", 1)
        self.request_timeout = rospy.get_param("~request_timeout", 3.0)
        self.camera_ns = rospy.get_param("~camera_ns", "camera")

        # --- State --------------------------------------------------------
        self._bridge = CvBridge()
        self._lock = threading.Lock()

        self._state = self.STARTING
        self._latest_rgb = None
        self._latest_depth = None
        self._last_frame_time = 0.0
        self._frame_count = 0
        self._error_count = 0
        self._consecutive_fails = 0
        self._last_upload_time = 0.0
        self._current_fps = FPS_MODE_MAP.get(self.fps_mode, 1.0)
        self._publish_interval = 1.0 / self._current_fps if self._current_fps > 0 else float("inf")

        # --- Status publisher ---------------------------------------------
        self._status_pub = rospy.Publisher(
            "~status", String, queue_size=5
        )

        # --- Subscribers + synchronizer -----------------------------------
        rgb_sub = Subscriber(f"/{self.camera_ns}/color/image_raw", Image)
        depth_sub = Subscriber(f"/{self.camera_ns}/depth/image_raw", Image)
        self._sync = ApproximateTimeSynchronizer(
            [rgb_sub, depth_sub], queue_size=10, slop=0.05
        )
        self._sync.registerCallback(self._sync_callback)

        # --- Timers -------------------------------------------------------
        self._timer = rospy.Timer(
            rospy.Duration(0.05), self._timer_callback
        )
        self._param_watcher = rospy.Timer(
            rospy.Duration(1.0), self._param_watcher
        )

        self._publish_status()
        rospy.loginfo(
            f"FrameSender [{self._state}] | server={self.server_url} | "
            f"fps_mode={self.fps_mode} ({self._current_fps} fps)"
        )

    # ------------------------------------------------------------------
    # Server address parsing
    # ------------------------------------------------------------------
    def _parse_server_host_port(self):
        """Extract host and port from server_url for TCP health checks."""
        url = self.server_url
        # http://host:port/path → (host, port)
        try:
            if "://" in url:
                host_part = url.split("://")[1]
            else:
                host_part = url
            if "/" in host_part:
                host_part = host_part.split("/")[0]
            if ":" in host_part:
                self._server_host = host_part.split(":")[0]
                self._server_port = int(host_part.split(":")[1])
            else:
                self._server_host = host_part
                self._server_port = 80
        except Exception:
            self._server_host = "127.0.0.1"
            self._server_port = 80

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------
    def _transition(self, new_state):
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        rospy.logwarn(f"State: {old} → {new_state}")
        self._publish_status()

    def _publish_status(self):
        msg = String()
        msg.data = json.dumps({
            "state": self._state,
            "fps_mode": self.fps_mode,
            "current_fps": self._current_fps,
            "sent": self._frame_count,
            "errors": self._error_count,
            "consecutive_fails": self._consecutive_fails,
        })
        try:
            self._status_pub.publish(msg)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Network health check (raw TCP, no HTTP overhead)
    # ------------------------------------------------------------------
    def _check_network(self):
        """Return True if server port is reachable."""
        try:
            sock = socket.create_connection(
                (self._server_host, self._server_port),
                timeout=HEALTH_CHECK_TIMEOUT,
            )
            sock.close()
            return True
        except (socket.timeout, socket.error, OSError):
            return False

    # ------------------------------------------------------------------
    # Sync callback — lightweight, just stash latest frame pair
    # ------------------------------------------------------------------
    def _sync_callback(self, rgb_msg, depth_msg):
        try:
            rgb_img = self._bridge.imgmsg_to_cv2(rgb_msg, desired_encoding="bgr8")
            depth_img = self._bridge.imgmsg_to_cv2(
                depth_msg, desired_encoding="passthrough"
            )
            ts = max(
                rgb_msg.header.stamp.to_sec(),
                depth_msg.header.stamp.to_sec(),
            )
            with self._lock:
                self._latest_rgb = (ts, rgb_img)
                self._latest_depth = (ts, depth_img)
                self._last_frame_time = time.time()

            # Camera is back → recover from CAMERA_LOST
            if self._state == self.CAMERA_LOST:
                if self._check_network():
                    self._transition(self.RUNNING)
                else:
                    self._transition(self.NETWORK_LOST)

        except CvBridgeError as e:
            rospy.logerr_throttle(10, f"cv_bridge error: {e}")

    # ------------------------------------------------------------------
    # Main processing timer
    # ------------------------------------------------------------------
    def _timer_callback(self, event):
        now = time.time()

        # ---- State evaluation -----------------------------------------
        if self._state == self.PAUSED:
            return

        if self._state == self.STARTING:
            # Wait for first valid frame + network before transitioning
            has_frame = self._last_frame_time > 0
            if has_frame and self._check_network():
                self._transition(self.RUNNING)
            elif has_frame and not self._check_network():
                self._transition(self.NETWORK_LOST)
            return  # don't send in STARTING

        if self._state == self.RUNNING:
            # Check camera timeout
            if self._last_frame_time > 0 and \
               (now - self._last_frame_time) > CAMERA_TIMEOUT:
                self._transition(self.CAMERA_LOST)
                return

        if self._state == self.CAMERA_LOST:
            # Waiting for camera to come back — checked in _sync_callback
            return

        if self._state == self.NETWORK_LOST:
            # Periodic network recheck
            if self._check_network():
                # Network back — check camera too
                if self._last_frame_time > 0 and \
                   (now - self._last_frame_time) < CAMERA_TIMEOUT:
                    self._transition(self.RUNNING)
                else:
                    self._transition(self.CAMERA_LOST)
            return

        # ---- RUNNING: rate-limited upload ------------------------------
        if self._current_fps <= 0:
            return

        if now - self._last_upload_time < self._publish_interval:
            return

        with self._lock:
            if self._latest_rgb is None or self._latest_depth is None:
                return
            _, rgb_img = self._latest_rgb
            _, depth_img = self._latest_depth
            # Use wall-clock timestamp for the payload
            ts = time.time()

        # Offload encoding + POST to a short-lived thread
        t = threading.Thread(
            target=self._encode_and_send, args=(ts, rgb_img, depth_img)
        )
        t.daemon = True
        t.start()

    # ------------------------------------------------------------------
    # Encode & POST
    # ------------------------------------------------------------------
    def _encode_and_send(self, ts, rgb_img, depth_img):
        try:
            # RGB (BGR8) → JPEG → base64
            _, jpeg_buf = cv2.imencode(
                ".jpg", rgb_img,
                [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            )
            image_b64 = base64.b64encode(jpeg_buf).decode("ascii")

            # Depth (uint16 mm) → 16-bit PNG → base64
            _, png_buf = cv2.imencode(
                ".png", depth_img,
                [cv2.IMWRITE_PNG_COMPRESSION, self.png_compression]
            )
            depth_b64 = base64.b64encode(png_buf).decode("ascii")

            payload = {
                "timestamp": ts,
                "image": image_b64,
                "depth_map": depth_b64,
            }

            resp = requests.post(
                self.server_url,
                json=payload,
                timeout=self.request_timeout,
            )

            if resp.status_code == 200:
                self._frame_count += 1
                self._last_upload_time = time.time()
                self._consecutive_fails = 0
                rospy.loginfo(
                    f"[{self._frame_count}] sent | ts={ts:.3f} | "
                    f"rgb={len(image_b64)//1024}KB "
                    f"depth={len(depth_b64)//1024}KB"
                )
            else:
                self._handle_network_failure(
                    f"HTTP {resp.status_code}: {resp.text[:200]}"
                )

        except requests.exceptions.Timeout:
            self._handle_network_failure("Request timeout")
        except requests.exceptions.ConnectionError:
            self._handle_network_failure("Connection refused")
        except Exception as e:
            self._error_count += 1
            rospy.logerr(f"Unexpected error: {e}")

    def _handle_network_failure(self, reason):
        self._consecutive_fails += 1
        self._error_count += 1
        rospy.logwarn_throttle(
            10,
            f"Network fail ({self._consecutive_fails}/{NETWORK_FAIL_THRESHOLD}): {reason}"
        )
        if self._consecutive_fails >= NETWORK_FAIL_THRESHOLD:
            self._transition(self.NETWORK_LOST)

    # ------------------------------------------------------------------
    # FPS mode watcher (checks for runtime param changes)
    # ------------------------------------------------------------------
    def _param_watcher(self, event):
        new_mode = rospy.get_param("~fps_mode", self.fps_mode)
        if new_mode != self.fps_mode:
            new_fps = FPS_MODE_MAP.get(new_mode, 1.0)
            self.fps_mode = new_mode
            self._current_fps = new_fps
            self._publish_interval = (
                1.0 / new_fps if new_fps > 0 else float("inf")
            )
            if new_mode == 0:
                self._transition(self.PAUSED)
            elif self._state == self.PAUSED:
                self._transition(self.STARTING)
            rospy.loginfo(
                f"FPS mode → {new_mode} ({new_fps} fps)  [{self._state}]"
            )
            self._publish_status()

        # Periodic status log
        if self._frame_count > 0 or self._error_count > 0:
            rospy.loginfo(
                f"Stats [{self._state}]: sent={self._frame_count} "
                f"errors={self._error_count} "
                f"fails_in_row={self._consecutive_fails} "
                f"fps_mode={self.fps_mode}"
            )

    # ------------------------------------------------------------------
    def run(self):
        rospy.spin()


# ==========================================================================
if __name__ == "__main__":
    try:
        sender = FrameSender()
        sender.run()
    except rospy.ROSInterruptException:
        pass
