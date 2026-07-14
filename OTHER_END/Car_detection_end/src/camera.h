#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include <memory>

class CameraCapture {
public:
    struct Config {
        std::string device = "/dev/video0";
        int width = 640;
        int height = 480;
        int jpeg_quality = 50;
    };

    explicit CameraCapture(const Config& cfg);
    ~CameraCapture();

    CameraCapture(const CameraCapture&) = delete;
    CameraCapture& operator=(const CameraCapture&) = delete;

    bool open();
    void close();
    bool is_open() const;

    // 抓取一帧 JPEG (MJPEG 模式)
    std::vector<uint8_t> grab();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
