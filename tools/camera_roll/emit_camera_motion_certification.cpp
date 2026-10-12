// ChrononTemplate — camera motion certification plan emitter.
//
// Lowers the spec's priority thirteen (01, 10, 11, 18, 19, 21, 27, 28, 33,
// 35, 41, 45, 49) to chronon.render-plan.v3 documents over one shared
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

    enum class Foreground { None, StaticBar, OcclusionSweep };

    json layerTrack(const std::string& prop, std::vector<std::pair<int, double>> keys,
                    const std::string& easing) {
        json list = json::array();
        for (const auto& [frame, value] : keys) {
            list.push_back({{"frame", frame}, {"value", round6(value)}});
        }
        return {{"property", prop}, {"keyframes", std::move(list)}, {"easing", easing}};
    }

    json planFor(const std::string& preset, int frames,
                 const std::vector<std::vector<double>>& channels,
                 const std::vector<double>& firstRow, Foreground foreground,
                 int cutFrame, bool focusTrack, double focusFirst) {
        (void)cutFrame;
        (void)focusTrack;
        (void)focusFirst;
        json tracks = json::array();
        const char* props[8] = {"camera_position_x", "camera_position_y", "camera_position_z",
                                "camera_rotation_x", "camera_rotation_y", "camera_rotation_z",
                                "camera_fov_deg", "camera_focus_distance"};
        for (std::size_t i = 0; i < channels.size(); ++i) {
            tracks.push_back(track(props[i], channels[i]));
        }

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
        if (foreground == Foreground::StaticBar) {
            // Frame-anchored bar (screen space): the panning title slides
            // under it, which reads as depth separation. NOTE: a `color`
            // layer with enable_3d renders black over the frame on the
            // current backend, so depth bars stay in screen space.
            layers.push_back({
                {"id", "foreground-bar"},
                {"type", "color"},
                {"color", {0.85, 0.62, 0.25, 1.0}},
                {"size", {260, 1080}},
                {"position", {180, 0}},
                {"screen_space", true},
                {"start_frame", 0},
                {"duration_frames", frames},
            });
        } else if (foreground == Foreground::OcclusionSweep) {
            // Staged static occluder. NOTE: an animated screen-space layer
            // corrupts frames on the current backend (alternating black
            // frames), so the cover is staged, not swept: title, full
            // cover hiding the cut, title again. Layer animation tracks
            // stay out of certification scenes until the backend is fixed.
            layers.push_back({
                {"id", "foreground-bar"},
                {"type", "color"},
                {"color", {0.85, 0.62, 0.25, 1.0}},
                {"size", {2400, 1080}},
                {"position", {-240, 0}},
                {"screen_space", true},
                {"start_frame", 3},
                {"duration_frames", cutFrame - 3 + 1},
            });
        }

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
            {"camera",
             {{"type", "perspective"},
              {"position", {round6(channels[0][0]), round6(channels[1][0]), round6(channels[2][0])}},
              {"rotation_deg", {round6(firstRow[4]), round6(firstRow[5]), round6(firstRow[6])}},
              {"fov_deg", round6(firstRow[7])},
              {"near", 1},
              {"far", 10000},
              {"zoom", 1},
              // NOTE: DOF enabled renders black on the Vulkan backend, so
              // certification covers the body move with DOF off. The
              // focus keys stay on the rig (unit-tested) and need a
              // backend with working DOF for rack-focus visuals.
              {"dof",
               json{{"enabled", false}}}}},
            {"camera_animation", {{"tracks", std::move(tracks)}}},
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

    // The whole pack: the priority thirteen first, then the remaining
    // thirty-seven in spec order.
    const std::vector<CameraMotionPreset> priority = {
        CameraMotionPreset::SoftPushIn, CameraMotionPreset::ImpactPunchSettle,
        CameraMotionPreset::KenBurnsIn, CameraMotionPreset::PortraitHeroArc,
        CameraMotionPreset::DocumentaryParallax, CameraMotionPreset::MapRegionPush,
        CameraMotionPreset::RouteCameraSweep, CameraMotionPreset::CountryFocusLock,
        CameraMotionPreset::CardStackParallax, CameraMotionPreset::DataDetailZoom,
        CameraMotionPreset::WhipPanLeft, CameraMotionPreset::FastDollyThrough,
        CameraMotionPreset::ForegroundOcclusionPass,
        CameraMotionPreset::SoftPullBack, CameraMotionPreset::EditorialDriftLeft,
        CameraMotionPreset::EditorialDriftRight, CameraMotionPreset::TitleRise,
        CameraMotionPreset::TitleDescend, CameraMotionPreset::QuietDiagonalDrift,
        CameraMotionPreset::TypeDepthFocus, CameraMotionPreset::TypeMicroOrbit,
        CameraMotionPreset::KenBurnsOut, CameraMotionPreset::PortraitUpwardTrack,
        CameraMotionPreset::PortraitDownwardTrack, CameraMotionPreset::PhotoRevealLeft,
        CameraMotionPreset::PhotoRevealRight, CameraMotionPreset::LowAnglePhotoReveal,
        CameraMotionPreset::PhotoRackFocus, CameraMotionPreset::MapRegionPull,
        CameraMotionPreset::MapEastwardTrack, CameraMotionPreset::MapWestwardTrack,
        CameraMotionPreset::MapNorthwardTrack, CameraMotionPreset::MapSouthwardTrack,
        CameraMotionPreset::CountryComparisonPan, CameraMotionPreset::GeopoliticalTiltReveal,
        CameraMotionPreset::UiPanelPush, CameraMotionPreset::DashboardPan,
        CameraMotionPreset::CornerDetailInspect, CameraMotionPreset::UiOverviewPull,
        CameraMotionPreset::SideBySideCompare, CameraMotionPreset::PanelAngledPeek,
        CameraMotionPreset::ChartTraverse, CameraMotionPreset::ProductUiMicroFloat,
        CameraMotionPreset::WhipPanRight, CameraMotionPreset::WhipPanUp,
        CameraMotionPreset::WhipPanDown, CameraMotionPreset::ReverseDollyReveal,
        CameraMotionPreset::RollMatchCut, CameraMotionPreset::OrbitHandoff,
        CameraMotionPreset::FocusHandoff};

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
        const Foreground foreground = preset == CameraMotionPreset::DocumentaryParallax
                                        ? Foreground::StaticBar
                                        : (preset == CameraMotionPreset::ForegroundOcclusionPass
                                                   ? Foreground::OcclusionSweep
                                                   : Foreground::None);

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

        const CameraMotionSpec& spec = cameraMotionSpecFor(preset);
        // NOTE: the focus channel is sampled on the rig (unit-tested) but
        // stays out of certification plans: the backend rejects animated
        // focus with DOF off and renders black with DOF on.
        const bool focusTrack = false;
        const int nChannels = 7;
        std::vector<std::vector<double>> channels(static_cast<std::size_t>(nChannels),
                                                  std::vector<double>(static_cast<std::size_t>(frames)));
        std::vector<double> firstRow(8, 0.0);
        for (int f = 0; f < frames; ++f) {
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
            if (focusTrack) channels[7][i] = pose.focusDistance;
            if (f == 0) {
                firstRow = {0.0, channels[0][0], channels[1][0], channels[2][0], r.x, r.y, r.z,
                            pose.fov};
            }
        }
        for (std::size_t c = 3; c < 6; ++c) unwrap(channels[c]);

        const int cutFrame = static_cast<int>(std::round(frames * spec.cutAt));
        const double focusFirst = focusTrack && !channels[7].empty() ? channels[7][0] : 0.0;
        const json plan = planFor(id, frames, channels, firstRow, foreground, cutFrame, focusTrack,
                                  focusFirst);
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
