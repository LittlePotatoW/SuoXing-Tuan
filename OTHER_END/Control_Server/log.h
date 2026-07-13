#pragma once
#include <deque>
#include <string>
#include <mutex>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

// 环形日志 (server 端 printf → 日志缓冲区)
class RingLog {
    std::deque<std::string> buf_;
    size_t max_;
    mutable std::mutex mtx_;
public:
    explicit RingLog(size_t max_lines = 100) : max_(max_lines) {}

    void append(const std::string& line) {
        std::lock_guard<std::mutex> lk(mtx_);
        buf_.push_back(line);
        while (buf_.size() > max_) buf_.pop_front();
    }

    json to_json() const {
        json arr = json::array();
        std::lock_guard<std::mutex> lk(mtx_);
        for (auto& s : buf_) arr.push_back(s);
        return arr;
    }
};

// 全局单例
extern RingLog g_log;
