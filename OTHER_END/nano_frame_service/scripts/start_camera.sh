#!/bin/bash
# =========================================================================
# Astra Pro Full Pipeline Startup
# 1. roscore
# 2. astra_camera driver → ROS topics
# 3. frame_bridge (Python 2) → TCP 127.0.0.1:8004
# 4. ws_stream_server (Python 3) → WebSocket 0.0.0.0:8002
# =========================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source ROS
. /opt/ros/melodic/setup.bash
. /home/jetson/catkin_ws/devel/setup.bash
export ROS_MASTER_URI=http://localhost:11311

# Kill old processes
killall -9 roscore rosmaster rosout astra_camera_node frame_bridge.py ws_stream_server.py python python3 2>/dev/null
sleep 2
rm -f /dev/shm/sem.* 2>/dev/null

# 1. roscore
echo "[1/4] Starting roscore..."
roscore &
sleep 4
if ! rostopic list > /dev/null 2>&1; then
    echo "ERROR: roscore failed!"
    exit 1
fi
echo "      roscore OK"

# 2. Camera driver
echo "[2/4] Starting Astra Pro camera..."
roslaunch astra_camera astrapro.launch camera_name:=camera \
    enable_point_cloud:=false enable_ir:=false &
sleep 8
echo "      Camera driver started"

# 3. Frame bridge (Python2 ROS → TCP)
echo "[3/4] Starting frame bridge (ROS → TCP:8004)..."
nohup python "${SCRIPT_DIR}/frame_bridge.py" > /tmp/bridge.log 2>&1 &
sleep 3
echo "      Frame bridge started"

# 4. WebSocket server (Python3 TCP → WS:8002)
echo "[4/4] Starting WebSocket server (TCP:8004 → WS:8002)..."
nohup python3 "${SCRIPT_DIR}/ws_stream_server.py" --port 8002 --bridge-port 8004 > /tmp/ws_server.log 2>&1 &
sleep 2

echo ""
echo "=========================================="
echo "  Astra Pro Pipeline Running"
echo "  ROS camera → frame_bridge → ws_server"
echo "  WebSocket: ws://172.20.10.11:8002"
echo "=========================================="
echo ""
echo "Logs:"
echo "  bridge:    tail -f /tmp/bridge.log"
echo "  ws_server: tail -f /tmp/ws_server.log"
echo ""

# Keep running
wait
