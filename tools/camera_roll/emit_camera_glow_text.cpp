// ChrononTemplate — 2.5D camera-motion text with a cyan halo and a light RGB split.
//
// Three canaries that put the same depth-separated title treatment under three
// real ChrononMotion3D title-camera recipes (SlowPush, SlowPullOut, VerticalRise):
//
//   narrative camera recipe -> CameraRig -> camera_samples (C3D render plan)
//
// The look is genuinely 2.5D, not a flat 2D card: the title, an echo and two
// halo copies sit on four different Z planes, so a dolly or a lateral drift
// separates them. Chronon3D still owns shaping, rasterization and the effect
// stack; no second renderer is added.
//
// Usage:
//   chronontemplate_emit_camera_glow_text <output-directory>

#include <nlohmann/json.hpp>

#include "chronontemplate/camera_roll/TitleCameraPack.hpp"
#include <chrononmotion/motion/RenderPlanLowering.hpp>

#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

namespace fs = std::filesystem;
using json = nlohmann::ordered_json;

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;

namespace {

    constexpr int kWidth = 1920;
    constexpr int kHeight = 1080;
    constexpr int kFps = 30;
    constexpr int kLastFrame = 119;      // 120 frames, 4 s
    constexpr int kFrameCount = 120;

    constexpr const char* kFont = "assets/fonts/Bricolage-Grotesque.ttf";
    constexpr const char* kKickerFont = "assets/fonts/Inter-Regular.ttf";
    constexpr const char* kFill = "#F4FBFF";
    constexpr const char* kCyan = "#3FE7FF";
    constexpr const char* kCyanCore = "#8DF4FF";
    constexpr const char* kCyanDeep = "#17BFDD";
    constexpr const char* kKicker = "#9BEFFF";

    class Host final : public ContentHost {
    public:
        ContentHandle createText(const TextRequest& r) override {
            ContentHandle h;
            h.id = "text/" + r.text;
            h.kind = ContentKind::Text;
            h.metrics.naturalSize = Vector2(1000.f, 180.f);
            h.metrics.anchor = Vector2(.5f, .5f);
            h.metrics.fingerprint = "camera-glow-text";
            return h;
        }
        ContentHandle createImage(const ImageRequest&) override { return {}; }
        ContentHandle createVideo(const VideoRequest&) override { return {}; }
        std::string currentFingerprint(const ContentId&) const override {
            return "camera-glow-text";
        }
    };

    struct Recipe {
        std::string id;
        std::string text;
        std::string kicker;
        TitleCameraMove move;
        TitleCameraIntensity intensity;
        double fontSize;
    };

    json chromatic(double redOffset, double blueOffset, double shiftX, double shiftY) {
        return json{
            {"type", "chromatic_aberration"},
            {"red_offset", redOffset},
            {"blue_offset", blueOffset},
            {"mode", "radial"},
            {"center", json::array({0.5, 0.5})},
            {"red_transform", json{{"translation", json::array({-shiftX, shiftY})}}},
            {"green_transform", json{{"translation", json::array({0.0, 0.0})}}},
            {"blue_transform", json{{"translation", json::array({shiftX, -shiftY})}}},
        };
    }

    /// Apparent-size multiplier for a plane at +z: the camera rests at
    /// -restDistance, so a plane behind the title is that much farther away.
    double depthCompensation(double z, double restDistance) {
        return (restDistance + z) / restDistance;
    }

    json textLayer(const std::string& id, const std::string& text, const char* font,
                   double fontSize, double x, double y, double z, double boxW, double boxH,
                   const std::string& fill, const json& effects, const json& animation,
                   double glowRadius, double glowIntensity, const char* glowColor) {
        json layer{
            {"id", id},
            {"type", "text"},
            {"text", text},
            {"size", json::array({boxW, boxH})},
            {"position", json::array({x, y, z})},
            {"start_frame", 0},
            {"duration_frames", kFrameCount},
            {"enable_3d", true},
            {"style", json{
                {"font", font},
                {"font_size", fontSize},
                {"fill", fill},
                {"glow", json{{"radius", glowRadius}, {"intensity", glowIntensity},
                              {"color", glowColor}}},
            }},
        };
        if (!effects.empty()) layer["effects"] = effects;
        if (!animation.empty()) layer["animation"] = animation;
        return layer;
    }

