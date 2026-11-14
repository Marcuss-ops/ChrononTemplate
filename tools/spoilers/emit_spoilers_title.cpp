// Recreates the SPOILERS reference title card in ChrononTemplate:
// 1920x1080, 24 fps, 72 frames (3.0 s), procedural film dust & curved lint
// fibers, smooth crimson title with glowing vector rim, and a composite optical
// adjustment stack (pincushion lens distortion, radial edge blur, chromatic
// aberration, soft diffusion, and vignette).
//
// Usage: chronontemplate_emit_spoilers_title <output-plan-path>
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;

namespace {

constexpr float kWidth = 1920.f;
constexpr float kHeight = 1080.f;
constexpr float kFps = 24.f;
constexpr int kFrames = 72; // 3.0 s at 24 fps

float hashUnit(std::uint32_t seed, std::uint32_t index, std::uint32_t channel) {
    std::uint32_t x = seed ^ (index * 0x9E3779B9u) ^ (channel * 0x85EBCA6Bu);
    x ^= x >> 16;
    x *= 0x7FEB352Du;
    x ^= x >> 15;
    x *= 0x846CA68Bu;
    x ^= x >> 16;
    return static_cast<float>(x & 0x00FFFFFFu) / static_cast<float>(0x01000000u);
}

class SpoilersAssetBackend {
public:
    ContentHandle text(const TextRequest& request) {
        return make("text/" + request.text, ContentKind::Text,
                    {1920.f, 700.f});
    }

    ContentHandle image(const ImageRequest& request) {
        return make(request.path, ContentKind::Image, {kWidth, kHeight});
    }

    ContentHandle video(const VideoRequest& request) {
        return make(request.path, ContentKind::Video, {kWidth, kHeight});
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
        handle.metrics.fingerprint = "spoilers-title-v1:" + handle.id;
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }

    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;
};

void addDustSpecks(TemplateScene& scene, std::uint32_t seed) {
    constexpr int kDustCount = 135;
    for (int i = 0; i < kDustCount; ++i) {
        const auto idx = static_cast<std::uint32_t>(i);
        const float uX = hashUnit(seed, idx, 1);
        const float uY = hashUnit(seed, idx, 2);
        const float uSize = hashUnit(seed, idx, 3);
        const float uAlpha = hashUnit(seed, idx, 4);
        const float uTone = hashUnit(seed, idx, 5);
        const float uDx = (hashUnit(seed, idx, 6) - 0.5f) * 14.f;
        const float uDy = (hashUnit(seed, idx, 7) - 0.5f) * 10.f;

        const float diameter = 1.8f + uSize * uSize * 5.2f;
        const float x = 24.f + uX * (kWidth - 48.f);
        const float y = 24.f + uY * (kHeight - 48.f);
        const float baseOpacity = 0.14f + uAlpha * 0.58f;

        std::string color = "#EAE8E1";
        if (uTone < 0.33f) color = "#BFBBB2";
        else if (uTone < 0.66f) color = "#D9D6CE";

        ShapeSpec speck{};
        speck.name = "dust_speck_" + std::to_string(i);
        speck.size = Vector2(diameter, diameter);
        speck.geometry = ShapeGeometry::Ellipse;
        speck.fillColor = color;

        auto& h = scene.shape(speck);
        h.position(x, y)
         .opacity(baseOpacity)
         .alive(0, kFrames - 1)
         .animatePosition(0, kFrames - 1, Vector3(uDx, uDy, 0.f));

        if (i % 3 == 0) {
            const float peak = std::min(0.85f, baseOpacity * 1.35f);
            h.animateOpacity(0, kFrames / 2, baseOpacity, peak)
             .animateOpacity(kFrames / 2, kFrames - 1, peak, baseOpacity);
        }
    }
}

void addLintFibers(TemplateScene& scene, std::uint32_t seed) {
    constexpr int kFiberCount = 34;
    for (int i = 0; i < kFiberCount; ++i) {
        const auto idx = static_cast<std::uint32_t>(i);
        const float uX = hashUnit(seed, idx, 10);
        const float uY = hashUnit(seed, idx, 11);
        const float uLen = hashUnit(seed, idx, 12);
        const float uAng = hashUnit(seed, idx, 13) * 6.2831853f;
        const float uCurve1 = (hashUnit(seed, idx, 14) - 0.5f) * 26.f;
        const float uCurve2 = (hashUnit(seed, idx, 15) - 0.5f) * 26.f;
        const float uAlpha = hashUnit(seed, idx, 16);
        const float uDx = (hashUnit(seed, idx, 17) - 0.5f) * 10.f;
        const float uDy = (hashUnit(seed, idx, 18) - 0.5f) * 8.f;

        const float boxSize = 90.f;
        const float half = boxSize * 0.5f;
        const float len = 18.f + uLen * 44.f;
        const float ca = std::cos(uAng);
        const float sa = std::sin(uAng);
        const float nx = -sa;
        const float ny = ca;

        const float p0x = half - ca * (len * 0.5f);
        const float p0y = half - sa * (len * 0.5f);
        const float p3x = half + ca * (len * 0.5f);
        const float p3y = half + sa * (len * 0.5f);
        const float c1x = half - ca * (len * 0.16f) + nx * uCurve1;
        const float c1y = half - sa * (len * 0.16f) + ny * uCurve1;
        const float c2x = half + ca * (len * 0.16f) + nx * uCurve2;
        const float c2y = half + sa * (len * 0.16f) + ny * uCurve2;

        ShapeSpec fiber{};
        fiber.name = "lint_fiber_" + std::to_string(i);
        fiber.size = Vector2(boxSize, boxSize);
        fiber.geometry = ShapeGeometry::Path;
        fiber.fillEnabled = false;
        fiber.strokeColor = (i % 2 == 0) ? "#DAD7CF" : "#B4B0A8";
        fiber.strokeWidth = 1.35f + hashUnit(seed, idx, 19) * 0.9f;
        fiber.strokeCap = "round";
        fiber.strokeJoin = "round";
        fiber.path = {
            ShapePathCommand::moveTo(p0x, p0y),
            ShapePathCommand::cubicTo(c1x, c1y, c2x, c2y, p3x, p3y),
        };

        const float x = 40.f + uX * (kWidth - 80.f);
        const float y = 40.f + uY * (kHeight - 80.f);
        scene.shape(fiber)
             .position(x, y)
             .opacity(0.18f + uAlpha * 0.36f)
             .alive(0, kFrames - 1)
             .animatePosition(0, kFrames - 1, Vector3(uDx, uDy, 0.f));
    }
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: chronontemplate_emit_spoilers_title <output-plan-path> [output-mp4-path]\n";
        return 2;
    }
    const std::filesystem::path planPath = argv[1];
    const std::string mp4Path = (argc >= 3)
        ? std::string(argv[2])
        : (planPath.parent_path() / "spoilers_chronontemplate.mp4").string();

