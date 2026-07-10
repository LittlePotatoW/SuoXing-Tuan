#include <iostream>
#include <memory>
#include <thread>
#include <chrono>
#include <cstring>
#include <ctime>
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
    svr.WebSocket("/stream", [state](const httplib::Request& req, httplib::ws::WebSocket& ws) {
        std::string mode = req.get_param_value("mode");
        bool send_loc = mode.empty() || mode == "all" || mode == "location";
        bool send_sensor = mode.empty() || mode == "all" || mode == "sensor";

        auto now = std::time(nullptr);
        char time_buf[32];
        std::strftime(time_buf, sizeof(time_buf), "%H:%M:%S", std::localtime(&now));
        printf("[%s] WS  client connected, mode=%s\n", time_buf,
               mode.empty() ? "all" : mode.c_str());

        uint64_t last_loc_ts = 0;
        uint64_t last_sensor_ts = 0;

        while (ws.is_open()) {
            std::string loc_json, sen_json;

            {
                std::lock_guard<std::mutex> lk(state->mtx);

                if (send_loc) {
                    auto items = state->loc_store.query(last_loc_ts, 0);
                    if (!items.empty()) {
                        json arr = json::array();
                        for (auto p : items) {
                            arr.push_back(*p);
                            if (p->timestamp_ns > last_loc_ts)
                                last_loc_ts = p->timestamp_ns;
                        }
                        json msg;
                        msg["type"] = "location";
                        msg["count"] = arr.size();
                        msg["frames"] = std::move(arr);
                        loc_json = msg.dump();
                    }
                }

                if (send_sensor) {
                    auto items = state->sensor_store.query(last_sensor_ts, 0);
                    if (!items.empty()) {
                        json arr = json::array();
                        for (auto p : items) {
                            arr.push_back(*p);
                            if (p->timestamp_ns > last_sensor_ts)
                                last_sensor_ts = p->timestamp_ns;
                        }
                        json msg;
                        msg["type"] = "sensor";
                        msg["count"] = arr.size();
                        msg["frames"] = std::move(arr);
                        sen_json = msg.dump();
                    }
                }
            }

            if (!loc_json.empty()) ws.send(loc_json);
            if (!sen_json.empty()) ws.send(sen_json);

            std::this_thread::sleep_for(200ms);
        }

        now = std::time(nullptr);
        std::strftime(time_buf, sizeof(time_buf), "%H:%M:%S", std::localtime(&now));
        printf("[%s] WS  client disconnected\n", time_buf);
    });

    std::cout << "TranspondServer starting on 0.0.0.0:" << port << std::endl;
    std::cout << "  max-loc=" << max_loc << " max-sensor=" << max_sensor << std::endl;

    svr.listen("0.0.0.0", port);
    return 0;
}
