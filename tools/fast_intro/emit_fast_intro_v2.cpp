// ChrononTemplate — Fast Intro v2 unified emitter.
//
// Single C++ writer for all four v2 recipes (opening_plate, punch_stat,
// whip_match, chapter_card). It authors through addFastIntroV2 so the plans
// stay single-sourced with the pack, then lowers to chronon.render-plan.v3.
//
//   chronontemplate_emit_fast_intro_v2 <out-dir> [--vertical]
//
// The Python mirror (tools/fast_intro/build_fast_intro_v2.py) produces the
// same four plans without a Linux build; the committed goldens in
// golden_plans/fast_intro_v2/ are the contract reference.
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
        c.metrics.fingerprint = "fast-intro-v2:" + c.id;
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

fast_intro::FastIntroV2Spec baseSpec(fast_intro::FastIntroRecipe recipe,
                                     const std::string& name, int duration,
                                     float w, float h) {
    fast_intro::FastIntroV2Spec spec;
    spec.recipe = recipe;
    spec.name = name;
    spec.durationFrames = duration;
    spec.width = w;
    spec.height = h;
    return spec;
}
}

int main(int argc, char** argv) {
    const std::filesystem::path outDir = argc > 1 ? argv[1]
        : "ChrononTemplate/out/fast_intro_v2";
    bool vertical = false;
    for (int i = 2; i < argc; ++i)
        if (std::string(argv[i]) == "--vertical") vertical = true;
    try {
        std::filesystem::create_directories(outDir);
        AssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& r) { return backend.createText(r); },
            .createImage = [&](const ImageRequest& r) { return backend.createImage(r); },
            .createVideo = [&](const VideoRequest& r) { return backend.createVideo(r); },
            .createShape = [&](const ShapeRequest& r) { return backend.createShape(r); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }});

        auto emit = [&](fast_intro::FastIntroV2Spec spec) {
            TemplateScene scene(spec.name, 30.f, host, spec.width, spec.height);
            (void)fast_intro::addFastIntroV2(scene, spec);
            writePlan(outDir, spec.name, scene, host);
        };

        {
            auto spec = baseSpec(fast_intro::FastIntroRecipe::OpeningPlate,
                                 "fast_intro_v2_opening", 120, 1920.f, 1080.f);
            spec.topics = {"CONTEXT", "EVIDENCE", "WHAT CHANGED"};
            emit(spec);
            if (vertical) {
                spec.name = "fast_intro_v2_opening_vertical";
                spec.width = 1080.f; spec.height = 1920.f;
                emit(spec);
            }
        }
        {
            auto spec = baseSpec(fast_intro::FastIntroRecipe::PunchStat,
                                 "fast_intro_v2_punch", 150, 1920.f, 1080.f);
            emit(spec);
            if (vertical) {
                spec.name = "fast_intro_v2_punch_vertical";
                spec.width = 1080.f; spec.height = 1920.f;
                emit(spec);
            }
        }
        {
            auto spec = baseSpec(fast_intro::FastIntroRecipe::WhipMatch,
                                 "fast_intro_v2_whip", 180, 1920.f, 1080.f);
            spec.plates = {
                "ChrononTemplate/assets/fast_intro_match_cut/news_masthead.png",
                "ChrononTemplate/assets/fast_intro_match_cut/crop_news_harmony.png",
                "ChrononTemplate/assets/fast_intro_match_cut/web_sports.png",
                "ChrononTemplate/assets/fast_intro_match_cut/web_essay.png",
                "ChrononTemplate/assets/fast_intro_match_cut/news_truth.png",
                "ChrononTemplate/assets/fast_intro_match_cut/web_numbered.png",
                "ChrononTemplate/assets/fast_intro_match_cut/news_discover.png",
                "ChrononTemplate/assets/fast_intro_match_cut/web_design.png"};
            emit(spec);
        }
        {
            auto spec = baseSpec(fast_intro::FastIntroRecipe::ChapterCard,
                                 "fast_intro_v2_chapter", 150, 1920.f, 1080.f);
            spec.chapterLabel = "CHAPTER 1";
            spec.title = "THE HITMAN HIDDEN IN A FAMILY PHOTO";
            spec.subtitle = "A parametric chapter card — no hard-coded copy.";
            emit(spec);
        }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "emit_fast_intro_v2: " << e.what() << '\n';
        return 1;
    }
}
