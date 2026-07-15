cmake_minimum_required(VERSION 3.20)
project(transpond-server VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 使用本地第三方头文件（避免 GitHub 下载）
set(THIRD_PARTY_DIR "${CMAKE_SOURCE_DIR}/third_party")

add_library(httplib INTERFACE)
target_include_directories(httplib INTERFACE "${THIRD_PARTY_DIR}/cpp-httplib")

add_library(nlohmann_json INTERFACE)
target_include_directories(nlohmann_json INTERFACE "${THIRD_PARTY_DIR}")
# #include <nlohmann/json.hpp> → third_party/nlohmann/json.hpp

add_executable(transpond-server main.cpp handlers.cpp)
target_link_libraries(transpond-server PRIVATE httplib nlohmann_json)
