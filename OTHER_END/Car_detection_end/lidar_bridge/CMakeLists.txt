cmake_minimum_required(VERSION 3.14)
project(LidarBridge LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(lidar_stdout lidar_stdout.cpp)

# Livox SDK (Jetson 上编译时指定路径)
if(DEFINED LIVOX_SDK_DIR)
    target_include_directories(lidar_stdout PRIVATE ${LIVOX_SDK_DIR}/include)
    target_link_directories(lidar_stdout PRIVATE ${LIVOX_SDK_DIR}/lib)
    target_link_libraries(lidar_stdout PRIVATE livox_sdk_static pthread dl)
endif()

target_link_libraries(lidar_stdout PRIVATE pthread)
