cmake_minimum_required(VERSION 3.10)
project(CarDetectionEnd VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O2")

# ── third-party include ──
include_directories(
    ${CMAKE_SOURCE_DIR}/third_party/cpp-httplib
    ${CMAKE_SOURCE_DIR}/third_party/nlohmann
)

# ── camera: V4L2 (Linux only) ──
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    find_package(PkgConfig)
    pkg_check_modules(V4L2 REQUIRED libv4l2)
    include_directories(${V4L2_INCLUDE_DIRS})
    set(CAMERA_LIBS ${V4L2_LIBRARIES})
else()
    message(WARNING "Non-Linux build: camera module needs V4L2")
    set(CAMERA_LIBS "")
endif()

# ── LiDAR bridge subdirectory ──
add_subdirectory(lidar_bridge)

# ── main executable ──
add_executable(car_detection
    src/main.cpp
    src/camera.cpp
    src/lidar.cpp
    src/packet.cpp
    src/sender.cpp
    src/watchdog.cpp
)

target_link_libraries(car_detection PRIVATE
    pthread
    ${CAMERA_LIBS}
)

# httplib needs pthread + OpenSSL on Linux
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_libraries(car_detection PRIVATE ssl crypto)
endif()
