cmake_minimum_required(VERSION 3.20)
project(transpond-server VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

# cpp-httplib: single-header HTTP/HTTPS/WebSocket
FetchContent_Declare(httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.18.5
)
FetchContent_MakeAvailable(httplib)

# nlohmann/json: single-header JSON
FetchContent_Declare(json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)
FetchContent_MakeAvailable(json)

add_executable(transpond-server main.cpp handlers.cpp)
target_link_libraries(transpond-server PRIVATE httplib::httplib nlohmann_json::nlohmann_json)
