#pragma once
#include <string>
#include "json.hpp"

using json = nlohmann::json;

struct HttpResponse {
    int status_code = 0;
    std::string body;
    bool ok() const { return status_code >= 200 && status_code < 300; }
};

class HttpSender {
public:
    HttpSender(const std::string& host, int port);
    HttpResponse post(const std::string& path, const json& body);

private:
    std::string base_url_;
};
