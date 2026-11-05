// Giulio Cesare apoteosi v5 — C++ camera authoring.
//
// The mesh and its collar are already authored scene data in the base plan.
// This emitter owns the camera move: a 144-degree front arc, always on the
// negative-Z side of the bust. The arc stays in front of the 2.5D layer plane
// instead of crossing it (the v4 360-degree experiment crossed z=0 and the
// layer was culled for the whole back half).

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;
using Json = nlohmann::ordered_json;

namespace {

constexpr int kDefaultFrames = 240;
constexpr float kFps = 30.0f;
constexpr float kRadius = 1400.0f;
constexpr float kCameraX = 960.0f;
constexpr float kCameraY = 540.0f;
constexpr float kArcHalfDegrees = 72.0f;
constexpr float kDegToRad = 0.01745329251994329577f;

float smoothstep01(float t) {
    t = std::clamp(t, 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

float round6(float value) {
    return std::round(value * 1.0e6f) / 1.0e6f;
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: emit_giulio_cesare_camera_v5 <base-plan.json> <out-plan.json>\n";
        return 2;
    }
    try {
        const fs::path base_path = fs::absolute(argv[1]);
        const fs::path out_path = fs::absolute(argv[2]);
        std::ifstream input(base_path);
        if (!input) throw std::runtime_error("cannot open base plan: " + base_path.string());
        Json plan = Json::parse(input);

        const Json canvas = plan.value("canvas", Json::object());
        const int frames = canvas.value("duration_frames", kDefaultFrames);
        if (frames <= 0) throw std::runtime_error("base plan has an invalid duration");
        if (!plan.contains("camera") || !plan["camera"].is_object())
            throw std::runtime_error("base plan has no camera descriptor");

        Json camera = plan["camera"];
        Json samples = Json::array();

        for (int frame = 0; frame < frames; ++frame) {
            const float t = frames > 1
                ? static_cast<float>(frame) / static_cast<float>(frames - 1)
                : 0.0f;
            const float eased = smoothstep01(t);
            const float angle_degrees =
                -kArcHalfDegrees + 2.0f * kArcHalfDegrees * eased;
            const float angle = angle_degrees * kDegToRad;

            Json sample_camera = camera;
            sample_camera["position"] = Json::array({
                round6(kCameraX + kRadius * std::sin(angle)),
                kCameraY,
                round6(-kRadius * std::cos(angle))});
            sample_camera["rotation_deg"] = Json::array({
                0.0,
                round6(-angle_degrees),
                0.0});

            samples.push_back({
                {"frame", frame},
                {"camera", std::move(sample_camera)}});
        }

        plan["camera"] = samples.front().at("camera");
        plan["camera_samples"] = std::move(samples);
        plan["canvas"]["duration_frames"] = frames;

        std::ofstream output(out_path);
        if (!output) throw std::runtime_error("cannot write plan: " + out_path.string());
        output << plan.dump(2) << '\n';
        std::cout << "wrote " << out_path << " with " << frames
                  << " camera samples\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "emit_giulio_cesare_camera_v5: " << error.what() << '\n';
        return 1;
    }
}
