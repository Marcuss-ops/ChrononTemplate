// Emitter: ArchivalTimelineReveal -> chronon render-plan JSON.
// Usage: emit_archival_timeline_reveal [YEAR] [HEADLINE] [OUT_PLAN_JSON]
#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/documentary_effects/ArchivalTimelinePack.hpp"
#include "chrononmotion/motion/Easing.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using chrononmotion::Vector2;

namespace {
class AssetBackend final : public ContentHost {
public:
    ContentHandle createText(const TextRequest& r) override {
        return make("text/" + r.text, chrononmotion::motion::ContentKind::Text,
                    {r.fontSize * .68f * static_cast<float>(r.text.size()), r.fontSize * 1.25f});
    }
    ContentHandle createImage(const ImageRequest& r) override {
        return make(r.path, chrononmotion::motion::ContentKind::Image, {1920.f, 1080.f});
    }
    ContentHandle createVideo(const VideoRequest& r) override {
        return make("video/" + r.path, chrononmotion::motion::ContentKind::Video, {1920.f, 1080.f});
    }
    ContentHandle createShape(const ShapeRequest& r) override {
        return make("shape/" + r.name, chrononmotion::motion::ContentKind::Image, r.size);
    }
    std::string currentFingerprint(const ContentId& id) const override {
        const auto it = fingerprints.find(id);
        return it == fingerprints.end() ? std::string{} : it->second;
    }
private:
    std::uint64_t next{1};
    std::unordered_map<ContentId, std::string> fingerprints;
    ContentHandle make(std::string id, chrononmotion::motion::ContentKind kind, Vector2 size) {
        ContentHandle c;
        c.id = std::move(id); c.wireId = next++; c.kind = kind;
        c.metrics.naturalSize = size; c.metrics.anchor = Vector2(.5f, .5f);
        c.metrics.fingerprint = "archival-timeline-reveal-v1:" + c.id;
        fingerprints.emplace(c.id, c.metrics.fingerprint);
        return c;
    }
};
}

int main(int argc, char** argv) {
    const std::string year = argc > 1 ? argv[1] : "2025";
    const std::string headline = argc > 2 ? argv[2] : "ALEX PASSED AWAY";
    const std::string path = argc > 3 ? argv[3]
        : "ChrononTemplate/golden_plans/date_spotlight_2025/date_spotlight_2025.plan.json";
    try {
        AssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& r) { return backend.createText(r); },
            .createImage = [&](const ImageRequest& r) { return backend.createImage(r); },
            .createVideo = [&](const VideoRequest& r) { return backend.createVideo(r); },
            .createShape = [&](const ShapeRequest& r) { return backend.createShape(r); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }});
        const std::string sceneId = "archival_timeline_reveal_v1";
        TemplateScene scene(sceneId, 30.f, host, 1920.f, 1080.f);

        docfx::ArchivalTimelineSpec spec;
        spec.year = year;
        spec.headline = headline;
        spec.sceneFrames = 180;
        const auto layers = docfx::addArchivalTimelineReveal(scene, spec);
        if (!layers.paper || !layers.line || !layers.year || !layers.headline)
            throw std::runtime_error("archival timeline layers missing");
        if (const auto problems = scene.validate(); !problems.empty())
            throw std::runtime_error("archival timeline invalid: " + problems.front());

        auto plan = lowerToRenderPlan(scene, host, sceneId, sceneId + ".mp4");
        plan.canvas.duration = chronon3d::Frame(180);
        for (auto& layer : plan.layers)
            if (layer.duration_frames) layer.duration_frames = chronon3d::Frame(180);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;
        std::ofstream out(path, std::ios::binary | std::ios::trunc);
        if (!out || !(out << chrononmotion::motion::renderPlanToJson(plan) << '\n'))
            throw std::runtime_error("could not write plan: " + path);
        std::cout << "Wrote " << path << " with " << plan.layers.size()
                  << " layers, 180 frames at 30 fps\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "archival timeline emitter: " << e.what() << '\n';
        return 1;
    }
}
