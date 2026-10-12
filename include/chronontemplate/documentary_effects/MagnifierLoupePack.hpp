// ChrononTemplate — magnifier loupe inspection look.
//
// A ring travels across an archive card along an authored path while the
// card breathes underneath it. The C++ side owns the validated spec, the
// motion half (traveling ring, halo, synced push-in) and the exact loupe
// math; the pixel refraction inside the ring is renderer-side (the
// motion/render-plan contract carries no masks), mirroring brushReveal.

#ifndef CHRONONTEMPLATE_MAGNIFIER_LOUPE_PACK_HPP
#define CHRONONTEMPLATE_MAGNIFIER_LOUPE_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>

namespace chronontemplate::docfx {

    struct LoupeSpec {
        std::string photoAsset{};
        float cardWidth{760.f};
        float cardHeight{480.f};
        float cardCenterX{960.f};
        float cardCenterY{430.f};
        float ringRadius{110.f};      ///< px, ring stroke centerline
        float ringWidth{7.f};         ///< px stroke
        std::string ringColor{"#F5F2EA"};
        float haloIntensity{0.30f};   ///< [0,1] glow riding under the ring
        // Travel path, canvas px, eased over the window.
        float fromX{700.f};
        float fromY{430.f};
        float toX{1220.f};
        float toY{430.f};
        int startFrame{10};
        int durationFrames{80};
        float pushFrom{1.0f};         ///< synced card breath
        float pushTo{1.04f};
        int inFrame{0};
        int sceneFrames{150};
    };

    struct LoupeLayers {
        MotionLayerId card{0};
        MotionLayerId ring{0};
    };

    /// Author the card, the traveling ring (+halo) and the synced push-in.
    /// Throws std::invalid_argument on any out-of-range spec value.
    [[nodiscard]] LoupeLayers addMagnifierLoupe(TemplateScene& scene,
                                                const LoupeSpec& spec);

    /// Loupe center at `frame`: smoothstep travel from->to across the
    /// window, clamped outside it. Pure function of the spec.
    [[nodiscard]] chrononmotion::Vector2 loupeCenter(const LoupeSpec& spec, int frame);

    /// Synced card scale at `frame`: ease-out pushFrom -> pushTo.
    [[nodiscard]] float loupePush(const LoupeSpec& spec, int frame);

    [[nodiscard]] const char* magnifierLoupeId() noexcept;

} // namespace chronontemplate::docfx

#endif // CHRONONTEMPLATE_MAGNIFIER_LOUPE_PACK_HPP
