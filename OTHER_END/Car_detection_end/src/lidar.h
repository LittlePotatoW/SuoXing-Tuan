#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include <memory>

class LidarCapture {
public:
    struct Point {
        float x, y, z, intensity;
    };

    struct Frame {
        uint64_t timestamp_ns = 0;   // Unix 纳秒 (system_clock)
        std::vector<Point> points;
    };

    struct Config {
        std::string binary_path = "./lidar_bridge/lidar_stdout";
        int max_points = 30000;
    };

    explicit LidarCapture(const Config& cfg);
    ~LidarCapture();

    LidarCapture(const LidarCapture&) = delete;
    LidarCapture& operator=(const LidarCapture&) = delete;

    bool start();
    void stop();
    bool alive() const;

    // 阻塞读取一帧. 超时返回空帧
    Frame read_frame(int timeout_ms = 2000);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
