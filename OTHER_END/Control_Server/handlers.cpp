#include "handlers.h"
#include <chrono>
#include <cstdarg>
#include <ctime>
#include <cstdio>

static uint64_t now_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

static void log_ts(const char* fmt, ...) {
    auto now = std::time(nullptr);
    char time_buf[32];
    std::strftime(time_buf, sizeof(time_buf), "%H:%M:%S", std::localtime(&now));
    printf("[%s] ", time_buf);
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);
    printf("\n");
    fflush(stdout);
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
        log_ts("[phone] ctrl → robot, room=%s", room->id.c_str());
    }
    else if (type == "ping") {
        room->last_ctrl_ts = now_ms();
    }
    else if (type == "loc_cfg") {
        room->forward_robot(msg);
        log_ts("[phone] loc_cfg → robot, room=%s", room->id.c_str());
    }
}

// ═══════════════════════════════════════
//  小车消息处理
// ═══════════════════════════════════════

void handle_robot_msg(std::shared_ptr<Room> room, const json& msg) {
    if (!msg.contains("type")) return;
    std::string type = msg["type"];

    if (type == "tele") {
        json out = msg;
        out["ts"] = now_ms();
        room->broadcast_phones(out);
        log_ts("[robot] tele → %zu phones, room=%s", room->phone_count(), room->id.c_str());
    }
    else if (type == "loc") {
        json out = msg;
        out["ts"] = now_ms();
        room->broadcast_phones(out);
        log_ts("[robot] loc → %zu phones, room=%s", room->phone_count(), room->id.c_str());
    }
}

// ═══════════════════════════════════════
//  连接处理
// ═══════════════════════════════════════

void on_phone_connect(std::shared_ptr<Room> room, const std::string& peer_id,
                      const std::string& room_id) {
    log_ts("[phone] %s joined room %s (%zu phones)", peer_id.c_str(), room_id.c_str(), room->phone_count());
}

void on_robot_connect(const std::string& room_id) {
    log_ts("[robot] joined room %s", room_id.c_str());
}

void on_phone_disconnect(std::shared_ptr<Room> room, const std::string& peer_id) {
    room->remove_phone(peer_id);
    json notify = {{"type","sys"},{"code",1005},{"peerId",peer_id},
                   {"msg","设备 " + peer_id + " 已离开"}};
    room->broadcast_phones(notify);
    log_ts("[phone] %s left room %s (%zu phones)", peer_id.c_str(), room->id.c_str(), room->phone_count());
}

void on_robot_disconnect(std::shared_ptr<Room> room) {
    json notify = {{"type","sys"},{"code",1002},{"msg","小车已断开"}};
    room->broadcast_phones(notify);
    room->close_all();
    std::lock_guard<std::mutex> lk(g_rooms_mtx);
    g_rooms.erase(room->id);
    log_ts("[robot] disconnected, room %s closed", room->id.c_str());
}