    try {
        if (planPath.has_parent_path()) {
            std::filesystem::create_directories(planPath.parent_path());
        }

        SpoilersAssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& request) { return backend.text(request); },
            .createImage = [&](const ImageRequest& request) { return backend.image(request); },
            .createVideo = [&](const VideoRequest& request) { return backend.video(request); },
            .createShape = [&](const ShapeRequest& request) { return backend.shape(request); },
            .currentFingerprint = [&](const ContentId& id) { return backend.fingerprint(id); }});

        TemplateScene scene("spoilers_reference_recreation", kFps, host, kWidth, kHeight);
        scene.camera().setFov(53.14f);

        // 1. Deep black backdrop.
        ShapeSpec background{};
        background.name = "black_backdrop";
        background.size = Vector2(kWidth, kHeight);
        background.fillColor = "#000000";
        scene.shape(background)
             .position(kWidth * 0.5f, kHeight * 0.5f)
             .alive(0, kFrames - 1);

        // 2. Procedural film dust & curved lint fibers.
        addDustSpecks(scene, 1997u);
        addLintFibers(scene, 4242u);

        // 3. SPOILERS title: smooth deep crimson fill, bright glowing rim, soft optical diffusion.
        TextSpec title{};
        title.name = "spoilers_title";
        title.text = "SPOILERS";
        title.font = "Chronon3d/assets/fonts/SF-Pro-Display-Black.otf";
        title.fontSize = 310.f;
        title.color = "#861103";
        title.stroke = TextStrokeStyle{
            .color = "#C81C0A",
            .width = 4.2f,
            .mode = "vector"
        };
        title.glow = TextGlowStyle{
            .color = "#E0200C",
            .radius = 12.f,
            .intensity = 0.75f
        };
        title.effectGlow = TextGlowStyle{
            .color = "#D61B09",
            .radius = 26.f,
            .intensity = 0.70f
        };
        title.halation = TextHalationStyle{
            .threshold = 0.10f,
            .softness = 0.25f,
            .radiusPx = 20.f,
            .intensity = 0.85f,
            .tint = {1.0f, 0.14f, 0.04f, 1.0f}
        };
        title.gaussianBlurRadius = 1.6f;

        scene.text(title)
             .position(kWidth * 0.5f, kHeight * 0.5f + 16.f)
             .alive(0, kFrames - 1);

        // 4. Composite optical adjustment layer: pincushion lens curvature,
        //    radial edge smear, subtle chromatic split, soft diffusion, vignette.
        AdjustmentSpec optics{};
        optics.name = "optical_lens_pass";
        optics.lensDistortion = AdjustmentLensDistortion{
            .curvature = -0.22f,
            .scale = 1.08f,
            .center = {0.5f, 0.5f}
        };
        optics.radialBlur = AdjustmentRadialBlur{
            .center = {0.5f, 0.5f},
            .amount = 0.45f,
            .renderSamples = 16,
            .previewSamples = 8
        };
        optics.chromaticAberration = AdjustmentChromaticAberration{
            .redOffset = 1.2f,
            .blueOffset = -1.2f,
            .offsetMode = 1
        };
        optics.gaussianBlurRadius = 0.7f;
        optics.vignette = AdjustmentVignette{
            .amount = 0.32f,
            .radius = 0.78f,
            .softness = 0.55f,
            .color = {0.f, 0.f, 0.f, 1.f}
        };
        scene.addAdjustment(std::move(optics));

        auto plan = lowerToRenderPlan(scene, host, "spoilers_chronontemplate_v1", mp4Path);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;

        std::ofstream file(planPath, std::ios::binary | std::ios::trunc);
        if (!file || !(file << renderPlanToJson(plan))) {
            throw std::runtime_error("failed to write RenderPlan: " + planPath.string());
        }
        std::cout << "Wrote " << planPath << " (" << plan.layers.size() << " layers)\n";
    } catch (const std::exception& e) {
        std::cerr << "emit_spoilers_title: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
