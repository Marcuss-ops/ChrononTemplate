// ChrononTemplate — true 2.5D photo parallax.
//
// One archive photo becomes two depth planes: the full frame drifts
// slowly behind while a cropped subject region floats faster in front,
// and the camera pushes through both. Unlike the single-plane drift,
// near and far separate. Fully authored with existing primitives
// (image crops, motion tracks, camera rig): no renderer-side gap.

#ifndef CHRONONTEMPLATE_DEPTH_PARALLAX_PACK_HPP
#define CHRONONTEMPLATE_DEPTH_PARALLAX_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <string>

namespace chronontemplate::docfx {

    struct DepthParallaxSpec {
        std::string photoAsset{};
        float cardWidth{960.f};
        float cardHeight{600.f};
        float cardCenterX{960.f};
        float cardCenterY{540.f};
        // Subject window, normalized 0..1 over the photo, drawnCOVER into
        // the same card rect so it registers over the background plane.
        float fgOriginX{0.30f};
        float fgOriginY{0.10f};
        float fgSizeW{0.40f};
        float fgSizeH{0.80f};
        float bgDriftX{40.f};   ///< px, background plane travel
        float bgDriftY{0.f};
        float fgDriftX{130.f};  ///< px, foreground plane travel (faster)
        float fgDriftY{-30.f};
        float cameraPush{300.f}; ///< rig dolly across the scene
        int inFrame{0};
        int sceneFrames{150};
    };

    struct DepthParallaxLayers {
        MotionLayerId background{0};
        MotionLayerId foreground{0};
    };

    /// Author both planes and the camera push. Throws std::invalid_argument
    /// on any out-of-range spec value.
    [[nodiscard]] DepthParallaxLayers addDepthParallax(TemplateScene& scene,
                                                       const DepthParallaxSpec& spec);

    /// Plane travel 0..1 at `frame` (smoothstep across the scene).
    [[nodiscard]] float parallaxProgress(const DepthParallaxSpec& spec, int frame);

    [[nodiscard]] const char* depthParallaxId() noexcept;

} // namespace chronontemplate::docfx

#endif // CHRONONTEMPLATE_DEPTH_PARALLAX_PACK_HPP
