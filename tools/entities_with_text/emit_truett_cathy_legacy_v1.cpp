#include "chronontemplate/backgrounds/BackgroundPack.hpp"
#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/entities_with_text/DocumentarySnapshotPack.hpp"
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
    ContentHandle createText(const TextRequest& request) override {
        const float width = std::max(request.fontSize * 0.6f,
            request.fontSize * 0.84f * static_cast<float>(request.text.size()));
        return make("text/" + request.text, chrononmotion::motion::ContentKind::Text,
                    {width, request.fontSize * 1.25f});
    }
    ContentHandle createImage(const ImageRequest& request) override {
        if (request.path.find("truett_cathy_portrait_v5_photo_cutout.png") != std::string::npos)
            return make(request.path, chrononmotion::motion::ContentKind::Image, {1342.f, 1172.f});
        if (request.path.find("true_legacy_night_restaurant_v1.png") != std::string::npos)
            return make(request.path, chrononmotion::motion::ContentKind::Image, {1672.f, 941.f});
        throw std::invalid_argument("unexpected image asset: " + request.path);
    }
    ContentHandle createVideo(const VideoRequest& request) override {
        return make("video/" + request.path, chrononmotion::motion::ContentKind::Video, {1920.f, 1080.f});
    }
    ContentHandle createShape(const ShapeRequest& request) override {
        return make("shape/" + request.name, chrononmotion::motion::ContentKind::Image, request.size);
    }
    std::string currentFingerprint(const ContentId& id) const override {
        const auto it = fingerprints.find(id);
        return it == fingerprints.end() ? std::string{} : it->second;
    }
private:
    std::uint64_t next{1};
    std::unordered_map<ContentId, std::string> fingerprints;
    ContentHandle make(std::string id, chrononmotion::motion::ContentKind kind, Vector2 size) {
        ContentHandle value;
        value.id = std::move(id);
        value.wireId = next++;
        value.kind = kind;
        value.metrics.naturalSize = size;
        value.metrics.anchor = Vector2(0.5f, 0.5f);
        value.metrics.fingerprint = "truett-cathy-legacy-v1:" + value.id;
        fingerprints.emplace(value.id, value.metrics.fingerprint);
        return value;
    }
};

} // namespace

