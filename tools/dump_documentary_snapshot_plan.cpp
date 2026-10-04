#include "chronontemplate/DocumentarySnapshotPack.hpp"
#include "chronontemplate/RenderPlanContentHost.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"
#include <chronon3d/render_plan/effect_presets.hpp>

#include <algorithm>
#include <fstream>
#include <iostream>
#include <array>
#include <cmath>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;
using namespace chronon3d::render_plan;
using namespace chronon3d::render_plan::effect_presets::light_leak;

namespace {

class ArchivalAssetBackend {
public:
    ContentHandle text(const TextRequest& request) {
        return make("text/" + request.text, ContentKind::Text,
                    {request.fontSize * static_cast<float>(request.text.size()) * 0.65f,
                     request.fontSize * 1.25f});
    }

    ContentHandle image(const ImageRequest& request) {
        if (request.path != kPhoto)
            throw std::invalid_argument("unexpected image in documentary adapter canary: " + request.path);
        return make(request.path, ContentKind::Image, {1920.f, 1472.f});
    }

    ContentHandle video(const VideoRequest& request) {
        return make(request.path, ContentKind::Video, {1920.f, 1080.f});
    }

    ContentHandle shape(const ShapeRequest& request) {
        return make("shape/" + request.name, ContentKind::Image, request.size);
    }

    std::string fingerprint(const ContentId& id) const {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }

private:
    static constexpr const char* kPhoto = "RenderingGen/testdata/golden/gerard_butler.jpg";

    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle handle;
        handle.id = std::move(id);
        handle.wireId = m_nextWireId++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = {0.5f, 0.5f};
        handle.metrics.fingerprint = "documentary-adapter-canary-v1:" + handle.id;
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }

    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;
};

} // namespace

