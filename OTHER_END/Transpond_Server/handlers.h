#pragma once
#include <memory>
#include <mutex>
#include <httplib.h>
#include "store.h"

struct AppState {
    RingStore<LocationData> loc_store;
    RingStore<SensorFrame> sensor_store;
    std::mutex mtx;  // 保护两个 store

    AppState(size_t max_loc, size_t max_sensor)
        : loc_store(max_loc), sensor_store(max_sensor) {}
};

// Handler 函数声明
void handle_post_location(const httplib::Request& req, httplib::Response& res, AppState& state);
void handle_post_frames(const httplib::Request& req, httplib::Response& res, AppState& state);
void handle_post_debug(const httplib::Request& req, httplib::Response& res, AppState& state);
void handle_get_status(const httplib::Request& req, httplib::Response& res, AppState& state);
void handle_get_location(const httplib::Request& req, httplib::Response& res, AppState& state);
void handle_get_sensor(const httplib::Request& req, httplib::Response& res, AppState& state);
