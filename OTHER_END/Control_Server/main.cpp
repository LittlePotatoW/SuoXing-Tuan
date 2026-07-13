// ============================================================
// OTHER_END/Control_Server/main.cpp
// WebSocket 中转服务器 + 数据缓存 + 日志
// ============================================================

#include <iostream>
#include <sstream>
#include <cstring>
#include <chrono>
#include <thread>
#include "handlers.h"
#include "log.h"
#include <httplib.h>

using namespace std::chrono_literals;

RingLog g_log(100);

// 重定向 std::cout → RingLog
class LogBuf : public std::stringbuf {
    int sync() override { g_log.append(str()); str(""); return 0; }
};

int main(int argc, char* argv[]) {
    int port = 8080;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--port") && i + 1 < argc)
            port = std::stoi(argv[++i]);
    }

    LogBuf lbuf;
    auto* old_buf = std::cout.rdbuf();
    std::cout.rdbuf(&lbuf);

    httplib::Server svr;

    svr.set_pre_routing_handler([](const httplib::Request& req, httplib::Response& res) {
        res.set_header("Access-Control-Allow-Origin", "*");
        if (req.method == "OPTIONS") { res.status = 204; return httplib::Server::HandlerResponse::Handled; }
        return httplib::Server::HandlerResponse::Unhandled;
    });

    // ── HTTP 端点 ──
    svr.Get("/status", [](const httplib::Request&, httplib::Response& res) {
        std::lock_guard<std::mutex> lk(g_rooms_mtx);
        json j = {{"rooms", g_rooms.size()}, {"status", "ok"}};
        res.set_content(j.dump(), "application/json");
    });

    svr.Get("/logs", [](const httplib::Request&, httplib::Response& res) {
        res.set_content(g_log.to_json().dump(), "application/json");
    });

    svr.Get("/replay/status", [](const httplib::Request& req, httplib::Response& res) {
        std::string room_id = req.get_param_value("room");
        std::lock_guard<std::mutex> lk(g_rooms_mtx);
        auto it = g_rooms.find(room_id);
        if (it == g_rooms.end()) {
            res.set_content(R"({"error":"room not found"})", "application/json");
            return;
        }
        auto& r = *it->second;
        std::lock_guard<std::mutex> rlk(r.mtx);
        json j = {{"tele_cached", r.tele_store.count()},
                  {"loc_cached", r.loc_store.count()},
                  {"status", "ok"}};
        res.set_content(j.dump(), "application/json");
    });

    svr.Get("/tele", [](const httplib::Request& req, httplib::Response& res) {
        std::string room_id = req.get_param_value("room");
        size_t limit = req.has_param("limit") ? std::stoul(req.get_param_value("limit")) : 50;
        std::lock_guard<std::mutex> lk(g_rooms_mtx);
        auto it = g_rooms.find(room_id);
        if (it == g_rooms.end()) { res.status = 404; return; }
        auto& r = *it->second;
        std::lock_guard<std::mutex> rlk(r.mtx);
        auto items = r.tele_store.query_json(0, limit);
        json arr = json::array();
        for (auto p : items) arr.push_back(*p);
        json j = {{"status","ok"},{"count",arr.size()},{"frames",arr}};
        res.set_content(j.dump(), "application/json");
    });

    svr.Get("/loc", [](const httplib::Request& req, httplib::Response& res) {
        std::string room_id = req.get_param_value("room");
        size_t limit = req.has_param("limit") ? std::stoul(req.get_param_value("limit")) : 50;
        std::lock_guard<std::mutex> lk(g_rooms_mtx);
        auto it = g_rooms.find(room_id);
        if (it == g_rooms.end()) { res.status = 404; return; }
        auto& r = *it->second;
        std::lock_guard<std::mutex> rlk(r.mtx);
        auto items = r.loc_store.query_json(0, limit);
        json arr = json::array();
        for (auto p : items) arr.push_back(*p);
        json j = {{"status","ok"},{"count",arr.size()},{"frames",arr}};
        res.set_content(j.dump(), "application/json");
    });

    // ── POST /debug ──
    svr.Post("/debug", [](const httplib::Request& req, httplib::Response& res) {
        std::string action;
        try { action = json::parse(req.body).value("action", ""); } catch (...) {}
        if (action == "clear") {
            std::lock_guard<std::mutex> lk(g_rooms_mtx);
            for (auto& [id, room] : g_rooms) {
                std::lock_guard<std::mutex> rlk(room->mtx);
                room->tele_store.clear();
                room->loc_store.clear();
            }
            res.set_content(R"({"status":"ok","action":"clear"})", "application/json");
        } else {
            json j = {{"status","ok"}};
            {
                std::lock_guard<std::mutex> lk(g_rooms_mtx);
                for (auto& [id, room] : g_rooms) {
                    std::lock_guard<std::mutex> rlk(room->mtx);
                    j[id] = {{"tele",room->tele_store.count()},{"loc",room->loc_store.count()}};
                }
            }
            res.set_content(j.dump(), "application/json");
        }
    });

    // ═══════════════════════════════════════
    //  WS /phone
    // ═══════════════════════════════════════
    svr.WebSocket("/phone", [](const httplib::Request& req, httplib::ws::WebSocket& ws) {
        std::string room_id = req.get_param_value("room");
        if (room_id.empty()) return;
        auto room = get_or_create_room(room_id);
        std::string peer_id = room->add_phone(&ws);
        if (peer_id.empty()) {
            json m = {{"type","sys"},{"code",1000},{"msg","房间已满"}};
            ws.send(m.dump()); return;
        }
        json hi = {{"type","sys"},{"code",1001},{"peerId",peer_id},
                   {"msg","已加入房间 " + room_id + ", 当前 " +
                    std::to_string(room->phone_count()) + " 台设备在线"}};
        ws.send(hi.dump());
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
    //  WS /robot
    // ═══════════════════════════════════════
    svr.WebSocket("/robot", [](const httplib::Request& req, httplib::ws::WebSocket& ws) {
        std::string room_id = req.get_param_value("room");
        if (room_id.empty()) return;
        auto room = get_or_create_room(room_id);
        if (!room->set_robot(&ws)) {
            json m = {{"type","sys"},{"code",1000},{"msg","房间已有小车"}};
            ws.send(m.dump()); return;
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
                // 存入环形缓冲区（注入时间戳）
                if (msg.contains("type")) {
                    std::string t = msg["type"];
                    msg["timestamp_ns"] = std::chrono::duration_cast<std::chrono::nanoseconds>(
                        std::chrono::system_clock::now().time_since_epoch()).count();
                    if (t == "tele") room->tele_store.push(msg);
                    else if (t == "loc") room->loc_store.push(msg);
                }
                handle_robot_msg(room, msg);
            } catch (...) {}
        }
        on_robot_disconnect(room);
    });

    std::thread watchdog([]() { while (true) std::this_thread::sleep_for(50ms); });
    watchdog.detach();

    std::cout << "Control Server on 0.0.0.0:" << port << std::endl
              << "  GET /status /logs /tele?room=x&limit=N /loc?room=x&limit=N /replay/status?room=x" << std::endl
              << "  WS /phone?room=x  /robot?room=x" << std::endl;

    svr.listen("0.0.0.0", port);

    std::cout.rdbuf(old_buf);
    return 0;
}
