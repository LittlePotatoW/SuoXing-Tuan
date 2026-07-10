#include "camera.h"

#include <cstring>
#include <stdexcept>
#include <cerrno>
#include <iostream>

#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <linux/videodev2.h>

CameraCapture::CameraCapture(const Config& cfg) : cfg_(cfg) {}

CameraCapture::~CameraCapture() { close(); }

bool CameraCapture::open() {
    fd_ = ::open(cfg_.device.c_str(), O_RDWR);
    if (fd_ < 0) {
        std::cerr << "V4L2: cannot open " << cfg_.device << ": "
                  << std::strerror(errno) << std::endl;
        return false;
    }

    // ── 查询能力 ──
    v4l2_capability cap{};
    if (ioctl(fd_, VIDIOC_QUERYCAP, &cap) < 0) {
        std::cerr << "V4L2: VIDIOC_QUERYCAP failed" << std::endl;
        close(); return false;
    }

    // ── 设置 MJPEG 格式 ──
    v4l2_format fmt{};
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    fmt.fmt.pix.width = static_cast<__u32>(cfg_.width);
    fmt.fmt.pix.height = static_cast<__u32>(cfg_.height);
    fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_MJPEG;
    fmt.fmt.pix.field = V4L2_FIELD_ANY;

    if (ioctl(fd_, VIDIOC_S_FMT, &fmt) < 0) {
        std::cerr << "V4L2: MJPEG format not supported, trying fallback"
                  << std::endl;
        // 如果 MJPEG 不支持, 回退到 YUYV (需要软件编码, 较慢)
        fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_YUYV;
        if (ioctl(fd_, VIDIOC_S_FMT, &fmt) < 0) {
            std::cerr << "V4L2: fallback format also failed" << std::endl;
            close(); return false;
        }
    }

    // ── 设置 JPEG 压缩质量 ──
    if (fmt.fmt.pix.pixelformat == V4L2_PIX_FMT_MJPEG) {
        v4l2_control ctrl{};
        ctrl.id = V4L2_CID_JPEG_COMPRESSION_QUALITY;
        ctrl.value = cfg_.jpeg_quality;
        if (ioctl(fd_, VIDIOC_S_CTRL, &ctrl) < 0) {
            std::cerr << "V4L2: cannot set JPEG quality (ignored)" << std::endl;
        }
    }

    std::cout << "V4L2: " << cfg_.device
              << " " << fmt.fmt.pix.width << "x" << fmt.fmt.pix.height
              << " jpeg_q=" << cfg_.jpeg_quality << std::endl;
    return true;
}

void CameraCapture::close() {
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
}

bool CameraCapture::is_open() const { return fd_ >= 0; }

std::vector<uint8_t> CameraCapture::grab() {
    // V4L2 read() 方式 — 简单但有效, MJPEG 模式下直接返回 JPEG 字节
    constexpr size_t BUF_SIZE = 512 * 1024;  // 512KB
    std::vector<uint8_t> buf(BUF_SIZE);
    ssize_t n = ::read(fd_, buf.data(), BUF_SIZE);
    if (n <= 0) {
        std::cerr << "V4L2: read failed: " << std::strerror(errno) << std::endl;
        return {};
    }
    buf.resize(static_cast<size_t>(n));
    return buf;
}
