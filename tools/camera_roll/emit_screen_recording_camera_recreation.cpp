// Emit a 3D camera pass over the user's supplied screen recording.
#include <nlohmann/json.hpp>

#include <chrononmotion/motion/CameraRig.hpp>
#include <chrononmotion/motion/RenderPlanLowering.hpp>
#include <chrononmotion/motion/Easing.hpp>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using Json = nlohmann::ordered_json;
using namespace chrononmotion::motion;
using chrononmotion::Quaternion;
using chrononmotion::Vector3;

namespace {
constexpr int kWidth = 1920;
constexpr int kHeight = 1080;
constexpr int kFps = 30;
constexpr int kFrames = 261;
constexpr float kDuration = static_cast<float>(kFrames - 1) / kFps;

double round6(double value) { return std::round(value * 1e6) / 1e6; }

Vector3 cameraEuler(const Quaternion& orientation) {
    constexpr float kRadToDeg = 57.29577951308232f;
    Quaternion q = orientation;
    q.invert();
    const float x = std::atan2(2.f * (q.w * q.x - q.y * q.z),
                               1.f - 2.f * (q.x * q.x + q.y * q.y));
    const float sinY = std::clamp(2.f * (q.w * q.y + q.z * q.x), -1.f, 1.f);
    const float y = std::asin(sinY);
    const float z = std::atan2(2.f * (q.w * q.z - q.x * q.y),
                               1.f - 2.f * (q.y * q.y + q.z * q.z));
    return {x * kRadToDeg, y * kRadToDeg, z * kRadToDeg};
}

Json track(const char* property, const std::vector<double>& values) {
    Json keys = Json::array();
    for (std::size_t i = 0; i < values.size(); ++i)
        keys.push_back({{"frame", i}, {"value", round6(values[i])}});
    return {{"property", property}, {"easing", "linear"}, {"keyframes", std::move(keys)}};
}
}

int main(int argc, char** argv) try {
    if (argc != 3)
        throw std::runtime_error("usage: emit_screen_recording_camera_recreation <source.mp4> <plan.json>");

    const fs::path source = fs::absolute(argv[1]);
    const fs::path output = fs::absolute(argv[2]);
    if (!fs::is_regular_file(source)) throw std::runtime_error("source video does not exist: " + source.string());

    // Motion coordinates are centered at the composition origin; RenderPlan
    // positions are top-left-origin pixel coordinates and camera-forward +Z.
    constexpr float kCenterX = static_cast<float>(kWidth) * 0.5f;
    constexpr float kCenterY = static_cast<float>(kHeight) * 0.5f;
    CameraRig rig(1, 55.f, static_cast<float>(kWidth) / kHeight, 1.f, 5000.f);
    rig.setPosition({kCenterX, kCenterY, 1120.f})
        .setTarget({kCenterX, kCenterY, 0.f}).setFov(55.f);
    const Easing move = Easing::cubicBezier(.35f, .05f, .65f, 1.f);
    rig.positionTrack().add(0.f, {kCenterX, kCenterY, 1120.f}, move)
        .add(3.0f, {kCenterX - 12.f, kCenterY + 8.f, 1090.f}, move)
        .add(6.1f, {kCenterX + 18.f, kCenterY - 12.f, 1065.f}, move)
        .add(kDuration, {kCenterX + 8.f, kCenterY + 4.f, 1080.f}, Easing::easeInOut());
    rig.targetTrack().add(0.f, {kCenterX, kCenterY, 0.f}, move)
        .add(3.f, {kCenterX, kCenterY, 0.f}, move)
        .add(6.1f, {kCenterX, kCenterY, 0.f}, move)
        .add(kDuration, {kCenterX, kCenterY, 0.f}, Easing::easeInOut());

    const Json cameraSamples = chrononmotion::motion::cameraSamplesToJson(
        chrononmotion::motion::bakeResolvedCameraSamples(rig, float(kFps), kFrames, 1.f, 5000.f,
            Vector3(-static_cast<float>(kWidth) * 0.5f, -static_cast<float>(kHeight) * 0.5f, 0.f)));

    const fs::path parent = output.parent_path();
    const std::string sourceName = source.filename().generic_string();
    Json plan = {
        {"schema", "chronon.render-plan.v3"}, {"version", 3},
        {"job_id", "screen_recording_camera_recreation_v1"},
        {"canvas", {{"width", kWidth}, {"height", kHeight}, {"fps_num", kFps},
                    {"fps_den", 1}, {"duration_frames", kFrames}}},
        {"camera", cameraSamples.front().at("camera")},
        {"camera_samples", cameraSamples},
        {"layers", Json::array({Json{{"id", "source_footage"}, {"type", "video"}, {"source", sourceName},
                    {"size", {kWidth, kHeight}}, {"position", {kWidth / 2, kHeight / 2, 0}},
                    {"fit", "cover"}, {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", kFrames}}})},
        {"output", {{"path", "Screen_Recording_Camera_Recreation.mp4"}, {"format", "mp4"}, {"codec", "h264"}}}
    };
    fs::create_directories(parent);
    std::ofstream file(output);
    if (!file) throw std::runtime_error("cannot write plan: " + output.string());
    file << plan.dump(2) << '\n';
    std::cout << "Wrote " << output << " (" << kFrames << " frames at " << kFps
              << " fps; perspective camera sampled from ChrononMotion CameraRig)\n";
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
