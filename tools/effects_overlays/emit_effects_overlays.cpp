// Emits one RenderPlan per "Effects" overlay on a white 1920x1080 background,
// 5 seconds at 30 fps. Rendering is done by chronon3d_cli from the plans.
// Usage: chronontemplate_emit_effects_overlays <output-directory>
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/effects/EffectsPack.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;

namespace {

constexpr float kWidth = 1920.f;
constexpr float kHeight = 1080.f;
constexpr float kFps = 30.f;
constexpr int kFrames = 150;  // 5 s at 30 fps

class SampleAssetBackend {
public:
    ContentHandle text(const TextRequest& request) {
        return make("text/" + request.text, ContentKind::Text,
                    {request.fontSize * static_cast<float>(request.text.size()) * 0.65f,
                     request.fontSize * 1.25f});
    }

    ContentHandle image(const ImageRequest& request) {
        return make(request.path, ContentKind::Image, {kWidth, kHeight});
    }

    ContentHandle video(const VideoRequest& request) {
        return make(request.path, ContentKind::Video, {kWidth, kHeight});
    }

    ContentHandle shape(const ShapeRequest& request) {
        return make("shape/" + request.name, ContentKind::Image, request.size);
    }

    std::string fingerprint(const ContentId& id) const {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }

private:
    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle handle;
        handle.id = std::move(id);
        handle.wireId = m_nextWireId++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = {0.5f, 0.5f};
        handle.metrics.fingerprint = "effects-overlays-v2:" + handle.id;
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }

    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;
};

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: chronontemplate_emit_effects_overlays <output-directory>\n";
        return 2;
    }
    const std::filesystem::path outDir = argv[1];

    try {
        std::filesystem::create_directories(outDir);
        for (std::size_t index = 0; index < effects::effectCount(); ++index) {
            const auto kind = static_cast<effects::EffectKind>(index);
            const std::string name = effects::effectName(kind);

            SampleAssetBackend backend;
            RenderPlanContentHost host({
                .createText = [&](const TextRequest& request) { return backend.text(request); },
                .createImage = [&](const ImageRequest& request) { return backend.image(request); },
                .createVideo = [&](const VideoRequest& request) { return backend.video(request); },
                .createShape = [&](const ShapeRequest& request) { return backend.shape(request); },
                .currentFingerprint = [&](const ContentId& id) { return backend.fingerprint(id); }});

            TemplateScene scene("effect_" + name, kFps, host, kWidth, kHeight);
            // The default 55-degree camera sees a slightly larger area than
            // the canvas (1998x1124), leaving a black padding border. A 53.14
            // fov frames exactly 1920x1080 so the white card fills the frame.
            scene.camera().setFov(53.14f);

            // White background first, so the overlay is composited over it.
            ShapeSpec background{};
            background.size = Vector2(kWidth, kHeight);
            background.fillColor = "#FFFFFF";
            background.name = "white_background";
            scene.shape(background).position(kWidth / 2.f, kHeight / 2.f).alive(0, kFrames - 1);

            effects::EffectSpec spec{};
            spec.intensity = 1.f;
            spec.opacity = 1.f;
            spec.seed = 1u + static_cast<std::uint32_t>(index);
            spec.startFrame = 0;
            spec.endFrame = kFrames - 1;
            (void)effects::addEffect(scene, kind, spec);

            const std::string mp4 = (outDir / (name + ".mp4")).string();
            auto plan = lowerToRenderPlan(scene, host, "effect_" + name, mp4);
            plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;

            const std::string output = (outDir / (name + ".plan.json")).string();
            std::ofstream file(output, std::ios::binary | std::ios::trunc);
            if (!file || !(file << renderPlanToJson(plan))) {
                throw std::runtime_error("failed to write RenderPlan: " + output);
            }
            std::cout << "Wrote " << output << " (" << plan.layers.size() << " layers)\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "emit_effects_overlays: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
