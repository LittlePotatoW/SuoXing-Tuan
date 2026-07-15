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

static constexpr int BUF_COUNT = 4;

struct Buffer {
    void*  start  = nullptr;
    size_t length = 0;
};

struct CameraCapture::Impl {
    Config cfg;
    int fd = -1;
    Buffer buffers[BUF_COUNT];
    int nbufs = 0;
};

CameraCapture::CameraCapture(const Config& cfg)
    : impl_(std::make_unique<Impl>(Impl{cfg})) {}

CameraCapture::~CameraCapture() { close(); }

bool CameraCapture::open() {
    impl_->fd = ::open(impl_->cfg.device.c_str(), O_RDWR);
    if (impl_->fd < 0) {
        std::cerr << "V4L2: cannot open " << impl_->cfg.device << ": "
                  << std::strerror(errno) << std::endl;
        return false;
    }

    // ── 查询能力 ──
    v4l2_capability cap{};
    if (ioctl(impl_->fd, VIDIOC_QUERYCAP, &cap) < 0) {
        std::cerr << "V4L2: VIDIOC_QUERYCAP failed" << std::endl;
        close(); return false;
    }

    if (!(cap.capabilities & V4L2_CAP_VIDEO_CAPTURE)) {
        std::cerr << "V4L2: " << impl_->cfg.device << " is not a capture device" << std::endl;
        close(); return false;
    }

    if (!(cap.capabilities & V4L2_CAP_STREAMING)) {
        std::cerr << "V4L2: " << impl_->cfg.device << " does not support streaming I/O" << std::endl;
        close(); return false;
    }

    // ── 设置 MJPEG 格式 ──
    v4l2_format fmt{};
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    fmt.fmt.pix.width = static_cast<__u32>(impl_->cfg.width);
    fmt.fmt.pix.height = static_cast<__u32>(impl_->cfg.height);
    fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_MJPEG;
    fmt.fmt.pix.field = V4L2_FIELD_ANY;

    if (ioctl(impl_->fd, VIDIOC_S_FMT, &fmt) < 0) {
        std::cerr << "V4L2: MJPEG not supported at "
                  << impl_->cfg.width << "x" << impl_->cfg.height
                  << " on " << impl_->cfg.device << ", trying default" << std::endl;
        fmt.fmt.pix.pixelformat = 0;
        if (ioctl(impl_->fd, VIDIOC_S_FMT, &fmt) < 0) {
            std::cerr << "V4L2: cannot set any format on " << impl_->cfg.device << std::endl;
            close(); return false;
        }
    }

    // ── 设置 JPEG 质量 ──
    v4l2_control ctrl{};
    ctrl.id = V4L2_CID_JPEG_COMPRESSION_QUALITY;
    ctrl.value = impl_->cfg.jpeg_quality;
    if (ioctl(impl_->fd, VIDIOC_S_CTRL, &ctrl) < 0) {
        std::cerr << "V4L2: cannot set JPEG quality on "
                  << impl_->cfg.device << " (ignored)" << std::endl;
    }

    // ── 请求缓冲区 ──
    v4l2_requestbuffers req{};
    req.type   = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    req.memory = V4L2_MEMORY_MMAP;
    req.count  = BUF_COUNT;

    if (ioctl(impl_->fd, VIDIOC_REQBUFS, &req) < 0) {
        std::cerr << "V4L2: REQBUFS failed on " << impl_->cfg.device
                  << ": " << std::strerror(errno) << std::endl;
        close(); return false;
    }

    if (req.count < 2) {
        std::cerr << "V4L2: insufficient buffers (" << req.count
                  << ") on " << impl_->cfg.device << std::endl;
        close(); return false;
    }

    impl_->nbufs = req.count;

    // ── mmap ──
    for (unsigned int i = 0; i < req.count; i++) {
        v4l2_buffer buf{};
        buf.type   = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory = V4L2_MEMORY_MMAP;
        buf.index  = i;

        if (ioctl(impl_->fd, VIDIOC_QUERYBUF, &buf) < 0) {
            std::cerr << "V4L2: QUERYBUF " << i << " failed on "
                      << impl_->cfg.device << std::endl;
            close(); return false;
        }

        impl_->buffers[i].length = buf.length;
        impl_->buffers[i].start = mmap(nullptr, buf.length,
                                       PROT_READ | PROT_WRITE,
                                       MAP_SHARED, impl_->fd, buf.m.offset);
        if (impl_->buffers[i].start == MAP_FAILED) {
            std::cerr << "V4L2: mmap " << i << " failed on "
                      << impl_->cfg.device << std::endl;
            close(); return false;
        }
    }

    // ── 入队 ──
    for (unsigned int i = 0; i < req.count; i++) {
        v4l2_buffer buf{};
        buf.type   = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory = V4L2_MEMORY_MMAP;
        buf.index  = i;

        if (ioctl(impl_->fd, VIDIOC_QBUF, &buf) < 0) {
            std::cerr << "V4L2: QBUF " << i << " failed on "
                      << impl_->cfg.device << std::endl;
            close(); return false;
        }
    }

    // ── 启动流 ──
    v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (ioctl(impl_->fd, VIDIOC_STREAMON, &type) < 0) {
        std::cerr << "V4L2: STREAMON failed on " << impl_->cfg.device
                  << ": " << std::strerror(errno) << std::endl;
        close(); return false;
    }

    std::cout << "V4L2: " << impl_->cfg.device
              << " " << fmt.fmt.pix.width << "x" << fmt.fmt.pix.height
              << " jpeg_q=" << impl_->cfg.jpeg_quality
              << " bufs=" << req.count << std::endl;
    return true;
}

void CameraCapture::close() {
    if (impl_->fd >= 0) {
        v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        ioctl(impl_->fd, VIDIOC_STREAMOFF, &type);

        for (int i = 0; i < impl_->nbufs; i++) {
            if (impl_->buffers[i].start != MAP_FAILED && impl_->buffers[i].start != nullptr) {
                munmap(impl_->buffers[i].start, impl_->buffers[i].length);
                impl_->buffers[i].start = nullptr;
            }
        }
        impl_->nbufs = 0;

        ::close(impl_->fd);
        impl_->fd = -1;
    }
}

bool CameraCapture::is_open() const { return impl_->fd >= 0; }

std::vector<uint8_t> CameraCapture::grab() {
    v4l2_buffer buf{};
    buf.type   = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;

    if (ioctl(impl_->fd, VIDIOC_DQBUF, &buf) < 0) {
        if (errno == EAGAIN) return {};
        std::cerr << "V4L2: DQBUF failed on " << impl_->cfg.device
                  << ": " << std::strerror(errno) << std::endl;
        return {};
    }

    std::vector<uint8_t> jpeg(buf.bytesused);
    std::memcpy(jpeg.data(), impl_->buffers[buf.index].start, buf.bytesused);

    if (ioctl(impl_->fd, VIDIOC_QBUF, &buf) < 0) {
        std::cerr << "V4L2: QBUF(re-enqueue) failed on "
                  << impl_->cfg.device << ": " << std::strerror(errno) << std::endl;
    }

    return jpeg;
}
