// ChrononTemplate — the camera motion pack (camera_motion_pack_v1).
//
// Narrative camera presets plus ten Web3D recipes across six families (editorial
// titles, photo documentary, geo maps, dashboard UI, transitions, product shots),
// all expressed as *recipes*,
// not one renderer function per move. Every preset is one row of spec numbers —
// durations at 30 fps, distances as fractions of the reference framing,
// lateral/vertical travel as fractions of the frame, angles in degrees, focus
// as percent of the configured depth interval — lowered by one generic
// resolver onto the ChrononMotion3D CameraRig:
//
//   Scene Framing (reference distance) → Motion Resolver (spec × intensity)
//     → PoseTracks (single shot) | ShotTimeline (two-shot cut)
//     → CameraDescriptor → CameraProgram → Chronon Render
//
// Boundary: the pack owns no camera math and no renderer. The named
// `camera_motion_*` ids are editorial vocabulary and live here, not in the
// motion core. A preset never touches a subject layer: every key lands on
// the rig. Presets flagged needsDof / needs25D / needsMultiPlane /
// needsOccluder declare backend requirements instead of faking them.

#ifndef CHRONONTEMPLATE_CAMERA_ROLL_CAMERA_MOTION_PACK_HPP
#define CHRONONTEMPLATE_CAMERA_ROLL_CAMERA_MOTION_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include "chrononmotion/math/Vector2.hpp"
#include "chrononmotion/math/Vector3.hpp"
#include "chrononmotion/motion/CameraRig.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// Narrative camera families. Web3D contains ten object-aware recipes.
    enum class CameraMotionFamily : std::uint8_t {
        EditorialTitle,   ///< titles and quotes
        PhotoDocumentary, ///< portraits and archive stills
        MapGeo,           ///< regions and routes
        DashboardUI,      ///< panels, cards and product UI
        Transition,       ///< two-shot handoffs between scenes
        Web3D             ///< product and web-object camera moves
    };

    /// Presets in spec order. Values are stable ids: they reach the catalog
    /// and the contract test verbatim.
    enum class CameraMotionPreset : std::uint16_t {
#define CAMERA_MOTION_PRESET(key, id, family, ...) key,
#include "chronontemplate/camera_roll/CameraMotionPresets.def"
#undef CAMERA_MOTION_PRESET
    };

    /// Planner loudness: one preset, three strengths. Amplitudes (distance
    /// deltas, lateral/vertical travel, angles) scale by the factor; durations
    /// and focus depths never scale.
    enum class CameraMotionIntensity : std::uint8_t {
        Subtle, ///< 50% of the authored amplitude
        Normal, ///< 100% of the authored amplitude
        Strong  ///< 150% of the authored amplitude, clamped by framing
    };

    /// What the planner recognised in the scene. The selection table maps
    /// each kind to the spec's recommended presets.
    enum class CameraContentKind : std::uint8_t {
        TitleOnWhite,        ///< title on plain background
        ImpactWord,          ///< number / stressed word
        SinglePortrait,      ///< one face / figure
        PortraitBuildingText,///< portrait + building + text
        ArchivePhoto,        ///< document / archive still
        MapCountry,          ///< map, one country lit
        MapTwoCountries,     ///< map, two countries
        MapRoute,            ///< map with a route
        DashboardChart,      ///< dashboard / chart
        PremiumUI3D,         ///< premium 3D UI
        FastCut,             ///< fast change of image
        ObjectPass,          ///< transition through an object
        BlurPass,            ///< transition with defocus
        Web3DObject          ///< a real 3D asset such as table.glb
    };

    /// What a shot frames: the subject's optical centre and half-extents in
    /// world units. Scene Framing fits the reference distance to this; the
    /// preset only describes motion *relative* to it.
    struct CameraMotionSubject {
        chrononmotion::Vector3 center{0.f, 0.f, 0.f};
        float halfWidth{480.f};
        float halfHeight{270.f};
    };

    /// Authoring description of one shot.
    struct CameraMotionShot {
        CameraMotionSubject subject{};
        CameraMotionIntensity intensity{CameraMotionIntensity::Normal};
        float fov{50.f};
        /// Depth interval the focus percents resolve against (world units).
        float focusNear{800.f};
        float focusFar{1400.f};
        int inFrame{0};
        /// 0 keeps the spec duration; positive overrides it (stretches keys).
        int durationOverride{0};
    };

    /// One row of the roster: the whole recipe as spec numbers. Distances are
    /// fractions of the reference framing (1.00 = reference); lateral (X) and
    /// vertical (Y) travel are fractions of the frame width/height, signed as
    /// seen by the camera (X+ = body right, Y+ = body down); angles are
    /// degrees; focus is percent of [focusNear, focusFar]. A *_mid value
    /// < -900 means "no mid key" (straight travel).
    struct CameraMotionSpec {
        const char* id{};
        CameraMotionFamily family{CameraMotionFamily::EditorialTitle};
        int durationFrames{90};
        float distStart{1.f};
        float distMid{-1000.f};
        float distMidAt{0.5f};
        float distEnd{1.f};
        float xStart{0.f};
        float xMid{-1000.f};
        float xEnd{0.f};
        float yStart{0.f};
        float yMid{-1000.f};
        float yEnd{0.f};
        float posMidAt{0.5f};
        /// Body travel window as fractions of the duration (holds outside).
        float travelStart{0.f};
        float travelEnd{1.f};
        float yawStart{0.f};
        float yawEnd{0.f};
        float pitchStart{0.f};
        float pitchEnd{0.f};
        float rollStart{0.f};
        float rollPeak{-1000.f};
        float rollEnd{0.f};
        float focusStart{-1.f};
        float focusEnd{-1.f};
        const char* easing{"smooth"};
        bool needsDof{false};
        bool needs25D{false};
        bool needsMultiPlane{false};
        bool twoShot{false};
        bool needsOccluder{false};
        bool highEnergy{false};
        /// Two-shot: fraction of the duration where scene A cuts to B.
        float cutAt{0.5f};
        /// Two-shot: the IN leg launches loud (expoOut) instead of easing
        /// in-out — whips and pass-throughs, not settles and reveals.
        bool snapIn{false};
    };

    /// Every preset in canonical roster order. The roster also generates the
    /// enum ordinals and supplies stable id/family metadata.
    [[nodiscard]] std::vector<CameraMotionPreset> cameraMotionPresets();

    /// Stable snake-case id of a preset (the catalog/consumer-facing name).
    [[nodiscard]] const char* cameraMotionPresetId(CameraMotionPreset preset) noexcept;

    /// Every preset id in canonical (spec) order, for catalogs and tests.
    [[nodiscard]] std::vector<std::string> cameraMotionPresetIds();

    /// Family of a preset. Pure.
    [[nodiscard]] CameraMotionFamily cameraMotionFamily(CameraMotionPreset preset);

    /// Spec duration in frames at 30 fps (before any override). Pure.
    [[nodiscard]] int cameraMotionDuration(CameraMotionPreset preset);

    /// The spec row. Pure: a function of the preset only.
    [[nodiscard]] const CameraMotionSpec& cameraMotionSpecFor(CameraMotionPreset preset);

    /// Intensity amplitude factor: Subtle 0.5, Normal 1.0, Strong 1.5. Pure.
    [[nodiscard]] float cameraMotionIntensityFactor(CameraMotionIntensity intensity) noexcept;

    /// Scene Framing: the reference eye distance at which the subject spans
    /// `frameFill` of the tighter frame axis. All spec distance fractions
    /// resolve against this. Pure; throws on bad inputs.
    [[nodiscard]] float cameraMotionReferenceDistance(const CameraMotionSubject& subject,
                                                      float fovDegrees,
                                                      const chrononmotion::Vector2& viewport,
                                                      float frameFill = 0.78f);

    /// Spec easing name → rig easing. Pure: cinematic/smooth → easeInOut,
    /// gentle_out → easeOut, snappy_out/whip_out → expoOut, whip_in → easeIn.
    [[nodiscard]] chrononmotion::motion::Easing cameraMotionEasingFor(const std::string& name);

    /// Planner selection table: the spec's recommended presets for recognised
    /// content. Pure.
    [[nodiscard]] std::vector<CameraMotionPreset> cameraMotionSuggestions(CameraContentKind kind);

    /// Every content kind in canonical order. Pure.
    [[nodiscard]] std::vector<CameraContentKind> cameraContentKinds();

    /// Author one shot onto the scene's camera rig. Single-shot presets key
    /// PoseTracks (travel + settle hold); two-shot transitions key a
    /// ShotTimeline (out leg → cut → mirrored in leg → settle). Subject
    /// layers are never touched. Throws on bad shot/duration/subject, and on
    /// non-finite resolved keys.
    void applyCameraMotionShot(TemplateScene& scene, CameraMotionPreset preset,
                               const CameraMotionShot& shot);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_CAMERA_ROLL_CAMERA_MOTION_PACK_HPP
