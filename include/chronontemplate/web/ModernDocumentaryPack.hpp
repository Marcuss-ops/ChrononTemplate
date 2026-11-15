// ChrononTemplate — Modern Documentary pack.
//
// Five native RenderPlan V3 looks distilled from the supplied modern
// documentary references:
//
//   VoxHighlight   paper article, left-anchored multiply highlighter, subject
//                  cutout, rack focus and floating dust.
//   SplitGlitch    torn split composition, glowing energy divider, UI card in
//                  Z-space with chromatic/mesh/slice glitch treatment.
//   MacroUiRain    macro comment UI, typewriter sentence, layered crowd
//                  silhouettes and a banknote particle rain with HUD.
//   KineticType    four 3D typographic beats, left-to-right bars and a
//                  whip-pan camera with a 180-degree temporal shutter.
//   VhsCarousel    CRT frame, spring-overshoot logo carousel, hot title and
//                  analog scanline/chroma wear.
//
// Every look is authored as ordinary `chronon.render-plan.v3` data. Chronon3D
// owns rasterization, effects, camera sampling and encoding; this module owns
// the design vocabulary and timing. No browser, DOM or live JS is involved.
//
// The pack deliberately uses the renderer's existing primitives:
//   * multiply blend + shape scale/position tracks (highlighter),
//   * camera_samples with thin-lens DoF (rack focus),
//   * text_animators + a character selector (typewriter),
//   * temporal_motion_blur + per-frame camera_samples (whip pan),
//   * chromatic_aberration, mesh_warp, scanlines, retro_tv, roughen_edges,
//     lens_distortion, glow/bloom and directional_blur (analog/UI wear),
//   * particle_emitter sprite, rotation and angular_velocity fields.
//
// The banknote rain is a 2.5D environment emitter: it uses the existing
// per-particle sprite rotation and fake depth/DoF fields. It is not a claim of
// a full six-degree-of-freedom rigid-body particle solver.
#ifndef CHRONONTEMPLATE_WEB_MODERN_DOCUMENTARY_PACK_HPP
#define CHRONONTEMPLATE_WEB_MODERN_DOCUMENTARY_PACK_HPP

#include <array>
#include <nlohmann/json.hpp>
#include <string>

namespace chronontemplate::web {

enum class ModernDocumentaryRecipe : unsigned char {
    VoxHighlight,
    SplitGlitch,
    MacroUiRain,
    KineticType,
    VhsCarousel
};

[[nodiscard]] const char* modernDocumentaryName(ModernDocumentaryRecipe recipe);
[[nodiscard]] std::array<ModernDocumentaryRecipe, 5> allModernDocumentaryRecipes();

struct ModernDocumentarySpec {
    ModernDocumentaryRecipe recipe{ModernDocumentaryRecipe::VoxHighlight};
    int durationFrames{150};  // 5 s at 30 fps
    int fps{30};
    std::string outputName{};

    void validate() const;
    [[nodiscard]] std::string planName() const;
    [[nodiscard]] std::string outputStem() const;
};

/// Complete `chronon.render-plan.v3` document for one look.
[[nodiscard]] nlohmann::json buildModernDocumentaryPlan(const ModernDocumentarySpec& spec);

}  // namespace chronontemplate::web

#endif  // CHRONONTEMPLATE_WEB_MODERN_DOCUMENTARY_PACK_HPP
