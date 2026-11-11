// ChrononTemplate — the title-camera documentary pack (camera_title_documentary_v1).
//
// Twenty editorial title moves as recipes over six camera primitives (dolly,
// pan, orbit, tilt, roll, FOV plus target lock and focus distance). The pack
// authors *only* the camera: the title layer keeps an empty transform, so the
// motion the audience sees is authored entirely by the lens — the documentary
// grammar the family exists for.
//
// Boundary: the pack owns no camera math. Every move is lowered onto the
// ChrononMotion3D CameraRig channels. The stable `title_camera_*` IDs and move
// evaluation are owned by CM3D; Template supplies title-specific shot data.

#ifndef CHRONONTEMPLATE_TITLE_CAMERA_PACK_HPP
#define CHRONONTEMPLATE_TITLE_CAMERA_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include "chrononmotion/math/Vector2.hpp"
#include "chrononmotion/math/Vector3.hpp"
#include "chrononmotion/motion/CameraRig.hpp"
#include "chrononmotion/motion/TitleCameraRecipe.hpp"

#include <cstdint>
#include <stdexcept>
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
        /// and safe-area checks (a conservative bound is fine). Must be
        /// positive whenever `TitleCameraShot::minVisible > 0`: a zero-size
        /// subject would make the visibility guard vacuous.
        float halfWidth{300.f};
        float halfHeight{120.f};
    };

    /// How tightly the lens frames the anchor at rest.
    using TitleFraming = chrononmotion::motion::camera::TitleFraming;

    /// Editorial loudness of the move. One preset, three strengths.
    using TitleCameraIntensity = chrononmotion::motion::camera::TitleIntensity;

    /// The title-camera presets. The values are stable ids: they reach
    /// the contract test and the catalog verbatim, so they are append-only.
    using TitleCameraMove = chrononmotion::motion::camera::TitleMove;

    /// Authoring description of one title shot: what is framed, how tight, how
    /// loud, how long. The camera is the only animated thing.
    struct TitleCameraShot {
        TitleShotAnchor anchor{};
        TitleFraming framing{TitleFraming::Medium};
        TitleCameraIntensity intensity{TitleCameraIntensity::Editorial};
        int inFrame{0};
        int duration{135};
        /// Minimum fraction of the title bounds that must stay inside the
        /// frame at every sampled frame. Set to 0 to opt out explicitly.
        float minVisible{0.95f};
    };

    /// Result of the per-frame subject-in-frame check. `failure` is a stable,
    /// human-readable diagnostic naming the move, the frame and the ratio.
    struct TitleCameraFramingReport {
        bool passed{true};
        int worstFrame{0};
        float worstVisible{1.f};
        std::string failure{};
    };

    /// Thrown by applyTitleCameraShot when the authored camera leaves the
    /// subject outside the frame. A named type lets callers distinguish a
    /// framing-authoring error from an I/O or plan error.
    class TitleCameraFramingLost : public std::runtime_error {
    public:
        using std::runtime_error::runtime_error;
    };

    /// Author `shot` on a private copy of the scene rig and sample that probe
    /// across the whole window. The scene is never mutated, so this can be
    /// called before `applyTitleCameraShot` to answer "would this shot frame
    /// the title?". This is the same `CameraValidator` the motion layer uses;
    /// the pack does not reimplement projection.
    [[nodiscard]] TitleCameraFramingReport titleCameraFramingReport(
        TemplateScene& scene, TitleCameraMove move, const TitleCameraShot& shot);

    /// Stable snake-case id of a preset (the catalog/consumer-facing name).
    [[nodiscard]] const char* titleCameraMoveId(TitleCameraMove move) noexcept;

    /// Every preset id in canonical order, for catalogs and contract tests.
    [[nodiscard]] std::vector<std::string> titleCameraMoveIds();

    /// Author `shot` onto the scene's camera rig. The title layer is never
    /// touched: dolly/pan/orbit/tilt/roll/FOV/focus keys land on the rig only,
    /// with an end settle (the last beat decelerates) unless the move states
    /// otherwise. The shot is validated on a private rig probe first, so a
    /// framing loss is rejected before the scene rig is mutated. Throws
    /// `std::invalid_argument` on an invalid duration, anchor or extents, and
    /// `TitleCameraFramingLost` when the authored camera leaves the title below
    /// `minVisible` in any sampled frame.
    void applyTitleCameraShot(TemplateScene& scene, TitleCameraMove move,
                              const TitleCameraShot& shot);

    // ── Pure resolution ────────────────────────────────────────────────────
    //
    // The numbers a preset would author, exposed separately from keying so a
    // test can pin the vocabulary without owning any scene.

    using TitleCameraPlan = chrononmotion::motion::camera::TitleCameraPlan;

    /// The numbers `applyTitleCameraShot` would key, in world units, for the
    /// pure function pair `titleCameraDistance` + `titleCameraPlanFor`. Pure:
    /// a function of the shot description only.
    [[nodiscard]] float titleCameraDistance(TitleFraming framing, float fovDegrees);

    /// The plan of a preset: every recipe is this plan lowered onto the rig.
    [[nodiscard]] TitleCameraPlan titleCameraPlanFor(TitleCameraMove move,
                                                     const TitleCameraShot& shot);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_TITLE_CAMERA_PACK_HPP
