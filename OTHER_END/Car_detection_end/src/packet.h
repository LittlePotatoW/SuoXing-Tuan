#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include "json.hpp"

using json = nlohmann::json;

struct Pose {
    double px, py, pz;
    double qw, qx, qy, qz;
};

struct CameraFrame {
    std::vector<uint8_t> jpeg;
    int width  = 640;
    int height = 480;
    Pose pose;
};

json build_location_packet(
    double velocity, double steering_angle,
    double wheel_base, uint64_t timestamp_ns);

json build_detection_packet(
    const std::string& frame_id, uint64_t timestamp_ns,
    const std::vector<float>& points, int point_count,
    const std::vector<CameraFrame>& cameras,
    const Pose& car_pose,
    double velocity, double steering_angle, double wheel_base);
