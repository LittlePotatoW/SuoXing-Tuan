#!/usr/bin/env python
"""
frame_bridge.py (ROS Melodic / Python 2)
=========================================
Bridges ROS camera topics to a local TCP stream.
Subscribes to RGB + Depth, encodes frames, writes JSON lines to TCP clients.

TCP Protocol: newline-delimited JSON, one frame per line
Format: {"timestamp": 1234567890.123, "image": "<base64 JPEG>", "depth_map": "<base64 PNG>"}

Listens on: tcp://127.0.0.1:8004
"""
import base64
import json
import socket
import threading
import time
import sys

import rospy
import numpy as np
import cv2
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
from message_filters import ApproximateTimeSynchronizer, Subscriber


# ---- config ------------------------------------------------------------
CAMERA_NS = "camera"
TCP_HOST = "127.0.0.1"
TCP_PORT = 8004
JPEG_QUALITY = 80
MAX_CLIENTS = 5


class FrameBridge:
    def __init__(self):
        rospy.init_node("frame_bridge", anonymous=False)

        self._bridge = CvBridge()
        self._lock = threading.Lock()
        self._latest_rgb = None
        self._latest_depth = None
        self._clients = []
        self._running = True

        # ROS subscribers + synchronizer
        rgb_sub = Subscriber("/{}/rgb/image_raw".format(CAMERA_NS), Image)
        depth_sub = Subscriber("/{}/depth/image_raw".format(CAMERA_NS), Image)
        self._sync = ApproximateTimeSynchronizer(
            [rgb_sub, depth_sub], queue_size=10, slop=0.05
        )
        self._sync.registerCallback(self._sync_cb)

        # TCP server thread
        self._tcp_thread = threading.Thread(target=self._tcp_server)
        self._tcp_thread.daemon = True
        self._tcp_thread.start()

        rospy.loginfo("FrameBridge: listening on tcp://%s:%d", TCP_HOST, TCP_PORT)

    # ---- ROS sync callback --------------------------------------------
    def _sync_cb(self, rgb_msg, depth_msg):
        try:
            rgb_img = self._bridge.imgmsg_to_cv2(rgb_msg, desired_encoding="bgr8")
            depth_img = self._bridge.imgmsg_to_cv2(depth_msg, desired_encoding="passthrough")
            ts = max(rgb_msg.header.stamp.to_sec(), depth_msg.header.stamp.to_sec())
            with self._lock:
                self._latest_rgb = (ts, rgb_img)
                self._latest_depth = (ts, depth_img)
        except CvBridgeError as e:
            rospy.logerr_throttle(10, "cv_bridge error: %s", e)

    # ---- TCP server ---------------------------------------------------
    def _tcp_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((TCP_HOST, TCP_PORT))
        sock.listen(MAX_CLIENTS)
        sock.settimeout(1.0)

        while self._running:
            try:
                conn, addr = sock.accept()
                rospy.loginfo("TCP client connected: %s:%d", *addr)
                self._clients.append(conn)
                t = threading.Thread(target=self._client_handler, args=(conn,))
                t.daemon = True
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    rospy.logerr("TCP accept error: %s", e)

        sock.close()

    def _client_handler(self, conn):
        conn.settimeout(30.0)
        frame_count = 0
        last_log = time.time()

        while self._running:
            with self._lock:
                if self._latest_rgb is None or self._latest_depth is None:
                    time.sleep(0.01)
                    continue
                ts, rgb = self._latest_rgb
                _, depth = self._latest_depth

            # Encode
            try:
                _, jpeg_buf = cv2.imencode(".jpg", rgb,
                                           [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                _, png_buf = cv2.imencode(".png", depth,
                                          [cv2.IMWRITE_PNG_COMPRESSION, 1])

                image_b64 = base64.b64encode(jpeg_buf)
                depth_b64 = base64.b64encode(png_buf)
            except Exception as e:
                rospy.logerr("Encode error: %s", e)
                continue

            line = json.dumps({
                "timestamp": ts,
                "image": image_b64,
                "depth_map": depth_b64,
            }) + "\n"

            try:
                conn.sendall(line.encode("ascii"))
            except Exception:
                break

            # Rate limit to ~30fps
            frame_count += 1
            if frame_count >= 30:
                elapsed = time.time() - last_log
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
                frame_count = 0
                last_log = time.time()

        # Client disconnected
        try:
            conn.close()
        except Exception:
            pass
        if conn in self._clients:
            self._clients.remove(conn)
        rospy.loginfo("TCP client disconnected")

    def run(self):
        rospy.spin()
        self._running = False


if __name__ == "__main__":
    try:
        FrameBridge().run()
    except rospy.ROSInterruptException:
        pass
