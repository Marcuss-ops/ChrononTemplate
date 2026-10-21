// Compose four original AI illustrations into a spatial image-card camera move.
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
constexpr float kCameraDistance = 1120.f;
constexpr float kCardY = 540.f;
constexpr float kCardSizeX = 1920.f;
constexpr float kCardSizeY = 1080.f;
constexpr float kCardStep = 2000.f;
constexpr float kFirstCardX = 960.f;

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

Json imageLayer(const char* id, const char* asset, float centerX, int frames) {
    return {{"id", id}, {"type", "image"}, {"asset", asset},
            {"size", {kCardSizeX, kCardSizeY}}, {"position", {centerX, kCardY, 0}},
            {"fit", "cover"}, {"start_frame", 0}, {"duration_frames", frames},
            {"enable_3d", true}};
}
}

int main(int argc, char** argv) try {
    if (argc != 2)
        throw std::runtime_error("usage: emit_ai_tabletop_camera <plan.json>");
    const fs::path output = fs::absolute(argv[1]);

    const float x1 = kFirstCardX;
    const float x2 = x1 + kCardStep;
    const float x3 = x2 + kCardStep;
    const float x4 = x3 + kCardStep;
    const Easing glide = Easing::cubicBezier(.25f, .05f, .55f, 1.f);
    const Easing whip = Easing::cubicBezier(.55f, 0.f, .9f, .45f);
    CameraRig rig(1, 55.f, static_cast<float>(kWidth) / kHeight, 1.f, 10000.f);
    rig.setPosition({x1, kCardY, kCameraDistance})
       .setTarget({x1, kCardY, 0.f}).setFov(55.f);

    // Long, gentle opening push; then three short diagonal whips that travel
    // between independent illustration planes, ending on a deliberate close-up.
    rig.positionTrack().add(0.f, {x1, kCardY, 1240.f}, glide)
       .add(2.0f, {x1 - 18.f, kCardY + 9.f, 1080.f}, glide)
       .add(4.55f, {x1 + 12.f, kCardY - 6.f, 1180.f}, glide)
       .add(4.9f, {x1, kCardY, 1150.f}, whip)
       .add(5.35f, {x2, kCardY + 15.f, 1160.f}, glide)
       .add(5.65f, {x2 - 16.f, kCardY - 10.f, 1010.f}, whip)
       .add(6.05f, {x3, kCardY, 1160.f}, glide)
       .add(6.38f, {x3 + 12.f, kCardY + 8.f, 970.f}, whip)
       .add(6.78f, {x4, kCardY, 1160.f}, glide)
       .add(kDuration, {x4 + 20.f, kCardY - 12.f, 790.f}, Easing::easeInOut());
    rig.targetTrack().add(0.f, {x1, kCardY, 0.f}, glide)
       .add(4.9f, {x1, kCardY, 0.f}, whip)
       .add(5.35f, {x2, kCardY, 0.f}, glide)
       .add(5.65f, {x2, kCardY, 0.f}, whip)
       .add(6.05f, {x3, kCardY, 0.f}, glide)
       .add(6.38f, {x3, kCardY, 0.f}, whip)
       .add(6.78f, {x4, kCardY, 0.f}, glide)
       .add(kDuration, {x4, kCardY, 0.f}, Easing::easeInOut());
    rig.rollTrack().add(0.f, 0.f, glide)
       .add(4.9f, 0.f, whip).add(5.35f, .11f, glide)
       .add(5.65f, 0.f, whip).add(6.05f, -.10f, glide)
       .add(6.38f, 0.f, whip).add(6.78f, .075f, glide)
       .add(kDuration, 0.f, Easing::easeInOut());

    const Json cameraSamples = chrononmotion::motion::cameraSamplesToJson(
        chrononmotion::motion::bakeResolvedCameraSamples(rig, float(kFps), kFrames, 1.f, 10000.f,
            Vector3(-static_cast<float>(kWidth) * 0.5f, -static_cast<float>(kHeight) * 0.5f, 0.f)));

    const Json layers = Json::array({
        Json{{"id", "table_backdrop"}, {"type", "color"}, {"color", {0.035, 0.025, 0.02, 1.0}},
             {"size", {kWidth, kHeight}}, {"screen_space", true}, {"start_frame", 0}, {"duration_frames", kFrames}},
        imageLayer("kyoto_parchment", "assets/ai_tabletop/01_kyoto_parchment.png", x1, kFrames),
        imageLayer("rain_bridge", "assets/ai_tabletop/02_rain_bridge.png", x2, kFrames),
        imageLayer("samurai_armor", "assets/ai_tabletop/03_samurai_armor.png", x3, kFrames),
        imageLayer("sumi_e_battle", "assets/ai_tabletop/04_sumi_e_battle.png", x4, kFrames),
    });
    Json plan = {
        {"schema", "chronon.render-plan.v3"}, {"version", 3},
        {"job_id", "ai_tabletop_camera_remake_v1"},
        {"canvas", {{"width", kWidth}, {"height", kHeight}, {"fps_num", kFps}, {"fps_den", 1}, {"duration_frames", kFrames}}},
        {"camera", cameraSamples.front().at("camera")},
        {"camera_samples", cameraSamples},
        {"layers", layers},
        {"output", {{"path", "AI_Tabletop_Camera_Remake_1080p.mp4"}, {"format", "mp4"}, {"codec", "h264"}}}
    };
    fs::create_directories(output.parent_path());
    std::ofstream file(output);
    if (!file) throw std::runtime_error("cannot write plan: " + output.string());
    file << plan.dump(2) << '\n';
    std::cout << "Wrote " << output << " with four independent generated image planes and a sampled ChrononMotion CameraRig\n";
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
