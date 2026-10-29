#include <chrononmotion/motion/CameraRig.hpp>
#include <chrononmotion/motion/CameraShake.hpp>
#include <chrononmotion/motion/RenderPlanLowering.hpp>
#include <nlohmann/json.hpp>

#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
using Json = nlohmann::ordered_json;
using namespace chrononmotion;
using namespace chrononmotion::motion;
namespace fs = std::filesystem;

constexpr int kWidth = 1920;
constexpr int kHeight = 1080;
constexpr int kFps = 30;
constexpr int kFrames = 180;
constexpr float kNear = 1.f;
constexpr float kFar = 10000.f;
constexpr const char* kTitleFont = "Chronon3d/assets/fonts/Poppins-Bold.ttf";
constexpr const char* kBodyFont = "Chronon3d/assets/fonts/Inter-Regular.ttf";
constexpr const char* kSandwich = "ChrononTemplate/assets/gpu_food_parallax_v1/crispy_chicken_sandwich_cutout_v1.png";
constexpr const char* kFries = "ChrononTemplate/assets/gpu_food_parallax_v1/crinkle_fries_cutout_v1.png";
constexpr const char* kPortrait = "ChrononTemplate/assets/images/truett_cathy_portrait_v5_photo_cutout.png";
constexpr const char* kRestaurant = "ChrononTemplate/assets/images/true_legacy_restaurant_background_v3_graded.png";
constexpr const char* kNightRestaurant = "ChrononTemplate/assets/images/true_legacy_night_restaurant_v1.png";

struct Story {
    const char* id;
    const char* eyebrow;
    const char* titleTop;
    const char* titleBottom;
    const char* dek;
    const char* background;
    Vector3 cameraStart;
    Vector3 cameraEnd;
    float fov;
    std::uint32_t shakeSeed;
    float shake;
    float portraitX;
    float sandwichX;
    float friesX;
};

Json cameraSamples(const Story& story) {
    CameraRig rig(1, story.fov, static_cast<float>(kWidth) / kHeight, kNear, kFar);
    rig.setPosition(story.cameraStart)
        .setTarget(Vector3(0.f, 0.f, 0.f))
        .setFov(story.fov);

    camera::CameraShakeSpec shake;
    shake.positionFrequency = 0.34f;
    shake.positionAmplitude = story.shake;
    shake.rotationFrequency = 0.f;
    shake.rotationAmplitudeDegrees = 0.f;
    shake.zoomFrequency = 0.f;
    shake.zoomAmplitude = 0.f;
    shake.seed = story.shakeSeed;

    const float lastFrame = static_cast<float>(kFrames - 1);
    for (int frame = 0; frame < kFrames; ++frame) {
        const float t = static_cast<float>(frame) / lastFrame;
        const float eased = t * t * (3.f - 2.f * t);
        Vector3 position = story.cameraStart * (1.f - eased) + story.cameraEnd * eased;
        const auto drift = camera::sampleCameraShake(shake, static_cast<float>(frame), lastFrame);
        position += drift.position;
        rig.positionTrack().add(static_cast<float>(frame) / kFps, position, Easing::linear());
    }

    const auto samples = bakeResolvedCameraSamples(
        rig, static_cast<float>(kFps), kFrames, kNear, kFar,
        Vector3(-static_cast<float>(kWidth) * 0.5f,
                -static_cast<float>(kHeight) * 0.5f, 0.f));
    return cameraSamplesToJson(samples);
}