namespace {
std::array<float, 6> cameraPoseAt(const std::vector<CameraTrackPlan>& tracks, int frame) {
    std::array<float, 6> pose{};
    for (const auto& track : tracks) {
        std::size_t channel = 6;
        switch (track.property) {
            case CameraPropertyPlan::PositionX: channel = 0; break;
            case CameraPropertyPlan::PositionY: channel = 1; break;
            case CameraPropertyPlan::PositionZ: channel = 2; break;
            case CameraPropertyPlan::RotationX: channel = 3; break;
            case CameraPropertyPlan::RotationY: channel = 4; break;
            case CameraPropertyPlan::RotationZ: channel = 5; break;
            default: break;
        }
        if (channel == 6 || track.keyframes.empty()) continue;
        const auto upper = std::lower_bound(track.keyframes.begin(), track.keyframes.end(), frame,
            [](const AnimationKeyframePlan& key, int f) { return key.frame.integral() < f; });
        if (upper == track.keyframes.begin()) pose[channel] = upper->value.front();
        else if (upper == track.keyframes.end()) pose[channel] = track.keyframes.back().value.front();
        else {
            const auto& b = *upper;
            const auto& a = *(upper - 1);
            const float span = static_cast<float>(b.frame.integral() - a.frame.integral());
            const float t = span > 0.f ? (frame - a.frame.integral()) / span : 0.f;
            pose[channel] = a.value.front() + (b.value.front() - a.value.front()) * t;
        }
    }
    return pose;
}

void addCameraSynchronizedLeak(RenderPlan& plan, int durationFrames) {
    if (!plan.camera_animation) throw std::runtime_error("snapshot plan has no camera animation");
    const auto& tracks = *plan.camera_animation;
    std::vector<float> speed(static_cast<std::size_t>(durationFrames + 1), 0.f);
    float peakSpeed = 0.f;
    for (int frame = 1; frame <= durationFrames; ++frame) {
        const auto previous = cameraPoseAt(tracks, frame - 1);
        const auto current = cameraPoseAt(tracks, frame);
        const float dx = current[0] - previous[0];
        const float dy = current[1] - previous[1];
        const float dz = current[2] - previous[2];
        const float drx = (current[3] - previous[3]) * 0.01745329252f * 900.f;
        const float dry = (current[4] - previous[4]) * 0.01745329252f * 900.f;
        const float drz = (current[5] - previous[5]) * 0.01745329252f * 900.f;
        speed[static_cast<std::size_t>(frame)] = std::sqrt(
            dx*dx + dy*dy + dz*dz + drx*drx + dry*dry + drz*drz);
        peakSpeed = std::max(peakSpeed, speed[static_cast<std::size_t>(frame)]);
    }
    LightLeakProfile profile;
    profile.shape = LightLeakShape::Edge;
    profile.edge = LightLeakEdge::Top;
    profile.color_a = kWarmTint;
    profile.color_b = kAmberTint;
    profile.intensity = 0.28f;
    profile.softness = 0.f;
    profile.spread = 0.48f;
    profile.position = 0.56f;
    profile.grain = 0.0f;
    auto leak = LightLeakResolver::resolve(profile, {1920.f, 1080.f}, "documentary-motion-light-leak");
    AnimationPlan animation;
    AnimationTrackPlan opacity;
    opacity.property = "opacity";
    opacity.easing = "linear";
    for (int frame = 0; frame <= durationFrames; ++frame) {
        float normalized = peakSpeed > 1e-6f ? speed[static_cast<std::size_t>(frame)] / peakSpeed : 0.f;
        const float settleFade = std::clamp((durationFrames - frame) / 2.f, 0.f, 1.f);
        normalized *= settleFade;
        AnimationKeyframePlan key;
        key.frame = chronon3d::Frame(static_cast<float>(frame));
        key.value = {std::clamp(normalized * normalized, 0.f, 1.f)};
        opacity.keyframes.push_back(std::move(key));
    }
    animation.tracks.push_back(std::move(opacity));
    leak.animation = std::move(animation);
    plan.layers.push_back(std::move(leak));
}

void finalizeTortureFocusTrack(TemplateScene& scene, int durationFrames,
                               int focusDropStart, int focusDropEnd) {
    auto& rig = scene.camera().rig();
    const Track<float> authoredFocus = rig.focusDistanceTrack();
    std::vector<std::pair<float, float>> samples;
    samples.reserve(static_cast<std::size_t>(durationFrames + 1));
    for (int frame = 0; frame <= durationFrames; ++frame) {
        const float time = static_cast<float>(frame) / scene.fps();
        const CameraPose pose = rig.sample(time);
        // FocusDrop intentionally racks across the title and photo depth
        // planes. Other shots focus on their resolved camera target. Rebuild
        // after all twelve camera paths have been authored so later paths
        // cannot leave stale focus samples at shared shot boundaries.
        float distance = frame >= focusDropStart && frame <= focusDropEnd
            ? authoredFocus.sample(time)
            : pose.position.distanceTo(pose.target);
        Vector3 forward(0.f, 0.f, -1.f);
        forward.applyQuaternion(pose.orientation);
        forward.normalize();
        const float focusPlaneZ = pose.position.z + forward.z * distance;
        if (focusPlaneZ > 0.f) {
            if (std::fabs(forward.z) <= 1e-4f)
                throw std::runtime_error("documentary torture focus cannot reach the supported scene depth");
            // RenderPlan's current DOF contract models a non-negative world-Z
            // focus plane. The title is authored on z=0, so keep tiny camera
            // target overshoot on the visible side of that title plane.
            distance = (-0.001f - pose.position.z) / forward.z;
        }
        if (!std::isfinite(distance) || distance <= 0.f)
            throw std::runtime_error("documentary torture sequence produced an invalid focus distance");
        samples.emplace_back(time, distance);
    }
    auto& focus = rig.focusDistanceTrack();
    focus.clear();
    for (const auto& [time, distance] : samples)
        focus.add(time, distance, Easing::linear());
}
} // namespace

