// Emitter: BulletListPack demo -> chronon render-plan JSON.
// Usage: emit_bullet_list_demo [SEED] [OUT_PLAN_JSON]
#include "chronontemplate/bullet_list/BulletListPack.hpp"
#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
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
        c.metrics.fingerprint = "bullet-list-v1:" + c.id;
        fingerprints.emplace(c.id, c.metrics.fingerprint);
        return c;
    }
};
}

int main(int argc, char** argv) {
    const std::uint32_t seed = argc > 1 ? static_cast<std::uint32_t>(std::stoul(argv[1])) : 11u;
    const std::string path = argc > 2 ? argv[2]
        : "ChrononTemplate/out/bullet_list_v1/bullet_list_v1.plan.json";
    constexpr int kFrames = 240;
    try {
        AssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& r) { return backend.createText(r); },
            .createImage = [&](const ImageRequest& r) { return backend.createImage(r); },
            .createVideo = [&](const VideoRequest& r) { return backend.createVideo(r); },
            .createShape = [&](const ShapeRequest& r) { return backend.createShape(r); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }});
        const std::string sceneId = "bullet_list_v1";
        TemplateScene scene(sceneId, 30.f, host, 1920.f, 1080.f);

        BulletListSpec spec;
        spec.items = {"Primo punto della lista",
                      "Secondo punto, con un dettaglio",
                      "Terzo punto della sequenza",
                      "Quarto punto che chiude il ragionamento"};
        spec.seed = seed;
        spec.centerX = 960.f;
        spec.centerY = 540.f;
        spec.lineSpacing = 120.f;
        spec.fontSize = 56.f;
        const BulletListComposition board = addBulletList(scene, spec);
        if (const auto problems = scene.validate(); !problems.empty())
            throw std::runtime_error("bullet list invalid: " + problems.front());

        auto plan = lowerToRenderPlan(scene, host, sceneId, sceneId + ".mp4");
        plan.canvas.duration = chronon3d::Frame(kFrames);
        for (auto& layer : plan.layers)
            if (layer.duration_frames) layer.duration_frames = chronon3d::Frame(kFrames);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;
        std::ofstream out(path, std::ios::binary | std::ios::trunc);
        if (!out || !(out << chrononmotion::motion::renderPlanToJson(plan) << '\n'))
            throw std::runtime_error("could not write plan: " + path);
        std::cout << "Wrote " << path << " with " << board.bullets.size() << " bullets, camera "
                  << titleCameraMoveId(board.camera) << ", " << kFrames << " frames at 30 fps\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "bullet list emitter: " << e.what() << '\n';
        return 1;
    }
}
