// Emits the 1080p GEL cinematic title through the canonical Template lowering.
//
// Usage:
//   chronontemplate_emit_gel_cinematic_title <out.plan.json> [plate] [font] [out.mp4]
//
// Asset paths are resolved by chronon3d_cli against its --assets-root. The
// defaults point at the reference plate and the pinned Liberation Mono Bold in
// the Chronon3d evidence tree.

#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/gel/GelCinematicTitlePack.hpp"
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
    constexpr int kFrames = 300;

    class MeasureBackend {
    public:
        ContentHandle text(const TextRequest& request) {
            return make("text/" + request.text, ContentKind::Text,
                        {request.fontSize * 0.62f * static_cast<float>(request.text.size()) + 8.f,
                         request.fontSize * 1.25f});
        }
        ContentHandle image(const ImageRequest& request) {
            const Vector2 size = (request.targetSize.x > 0.f && request.targetSize.y > 0.f)
                                     ? request.targetSize
                                     : Vector2(kWidth, kHeight);
            return make(request.path, ContentKind::Image, size);
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
            handle.metrics.fingerprint = "gel-cinematic-title-v1:" + handle.id;
            m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
            return handle;
        }

        std::uint64_t m_nextWireId{1};
        std::unordered_map<ContentId, std::string> m_fingerprints;
    };

}// namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: chronontemplate_emit_gel_cinematic_title "
                     "<out.plan.json> [plate] [font] [out.mp4]\n";
        return 2;
    }
    const std::filesystem::path output = argv[1];
    const std::string plate = argc > 2
        ? argv[2]
        : "docs/evidence/gel-cinematic-title-1080p-revision-20261107/plate_full_frame.png";
    const std::string font = argc > 3
        ? argv[3]
        : "docs/evidence/gel-reference-camera-20261106/LiberationMono-Bold.ttf";
    const std::string video = argc > 4 ? argv[4] : "output/gel_cinematic_title_1080p.mp4";

    try {
        MeasureBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& request) { return backend.text(request); },
            .createImage = [&](const ImageRequest& request) { return backend.image(request); },
            .createVideo = [&](const VideoRequest& request) { return backend.video(request); },
            .createShape = [&](const ShapeRequest& request) { return backend.shape(request); },
            .currentFingerprint = [&](const ContentId& id) { return backend.fingerprint(id); }});

        TemplateScene scene("gel-cinematic-title", kFps, host, kWidth, kHeight);
        scene.camera().setFov(55.f);

        gel::GelCinematicTitleSpec spec;
        spec.name = "gel_cinematic_title";
        spec.plate = plate;
        spec.plateFit = ImageFitMode::Stretch;
        spec.font = font;
        spec.fontSize = 125.f;
        // Reference word centres scaled from the 1094x143 strip to 1920x1080.
        spec.words = {
            {.text = "calories", .x = 382.f, .y = 540.f, .scale = 1.f},
            {.text = "or", .x = 813.f, .y = 540.f, .scale = 1.f},
            {.text = "ingredients", .x = 1408.f, .y = 540.f, .scale = 1.f}};
        spec.inFrame = 0;
        spec.durationFrames = kFrames - 1;
        spec.pushScale = 1.04f;
        (void)gel::addGelCinematicTitle(scene, spec);

        auto plan = lowerToRenderPlan(scene, host, "gel_cinematic_title_1080p", video);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;

        if (!output.parent_path().empty())
            std::filesystem::create_directories(output.parent_path());
        std::ofstream file(output, std::ios::binary | std::ios::trunc);
        if (!file || !(file << renderPlanToJson(plan)))
            throw std::runtime_error("failed to write RenderPlan: " + output.string());
        std::cout << "Wrote " << output << " (" << plan.layers.size() << " layers)\n";
    } catch (const std::exception& e) {
        std::cerr << "emit_gel_cinematic_title: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
