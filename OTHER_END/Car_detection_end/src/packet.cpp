#include "packet.h"

#include <cmath>
#include <string>

// base64 编码 (简易实现)
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

// ── 定位包 ──
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

static json camera_view_json(const CameraFrame& cam) {
    return {
        {"image_data", base64_encode(cam.jpeg)},
        {"width", cam.width},
        {"height", cam.height},
        {"camera_pose", {
            {"position", {{"x", cam.pose.px}, {"y", cam.pose.py}, {"z", cam.pose.pz}}},
            {"rotation", {{"qw", cam.pose.qw}, {"qx", cam.pose.qx},
                          {"qy", cam.pose.qy}, {"qz", cam.pose.qz}}},
        }},
    };
}

// float32×3 → base64 编码 (点云压缩, 体积减半)
static std::string encode_float32_base64(const std::vector<float>& pts, int point_count) {
    // point_count 个点, 每个点 3 个 float (x,y,z) = point_count × 3 × 4 字节
    size_t float_count = static_cast<size_t>(point_count) * 3;
    if (pts.size() < float_count) float_count = pts.size();
    const auto* bytes = reinterpret_cast<const uint8_t*>(pts.data());
    std::vector<uint8_t> raw(bytes, bytes + float_count * sizeof(float));
    return base64_encode(raw);
}

// ── 检测包 (float32_base64 点云 + 多相机) ──
json build_detection_packet(
    const std::string& frame_id, uint64_t timestamp_ns,
    const std::vector<float>& points, int point_count,
    const std::vector<CameraFrame>& cameras,
    const Pose& car_pose,
    double velocity, double steering_angle, double wheel_base)
{
    json views = json::array();
    for (const auto& cam : cameras) {
        views.push_back(camera_view_json(cam));
    }

    return {
        {"count", 1},
        {"frames", json::array({{
            {"frame_id", frame_id},
            {"timestamp_ns", timestamp_ns},
            {"point_cloud", {
                {"points", encode_float32_base64(points, point_count)},
                {"encoding", "float32_base64"},
                {"point_count", point_count},
            }},
            {"camera_views", views},
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
