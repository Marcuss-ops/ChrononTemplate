#ifndef CHRONONTEMPLATE_VINTAGE_DOCUMENTARY_PACK_HPP
#define CHRONONTEMPLATE_VINTAGE_DOCUMENTARY_PACK_HPP

// ChrononTemplate — vintage documentary look: torn-paper photo card with
// analog grading, black atmospheric background with a diffuse dark-red light,
// glowing yellow title, and a short digital slice glitch finale.
//
// The pack authors content and motion only. Every pixel effect lowers through
// the existing primitives owned elsewhere: ImageFrameStyle grading/grain
// (PlanLowering), RoughenEdges torn alpha, square-wave scanlines, Mosaic
// blocks, ChromaticAberration RGB split, text GlowStyle, radial-gradient
// shapes, and deterministic dust dots. No new renderer, no new effect kind.

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate::vintage_documentary {

    /// Analog photo grading + torn edge. All values mirror the recipe
    /// defaults for a 1920x1080 canvas; validation is fail-closed.
    struct VintagePhotoTreatment {
        float saturation{0.72f};    ///< [0,4], faded vintage grade
        float contrast{0.95f};      ///< [0,16], slightly softened
        float grain{0.018f};        ///< [0,1], fine surface grain
        std::uint32_t grainSeed{7}; ///< deterministic grain
        float vignette{0.10f};      ///< [0,1] inside the photo
        float cornerRadius{14.f};   ///< px, soft analog corners
        // Torn-paper alpha edge (RoughenEdges on the cutout boundary).
        float tornEdgeAmount{7.f};  ///< (0,64] px; 0 disables
        float tornEdgeScale{9.f};   ///< (0,1024]
        std::uint32_t tornEdgeSeed{7};
        // Scanlines live INSIDE the photo only.
        float scanlineIntensity{0.06f}; ///< [0,0.25]
        float scanlineSpacing{0.004f};  ///< [0.002,1] normalized wavelength
        // Muted pink wash over the photo (normal-blend veil, not a grade).
        std::string tintColor{"#D9A7A0"};
        float tintOpacity{0.14f};   ///< [0,1]
        // Soft halo bleeding from behind the cutout edges.
        std::string edgeGlowColor{"#FFF6D8"};
        float edgeGlowOpacity{0.10f}; ///< [0,1]
    };

    /// Black atmospheric backdrop: dominant black, one diffuse dark-red
    /// radial light, sparse dust, vignette, fine grain. Dust is composited
    /// over the whole scene by the caller ordering (bg first).
    struct AtmosphericBackground {
        std::string baseColor{"#050505"};
        std::string lightColor{"#52090D"};
        float lightCenterX{0.5f};   ///< [0,1] normalized canvas
        float lightCenterY{0.5f};
        float lightRadius{0.62f};   ///< (0,2] normalized
        float lightOpacity{0.22f};  ///< [0,1] — stays an atmosphere, not a disc
        std::uint32_t dustCount{36};///< [0,256] film-dust dots
        std::uint32_t dustSeed{42};
        float dustOpacity{0.25f};   ///< [0,1]
        float vignetteStrength{0.45f}; ///< [0,1] darkened edges
        float grain{0.02f};         ///< [0,1] backdrop grain
        std::uint32_t grainSeed{99};
    };

    /// Glowing title: thin white divider (with halo sandwich) plus the
    /// yellow title drawn twice — wide soft halo below, tight glow above.
    struct VintageTitle {
        std::string text{};
        std::string font{};
        float fontSize{64.f};
        std::string color{"#F3CA43"};
        // Wide halo layer.
        float glowWideRadius{65.f};   ///< [0,256]
        float glowWideIntensity{0.18f}; ///< [0,4]
        std::string glowWideColor{"#E4E6A0"};
        // Tight hot glow layer.
        float glowSmallRadius{12.f};
        float glowSmallIntensity{0.45f};
        float dividerWidth{420.f};    ///< px white rule above the title
        float dividerOpacity{0.9f};
    };

    /// Modern brush reveal: the photo paints itself across the card while
    /// pushing in slightly. The C++ side owns the validated spec, the
    /// motion half (ScalePop push-in, title timing) and the exact eased
    /// progress/edge/push math below; the per-pixel bristle wipe is
    /// renderer-side (the motion/render-plan contract carries no masks),
    /// implemented by the reference Python renderer with the same formula.
    enum class BrushDirection : std::uint8_t {
        RightToLeft, ///< painted mass grows leftwards (default, v2 sample)
        LeftToRight  ///< painted mass grows rightwards
    };

    struct BrushReveal {
        bool enabled{true};
        BrushDirection direction{BrushDirection::RightToLeft};
        int startFrame{0};
        int durationFrames{60}; ///< reveal sweep length
        std::uint32_t bristleSeed{11};
        float bristleAmplitudePx{44.f}; ///< (0,128] streak + blotch swing
        float edgeSoftnessPx{16.f};     ///< (0,64] smoothstep width
        float slant{-0.5f};             ///< [-1,1] top-lead bias (R2L)
        float pushFrom{1.08f};          ///< [1,1.5] content scale at start
        float pushTo{1.0f};             ///< [1,1.5] settled content scale
        int pushDurationFrames{70};     ///< ease-out settle window
        std::string leadColor{"#FFF6D2"};
        float leadIntensity{0.35f};     ///< [0,1] wet-paint edge highlight
        /// Real local photo for the card; empty keeps spec.photoAsset.
        std::string photoAsset{};
    };

    /// Closing digital break: a duplicate of the photo, alive only in the
    /// glitch window, carrying alternating-row slice displacement, RGB
    /// channel split and mosaic blocks. Deterministic for a given seed.
    struct DigitalSliceGlitch {
        int startFrame{0};
        int durationFrames{10};     ///< 8-12 at 30fps
        float sliceDisplace{0.6f};  ///< [0,1] alternating-row displacement
        float rgbSplitPx{5.f};      ///< [0,128] channel separation
        std::uint32_t mosaicBlockSize{12}; ///< 0 disables blocks, else [2,64]
        std::uint32_t seed{123};
    };

    /// One composed vintage documentary card: background, graded torn photo
    /// with tint wash and halo, divider + double-glow title, and the closing
    /// glitch duplicate. The camera is deliberately untouched (static).
    struct VintageDocumentaryScene {
        std::string name{"vintage_documentary"};
        std::string photoAsset{};
        float photoWidth{760.f};    ///< px card size on canvas
        float photoHeight{480.f};
        float photoCenterX{960.f};  ///< px canvas position
        float photoCenterY{430.f};
        VintagePhotoTreatment photo{};
        AtmosphericBackground background{};
        VintageTitle title{};
        float titleCenterY{790.f};
        BrushReveal brush{};
        DigitalSliceGlitch glitch{};
        int inFrame{0};
        int durationFrames{150};    ///< 5s at 30fps
    };

    /// Handles to every authored layer, for caller-side timing tweaks.
    struct VintageDocumentaryLayers {
        MotionLayerId background{0};
        MotionLayerId photo{0};
        MotionLayerId glitch{0};
    };

    /// Author the full scene. Throws std::invalid_argument on any invalid
    /// spec value. Static textures (torn edge, grain, dust) are baked once
    /// in the content requests; only transforms, opacity and the glitch
    /// window animate per frame.
    [[nodiscard]] VintageDocumentaryLayers addVintageDocumentaryScene(
            TemplateScene& scene, const VintageDocumentaryScene& spec);

    /// Eased reveal progress at `frame`: 0 before startFrame, smoothstep
    /// 0..1 across durationFrames, 1 after. Pure function of the spec.
    [[nodiscard]] float brushRevealProgress(const BrushReveal& brush, int frame);

    /// Reveal edge x in photo px, measured from the leading side:
    /// RightToLeft sweeps from photoWidth+40 down to -40.
    [[nodiscard]] float brushEdgeX(const BrushReveal& brush, int frame,
                                   float photoWidth);

    /// Content push-in scale at `frame`: ease-out pushFrom -> pushTo over
    /// pushDurationFrames from startFrame. Pure function of the spec.
    [[nodiscard]] float brushPushScale(const BrushReveal& brush, int frame);

    [[nodiscard]] const char* vintageDocumentaryId() noexcept;

} // namespace chronontemplate::vintage_documentary

#endif // CHRONONTEMPLATE_VINTAGE_DOCUMENTARY_PACK_HPP
