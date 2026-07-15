#pragma once
#include <string>
#include <unordered_map>
#include <memory>
#include <mutex>
#include <atomic>
#include <nlohmann/json.hpp>
#include <httplib.h>
#include "ring_store.h"

using json = nlohmann::json;

struct Room {
    std::string id;
    std::unordered_map<std::string, httplib::ws::WebSocket*> phones;
    httplib::ws::WebSocket* robot_ws = nullptr;
    std::atomic<uint64_t> last_ctrl_ts{0};
    int max_phones = 10;
    RingStore<json> tele_store{200};
    RingStore<json> loc_store{200};
    std::mutex mtx;

    explicit Room(std::string room_id, int max_p = 10)
        : id(std::move(room_id)), max_phones(max_p) {}

    std::string add_phone(httplib::ws::WebSocket* ws);
    bool set_robot(httplib::ws::WebSocket* ws);
    bool has_robot() { std::lock_guard<std::mutex> lk(mtx); return robot_ws != nullptr; }
    void broadcast_phones(const json& msg, const std::string& exclude_peer = "");
    void forward_robot(const json& msg);
    void remove_phone(const std::string& peer_id);
    size_t phone_count();
    void close_all();
};

// 全局房间表
extern std::unordered_map<std::string, std::shared_ptr<Room>> g_rooms;
extern std::mutex g_rooms_mtx;

std::shared_ptr<Room> get_or_create_room(const std::string& room_id);