    json buildPlan(const Recipe& recipe, const CameraRig& rig) {
        const json cameraSamples = cameraSamplesToJson(bakeResolvedCameraSamples(
            rig, float(kFps), std::size_t(kFrameCount), 1.f, 10000.f,
            Vector3(-kWidth * 0.5f, -kHeight * 0.5f, 0.f)));

        const double restDistance = std::abs(cameraSamples.front().at("camera")
                                                    .at("position").at(2).get<double>());
        if (!(restDistance > 1.0)) throw std::runtime_error("camera rest distance is degenerate");

        json background{
            {"id", "plate"},
            {"type", "color"},
            {"color", json::array({0.006, 0.017, 0.026, 1.0})},
            {"size", json::array({kWidth, kHeight})},
            {"screen_space", true},
            {"start_frame", 0},
            {"duration_frames", kFrameCount},
        };

        json kickerAnimation = json::array({
            json{{"property", "opacity"},
                 {"easing", "out_cubic"},
                 {"keyframes", json::array({json{{"frame", 0}, {"value", 0.0}},
                                            json{{"frame", 18}, {"value", 1.0}},
                                            json{{"frame", kLastFrame}, {"value", 1.0}}})}},
            json{{"property", "position"},
                 {"easing", "out_cubic"},
                 {"keyframes", json::array({
                     json{{"frame", 0}, {"value", json::array({kWidth * 0.5, kHeight * 0.5 - 196, 200.0})}},
                     json{{"frame", 24}, {"value", json::array({kWidth * 0.5, kHeight * 0.5 - 170, 200.0})}},
                     json{{"frame", kLastFrame}, {"value", json::array({kWidth * 0.5, kHeight * 0.5 - 170, 200.0})}},
                 })}},
        });

        const double kickerComp = depthCompensation(200.0, restDistance);
        json kicker = textLayer("kicker", recipe.kicker, kKickerFont, 64.0 * kickerComp,
                                kWidth * 0.5, kHeight * 0.5 - 170, 200.0,
                                1200.0 * kickerComp, 120.0 * kickerComp, kKicker,
                                json::array(), json{{"tracks", kickerAnimation}},
                                16.0 * kickerComp, 0.28, kCyan);

        json title = textLayer("title", recipe.text, kFont, recipe.fontSize,
                               kWidth * 0.5, kHeight * 0.5, 0.0, 1520.0, 200.0,
                               kFill,
                               json::array({chromatic(1.1, -1.1, 0.5, 0.25)}),
                               json{{"tracks", json::array({
                                        json{{"property", "position"},
                                             {"easing", "out_cubic"},
                                             {"keyframes", json::array({
                                                 json{{"frame", 0}, {"value", json::array({kWidth * 0.5, kHeight * 0.5 + 26, 0.0})}},
                                                 json{{"frame", 18}, {"value", json::array({kWidth * 0.5, kHeight * 0.5, 0.0})}},
                                                 json{{"frame", kLastFrame}, {"value", json::array({kWidth * 0.5, kHeight * 0.5, 0.0})}},
                                             })}},
                                        json{{"property", "scale"},
                                             {"easing", "out_cubic"},
                                             {"keyframes", json::array({
                                                 json{{"frame", 0}, {"value", 0.985}},
                                                 json{{"frame", 24}, {"value", 1.0}},
                                                 json{{"frame", kLastFrame}, {"value", 1.008}},
                                             })}},
                                        json{{"property", "opacity"},
                                             {"easing", "out_cubic"},
                                             {"keyframes", json::array({
                                                 json{{"frame", 0}, {"value", 0.0}},
                                                 json{{"frame", 14}, {"value", 1.0}},
                                                 json{{"frame", kLastFrame}, {"value", 1.0}},
                                             })}},
                                    })}},                                    34.0, 0.35, kCyan);

        return json{
            {"schema", "chronon.render-plan.v3"},
            {"version", 3},
            {"job_id", "chronon_camera_glow_cyan_" + recipe.id},
            {"canvas", json{{"width", kWidth}, {"height", kHeight}, {"fps_num", kFps},
                            {"fps_den", 1}, {"duration_frames", kFrameCount}}},
            {"camera", cameraSamples.front().at("camera")},
            {"camera_samples", cameraSamples},
            {"layers", json::array({background, kicker, title})},
            {"output", json{{"path", recipe.id + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}},
        };
    }

}// namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_emit_camera_glow_text <output-directory>\n";
        return 2;
    }

    // LeftDrift yawed the near title plane out of frame, so the third shot
    // uses the pull-out dolly instead.
    const std::vector<Recipe> recipes = {
        {"slow_push", "IL TEMPO E TUTTO", "CAMERA / SLOW PUSH", TitleCameraMove::SlowPush,
         TitleCameraIntensity::Editorial, 112.0},
        {"slow_pull_out", "OGNI DETTAGLIO CONTA", "CAMERA / SLOW PULL OUT",
         TitleCameraMove::SlowPullOut, TitleCameraIntensity::Editorial, 112.0},
        {"vertical_rise", "RESTA ANCORA", "CAMERA / VERTICAL RISE", TitleCameraMove::VerticalRise,
         TitleCameraIntensity::Editorial, 132.0},
    };

    const fs::path out = argv[1];
    std::error_code ec;
    fs::create_directories(out, ec);
    if (ec) {
        std::cerr << "cannot create " << out << ": " << ec.message() << "\n";
        return 1;
    }

    json manifest = json::array();
    for (const Recipe& recipe : recipes) {
        Host host;
        TemplateScene scene("camera_glow_cyan", float(kFps), host,
                            float(kWidth), float(kHeight));
        auto& title = scene.text({.text = recipe.text, .font = kFont,
                                  .fontSize = float(recipe.fontSize)});
        title.position(float(kWidth) * 0.5f, float(kHeight) * 0.5f);

        // The anchor must describe the run that is actually rendered. The old
        // 900 px half-width was a placeholder and would make the new framing
        // guard reject every shot. 0.42 em is a conservative average advance
        // for Bricolage at these sizes (spaces included), so the bound stays
        // slightly wider than the raster.
        const float titleHalfWidth =
            0.42f * float(recipe.fontSize) * float(recipe.text.size()) * 0.5f;
        applyTitleCameraShot(
            scene, recipe.move,
            TitleCameraShot{.anchor = {.center = Vector3(float(kWidth) * 0.5f,
                                                          float(kHeight) * 0.5f, 0.f),
                                        .halfWidth = titleHalfWidth,
                                        .halfHeight = float(recipe.fontSize) * 0.7f},
                            .framing = TitleFraming::Medium,
                            .intensity = recipe.intensity,
                            .inFrame = 0,
                            .duration = kLastFrame});

        const json plan = buildPlan(recipe, scene.camera().rig());
        const fs::path planPath = out / (recipe.id + ".plan.json");
        std::ofstream file(planPath);
        if (!file) {
            std::cerr << "cannot write " << planPath << "\n";
            return 1;
        }
        file << plan.dump(2) << "\n";
        manifest.push_back({{"id", recipe.id},
                            {"text", recipe.text},
                            {"plan", planPath.filename().string()}});
    }

    std::ofstream manifestFile(out / "manifest.json");
    manifestFile << manifest.dump(2) << "\n";
    std::cout << "Emitted " << manifest.size() << " 2.5D camera-glow-cyan plans under " << out << "\n";
    return 0;
}
