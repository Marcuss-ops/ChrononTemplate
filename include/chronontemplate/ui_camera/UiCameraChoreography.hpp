// ChrononTemplate — UI + smooth-camera choreography (ui_camera_choreography_v1).
//
// What the After Effects tutorial "This Camera Movement Makes UI Animations
// So Smooth" does in three phases — build the graphics, animate the layers,
// refine the camera move in the Graph Editor — lowered onto primitives
// Chronon already owns:
//
//   - graphics: ShapeContentPlan rects, StrokeStyle, native drop shadow,
//     the text engine, the SVG importer;
//   - layer motion: AnimationTrackPlan position/scale/opacity keys, per-segment
//     CubicBezier easing, StaggerPlan;
//   - camera: selected panel-move parameters passed to the ChrononMotion3D
//     panel choreography resolver, then lowered from its CameraRig tracks;
//   - motion blur: TemporalMotionBlurSettings -> MotionBlurPlan.
//
// The pack adds no renderer, sampler, easing model or parenting system. It is
// a composer: one Null-controller hierarchy (TemplateScene::group, i.e. the
// canonical MotionScene::addNull) carries the whole UI panel so the entrance
// is authored once, and the camera is the only other animated thing. A Null
// controller needs no new RenderPlan LayerType: the canonical Motion ->
// RenderPlan lowerer bakes its world motion into the children and emits the
// controller itself as a transparent 1x1 color layer, so the hierarchy rides
// the existing contract instead of widening it.
//
// Framing is derived from the measured ContentHost metrics (the real bounds
// of the card/title/icon), never from hand-placed coordinates, so a zoom
// cannot crop text, cards or icons. Every move ends in a settle beat — the
// last frames decelerate into the hold — which is what reads as "smooth".

#ifndef CHRONONTEMPLATE_UI_CAMERA_CHOREOGRAPHY_HPP
#define CHRONONTEMPLATE_UI_CAMERA_CHOREOGRAPHY_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include "chrononmotion/math/Vector2.hpp"
#include "chrononmotion/math/Vector3.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// The look of one UI panel. No timing here: this is what the panel is,
    /// the choreography spec below says when it moves.
    struct UiPanelSpec {
        std::string title{"CHRONON"};
        std::string font{"Inter-Bold.ttf"};
        float fontSize{96.f};
        std::string titleColor{"#FFFFFF"};
        chrononmotion::Vector2 cardSize{900.f, 500.f};
        std::string cardFill{"#141B2A"};
        float cornerRadius{28.f};
        std::string strokeColor{"#3A4A63"};
        float strokeWidth{2.f};
        bool shadow{true};
        /// Optional icon asset. Empty means a procedural placeholder lozenge,
        /// so the canary never needs a file on disk.
        std::string iconPath{};
        chrononmotion::Vector2 iconSize{120.f, 120.f};
        chrononmotion::Vector2 center{960.f, 540.f};
    };

    /// The 90-frame test grammar from the tutorial analysis, as data:
    /// the panel enters from below (0-15) while the camera is already
    /// pushing in (10-35), drifts laterally toward the text (28-65), then
    /// settles (65-90). All windows are [inFrame, inFrame + duration).
    struct UiCameraChoreographySpec {
        int totalFrames{90};
        int panelInFrame{0};
        int panelDuration{15};
        float panelEnterDistance{420.f};
        int zoomInFrame{10};
        int zoomDuration{25};
        float zoomDolly{180.f};
        int panInFrame{28};
        int panDuration{37};
        chrononmotion::Vector2 panOffset{-160.f, 0.f};
        float fov{50.f};
        bool motionBlur{true};
        float shutterAngle{180.f};
        std::uint32_t motionBlurSamples{8};
        /// The panel spans frameFill of the tighter frame axis; safeMargin
        /// pads the fitted distance so glyphs never touch the frame edge.
        float frameFill{0.78f};
        float safeMargin{1.12f};
    };

    /// The authored hierarchy. root is the Null controller: it owns no
    /// content and carries the entrance. card/title/icon are parented to it.
    struct UiPanelComposition {
        MotionLayerId root{0};
        MotionLayerId card{0};
        MotionLayerId shadow{0};
        MotionLayerId title{0};
        MotionLayerId icon{0};
        /// Real bounds: the max of the card size and the measured title and
        /// icon extents, as reported by the ContentHost. The framing law fits
        /// this, not the authored cardSize alone.
        chrononmotion::Vector2 panelSize{0.f, 0.f};
    };

    /// Build the static panel: one Null root plus card, title and icon
    /// parented under it. Writes no keys — motion belongs to
    /// applyUiCameraChoreography. Throws std::invalid_argument on an empty
    /// title or non-positive, non-finite geometry.
    [[nodiscard]] UiPanelComposition buildUiPanel(TemplateScene& scene, const UiPanelSpec& spec);

    /// Author the whole move: the panel entrance on the Null root, the
    /// staggered card/title/icon reveals, the overlapping camera push and
    /// lateral drift on the rig, the settle hold, and the opt-in temporal
    /// motion blur. Throws std::invalid_argument on overlapping-broken or
    /// non-positive windows, non-finite distances, or a framing that cannot
    /// fit the measured panel.
    void applyUiCameraChoreography(TemplateScene& scene,
                                   const UiCameraChoreographySpec& spec,
                                   const UiPanelComposition& panel);

    /// Compatibility wrapper around the CM3D panel framing law. Throws
    /// std::invalid_argument on bad inputs.
    [[nodiscard]] float uiFramingDistance(float subjectWidth, float fovDegrees,
                                          const chrononmotion::Vector2& viewport,
                                          float frameFill = 0.78f);

    struct UiChoreographyReport {
        bool ok{false};
        std::vector<std::string> problems{};
        /// Largest per-frame camera translation step (world units).
        float maxJump{0.f};
        /// Peak rig speed mid-travel vs in the settle hold (units/s).
        float midRate{0.f};
        float endRate{0.f};
    };

    /// Verify the authored choreography without rendering: camera continuity
    /// (no teleports), end settle (slower than mid-travel), animated-parent
    /// propagation (children follow the Null root), and safe-area framing of
    /// the measured panel across the whole window.
    [[nodiscard]] UiChoreographyReport validateUiChoreography(
        TemplateScene& scene, const UiCameraChoreographySpec& spec,
        const UiPanelComposition& panel);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_UI_CAMERA_CHOREOGRAPHY_HPP
