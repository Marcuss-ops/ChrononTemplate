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

    Vector3 euler(const Quaternion& q) {
        constexpr float radToDeg = 57.29577951308232f;
        Quaternion camera = q;
        camera.invert();
        const float x = std::atan2(2.f * (camera.w * camera.x - camera.y * camera.z),
                                   1.f - 2.f * (camera.x * camera.x + camera.y * camera.y));
        const float s = std::clamp(2.f * (camera.w * camera.y + camera.z * camera.x), -1.f, 1.f);
        const float y = std::asin(s);
        const float z = std::atan2(2.f * (camera.w * camera.z - camera.x * camera.y),
                                   1.f - 2.f * (camera.y * camera.y + camera.z * camera.z));
        return Vector3(x * radToDeg, y * radToDeg, z * radToDeg);
    }

    void unwrap(std::vector<double>& values) {
        for (std::size_t i = 1; i < values.size(); ++i) {
            double angle = values[i];
            const double prev = values[i - 1];
            while (angle - prev > 180.0) angle -= 360.0;
            while (angle - prev < -180.0) angle += 360.0;
            values[i] = angle;
        }
    }

    double round6(double v) { return std::round(v * 1e6) / 1e6; }

    json track(const std::string& prop, const std::vector<double>& values) {
        json keys = json::array();
        for (std::size_t i = 0; i < values.size(); ++i) {
            keys.push_back({{"frame", static_cast<int>(i)}, {"value", round6(values[i])}});
        }
        return {{"property", prop}, {"easing", "linear"}, {"keyframes", std::move(keys)}};
    }

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
                 const std::vector<std::vector<double>>& channels,
                 const std::vector<double>& firstRow) {
        const bool shortTitle = titleCase.text == "ROME";
        const double titleSize = shortTitle ? 188.0 : 112.0;
        const double titleH = shortTitle ? 270.0 : 200.0;

        json tracks = json::array();
        const char* props[7] = {"camera_position_x", "camera_position_y", "camera_position_z",
                                "camera_rotation_x", "camera_rotation_y", "camera_rotation_z",
                                "camera_fov_deg"};
        for (int i = 0; i < 7; ++i) tracks.push_back(track(props[i], channels[static_cast<std::size_t>(i)]));

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
            {"camera",
             {{"type", "perspective"},
              {"position", {round6(channels[0][0]), round6(channels[1][0]), round6(channels[2][0])}},
              {"rotation_deg", {round6(firstRow[4]), round6(firstRow[5]), round6(firstRow[6])}},
              {"fov_deg", round6(firstRow[7])},
              {"near", 1},
              {"far", 10000},
              {"zoom", 1}}},
            {"camera_animation", {{"tracks", std::move(tracks)}}},
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

            // Sample the rig exactly like dump_title_camera_poses, then lower
            // to render-plan camera channels with the same canvas convention
            // the Python renderer used (canvas-centre relative, -Z forward).
            std::vector<std::vector<double>> channels(7, std::vector<double>(kDurationFrames));
            std::vector<double> firstRow(8, 0.0);
            for (int f = 0; f <= kDuration; ++f) {
                const auto pose = scene.camera().rig().sample(static_cast<float>(f) / kFps);
                const Vector3 r = euler(pose.orientation);
                const std::size_t i = static_cast<std::size_t>(f);
                channels[0][i] = pose.position.x - kWidth / 2;
                channels[1][i] = pose.position.y - kHeight / 2;
                channels[2][i] = -pose.position.z;
                channels[3][i] = r.x;
                channels[4][i] = r.y;
                channels[5][i] = r.z;
                channels[6][i] = pose.fov;
                if (f == 0) {
                    firstRow = {0.0, channels[0][0], channels[1][0], channels[2][0], r.x, r.y,
                                r.z, pose.fov};
                }
            }
            for (std::size_t c = 3; c < 6; ++c) unwrap(channels[c]);

            const json plan = planFor(ids[m], titleCase, channels, firstRow);
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
