#include "chronontemplate/documentary_effects/MagnifierLoupePack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <cmath>
#include <stdexcept>

namespace chronontemplate::docfx {

    namespace {

        void requireFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("loupe: ") + what + " must be finite");
        }

        void validate(const LoupeSpec& spec, float canvasW, float canvasH) {
            requireFinite(spec.cardWidth, "cardWidth");
            requireFinite(spec.cardHeight, "cardHeight");
            requireFinite(spec.cardCenterX, "cardCenterX");
            requireFinite(spec.cardCenterY, "cardCenterY");
            requireFinite(spec.ringRadius, "ringRadius");
            requireFinite(spec.ringWidth, "ringWidth");
            requireFinite(spec.haloIntensity, "haloIntensity");
            requireFinite(spec.fromX, "fromX");
            requireFinite(spec.fromY, "fromY");
            requireFinite(spec.toX, "toX");
            requireFinite(spec.toY, "toY");
            requireFinite(spec.pushFrom, "pushFrom");
            requireFinite(spec.pushTo, "pushTo");
            if (spec.photoAsset.empty())
                throw std::invalid_argument("loupe: photo asset is required");
            if (spec.cardWidth <= 0.f || spec.cardWidth > canvasW ||
                spec.cardHeight <= 0.f || spec.cardHeight > canvasH ||
                spec.cardCenterX < 0.f || spec.cardCenterX > canvasW ||
                spec.cardCenterY < 0.f || spec.cardCenterY > canvasH ||
                spec.ringRadius < 20.f || spec.ringRadius > 400.f ||
                spec.ringWidth < 1.f || spec.ringWidth > 32.f ||
                spec.haloIntensity < 0.f || spec.haloIntensity > 1.f ||
                spec.pushFrom < 1.f || spec.pushFrom > 1.5f ||
                spec.pushTo < 1.f || spec.pushTo > 1.5f ||
                spec.pushFrom > spec.pushTo ||
                spec.inFrame < 0 || spec.sceneFrames < 1 || spec.sceneFrames > 900 ||
                spec.startFrame < spec.inFrame || spec.durationFrames < 1 ||
                spec.durationFrames > 300 ||
                spec.startFrame + spec.durationFrames > spec.inFrame + spec.sceneFrames)
                throw std::invalid_argument("loupe: spec is outside supported ranges");
            if (!chronon3d::render_plan::parse_hex_color(spec.ringColor))
                throw std::invalid_argument("loupe: ringColor must be #RRGGBB");
        }

    } // namespace

    chrononmotion::Vector2 loupeCenter(const LoupeSpec& spec, int frame) {
        float p = 0.f;
        if (frame > spec.startFrame) {
            if (frame >= spec.startFrame + spec.durationFrames) {
                p = 1.f;
            } else {
                p = static_cast<float>(frame - spec.startFrame) /
                    static_cast<float>(spec.durationFrames);
                p = p * p * (3.f - 2.f * p);
            }
        }
        return chrononmotion::Vector2(spec.fromX + (spec.toX - spec.fromX) * p,
                                      spec.fromY + (spec.toY - spec.fromY) * p);
    }

    float loupePush(const LoupeSpec& spec, int frame) {
        if (frame <= spec.startFrame) return spec.pushFrom;
        if (frame >= spec.startFrame + spec.durationFrames) return spec.pushTo;
        const float p = static_cast<float>(frame - spec.startFrame) /
            static_cast<float>(spec.durationFrames);
        const float eased = 1.f - (1.f - p) * (1.f - p);
        return spec.pushFrom + (spec.pushTo - spec.pushFrom) * eased;
    }

    LoupeLayers addMagnifierLoupe(TemplateScene& scene, const LoupeSpec& spec) {
        validate(spec, scene.canvas().x, scene.canvas().y);
        const int endFrame = spec.inFrame + spec.sceneFrames;
        LoupeLayers out{};

        LayerHandle& card = scene.image(ImageSpec{
                .path = spec.photoAsset, .name = "loupe_card",
                .fit = ImageFitMode::Cover,
                .targetSize = chrononmotion::Vector2(spec.cardWidth, spec.cardHeight)});
        card.position(spec.cardCenterX, spec.cardCenterY);
        card.alive(spec.inFrame, endFrame);
        card.animate(FadeIn{.inFrame = spec.inFrame, .duration = 16});
        card.animate(ScalePop{.inFrame = spec.startFrame, .duration = spec.durationFrames,
                              .from = spec.pushFrom, .to = spec.pushTo});
        card.animate(FadeOut{.startFrame = endFrame - 16, .duration = 16});
        out.card = card.id();

        // Halo riding under the ring, then the ring itself: both follow the
        // authored travel with keyed position tracks.
        const auto travel = [&](LayerHandle& layer) {
            const chrononmotion::Vector2 a = loupeCenter(spec, spec.startFrame);
            const chrononmotion::Vector2 b = loupeCenter(spec, spec.startFrame + spec.durationFrames);
            layer.position(a.x, a.y);
            layer.alive(spec.inFrame, endFrame);
            layer.animatePosition(spec.startFrame, spec.durationFrames,
                                  chrononmotion::Vector3(b.x - a.x, b.y - a.y, 0.f),
                                  chrononmotion::motion::Easing::easeInOut());
        };
        const float haloR = spec.ringRadius * 2.6f;
        LayerHandle& halo = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(haloR, haloR),
                .fillColor = "#FFF6D8", .name = "loupe_halo",
                .geometry = ShapeGeometry::Ellipse});
        halo.opacity(spec.haloIntensity);
        travel(halo);
        halo.animateOpacity(spec.startFrame, 12, 0.f, spec.haloIntensity);
        halo.animateOpacity(endFrame - 12, 12, spec.haloIntensity, 0.f);

        const float ringD = spec.ringRadius * 2.f;
        LayerHandle& ring = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(ringD, ringD),
                .fillColor = "#FFFFFF", .name = "loupe_ring",
                .fillEnabled = false, .geometry = ShapeGeometry::Ellipse,
                .strokeColor = spec.ringColor, .strokeWidth = spec.ringWidth});
        travel(ring);
        ring.animateOpacity(spec.startFrame, 12, 0.f, 1.f);
        ring.animateOpacity(endFrame - 12, 12, 1.f, 0.f);
        out.ring = ring.id();
        return out;
    }

    const char* magnifierLoupeId() noexcept {
        return "docfx_magnifier_loupe_v1";
    }

} // namespace chronontemplate::docfx
