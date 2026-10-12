#include "chronontemplate/documentary_effects/AnimatedCountersPack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <cmath>
#include <stdexcept>

namespace chronontemplate::docfx {

    namespace {

        void requireFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("counters: ") + what + " must be finite");
        }

        void validate(const CounterSpec& spec) {
            requireFinite(spec.fontSize, "fontSize");
            requireFinite(spec.centerX, "centerX");
            requireFinite(spec.centerY, "centerY");
            requireFinite(spec.rulerY, "rulerY");
            requireFinite(spec.rulerWidth, "rulerWidth");
            requireFinite(spec.tickSize, "tickSize");
            if (spec.prefix.size() > 8 || spec.suffix.size() > 8)
                throw std::invalid_argument("counters: prefix/suffix are limited to 8 chars");
            if (spec.steps < 1 || spec.steps > 60 ||
                spec.fontSize <= 0.f || spec.fontSize > 400.f ||
                spec.centerX < 0.f || spec.centerX > 1920.f ||
                spec.centerY < 0.f || spec.centerY > 1080.f ||
                spec.rulerY < 0.f || spec.rulerY > 1080.f ||
                spec.rulerWidth <= 0.f || spec.rulerWidth > 1920.f ||
                spec.tickSize <= 0.f || spec.tickSize > 128.f ||
                spec.inFrame < 0 || spec.sceneFrames < 1 || spec.sceneFrames > 900 ||
                spec.startFrame < spec.inFrame || spec.stepFrames < 1 ||
                spec.stepFrames > 60 ||
                spec.startFrame + spec.steps * spec.stepFrames >
                    spec.inFrame + spec.sceneFrames ||
                spec.years.size() > 12)
                throw std::invalid_argument("counters: spec is outside supported ranges");
            for (const auto& year : spec.years) {
                if (year.empty() || year.size() > 12)
                    throw std::invalid_argument("counters: year labels must be 1-12 chars");
            }
            if (!chronon3d::render_plan::parse_hex_color(spec.color) ||
                !chronon3d::render_plan::parse_hex_color(spec.accentColor))
                throw std::invalid_argument("counters: colors must be #RRGGBB");
        }

    } // namespace

    long long counterValue(const CounterSpec& spec, int frame) {
        if (frame <= spec.startFrame) return spec.startValue;
        const int window = spec.steps * spec.stepFrames;
        if (frame >= spec.startFrame + window) return spec.endValue;
        const int step = (frame - spec.startFrame) / spec.stepFrames;
        const long long span = spec.endValue - spec.startValue;
        return spec.startValue + span * step / spec.steps;
    }

    std::string counterText(const CounterSpec& spec, int frame) {
        return spec.prefix + std::to_string(counterValue(spec, frame)) + spec.suffix;
    }

    float rulerProgress(const CounterSpec& spec, int frame) {
        const int window = spec.steps * spec.stepFrames;
        if (frame <= spec.startFrame) return 0.f;
        if (frame >= spec.startFrame + window) return 1.f;
        return static_cast<float>(frame - spec.startFrame) / static_cast<float>(window);
    }

    CounterLayers addAnimatedCounters(TemplateScene& scene, const CounterSpec& spec) {
        validate(spec);
        const int endFrame = spec.inFrame + spec.sceneFrames;
        const int window = spec.steps * spec.stepFrames;
        CounterLayers out{};

        // Flip-book values: one layer per step, handed off in sequence.
        for (int step = 0; step <= spec.steps; ++step) {
            const long long span = spec.endValue - spec.startValue;
            const long long value = spec.startValue + span * step / spec.steps;
            const int onset = spec.startFrame + step * spec.stepFrames;
            const int hold = (step == spec.steps)
                ? endFrame - onset
                : std::min(spec.stepFrames + 2, endFrame - onset);
            if (hold <= 0) continue;
            LayerHandle& digit = scene.text(TextSpec{
                    .text = spec.prefix + std::to_string(value) + spec.suffix,
                    .fontSize = spec.fontSize, .color = spec.color,
                    .name = "counter_" + std::to_string(step)});
            digit.position(spec.centerX, spec.centerY);
            digit.alive(onset, onset + hold);
            digit.animate(ScalePop{.inFrame = onset, .duration = 6, .from = 1.15f, .to = 1.f});
            digit.animate(FadeIn{.inFrame = onset, .duration = 3});
            if (step < spec.steps)
                digit.animate(FadeOut{.startFrame = onset + hold - 2, .duration = 2});
        }

        // Ruler rail, year ticks + labels, scrubbing cursor.
        const float rx0 = spec.centerX - spec.rulerWidth * 0.5f;
        LayerHandle& rail = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.rulerWidth, 6.f),
                .fillColor = spec.accentColor, .name = "counter_rail"});
        rail.position(spec.centerX, spec.rulerY);
        rail.opacity(0.6f);
        rail.alive(spec.startFrame, endFrame);
        out.ruler = rail.id();

        const std::size_t ticks = spec.years.empty() ? 5 : spec.years.size();
        for (std::size_t i = 0; i < ticks; ++i) {
            const float t = ticks == 1 ? 0.5f
                                       : static_cast<float>(i) / static_cast<float>(ticks - 1);
            const float x = rx0 + t * spec.rulerWidth;
            LayerHandle& tick = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(5.f, spec.tickSize),
                    .fillColor = "#F5F2EA",
                    .name = "counter_tick_" + std::to_string(i)});
            tick.position(x, spec.rulerY);
            tick.opacity(0.7f);
            tick.alive(spec.startFrame, endFrame);
            if (!spec.years.empty()) {
                LayerHandle& tag = scene.text(TextSpec{
                        .text = spec.years[i], .fontSize = spec.tickSize * 0.9f,
                        .color = "#B9B2A4", .name = "counter_year_" + std::to_string(i)});
                tag.position(x, spec.rulerY + spec.tickSize);
                tag.alive(spec.startFrame, endFrame);
                tag.animate(FadeIn{.inFrame = spec.startFrame, .duration = 8});
            }
        }
        LayerHandle& cursor = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(8.f, spec.tickSize * 1.8f),
                .fillColor = spec.accentColor, .name = "counter_cursor"});
        cursor.position(rx0, spec.rulerY);
        cursor.alive(spec.startFrame, spec.startFrame + window);
        cursor.animatePosition(spec.startFrame, window,
                               chrononmotion::Vector3(spec.rulerWidth, 0.f, 0.f),
                               chrononmotion::motion::Easing::easeInOut());
        out.cursor = cursor.id();
        return out;
    }

    const char* animatedCountersId() noexcept {
        return "docfx_animated_counters_v1";
    }

} // namespace chronontemplate::docfx