Json image(std::string id, const char* asset, float x, float y, float z,
           float width, float height, const char* fit = "contain") {
    return Json{{"id", std::move(id)}, {"type", "image"}, {"asset", asset},
                {"position", {x, y, z}}, {"size", {width, height}}, {"fit", fit},
                {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", kFrames}};
}

Json title(std::string id, std::string copy, float x, float y, float z,
           float width, float height, int fontSize, const char* color = "#FFF7E8") {
    return Json{{"id", std::move(id)}, {"type", "text"}, {"text", std::move(copy)},
                {"position", {x, y, z}}, {"size", {width, height}},
                {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", kFrames},
                {"style", {{"font", kTitleFont}, {"font_size", fontSize},
                            {"min_font_size", fontSize - 10}, {"max_font_size", fontSize},
                            {"fit_mode", "shrink_only"}, {"text_align", "left"},
                            {"fill", color}}}};
}

Json label(std::string id, std::string copy, float x, float y, float z,
           float width, int fontSize, const char* color) {
    return Json{{"id", std::move(id)}, {"type", "text"}, {"text", std::move(copy)},
                {"position", {x, y, z}}, {"size", {width, 54}},
                {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", kFrames},
                {"style", {{"font", kBodyFont}, {"font_size", fontSize},
                            {"min_font_size", fontSize}, {"max_font_size", fontSize},
                            {"fit_mode", "shrink_only"}, {"text_align", "left"},
                            {"fill", color}}}};
}

Json panel(std::string id, float x, float y, float z, float width, float height,
           const char* color, float opacity) {
    const std::string hex = color;
    const auto channel = [&](std::size_t offset) {
        return static_cast<double>(std::stoul(hex.substr(offset, 2), nullptr, 16)) / 255.0;
    };
    return Json{{"id", std::move(id)}, {"type", "shape"}, {"enable_3d", true},
                {"position", {x, y, z}}, {"size", {width, height}},
                {"start_frame", 0}, {"duration_frames", kFrames},
                {"shape", {{"type", "rect"},
                            {"fill", {channel(1), channel(3), channel(5), opacity}}}}};
}

Json plan(const Story& story) {
    Json layers = Json::array();
    layers.push_back(image("deep_restaurant_plate", story.background,
                           -static_cast<float>(kWidth) * 0.5f,
                           -static_cast<float>(kHeight) * 0.5f, 360.f,
                           static_cast<float>(kWidth), static_cast<float>(kHeight), "cover"));
    // Large type sits on its own plane behind the founder cutout.
    layers.push_back(label("chapter_eyebrow", story.eyebrow, -760.f, 335.f, 190.f,
                           900.f, 24, "#F4B45E"));
    layers.push_back(title("headline_top", story.titleTop, -760.f, 170.f, 175.f,
                           1080.f, 190.f, 112));
    layers.push_back(title("headline_bottom", story.titleBottom, -760.f, 20.f, 165.f,
                           1120.f, 190.f, 112, "#F4B45E"));
    layers.push_back(label("story_dek", story.dek, -748.f, -130.f, 150.f,
                           800.f, 28, "#E8E1D6"));

    // The portrait is an existing transparent cutout. The food cutouts are
    // newly generated transparent PNGs, each on a nearer plane for parallax.
    layers.push_back(image("founder_cutout", kPortrait, story.portraitX, -30.f, 15.f,
                           920.f, 950.f));
    auto sandwich = image("hero_sandwich", kSandwich, story.sandwichX, -330.f, -125.f,
                          620.f, 414.f);
    sandwich["animation"] = {{"tracks", Json::array({
        Json{{"property", "position_y"}, {"easing", "in_out_sine"},
             {"keyframes", Json::array({{{"frame", 0}, {"value", -330}},
                                         {{"frame", 90}, {"value", -304}},
                                         {{"frame", 179}, {"value", -330}}})}},
        Json{{"property", "rotation_z"}, {"easing", "in_out_sine"},
             {"keyframes", Json::array({{{"frame", 0}, {"value", -2.0}},
                                         {{"frame", 90}, {"value", 1.2}},
                                         {{"frame", 179}, {"value", -2.0}}})}}
    })}};
    layers.push_back(std::move(sandwich));
    layers.push_back(image("fries_cutout", kFries, story.friesX, -280.f, -220.f,
                           330.f, 302.f));

    // A restrained editorial marker anchors the lower edge while staying in
    // the moving scene, so the foreground objects pass at a different rate.
    layers.push_back(panel("red_marker", -720.f, -430.f, 45.f, 8.f, 72.f,
                           "#E93B2F", 1.f));
    layers.push_back(label("source_line", "A FAMILY RECIPE. A LONG GAME.",
                           -680.f, -420.f, 45.f, 760.f, 22, "#FFF7E8"));

    const Json samples = cameraSamples(story);
    return Json{{"schema", "chronon.render-plan.v3"}, {"version", 3},
                {"job_id", story.id},
                {"canvas", {{"width", kWidth}, {"height", kHeight},
                             {"fps_num", kFps}, {"fps_den", 1},
                             {"duration_frames", kFrames}}},
                {"camera", samples.front().at("camera")},
                {"camera_samples", samples},
                {"layers", std::move(layers)},
                {"output", {{"path", std::string(story.id) + ".mp4"},
                             {"format", "mp4"}, {"codec", "h264"}}}};
}

} // namespace

int main(int argc, char** argv) {
    try {
        const fs::path output = argc > 1 ? fs::path(argv[1])
                                         : fs::path("examples/gpu_food_parallax_v1/plans");
        fs::create_directories(output);
        const std::array<Story, 3> stories{{
            {"food_story_01_humble_beginnings", "THE ORIGIN STORY",
             "HUMBLE", "BEGINNINGS", "A small dining room. One focused idea.",
             kNightRestaurant, {0.f, 0.f, 1380.f}, {42.f, 12.f, 1160.f},
             46.f, 1946U, 1.0f, 360.f, -560.f, 680.f},
            {"food_story_02_the_sandwich", "ONE PRODUCT / ONE POINT OF VIEW",
             "THE CHICKEN", "SANDWICH", "A simple menu becomes the whole story.",
             kRestaurant, {-55.f, 12.f, 1440.f}, {35.f, -4.f, 1080.f},
             49.f, 1947U, 0.7f, -420.f, 420.f, -720.f},
            {"food_story_03_long_game", "THE LONG GAME",
             "FROM ONE STORE", "TO A NATIONAL ICON", "Consistency turns a local idea into a ritual.",
             kNightRestaurant, {-90.f, 0.f, 1480.f}, {65.f, 18.f, 1100.f},
             44.f, 1948U, 1.4f, 430.f, -440.f, 700.f}
        }};

        Json manifest{{"schema", "chronontemplate.gpu-food-parallax.v1"},
                      {"renderer", "Chronon3D RenderPlan V3 / strict Vulkan"},
                      {"camera_authority", "ChrononMotion3D CameraRig + CameraShake"},
                      {"canvas", {{"width", kWidth}, {"height", kHeight},
                                  {"fps", kFps}, {"frames", kFrames}}},
                      {"asset_notes", "Founder/restaurant assets are existing project files; sandwich/fries are generated transparent cutouts."},
                      {"plans", Json::array()}};
        for (const auto& story : stories) {
            const fs::path file = output / (std::string(story.id) + ".plan.json");
            std::ofstream stream(file, std::ios::binary | std::ios::trunc);
            const Json value = plan(story);
            if (!stream || !(stream << value.dump(2) << '\n'))
                throw std::runtime_error("failed writing plan " + file.string());
            manifest["plans"].push_back(file.filename().string());
            std::cout << "Wrote " << file << " (" << value["layers"].size()
                      << " layers, " << value["camera_samples"].size() << " camera samples)\n";
        }
        std::ofstream manifestFile(output / "manifest.json", std::ios::binary | std::ios::trunc);
        if (!manifestFile || !(manifestFile << manifest.dump(2) << '\n'))
            throw std::runtime_error("failed writing example manifest");
    } catch (const std::exception& error) {
        std::cerr << "emit_food_story_examples: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
