#!/bin/bash
# ============================================================
# Car_detection_end/start.sh
# 开机自启 — 等待网络 + 启动车端采集程序
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="$PROJECT_DIR/build/car_detection"
CONFIG="$PROJECT_DIR/config.json"
LIDAR_BRIDGE="$PROJECT_DIR/build/lidar_bridge/lidar_stdout"

echo "[$(date)] Starting Car Detection End..."

# 切换到项目目录
cd "$PROJECT_DIR"

# 启动采集程序
exec "$BINARY"

echo "[$(date)] Car Detection End stopped."