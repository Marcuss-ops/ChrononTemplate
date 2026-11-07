// ChrononTemplate — native heterogeneous group-animation showcase.
//
// Emits five chronon.render-plan.v3 documents from the C++ GroupAnimationPack:
// one master with all five roles (important_phrase, image, caption, date, metric)
// and four two-member clips that isolate image/caption/date/metric next to the
// phrase. Every clip is 1920x1080 and at most ten seconds at 30 fps.
//
// Usage:
//   chronontemplate_emit_group_animation_showcase <output-directory>

#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/group_animation/GroupAnimationPack.hpp"

#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <chronon3d/render_plan/render_plan_core.hpp>

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

    using json = nlohmann::ordered_json;
    using namespace chronontemplate;
    using chrononmotion::Vector2;
    using chrononmotion::motion::ContentKind;

    class AssetBackend final : public ContentHost {
    public:
        ContentHandle createText(const TextRequest& request) override {
            // Keep the measured box wider than the glyphs: the renderer wraps on
            // this box, and a tight estimate breaks words apart.
            const float width = std::max(1.f, request.fontSize * 0.8f *
                                                 static_cast<float>(request.text.size()) + 24.f);
            return make("text/" + request.text + "@" + std::to_string(static_cast<int>(request.fontSize)),
                        ContentKind::Text, Vector2(width, request.fontSize * 1.3f));
        }

        ContentHandle createImage(const ImageRequest& request) override {
            // The renderer consumes this id as the logical asset path, not as a
            // namespaced content handle: keep it asset-root-relative. Honour the
            // requested box so the portrait is laid out at its authored size.
            const Vector2 natural = request.targetSize.x > 0.f && request.targetSize.y > 0.f
                    ? request.targetSize
                    : Vector2(640.f, 360.f);
            return make(request.path, ContentKind::Image, natural);
        }

        ContentHandle createVideo(const VideoRequest& request) override {
            return make(request.path, ContentKind::Video, Vector2(1920.f, 1080.f));
        }

        ContentHandle createShape(const ShapeRequest& request) override {
            return make("shape/" + request.name + "/" + request.fillColor,
                        ContentKind::Image, request.size);
        }

        std::string currentFingerprint(const ContentId& content) const override {
            const auto found = fingerprints.find(content);
            return found == fingerprints.end() ? std::string{} : found->second;
        }

    private:
        ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
            ContentHandle handle;
            handle.id = std::move(id);
            handle.wireId = nextWireId++;
            handle.kind = kind;
            handle.metrics.naturalSize = size;
            handle.metrics.anchor = Vector2(0.5f, 0.5f);
            handle.metrics.fingerprint = "group-animation-showcase:" + handle.id;
            fingerprints[handle.id] = handle.metrics.fingerprint;
            return handle;
        }

        std::uint64_t nextWireId{1};
        std::unordered_map<ContentId, std::string> fingerprints{};
    };

    void writeFile(const std::filesystem::path& path, const std::string& contents) {
        std::ofstream output(path, std::ios::binary | std::ios::trunc);
        if (!output || !(output << contents)) {
            throw std::runtime_error("could not write " + path.string());
        }
    }

    json memberJson(const GroupAnimationSpec& spec) {
        json members = json::array();
        for (const GroupMemberTiming& member : groupShowcaseTimeline(spec)) {
            members.push_back({{"role", groupRoleId(member.role)},
                               {"offset_frames", member.offsetFrames},
                               {"enter_frames", member.enterFrames}});
        }
        return members;
    }

    int memberOffsetFrames(const GroupAnimationSpec& spec, GroupRole role) {
        for (const GroupMemberTiming& member : groupShowcaseTimeline(spec)) {
            if (member.role == role) return member.offsetFrames;
        }
        return 0;
    }

    chronon3d::render_plan::AnimationKeyframePlan scalarKey(int frame, float value) {
        chronon3d::render_plan::AnimationKeyframePlan key;
        key.frame = chronon3d::Frame(frame);
        key.value = {value};
        return key;
    }

    /// The flat 2D showcase uses no scene camera. Resolved samples already
    /// carry screen-space transforms, so text and shapes keep their lowered
    /// samples; images are re-centred to the renderer's centre-relative image
    /// convention and re-animated with ordinary keyframe tracks.
    void adaptForFlatShowcase(chronon3d::render_plan::RenderPlan& plan,
                              const GroupAnimationSpec& spec) {
        constexpr int kExitFrames = 22;
        constexpr int kExitDuration = 16;
        plan.camera.reset();
        plan.camera_samples.reset();

        for (auto& layer : plan.layers) {
            if (layer.style) layer.style->glow.reset();

            if (layer.type != chronon3d::render_plan::LayerType::Image) continue;

            if (layer.transform_samples.empty()) {
                // Static editorial image (the caption clip's context portrait):
                // convert the absolute box to the centre-relative convention.
                layer.position[0] -= 960.f;
                layer.position[1] -= 540.f;
                layer.enable_3d = true;
                continue;
            }

            const std::size_t restIndex = std::min<std::size_t>(
                    layer.transform_samples.size() - 1,
                    static_cast<std::size_t>(spec.durationFrames / 2));
            const auto rest = layer.transform_samples[restIndex];
            const float restX = rest.position[0] - 960.f;
            const float restY = rest.position[1] - 540.f;

            layer.transform_samples.clear();
            layer.enable_3d = true;
            layer.position = {restX, restY, rest.position[2]};
            layer.opacity = 1.f;

            const int offset = memberOffsetFrames(spec, GroupRole::Image);
            chronon3d::render_plan::AnimationTrackPlan fade;
            fade.property = "opacity";
            fade.easing = "linear";
            fade.keyframes = {
                    scalarKey(offset, 0.f),
                    scalarKey(offset + spec.enterFrames, 1.f),
                    scalarKey(spec.durationFrames - kExitFrames, 1.f),
                    scalarKey(spec.durationFrames - kExitDuration, 0.f)};

            chronon3d::render_plan::AnimationTrackPlan slide;
            slide.property = "position_y";
            slide.easing = "linear";
            slide.keyframes = {
                    scalarKey(offset, restY + 52.f),
                    scalarKey(offset + spec.enterFrames, restY)};

            layer.animation = chronon3d::render_plan::AnimationPlan{.tracks = {std::move(fade), std::move(slide)}};
        }
    }

}// namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_emit_group_animation_showcase <output-directory>\n";
        return 2;
    }
    try {
        const std::filesystem::path outDir = argv[1];
        std::filesystem::create_directories(outDir);

        json manifest = {
                {"schema", "chronontemplate.group-animation-showcase.v1"},
                {"pipeline", "ChrononTemplate C++ GroupAnimationPack -> chronon.render-plan.v3 -> Chronon3D"},
                {"choreography", "sequence_v1"},
                {"canvas", {{"width", 1920}, {"height", 1080}, {"fps", 30}, {"max_duration_frames", 300}}},
                {"roles", json::array({"important_phrase", "image", "caption", "date", "metric"})},
                {"clips", json::array()}};

        for (const GroupAnimationSpec& spec : groupAnimationShowcaseSpecs()) {
            AssetBackend backend;
            RenderPlanContentHost host({
                    .createText = [&](const TextRequest& request) { return backend.createText(request); },
                    .createImage = [&](const ImageRequest& request) { return backend.createImage(request); },
                    .createVideo = [&](const VideoRequest& request) { return backend.createVideo(request); },
                    .createShape = [&](const ShapeRequest& request) { return backend.createShape(request); },
                    .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }});

            TemplateScene scene(spec.id, static_cast<float>(spec.fps), host, 1920.f, 1080.f);
            buildGroupAnimationShowcase(scene, spec);
            const std::vector<std::string> errors = scene.validate();
            if (!errors.empty()) {
                throw std::runtime_error(spec.id + ": " + errors.front());
            }

            auto plan = lowerToRenderPlan(scene, host, spec.id, spec.id + ".mp4");
            plan.canvas.duration = chronon3d::Frame(spec.durationFrames);
            for (auto& layer : plan.layers) {
                if (layer.duration_frames) layer.duration_frames = chronon3d::Frame(spec.durationFrames);
                // Lowered group children carry frame 0 (transparent) as their
                // static opacity. The renderer materializes with that value, so
                // keep the layer visible and let the resolved samples drive the
                // actual fade. A fully transparent first frame stays transparent.
                if (!layer.transform_samples.empty()) {
                    float peakOpacity = 0.f;
                    for (const auto& sample : layer.transform_samples) {
                        peakOpacity = std::max(peakOpacity, sample.opacity);
                    }
                    layer.opacity = peakOpacity;
                }
            }
            adaptForFlatShowcase(plan, spec);
            plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;

            const std::string planName = spec.id + ".plan.json";
            writeFile(outDir / planName,
                      chrononmotion::motion::renderPlanToJson(plan) + "\n");

            manifest["clips"].push_back({
                    {"id", spec.id},
                    {"title", spec.title},
                    {"mode", groupShowcaseModeId(spec.mode)},
                    {"plan", planName},
                    {"render", spec.id + ".mp4"},
                    {"duration_frames", spec.durationFrames},
                    {"fps", spec.fps},
                    {"members", memberJson(spec)}});
            std::cout << "emitted " << planName << " (" << spec.durationFrames << " frames, "
                      << plan.layers.size() << " layers)\n";
        }
        writeFile(outDir / "manifest.json", manifest.dump(2) + "\n");
        std::cout << "emitted " << manifest["clips"].size() << " group-animation plans in "
                  << outDir.string() << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "emit_group_animation_showcase: " << error.what() << "\n";
        return 1;
    }
}
