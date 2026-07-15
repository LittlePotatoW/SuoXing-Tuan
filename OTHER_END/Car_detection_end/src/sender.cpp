#include "sender.h"

#include <iostream>
#include "httplib.h"

HttpSender::HttpSender(const std::string& host, int port)
    : base_url_("http://" + host + ":" + std::to_string(port)) {}

HttpResponse HttpSender::post(const std::string& path, const json& body) {
    HttpResponse resp;

    // cpp-httplib 用法
    httplib::Client cli(base_url_);
    cli.set_connection_timeout(3, 0);   // 3 秒连接超时
    cli.set_read_timeout(5, 0);         // 5 秒读取超时

    std::string payload = body.dump();
    auto res = cli.Post(path.c_str(), payload, "application/json");

    if (res) {
        resp.status_code = res->status;
        resp.body = res->body;
    } else {
        resp.status_code = 0;
        resp.body = httplib::to_string(res.error());
    }
    return resp;
}
