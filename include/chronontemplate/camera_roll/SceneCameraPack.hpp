// ChrononTemplate — the scene-camera pack (scene_camera_sequencer_v1).
//
// The shot-boundary grammar of a documentary edit, pre-configured: an object
// (a phrase, an image, a text, a card) holds its framing — the *stacco* — then
// the camera itself carries the audience to the next object, which lands on
// its own framing and holds. The subjects never animate: every key lands on
// the shared CameraRig, so the same sequence reframes "frase 1 → immagine →
// testo" without any of them carrying coordinates, exactly like the
// title-camera pack does for a single title.
//
// One call authors the whole chain: `applySceneCameraSequence` walks the beats,
// derives each rest framing from the subject's own size (the framing law), and
// keys the selected transition between consecutive holds. The legs never
// overlap and every leg starts and ends exactly on the two rests it joins, so
// a sequence of any length is continuous by construction — no teleport at a
// boundary, no drift into a hold.
//
// Boundary: the pack owns no camera math. Every move is lowered onto the
// ChrononMotion3D CameraRig channels; the named `scene_camera_*` ids are
// editorial vocabulary and deliberately live here, not in the motion core.

#ifndef CHRONONTEMPLATE_SCENE_CAMERA_PACK_HPP
#define CHRONONTEMPLATE_SCENE_CAMERA_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include "chrononmotion/math/Vector2.hpp"
#include "chrononmotion/math/Vector3.hpp"
#include "chrononmotion/motion/CameraRig.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// What a stacco frames. The kind selects the framing tightness and the
    /// lens: a phrase sits flatter and closer, an image wider, a title text
    /// on a longer lens. It is editorial metadata, never content.
    enum class SubjectKind : std::uint8_t {
        Phrase,
        Image,
        Text,
        Card
    };

    /// The subject of one stacco: an anchored object in the scene with the
    /// world-space half-extents the framing law fits. The centre is the
    /// object's optical centre (usually the canvas centre in 2.5D scenes,
    /// offset in Z for depth).
    struct SceneSubject {
        SubjectKind kind{SubjectKind::Phrase};
        chrononmotion::Vector3 center{0.f, 0.f, 0.f};
        float halfWidth{480.f};
        float halfHeight{270.f};
    };

    /// The travel from one stacco to the next. Stable ids: they reach the
    /// catalog and the contract test verbatim, so they are append-only.
    enum class SceneCameraTransition : std::uint8_t {
        PushThrough,      ///< scene_camera_push_through — dive through the seam between the two holds
        LateralSwipe,     ///< scene_camera_lateral_swipe — the body crosses sideways past the seam, aimed ahead
        ArcCarry,         ///< scene_camera_arc_carry — a curved perpendicular bow carries the frame across
        OrbitHandoff,     ///< scene_camera_orbit_handoff — the camera orbits the seam pivot from hold A to hold B
        RiseAndLand,      ///< scene_camera_rise_and_land — lift over the seam and settle down onto the next hold
        FocusRack,        ///< scene_camera_focus_rack — a near-still frame where the lens hands focus over
        PullBackReveal,   ///< scene_camera_pull_back_reveal — start tight on A with a roll, pull back, land wide on B
        WhipReframe,      ///< scene_camera_whip_reframe — one loud acquisition swing, then a long settle onto B
    };

    /// One node of the sequence: what the audience watches, and for how long.
    /// The framing hold is the stacco; the travel to the next beat is appended
    /// after the hold, so `inFrame` of a beat is derived, not authored.
    struct SceneBeat {
        SceneSubject subject{};
        /// Frames the subject holds its framing before the camera leaves.
        int hold{90};
    };

    /// Authoring description of the whole chain.
    struct SceneCameraSequence {
        std::vector<SceneBeat> beats{};
        /// The transition lowered between every consecutive pair of holds.
        SceneCameraTransition transition{SceneCameraTransition::PushThrough};
        /// The loudness ladder: 0.55 subtle, 1 editorial, 1.9 cinematic.
        float intensity{1.f};
        /// Frames of camera travel between two framing holds.
        int travelFrames{24};
        /// Frame the first hold starts on (the rest are derived).
        int inFrame{0};
    };

    /// Stable snake-case id of a transition (the catalog/consumer-facing name).
    [[nodiscard]] const char* sceneCameraTransitionId(SceneCameraTransition transition) noexcept;

    /// Every transition id in canonical order, for catalogs and contract tests.
    [[nodiscard]] std::vector<std::string> sceneCameraTransitionIds();

    // ── Pure resolution ─────────────────────────────────────────────────────
    //
    // The numbers a sequence would author, exposed separately from keying so a
    // test can pin the vocabulary without owning any scene.

    /// The optical rest distance for one subject: the subject spans `frameFill`
    /// of the tighter frame axis at the delivery aspect. Pure.
    [[nodiscard]] float sceneFramingDistance(const SceneSubject& subject, float fovDegrees,
                                             const chrononmotion::Vector2& viewport,
                                             float frameFill = 0.62f);

    /// The lens a subject kind is framed on (degrees).
    [[nodiscard]] float sceneSubjectFov(SubjectKind kind);

    /// Author the whole chain onto the scene's camera rig. The subjects' layers
    /// are never touched: position/target/fov/focus/roll keys land on the rig
    /// only, each leg starts and ends on the two rests it joins, and the rig's
    /// static pose matches the first rest (so the opening hold samples it).
    /// Throws `std::invalid_argument` on an empty sequence, a non-positive
    /// hold/travel/intensity, a non-finite subject, or a rest framing that
    /// leaves its subject outside the safe area.
    void applySceneCameraSequence(TemplateScene& scene, const SceneCameraSequence& sequence);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_SCENE_CAMERA_PACK_HPP
