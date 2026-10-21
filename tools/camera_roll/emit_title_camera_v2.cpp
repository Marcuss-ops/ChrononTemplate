// ChrononTemplate — title-camera v2 plan emitter (100% C++, no Python).
//
// Lowers every TitleCameraPack preset (20 v1 + 5 v2) to a
// chronon.render-plan.v3 document with the modern short-phrase look:
// Bricolage-Grotesque title face, warm-white fill + glow, deep-ink
// background. The camera keys are sampled straight from the C++ CameraRig,
// so this replaces tools/camera_roll/render_title_camera_documentary_v1.py.
//
// Usage:
//   chronontemplate_emit_title_camera_v2 <output-directory> [--v1-only]
//
// Layout:
//   <out>/<title_id>/plans/<move>.plan.json
//   <out>/manifest.json  (move, title, plan path)

#include <nlohmann/json.hpp>

#include "chronontemplate/camera_roll/TitleCameraPack.hpp"
#include <chrononmotion/motion/RenderPlanLowering.hpp>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
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
    constexpr int kDuration = 135;          // inclusive last frame
    constexpr int kDurationFrames = 136;

    // Modern short-phrase look, as chosen for the v2 refresh.
    constexpr const char* kTitleFont = "assets/fonts/Bricolage-Grotesque.ttf";
    constexpr const char* kCaptionFont = "assets/fonts/Inter-Regular.ttf";
    constexpr const char* kTitleFill = "#F2F0E8";
    constexpr const char* kTitleGlow = "#F2F0E8";
    constexpr double kGlowRadius = 24.0;
    constexpr double kGlowIntensity = 0.55;
    constexpr const char* kCaptionFill = "#C9BFAE";

    class Host final : public ContentHost {
    public:
        ContentHandle createText(const TextRequest& r) override {
            ContentHandle h;
            h.id = "text/" + r.text;
            h.kind = ContentKind::Text;
            h.metrics.naturalSize = Vector2(1000.f, 180.f);
            h.metrics.anchor = Vector2(.5f, .5f);
            h.metrics.fingerprint = "title-camera-v2";
            return h;
        }
        ContentHandle createImage(const ImageRequest&) override { return {}; }
        ContentHandle createVideo(const VideoRequest&) override { return {}; }
        std::string currentFingerprint(const ContentId&) const override { return "title-camera-v2"; }
    };

    std::string captionFor(const std::string& move) {
        constexpr const char* prefix = "title_camera_";
        std::string s = move;
        if (s.rfind(prefix, 0) == 0) s = s.substr(std::string(prefix).size());
        for (char& c : s) {
            if (c == '_') c = ' ';
            else c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
        }
        return s;
    }

    struct TitleCase {
        std::string id;
        std::string text;
    };

    json planFor(const std::string& moveId, const TitleCase& titleCase,
                 const CameraRig& rig) {
        const bool shortTitle = titleCase.text == "ROME";
        const double titleSize = shortTitle ? 188.0 : 112.0;
        const double titleH = shortTitle ? 270.0 : 200.0;

        const json cameraSamples = cameraSamplesToJson(bakeResolvedCameraSamples(
            rig, float(kFps), static_cast<std::size_t>(kDurationFrames), 1.f, 10000.f,
            Vector3(-kWidth * 0.5f, -kHeight * 0.5f, 0.f)));

        json bg = {{"id", "background"},
                   {"type", "color"},
                   {"color", {0.025, 0.032, 0.045, 1.0}},
                   {"size", {kWidth, kHeight}},
                   {"screen_space", true},
                   {"start_frame", 0},
                   {"duration_frames", kDurationFrames}};

        json titleLayer = {
            {"id", "hero-title"},
            {"type", "text"},
            {"text", titleCase.text},
            {"size", {1520, titleH}},
            {"position", {960, 540, 0}},
            {"start_frame", 0},
            {"duration_frames", kDurationFrames},
            {"enable_3d", true},
            {"style",
             {{"font", kTitleFont},
              {"font_size", titleSize},
              {"fill", kTitleFill},
              {"fit_mode", "shrink_only"},
              {"min_font_size", 54},
              {"max_font_size", titleSize},
              {"glow", {{"radius", kGlowRadius}, {"intensity", kGlowIntensity}, {"color", kTitleGlow}}}}}};

        json caption = {
            {"id", "move-caption"},
            {"type", "text"},
            {"text", captionFor(moveId)},
            {"size", {1000, 54}},
            {"position", {960, 875, 0}},
            {"start_frame", 0},
            {"duration_frames", kDurationFrames},
            {"enable_3d", true},
            {"style",
             {{"font", kCaptionFont},
              {"font_size", 26},
              {"fill", kCaptionFill},
              {"fit_mode", "shrink_only"},
              {"min_font_size", 20},
              {"max_font_size", 26}}}};

        return {
            {"schema", "chronon.render-plan.v3"},
            {"version", 3},
            {"job_id", "camera_title_documentary_v2_" + titleCase.id + "_" + moveId},
            {"canvas",
             {{"width", kWidth},
              {"height", kHeight},
              {"fps_num", kFps},
              {"fps_den", 1},
              {"duration_frames", kDurationFrames}}},
            {"camera", cameraSamples.front().at("camera")},
            {"camera_samples", cameraSamples},
            {"layers", {std::move(bg), std::move(titleLayer), std::move(caption)}},
            {"output",
             {{"path", titleCase.id + "/" + moveId + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}}};
    }

} // namespace

