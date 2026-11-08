// ChrononTemplate — declarative GEL cinematic title.
//
// This pack exists so a template can request the certified Chronon3D GEL look
// without rebuilding the recipe by hand and without editing the renderer:
// plate, extruded royal-blue backing words, dielectric cyan GEL faces and the
// selective optics (drop shadow, chromatic dispersion, tight glow, thresholded
// bloom, downward light shafts) are all emitted through the existing
// ContentHost -> RenderPlan contract.

#ifndef CHRONONTEMPLATE_GEL_CINEMATIC_TITLE_PACK_HPP
#define CHRONONTEMPLATE_GEL_CINEMATIC_TITLE_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <string>
#include <vector>

namespace chronontemplate::gel {

    /// One word of the title. `x`/`y` are canvas-space centres; `scale` is the
    /// per-word face scale.
    struct GelCinematicWord {
        std::string text{};
        float x{0.f};
        float y{0.f};
        float scale{1.f};
    };

    /// The GEL recipe: one plate and N dielectric faces, with the same effect
    /// stack on every face. Backings are intentionally not emitted: the video
    /// path composited them over the faces and hid their lime crest. Defaults
    /// are the values pinned by the 2026-11-07 reference closure.
    struct GelCinematicTitleSpec {
        std::string name{"GelCinematicTitle"};
        std::string plate{};
        ImageFitMode plateFit{ImageFitMode::Cover};
        /// Zero means "use the scene canvas". The plate is always one
        /// full-frame screen-space image: bake any out-of-focus extension into
        /// the asset instead of stacking a strip over a blurred copy.
        chrononmotion::Vector2 plateSize{0.f, 0.f};
        std::string font{};
        float fontSize{125.f};
        std::string faceColor{"#00E8FF"};
        // Retained for source compatibility with the earlier backing recipe;
        // the backing is no longer emitted.
        std::string backingColor{"#1454FF"};
        float extrusionDepth{8.f};
        float backingScale{1.004f};
        chrononmotion::Vector2 backingOffset{1.f, 5.f};
        std::vector<GelCinematicWord> words{};
        int inFrame{0};
        int durationFrames{300};
        /// Slow optical push shared by every layer. 1.0 keeps the title static.
        float pushScale{1.035f};
        /// Dielectric backdrop transmission. False is the opaque diagnostic
        /// ablation kept for A/B renders.
        bool gelTransmission{true};
        /// Downward shafts generated from each word's own luminance. The pack
        /// moves the origin to that word's top centre in canvas space.
        bool enableLightRays{true};
        TextLightRaysStyle lightRays{
            .originX = 0.5f, .originY = 0.2f,
            .length = 300.f, .density = 1.35f, .decay = 0.88f,
            .color = "#35DFFF", .opacity = 0.34f};

        TextDropShadowStyle dropShadow{
            .color = "#0547E0", .opacity = 0.45f, .blur = 2.f, .offset = {1.f, 2.f}};
        TextChromaticAberrationStyle chromaticAberration{
            .redOffset = 0.f,
            .blueOffset = 0.f,
            .redShift = {-0.25f, -0.45f},
            .greenShift = {-0.75f, -1.05f},
            .blueShift = {0.85f, 0.95f}};
        TextGlowStyle glow{
            .color = "#0AD1FF", .radius = 4.5f, .intensity = 0.12f};
        TextBloomStyle bloom{
            .threshold = 0.68f, .radius = 6.5f, .intensity = 0.55f};
        TextLensFlareStyle lensFlare{
            .threshold = 0.55f,
            .intensity = 1.10f,
            // 0.18 of the short side is the optical radius. The anamorphic
            // wing collapses the glyph rows into a column profile, stretches
            // it horizontally and fades it on a narrow vertical Gaussian.
            .radius = 0.18f,
            .halo = 0.f,
            .ghost = 0.f,
            .streak = 1.f};
        /// The legacy highlight-only horizontal wing is retained as a
        /// diagnostic only. The reference has no horizontal cut through the
        /// backdrop; the current composite uses downward light shafts instead.
        bool enableLensFlare{false};
    };

    struct GelCinematicTitleLayers {
        MotionLayerId plate{0};
        /// Always empty; retained for source compatibility.
        std::vector<MotionLayerId> backings{};
        std::vector<MotionLayerId> faces{};
    };

    /// Author the recipe into `scene`. Layers are created plate -> all faces
    /// so the draw order is the certified one. The content is measured and
    /// owned by the supplied ContentHost; this function only states what to
    /// create, where it sits and how the optics behave.
    [[nodiscard]] GelCinematicTitleLayers addGelCinematicTitle(
            TemplateScene& scene, const GelCinematicTitleSpec& spec);

}// namespace chronontemplate::gel

#endif//CHRONONTEMPLATE_GEL_CINEMATIC_TITLE_PACK_HPP
