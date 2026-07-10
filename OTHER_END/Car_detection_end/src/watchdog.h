#pragma once
#include <chrono>
#include <atomic>

class Watchdog {
public:
    explicit Watchdog(int timeout_ms = 10000);

    void feed();                        // 喂狗 (线程定期调用)
    bool ok() const;                    // 是否超时
    int timeout_ms() const { return timeout_ms_; }

private:
    int timeout_ms_;
    std::chrono::steady_clock::time_point last_feed_;
};
