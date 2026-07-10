#!/bin/bash
# ============================================================
# Car_detection_end/build.sh
# 编译脚本 (Jetson Nano 上运行)
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build"

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

cmake "$PROJECT_DIR" -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

echo ""
echo "Build complete."
echo "  Binary:   $BUILD_DIR/car_detection"
echo "  LiDAR:    $BUILD_DIR/lidar_bridge/lidar_stdout"
echo ""
echo "Run: $BUILD_DIR/car_detection"
