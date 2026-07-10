#pragma once
#include <deque>
#include <cstdint>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

// ── 数据模型 ──

struct SensorFrame {
    std::string frame_id;
    uint64_t timestamp_ns = 0;
    json point_cloud;
    std::vector<json> camera_views;
    json car_position;
    json kinematics;
};

struct SensorBatch {
    size_t count = 0;
    std::vector<SensorFrame> frames;
};

// json → SensorFrame (带默认值容错)
inline void from_json(const json& j, SensorFrame& f) {
    f.frame_id = j.value("frame_id", "");
    f.timestamp_ns = j.value("timestamp_ns", 0ULL);
    f.point_cloud = j.value("point_cloud", json::object());
    f.camera_views.clear();
    if (j.contains("camera_views") && j["camera_views"].is_array()) {
        for (auto& cv : j["camera_views"]) f.camera_views.push_back(cv);
    }
    f.car_position = j.value("car_position", json::object());
    f.kinematics = j.value("kinematics", json::object());
}

inline void from_json(const json& j, SensorBatch& b) {
    b.count = j.value("count", 0);
    b.frames.clear();
    if (j.contains("frames") && j["frames"].is_array()) {
        for (auto& f : j["frames"]) b.frames.push_back(f.get<SensorFrame>());
    }
}

// ── 环形缓冲区 ──

template<typename T>
class RingStore {
    std::deque<T> buffer_;
    size_t max_len_;
public:
    explicit RingStore(size_t max_len) : max_len_(max_len) {}

    void push(T item) {
        while (buffer_.size() >= max_len_) buffer_.pop_front();
        buffer_.push_back(std::move(item));
    }
    size_t count() const { return buffer_.size(); }
    void set_max_len(size_t n) { max_len_ = n; while (buffer_.size() > max_len_) buffer_.pop_front(); }
    void clear() { buffer_.clear(); }

    // 查询: after=只返回 ts>after, limit=最多 N 条 (取最新)
    std::vector<const T*> query(uint64_t after, size_t limit) const {
        std::vector<const T*> out;
        for (auto& item : buffer_) {
            if (item.timestamp_ns > after) out.push_back(&item);
        }
        size_t n = limit ? std::min(limit, out.size()) : out.size();
        return {out.end() - n, out.end()};
    }
    // 取全部
    std::vector<const T*> all() const {
        std::vector<const T*> out;
        for (auto& item : buffer_) out.push_back(&item);
        return out;
    }
};

// ── Location 数据 ──

struct LocationData {
    uint64_t timestamp_ns = 0;
    std::vector<json> camera;
    json car;
};

inline void from_json(const json& j, LocationData& l) {
    l.timestamp_ns = j.value("timestamp_ns", 0ULL);
    l.camera.clear();
    if (j.contains("camera") && j["camera"].is_array())
        for (auto& c : j["camera"]) l.camera.push_back(c);
    l.car = j.value("car", json::object());
}

inline void to_json(json& j, const LocationData& l) {
    j["timestamp_ns"] = l.timestamp_ns;
    j["camera"] = l.camera;
    j["car"] = l.car;
}

inline void to_json(json& j, const SensorFrame& f) {
    j["frame_id"] = f.frame_id;
    j["timestamp_ns"] = f.timestamp_ns;
    j["point_cloud"] = f.point_cloud;
    j["camera_views"] = f.camera_views;
    j["car_position"] = f.car_position;
    j["kinematics"] = f.kinematics;
}
