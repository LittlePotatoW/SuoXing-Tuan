// ============================================================
// Car_detection_end/src/main.cpp
// 车端主程序 — 采集 LiDAR + 双相机 → 发送到 Transpond_Server
// ============================================================

// ══════════════════════════════════════════════
//  ⚙️ 默认参数 — 命令行可覆盖
// ══════════════════════════════════════════════
static const char*  DEFAULT_HOST         = "127.0.0.1";
static const int    DEFAULT_PORT         = 8001;
static const int    DEFAULT_JPEG_QUALITY = 50;     // 1-100
static const int    DEFAULT_CAM_W        = 640;
static const int    DEFAULT_CAM_H        = 480;
static const int    DEFAULT_LOC_MS       = 200;    // 定位发送间隔
static const int    DEFAULT_DET_MS       = 1000;   // 检测发送间隔
static const int    DEFAULT_WDOG_MS      = 10000;  // 看门狗超时
static const double DEFAULT_VELOCITY     = 0.5;    // m/s
static const double DEFAULT_STEERING     = 0.0;    // rad
static const double DEFAULT_WHEEL_BASE   = 1.5;    // m

// ============================================================

#include "camera.h"
#include "lidar.h"
#include "packet.h"
#include "sender.h"
#include "watchdog.h"

#include <atomic>
#include <csignal>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>

static std::atomic<bool> g_running{true};
static void on_signal(int) { g_running = false; }

