// ChrononTemplate — animated counters and date ruler.
//
// Election/economics graphics: a flip-book number counting from start to
// end in discrete steps plus a date ruler whose cursor scrubs across year
// ticks. Text content never changes mid-layer: each step is its own
// layer with its own alive window, so everything authors with existing
// primitives (text, shapes, motion): no renderer-side gap.

#ifndef CHRONONTEMPLATE_ANIMATED_COUNTERS_PACK_HPP
#define CHRONONTEMPLATE_ANIMATED_COUNTERS_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate::docfx {

    struct CounterSpec {
        long long startValue{0};
        long long endValue{100};
        int steps{10};            ///< flip-book steps across the window
        std::string prefix{};
        std::string suffix{};
        float fontSize{120.f};
        std::string color{"#F5F2EA"};
        float centerX{960.f};
        float centerY{420.f};
        // Date ruler below the counter.
        std::vector<std::string> years{};
        float rulerY{640.f};
        float rulerWidth{1100.f};
        float tickSize{36.f};
        std::string accentColor{"#E8B84A"};
        int startFrame{10};
        int stepFrames{9};        ///< frames each value holds
        int inFrame{0};
        int sceneFrames{150};
    };

    struct CounterLayers {
        MotionLayerId ruler{0};
        MotionLayerId cursor{0};
    };

    /// Author the flip-book values, the ruler, the cursor and the ticks.
    /// Throws std::invalid_argument on any out-of-range spec value.
    [[nodiscard]] CounterLayers addAnimatedCounters(TemplateScene& scene,
                                                     const CounterSpec& spec);

    /// Displayed value at `frame` (last step wins past the window).
    [[nodiscard]] long long counterValue(const CounterSpec& spec, int frame);

    /// Formatted "prefix + value + suffix" at `frame`.
    [[nodiscard]] std::string counterText(const CounterSpec& spec, int frame);

    /// Cursor 0..1 progress across the ruler at `frame`.
    [[nodiscard]] float rulerProgress(const CounterSpec& spec, int frame);

    [[nodiscard]] const char* animatedCountersId() noexcept;

} // namespace chronontemplate::docfx

#endif // CHRONONTEMPLATE_ANIMATED_COUNTERS_PACK_HPP
