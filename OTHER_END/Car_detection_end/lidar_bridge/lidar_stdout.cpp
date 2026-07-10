// ============================================================
// Car_detection_end/lidar_bridge/lidar_stdout.cpp
// Livox LiDAR → 二进制 stdout 桥接
//
// 修复: steady_clock → system_clock (Unix 纳秒时间戳)
// ============================================================

#include <chrono>
#include <cstdint>
#include <csignal>
#include <cstring>
#include <iostream>
#include <vector>

#ifdef HAS_LIVOX_SDK
#include "livox_sdk.h"
#endif

// ── 二进制帧格式 ──
static constexpr uint8_t  FRAME_TYPE  = 0x01;
static constexpr uint32_t MAX_POINTS  = 30000;

static volatile sig_atomic_t g_running = 1;

static void on_signal(int) { g_running = 0; }

// ── 写入帧头 ──
static void write_header(uint64_t ts_ns, uint32_t payload_len, uint32_t num_points) {
    uint8_t header[17];
    header[0] = FRAME_TYPE;
    std::memcpy(header + 1, &ts_ns, 8);
    std::memcpy(header + 9, &payload_len, 4);
    std::memcpy(header + 13, &num_points, 4);
    std::cout.write(reinterpret_cast<const char*>(header), sizeof(header));
}

// ── 写入点云 ──
static void write_points(const float* data, uint32_t count) {
    size_t bytes = count * 4 * sizeof(float);  // x,y,z,intensity
    std::cout.write(reinterpret_cast<const char*>(data), bytes);
    std::cout.flush();
}

// ── 获取 Unix 纳秒时间戳 ──
static uint64_t unix_nanos() {
    auto now = std::chrono::system_clock::now().time_since_epoch();
    return std::chrono::duration_cast<std::chrono::nanoseconds>(now).count();
}

// ═══════════════════════════════════════════════════════════
//  Livox SDK 模式
// ═══════════════════════════════════════════════════════════
#ifdef HAS_LIVOX_SDK

static std::vector<float> g_point_buf;
static std::mutex g_mutex;

static void on_point_cloud(uint32_t handle, const uint8_t* dev_type,
                           LivoxLidarFrame* frame, void* client_data) {
    (void)handle; (void)dev_type; (void)client_data;
    if (!frame || frame->data_type != kLivoxLidarCartesian) return;

    auto* raw = static_cast<LivoxRawPoint*>(frame->data);
    auto cnt = static_cast<uint32_t>(frame->data_num);
    if (cnt > MAX_POINTS) cnt = MAX_POINTS;

    uint64_t ts = unix_nanos();
    uint32_t payload = cnt * 4 * sizeof(float);

    std::lock_guard<std::mutex> lock(g_mutex);
    write_header(ts, payload, cnt);

    g_point_buf.resize(cnt * 4);
    for (uint32_t i = 0; i < cnt; ++i) {
        g_point_buf[i * 4 + 0] = raw[i].x / 1000.0f;  // mm → m
        g_point_buf[i * 4 + 1] = raw[i].y / 1000.0f;
        g_point_buf[i * 4 + 2] = raw[i].z / 1000.0f;
        g_point_buf[i * 4 + 3] = static_cast<float>(raw[i].reflectivity);
    }
    write_points(g_point_buf.data(), cnt);
}

#endif  // HAS_LIVOX_SDK

// ═══════════════════════════════════════════════════════════
//  模拟模式 (无 Livox SDK 时, 输出模拟点云用于测试)
// ═══════════════════════════════════════════════════════════
#ifndef HAS_LIVOX_SDK

#include <cmath>
#include <random>
#include <thread>

static void mock_loop() {
    std::mt19937 rng(42);
    std::uniform_real_distribution<float> pos(-0.25f, 0.25f);
    std::vector<float> buf(MAX_POINTS * 4);

    while (g_running) {
        uint32_t n = 400;
        uint32_t payload = n * 4 * sizeof(float);
        uint64_t ts = unix_nanos();

        write_header(ts, payload, n);

        // 生成立方体表面点云 (模拟隧道衬砌扫描)
        for (uint32_t i = 0; i < n; ++i) {
            buf[i * 4 + 0] = pos(rng);          // x
            buf[i * 4 + 1] = 3.0f + pos(rng);   // y (前方 3m)
            buf[i * 4 + 2] = 1.5f + pos(rng);   // z (高度 1.5m)
            buf[i * 4 + 3] = 100.0f + pos(rng); // intensity
        }
        write_points(buf.data(), n);
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}

#endif

// ═══════════════════════════════════════════════════════════
//  main
// ═══════════════════════════════════════════════════════════
int main() {
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

#ifdef HAS_LIVOX_SDK
    // 初始化 Livox SDK ...
    std::cerr << "lidar_stdout: Livox mode (not fully implemented in this stub)"
              << std::endl;
    // TODO: 集成队员的 Livox SDK 初始化代码
    while (g_running) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
#else
    std::cerr << "lidar_stdout: mock mode (NO Livox SDK)" << std::endl;
    mock_loop();
#endif

    return 0;
}
