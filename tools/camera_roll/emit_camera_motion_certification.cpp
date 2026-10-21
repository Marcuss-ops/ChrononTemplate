// ChrononTemplate — camera motion certification plan emitter.
//
// Lowers the whole fifteen-preset pack, in roster order, to chronon.render-plan.v3 documents over one shared
// canary look (deep-ink background, warm-white hero title, preset caption).
// The camera keys are sampled straight from the C++ CameraRig, so a render
// through chronon3d_cli certifies the authored move on the real backend.
//
// Usage:
//   chronontemplate_emit_camera_motion_certification <output-directory>
//
// Layout:
//   <out>/plans/<preset>.plan.json
//   <out>/manifest.json  (preset, frames, plan path, mp4 path)

#include <nlohmann/json.hpp>

#include "chronontemplate/camera_roll/CameraMotionPack.hpp"
#include <chrononmotion/motion/RenderPlanLowering.hpp>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
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

    constexpr const char* kTitleFont = "assets/fonts/Bricolage-Grotesque.ttf";
    constexpr const char* kCaptionFont = "assets/fonts/Inter-Regular.ttf";
    constexpr const char* kTitleFill = "#F2F0E8";
    constexpr const char* kCaptionFill = "#C9BFAE";

    class Host final : public ContentHost {
    public:
        ContentHandle createText(const TextRequest& r) override {
            ContentHandle h;
            h.id = "text/" + r.text;
            h.kind = ContentKind::Text;
            h.metrics.naturalSize = Vector2(1520.f, 200.f);
            h.metrics.anchor = Vector2(.5f, .5f);
            h.metrics.fingerprint = "camera-motion-cert";
            return h;
        }
        ContentHandle createShape(const ShapeRequest& r) override {
            ContentHandle h;
            h.id = "shape/" + r.name;
            h.kind = ContentKind::Image;
            h.metrics.naturalSize = r.size;
            h.metrics.anchor = Vector2(.5f, .5f);
            h.metrics.fingerprint = "camera-motion-cert";
            return h;
        }
        ContentHandle createImage(const ImageRequest&) override { return {}; }
        ContentHandle createVideo(const VideoRequest&) override { return {}; }
        std::string currentFingerprint(const ContentId&) const override { return "camera-motion-cert"; }
    };

    std::string captionFor(const std::string& id) {
        constexpr const char* prefix = "camera_motion_";
        std::string s = id;
        if (s.rfind(prefix, 0) == 0) s = s.substr(std::string(prefix).size());
        for (char& c : s) {
            if (c == '_') c = ' ';
            else c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
        }
        return s;
    }

    json planFor(const std::string& preset, int frames, const CameraRig& rig) {
        const json cameraSamples = cameraSamplesToJson(bakeResolvedCameraSamples(
            rig, float(kFps), static_cast<std::size_t>(frames), 1.f, 10000.f,
            Vector3(-kWidth * 0.5f, -kHeight * 0.5f, 0.f)));

        json bg = {{"id", "background"},
                   {"type", "color"},
                   {"color", {0.025, 0.032, 0.045, 1.0}},
                   {"size", {kWidth, kHeight}},
                   {"screen_space", true},
                   {"start_frame", 0},
                   {"duration_frames", frames}};

        json titleLayer = {
            {"id", "hero-title"},
            {"type", "text"},
            {"text", "THE CAMERA TELLS THE STORY"},
            {"size", {1520, 200}},
            {"position", {960, 470, 0}},
            {"start_frame", 0},
            {"duration_frames", frames},
            {"enable_3d", true},
            {"style",
             {{"font", kTitleFont},
              {"font_size", 112},
              {"fill", kTitleFill},
              {"fit_mode", "shrink_only"},
              {"min_font_size", 54},
              {"max_font_size", 112}}}};

        json caption = {
            {"id", "move-caption"},
            {"type", "text"},
            {"text", captionFor(preset)},
            {"size", {1000, 54}},
            {"position", {960, 875, 0}},
            {"start_frame", 0},
            {"duration_frames", frames},
            {"enable_3d", true},
            {"style",
             {{"font", kCaptionFont},
              {"font_size", 26},
              {"fill", kCaptionFill},
              {"fit_mode", "shrink_only"},
              {"min_font_size", 20},
              {"max_font_size", 26}}}};

        json layers = json::array({std::move(bg), std::move(titleLayer), std::move(caption)});

        return {
            {"schema", "chronon.render-plan.v3"},
            {"version", 3},
            {"job_id", std::string("camera_motion_cert_") + preset},
            {"canvas",
             {{"width", kWidth},
              {"height", kHeight},
              {"fps_num", kFps},
              {"fps_den", 1},
              {"duration_frames", frames}}},
            {"camera", cameraSamples.front().at("camera")},
            {"camera_samples", cameraSamples},
            {"layers", std::move(layers)},
            {"output",
             {{"path", preset + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}}};
    }

}// namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_emit_camera_motion_certification <output-directory>\n";
        return 2;
    }

    // The whole pack, in roster order.
    const std::vector<CameraMotionPreset> priority = chronontemplate::cameraMotionPresets();

    const fs::path out = argv[1];
    std::error_code ec;
    fs::create_directories(out / "plans", ec);
    if (ec) {
        std::cerr << "emit_camera_motion_certification: cannot create " << out << ": " << ec.message()
                  << "\n";
        return 1;
    }

    json manifest = json::array();
    for (const CameraMotionPreset preset : priority) {
        const std::string id = cameraMotionPresetId(preset);
        const int frames = cameraMotionDuration(preset);

        Host host;
        TemplateScene scene("camera_motion_cert", static_cast<float>(kFps), host,
                            static_cast<float>(kWidth), static_cast<float>(kHeight));
        auto& title = scene.text({.text = "THE CAMERA TELLS THE STORY", .font = kTitleFont,
                                  .fontSize = 160.f});
        title.position(960.f, 470.f);

        CameraMotionShot shot;
        shot.subject.center = Vector3(960.f, 540.f, 0.f);
        shot.subject.halfWidth = 760.f;
        shot.subject.halfHeight = 170.f;
        try {
            applyCameraMotionShot(scene, preset, shot);
        } catch (const std::exception& e) {
            std::cerr << "emit_camera_motion_certification: " << id << ": " << e.what() << "\n";
            return 1;
        }

        const json plan = planFor(id, frames, scene.camera().rig());
        const fs::path planPath = out / "plans" / (id + ".plan.json");
        std::ofstream file(planPath);
        if (!file) {
            std::cerr << "emit_camera_motion_certification: cannot write " << planPath << "\n";
            return 1;
        }
        file << plan.dump(2) << "\n";
        manifest.push_back({{"preset", id}, {"frames", frames}, {"plan", std::string("plans/") + id + ".plan.json"},
                            {"mp4", id + ".mp4"}});
    }

    {
        std::ofstream file(out / "manifest.json");
        if (!file) {
            std::cerr << "emit_camera_motion_certification: cannot write manifest\n";
            return 1;
        }
        file << manifest.dump(2) << "\n";
    }
    std::cout << "Emitted " << manifest.size() << " certification plans under " << out << "\n";
    return 0;
}
