// Emits the documentary date-group sequence as a RenderPlan for render review.
// Usage: chronontemplate_emit_date_groups <output-directory>
#include "chronontemplate/date_groups/DateGroupsPack.hpp"
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

namespace {

class SampleAssetBackend {
public:
    ContentHandle text(const TextRequest& request) {
        return make("text/" + request.text + "@" + std::to_string(static_cast<int>(request.fontSize)),
                    ContentKind::Text,
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
        handle.metrics.fingerprint = "date-groups-sample-v1:" + handle.id;
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }

    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;
};

DateGroupsSpec sampleSpec() {
    DateGroupsSpec spec;
    spec.name = "date_groups";
    spec.fps = 30.f;
    spec.secondsPerDate = 3;
    spec.animations = {
        {.name = "BIRTH", .dates = {"1948", "1951"}},
        {.name = "FIRST STEP", .dates = {"1962", "1965"}},
        {.name = "CHANGE", .dates = {"1969", "1973"}},
        {.name = "SIGNAL", .dates = {"1980", "1984"}},
        {.name = "NETWORK", .dates = {"1989", "1991"}},
        {.name = "LAUNCH", .dates = {"1998", "2001"}},
        {.name = "MOBILE", .dates = {"2007", "2010"}},
        {.name = "CLOUD", .dates = {"2012", "2015"}},
        {.name = "AI", .dates = {"2017", "2022"}},
        {.name = "NOW", .dates = {"2025", "2026"}},
    };
    return spec;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: chronontemplate_emit_date_groups <output-directory>\n";
        return 2;
    }
    const std::string outDir = argv[1];

    try {
        SampleAssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& request) { return backend.text(request); },
            .createImage = [&](const ImageRequest& request) { return backend.image(request); },
            .createVideo = [&](const VideoRequest& request) { return backend.video(request); },
            .createShape = [&](const ShapeRequest& request) { return backend.shape(request); },
            .currentFingerprint = [&](const ContentId& id) { return backend.fingerprint(id); }});

        const DateGroupsSpec spec = sampleSpec();
        const int duration = dateGroupsDurationFrames(spec);
        TemplateScene scene("date_groups_sample", spec.fps, host, spec.width, spec.height);
        (void)addDateGroups(scene, spec);
        auto plan = lowerToRenderPlan(scene, host, "date_groups_sample", "date_groups_sample.mp4");
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;

        const std::string output = outDir + "/date_groups.plan.json";
        std::ofstream file(output, std::ios::binary | std::ios::trunc);
        if (!file || !(file << renderPlanToJson(plan))) {
            throw std::runtime_error("failed to write RenderPlan: " + output);
        }
        std::cout << "Wrote " << output << " with " << plan.layers.size() << " layers, "
                  << duration << " frames\n";
    } catch (const std::exception& e) {
        std::cerr << "emit_date_groups: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
