#!/usr/bin/env python
"""
Depth Colorizer Node (ROS Melodic / Python 2)
================================================
Subscribes to /camera/depth/image_raw (16UC1, mm)
Applies Turbo colormap
Publishes to /camera/depth/image_color (RGB8) for web_video_server
"""
import rospy
import numpy as np
import cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


def build_turbo_colormap():
    """256-entry BGR turbo-inspired colormap."""
    stops = [
        (0.0,   (0, 0, 0)),
        (0.1,   (120, 30, 30)),
        (0.3,   (200, 140, 0)),
        (0.5,   (80, 200, 50)),
        (0.7,   (30, 210, 230)),
        (0.85,  (20, 120, 240)),
        (1.0,   (20, 60, 220)),
    ]
    cmap = np.zeros((256, 1, 3), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        lo, hi = stops[0], stops[-1]
        for s in range(len(stops) - 1):
            if stops[s][0] <= t <= stops[s + 1][0]:
                lo, hi = stops[s], stops[s + 1]
                break
        frac = (t - lo[0]) / (hi[0] - lo[0]) if hi[0] != lo[0] else 0
        rgb = tuple(
            int(lo[1][c] + frac * (hi[1][c] - lo[1][c])) for c in range(3)
        )
        cmap[i, 0] = rgb  # BGR for OpenCV
    return cmap


TURBO = build_turbo_colormap()


class DepthColorizer:
    def __init__(self):
        rospy.init_node("depth_colorizer", anonymous=False)
        self._bridge = CvBridge()
        self._pub = rospy.Publisher(
            "/camera/depth/image_color", Image, queue_size=5
        )
        self._sub = rospy.Subscriber(
            "/camera/depth/image_raw", Image, self._callback, queue_size=5
        )
        rospy.loginfo("DepthColorizer started")

    def _callback(self, msg):
        try:
            depth = self._bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as e:
            rospy.logerr_throttle(10, "cv_bridge error: %s" % e)
            return

        # depth is uint16 numpy (mm)
        valid = depth > 10  # ignore noise < 1cm
        if np.any(valid):
            vmin = depth[valid].min()
            vmax = depth[valid].max()
        else:
            vmin, vmax = 0, 5000

        if vmax <= vmin:
            vmax = vmin + 1

        # Normalize to 0-255
        scaled = np.clip((depth.astype(np.float32) - vmin) / (vmax - vmin) * 255, 0, 255)
        scaled = scaled.astype(np.uint8)

        # Apply colormap
        colored = cv2.applyColorMap(scaled, cv2.COLORMAP_JET)
        # Set invalid pixels to black
        colored[depth <= 10] = (0, 0, 0)

        # Publish
        out_msg = self._bridge.cv2_to_imgmsg(colored, encoding="bgr8")
        out_msg.header = msg.header
        self._pub.publish(out_msg)


if __name__ == "__main__":
    try:
        DepthColorizer()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
