#include "room.h"
#include <random>
#include <sstream>
#include <iostream>

std::unordered_map<std::string, std::shared_ptr<Room>> g_rooms;
std::mutex g_rooms_mtx;

// ── peerId 生成 ──
static std::string gen_peer_id() {
    static const char hex[] = "0123456789ABCDEF";
    static std::mt19937 rng(std::random_device{}());
    static std::uniform_int_distribution<int> dist(0, 15);
    std::string id(4, '0');
    for (int i = 0; i < 4; i++) id[i] = hex[dist(rng)];
    return id;
}

std::shared_ptr<Room> get_or_create_room(const std::string& room_id) {
    std::lock_guard<std::mutex> lk(g_rooms_mtx);
    auto it = g_rooms.find(room_id);
    if (it != g_rooms.end()) return it->second;
    auto room = std::make_shared<Room>(room_id);
    g_rooms[room_id] = room;
    return room;
}

// ── Room 方法 ──

std::string Room::add_phone(httplib::ws::WebSocket* ws) {
    std::lock_guard<std::mutex> lk(mtx);
    if (phones.size() >= (size_t)max_phones) return "";
    std::string pid = gen_peer_id();
    while (phones.count(pid)) pid = gen_peer_id();
    phones[pid] = ws;
    return pid;
}

bool Room::set_robot(httplib::ws::WebSocket* ws) {
    std::lock_guard<std::mutex> lk(mtx);
    if (robot_ws) return false;
    robot_ws = ws;
    return true;
}

void Room::broadcast_phones(const json& msg, const std::string& exclude_peer) {
    std::lock_guard<std::mutex> lk(mtx);
    std::string payload = msg.dump();
    for (auto& [pid, ws] : phones) {
        if (pid == exclude_peer) continue;
        if (ws->is_open()) ws->send(payload);
    }
}

void Room::forward_robot(const json& msg) {
    std::lock_guard<std::mutex> lk(mtx);
    if (robot_ws && robot_ws->is_open()) {
        robot_ws->send(msg.dump());
    }
}

void Room::remove_phone(const std::string& peer_id) {
    std::lock_guard<std::mutex> lk(mtx);
    phones.erase(peer_id);
}

size_t Room::phone_count() {
    std::lock_guard<std::mutex> lk(mtx);
    return phones.size();
}

void Room::close_all() {
    std::lock_guard<std::mutex> lk(mtx);
    json msg = {{"type","sys"},{"code",1002},{"msg","小车已断开"}};
    std::string payload = msg.dump();
    for (auto& [pid, ws] : phones) {
        if (ws->is_open()) ws->send(payload);
    }
    phones.clear();
    if (robot_ws) robot_ws = nullptr;
}
