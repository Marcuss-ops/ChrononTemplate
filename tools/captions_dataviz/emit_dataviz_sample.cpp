// Emits documentary-style data-viz sample plans (bar + step-line) for render review.
// Usage: chronontemplate_emit_dataviz_sample <output-directory>
#include "chronontemplate/captions_dataviz/CaptionsDataVizPack.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <fstream>
#include <iostream>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;

namespace {

class SampleAssetBackend {
public:
    ContentHandle text(const TextRequest& request) {
        return make("text/" + request.text, ContentKind::Text,
                    {request.fontSize * static_cast<float>(request.text.size()) * 0.65f,
                     request.fontSize * 1.25f});
    }

    ContentHandle image(const ImageRequest& request) {
        return make(request.path, ContentKind::Image, {1920.f, 1080.f});
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
    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle handle;
        handle.id = std::move(id);
        handle.wireId = m_nextWireId++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = {0.5f, 0.5f};
        handle.metrics.fingerprint = "dataviz-sample-v1:" + handle.id;
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }

    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;
};

void addPaperBackground(TemplateScene& scene, int endFrame) {
    LayerHandle& bg = scene.video(
        VideoSpec{.path = "assets/images/documentary_paper_alive.mp4", .name = "paper_bg"});
    bg.alive(0, endFrame);
}

DataVizSpec sampleSpec(const std::string& name) {
    DataVizSpec spec;
    spec.values = {35.f, 80.f, 55.f, 95.f};
    spec.labels = {"Q1", "Q2", "Q3", "Q4"};
    spec.highlightIndex = 3;
    spec.title = "CRESCITA TRIMESTRALE";
    spec.name = name;
    spec.inFrame = 5;
    spec.duration = 195;
    return spec;
}

void writePlan(const chronon3d::render_plan::RenderPlan& plan, const std::string& output) {
    std::ofstream file(output, std::ios::binary | std::ios::trunc);
    if (!file || !(file << renderPlanToJson(plan))) {
        throw std::runtime_error("failed to write RenderPlan: " + output);
    }
    std::cout << "Wrote " << output << " with " << plan.layers.size() << " layers\n";
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: chronontemplate_emit_dataviz_sample <output-directory>\n";
        return 2;
    }
    const std::string outDir = argv[1];

    try {
        {
            SampleAssetBackend backend;
            RenderPlanContentHost host({
                .createText = [&](const TextRequest& request) { return backend.text(request); },
                .createImage = [&](const ImageRequest& request) { return backend.image(request); },
                .createVideo = [&](const VideoRequest& request) { return backend.video(request); },
                .createShape = [&](const ShapeRequest& request) { return backend.shape(request); },
                .currentFingerprint = [&](const ContentId& id) { return backend.fingerprint(id); }});
            TemplateScene scene("dataviz_bar_sample", 30.f, host, 1920.f, 1080.f);
            addPaperBackground(scene, 200);
            (void)addDataVizChart(scene, sampleSpec("dataviz_bar"));
            auto plan = lowerToRenderPlan(scene, host, "dataviz_bar_sample", "dataviz_bar_sample.mp4");
            writePlan(plan, outDir + "/dataviz_bar.plan.json");
        }
        {
            SampleAssetBackend backend;
            RenderPlanContentHost host({
                .createText = [&](const TextRequest& request) { return backend.text(request); },
                .createImage = [&](const ImageRequest& request) { return backend.image(request); },
                .createVideo = [&](const VideoRequest& request) { return backend.video(request); },
                .createShape = [&](const ShapeRequest& request) { return backend.shape(request); },
                .currentFingerprint = [&](const ContentId& id) { return backend.fingerprint(id); }});
            TemplateScene scene("dataviz_line_sample", 30.f, host, 1920.f, 1080.f);
            addPaperBackground(scene, 200);
            (void)addDataVizLineChart(scene, sampleSpec("dataviz_line"));
            auto plan = lowerToRenderPlan(scene, host, "dataviz_line_sample", "dataviz_line_sample.mp4");
            writePlan(plan, outDir + "/dataviz_line.plan.json");
        }
    } catch (const std::exception& e) {
        std::cerr << "emit_dataviz_sample: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
