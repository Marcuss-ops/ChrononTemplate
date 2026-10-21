#include "chronontemplate/date_timeline/DateTimelinePack.hpp"
#include "chronontemplate/fast_intro/FastIntroPack.hpp"
#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <cstdint>
#include <unordered_map>

using namespace chronontemplate;

namespace {
class AssetBackend final : public ContentHost {
public:
    ContentHandle createText(const TextRequest& r) override {
        return make("text/" + r.text, chrononmotion::motion::ContentKind::Text,
                    {r.fontSize * .66f * static_cast<float>(r.text.size()), r.fontSize * 1.25f});
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
    ContentHandle make(std::string id, chrononmotion::motion::ContentKind kind,
                       chrononmotion::Vector2 size) {
        ContentHandle c;
        c.id = std::move(id); c.wireId = next++; c.kind = kind;
        c.metrics.naturalSize = size; c.metrics.anchor = chrononmotion::Vector2(.5f, .5f);
        c.metrics.fingerprint = "fast-intro-date-timeline-v1:" + c.id;
        fingerprints.emplace(c.id, c.metrics.fingerprint);
        return c;
    }
};

void writePlan(const std::filesystem::path& directory, const std::string& id,
               TemplateScene& scene, RenderPlanContentHost& host) {
    std::filesystem::create_directories(directory);
    if (const auto problems = scene.validate(); !problems.empty())
        throw std::runtime_error(id + " invalid: " + problems.front());
    auto plan = lowerToRenderPlan(scene, host, id, id + ".mp4");
    plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;
    const auto path = directory / (id + ".plan.json");
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out || !(out << chrononmotion::motion::renderPlanToJson(plan) << '\n'))
        throw std::runtime_error("could not write plan: " + path.string());
    std::cout << "Wrote " << path << " with " << plan.layers.size() << " layers\n";
}
}

int main(int argc, char** argv) {
    const std::filesystem::path outDir = argc > 1 ? argv[1]
        : "ChrononTemplate/golden_plans";
    try {
        std::filesystem::create_directories(outDir);
        AssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& r) { return backend.createText(r); },
            .createImage = [&](const ImageRequest& r) { return backend.createImage(r); },
            .createVideo = [&](const VideoRequest& r) { return backend.createVideo(r); },
            .createShape = [&](const ShapeRequest& r) { return backend.createShape(r); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }});

        fast_intro::FastIntroSpec introSpec;
        TemplateScene intro("fast_intro_v1", 30.f, host, introSpec.width, introSpec.height);
        (void)fast_intro::addFastIntro(intro, introSpec);
        writePlan(outDir / "fast_intro_v1", "fast_intro_v1", intro, host);

        for (const auto& choice : date_timeline::timelineMotionChoices()) {
            date_timeline::DateTimelineSpec timelineSpec;
            timelineSpec.name = "date_timeline_" + choice.id;
            timelineSpec.motion = choice.motion;
            timelineSpec.milestones = date_timeline::technologyDateSample();
            TemplateScene timeline(timelineSpec.name, 30.f, host,
                                   timelineSpec.width, timelineSpec.height);
            (void)date_timeline::addDateTimeline(timeline, timelineSpec);
            writePlan(outDir / "date_timeline_v1" / "animations",
                      timelineSpec.name, timeline, host);
        }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "emit_fast_intro_and_date_timeline: " << e.what() << '\n';
        return 1;
    }
}
