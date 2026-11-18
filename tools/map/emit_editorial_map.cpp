// Lowers one chrononplugin.editorial-map-scene.v1 document to a RenderPlan.
// The DTO already carries canvas-space rings, hatch segments, pins and labels:
// this tool does not read GeoJSON, project coordinates or touch OpenCV.
//
//   chronontemplate_emit_editorial_map <scene.json> [out.plan.json]
//
// Render a proof frame with:
//   chronon3d_cli render --plan <out.plan.json>
//     --assets-root "$PWD/ChrononTemplate" --frame 180 --output <frame.png>

#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/map/EditorialMapPack.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using chrononmotion::Vector2;
using chrononmotion::motion::ContentKind;

namespace {

class PlanBackend final : public ContentHost {
public:
    PlanBackend(float width, float height) : m_width(width), m_height(height) {}

    ContentHandle createText(const TextRequest& request) override {
        return make("text/" + request.text, ContentKind::Text,
                    {request.fontSize * 0.6f * static_cast<float>(request.text.size()),
                     request.fontSize * 1.25f});
    }
    ContentHandle createImage(const ImageRequest& request) override {
        return make(request.path, ContentKind::Image, {m_width, m_height});
    }
    ContentHandle createVideo(const VideoRequest& request) override {
        return make("video/" + request.path, ContentKind::Video, {m_width, m_height});
    }
    ContentHandle createShape(const ShapeRequest& request) override {
        return make("shape/" + request.name, ContentKind::Image, request.size);
    }
    std::string currentFingerprint(const ContentId& id) const override {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }

private:
    float m_width;
    float m_height;
    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;

    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle handle;
        handle.id = std::move(id);
        handle.wireId = m_nextWireId++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = Vector2(0.5f, 0.5f);
        handle.metrics.fingerprint = "editorial-map:" + handle.id;
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }
};

}  // namespace

int main(int argc, char** argv) {
    const std::string scenePath =
        argc > 1 ? argv[1] : ".tmp/editorial-scenes/editorial_vox.scene.json";
    const std::string outPath =
        argc > 2 ? argv[2] : "ChrononTemplate/out/editorial_maps/editorial_map.plan.json";
    try {
        const EditorialMapScene spec = loadEditorialMapScene(scenePath);
        std::filesystem::path path(outPath);
        if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path());

        PlanBackend backend(spec.canvas.x, spec.canvas.y);
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& request) { return backend.createText(request); },
            .createImage = [&](const ImageRequest& request) { return backend.createImage(request); },
            .createVideo = [&](const VideoRequest& request) { return backend.createVideo(request); },
            .createShape = [&](const ShapeRequest& request) { return backend.createShape(request); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); },
        });

        TemplateScene scene("editorial_map_" + spec.style, spec.fps, host,
                            spec.canvas.x, spec.canvas.y);
        const EditorialMapComposition composition = addEditorialMap(scene, spec);

        auto plan = lowerToRenderPlan(scene, host, "editorial_map_" + spec.style,
                                      "editorial_map_" + spec.style + ".mp4");
        plan.canvas.duration = chronon3d::Frame(spec.frameCount);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;
        // Flat canvas treatment: drop the perspective camera so the 2D canvas
        // camera places screen-space layers directly.
        plan.camera.reset();
        plan.camera_samples.reset();
        for (auto& layer : plan.layers) {
            layer.screen_space = true;
            layer.enable_3d = false;
            // Path layers are anchored at their centre by the plan renderer,
            // while the pack authors path geometry from the top-left bounds.
            // Pull the anchor back by half the size so the canvas-space path
            // lands exactly on its DTO coordinates.
            float pathOffsetX = 0.f;
            float pathOffsetY = 0.f;
            if (layer.shape &&
                layer.shape->type == chronon3d::render_plan::ShapeContentTypePlan::Path) {
                pathOffsetX = -layer.size[0] * 0.5f;
                pathOffsetY = -layer.size[1] * 0.5f;
            }
            layer.position[0] += pathOffsetX;
            layer.position[1] += pathOffsetY;
            // The static opacity is what the screen-space path reads. Keep it
            // at the strongest authored value so fade-in labels and pins remain
            // visible even when the sampler is ignored; sampled opacity still
            // drives the actual fade when available.
            float baseOpacity = layer.opacity.value_or(1.f);
            for (auto& transform : layer.transform_samples) {
                transform.position[0] += spec.canvas.x * 0.5f + pathOffsetX;
                transform.position[1] += spec.canvas.y * 0.5f + pathOffsetY;
                baseOpacity = std::max(baseOpacity, transform.opacity);
            }
            layer.opacity = baseOpacity;
            // The screen-space sampler pins the first sample's opacity, which is
            // zero for every fade-in layer. Keep the authored geometry samples
            // (movement, pulse scale, trim) but make their opacity constant at
            // the strongest value so highlights, pins and labels never vanish.
            for (auto& transform : layer.transform_samples)
                transform.opacity = baseOpacity;
            if (layer.type == chronon3d::render_plan::LayerType::Text &&
                !layer.text.empty()) {
                // The pack estimates text width from font size only. Playfair
                // and mono are wider than that estimate, so grow the box instead
                // of letting the last glyph wrap onto a second line.
                const float fontPx = layer.size[1] > 0.f ? layer.size[1] / 1.25f : 0.f;
                const float needed =
                    fontPx * static_cast<float>(layer.text.size()) * 0.85f + 32.f;
                layer.size[0] = std::max(layer.size[0], needed);
                // Text sampling currently pins the first sample on the
                // screen-space text path; the text is static by design here.
                layer.transform_samples.clear();
            }
        }

        std::ofstream out(outPath, std::ios::binary | std::ios::trunc);
        if (!out || !(out << chrononmotion::motion::renderPlanToJson(plan) << '\n'))
            throw std::runtime_error("could not write plan: " + outPath);
        std::cout << "Wrote " << outPath << " with " << plan.layers.size()
                  << " layers from " << scenePath << " ("
                  << spec.frameCount << " frames at " << spec.fps << " fps, end "
                  << composition.endFrame << ")\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "editorial map emitter error: " << error.what() << '\n';
        return 1;
    }
}
