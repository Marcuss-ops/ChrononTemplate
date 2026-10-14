#ifndef CHRONONTEMPLATE_VINTAGE_DOCUMENTARY_TITLE_01_PACK_HPP
#define CHRONONTEMPLATE_VINTAGE_DOCUMENTARY_TITLE_01_PACK_HPP

// ChrononTemplate — vintage documentary title card ("The / DOCUMENTARY /
// editing-style"): giant condensed title on near-black with deterministic
// analog motion. Companion of the VintageDocumentaryPack card.
//
// The pack authors content and motion only, through the existing primitives
// owned elsewhere: text requests with halo shadow (ContentHost), deterministic
// dust dots, vignette plate, and dense baked keyframes (the Motion lowering
// of weave / zoom / flicker). No new renderer, no new effect kind.
//
// Motion/track convention: Motion channels hold ABSOLUTE values (a keyed
// channel overrides the static pose); the RenderPlan lowering re-expresses
// position keys as offsets added to the static base. The deterministic twins
// below (weave, LCG flicker) are shared verbatim with the RenderPlan
// generator so both lowerings agree sample-for-sample.

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>

namespace chronontemplate::vintage_documentary {

    /// One film-grain layer: deterministic (seed, frame) noise.
    struct TitleGrain {
        float amount{0.08f};      ///< [0,1]
        std::uint32_t seed{42};   ///< fixed per recipe
        bool animated{true};      ///< temporal grain when true
    };

    /// Darkened edges (vignette plate).
    struct TitleVignette {
        float radius{0.72f};      ///< [0,1]
        float softness{0.55f};    ///< [0,1]
        float amount{0.38f};      ///< [0,1]
    };

    /// Sparse deterministic film dust over the whole scene.
    struct TitleDust {
        std::uint32_t count{45};  ///< [0,256]
        std::uint32_t seed{1234};
        float opacity{0.55f};      ///< [0,1]
    };

    /// Exposure flicker: deterministic per-hold lift around a base, plus a
    /// short analog flash on the way out. Holds advance every 3 frames.
    struct TitleFlicker {
        float baseLift{0.006f};   ///< [0,1] minimum white-veil opacity
        float variance{0.018f};   ///< [0,1] LCG-driven swing above the base
        float flashLift{0.07f};   ///< [0,1] exit-flash peak
        int flashFrame{132};      ///< first flash frame (exit window start)
    };

    /// Whole-frame film weave: two incommensurate sine pairs, same keys on
    /// every text layer so the frame moves as one piece.
    struct TitleWeave {
        float amplitude{1.0f};    ///< overall scale, px at 1.0
    };

    /// One typographic line of the card.
    struct TitleLine {
        std::string text{};
        std::string font{};
        float fontSize{92.f};     ///< (0,512]
        std::string color{"#EBEBEB"};
        float posX{960.f};        ///< px canvas, motion-space absolute
        float posY{540.f};
        int enterFrame{6};        ///< fade-in start, 15-frame rise
        float haloOpacity{0.25f}; ///< [0,1] white shadow halo (halation)
        float haloBlur{6.f};      ///< [0,256] halo softness
        float chromaSplit{0.8f};  ///< [0,128] red/blue ghosting, px
        float distressAmount{0.03f}; ///< [0,1] static grain on the glyphs
        std::uint32_t distressSeed{7};
    };

    /// One composed title card: background, three typographic lines,
    /// dust, vignette and the flicker veil. The camera is untouched.
    struct VintageDocumentaryTitle01Scene {
        std::string name{"vintage_documentary_title_01"};
        TitleLine small{};        ///< "The"
        TitleLine main{};         ///< "DOCUMENTARY"
        TitleLine script{};       ///< "editing-style"
        std::string backgroundColor{"#090909"};
        TitleGrain grain{};        ///< temporal grain (seed 42)
        TitleGrain flickerGrain{}; ///< second animated layer, finer
        TitleVignette vignette{};
        TitleDust dust{};
        TitleFlicker flicker{};
        TitleWeave weave{};
        float zoomFrom{1.0f};     ///< composition push-in
        float zoomTo{1.025f};
        int exitStartFrame{132};  ///< fade-out + flash window start
        int inFrame{0};
        int durationFrames{150};  ///< 5s at 30fps
    };

    /// Handles to every authored layer, for caller-side timing tweaks.
    struct VintageDocumentaryTitle01Layers {
        MotionLayerId background{0};
        MotionLayerId smallLine{0};
        MotionLayerId mainTitle{0};
        MotionLayerId scriptLine{0};
        MotionLayerId dust{0};
        MotionLayerId flickerVeil{0};
    };

    /// Deterministic [0,1) from an integer index (splitmix64): the same LCG
    /// stream the RenderPlan generator uses for flicker holds and dust.
    [[nodiscard]] float titleHash01(std::uint64_t index, std::uint64_t seed) noexcept;

    /// Film-weave offset of `frame` (absolute frames) along one axis.
    /// Matches the RenderPlan generator sample-for-sample.
    [[nodiscard]] float weaveOffsetX(int frame, float amplitude = 1.0f) noexcept;
    [[nodiscard]] float weaveOffsetY(int frame, float amplitude = 1.0f) noexcept;

    /// White-veil opacity of flicker hold `holdIndex` (one hold = 3 frames),
    /// including the exit flash. Matches the RenderPlan generator.
    [[nodiscard]] float flickerLift(const TitleFlicker& flicker, int holdIndex,
                                    int frame) noexcept;

    /// Author the full title card. Throws std::invalid_argument on any
    /// invalid spec value. Only transforms and opacity animate per frame;
    /// grain/distress/dust seeds are baked into the content requests.
    [[nodiscard]] VintageDocumentaryTitle01Layers addVintageDocumentaryTitle01Scene(
            TemplateScene& scene, const VintageDocumentaryTitle01Scene& spec);

    [[nodiscard]] const char* vintageDocumentaryTitle01Id() noexcept;

} // namespace chronontemplate::vintage_documentary

#endif // CHRONONTEMPLATE_VINTAGE_DOCUMENTARY_TITLE_01_PACK_HPP
