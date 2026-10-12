// ChrononTemplate — redacted document reveal.
//
// A paper document carries black redaction bars that retract staggered,
// then a red DECLASSIFIED-style stamp slams in. Fully authored with
// existing primitives (shapes, text, motion): no renderer-side gap.

#ifndef CHRONONTEMPLATE_REDACTED_PACK_HPP
#define CHRONONTEMPLATE_REDACTED_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate::docfx {

    /// One black bar in normalized card coordinates (origin 0..1 from the
    /// card's top-left, size 0..1 fractions of the card).
    struct RedactionBar {
        float x{0.1f};
        float y{0.2f};
        float w{0.8f};
        float h{0.06f};
        int retractDelay{0}; ///< extra frames after the stagger slot
    };

    struct RedactedSpec {
        std::string paperColor{"#EDE6D6"};
        float cardWidth{860.f};
        float cardHeight{1080.f};
        float cardCenterX{960.f};
        float cardCenterY{540.f};
        std::vector<RedactionBar> bars{{0.1f, 0.15f, 0.8f, 0.06f, 0},
                                       {0.1f, 0.35f, 0.6f, 0.06f, 10}};
        int startFrame{10};
        int staggerFrames{14};    ///< retract onset spacing per bar
        int retractFrames{18};    ///< each bar slides out to the right
        std::string stampText{"DECLASSIFIED"};
        std::string stampColor{"#B3282D"};
        float stampFontSize{92.f};
        int stampFrame{90};       ///< slam entrance frame
        int inFrame{0};
        int sceneFrames{150};
    };

    struct RedactedLayers {
        MotionLayerId paper{0};
        MotionLayerId stamp{0};
    };

    /// Author the paper, the retracting bars and the slamming stamp.
    /// Throws std::invalid_argument on any out-of-range spec value.
    [[nodiscard]] RedactedLayers addRedactedDocument(TemplateScene& scene,
                                                     const RedactedSpec& spec);

    /// Bar retract progress 0..1 at `frame` for bar `index` (staggered).
    [[nodiscard]] float barRetract(const RedactedSpec& spec, std::size_t index, int frame);

    [[nodiscard]] const char* redactedId() noexcept;

} // namespace chronontemplate::docfx

#endif // CHRONONTEMPLATE_REDACTED_PACK_HPP
