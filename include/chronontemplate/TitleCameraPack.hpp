// ChrononTemplate — the title-camera documentary pack (camera_title_documentary_v1).
//
// Twenty editorial title moves as recipes over six camera primitives (dolly,
// pan, orbit, tilt, roll, FOV plus target lock and focus distance). The pack
// authors *only* the camera: the title layer keeps an empty transform, so the
// motion the audience sees is authored entirely by the lens — the documentary
// grammar the family exists for.
//
// Boundary: the pack owns no camera math. Every move is lowered onto the
// ChrononMotion3D CameraRig channels; the named `title_camera_*` ids are
// editorial vocabulary and deliberately live here, not in the motion core.

#ifndef CHRONONTEMPLATE_TITLE_CAMERA_PACK_HPP
#define CHRONONTEMPLATE_TITLE_CAMERA_PACK_HPP

#include "chronontemplate/TemplateScene.hpp"

#include "chrononmotion/math/Vector2.hpp"
#include "chrononmotion/math/Vector3.hpp"
#include "chrononmotion/motion/CameraRig.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// The one thing every title shot needs: where the title lives in the scene.
    /// Every preset takes this anchor as its target, so the same move frames
    /// "ROME", "2008", "$4.5 BILLION" or "THE STORY OF APPLE" without any of
    /// them carrying coordinates.
    struct TitleShotAnchor {
        /// World-space position of the title's optical centre (the layer's
        /// authored position, usually the canvas centre in 2.5D scenes).
        chrononmotion::Vector3 center{0.f, 0.f, 0.f};
        /// Half-extent of the title run in world units, used for framing math
        /// and safe-area checks (a conservative bound is fine).
        float halfWidth{300.f};
        float halfHeight{120.f};
    };

    /// How tightly the lens frames the anchor at rest.
    enum class TitleFraming : std::uint8_t {
        Hero,          ///< tight, the title dominates the frame
        Medium,        ///< default documentary framing
        Wide,          ///< title inside its context
        ExtremeClose   ///< detail framing for short, heavy titles
    };

    /// Editorial loudness of the move. One preset, three strengths.
    enum class TitleCameraIntensity : std::uint8_t {
        Subtle,
        Editorial,
        Cinematic
    };

    /// The twenty title-camera presets. The values are stable ids: they reach
    /// the contract test and the catalog verbatim, so they are append-only.
    enum class TitleCameraMove : std::uint8_t {
        SlowPush,            ///< title_camera_slow_push
        SlowPullOut,         ///< title_camera_slow_pull_out
        LeftDrift,           ///< title_camera_left_drift
        RightDrift,          ///< title_camera_right_drift
        VerticalRise,        ///< title_camera_vertical_rise
        VerticalDescend,     ///< title_camera_vertical_descend
        MicroOrbitLeft,      ///< title_camera_micro_orbit_left
        MicroOrbitRight,     ///< title_camera_micro_orbit_right
        ArcPush,             ///< title_camera_arc_push
        ArcPull,             ///< title_camera_arc_pull
        LowAnglePush,        ///< title_camera_low_angle_push
        HighAngleSettle,     ///< title_camera_high_angle_settle
        RollSettle,          ///< title_camera_roll_settle
        RollPass,            ///< title_camera_roll_pass
        DollyZoomSubtle,     ///< title_camera_dolly_zoom_subtle
        FocusPush,           ///< title_camera_focus_push
        ParallaxSide,        ///< title_camera_parallax_side
        ParallaxPush,        ///< title_camera_parallax_push
        WhipSettle,          ///< title_camera_whip_settle
        CornerReveal         ///< title_camera_corner_reveal
    };

    /// Authoring description of one title shot: what is framed, how tight, how
    /// loud, how long. The camera is the only animated thing.
    struct TitleCameraShot {
        TitleShotAnchor anchor{};
        TitleFraming framing{TitleFraming::Medium};
        TitleCameraIntensity intensity{TitleCameraIntensity::Editorial};
        int inFrame{0};
        int duration{135};
    };

    /// Stable snake-case id of a preset (the catalog/consumer-facing name).
    [[nodiscard]] const char* titleCameraMoveId(TitleCameraMove move) noexcept;

    /// Every preset id in canonical order, for catalogs and contract tests.
    [[nodiscard]] std::vector<std::string> titleCameraMoveIds();

    /// Author `shot` onto the scene's camera rig. The title layer is never
    /// touched: dolly/pan/orbit/tilt/roll/FOV/focus keys land on the rig only,
    /// with an end settle (the last beat decelerates) unless the move states
    /// otherwise. Throws `std::invalid_argument` on a non-positive duration or
    /// a non-finite anchor.
    void applyTitleCameraShot(TemplateScene& scene, TitleCameraMove move,
                              const TitleCameraShot& shot);

    // ── Pure resolution ────────────────────────────────────────────────────
    //
    // The numbers a preset would author, exposed separately from keying so a
    // test can pin the vocabulary without owning any scene.

    struct TitleCameraPlan {
        /// Optical distance of the frontal rest framing, world units.
        float distance{1000.f};
        /// FOV of the rest framing, degrees.
        float fov{55.f};
        /// Dolly travel along the view axis. Positive moves the *end* pose
        /// toward the anchor (a push); negative moves it away (a pull out).
        float dolly{0.f};
        /// Total lateral body crossing of a drift, world units (+ = left to
        /// right). The camera crosses past the anchor, aimed at it throughout.
        float panX{0.f};
        /// Lateral start offset the move returns from, world units (arcs,
        /// whip, corner reveal).
        float restLateral{0.f};
        /// Mid-travel lateral bow of an arc path, world units.
        float arcBow{0.f};
        /// Height offset at the start of the move, world units (negative =
        /// below the anchor).
        float heightOffset{0.f};
        /// Height offset at the end of the move; 0 is the rest level. Angle
        /// pushes retain their offset (heightEnd == heightOffset); rises and
        /// settles shed it (heightEnd == 0).
        float heightEnd{0.f};
        /// Orbit yaw offsets about the anchor, radians: the micro-orbit start
        /// and end swing, or the whip's off-axis acquisition.
        float yawStart{0.f};
        float yawEnd{0.f};
        /// Roll about the view axis, radians: start, optional mid peak, end.
        float rollStart{0.f};
        float rollPeak{0.f};
        float rollEnd{0.f};
        /// FOV at the end of the move; 0 leaves the lens untouched.
        float fovEnd{0.f};
        /// Focus-distance travel; positive pulls the focal plane toward the
        /// anchor (0 = untouched).
        float focusPull{0.f};
        /// Entrance pupil authored for the move in millimetres (0 = untouched).
        float aperture{0.f};
        /// Fraction of the travel the whip spends acquiring (whip_settle only).
        float whipAcquisition{0.f};
    };

    /// The numbers `applyTitleCameraShot` would key, in world units, for the
    /// pure function pair `titleCameraDistance` + `titleCameraPlanFor`. Pure:
    /// a function of the shot description only.
    [[nodiscard]] float titleCameraDistance(TitleFraming framing, float fovDegrees);

    /// The plan of a preset: every recipe is this plan lowered onto the rig.
    [[nodiscard]] TitleCameraPlan titleCameraPlanFor(TitleCameraMove move,
                                                     const TitleCameraShot& shot);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_TITLE_CAMERA_PACK_HPP