int main(int argc, char** argv) {
    if (argc < 2 || argc > 3) {
        std::cerr << "usage: chronontemplate_emit_title_camera_v2 <output-directory> [--v1-only]\n";
        return 2;
    }
    const bool v1Only = argc == 3 && std::string(argv[2]) == "--v1-only";
    if (argc == 3 && !v1Only) {
        std::cerr << "unknown flag: " << argv[2] << " (only --v1-only)\n";
        return 2;
    }

    const std::vector<TitleCase> titles = {{"simplicity", "THE ART OF SIMPLICITY"}, {"rome", "ROME"}};

    std::vector<std::string> ids = titleCameraMoveIds();
    if (v1Only && ids.size() > 20) ids.resize(20);
    if (ids.empty()) {
        std::cerr << "emit_title_camera_v2: no presets in the pack\n";
        return 1;
    }

    const fs::path out = argv[1];
    std::error_code ec;
    fs::create_directories(out, ec);
    if (ec) {
        std::cerr << "emit_title_camera_v2: cannot create " << out << ": " << ec.message() << "\n";
        return 1;
    }

    json manifest = json::array();
    for (const TitleCase& titleCase : titles) {
        for (std::size_t m = 0; m < ids.size(); ++m) {
            const auto move = static_cast<TitleCameraMove>(m);
            Host host;
            TemplateScene scene("title_camera_v2", static_cast<float>(kFps), host,
                                static_cast<float>(kWidth), static_cast<float>(kHeight));
            auto& title = scene.text(
                {.text = titleCase.text, .font = kTitleFont, .fontSize = 180.f});
            title.position(960.f, 540.f);
            try {
                applyTitleCameraShot(
                    scene, move,
                    TitleCameraShot{.anchor = {.center = Vector3(960.f, 540.f, 0.f),
                                              .halfWidth = 900.f,
                                              .halfHeight = 120.f},
                                    .framing = TitleFraming::Medium,
                                    .intensity = TitleCameraIntensity::Editorial,
                                    .inFrame = 0,
                                    .duration = kDuration});
            } catch (const std::exception& e) {
                std::cerr << "emit_title_camera_v2: " << ids[m] << ": " << e.what() << "\n";
                return 1;
            }

            const json plan = planFor(ids[m], titleCase, scene.camera().rig());
            const fs::path planPath = out / titleCase.id / "plans" / (ids[m] + ".plan.json");
            fs::create_directories(planPath.parent_path(), ec);
            if (ec) {
                std::cerr << "emit_title_camera_v2: cannot create " << planPath.parent_path()
                          << ": " << ec.message() << "\n";
                return 1;
            }
            std::ofstream file(planPath);
            if (!file) {
                std::cerr << "emit_title_camera_v2: cannot write " << planPath << "\n";
                return 1;
            }
            file << plan.dump(2) << "\n";
            manifest.push_back({{"move", ids[m]},
                                {"title", titleCase.id},
                                {"plan", (titleCase.id + "/plans/" + ids[m] + ".plan.json")}});
        }
    }

    {
        std::ofstream file(out / "manifest.json");
        if (!file) {
            std::cerr << "emit_title_camera_v2: cannot write manifest\n";
            return 1;
        }
        file << manifest.dump(2) << "\n";
    }
    std::cout << "Emitted " << manifest.size() << " title-camera v2 plans under " << out << "\n";
    return 0;
}
