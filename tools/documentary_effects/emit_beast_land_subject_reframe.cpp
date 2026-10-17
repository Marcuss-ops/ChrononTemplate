// Native C++ scene-camera example: measured presenter bounds drive a reusable
// SceneCameraPack reframe. Usage: <asset-dir> <plan.json> [preview|video].
#include "chronontemplate/camera_roll/SceneCameraPack.hpp"
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;
namespace fs = std::filesystem;
using Json = nlohmann::ordered_json;

namespace {
class AssetBackend {
public:
    ContentHandle image(const ImageRequest& request) {
        std::ifstream input(request.path, std::ios::binary);
        unsigned char header[24]{};
        if (!input.read(reinterpret_cast<char*>(header), sizeof(header)) ||
            header[0] != 0x89 || header[1] != 'P' || header[2] != 'N' || header[3] != 'G')
            throw std::runtime_error("expected a readable PNG asset: " + request.path);
        const auto be32 = [&](int offset) {
            return (static_cast<std::uint32_t>(header[offset]) << 24U) |
                   (static_cast<std::uint32_t>(header[offset + 1]) << 16U) |
                   (static_cast<std::uint32_t>(header[offset + 2]) << 8U) |
                   static_cast<std::uint32_t>(header[offset + 3]);
        };
        ContentHandle handle;
        handle.id = request.path;
        handle.wireId = next++;
        handle.kind = ContentKind::Image;
        handle.metrics.naturalSize = Vector2(static_cast<float>(be32(16)), static_cast<float>(be32(20)));
        handle.metrics.anchor = Vector2(0.f, 0.f);
        handle.metrics.fingerprint = std::to_string(fs::file_size(request.path));
        fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }
    ContentHandle text(const TextRequest& request) {
        return make("text/" + request.text, ContentKind::Text,
                    Vector2(request.fontSize * request.text.size() * .6f, request.fontSize * 1.3f));
    }
    ContentHandle video(const VideoRequest& request) {
        return make("video/" + request.path, ContentKind::Video, Vector2(1920.f, 1080.f));
    }
    ContentHandle shape(const ShapeRequest& request) {
        return make("shape/" + request.name, ContentKind::Image, request.size);
    }
    std::string fingerprint(const ContentId& id) const {
        const auto found = fingerprints.find(id);
        return found == fingerprints.end() ? std::string{} : found->second;
    }
private:
    std::uint64_t next{1};
    std::unordered_map<ContentId, std::string> fingerprints;
    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle handle;
        handle.id = std::move(id);
        handle.wireId = next++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = Vector2(.5f, .5f);
        handle.metrics.fingerprint = "beast-land-reframe-v1:" + handle.id;
        fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }
};
}

