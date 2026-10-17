// ChrononTemplate — "Effects": procedural cinematic overlays.
//
// Twenty single overlay effects (light leaks, film grain, dust, vignette, ...)
// authored entirely with existing shape primitives: nested flat ellipses for
// soft falloff (the renderer's radial-gradient fill produces no pixels),
// animated noise, grids, strokes, ellipses and rectangles. No overlay video or texture asset is
// read, so every effect is deterministic from its seed and renders the same
// on a distributed or resumed render.

#ifndef CHRONONTEMPLATE_EFFECTS_PACK_HPP
#define CHRONONTEMPLATE_EFFECTS_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate::effects {

    enum class EffectKind : std::uint8_t {
        LightLeak,
        FilmGrain,
        FilmScratches,
        FilmBurn,
        ScanlineInterference,
        GateWeave,
        FloatingDust,
        AtmosphericHaze,
        DefocusedBokeh,
        LightRays,
        MovingLightShadow,
        LensFlare,
        CinematicVignette,
        ChromaticAberration,
        PaperGrain,
        FilmHalation,
        OpticalDiffusion,
        FilmEdgeMatte,
        DirectionalMotionSmear,
        ExposureFlicker,
    };

    /// Parameters shared by every effect. `intensity` scales how strong the
    /// look is (0 = invisible), `opacity` is the layer opacity on top of it.
    /// The effect is visible only on frames in [startFrame, endFrame).
    struct EffectSpec {
        float intensity{1.f};
        float opacity{1.f};
        std::uint32_t seed{1};
        int startFrame{0};
        int endFrame{120};
        std::string color{};  ///< empty = the effect's own default tint
    };

    /// Author one effect on the scene and return the layers it created.
    /// Throws std::invalid_argument on out-of-range values or bad colors.
    [[nodiscard]] std::vector<MotionLayerId> addEffect(TemplateScene& scene,
                                                       EffectKind kind,
                                                       const EffectSpec& spec);

    /// Stable snake_case name of an effect, used in layer names.
    [[nodiscard]] const char* effectName(EffectKind kind) noexcept;

    /// Number of effect kinds in the pack.
    [[nodiscard]] constexpr std::size_t effectCount() noexcept { return 20; }

    [[nodiscard]] const char* effectsId() noexcept;

} // namespace chronontemplate::effects

#endif // CHRONONTEMPLATE_EFFECTS_PACK_HPP
