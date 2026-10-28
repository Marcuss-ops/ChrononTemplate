#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using chrononmotion::Vector2;
using chrononmotion::Vector3;

namespace {
constexpr int kFps = 30;
constexpr int kFrames = 180;

class AssetBackend final : public ContentHost {
public:
    ContentHandle createText(const TextRequest& request) override {
        return make("text/" + request.text, chrononmotion::motion::ContentKind::Text,
                    {request.fontSize * 1.05f * static_cast<float>(request.text.size()),
                     request.fontSize * 1.3f});
    }
    ContentHandle createImage(const ImageRequest& request) override {
        return make(request.path, chrononmotion::motion::ContentKind::Image, {1920.f, 1080.f});
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
        ContentHandle handle;
        handle.id = std::move(id);
        handle.wireId = next++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = Vector2(.5f, .5f);
        handle.metrics.fingerprint = "real-depth-focus-v1:" + handle.id;
        fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }
};

void markLayer(chronon3d::render_plan::RenderPlan& plan, MotionLayerId id,
               bool enable3d, bool screenSpace = false) {
    const auto wireId = std::to_string(id);
    for (auto& layer : plan.layers) {
        if (layer.id == wireId) {
            layer.enable_3d = enable3d;
            layer.screen_space = screenSpace;
            if (screenSpace) layer.position_dimensions = 2;
            return;
        }
    }
    throw std::runtime_error("lowered layer not found: " + wireId);
}
}

int main(int argc, char** argv) {
    const std::filesystem::path outDir = argc > 1 ? argv[1] : "out/real_depth_focus_v1";
    try {
        AssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& r) { return backend.createText(r); },
            .createImage = [&](const ImageRequest& r) { return backend.createImage(r); },
            .createVideo = [&](const VideoRequest& r) { return backend.createVideo(r); },
            .createShape = [&](const ShapeRequest& r) { return backend.createShape(r); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }});

        TemplateScene scene("real_depth_focus_v1", static_cast<float>(kFps), host, 1920.f, 1080.f);
        scene.camera().setFov(48.f);
        auto& camera = scene.cameraRig();
        camera.setFocusDistance(1260.f).setFStop(2.8f).setMaxBlur(22.f)
              .setLensShift(Vector2(.012f, 0.f));
        camera.focusDistanceTrack()
            .add(0.f, 1260.f)
            .add(1.5f, 1260.f)
            .add(2.5f, 1080.f)
            .add(3.5f, 1080.f)
            .add(4.5f, 900.f)
            .add(6.f, 900.f);
        camera.fStopTrack().add(0.f, 2.8f).add(6.f, 2.8f);
        camera.maxBlurTrack().add(0.f, 22.f).add(6.f, 22.f);
        scene.camera().orbit(.035f, .012f).between(0, kFrames - 1);

        auto& background = scene.shape(ShapeSpec{
            .size = Vector2(1920.f, 1080.f), .fillColor = "#080B16", .name = "InkBlueBackground"});
        background.position(0.f, 0.f).alive(0, kFrames - 1);

        const std::string font = "Chronon3d/assets/fonts/InterDisplay-Bold.ttf";
        auto& far = scene.text(TextSpec{.text = "CAMERA", .font = font, .fontSize = 112.f,
            .color = "#B5C1D2", .name = "FarPlaneCamera"});
        far.position(960.f, 300.f, -180.f).alive(0, kFrames - 1)
           .animateOpacity(0, 20, 0.f, .82f);

        auto& middle = scene.text(TextSpec{.text = "FOCUS", .font = font, .fontSize = 118.f,
            .color = "#F1F7FF", .name = "MiddlePlaneFocus",
            .glow = TextGlowStyle{.color = "#36DDF2", .radius = 7.f, .intensity = .08f}});
        middle.position(960.f, 540.f, 0.f).alive(0, kFrames - 1)
              .animateOpacity(10, 24, 0.f, 1.f);

        auto& near = scene.text(TextSpec{.text = "DEPTH", .font = font, .fontSize = 100.f,
            .color = "#E9FBFF", .name = "NearPlaneDepth",
            .glow = TextGlowStyle{.color = "#24CBE8", .radius = 8.f, .intensity = .09f}});
        near.position(960.f, 780.f, 180.f).alive(0, kFrames - 1)
            .animateOpacity(22, 28, 0.f, 1.f);

        auto plan = lowerToRenderPlan(scene, host, "real_depth_focus_v1", "real_depth_focus_v1.mp4");
        plan.canvas.duration = chronon3d::Frame(kFrames);
        for (auto& layer : plan.layers)
            if (layer.duration_frames) layer.duration_frames = chronon3d::Frame(kFrames);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;
        markLayer(plan, background.id(), true, true);
        markLayer(plan, far.id(), true);
        markLayer(plan, middle.id(), true);
        markLayer(plan, near.id(), true);

        std::filesystem::create_directories(outDir);
        const auto planPath = outDir / "real_depth_focus_v1.plan.json";
        std::ofstream output(planPath, std::ios::binary | std::ios::trunc);
        if (!output || !(output << chrononmotion::motion::renderPlanToJson(plan) << '\n'))
            throw std::runtime_error("could not write RenderPlan: " + planPath.string());
        std::cout << "Wrote " << planPath << " — " << kFrames << " frames at 1920x1080, "
                  << plan.layers.size() << " layers\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "real_depth_focus_v1: " << error.what() << '\n';
        return 1;
    }
}