int main(int argc, char** argv) {
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    // ── 参数解析 ──
    std::string host         = DEFAULT_HOST;
    int port                 = DEFAULT_PORT;
    int jpeg_quality         = DEFAULT_JPEG_QUALITY;
    int cam_w                = DEFAULT_CAM_W;
    int cam_h                = DEFAULT_CAM_H;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--host") == 0 && i + 1 < argc)
            host = argv[++i];
        else if (strcmp(argv[i], "--port") == 0 && i + 1 < argc)
            port = std::stoi(argv[++i]);
        else if (strcmp(argv[i], "--jpeg-quality") == 0 && i + 1 < argc)
            jpeg_quality = std::stoi(argv[++i]);
        else if (strcmp(argv[i], "--cam-w") == 0 && i + 1 < argc)
            cam_w = std::stoi(argv[++i]);
        else if (strcmp(argv[i], "--cam-h") == 0 && i + 1 < argc)
            cam_h = std::stoi(argv[++i]);
        else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            std::cout << "Usage: car_detection [options]\n"
                      << "  --host HOST         server IP (default: " << DEFAULT_HOST << ")\n"
                      << "  --port PORT         server port (default: " << DEFAULT_PORT << ")\n"
                      << "  --jpeg-quality Q    JPEG quality 1-100 (default: " << DEFAULT_JPEG_QUALITY << ")\n"
                      << "  --cam-w W           camera width (default: " << DEFAULT_CAM_W << ")\n"
                      << "  --cam-h H           camera height (default: " << DEFAULT_CAM_H << ")\n";
            return 0;
        }
    }

    std::cout << "Server: " << host << ":" << port << std::endl;
    std::cout << "Camera: " << cam_w << "x" << cam_h << " jpeg_q=" << jpeg_quality << std::endl;
    std::cout << "Timing: loc=" << DEFAULT_LOC_MS << "ms det=" << DEFAULT_DET_MS << "ms" << std::endl;

    // ── 双相机 ──
    CameraCapture::Config cam_cfg;
    cam_cfg.width  = cam_w;
    cam_cfg.height = cam_h;
    cam_cfg.jpeg_quality = jpeg_quality;

    std::vector<std::unique_ptr<CameraCapture>> cameras;
    std::vector<Pose> camera_poses;

    const char* devs[] = {"/dev/video0", "/dev/video1"};
    for (auto* dev : devs) {
        cam_cfg.device = dev;
        auto cam = std::make_unique<CameraCapture>(cam_cfg);
        if (cam->open()) {
            cameras.push_back(std::move(cam));
            // 默认相机外参 (需标定替换)
            camera_poses.push_back({0.0, 0.0, 1.0, 0.7071, 0.0, 0.7071, 0.0});
            std::cout << "Camera " << cameras.size() << ": " << dev << std::endl;
        } else {
            std::cerr << "Camera init failed: " << dev << std::endl;
        }
    }

    if (cameras.empty()) {
        std::cerr << "No camera available, exiting." << std::endl;
        return 1;
    }

    // ── LiDAR ──
    LidarCapture::Config lidar_cfg;
    lidar_cfg.binary_path = "./build/lidar_bridge/lidar_stdout";
    lidar_cfg.max_points  = 30000;
    LidarCapture lidar(lidar_cfg);
    if (!lidar.start()) { std::cerr << "LiDAR init failed" << std::endl; return 1; }

    // ── HTTP 发送器 ──
    HttpSender sender(host, port);

    // ── 定位线程 ──
    std::thread loc_thread([&]() {
        while (g_running) {
            auto body = build_location_packet(
                DEFAULT_VELOCITY, DEFAULT_STEERING, DEFAULT_WHEEL_BASE,
                std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::system_clock::now().time_since_epoch()).count());
            sender.post("/location", body);
            std::this_thread::sleep_for(std::chrono::milliseconds(DEFAULT_LOC_MS));
        }
    });

    // ── 检测线程 ──
    std::thread det_thread([&]() {
        // "FAIL" 字体 — LiDAR 断连时显示
        static const bool FONT_FAIL[4][5][5] = {
            {{1,1,1,1,1}, {1,0,0,0,0}, {1,1,1,1,0}, {1,0,0,0,0}, {1,0,0,0,0}},
            {{0,1,1,1,0}, {1,0,0,0,1}, {1,1,1,1,1}, {1,0,0,0,1}, {1,0,0,0,1}},
            {{0,1,1,1,0}, {0,0,1,0,0}, {0,0,1,0,0}, {0,0,1,0,0}, {0,1,1,1,0}},
            {{1,0,0,0,0}, {1,0,0,0,0}, {1,0,0,0,0}, {1,0,0,0,0}, {1,1,1,1,1}},
        };
        int idx = 0;
        while (g_running) {
            auto now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();

            // 1 秒内收集 LiDAR 帧
            std::vector<LidarCapture::Frame> lidar_frames;
            auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(950);
            while (std::chrono::steady_clock::now() < deadline) {
                auto f = lidar.read_frame(100);
                if (!f.points.empty()) lidar_frames.push_back(std::move(f));
            }

            // 合并所有帧的 points
            std::vector<float> pts;
            int pc = 0;
            for (auto& f : lidar_frames) {
                for (auto& p : f.points) {
                    pts.insert(pts.end(), {p.x, p.y, p.z});
                    pc++;
                }
            }

            // LiDAR 无数据时用 "FAIL" 假点云
            if (pc == 0) {
                for (int li = 0; li < 4; li++) {
                    float ox = li * 1.4f - 2.8f;
                    for (int row = 0; row < 5; row++) {
                        for (int col = 0; col < 5; col++) {
                            if (FONT_FAIL[li][row][col]) {
                                pts.insert(pts.end(), {
                                    ox + col * 0.25f,
                                    3.0f - row * 0.25f,
                                    1.5f
                                });
                                pc++;
                            }
                        }
                    }
                }
            }

            // 从所有相机抓图
            std::vector<CameraFrame> cam_frames;
            for (size_t ci = 0; ci < cameras.size(); ci++) {
                auto jpeg = cameras[ci]->grab();
                if (!jpeg.empty()) {
                    cam_frames.push_back({std::move(jpeg), cam_w, cam_h, camera_poses[ci]});
                }
            }
            if (cam_frames.empty()) continue;

            Pose car{0, 0, 0, 1, 0, 0, 0};
            auto body = build_detection_packet(
                "car_" + std::to_string(idx), now_ns,
                pts, pc, cam_frames,
                car,
                DEFAULT_VELOCITY, DEFAULT_STEERING, DEFAULT_WHEEL_BASE);

            auto resp = sender.post("/frames", body);

            // 日志: 显示每路相机 JPEG 大小
            std::cout << "det " << idx << ": HTTP " << resp.status_code
                      << " frames=" << lidar_frames.size() << " pts=" << pc;
            for (size_t ci = 0; ci < cam_frames.size(); ci++) {
                std::cout << " jpeg" << ci << "=" << cam_frames[ci].jpeg.size()/1024 << "KB";
            }
            std::cout << std::endl;
            idx++;
        }
    });

    // ── 看门狗 ──
    std::thread wd_thread([&]() {
        Watchdog wd(DEFAULT_WDOG_MS);
        while (g_running) {
            wd.feed();
            if (!lidar.alive()) {
                std::cerr << "LiDAR dead, restarting..." << std::endl;
                lidar.stop();
                std::this_thread::sleep_for(std::chrono::seconds(1));
                lidar.start();
            }
            std::this_thread::sleep_for(std::chrono::seconds(2));
        }
    });

    std::cout << "Running. Ctrl+C to stop." << std::endl;
    loc_thread.join();
    det_thread.join();
    wd_thread.join();

    lidar.stop();
    for (auto& cam : cameras) {
        cam->close();
    }
    std::cout << "Stopped." << std::endl;
    return 0;
}
