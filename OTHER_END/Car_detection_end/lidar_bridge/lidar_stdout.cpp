// ============================================================
// Car_detection_end/lidar_bridge/lidar_stdout.cpp
// Livox LiDAR (Mid-40) → 二进制 stdout 桥接
//
// Livox SDK v2 API:
//   Init → SetBroadcastCallback → Start
//   → 广播回调中 AddLidarToConnect(broadcast_code)
//   → DeviceStateUpdateCallback(kEventConnect) 中 SetDataCallback + LidarStartSampling
//   → 数据回调中输出二进制帧到 stdout
// ============================================================

#include <chrono>
#include <cstdint>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <vector>

#ifdef HAS_LIVOX_SDK
#include "livox_sdk.h"
#include <mutex>
#include <thread>
#include <fcntl.h>
#include <unistd.h>
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
    size_t bytes = count * 4 * sizeof(float);
    std::cout.write(reinterpret_cast<const char*>(data), bytes);
    std::cout.flush();
}

// ═══════════════════════════════════════════════════════════
//  Livox SDK v2 模式
// ═══════════════════════════════════════════════════════════
#ifdef HAS_LIVOX_SDK

static std::mutex g_mutex;
static uint8_t   g_lidar_handle = 0;
static bool      g_connected    = false;
static bool      g_sampling     = false;

// ── 点云数据回调 ──
static void on_point_cloud(uint8_t handle, LivoxEthPacket *data,
                           uint32_t data_num, void *client_data) {
    (void)handle;
    (void)client_data;
    if (!data || data_num == 0) return;

    // 仅处理 Cartesian 格式 (Mid-40 默认)
    if (data->data_type != kCartesian) return;

    uint32_t cnt = data_num;
    if (cnt > MAX_POINTS) cnt = MAX_POINTS;

    // 解析 8 字节纳秒时间戳
    uint64_t ts = 0;
    std::memcpy(&ts, data->timestamp, 8);

    uint32_t payload = cnt * 4 * sizeof(float);

    // LivoxRawPoint[] → float[4] (mm → m)
    std::vector<float> buf(cnt * 4);
    auto* raw = reinterpret_cast<LivoxRawPoint*>(data->data);
    for (uint32_t i = 0; i < cnt; ++i) {
        buf[i * 4 + 0] = raw[i].x / 1000.0f;
        buf[i * 4 + 1] = raw[i].y / 1000.0f;
        buf[i * 4 + 2] = raw[i].z / 1000.0f;
        buf[i * 4 + 3] = static_cast<float>(raw[i].reflectivity);
    }

    std::lock_guard<std::mutex> lock(g_mutex);
    write_header(ts, payload, cnt);
    write_points(buf.data(), cnt);
}

// ── 设备广播回调: 发现 Mid-40 后加入连接列表 ──
static void on_broadcast(const BroadcastDeviceInfo *info) {
    if (!info) return;
    // 仅连接 Mid-40 (type=1)
    if (info->dev_type != kDeviceTypeLidarMid40) return;

    // 避免重复添加
    if (g_connected) return;

    std::cerr << "lidar_stdout: found Mid-40, code="
              << info->broadcast_code
              << " ip=" << info->ip << std::endl;

    uint8_t handle = 0;
    livox_status st = AddLidarToConnect(info->broadcast_code, &handle);
    if (st == kStatusSuccess) {
        std::cerr << "lidar_stdout: added to connect list, handle="
                  << static_cast<int>(handle) << std::endl;
        g_lidar_handle = handle;
    } else {
        std::cerr << "lidar_stdout: AddLidarToConnect failed, status="
                  << st << std::endl;
    }
}

// ── 设备状态回调 ──
static void on_device_state(const DeviceInfo *device, DeviceEvent type) {
    if (!device) return;

    if (type == kEventConnect) {
        std::cerr << "lidar_stdout: connected! handle="
                  << static_cast<int>(device->handle) << std::endl;
        g_connected = true;
        g_lidar_handle = device->handle;

        // 设置点云回调
        SetDataCallback(device->handle, on_point_cloud, nullptr);

        // 开始采样
        livox_status st = LidarStartSampling(device->handle, nullptr, nullptr);
        if (st == kStatusSuccess) {
            g_sampling = true;
            std::cerr << "lidar_stdout: sampling started" << std::endl;
        } else {
            std::cerr << "lidar_stdout: LidarStartSampling failed, status="
                      << st << std::endl;
        }
    } else if (type == kEventDisconnect) {
        std::cerr << "lidar_stdout: disconnected" << std::endl;
        g_connected = false;
        g_sampling = false;
    } else if (type == kEventStateChange) {
        std::cerr << "lidar_stdout: state changed to "
                  << static_cast<int>(device->state) << std::endl;
    }
}

#endif  // HAS_LIVOX_SDK

