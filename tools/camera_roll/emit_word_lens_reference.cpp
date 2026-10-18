// Native C++ reference plan for the camera-led word lens treatment.

#include "chronontemplate/camera_roll/WordLensPack.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;
using namespace chronon3d::render_plan;

namespace {
class Backend {
public:
    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle handle;
        handle.id = id;
        handle.wireId = next++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = Vector2(.5f, .5f);
        handle.metrics.fingerprint = "word-lens-reference:" + id;
        fingerprints[id] = handle.metrics.fingerprint;
        return handle;
    }
    ContentHandle text(const TextRequest& r) {
        return make("text/" + r.text, ContentKind::Text,
                    {static_cast<float>(r.fontSize * r.text.size() * .62f), r.fontSize * 1.25f});
    }
    ContentHandle image(const ImageRequest& r) {
        return make(r.path, ContentKind::Image, {1920.f, 1080.f});
    }
    ContentHandle shape(const ShapeRequest& r) {
        return make("shape/" + r.name, ContentKind::Image, r.size);
    }
    std::string fingerprint(const ContentId& id) const {
        auto it = fingerprints.find(id);
        return it == fingerprints.end() ? std::string{} : it->second;
    }
private:
    std::uint64_t next{1};
    std::unordered_map<ContentId, std::string> fingerprints;
};
}

int main(int argc, char** argv) {
    try {
        const std::string outputPath = argc > 1 ? argv[1] : "out/word_lens_reference.plan.json";
        Backend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& r) { return backend.text(r); },
            .createImage = [&](const ImageRequest& r) { return backend.image(r); },
            .createVideo = [&](const VideoRequest&) { return ContentHandle{}; },
            .createShape = [&](const ShapeRequest& r) { return backend.shape(r); },
            .currentFingerprint = [&](const ContentId& id) { return backend.fingerprint(id); }});

        TemplateScene scene("word_lens_reference", 30.f, host, 1920.f, 1080.f);
        const auto board = addWordLensBoard(scene);
        auto plan = lowerToRenderPlan(scene, host, "word_lens_reference_v1",
                                      "word_lens_reference_v1.mp4");
        plan.output.format = OutputFormat::Mp4;
        std::ofstream out(outputPath, std::ios::binary | std::ios::trunc);
        if (!out || !(out << renderPlanToJson(plan)))
            throw std::runtime_error("failed to write plan: " + outputPath);
        std::cout << "Wrote " << outputPath << " layers=" << plan.layers.size()
                  << " words=" << board.wordLayers.size()
                  << " point_lights=" << board.pointLightIds.size() << '\n';
    } catch (const std::exception& error) {
        std::cerr << "word lens reference: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
