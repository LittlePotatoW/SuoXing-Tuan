#!/bin/bash
# =========================================================================
# Astra Pro Data Collector - Systemd Startup Script
# =========================================================================
# Sources ROS workspace and launches the data collector.
# If the camera is not connected, the driver will wait.
# The frame sender node handles camera & network auto-recovery internally.
# =========================================================================

set -e

# Source ROS environment
source /opt/ros/melodic/setup.bash
source /home/jetson/catkin_ws/devel/setup.bash

# Export for child processes
export ROS_MASTER_URI=http://localhost:11311
export ROS_IP=127.0.0.1

# Ensure roscore is running (start if not)
if ! rostopic list > /dev/null 2>&1; then
    echo "[startup] Starting roscore..."
    roscore &
    sleep 3
fi

echo "[startup] Launching Astra Pro data collector..."
exec roslaunch astra_data_collector auto_start.launch "$@"