// ═══════════════════════════════════════════════════════════
//  模拟模式 (无 Livox SDK, 输出 "SIM" 假点云)
// ═══════════════════════════════════════════════════════════
#ifndef HAS_LIVOX_SDK

#include <thread>

static const bool FONT_SIM[3][5][5] = {
    {{0,1,1,1,0}, {1,0,0,0,1}, {0,1,1,1,0}, {0,0,0,0,1}, {1,1,1,1,0}},
    {{0,1,1,1,0}, {0,0,1,0,0}, {0,0,1,0,0}, {0,0,1,0,0}, {0,1,1,1,0}},
    {{1,0,0,0,1}, {1,1,0,1,1}, {1,0,1,0,1}, {1,0,0,0,1}, {1,0,0,0,1}},
};

static void mock_loop() {
    float sim_pts[3 * 5 * 5 * 4];
    uint32_t sim_n = 0;
    for (int li = 0; li < 3; li++) {
        float ox = li * 1.5f - 1.5f;
        for (int row = 0; row < 5; row++) {
            for (int col = 0; col < 5; col++) {
                if (FONT_SIM[li][row][col]) {
                    sim_pts[sim_n * 4 + 0] = ox + col * 0.25f;
                    sim_pts[sim_n * 4 + 1] = 3.0f - row * 0.25f;
                    sim_pts[sim_n * 4 + 2] = 1.5f;
                    sim_pts[sim_n * 4 + 3] = 100.0f;
                    sim_n++;
                }
            }
        }
    }
    uint32_t payload = sim_n * 4 * sizeof(float);
    // 这里需要 unix_nanos, 模拟模式需要时间戳
    while (g_running) {
        auto now = std::chrono::system_clock::now().time_since_epoch();
        uint64_t ts = std::chrono::duration_cast<std::chrono::nanoseconds>(now).count();
        write_header(ts, payload, sim_n);
        write_points(sim_pts, sim_n);
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}

#endif  // !HAS_LIVOX_SDK

// ═══════════════════════════════════════════════════════════
//  main
// ═══════════════════════════════════════════════════════════
int main(int argc, char** argv) {
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    // 解析 -n <frames> 参数: 输出指定帧数后自动退出
    int max_frames = 0;  // 0 = 不限
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-n") == 0 && i + 1 < argc) {
            max_frames = std::atoi(argv[++i]);
        }
    }

#ifdef HAS_LIVOX_SDK
    std::cerr << "lidar_stdout: Livox SDK v2 mode" << std::endl;

    // SDK 内部日志会直接写 stdout (不受 DisableConsoleLogger 控制).
    // 在 SDK 初始化期间临时将 stdout 重定向到 /dev/null.
    int stdout_backup = dup(STDOUT_FILENO);
    int devnull = open("/dev/null", O_WRONLY);
    dup2(devnull, STDOUT_FILENO);
    close(devnull);

    if (!Init()) {
        dup2(stdout_backup, STDOUT_FILENO);
        close(stdout_backup);
        std::cerr << "lidar_stdout: Init() failed" << std::endl;
        return 1;
    }
    DisableConsoleLogger();

    SetBroadcastCallback(on_broadcast);
    SetDeviceStateUpdateCallback(on_device_state);

    if (!Start()) {
        dup2(stdout_backup, STDOUT_FILENO);
        close(stdout_backup);
        std::cerr << "lidar_stdout: Start() failed" << std::endl;
        Uninit();
        return 1;
    }

    // 等待设备连接 (此时 SDK 日志仍会继续输出, 保持重定向)
    std::cerr << "lidar_stdout: scanning for Mid-40..." << std::endl;
    while (g_running && !g_sampling) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    // 连接成功, 恢复 stdout 开始输出二进制帧
    dup2(stdout_backup, STDOUT_FILENO);
    close(stdout_backup);
    std::cerr << "lidar_stdout: running, outputting frames..." << std::endl;

    // 保持运行 (支持 -n 自动退出)
    int frame_count = 0;
    while (g_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        if (max_frames > 0) {
            // 粗略计数: 以 ~10Hz 估算, 100ms ≈ 1 帧
            frame_count++;
            if (frame_count >= max_frames) {
                std::cerr << "lidar_stdout: captured " << frame_count
                          << " frames, exiting" << std::endl;
                break;
            }
        }
    }

    // 清理 — 再次屏蔽 stdout 防止 SDK Uninit 日志污染
    stdout_backup = dup(STDOUT_FILENO);
    devnull = open("/dev/null", O_WRONLY);
    dup2(devnull, STDOUT_FILENO);
    close(devnull);

    if (g_sampling) {
        LidarStopSampling(g_lidar_handle, nullptr, nullptr);
    }
    Uninit();

    dup2(stdout_backup, STDOUT_FILENO);
    close(stdout_backup);
    std::cerr << "lidar_stdout: stopped" << std::endl;
#else
    std::cerr << "lidar_stdout: mock mode (NO Livox SDK)" << std::endl;
    mock_loop();
#endif

    return 0;
}
