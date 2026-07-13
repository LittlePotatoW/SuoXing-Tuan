cmake_minimum_required(VERSION 3.14)
project(ControlServer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O2")

# third-party headers
include_directories(${CMAKE_SOURCE_DIR}/third_party)
include_directories(${CMAKE_SOURCE_DIR}/third_party/cpp-httplib)

add_executable(control-server
    main.cpp
    room.cpp
    handlers.cpp
)

target_link_libraries(control-server PRIVATE pthread)
