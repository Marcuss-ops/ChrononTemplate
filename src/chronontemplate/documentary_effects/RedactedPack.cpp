#include "chronontemplate/documentary_effects/RedactedPack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <cmath>
#include <stdexcept>

namespace chronontemplate::docfx {

    namespace {

        void requireFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("redacted: ") + what + " must be finite");
        }

        void validate(const RedactedSpec& spec) {
            requireFinite(spec.cardWidth, "cardWidth");
            requireFinite(spec.cardHeight, "cardHeight");
            requireFinite(spec.cardCenterX, "cardCenterX");
            requireFinite(spec.cardCenterY, "cardCenterY");
            requireFinite(spec.stampFontSize, "stampFontSize");
            if (spec.paperColor.empty() || spec.stampText.empty())
                throw std::invalid_argument("redacted: paper color and stamp text are required");
            if (spec.bars.empty() || spec.bars.size() > 24)
                throw std::invalid_argument("redacted: 1-24 redaction bars are required");
            if (spec.cardWidth <= 0.f || spec.cardWidth > 1920.f ||
                spec.cardHeight <= 0.f || spec.cardHeight > 1080.f ||
                spec.stampFontSize <= 0.f || spec.stampFontSize > 256.f ||
                spec.inFrame < 0 || spec.sceneFrames < 1 || spec.sceneFrames > 900 ||
                spec.startFrame < spec.inFrame || spec.staggerFrames < 1 ||
                spec.staggerFrames > 120 || spec.retractFrames < 1 ||
                spec.retractFrames > 120 || spec.stampFrame < spec.inFrame ||
                spec.stampFrame > spec.inFrame + spec.sceneFrames)
                throw std::invalid_argument("redacted: spec is outside supported ranges");
            for (const auto& bar : spec.bars) {
                requireFinite(bar.x, "bar.x");
                requireFinite(bar.y, "bar.y");
                requireFinite(bar.w, "bar.w");
                requireFinite(bar.h, "bar.h");
                if (bar.x < 0.f || bar.y < 0.f || bar.w <= 0.f || bar.h <= 0.f ||
                    bar.x + bar.w > 1.f || bar.y + bar.h > 1.f || bar.retractDelay < 0 ||
                    bar.retractDelay > 300)
                    throw std::invalid_argument("redacted: bar rect must sit inside the card");
            }
            const int lastOnset = spec.startFrame +
                static_cast<int>(spec.bars.size() - 1) * spec.staggerFrames + 300;
            if (lastOnset < spec.startFrame ||
                spec.startFrame + static_cast<int>(spec.bars.size()) * spec.staggerFrames +
                        spec.retractFrames > spec.inFrame + spec.sceneFrames)
                throw std::invalid_argument("redacted: bar retractions overflow the scene");
            if (!chronon3d::render_plan::parse_hex_color(spec.paperColor) ||
                !chronon3d::render_plan::parse_hex_color(spec.stampColor))
                throw std::invalid_argument("redacted: colors must be #RRGGBB");
        }

    } // namespace

    float barRetract(const RedactedSpec& spec, std::size_t index, int frame) {
        if (index >= spec.bars.size()) return 1.f;
        const int onset = spec.startFrame + static_cast<int>(index) * spec.staggerFrames +
            spec.bars[index].retractDelay;
        if (frame <= onset) return 0.f;
        if (frame >= onset + spec.retractFrames) return 1.f;
        float p = static_cast<float>(frame - onset) / static_cast<float>(spec.retractFrames);
        return p * p * (3.f - 2.f * p);
    }

    RedactedLayers addRedactedDocument(TemplateScene& scene, const RedactedSpec& spec) {
        validate(spec);
        const int endFrame = spec.inFrame + spec.sceneFrames;
        RedactedLayers out{};
        const float x0 = spec.cardCenterX - spec.cardWidth * 0.5f;
        const float y0 = spec.cardCenterY - spec.cardHeight * 0.5f;

        LayerHandle& paper = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.cardWidth, spec.cardHeight),
                .fillColor = spec.paperColor, .name = "redacted_paper"});
        paper.position(spec.cardCenterX, spec.cardCenterY);
        paper.alive(spec.inFrame, endFrame);
        paper.animateOpacity(spec.inFrame, 16, 0.f, 1.f);
        paper.animateOpacity(endFrame - 16, 16, 1.f, 0.f);
        out.paper = paper.id();

        // Faint text lines under the bars so the reveal shows content.
        for (std::size_t i = 0; i < spec.bars.size(); ++i) {
            const auto& bar = spec.bars[i];
            LayerHandle& line = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(bar.w * spec.cardWidth * 0.96f, 8.f),
                    .fillColor = "#8A8474",
                    .name = "redacted_line_" + std::to_string(i)});
            line.position(x0 + (bar.x + bar.w * 0.5f) * spec.cardWidth,
                          y0 + (bar.y + bar.h * 0.5f) * spec.cardHeight);
            line.opacity(0.85f);
            line.alive(spec.inFrame, endFrame);
        }
        // Bars slide out to the right, staggered.
        for (std::size_t i = 0; i < spec.bars.size(); ++i) {
            const auto& bar = spec.bars[i];
            const float bw = bar.w * spec.cardWidth;
            const float bh = bar.h * spec.cardHeight;
            LayerHandle& cover = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(bw, bh),
                    .fillColor = "#0B0B0C",
                    .name = "redacted_bar_" + std::to_string(i)});
            const float cx = x0 + (bar.x + bar.w * 0.5f) * spec.cardWidth;
            const float cy = y0 + (bar.y + bar.h * 0.5f) * spec.cardHeight;
            cover.position(cx, cy);
            const int onset = spec.startFrame + static_cast<int>(i) * spec.staggerFrames +
                bar.retractDelay;
            cover.alive(spec.inFrame, onset + spec.retractFrames);
            cover.animatePosition(onset, spec.retractFrames,
                                  chrononmotion::Vector3(bw * 1.2f, 0.f, 0.f));
            cover.animateOpacity(onset + spec.retractFrames - 6, 6, 1.f, 0.f);
        }

        TextSpec stamp{.text = spec.stampText,
                       .fontSize = spec.stampFontSize,
                       .color = spec.stampColor,
                       .name = "redacted_stamp"};
        stamp.stroke = TextStrokeStyle{spec.stampColor, 2.f};
        LayerHandle& mark = scene.text(stamp);
        mark.position(spec.cardCenterX, spec.cardCenterY);
        mark.alive(spec.stampFrame, endFrame);
        mark.animate(ScalePop{.inFrame = spec.stampFrame, .duration = 14,
                              .from = 2.2f, .to = 1.f});
        mark.animate(FadeIn{.inFrame = spec.stampFrame, .duration = 6});
        out.stamp = mark.id();
        return out;
    }

    const char* redactedId() noexcept {
        return "docfx_redacted_v1";
    }

} // namespace chronontemplate::docfx
