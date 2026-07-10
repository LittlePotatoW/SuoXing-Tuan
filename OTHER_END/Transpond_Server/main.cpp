#include <iostream>
#include <memory>
#include <thread>
#include <chrono>
#include <cstring>
#include "handlers.h"

using namespace std::chrono_literals;

int main(int argc, char* argv[]) {
    int port = 8001;
    size_t max_loc = 2000;
    size_t max_sensor = 200;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--port") && i+1 < argc) port = std::stoi(argv[++i]);
        else if (!strcmp(argv[i], "--max-loc") && i+1 < argc) max_loc = std::stoul(argv[++i]);
        else if (!strcmp(argv[i], "--max-sensor") && i+1 < argc) max_sensor = std::stoul(argv[++i]);
    }

    auto state = std::make_shared<AppState>(max_loc, max_sensor);
    httplib::Server svr;

    // ── POST ──
    svr.Post("/location", [state](const httplib::Request& req, httplib::Response& res) {
        handle_post_location(req, res, *state);
    });
    svr.Post("/frames", [state](const httplib::Request& req, httplib::Response& res) {
        handle_post_frames(req, res, *state);
    });
    svr.Post("/debug", [state](const httplib::Request& req, httplib::Response& res) {
        handle_post_debug(req, res, *state);
    });

    // ── GET ──
    svr.Get("/status", [state](const httplib::Request& req, httplib::Response& res) {
        handle_get_status(req, res, *state);
    });
    svr.Get("/location", [state](const httplib::Request& req, httplib::Response& res) {
        handle_get_location(req, res, *state);
    });
    svr.Get("/sensor", [state](const httplib::Request& req, httplib::Response& res) {
        handle_get_sensor(req, res, *state);
    });

    // ── WebSocket /stream ──
    svr.Get("/stream", [state](const httplib::Request& req, httplib::Response& res) {
        std::string mode = req.get_param_value("mode");  // "all", "location", "sensor"
        bool send_all = mode.empty() || mode == "all";
        bool send_loc = send_all || mode == "location";
        bool send_sensor = send_all || mode == "sensor";

        res.set_header("Connection", "Upgrade");
        res.set_header("Upgrade", "websocket");
        res.status = 101; // Switching Protocols

        // 用 httplib 的 WebSocket 连接
        // httplib 在 response 设置 Upgrade 后自动升级
    });

    std::cout << "TranspondServer starting on 0.0.0.0:" << port << std::endl;
    std::cout << "  max-loc=" << max_loc << " max-sensor=" << max_sensor << std::endl;

    svr.listen("0.0.0.0", port);
    return 0;
}
