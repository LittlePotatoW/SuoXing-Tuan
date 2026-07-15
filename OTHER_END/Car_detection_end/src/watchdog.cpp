#include "watchdog.h"

Watchdog::Watchdog(int timeout_ms)
    : timeout_ms_(timeout_ms)
    , last_feed_(std::chrono::steady_clock::now()) {}

void Watchdog::feed() {
    last_feed_ = std::chrono::steady_clock::now();
}

bool Watchdog::ok() const {
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        now - last_feed_).count();
    return elapsed < timeout_ms_;
}
