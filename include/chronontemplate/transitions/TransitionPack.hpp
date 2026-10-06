// ChrononTemplate — the declarative transition pack (BACKLOG item 4).
//
// A transition here is a small composition of native shape plates plus motion.
// Nothing rasterizes here — Chronon draws every plate exactly like every other
// shape layer — and motion is authored with ordinary transform/opacity tracks,
// so every transition is a pure function of (scene, frame) like the rest of the
// module. The rapid light looks are explicit shape approximations, not optical
// effects or RGB channel processing.
//
// The looks are editorial data; `transitionId` is the stable, catalog-facing
// name and is append-only.

#ifndef CHRONONTEMPLATE_TRANSITIONS_TRANSITION_PACK_HPP
#define CHRONONTEMPLATE_TRANSITIONS_TRANSITION_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// The transition looks the pack can assemble. Existing values are frozen;
    /// new looks are append-only so serialized enum values remain stable.
    enum class TransitionLook : std::uint8_t {
        Wipe,
        PushThrough,
        DipToBlack,
        DipToColor,
        Blinds,
        IrisCircle,
        GlitchSlices,
        LightLeak,
        BarnDoors,
        CurtainLift,
        DiamondIris,
        FourWayDoors,
        LightLeakFlashSweep,
        LightLeakCornerBurn,
        LightLeakWhiteout,
        LightLeakDiagonalCut,
        LightLeakDoublePass,
        LightLeakFilmBurn,
        LightLeakCenterBurst,
        LightLeakHorizontalWhip
    };

    struct TransitionDurationBounds {
        int minimumFrames{0};
        int maximumFrames{0};
    };

    [[nodiscard]] TransitionDurationBounds transitionDurationBounds(TransitionLook look) noexcept;
    [[nodiscard]] int recommendedTransitionDuration(TransitionLook look) noexcept;
    [[nodiscard]] bool isRapidTransition(TransitionLook look) noexcept;

    enum class TransitionTimingClass : std::uint8_t { Legacy, Micro, Normal, Hero };
    [[nodiscard]] TransitionTimingClass transitionTimingClass(TransitionLook look) noexcept;

    /// Suggested selector distribution; percentages sum to 100. It is catalog
    /// data only and does not imply that a random selector consumes it.
    struct TransitionWeight { TransitionLook look; std::uint8_t percent; };
    [[nodiscard]] std::vector<TransitionWeight> recommendedTransitionWeights();

    struct TransitionSpec {
        TransitionLook look{TransitionLook::Wipe};
        std::string plateColor{"#0B0E14"};   ///< the covering plate (or dip colour)
        std::string inColor{"#101720"};      ///< the incoming plate for PushThrough
        std::string leakColor{"#FFB35C"};    ///< the LightLeak wash colour
        chrononmotion::motion::presets::Direction travel{
                chrononmotion::motion::presets::Direction::Right}; ///< sweep direction
        int slices{8};                       ///< GlitchSlices: slice count (1..16)
        float leakPeakOpacity{0.55f};        ///< LightLeak: peak wash opacity in (0, 1]
        std::string name{"transition"};
        int inFrame{0};                      ///< first frame of the transition
        int duration{24};                    ///< frames the whole transition spans
        bool enableMotionBlur{false};        ///< opt-in temporal motion blur on the scene
    };

    /// What the pack authored: the plates in authoring order, the peak/cover
    /// frame (full opacity only for covering looks such as whiteout), and range.
    struct TransitionComposition {
        std::vector<LayerHandle*> plates{};
        int coverFrame{0};
        int inFrame{0};
        int endFrame{0};
    };

    /// Stable snake-case id of a look (the catalog/consumer-facing name).
    [[nodiscard]] const char* transitionId(TransitionLook look) noexcept;

    /// Every look in canonical order, for catalogs and contract tests.
    [[nodiscard]] std::vector<TransitionLook> transitionLooks();

    /// Build the transition into `scene`. Rapid looks enforce their documented
    /// duration window; when a rapid spec leaves `duration` at its historical
    /// value 24, callers should set it with `recommendedTransitionDuration`.
    /// The plates are shapes keyed over the transition window; when
    /// `spec.enableMotionBlur` is set, the
    /// scene's temporal motion blur is declared (180-degree shutter, 8 samples)
    /// so fast plate moves render with the engine's blur contract.
    ///
    /// Throws `std::invalid_argument` on a duration outside the selected rapid
    /// look's published bounds, a slice count outside [1, 16], or a leak peak
    /// opacity outside (0, 1].
    [[nodiscard]] TransitionComposition addTransition(TemplateScene& scene, const TransitionSpec& spec);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_TRANSITIONS_TRANSITION_PACK_HPP
