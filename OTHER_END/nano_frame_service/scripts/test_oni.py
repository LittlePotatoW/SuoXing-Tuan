#!/usr/bin/env python3
"""Test OpenNI2 ctypes loading for Astra Pro depth camera."""
import ctypes
import os
import sys

# Set up OpenNI2 environment
REDIST = "/home/jetson/catkin_ws/src/ros_astra_camera/include/openni2_redist/arm64"
os.environ["OPENNI2_DRIVERS_PATH"] = os.path.join(REDIST, "OpenNI2", "Drivers")

print("Loading libOpenNI2.so...")
lib = ctypes.CDLL(os.path.join(REDIST, "libOpenNI2.so"))
print("Library loaded:", lib)

# oniInitialize
lib.oniInitialize.restype = ctypes.c_int
lib.oniInitialize.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                               ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

rc = lib.oniInitialize(2, None, None, None, None, None)
print(f"oniInitialize: rc={rc}")

if rc != 0:
    # Try to get extended error
    try:
        lib.oniGetExtendedError.restype = ctypes.c_char_p
        err = lib.oniGetExtendedError()
        print(f"Extended error: {err}")
    except:
        pass
    sys.exit(1)

# oniDeviceOpen
lib.oniDeviceOpen.restype = ctypes.c_int
lib.oniDeviceOpen.argtypes = [ctypes.c_char_p, ctypes.c_void_p,
                               ctypes.POINTER(ctypes.c_void_p)]

device = ctypes.c_void_p()
rc = lib.oniDeviceOpen(None, None, ctypes.byref(device))
print(f"oniDeviceOpen: rc={rc}")

if rc != 0:
    print("Cannot open device. Is Astra Pro plugged in?")
    lib.oniShutdown()
    sys.exit(1)

# oniDeviceCreateStream (depth)
lib.oniDeviceCreateStream.restype = ctypes.c_int
lib.oniDeviceCreateStream.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                       ctypes.POINTER(ctypes.c_void_p)]

depth_stream = ctypes.c_void_p()
rc = lib.oniDeviceCreateStream(device, 1, ctypes.byref(depth_stream))  # 1 = SENSOR_DEPTH
print(f"oniDeviceCreateStream(depth): rc={rc}")

if rc != 0:
    print("Cannot create depth stream")
    lib.oniShutdown()
    sys.exit(1)

# oniStreamStart
lib.oniStreamStart.restype = ctypes.c_int
lib.oniStreamStart.argtypes = [ctypes.c_void_p]

rc = lib.oniStreamStart(depth_stream)
print(f"oniStreamStart: rc={rc}")

if rc != 0:
    print("Cannot start depth stream")
    lib.oniShutdown()
    sys.exit(1)

# Read one frame
lib.oniStreamReadFrame.restype = ctypes.c_int
lib.oniStreamReadFrame.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]

lib.oniFrameGetWidth.restype = ctypes.c_int
lib.oniFrameGetWidth.argtypes = [ctypes.c_void_p]

lib.oniFrameGetHeight.restype = ctypes.c_int
lib.oniFrameGetHeight.argtypes = [ctypes.c_void_p]

frame = ctypes.c_void_p()
rc = lib.oniStreamReadFrame(depth_stream, ctypes.byref(frame))
print(f"oniStreamReadFrame: rc={rc}")

if rc == 0:
    w = lib.oniFrameGetWidth(frame)
    h = lib.oniFrameGetHeight(frame)
    print(f"Depth frame: {w}x{h}")
    lib.oniFrameRelease(frame)
else:
    print("No depth frame received (timeout?)")

# Cleanup
lib.oniShutdown()
print("Done!")
