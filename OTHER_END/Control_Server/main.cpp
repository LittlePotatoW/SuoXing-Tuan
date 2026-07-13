// ============================================================
// OTHER_END/Control_Server/main.cpp
// WebSocket 中转服务器 — 手机 ↔ 小车 实时消息转发
// ============================================================

#include <iostream>
#include <cstring>
#include <chrono>
#include <thread>
#include "handlers.h"
#include <httplib.h>

using namespace std::chrono_literals;

int main(int argc, char* argv[]) {
    int port = 8080;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--port") && i + 1 < argc)
            port = std::stoi(argv[++i]);
    }

    httplib::Server svr;

    // CORS
    svr.set_pre_routing_handler([](const httplib::Request& req, httplib::Response& res) {
        res.set_header("Access-Control-Allow-Origin", "*");
        if (req.method == "OPTIONS") { res.status = 204; return httplib::Server::HandlerResponse::Handled; }
        return httplib::Server::HandlerResponse::Unhandled;
    });

    // HTTP health
    svr.Get("/status", [](const httplib::Request&, httplib::Response& res) {
        std::lock_guard<std::mutex> lk(g_rooms_mtx);
        json j = {{"rooms", g_rooms.size()}, {"status", "ok"}};
        res.set_content(j.dump(), "application/json");
    });

    // ═══════════════════════════════════════
    //  WS /phone?room=<id> — 手机连接
    // ═══════════════════════════════════════
    svr.WebSocket("/phone", [](const httplib::Request& req, httplib::ws::WebSocket& ws) {
        std::string room_id = req.get_param_value("room");
        if (room_id.empty()) return;
        auto room = get_or_create_room(room_id);
        std::string peer_id = room->add_phone(&ws);
        if (peer_id.empty()) {
            json m = {{"type","sys"},{"code",1000},{"msg","房间已满"}};
            ws.send(m.dump());
            return;
        }
        // 通知本机
        json hi = {{"type","sys"},{"code",1001},{"peerId",peer_id},
                   {"msg","已加入房间 " + room_id + ", 当前 " +
                    std::to_string(room->phone_count()) + " 台设备在线"}};
        ws.send(hi.dump());
        // 通知房间内其他手机
        json nf = {{"type","sys"},{"code",1004},{"peerId",peer_id},{"msg","新设备加入"}};
        room->broadcast_phones(nf, peer_id);
        on_phone_connect(room, peer_id, room_id);

        std::string data;
        while (ws.is_open()) {
            auto r = ws.read(data);
            if (r == httplib::ws::ReadResult::Fail) break;
            try {
                json msg = json::parse(data);
                handle_phone_msg(room, peer_id, msg);
            } catch (...) {}
        }
        on_phone_disconnect(room, peer_id);
    });

    // ═══════════════════════════════════════
    //  WS /robot?room=<id> — 小车连接
    // ═══════════════════════════════════════
    svr.WebSocket("/robot", [](const httplib::Request& req, httplib::ws::WebSocket& ws) {
        std::string room_id = req.get_param_value("room");
        if (room_id.empty()) return;
        auto room = get_or_create_room(room_id);
        if (!room->set_robot(&ws)) {
            json m = {{"type","sys"},{"code",1000},{"msg","房间已有小车"}};
            ws.send(m.dump());
            return;
        }
        json ok = {{"type","sys"},{"code",1001},{"msg","配对成功"}};
        ws.send(ok.dump());
        on_robot_connect(room_id);

        std::string data;
        while (ws.is_open()) {
            auto r = ws.read(data);
            if (r == httplib::ws::ReadResult::Fail) break;
            try {
                json msg = json::parse(data);
                handle_robot_msg(room, msg);
            } catch (...) {}
        }
        on_robot_disconnect(room);
    });

    // ── 看门狗 ──
    std::thread watchdog([]() { while (true) std::this_thread::sleep_for(50ms); });
    watchdog.detach();

    std::cout << "Control Server on 0.0.0.0:" << port << std::endl;
    std::cout << "  ws://host:" << port << "/phone?room=<id>" << std::endl;
    std::cout << "  ws://host:" << port << "/robot?room=<id>" << std::endl;

    svr.listen("0.0.0.0", port);
    return 0;
}
