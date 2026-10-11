#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"
#include "chrononmotion/motion/Easing.hpp"

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using chrononmotion::Vector2;
using chrononmotion::Vector3;

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
        c.metrics.fingerprint = "usa-atmospheric-backlight-v1:" + c.id;
        fingerprints.emplace(c.id, c.metrics.fingerprint);
        return c;
    }
};
}

int main(int argc, char** argv) {
    const std::string slug = argc > 1 ? argv[1] : "usa";
    const std::string label = argc > 2 ? argv[2] : "UNITED STATES";
    const std::string accent = argc > 3 ? argv[3] : "#D44A45";
    const std::string path = argc > 4 ? argv[4] :
        "ChrononTemplate/out/usa_atmospheric_backlight_v1/usa_atmospheric_backlight_v1.plan.json";
    try {
        AssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& r) { return backend.createText(r); },
            .createImage = [&](const ImageRequest& r) { return backend.createImage(r); },
            .createVideo = [&](const VideoRequest& r) { return backend.createVideo(r); },
            .createShape = [&](const ShapeRequest& r) { return backend.createShape(r); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }});
        const std::string sceneId = slug + "_atmospheric_backlight_v1";
        const std::string assets = "ChrononTemplate/assets/" + sceneId + "/";
        TemplateScene scene(sceneId, 30.f, host, 1920.f, 1080.f);
        scene.camera().setFov(45.f);

        auto addPlate = [&](const char* file, const char* name, float z, float opacity = 1.f) -> auto& {
            auto& image = scene.image(ImageSpec{
                .path = assets + file,
                .name = name, .fit = ImageFitMode::Contain, .targetSize = Vector2(1920.f, 1080.f)});
            // Keep plates in a stable perspective range, with matching scale;
            // the slight z offsets preserve the compositing order.
            image.position(960.f, 540.f, -400.f + (z + 400.f) * .01f)
                .scale(1.15f).opacity(opacity).alive(0, 150);
            return image;
        };

        auto& dark = scene.shape(ShapeSpec{.size = Vector2(1920.f, 1080.f),
            .fillColor = "#070707", .name = "NearBlackBase"});
        dark.position(960.f, 540.f, -401.f).scale(1.15f).alive(0, 150);
        addPlate("dark_field.png", "DarkCharcoalField", -400.f);
        auto& wide = addPlate("wide_red_backlight.png", "WideSilhouetteBacklight", -300.f, .88f);
        wide.animateOpacity(0, 149, .79f, .92f, chrononmotion::motion::Easing::easeInOut());
        addPlate("tight_red_diffusion.png", "TightRedDiffusion", -200.f, .78f);
        addPlate("burgundy_country.png", "DarkBurgundyCountrySilhouette", -80.f);
        addPlate("smoke_veil.png", "ProceduralSmokeVeil", 15.f, .82f);

        auto& number = scene.text(TextSpec{.text = "3,200",
            .font = "ChrononTemplate/assets/fonts/Anton-Regular.ttf",
            .fontSize = 190.f, .color = "#E8E2DC", .name = "Metric3200",
            .glow = TextGlowStyle{.color = accent, .radius = 15.f, .intensity = .13f}});
        number.position(1015.f, 545.f, -394.f).alive(0, 150)
            .animateOpacity(0, 22, 0.f, 1.f, chrononmotion::motion::Easing::easeOut());
        if (auto* motion = scene.motion().findLayer("Metric3200")) {
            motion->tracks.scale
                .add(0.f, Vector3(.94f, .94f, 1.f), chrononmotion::motion::Easing::easeOut())
                .add(.75f, Vector3(1.f, 1.f, 1.f), chrononmotion::motion::Easing::easeOut());
        }

        auto& country = scene.text(TextSpec{.text = label,
            .font = "ChrononTemplate/assets/fonts/Anton-Regular.ttf",
            .fontSize = 38.f, .color = accent, .name = "CountryLabel"});
        country.position(1015.f, 718.f, -394.f).alive(0, 150)
            .animateOpacity(0, 28, 0.f, 1.f, chrononmotion::motion::Easing::easeOut());

        auto plan = lowerToRenderPlan(scene, host, sceneId, sceneId + ".mp4");
        plan.canvas.duration = chronon3d::Frame(150);
        for (auto& layer : plan.layers)
            if (layer.duration_frames) layer.duration_frames = chronon3d::Frame(150);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;
        std::ofstream out(path, std::ios::binary | std::ios::trunc);
        if (!out || !(out << chrononmotion::motion::renderPlanToJson(plan) << '\n'))
            throw std::runtime_error("could not write plan: " + path);
        std::cout << "Wrote " << path << " with " << plan.layers.size() << " layers, 150 frames at 30 fps\n";
    } catch (const std::exception& e) {
        std::cerr << "USA backlight emitter: " << e.what() << '\n';
        return 1;
    }
}
