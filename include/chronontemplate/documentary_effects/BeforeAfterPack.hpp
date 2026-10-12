// ChrononTemplate — before/after comparison wipe.
//
// Two versions of one scene sit stacked while a divider bar travels
// across, wiping from "before" to "after" and back. The C++ side owns the
// validated spec, the motion half (traveling divider, labels) and the
// exact split math; the per-pixel wipe is renderer-side (the
// motion/render-plan contract carries no masks), mirroring brushReveal.

#ifndef CHRONONTEMPLATE_BEFORE_AFTER_PACK_HPP
#define CHRONONTEMPLATE_BEFORE_AFTER_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <string>

namespace chronontemplate::docfx {

    struct BeforeAfterSpec {
        std::string beforeAsset{};
        std::string afterAsset{};
        float cardWidth{1240.f};
        float cardHeight{700.f};
        float cardCenterX{960.f};
        float cardCenterY{540.f};
        int startFrame{10};
        int sweepFrames{50};   ///< divider travel across the card
        int holdFrames{20};    ///< full-after hold before sweeping back
        float dividerWidth{6.f};
        std::string dividerColor{"#FFFFFF"};
        std::string beforeLabel{"BEFORE"};
        std::string afterLabel{"AFTER"};
        float labelSize{44.f};
        int inFrame{0};
        int sceneFrames{150};
    };

    struct BeforeAfterLayers {
        MotionLayerId before{0};
        MotionLayerId after{0};
        MotionLayerId divider{0};
    };

    /// Author both cards, the traveling divider and the labels.
    /// Throws std::invalid_argument on any out-of-range spec value.
    [[nodiscard]] BeforeAfterLayers addBeforeAfter(TemplateScene& scene,
                                                   const BeforeAfterSpec& spec);

    /// Visible "after" fraction 0..1 at `frame`: sweeps out, holds, sweeps
    /// back. Pure function of the spec.
    [[nodiscard]] float afterSplit(const BeforeAfterSpec& spec, int frame);

    [[nodiscard]] const char* beforeAfterId() noexcept;

} // namespace chronontemplate::docfx

#endif // CHRONONTEMPLATE_BEFORE_AFTER_PACK_HPP