int main(int argc, char** argv) {
    const std::string outputPath = argc > 1 ? argv[1] :
        "ChrononTemplate/out/entity_true_legacy_v1/true_legacy_v1.plan.json";
    try {
        AssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& request) { return backend.createText(request); },
            .createImage = [&](const ImageRequest& request) { return backend.createImage(request); },
            .createVideo = [&](const VideoRequest& request) { return backend.createVideo(request); },
            .createShape = [&](const ShapeRequest& request) { return backend.createShape(request); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }});
        TemplateScene scene("entity_true_legacy_v1", 30.f, host, 1920.f, 1080.f);

        // Documentary depth comes from three clean compositing planes and a
        // restrained camera push, not simulated geometry.
        scene.camera().setFov(45.f);
        scene.camera().push(150.f).between(0, 149);
        auto& restaurant = scene.image(ImageSpec{
            .path = "ChrononTemplate/assets/images/true_legacy_night_restaurant_v1.png",
            .name = "NightRestaurantBackground",
            .frame = ImageFrameStyle{.saturation = 0.82f, .contrast = 1.08f, .vignette = 0.18f},
            .fit = ImageFitMode::Cover,
            .targetSize = Vector2(1920.f, 1080.f)});
        restaurant.position(960.f, 540.f, -300.f).scale(1.25f).alive(0, 150);

        auto& atmosphere = scene.shape(ShapeSpec{.size = Vector2(2600.f, 1500.f),
            .fillColor = "#000000", .name = "DocumentaryBackgroundGrade"});
        atmosphere.position(960.f, 540.f, -200.f).opacity(0.13f).alive(0, 150);

        // The title reads as part of the scene and leaves the portrait room.
        auto& title = scene.text(TextSpec{.text = "TRUETT CATHY",
            .font = "ChrononTemplate/assets/fonts/Anton-Regular.ttf",
            .fontSize = 230.f, .color = "#E5E3DE", .name = "LegacyTitle",
            .glow = TextGlowStyle{.color = "#FFF0D7", .radius = 30.f, .intensity = 0.30f}});
        // The title is a real perspective plane behind the portrait. It swings
        // into view, then holds a slight yaw so the depth stays readable.
        title.position(960.f, 750.f, -70.f).alive(0, 149)
            .animatePosition(0, 30, Vector3(0.f, 18.f, -80.f),
                             chrononmotion::motion::Easing::easeOut())
            .animateOpacity(0, 24, 0.f, 1.f, chrononmotion::motion::Easing::easeOut());
        if (auto* titleMotion = scene.motion().findLayer("LegacyTitle")) {
            constexpr float kIntroSeconds = 1.0f;
            titleMotion->tracks.scale
                .add(0.f, Vector3(0.88f, 0.88f, 1.f), chrononmotion::motion::Easing::easeOut())
                .add(kIntroSeconds, Vector3(1.f, 1.f, 1.f), chrononmotion::motion::Easing::easeOut());
            titleMotion->tracks.rotation
                .add(0.f, Vector3(-0.10f, 0.24f, -0.015f), chrononmotion::motion::Easing::easeOut())
                .add(kIntroSeconds, Vector3(-0.035f, 0.12f, 0.f), chrononmotion::motion::Easing::easeOut())
                .add(5.f, Vector3(-0.035f, 0.12f, 0.f), chrononmotion::motion::Easing::linear());
        }

        // Foreground photo cutout; keep its existing position and motion in the title composition.
        auto& portrait = scene.image(ImageSpec{
            .path = "ChrononTemplate/assets/images/truett_cathy_portrait_v5_photo_cutout.png",
            .name = "TruettCathyPortrait",
            .frame = ImageFrameStyle{.saturation = 0.84f, .contrast = 0.96f},
            .fit = ImageFitMode::Contain,
            .targetSize = Vector2(1342.f, 1172.f)});
        portrait.position(960.f, 400.f, 160.f).scale(0.60f).alive(0, 149)
            .animatePosition(0, 36, Vector3(0.f, 36.f, -35.f),
                             chrononmotion::motion::Easing::easeOut())
            .animateOpacity(0, 24, 0.f, 1.f, chrononmotion::motion::Easing::easeOut());
        if (auto* portraitMotion = scene.motion().findLayer("TruettCathyPortrait")) {
            portraitMotion->tracks.scale
                .add(0.f, Vector3(0.58f, 0.58f, 1.f), chrononmotion::motion::Easing::easeOut())
                .add(1.2f, Vector3(0.60f, 0.60f, 1.f), chrononmotion::motion::Easing::easeOut())
                .add(5.f, Vector3(0.60f, 0.60f, 1.f), chrononmotion::motion::Easing::linear());
        }

        auto plan = lowerToRenderPlan(scene, host, "entity_true_legacy_v1",
                                      "true_legacy_v1.mp4");
        // The template API treats lifetime endpoints as inclusive; constrain the
        // exported clip explicitly to exactly five seconds at 30 fps.
        plan.canvas.duration = chronon3d::Frame(150);
        for (auto& layer : plan.layers)
            if (layer.duration_frames) layer.duration_frames = chronon3d::Frame(150);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;
        std::ofstream out(outputPath, std::ios::binary | std::ios::trunc);
        if (!out || !(out << chrononmotion::motion::renderPlanToJson(plan) << '\n'))
            throw std::runtime_error("failed to write RenderPlan: " + outputPath);
        std::cout << "Wrote " << outputPath << " with " << plan.layers.size()
                  << " native layers, 150 frames at 30 fps\n";
    } catch (const std::exception& error) {
        std::cerr << "true legacy emitter: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
