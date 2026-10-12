#include "chronontemplate/documentary_effects/BeforeAfterPack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <cmath>
#include <stdexcept>

namespace chronontemplate::docfx {

    namespace {

        void requireFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("beforeafter: ") + what + " must be finite");
        }

        void validate(const BeforeAfterSpec& spec) {
            requireFinite(spec.cardWidth, "cardWidth");
            requireFinite(spec.cardHeight, "cardHeight");
            requireFinite(spec.cardCenterX, "cardCenterX");
            requireFinite(spec.cardCenterY, "cardCenterY");
            requireFinite(spec.dividerWidth, "dividerWidth");
            requireFinite(spec.labelSize, "labelSize");
            if (spec.beforeAsset.empty() || spec.afterAsset.empty() ||
                spec.beforeLabel.empty() || spec.afterLabel.empty())
                throw std::invalid_argument("beforeafter: both assets and labels are required");
            if (spec.cardWidth <= 0.f || spec.cardWidth > 1920.f ||
                spec.cardHeight <= 0.f || spec.cardHeight > 1080.f ||
                spec.dividerWidth < 1.f || spec.dividerWidth > 32.f ||
                spec.labelSize <= 0.f || spec.labelSize > 128.f ||
                spec.inFrame < 0 || spec.sceneFrames < 1 || spec.sceneFrames > 900 ||
                spec.startFrame < spec.inFrame || spec.sweepFrames < 5 ||
                spec.sweepFrames > 300 || spec.holdFrames < 0 || spec.holdFrames > 300 ||
                spec.startFrame + 2 * spec.sweepFrames + spec.holdFrames >
                    spec.inFrame + spec.sceneFrames)
                throw std::invalid_argument("beforeafter: spec is outside supported ranges");
            if (!chronon3d::render_plan::parse_hex_color(spec.dividerColor))
                throw std::invalid_argument("beforeafter: dividerColor must be #RRGGBB");
        }

        float ease(float p) {
            p = std::clamp(p, 0.f, 1.f);
            return p * p * (3.f - 2.f * p);
        }

    } // namespace

    float afterSplit(const BeforeAfterSpec& spec, int frame) {
        const int out = spec.startFrame + spec.sweepFrames;
        const int back = out + spec.holdFrames;
        const int done = back + spec.sweepFrames;
        if (frame <= spec.startFrame) return 0.f;
        if (frame < out)
            return ease(static_cast<float>(frame - spec.startFrame) /
                        static_cast<float>(spec.sweepFrames));
        if (frame < back) return 1.f;
        if (frame < done)
            return 1.f - ease(static_cast<float>(frame - back) /
                              static_cast<float>(spec.sweepFrames));
        return 0.f;
    }

    BeforeAfterLayers addBeforeAfter(TemplateScene& scene,
                                     const BeforeAfterSpec& spec) {
        validate(spec);
        const int endFrame = spec.inFrame + spec.sceneFrames;
        BeforeAfterLayers layers{};
        const chrononmotion::Vector2 card(spec.cardWidth, spec.cardHeight);
        const int done = spec.startFrame + 2 * spec.sweepFrames + spec.holdFrames;

        LayerHandle& before = scene.image(ImageSpec{
                .path = spec.beforeAsset, .name = "comparison_before",
                .fit = ImageFitMode::Cover, .targetSize = card});
        before.position(spec.cardCenterX, spec.cardCenterY);
        before.alive(spec.inFrame, endFrame);
        before.animate(FadeIn{.inFrame = spec.inFrame, .duration = 16});
        before.animate(FadeOut{.startFrame = endFrame - 16, .duration = 16});
        layers.before = before.id();

        LayerHandle& after = scene.image(ImageSpec{
                .path = spec.afterAsset, .name = "comparison_after",
                .fit = ImageFitMode::Cover, .targetSize = card});
        after.position(spec.cardCenterX, spec.cardCenterY);
        after.alive(spec.inFrame, endFrame);
        after.animate(FadeIn{.inFrame = spec.inFrame, .duration = 16});
        after.animate(FadeOut{.startFrame = endFrame - 16, .duration = 16});
        layers.after = after.id();

        // Divider rides the split: left edge -> right edge -> back.
        const float x0 = spec.cardCenterX - spec.cardWidth * 0.5f;
        LayerHandle& divider = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.dividerWidth, spec.cardHeight),
                .fillColor = spec.dividerColor, .name = "comparison_divider"});
        divider.position(x0, spec.cardCenterY);
        divider.alive(spec.startFrame, done);
        divider.animatePosition(spec.startFrame, spec.sweepFrames,
                                chrononmotion::Vector3(spec.cardWidth, 0.f, 0.f),
                                chrononmotion::motion::Easing::easeInOut());
        divider.animatePosition(spec.startFrame + spec.sweepFrames + spec.holdFrames,
                                spec.sweepFrames,
                                chrononmotion::Vector3(-spec.cardWidth, 0.f, 0.f),
                                chrononmotion::motion::Easing::easeInOut());
        divider.animateOpacity(spec.startFrame, 10, 0.f, 1.f);
        divider.animateOpacity(done - 10, 10, 1.f, 0.f);
        layers.divider = divider.id();

        LayerHandle& beforeTag = scene.text(TextSpec{
                .text = spec.beforeLabel, .fontSize = spec.labelSize,
                .color = "#F5F2EA", .name = "comparison_tag_before"});
        beforeTag.position(x0 + 110.f, spec.cardCenterY - spec.cardHeight * 0.5f + 60.f);
        beforeTag.alive(spec.inFrame, endFrame);
        beforeTag.animateOpacity(spec.inFrame, 12, 0.f, 0.95f);
        LayerHandle& afterTag = scene.text(TextSpec{
                .text = spec.afterLabel, .fontSize = spec.labelSize,
                .color = "#F5F2EA", .name = "comparison_tag_after"});
        afterTag.position(x0 + spec.cardWidth - 110.f,
                          spec.cardCenterY - spec.cardHeight * 0.5f + 60.f);
        afterTag.alive(spec.inFrame, endFrame);
        afterTag.animateOpacity(spec.inFrame, 12, 0.f, 0.95f);
        return layers;
    }

    const char* beforeAfterId() noexcept {
        return "docfx_before_after_v1";
    }

} // namespace chronontemplate::docfx
