#include "packet.h"

#include <cmath>
#include <string>

// base64 编码 (简易实现, 不依赖外部库)
static const char B64_TABLE[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static std::string base64_encode(const std::vector<uint8_t>& data) {
    std::string out;
    out.reserve(((data.size() + 2) / 3) * 4);
    for (size_t i = 0; i < data.size(); i += 3) {
        uint32_t n = static_cast<uint32_t>(data[i]) << 16;
        if (i + 1 < data.size()) n |= static_cast<uint32_t>(data[i + 1]) << 8;
        if (i + 2 < data.size()) n |= static_cast<uint32_t>(data[i + 2]);
        out.push_back(B64_TABLE[(n >> 18) & 0x3F]);
        out.push_back(B64_TABLE[(n >> 12) & 0x3F]);
        if (i + 1 < data.size()) out.push_back(B64_TABLE[(n >> 6) & 0x3F]);
        else                    out.push_back('=');
        if (i + 2 < data.size()) out.push_back(B64_TABLE[n & 0x3F]);
        else                    out.push_back('=');
    }
    return out;
}

// ── 定位包: 匹配 Transpond_Server POST /location ──
json build_location_packet(
    double velocity, double steering_angle,
    double wheel_base, uint64_t timestamp_ns)
{
    return {
        {"timestamp_ns", timestamp_ns},
        {"camera", json::array({{
            {"camera_pose", {
                {"position", {{"x", 0.0}, {"y", 0.0}, {"z", 1.0}}},
                {"rotation", {{"qw", 0.7071}, {"qx", 0.0}, {"qy", 0.7071}, {"qz", 0.0}}},
            }}
        }})},
        {"car", {
            {"kinematics", {
                {"velocity", velocity},
                {"steering_angle", steering_angle},
                {"wheel_base", wheel_base},
            }}
        }},
    };
}

// ── 检测包: 匹配 Transpond_Server POST /frames (批量格式) ──
json build_detection_packet(
    const std::string& frame_id, uint64_t timestamp_ns,
    const std::vector<float>& points, int point_count,
    const std::vector<uint8_t>& jpeg, int width, int height,
    const Pose& car_pose, const Pose& camera_pose_in_body,
    double velocity, double steering_angle, double wheel_base)
{
    return {
        {"count", 1},
        {"frames", json::array({{
            {"frame_id", frame_id},
            {"timestamp_ns", timestamp_ns},
            {"point_cloud", {
                {"points", points},
                {"point_count", point_count},
            }},
            {"camera_views", json::array({{
                {"image_data", base64_encode(jpeg)},
                {"width", width},
                {"height", height},
                {"camera_pose", {
                    {"position", {{"x", camera_pose_in_body.px},
                                  {"y", camera_pose_in_body.py},
                                  {"z", camera_pose_in_body.pz}}},
                    {"rotation", {{"qw", camera_pose_in_body.qw},
                                  {"qx", camera_pose_in_body.qx},
                                  {"qy", camera_pose_in_body.qy},
                                  {"qz", camera_pose_in_body.qz}}},
                }},
            }})},
            {"car_position", {
                {"pose", {
                    {"position", {{"x", car_pose.px}, {"y", car_pose.py}, {"z", car_pose.pz}}},
                    {"rotation", {{"qw", car_pose.qw}, {"qx", car_pose.qx},
                                  {"qy", car_pose.qy}, {"qz", car_pose.qz}}},
                }},
                {"timestamp_ns", timestamp_ns},
            }},
            {"kinematics", {
                {"velocity", velocity},
                {"steering_angle", steering_angle},
                {"wheel_base", wheel_base},
                {"timestamp_ns", timestamp_ns},
            }},
        }})},
    };
}
