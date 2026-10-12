// ChrononTemplate — the camera motion pack (camera_motion_pack_v1).
//
// Fifty narrative camera presets in five families (editorial titles, photo
// documentary, geo maps, dashboard UI, two-shot transitions) as *recipes*,
// not fifty renderer functions. Every preset is one row of spec numbers —
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

    /// The five narrative families, in spec order.
    enum class CameraMotionFamily : std::uint8_t {
        EditorialTitle,   ///< 01–10: quotes, numbers, documentary titles
        PhotoDocumentary, ///< 11–20: portraits, archive, buildings, cutouts
        MapGeo,           ///< 21–30: regions, routes, country focus
        DashboardUI,      ///< 31–40: panels, cards, charts, product UI
        Transition        ///< 41–50: two-shot handoffs between scenes
    };

    /// The fifty presets, in spec order. Values are stable ids: they reach
    /// the catalog and the contract test verbatim, so they are append-only.
    enum class CameraMotionPreset : std::uint16_t {
        SoftPushIn,            ///< camera_motion_soft_push_in (01)
        SoftPullBack,          ///< camera_motion_soft_pull_back (02)
        EditorialDriftLeft,    ///< camera_motion_editorial_drift_left (03)
        EditorialDriftRight,   ///< camera_motion_editorial_drift_right (04)
        TitleRise,             ///< camera_motion_title_rise (05)
        TitleDescend,          ///< camera_motion_title_descend (06)
        QuietDiagonalDrift,    ///< camera_motion_quiet_diagonal_drift (07)
        TypeDepthFocus,        ///< camera_motion_type_depth_focus (08, DOF)
        TypeMicroOrbit,        ///< camera_motion_type_micro_orbit (09, 2.5D)
        ImpactPunchSettle,     ///< camera_motion_impact_punch_settle (10)
        KenBurnsIn,            ///< camera_motion_ken_burns_in (11)
        KenBurnsOut,           ///< camera_motion_ken_burns_out (12)
        PortraitUpwardTrack,   ///< camera_motion_portrait_upward_track (13)
        PortraitDownwardTrack, ///< camera_motion_portrait_downward_track (14)
        PhotoRevealLeft,       ///< camera_motion_photo_reveal_left (15)
        PhotoRevealRight,      ///< camera_motion_photo_reveal_right (16)
        LowAnglePhotoReveal,   ///< camera_motion_low_angle_photo_reveal (17, 2.5D)
        PortraitHeroArc,       ///< camera_motion_portrait_hero_arc (18, 2.5D)
        DocumentaryParallax,   ///< camera_motion_documentary_parallax (19, planes)
        PhotoRackFocus,        ///< camera_motion_photo_rack_focus (20, DOF)
        MapRegionPush,         ///< camera_motion_map_region_push (21)
        MapRegionPull,         ///< camera_motion_map_region_pull (22)
        MapEastwardTrack,      ///< camera_motion_map_eastward_track (23)
        MapWestwardTrack,      ///< camera_motion_map_westward_track (24)
        MapNorthwardTrack,     ///< camera_motion_map_northward_track (25)
        MapSouthwardTrack,     ///< camera_motion_map_southward_track (26)
        RouteCameraSweep,      ///< camera_motion_route_camera_sweep (27)
        CountryFocusLock,      ///< camera_motion_country_focus_lock (28)
        CountryComparisonPan,  ///< camera_motion_country_comparison_pan (29)
        GeopoliticalTiltReveal,///< camera_motion_geopolitical_tilt_reveal (30, 2.5D)
        UiPanelPush,           ///< camera_motion_ui_panel_push (31)
        DashboardPan,          ///< camera_motion_dashboard_pan (32)
        CardStackParallax,     ///< camera_motion_card_stack_parallax (33, 2.5D)
        CornerDetailInspect,   ///< camera_motion_corner_detail_inspect (34)
        DataDetailZoom,        ///< camera_motion_data_detail_zoom (35)
        UiOverviewPull,        ///< camera_motion_ui_overview_pull (36)
        SideBySideCompare,     ///< camera_motion_side_by_side_compare (37)
        PanelAngledPeek,       ///< camera_motion_panel_angled_peek (38, 2.5D)
        ChartTraverse,         ///< camera_motion_chart_traverse (39)
        ProductUiMicroFloat,   ///< camera_motion_product_ui_micro_float (40, loop)
        WhipPanLeft,           ///< camera_motion_whip_pan_left (41, two-shot)
        WhipPanRight,          ///< camera_motion_whip_pan_right (42, two-shot)
        WhipPanUp,             ///< camera_motion_whip_pan_up (43, two-shot)
        WhipPanDown,           ///< camera_motion_whip_pan_down (44, two-shot)
        FastDollyThrough,      ///< camera_motion_fast_dolly_through (45, two-shot)
        ReverseDollyReveal,    ///< camera_motion_reverse_dolly_reveal (46, two-shot)
        RollMatchCut,          ///< camera_motion_roll_match_cut (47, two-shot)
        OrbitHandoff,          ///< camera_motion_orbit_handoff (48, two-shot, 2.5D)
        ForegroundOcclusionPass,///< camera_motion_foreground_occlusion_pass (49, two-shot)
        FocusHandoff           ///< camera_motion_focus_handoff (50, two-shot, DOF)
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
        TitleOnWhite,        ///< title on plain background → 01, 02, 05, 06
        ImpactWord,          ///< number / stressed word → 10, 35
        SinglePortrait,      ///< one face / figure → 11, 13, 18
        PortraitBuildingText,///< portrait + building + text → 18, 19
        ArchivePhoto,        ///< document / archive still → 11, 12, 15, 16
        MapCountry,          ///< map, one country lit → 21, 28
        MapTwoCountries,     ///< map, two countries → 23, 24, 29
        MapRoute,            ///< map with a route → 27
        DashboardChart,      ///< dashboard / chart → 31, 32, 35, 39
        PremiumUI3D,         ///< premium 3D UI → 33, 38, 40
        FastCut,             ///< fast change of image → 41–44
        ObjectPass,          ///< transition through an object → 45, 49
        BlurPass             ///< transition with defocus → 50
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

    /// One row of the fifty: the whole recipe as spec numbers. Distances are
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
