#include "chronontemplate/backgrounds/BackgroundPack.hpp"

#include <algorithm>
#include <stdexcept>
#include <utility>

namespace chronontemplate {

    namespace {

        using chrononmotion::Vector2;

        [[nodiscard]] int exitFramesFor(int duration) {
            return std::max(1, std::min(18, duration / 8));
        }

    }// namespace

    const char* backgroundLookId(BackgroundLook look) noexcept {
        switch (look) {
            case BackgroundLook::SolidTint: return "bg_solid_tint";
            case BackgroundLook::LetterboxBars: return "bg_letterbox_bars";
            case BackgroundLook::VerticalSplit: return "bg_vertical_split";
            case BackgroundLook::VignettePulse: return "bg_vignette_pulse";
            case BackgroundLook::CornerGlow: return "bg_corner_glow";
        }
        return "unknown";
    }

    std::vector<BackgroundLook> backgroundLooks() {
        return {BackgroundLook::SolidTint, BackgroundLook::LetterboxBars,
                BackgroundLook::VerticalSplit, BackgroundLook::VignettePulse,
                BackgroundLook::CornerGlow};
    }

    BackgroundComposition addBackground(TemplateScene& scene, const BackgroundSpec& spec) {
        if (spec.duration <= 0) {
            throw std::invalid_argument("addBackground: the duration must be positive");
        }
        if (!(spec.barFraction >= 0.f) || spec.barFraction >= 0.5f) {
            throw std::invalid_argument("addBackground: the bar fraction must be in [0, 0.5)");
        }
        if (!(spec.pulse >= 0.f) || spec.pulse > 1.f) {
            throw std::invalid_argument("addBackground: the pulse must be in [0, 1]");
        }

        const Vector2 canvas = scene.canvas();
        const int inFrame = spec.inFrame;
        const int endFrame = spec.inFrame + spec.duration;
        const int exitFrames = exitFramesFor(spec.duration);
        const int exitStart = endFrame - exitFrames;
        const int enterFrames = std::max(1, spec.duration / 10);

        const auto dress = [&](LayerHandle& layer, const char* suffix) {
            layer.alive(inFrame, endFrame);
            layer.animate(FadeIn{.inFrame = inFrame, .duration = enterFrames});
            layer.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
            (void) suffix;
            return &layer;
        };

        BackgroundComposition out;
        out.inFrame = inFrame;
        out.endFrame = endFrame;

        LayerHandle& ground = scene.shape(ShapeSpec{.size = canvas,
                                                    .fillColor = spec.ground,
                                                    .name = spec.name + "_ground"});
        ground.position(canvas.x * 0.5f, canvas.y * 0.5f);
        out.ground = dress(ground, "ground");

        switch (spec.look) {
            case BackgroundLook::SolidTint:
                break;

            case BackgroundLook::LetterboxBars: {
                const float barHeight = canvas.y * spec.barFraction;
                if (barHeight > 0.f) {
                    LayerHandle& top = scene.shape(ShapeSpec{
                            .size = Vector2(canvas.x, barHeight),
                            .fillColor = spec.accent,
                            .name = spec.name + "_bar_top"});
                    top.position(canvas.x * 0.5f, barHeight * 0.5f);
                    out.accents.push_back(dress(top, "bar_top"));

                    LayerHandle& bottom = scene.shape(ShapeSpec{
                            .size = Vector2(canvas.x, barHeight),
                            .fillColor = spec.accent,
                            .name = spec.name + "_bar_bottom"});
                    bottom.position(canvas.x * 0.5f, canvas.y - barHeight * 0.5f);
                    out.accents.push_back(dress(bottom, "bar_bottom"));
                }
                break;
            }

            case BackgroundLook::VerticalSplit: {
                const float halfWidth = canvas.x * 0.5f;
                LayerHandle& left = scene.shape(ShapeSpec{
                        .size = Vector2(halfWidth, canvas.y),
                        .fillColor = spec.accent,
                        .name = spec.name + "_left"});
                left.position(halfWidth * 0.5f, canvas.y * 0.5f);
                out.accents.push_back(dress(left, "left"));

                const float seamWidth = std::max(2.f, canvas.x * 0.004f);
                LayerHandle& seam = scene.shape(ShapeSpec{
                        .size = Vector2(seamWidth, canvas.y),
                        .fillColor = spec.seam,
                        .name = spec.name + "_seam"});
                seam.position(canvas.x * 0.5f, canvas.y * 0.5f);
                out.accents.push_back(dress(seam, "seam"));
                break;
            }

            case BackgroundLook::VignettePulse: {
                LayerHandle& veil = scene.shape(ShapeSpec{
                        .size = canvas,
                        .fillColor = spec.accent,
                        .name = spec.name + "_veil"});
                veil.position(canvas.x * 0.5f, canvas.y * 0.5f);
                veil.alive(inFrame, endFrame);
                const float low = std::max(0.f, 0.5f - spec.pulse);
                const float high = std::min(1.f, 0.5f + spec.pulse);
                const int half = std::max(1, spec.duration / 2);
                veil.animateOpacity(inFrame, half, low, high);
                veil.animateOpacity(inFrame + half, half, high, low);
                out.accents.push_back(&veil);
                break;
            }

            case BackgroundLook::CornerGlow: {
                const float block = std::min(canvas.x, canvas.y) * 0.45f;
                LayerHandle& glow = scene.shape(ShapeSpec{
                        .size = Vector2(block, block),
                        .fillColor = spec.accent,
                        .name = spec.name + "_glow",
                        .cornerRadius = block * 0.5f});
                glow.position(block * 0.5f, block * 0.5f);
                glow.alive(inFrame, endFrame);
                const float low = std::max(0.f, 0.35f - spec.pulse);
                const float high = std::min(1.f, 0.35f + spec.pulse);
                const int half = std::max(1, spec.duration / 2);
                glow.animateOpacity(inFrame, half, low, high);
                glow.animateOpacity(inFrame + half, half, high, low);
                out.accents.push_back(&glow);
                break;
            }
        }

        return out;
    }

}// namespace chronontemplate