int main(int argc, char** argv) {
    const std::string output = argc > 1 ? argv[1] : "/tmp/documentary_snapshot_adapter_canary.plan.json";
    ArchivalAssetBackend backend;
    RenderPlanContentHost host({
        .createText = [&](const TextRequest& request) { return backend.text(request); },
        .createImage = [&](const ImageRequest& request) { return backend.image(request); },
        .createVideo = [&](const VideoRequest& request) { return backend.video(request); },
        .createShape = [&](const ShapeRequest& request) { return backend.shape(request); },
        .currentFingerprint = [&](const ContentId& id) { return backend.fingerprint(id); }});

    constexpr int fps = 30;
    const bool torture = argc > 4 && std::string(argv[4]) == "torture";
    int duration = torture ? 600 : 120;
    TemplateScene scene("documentary_snapshot_adapter_canary", static_cast<float>(fps),
                        host, 1920.f, 1080.f);
    DocumentaryShot shot;
    shot.title = {Vector3(960.f, 300.f, 0.f), 820.f, 120.f};
    shot.snapshots = {{"RenderingGen/testdata/golden/gerard_butler.jpg",
                       {Vector3(960.f, 960.f, -80.f), 620.f, 350.f},
                       "ROME, 1986", SnapshotFit::Fit}};
    if (argc > 2) {
        const std::string fit = argv[2];
        if (fit == "fit") {
            shot.snapshots.front().fit = SnapshotFit::Fit;
        } else if (fit == "fill") {
            shot.snapshots.front().fit = SnapshotFit::Fill;
        } else if (fit == "crop") {
            shot.snapshots.front().fit = SnapshotFit::Crop;
            shot.snapshots.front().crop = {true, Vector2(0.14f, 0.08f),
                                            Vector2(0.72f, 0.84f)};
        } else {
            std::cerr << "snapshot fit must be fit, fill, or crop\n";
            return 2;
        }
    }
    if (argc > 3) {
        const std::string style = argv[3];
        if (style == "clean") shot.style = SnapshotStyle::Clean;
        else if (style == "archive") shot.style = SnapshotStyle::Archive;
        else if (style == "polaroid") shot.style = SnapshotStyle::Polaroid;
        else if (style == "filmstrip") shot.style = SnapshotStyle::Filmstrip;
        else if (style == "evidence") shot.style = SnapshotStyle::Evidence;
        else if (style == "newspaper") shot.style = SnapshotStyle::Newspaper;
        else if (style == "bw-documentary") shot.style = SnapshotStyle::BlackAndWhiteDocumentary;
        else {
            std::cerr << "snapshot style must be clean, archive, polaroid, filmstrip, evidence, newspaper, or bw-documentary\n";
            return 2;
        }
    }
    if (argc > 4) {
        const std::string recipe = argv[4];
        if (recipe == "torture") {
            // The 20-second canary puts all twelve native recipes into one
            // scene and one CameraRig, with each 50-frame shot following the
            // previous shot's declared end pose.
        } else if (recipe == "snap-down") shot.recipe = DocumentaryRecipe::SnapDown;
        else if (recipe == "pullback-reveal") shot.recipe = DocumentaryRecipe::PullbackReveal;
        else if (recipe == "push-through-snapshot") shot.recipe = DocumentaryRecipe::PushThroughSnapshot;
        else if (recipe == "whip-to-photo") shot.recipe = DocumentaryRecipe::WhipToPhoto;
        else if (recipe == "focus-drop") shot.recipe = DocumentaryRecipe::FocusDrop;
        else if (recipe == "reveal-90") shot.recipe = DocumentaryRecipe::Reveal90;
        else if (recipe == "corner-turn") shot.recipe = DocumentaryRecipe::CornerTurn;
        else if (recipe == "foreground-photo-pass") shot.recipe = DocumentaryRecipe::ForegroundPhotoPass;
        else if (recipe == "photo-stack") shot.recipe = DocumentaryRecipe::PhotoStack;
        else if (recipe == "filmstrip-handoff") shot.recipe = DocumentaryRecipe::FilmstripHandoff;
        else if (recipe == "split-depth") shot.recipe = DocumentaryRecipe::SplitDepth;
        else if (recipe == "archive-crane-reveal") shot.recipe = DocumentaryRecipe::ArchiveCraneReveal;
        else if (recipe != "torture") {
            std::cerr << "unsupported documentary recipe: " << recipe << '\n';
            return 2;
        }
        if (!torture && (shot.recipe == DocumentaryRecipe::PhotoStack ||
            shot.recipe == DocumentaryRecipe::FilmstripHandoff ||
            shot.recipe == DocumentaryRecipe::ArchiveCraneReveal)) {
            const auto asset = shot.snapshots.front();
            if (shot.recipe == DocumentaryRecipe::PhotoStack) {
                shot.snapshots = {
                    {asset.path, {Vector3(960.f, 960.f, -80.f), 620.f, 350.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(960.f, 960.f, -260.f), 620.f, 350.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(960.f, 960.f, -440.f), 620.f, 350.f}, "ROME, 1986", asset.fit}};
            } else if (shot.recipe == DocumentaryRecipe::FilmstripHandoff) {
                shot.snapshots = {
                    {asset.path, {Vector3(300.f, 960.f, -80.f), 280.f, 350.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(960.f, 960.f, -80.f), 280.f, 350.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(1620.f, 960.f, -80.f), 280.f, 350.f}, "ROME, 1986", asset.fit}};
            } else {
                shot.snapshots = {
                    {asset.path, {Vector3(430.f, 900.f, -80.f), 340.f, 240.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(960.f, 900.f, -110.f), 340.f, 240.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(1490.f, 900.f, -140.f), 340.f, 240.f}, "ROME, 1986", asset.fit}};
            }
        }
    }
    if (!torture && shot.recipe == DocumentaryRecipe::FocusDrop) {
        // This canary presents both depth planes at the opening. RenderPlan's
        // projected Y grows upward, so place the snapshot below the title.
        shot.snapshots.front().anchor.center.y =
            shot.title.center.y - shot.title.halfHeight -
            shot.snapshots.front().anchor.halfHeight - 180.f;
    }
    if (!torture && shot.recipe == DocumentaryRecipe::Reveal90)
        shot.snapshots.front().anchor.center.y = shot.title.center.y;
    const auto addShot = [&](const DocumentaryShot& authored, const std::string& titleText) {
        addDocumentarySnapshot(scene,
            TextSpec{.text = titleText,
                     .font = "ChrononTemplate/assets/fonts/didone_font_playfair_display_italic.ttf",
                     .fontSize = 138.f, .color = "#F1EBDD", .name = "DocumentaryTitle"},
            authored);
    };
    std::string recipeId;
    std::string styleId;
    if (torture) {
        const std::array<DocumentaryRecipe, 12> recipes{
            DocumentaryRecipe::SnapDown, DocumentaryRecipe::PullbackReveal,
            DocumentaryRecipe::PushThroughSnapshot, DocumentaryRecipe::WhipToPhoto,
            DocumentaryRecipe::FocusDrop, DocumentaryRecipe::Reveal90,
            DocumentaryRecipe::CornerTurn, DocumentaryRecipe::ForegroundPhotoPass,
            DocumentaryRecipe::PhotoStack, DocumentaryRecipe::FilmstripHandoff,
            DocumentaryRecipe::SplitDepth, DocumentaryRecipe::ArchiveCraneReveal};
        const std::array<const char*, 12> titles{
            "THE STORY OF ROME", "A CITY IN TRANSITION", "THE MOMENT OF CHANGE",
            "THE WITNESS", "THE ARCHIVE REMEMBERS", "A NEW PERSPECTIVE",
            "BEYOND THE HEADLINE", "THE HUMAN STORY", "THREE MOMENTS",
            "A STRIP OF HISTORY", "PAST AND PRESENT", "THE COMPLETE RECORD"};
        for (std::size_t i = 0; i < recipes.size(); ++i) {
            DocumentaryShot authored = shot;
            authored.recipe = recipes[i];
            authored.style = static_cast<SnapshotStyle>(i % snapshotStyleIds().size());
            authored.inFrame = static_cast<int>(i) * 50;
            authored.duration = 50;
            authored.titleHoldFrames = 22;
            authored.transitionFrames = 8;
            authored.title = {Vector3(960.f, 280.f, 0.f), 820.f, 120.f};
            authored.snapshots.front().anchor = {Vector3(960.f, 900.f, -80.f), 620.f, 350.f};
            const auto asset = authored.snapshots.front();
            if (recipes[i] == DocumentaryRecipe::PhotoStack) {
                authored.snapshots = {
                    {asset.path, {Vector3(960.f, 900.f, -80.f), 620.f, 350.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(960.f, 900.f, -260.f), 620.f, 350.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(960.f, 900.f, -440.f), 620.f, 350.f}, "ROME, 1986", asset.fit}};
            } else if (recipes[i] == DocumentaryRecipe::FilmstripHandoff) {
                authored.snapshots = {
                    {asset.path, {Vector3(300.f, 900.f, -80.f), 280.f, 350.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(960.f, 900.f, -80.f), 280.f, 350.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(1620.f, 900.f, -80.f), 280.f, 350.f}, "ROME, 1986", asset.fit}};
            } else if (recipes[i] == DocumentaryRecipe::ArchiveCraneReveal) {
                authored.snapshots = {
                    {asset.path, {Vector3(430.f, 840.f, -80.f), 340.f, 240.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(960.f, 840.f, -110.f), 340.f, 240.f}, "ROME, 1986", asset.fit},
                    {asset.path, {Vector3(1490.f, 840.f, -140.f), 340.f, 240.f}, "ROME, 1986", asset.fit}};
            }
            addShot(authored, titles[i]);
        }
        recipeId = "documentary_title_snapshot_torture";
        styleId = "seven_styles";
        finalizeTortureFocusTrack(scene, duration, 4 * 50, 4 * 50 + 50);
    } else {
        shot.duration = duration;
        shot.titleHoldFrames = 45;
        shot.transitionFrames = 8;
        addShot(shot, "THE STORY OF ROME");
        styleId = snapshotStyleId(shot.style);
        recipeId = documentaryRecipeId(shot.recipe);
    }

    auto plan = lowerToRenderPlan(scene, host,
        "documentary_snapshot_adapter_" + recipeId + "_" + styleId + "_v1",
        "documentary_snapshot_adapter_" + recipeId + "_" + styleId + "_v1.mp4");
    addCameraSynchronizedLeak(plan, duration);
    plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;
    std::ofstream file(output, std::ios::binary | std::ios::trunc);
    if (!file || !(file << chrononmotion::motion::renderPlanToJson(plan))) {
        std::cerr << "failed to write RenderPlan: " << output << '\n';
        return 1;
    }
    std::cout << "Wrote adapter-lowered plan " << output << " with " << plan.layers.size()
              << " layers and " << duration + 1 << " frames\n";
    return 0;
}
