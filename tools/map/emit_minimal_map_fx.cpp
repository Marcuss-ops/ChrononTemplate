// Emits the minimal map FX proof plan: one authored map plate and four acts
// (area pulse, radar reveal, light beam, city network). Every act lowers to
// ellipse/rectangle/path shapes, so Chronon3d needs no map-specific code path.
//
//   chronontemplate_emit_minimal_map_fx [out.plan.json]
//
// Render a proof frame with: chronon3d_cli render --plan <out.plan.json>
// --assets-root ChrononTemplate --frame 45 --output <frame.png>

#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/map/MapFxPack.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace chronontemplate;
using chrononmotion::Vector2;
using chrononmotion::motion::ContentKind;

namespace {

constexpr float kWidth = 1920.f;
constexpr float kHeight = 1080.f;
constexpr float kFps = 30.f;
constexpr int kTotalFrames = 360;

class PlanBackend final : public ContentHost {
public:
    ContentHandle createText(const TextRequest& request) override {
        return make("text/" + request.text, ContentKind::Text,
                    {request.fontSize * 0.6f * static_cast<float>(request.text.size()),
                     request.fontSize * 1.25f});
    }
    ContentHandle createImage(const ImageRequest& request) override {
        // The plan carries this id as the logical asset path; keep it relative
        // so `chronon3d_cli --assets-root` can mount the template checkout.
        return make(request.path, ContentKind::Image, {kWidth, kHeight});
    }
    ContentHandle createVideo(const VideoRequest& request) override {
        return make("video/" + request.path, ContentKind::Video, {kWidth, kHeight});
    }
    ContentHandle createShape(const ShapeRequest& request) override {
        return make("shape/" + request.name, ContentKind::Image, request.size);
    }
    std::string currentFingerprint(const ContentId& id) const override {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }

private:
    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;

    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle handle;
        handle.id = std::move(id);
        handle.wireId = m_nextWireId++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = Vector2(0.5f, 0.5f);
        handle.metrics.fingerprint = "minimal-map-fx:" + handle.id;
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }
};

void addMapPlate(TemplateScene& scene) {
    ImageSpec plate;
    plate.path = "catalog/maps/nasa_blue_marble_august.jpg";
    plate.name = "minimal_map_plate";
    plate.targetSize = Vector2(kWidth, kHeight);
    scene.image(plate).position(kWidth * 0.5f, kHeight * 0.5f).alive(0, kTotalFrames - 1)
        .animate(FadeIn{.inFrame = 0, .duration = 12})
        .animate(FadeOut{.startFrame = kTotalFrames - 24, .duration = 15});
}

void addMarker(TemplateScene& scene, const std::string& name, Vector2 position,
               const std::string& color) {
    ShapeSpec marker;
    marker.size = Vector2(18.f, 18.f);
    marker.fillColor = color;
    marker.name = name;
    marker.geometry = ShapeGeometry::Ellipse;
    marker.glowColor = color;
    marker.glowRadius = 16.f;
    marker.glowIntensity = 0.8f;
    scene.shape(marker).position(position.x, position.y).alive(0, kTotalFrames - 1)
        .animate(ScalePop{.inFrame = 0, .duration = 14, .from = 0.2f, .to = 1.f})
        .animate(FadeOut{.startFrame = kTotalFrames - 24, .duration = 15});
}

} // namespace

int main(int argc, char** argv) {
    const std::string outPath = argc > 1
        ? argv[1]
        : "ChrononTemplate/out/minimal_map_fx/minimal_map_fx.plan.json";
    try {
        std::filesystem::path path(outPath);
        if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path());

        PlanBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& request) { return backend.createText(request); },
            .createImage = [&](const ImageRequest& request) { return backend.createImage(request); },
            .createVideo = [&](const VideoRequest& request) { return backend.createVideo(request); },
            .createShape = [&](const ShapeRequest& request) { return backend.createShape(request); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); },
        });

        TemplateScene scene("minimal_map_fx", kFps, host, kWidth, kHeight);
        addMapPlate(scene);

        const std::vector<Vector2> anchors = {
            {430.f, 690.f}, {960.f, 540.f}, {1490.f, 360.f},
        };
        addMarker(scene, "minimal_map_marker_0", anchors[0], "#38D9C5");
        addMarker(scene, "minimal_map_marker_1", anchors[1], "#F3C76A");
        addMarker(scene, "minimal_map_marker_2", anchors[2], "#38D9C5");

        MapFxSpec area;
        area.kind = MapFxKind::AreaGlowPulse;
        area.delayFrames = 0;
        area.durationFrames = 85;
        area.radius = 120.f;
        (void)addMapFx(scene, area, {anchors[0]}, 0, kTotalFrames);

        MapFxSpec radar;
        radar.kind = MapFxKind::RadarLocationReveal;
        radar.delayFrames = 90;
        radar.durationFrames = 85;
        radar.radius = 135.f;
        (void)addMapFx(scene, radar, {anchors[1]}, 0, kTotalFrames);

        MapFxSpec beam;
        beam.kind = MapFxKind::LightBeamDrop;
        beam.delayFrames = 180;
        beam.durationFrames = 80;
        beam.radius = 105.f;
        (void)addMapFx(scene, beam, {anchors[2]}, 0, kTotalFrames);

        MapFxSpec network;
        network.kind = MapFxKind::CityNetworkExpansion;
        network.delayFrames = 270;
        network.durationFrames = 85;
        (void)addMapFx(scene, network, anchors, 0, kTotalFrames);

        auto plan = lowerToRenderPlan(scene, host, "minimal_map_fx", "minimal_map_fx.mp4");
        plan.canvas.duration = chronon3d::Frame(kTotalFrames);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;

        std::ofstream out(outPath, std::ios::binary | std::ios::trunc);
        if (!out || !(out << chrononmotion::motion::renderPlanToJson(plan) << '\n')) {
            throw std::runtime_error("could not write plan: " + outPath);
        }
        std::cout << "Wrote " << outPath << " with " << plan.layers.size() << " layers, "
                  << kTotalFrames << " frames at " << kFps << " fps\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "minimal map fx emitter error: " << error.what() << '\n';
        return 1;
    }
}
