#include "handlers.h"
#include <ctime>
#include <cstdio>

// ── POST /location ──

void handle_post_location(const httplib::Request& req, httplib::Response& res, AppState& state) {
    auto now = std::time(nullptr);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%H:%M:%S", std::localtime(&now));
    printf("[%s] POST /location  body=%zu bytes\n", buf, req.body.size());

    try {
        auto j = json::parse(req.body);
        LocationData loc = j.get<LocationData>();
        {
            std::lock_guard<std::mutex> lk(state.mtx);
            state.loc_store.push(std::move(loc));
        }
        res.set_content(json{{"status","ok"},{"cached",state.loc_store.count()}}.dump(), "application/json");
    } catch (...) {
        res.status = 400;
        res.set_content(R"({"status":"error","message":"invalid json"})", "application/json");
    }
}

// ── POST /frames ──

void handle_post_frames(const httplib::Request& req, httplib::Response& res, AppState& state) {
    auto now = std::time(nullptr);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%H:%M:%S", std::localtime(&now));
    printf("[%s] POST /frames  body=%zu bytes\n", buf, req.body.size());

    try {
        auto j = json::parse(req.body);
        SensorBatch batch = j.get<SensorBatch>();
        {
            std::lock_guard<std::mutex> lk(state.mtx);
            for (auto& f : batch.frames)
                state.sensor_store.push(std::move(f));
        }
        res.set_content(json{{"status","ok"},{"received",batch.frames.size()},{"cached",state.sensor_store.count()}}.dump(), "application/json");
    } catch (...) {
        res.status = 400;
        res.set_content(R"({"status":"error","message":"invalid json"})", "application/json");
    }
}

// ── POST /debug ──

void handle_post_debug(const httplib::Request& req, httplib::Response& res, AppState& state) {
    std::string action;
    try {
        auto j = json::parse(req.body);
        action = j.value("action", "");
    } catch (...) {}

    auto now = std::time(nullptr);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%H:%M:%S", std::localtime(&now));
    printf("[%s] POST /debug  action=%s\n", buf, action.empty() ? "status" : action.c_str());

    if (action == "clear") {
        std::lock_guard<std::mutex> lk(state.mtx);
        state.loc_store.clear();
        state.sensor_store.clear();
        res.set_content(R"({"status":"ok","action":"clear"})", "application/json");
    } else {
        size_t lc, sc;
        {
            std::lock_guard<std::mutex> lk(state.mtx);
            lc = state.loc_store.count();
            sc = state.sensor_store.count();
        }
        res.set_content(json{{"status","ok"},{"location_cached",lc},{"sensor_cached",sc}}.dump(), "application/json");
    }
}

// ── GET /status ──

void handle_get_status(const httplib::Request&, httplib::Response& res, AppState& state) {
    auto now = std::time(nullptr);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%H:%M:%S", std::localtime(&now));
    printf("[%s] GET  /status\n", buf);

    size_t lc, sc;
    {
        std::lock_guard<std::mutex> lk(state.mtx);
        lc = state.loc_store.count();
        sc = state.sensor_store.count();
    }
    res.set_content(json{{"status","ok"},{"location_cached",lc},{"sensor_cached",sc}}.dump(), "application/json");
}

// ── 辅助: 解析查询参数 ──

static uint64_t param_after(const httplib::Request& req) {
    if (req.has_param("after")) return std::stoull(req.get_param_value("after"));
    return 0;
}
static size_t param_limit(const httplib::Request& req) {
    if (req.has_param("limit")) return std::stoul(req.get_param_value("limit"));
    return 0;
}

// ── GET /location ──

void handle_get_location(const httplib::Request& req, httplib::Response& res, AppState& state) {
    auto after = param_after(req);
    auto limit = param_limit(req);

    auto now = std::time(nullptr);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%H:%M:%S", std::localtime(&now));
    printf("[%s] GET  /location  after=%llu limit=%zu\n", buf,
           (unsigned long long)after, limit);
    json frames = json::array();
    {
        std::lock_guard<std::mutex> lk(state.mtx);
        auto items = state.loc_store.query(after, limit);
        for (auto p : items) frames.push_back(*p);
    }
    res.set_content(json{{"status","ok"},{"count",frames.size()},{"frames",frames}}.dump(), "application/json");
}

// ── GET /sensor ──

void handle_get_sensor(const httplib::Request& req, httplib::Response& res, AppState& state) {
    auto after = param_after(req);
    auto limit = param_limit(req);

    auto now = std::time(nullptr);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%H:%M:%S", std::localtime(&now));
    printf("[%s] GET  /sensor   after=%llu limit=%zu\n", buf,
           (unsigned long long)after, limit);
    json frames = json::array();
    {
        std::lock_guard<std::mutex> lk(state.mtx);
        auto items = state.sensor_store.query(after, limit);
        for (auto p : items) frames.push_back(*p);
    }
    res.set_content(json{{"status","ok"},{"count",frames.size()},{"frames",frames}}.dump(), "application/json");
}