int main(int argc, char** argv) {
    try {
        if (argc < 3) throw std::runtime_error("usage: emitter <asset-dir> <plan.json> [preview|video]");
        const fs::path assets = fs::absolute(argv[1]);
        const fs::path destination = fs::absolute(argv[2]);
        const std::string plateAsset = fs::relative(assets / "beast_land_plate.png",
                                                     assets.parent_path()).generic_string();
        const std::string presenterAsset = fs::relative(assets / "mrbeast_cutout_clean.png",
                                                         assets.parent_path()).generic_string();
        const bool preview = argc < 4 || std::string(argv[3]) == "preview";
        if (argc >= 4 && !preview && std::string(argv[3]) != "video")
            throw std::runtime_error("mode must be preview or video");
        fs::create_directories(destination.parent_path());

        constexpr float fps = 30.f;
        const float width = preview ? 854.f : 1920.f;
        const float height = preview ? 480.f : 1080.f;
        const float scaleX = width / 854.f, scaleY = height / 480.f;
        constexpr int wideHold = 75, travel = 54, closeHold = 45;
        AssetBackend backend;
        class Host final : public ContentHost {
        public:
            explicit Host(AssetBackend& value) : backend(value) {}
            ContentHandle createText(const TextRequest& r) override { return backend.text(r); }
            ContentHandle createImage(const ImageRequest& r) override { return backend.image(r); }
            ContentHandle createVideo(const VideoRequest& r) override { return backend.video(r); }
            ContentHandle createShape(const ShapeRequest& r) override { return backend.shape(r); }
            std::string currentFingerprint(const ContentId& id) const override { return backend.fingerprint(id); }
            AssetBackend& backend;
        } host(backend);
        TemplateScene scene("beast_land_subject_reframe_v1", fps, host, width, height);

        ImageSpec plate;
        plate.path = (assets / "beast_land_plate.png").string();
        plate.name = "Beast Land background plate";
        plate.fit = ImageFitMode::Stretch;
        plate.targetSize = Vector2(width * 2.40f, height * 2.40f);
        auto& background = scene.image(plate);
        background.position(width * .5f, height * .5f, -180.f)
                  .anchor(836.f, 470.5f)
                  .scale((width * 2.40f) / 1672.f);

        ImageSpec presenter;
        presenter.path = (assets / "mrbeast_cutout_clean.png").string();
        presenter.name = "MrBeast foreground cutout";
        presenter.fit = ImageFitMode::Contain;
        presenter.targetSize = Vector2(618.f * scaleX, 471.f * scaleY);
        auto& subject = scene.image(presenter);
        subject.position(width * .5f, 245.f * scaleY, 0.f)
               .anchor(605.f, 461.f)
               .scale((618.f / 1210.f) * scaleX);

        const SceneSubject measured = sceneSubjectFromLayer(scene, subject, SubjectKind::Image);
        const SceneSubject closeFace{
            SubjectKind::Image,
            Vector3(measured.center.x + 5.f * scaleX, height * .5f + 50.f * scaleY, measured.center.z),
            measured.halfWidth * .50f,
            measured.halfHeight * .55f};
        applySceneCameraSequence(scene, SceneCameraSequence{
            .beats = {{measured, wideHold}, {closeFace, closeHold}},
            .transition = SceneCameraTransition::OrbitHandoff,
            .intensity = .82f,
            .travelFrames = travel,
            .inFrame = 0});

        if (const auto problems = scene.validate(); !problems.empty())
            throw std::runtime_error("scene validation failed: " + problems.front());
        const int duration = preview ? 1 : wideHold + travel + closeHold;
        // Motion cameras look down -Z; RenderPlan camera-backed projection
        // looks down +Z. Match Motion's canonical lowering: mirror camera Z
        // and invert its orientation at this boundary.
        auto eulerDegrees = [](Quaternion q) {
            constexpr float radToDeg = 57.29577951308232f;
            q.invert();
            const float x = std::atan2(2.f * (q.w * q.x - q.y * q.z),
                                       1.f - 2.f * (q.x * q.x + q.y * q.y));
            const float s = std::clamp(2.f * (q.w * q.y + q.z * q.x), -1.f, 1.f);
            const float y = std::asin(s);
            const float z = std::atan2(2.f * (q.w * q.z - q.x * q.y),
                                       1.f - 2.f * (q.y * q.y + q.z * q.z));
            return Vector3(x * radToDeg, y * radToDeg, z * radToDeg);
        };
        const auto firstPose = scene.cameraRig().sample(0.f);
        Json cameraTracks = Json::array();
        const char* properties[] = {"camera_position_x", "camera_position_y", "camera_position_z",
                                    "camera_rotation_x", "camera_rotation_y", "camera_rotation_z",
                                    "camera_fov_deg"};
        Json keys[7] = {Json::array(), Json::array(), Json::array(), Json::array(),
                        Json::array(), Json::array(), Json::array()};
        for (int frame = 0; frame < duration; ++frame) {
            const auto pose = scene.cameraRig().sample(static_cast<float>(frame) / fps);
            const Vector3 rotation = eulerDegrees(pose.orientation);
            // TemplateScene expresses camera X/Y in canvas coordinates with
            // the origin at the upper-left. RenderPlan's camera origin is at
            // the canvas center, as in the other camera-pack emitters.
            const double values[] = {pose.position.x - width * .5,
                                     pose.position.y - height * .5,
                                     -pose.position.z,
                                     rotation.x, rotation.y, rotation.z, pose.fov};
            for (int channel = 0; channel < 7; ++channel)
                keys[channel].push_back({{"frame", frame}, {"value", values[channel]}});
        }
        for (int channel = 0; channel < 7; ++channel)
            cameraTracks.push_back({{"property", properties[channel]}, {"easing", "linear"},
                                    {"keyframes", std::move(keys[channel])}});
        Json outputSpec = {{"path", preview
            ? (destination.parent_path() / "beast_land_subject_preview.png").string()
            : (destination.parent_path() / "beast_land_subject_reframe.mp4").string()},
            {"format", preview ? "png" : "mp4"}};
        Json plan = {
            {"schema", "chronon.render-plan.v3"}, {"version", 3},
            {"job_id", "beast_land_subject_reframe_v1"},
            {"canvas", {{"width", static_cast<int>(width)}, {"height", static_cast<int>(height)},
                        {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", duration}}},
            {"camera", {{"type", "perspective"},
                         {"position", {firstPose.position.x - width * .5,
                                        firstPose.position.y - height * .5,
                                        -firstPose.position.z}},
                         {"rotation_deg", {eulerDegrees(firstPose.orientation).x,
                                           eulerDegrees(firstPose.orientation).y,
                                           eulerDegrees(firstPose.orientation).z}},
                         {"fov_deg", firstPose.fov}, {"near", 1.0}, {"far", 10000.0}, {"zoom", 1.0}}},
            {"camera_animation", {{"tracks", std::move(cameraTracks)}}},
            {"layers", Json::array({
                {{"id", "beast_land_background"}, {"type", "image"}, {"asset", plateAsset},
                {"size", {width * 2.40f, height * 2.40f}},
                 {"position", {0.f, 0.f, 180.f}},
                 {"scale", {2.2f, 2.2f, 1.f}},
                 {"fit", "cover"}, {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", duration}},
                {{"id", "mrbeast_foreground"}, {"type", "image"}, {"asset", presenterAsset},
                 {"size", {618.f * scaleX, 471.f * scaleY}},
                 {"position", {0.f, 245.f * scaleY - height * .5f - 52.5f * scaleY, 0.f}},
                 {"scale", {1.2f, 1.2f, 1.f}},
                 {"fit", "contain"}, {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", duration}}
            })},
            {"output", std::move(outputSpec)}
        };
        std::ofstream output(destination, std::ios::binary | std::ios::trunc);
        if (!output || !(output << plan.dump(2) << '\n'))
            throw std::runtime_error("could not write plan: " + destination.string());
        std::cout << "Wrote " << destination << " mode=" << (preview ? "preview" : "video")
                  << " layers=2 subject-bounds="
                  << measured.halfWidth * 2.f << 'x' << measured.halfHeight * 2.f << '\n';
    } catch (const std::exception& e) {
        std::cerr << "beast-land subject reframe: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
