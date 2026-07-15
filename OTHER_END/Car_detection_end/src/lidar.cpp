#include "lidar.h"

#include <cstring>
#include <iostream>
#include <stdexcept>

#include <unistd.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <signal.h>
#include <poll.h>
#include <cerrno>

// ── 二进制帧格式 (与 lidar_stdout 输出一致) ──
static constexpr int HEADER_SIZE = 17;   // type(1) + ts(8) + len(4) + npts(4)
static constexpr int POINT_SIZE  = 16;   // x(4) + y(4) + z(4) + intensity(4)

struct LidarCapture::Impl {
    Config cfg;
    pid_t pid = -1;
    int pipe_fd = -1;
    bool started = false;
};

LidarCapture::LidarCapture(const Config& cfg)
    : impl_(std::make_unique<Impl>(Impl{cfg})) {}

LidarCapture::~LidarCapture() { stop(); }

bool LidarCapture::start() {
    int pipefd[2];
    if (pipe(pipefd) < 0) {
        std::cerr << "Lidar: pipe failed: " << strerror(errno) << std::endl;
        return false;
    }

    pid_t pid = fork();
    if (pid < 0) {
        std::cerr << "Lidar: fork failed: " << strerror(errno) << std::endl;
        close(pipefd[0]); close(pipefd[1]);
        return false;
    }

    if (pid == 0) {
        // ── child ──
        close(pipefd[0]);                    // 关闭读端
        dup2(pipefd[1], STDOUT_FILENO);      // stdout → 管道写端
        close(pipefd[1]);

        execl(impl_->cfg.binary_path.c_str(),
              impl_->cfg.binary_path.c_str(), nullptr);
        std::cerr << "Lidar: execl failed: " << strerror(errno) << std::endl;
        _exit(1);
    }

    // ── parent ──
    close(pipefd[1]);                        // 关闭写端
    impl_->pipe_fd = pipefd[0];
    impl_->pid = pid;
    impl_->started = true;

    // 非阻塞读
    int flags = fcntl(impl_->pipe_fd, F_GETFL, 0);
    fcntl(impl_->pipe_fd, F_SETFL, flags | O_NONBLOCK);

    std::cout << "Lidar: started (pid=" << pid << ")" << std::endl;
    return true;
}

void LidarCapture::stop() {
    if (impl_->pid > 0) {
        kill(impl_->pid, SIGTERM);
        waitpid(impl_->pid, nullptr, 0);
        impl_->pid = -1;
    }
    if (impl_->pipe_fd >= 0) {
        close(impl_->pipe_fd);
        impl_->pipe_fd = -1;
    }
    impl_->started = false;
}

bool LidarCapture::alive() const {
    if (!impl_->started || impl_->pid <= 0) return false;
    int status;
    pid_t r = waitpid(impl_->pid, &status, WNOHANG);
    return r == 0;  // 0 = still running
}

LidarCapture::Frame LidarCapture::read_frame(int timeout_ms) {
    Frame frame;
    if (impl_->pipe_fd < 0) return frame;

    // 等待数据可读
    pollfd pfd{impl_->pipe_fd, POLLIN, 0};
    int ready = poll(&pfd, 1, timeout_ms);
    if (ready <= 0) return frame;  // 超时

    // 读取帧头
    uint8_t header[HEADER_SIZE];
    ssize_t n = ::read(impl_->pipe_fd, header, HEADER_SIZE);
    if (n != HEADER_SIZE) return frame;

    // 解析帧头: [type:1B][ts:8B][payload_len:4B][num_points:4B]
    uint8_t  type   = header[0];
    if (type != 0x01) return frame;  // 非点云帧

    uint64_t ts     = *reinterpret_cast<uint64_t*>(header + 1);
    uint32_t paylen = *reinterpret_cast<uint32_t*>(header + 9);
    uint32_t npts   = *reinterpret_cast<uint32_t*>(header + 13);

    if (npts > static_cast<uint32_t>(impl_->cfg.max_points)) {
        npts = impl_->cfg.max_points;
    }

    // 读取点云数据
    size_t expected = static_cast<size_t>(npts) * POINT_SIZE;
    if (paylen != expected) return frame;

    std::vector<uint8_t> buf(expected);
    n = ::read(impl_->pipe_fd, buf.data(), expected);
    if (static_cast<size_t>(n) != expected) return frame;

    // 解析点
    frame.timestamp_ns = ts;
    frame.points.reserve(npts);
    const auto* ptr = reinterpret_cast<const float*>(buf.data());
    for (uint32_t i = 0; i < npts; ++i) {
        frame.points.push_back({
            ptr[i * 4 + 0], ptr[i * 4 + 1],
            ptr[i * 4 + 2], ptr[i * 4 + 3],
        });
    }
    return frame;
}
