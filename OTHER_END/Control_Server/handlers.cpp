#include "handlers.h"
#include <chrono>
#include <iostream>

static uint64_t now_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

// ═══════════════════════════════════════
//  手机消息处理
// ═══════════════════════════════════════

void handle_phone_msg(std::shared_ptr<Room> room, const std::string& /*peer_id*/,
                      const json& msg) {
    if (!msg.contains("type")) return;
    std::string type = msg["type"];

    if (type == "ctrl") {
        room->last_ctrl_ts = now_ms();
        room->forward_robot(msg);
    }
    else if (type == "ping") {
        room->last_ctrl_ts = now_ms();
    }
    else if (type == "loc_cfg") {
        room->forward_robot(msg);
    }
}

// ═══════════════════════════════════════
//  小车消息处理
// ═══════════════════════════════════════

void handle_robot_msg(std::shared_ptr<Room> room, const json& msg) {
    if (!msg.contains("type")) return;
    std::string type = msg["type"];

    if (type == "tele" || type == "loc") {
        json out = msg;
        out["ts"] = now_ms();
        room->broadcast_phones(out);
    }
}

// ═══════════════════════════════════════
//  连接处理
// ═══════════════════════════════════════

void on_phone_connect(std::shared_ptr<Room> room, const std::string& peer_id,
                      const std::string& room_id) {
    std::cout << "[phone] " << peer_id << " joined room " << room_id
              << " (" << room->phone_count() << " phones)" << std::endl;
}

void on_robot_connect(const std::string& room_id) {
    std::cout << "[robot] joined room " << room_id << std::endl;
}

void on_phone_disconnect(std::shared_ptr<Room> room, const std::string& peer_id) {
    room->remove_phone(peer_id);
    json notify = {{"type","sys"},{"code",1005},{"peerId",peer_id},
                   {"msg","设备 " + peer_id + " 已离开"}};
    room->broadcast_phones(notify);
    std::cout << "[phone] " << peer_id << " left (" << room->phone_count()
              << " phones)" << std::endl;
}

void on_robot_disconnect(std::shared_ptr<Room> room) {
    json notify = {{"type","sys"},{"code",1002},{"msg","小车已断开"}};
    room->broadcast_phones(notify);
    room->close_all();
    std::lock_guard<std::mutex> lk(g_rooms_mtx);
    g_rooms.erase(room->id);
    std::cout << "[robot] disconnected, room " << room->id << " closed" << std::endl;
}
