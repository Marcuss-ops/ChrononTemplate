// ChrononTemplate — archival documentary timeline reveal.
//
// A historic paper clipping over a drawn timeline axis, with a year and a
// gold headline below. Fully authored with existing primitives (background
// dust, image torn edges, keyed scale tracks, text, camera push): no
// renderer-side gap.

#ifndef CHRONONTEMPLATE_ARCHIVAL_TIMELINE_PACK_HPP
#define CHRONONTEMPLATE_ARCHIVAL_TIMELINE_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>

namespace chronontemplate::docfx {

    struct ArchivalTimelineSpec {
        std::string year{"1971"};
        std::string headline{"EXPOSED BY THE MEDIA"};
        std::string paperAsset{
            "ChrononTemplate/assets/archival_timeline_reveal_v1/paper_card.png"};
        float paperWidth{790.f};
        float lineY{710.f};
        float yearFontSize{76.f};
        float headlineFontSize{72.f};
        std::string headlineColor{"#AD8A47"};
        int sceneFrames{180}; ///< 6 s at 30 fps
        int inFrame{0};
    };

    struct ArchivalTimelineLayers {
        MotionLayerId background{0};
        MotionLayerId paper{0};
        MotionLayerId line{0};
        MotionLayerId year{0};
        MotionLayerId headlineShadow{0};
        MotionLayerId headline{0};
    };

    /// Author the dust background, the torn paper clipping, the drawn axis,
    /// the year, the headline and the slow camera push.
    /// Throws std::invalid_argument on any out-of-range spec value.
    [[nodiscard]] ArchivalTimelineLayers addArchivalTimelineReveal(
        TemplateScene& scene, const ArchivalTimelineSpec& spec);

    /// Axis draw progress 0..1 at `frame` (left-anchored scale reveal).
    [[nodiscard]] float axisReveal(const ArchivalTimelineSpec& spec, int frame);

    [[nodiscard]] const char* archivalTimelineId() noexcept;

} // namespace chronontemplate::docfx

#endif // CHRONONTEMPLATE_ARCHIVAL_TIMELINE_PACK_HPP
