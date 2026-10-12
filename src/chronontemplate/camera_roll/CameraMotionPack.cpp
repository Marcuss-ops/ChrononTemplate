// ChrononTemplate — the camera motion pack, implementation.
//
// Fifty recipes, one resolver. Every preset is a row of spec numbers
// (specFor); resolveShot lowers a row × intensity onto rig poses; the
// single-shot and two-shot appliers key those poses onto the CameraRig.
// Subject layers are never touched: the camera is the only animated thing.

#include "chronontemplate/camera_roll/CameraMotionPack.hpp"

#include "chrononmotion/math/MathUtils.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace chronontemplate {

    using chrononmotion::Vector2;
    using chrononmotion::Vector3;
    using chrononmotion::motion::CameraPose;
    using chrononmotion::motion::CameraRig;
    using chrononmotion::motion::Easing;
    using chrononmotion::math::degToRad;

    namespace {

        constexpr float kPi = 3.14159265358979323846f;
        constexpr float kNoMid = -1000.f;

        [[nodiscard]] float at(int frame, float fps) { return static_cast<float>(frame) / fps; }

        [[nodiscard]] bool finiteSubject(const CameraMotionSubject& subject) {
            return std::isfinite(subject.center.x) && std::isfinite(subject.center.y) &&
                   std::isfinite(subject.center.z) && std::isfinite(subject.halfWidth) &&
                   std::isfinite(subject.halfHeight);
        }

        // ------------------------------------------------- the 50 rows ----
        // Durations are frames at 30 fps; distances are fractions of the
        // reference framing; X/Y are fractions of the frame width/height
        // (X+ = body right, Y+ = body down); angles are degrees; focus is
        // percent of the configured depth interval. Values transcribed from
        // the camera motion pack spec, families 1–5 in order.

        [[nodiscard]] CameraMotionSpec specFor(CameraMotionPreset preset) {
            CameraMotionSpec spec;
            switch (preset) {
                // ── Family 1: editorial titles ──
                case CameraMotionPreset::SoftPushIn:
                    spec.id = "camera_motion_soft_push_in";
                    spec.family = CameraMotionFamily::EditorialTitle;
                    spec.durationFrames = 75;
                    spec.distStart = 1.09f; spec.distEnd = 1.00f;
                    spec.easing = "cinematic";
                    break;
                case CameraMotionPreset::SoftPullBack:
                    spec.id = "camera_motion_soft_pull_back";
                    spec.family = CameraMotionFamily::EditorialTitle;
                    spec.durationFrames = 75;
                    spec.distStart = 0.94f; spec.distEnd = 1.06f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::EditorialDriftLeft:
                    spec.id = "camera_motion_editorial_drift_left";
                    spec.family = CameraMotionFamily::EditorialTitle;
                    spec.durationFrames = 84;
                    spec.xStart = 0.075f; spec.xEnd = -0.075f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::EditorialDriftRight:
                    spec.id = "camera_motion_editorial_drift_right";
                    spec.family = CameraMotionFamily::EditorialTitle;
                    spec.durationFrames = 84;
                    spec.xStart = -0.075f; spec.xEnd = 0.075f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::TitleRise:
                    spec.id = "camera_motion_title_rise";
                    spec.family = CameraMotionFamily::EditorialTitle;
                    spec.durationFrames = 50;
                    spec.distStart = 1.035f; spec.distEnd = 1.00f;
                    spec.yStart = 0.085f; spec.yEnd = 0.f;
                    spec.easing = "gentle_out";
                    break;
                case CameraMotionPreset::TitleDescend:
                    spec.id = "camera_motion_title_descend";
                    spec.family = CameraMotionFamily::EditorialTitle;
                    spec.durationFrames = 50;
                    spec.distStart = 1.035f; spec.distEnd = 1.00f;
                    spec.yStart = -0.08f; spec.yEnd = 0.f;
                    spec.easing = "gentle_out";
                    break;
                case CameraMotionPreset::QuietDiagonalDrift:
                    spec.id = "camera_motion_quiet_diagonal_drift";
                    spec.family = CameraMotionFamily::EditorialTitle;
                    spec.durationFrames = 90;
                    spec.xStart = -0.045f; spec.xEnd = 0.045f;
                    spec.yStart = 0.045f; spec.yEnd = -0.045f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::TypeDepthFocus:
                    spec.id = "camera_motion_type_depth_focus";
                    spec.family = CameraMotionFamily::EditorialTitle;
                    spec.durationFrames = 70;
                    spec.distStart = 1.04f; spec.distEnd = 1.00f;
                    spec.focusStart = 10.f; spec.focusEnd = 90.f;
                    spec.needsDof = true;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::TypeMicroOrbit:
                    spec.id = "camera_motion_type_micro_orbit";
                    spec.family = CameraMotionFamily::EditorialTitle;
                    spec.durationFrames = 100;
                    spec.distStart = 1.05f; spec.distMid = 1.00f; spec.distMidAt = 0.5f;
                    spec.distEnd = 1.03f;
                    spec.xStart = -0.025f; spec.xMid = 0.f; spec.xEnd = 0.025f;
                    spec.yawStart = -2.f; spec.yawEnd = 2.f;
                    spec.needs25D = true;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::ImpactPunchSettle:
                    spec.id = "camera_motion_impact_punch_settle";
                    spec.family = CameraMotionFamily::EditorialTitle;
                    spec.durationFrames = 22;
                    spec.distStart = 1.28f; spec.distMid = 0.975f; spec.distMidAt = 8.f / 22.f;
                    spec.distEnd = 1.00f;
                    spec.highEnergy = true;
                    spec.easing = "snappy_out";
                    break;
                // ── Family 2: photo documentary ──
                case CameraMotionPreset::KenBurnsIn:
                    spec.id = "camera_motion_ken_burns_in";
                    spec.family = CameraMotionFamily::PhotoDocumentary;
                    spec.durationFrames = 120;
                    spec.distStart = 1.07f; spec.distEnd = 0.91f;
                    spec.xStart = -0.045f; spec.xEnd = 0.055f;
                    spec.yStart = 0.035f; spec.yEnd = -0.03f;
                    spec.easing = "cinematic";
                    break;
                case CameraMotionPreset::KenBurnsOut:
                    spec.id = "camera_motion_ken_burns_out";
                    spec.family = CameraMotionFamily::PhotoDocumentary;
                    spec.durationFrames = 120;
                    spec.distStart = 0.90f; spec.distEnd = 1.07f;
                    spec.xStart = 0.035f; spec.xEnd = -0.04f;
                    spec.yStart = -0.04f; spec.yEnd = 0.03f;
                    spec.easing = "cinematic";
                    break;
                case CameraMotionPreset::PortraitUpwardTrack:
                    spec.id = "camera_motion_portrait_upward_track";
                    spec.family = CameraMotionFamily::PhotoDocumentary;
                    spec.durationFrames = 85;
                    spec.distStart = 0.93f; spec.distEnd = 0.94f;
                    spec.yStart = 0.20f; spec.yEnd = -0.08f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::PortraitDownwardTrack:
                    spec.id = "camera_motion_portrait_downward_track";
                    spec.family = CameraMotionFamily::PhotoDocumentary;
                    spec.durationFrames = 85;
                    spec.distStart = 0.95f; spec.distEnd = 0.95f;
                    spec.yStart = -0.14f; spec.yEnd = 0.14f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::PhotoRevealLeft:
                    spec.id = "camera_motion_photo_reveal_left";
                    spec.family = CameraMotionFamily::PhotoDocumentary;
                    spec.durationFrames = 70;
                    spec.distStart = 0.90f; spec.distEnd = 0.94f;
                    spec.xStart = 0.18f; spec.xEnd = -0.10f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::PhotoRevealRight:
                    spec.id = "camera_motion_photo_reveal_right";
                    spec.family = CameraMotionFamily::PhotoDocumentary;
                    spec.durationFrames = 70;
                    spec.distStart = 0.90f; spec.distEnd = 0.94f;
                    spec.xStart = -0.18f; spec.xEnd = 0.10f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::LowAnglePhotoReveal:
                    spec.id = "camera_motion_low_angle_photo_reveal";
                    spec.family = CameraMotionFamily::PhotoDocumentary;
                    spec.durationFrames = 72;
                    spec.distStart = 1.10f; spec.distEnd = 0.98f;
                    spec.yStart = 0.13f; spec.yEnd = 0.f;
                    spec.pitchStart = 5.f; spec.pitchEnd = 0.f;
                    spec.needs25D = true;
                    spec.easing = "gentle_out";
                    break;
                case CameraMotionPreset::PortraitHeroArc:
                    spec.id = "camera_motion_portrait_hero_arc";
                    spec.family = CameraMotionFamily::PhotoDocumentary;
                    spec.durationFrames = 100;
                    spec.distStart = 1.02f; spec.distMid = 0.97f; spec.distMidAt = 0.5f;
                    spec.distEnd = 1.04f;
                    spec.xStart = -0.11f; spec.xMid = 0.f; spec.xEnd = 0.10f;
                    spec.yawStart = -5.f; spec.yawEnd = 5.f;
                    spec.needs25D = true;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::DocumentaryParallax:
                    spec.id = "camera_motion_documentary_parallax";
                    spec.family = CameraMotionFamily::PhotoDocumentary;
                    spec.durationFrames = 105;
                    spec.distStart = 1.02f; spec.distEnd = 0.98f;
                    spec.xStart = -0.10f; spec.xEnd = 0.10f;
                    spec.needsMultiPlane = true;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::PhotoRackFocus:
                    spec.id = "camera_motion_photo_rack_focus";
                    spec.family = CameraMotionFamily::PhotoDocumentary;
                    spec.durationFrames = 78;
                    spec.focusStart = 95.f; spec.focusEnd = 10.f;
                    spec.needsDof = true;
                    spec.easing = "smooth";
                    break;
                // ── Family 3: geo maps ──
                case CameraMotionPreset::MapRegionPush:
                    spec.id = "camera_motion_map_region_push";
                    spec.family = CameraMotionFamily::MapGeo;
                    spec.durationFrames = 90;
                    spec.distStart = 1.16f; spec.distEnd = 0.82f;
                    spec.easing = "cinematic";
                    break;
                case CameraMotionPreset::MapRegionPull:
                    spec.id = "camera_motion_map_region_pull";
                    spec.family = CameraMotionFamily::MapGeo;
                    spec.durationFrames = 100;
                    spec.distStart = 0.78f; spec.distEnd = 1.20f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::MapEastwardTrack:
                    spec.id = "camera_motion_map_eastward_track";
                    spec.family = CameraMotionFamily::MapGeo;
                    spec.durationFrames = 105;
                    spec.distStart = 0.92f; spec.distEnd = 0.92f;
                    spec.xStart = -0.25f; spec.xEnd = 0.22f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::MapWestwardTrack:
                    spec.id = "camera_motion_map_westward_track";
                    spec.family = CameraMotionFamily::MapGeo;
                    spec.durationFrames = 105;
                    spec.distStart = 0.92f; spec.distEnd = 0.92f;
                    spec.xStart = 0.24f; spec.xEnd = -0.23f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::MapNorthwardTrack:
                    spec.id = "camera_motion_map_northward_track";
                    spec.family = CameraMotionFamily::MapGeo;
                    spec.durationFrames = 95;
                    spec.distStart = 0.95f; spec.distEnd = 0.95f;
                    spec.yStart = 0.24f; spec.yEnd = -0.21f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::MapSouthwardTrack:
                    spec.id = "camera_motion_map_southward_track";
                    spec.family = CameraMotionFamily::MapGeo;
                    spec.durationFrames = 95;
                    spec.distStart = 0.95f; spec.distEnd = 0.95f;
                    spec.yStart = -0.22f; spec.yEnd = 0.24f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::RouteCameraSweep:
                    spec.id = "camera_motion_route_camera_sweep";
                    spec.family = CameraMotionFamily::MapGeo;
                    spec.durationFrames = 120;
                    spec.distStart = 1.10f; spec.distMid = 0.88f; spec.distMidAt = 0.5f;
                    spec.distEnd = 0.93f;
                    spec.xStart = -0.20f; spec.xMid = 0.f; spec.xEnd = 0.20f;
                    spec.yStart = 0.10f; spec.yMid = 0.f; spec.yEnd = -0.10f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::CountryFocusLock:
                    spec.id = "camera_motion_country_focus_lock";
                    spec.family = CameraMotionFamily::MapGeo;
                    spec.durationFrames = 82;
                    spec.distStart = 1.16f; spec.distMid = 0.83f; spec.distMidAt = 0.65f;
                    spec.distEnd = 0.84f;
                    spec.xStart = -0.13f; spec.xEnd = 0.f;
                    spec.yStart = 0.04f; spec.yEnd = 0.f;
                    spec.easing = "snappy_out";
                    break;
                case CameraMotionPreset::CountryComparisonPan:
                    spec.id = "camera_motion_country_comparison_pan";
                    spec.family = CameraMotionFamily::MapGeo;
                    spec.durationFrames = 110;
                    spec.distStart = 0.96f; spec.distEnd = 0.96f;
                    spec.xStart = -0.23f; spec.xEnd = 0.23f;
                    spec.travelStart = 0.20f; spec.travelEnd = 0.85f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::GeopoliticalTiltReveal:
                    spec.id = "camera_motion_geopolitical_tilt_reveal";
                    spec.family = CameraMotionFamily::MapGeo;
                    spec.durationFrames = 98;
                    spec.distStart = 1.15f; spec.distEnd = 0.95f;
                    spec.yStart = 0.08f; spec.yEnd = 0.f;
                    spec.pitchStart = 7.f; spec.pitchEnd = 0.f;
                    spec.needs25D = true;
                    spec.easing = "gentle_out";
                    break;
                // ── Family 4: dashboard UI ──
                case CameraMotionPreset::UiPanelPush:
                    spec.id = "camera_motion_ui_panel_push";
                    spec.family = CameraMotionFamily::DashboardUI;
                    spec.durationFrames = 63;
                    spec.distStart = 1.16f; spec.distEnd = 0.91f;
                    spec.easing = "gentle_out";
                    break;
                case CameraMotionPreset::DashboardPan:
                    spec.id = "camera_motion_dashboard_pan";
                    spec.family = CameraMotionFamily::DashboardUI;
                    spec.durationFrames = 100;
                    spec.distStart = 0.96f; spec.distEnd = 0.96f;
                    spec.xStart = -0.18f; spec.xEnd = 0.18f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::CardStackParallax:
                    spec.id = "camera_motion_card_stack_parallax";
                    spec.family = CameraMotionFamily::DashboardUI;
                    spec.durationFrames = 86;
                    spec.distStart = 1.08f; spec.distEnd = 0.92f;
                    spec.xStart = -0.08f; spec.xEnd = 0.10f;
                    spec.yawStart = -2.5f; spec.yawEnd = 2.5f;
                    spec.needs25D = true;
                    spec.needsMultiPlane = true;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::CornerDetailInspect:
                    spec.id = "camera_motion_corner_detail_inspect";
                    spec.family = CameraMotionFamily::DashboardUI;
                    spec.durationFrames = 77;
                    spec.distStart = 1.18f; spec.distEnd = 0.83f;
                    spec.xStart = -0.02f; spec.xEnd = 0.15f;
                    spec.yStart = -0.02f; spec.yEnd = -0.12f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::DataDetailZoom:
                    spec.id = "camera_motion_data_detail_zoom";
                    spec.family = CameraMotionFamily::DashboardUI;
                    spec.durationFrames = 70;
                    spec.distStart = 1.15f; spec.distMid = 0.85f; spec.distMidAt = 0.72f;
                    spec.distEnd = 0.87f;
                    spec.easing = "snappy_out";
                    break;
                case CameraMotionPreset::UiOverviewPull:
                    spec.id = "camera_motion_ui_overview_pull";
                    spec.family = CameraMotionFamily::DashboardUI;
                    spec.durationFrames = 90;
                    spec.distStart = 0.80f; spec.distEnd = 1.20f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::SideBySideCompare:
                    spec.id = "camera_motion_side_by_side_compare";
                    spec.family = CameraMotionFamily::DashboardUI;
                    spec.durationFrames = 110;
                    spec.distStart = 0.95f; spec.distMid = 0.98f; spec.distMidAt = 0.45f;
                    spec.distEnd = 0.95f;
                    spec.xStart = -0.25f; spec.xMid = 0.f; spec.xEnd = 0.25f;
                    spec.posMidAt = 0.45f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::PanelAngledPeek:
                    spec.id = "camera_motion_panel_angled_peek";
                    spec.family = CameraMotionFamily::DashboardUI;
                    spec.durationFrames = 76;
                    spec.distStart = 1.08f; spec.distEnd = 0.98f;
                    spec.xStart = -0.06f; spec.xEnd = 0.f;
                    spec.yawStart = -6.f; spec.yawEnd = 0.f;
                    spec.needs25D = true;
                    spec.easing = "gentle_out";
                    break;
                case CameraMotionPreset::ChartTraverse:
                    spec.id = "camera_motion_chart_traverse";
                    spec.family = CameraMotionFamily::DashboardUI;
                    spec.durationFrames = 105;
                    spec.distStart = 0.88f; spec.distEnd = 0.88f;
                    spec.xStart = -0.30f; spec.xMid = -0.08f; spec.xEnd = 0.30f;
                    spec.posMidAt = 0.40f;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::ProductUiMicroFloat:
                    spec.id = "camera_motion_product_ui_micro_float";
                    spec.family = CameraMotionFamily::DashboardUI;
                    spec.durationFrames = 150;
                    spec.distStart = 1.02f; spec.distMid = 0.99f; spec.distMidAt = 0.5f;
                    spec.distEnd = 1.02f;
                    spec.xStart = -0.015f; spec.xMid = 0.014f; spec.xEnd = -0.015f;
                    spec.yStart = 0.015f; spec.yMid = -0.014f; spec.yEnd = 0.015f;
                    spec.needs25D = true;
                    spec.easing = "smooth";
                    break;
                // ── Family 5: two-shot transitions ──
                // Rows state the OUT leg (start → end); the resolver mirrors
                // the out end across the rest pose for the IN leg start and
                // settles both legs onto the rest framing.
                case CameraMotionPreset::WhipPanLeft:
                    spec.id = "camera_motion_whip_pan_left";
                    spec.family = CameraMotionFamily::Transition;
                    spec.durationFrames = 14;
                    spec.xStart = 0.f; spec.xEnd = -0.38f;
                    spec.twoShot = true; spec.highEnergy = true;
                    spec.snapIn = true;
                    spec.easing = "whip_in";
                    break;
                case CameraMotionPreset::WhipPanRight:
                    spec.id = "camera_motion_whip_pan_right";
                    spec.family = CameraMotionFamily::Transition;
                    spec.durationFrames = 14;
                    spec.xStart = 0.f; spec.xEnd = 0.38f;
                    spec.twoShot = true; spec.highEnergy = true;
                    spec.snapIn = true;
                    spec.easing = "whip_in";
                    break;
                case CameraMotionPreset::WhipPanUp:
                    spec.id = "camera_motion_whip_pan_up";
                    spec.family = CameraMotionFamily::Transition;
                    spec.durationFrames = 16;
                    spec.yStart = 0.f; spec.yEnd = -0.32f;
                    spec.twoShot = true; spec.highEnergy = true;
                    spec.snapIn = true;
                    spec.easing = "whip_in";
                    break;
                case CameraMotionPreset::WhipPanDown:
                    spec.id = "camera_motion_whip_pan_down";
                    spec.family = CameraMotionFamily::Transition;
                    spec.durationFrames = 16;
                    spec.yStart = 0.f; spec.yEnd = 0.32f;
                    spec.twoShot = true; spec.highEnergy = true;
                    spec.snapIn = true;
                    spec.easing = "whip_in";
                    break;
                case CameraMotionPreset::FastDollyThrough:
                    spec.id = "camera_motion_fast_dolly_through";
                    spec.family = CameraMotionFamily::Transition;
                    spec.durationFrames = 22;
                    spec.distStart = 1.00f; spec.distEnd = 0.48f;
                    spec.twoShot = true; spec.highEnergy = true;
                    spec.needsMultiPlane = true;
                    spec.snapIn = true;
                    spec.easing = "whip_in";
                    break;
                case CameraMotionPreset::ReverseDollyReveal:
                    spec.id = "camera_motion_reverse_dolly_reveal";
                    spec.family = CameraMotionFamily::Transition;
                    spec.durationFrames = 22;
                    spec.distStart = 1.00f; spec.distEnd = 1.46f;
                    spec.twoShot = true;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::RollMatchCut:
                    spec.id = "camera_motion_roll_match_cut";
                    spec.family = CameraMotionFamily::Transition;
                    spec.durationFrames = 19;
                    spec.rollStart = 0.f; spec.rollPeak = kNoMid; spec.rollEnd = 15.f;
                    spec.twoShot = true;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::OrbitHandoff:
                    spec.id = "camera_motion_orbit_handoff";
                    spec.family = CameraMotionFamily::Transition;
                    spec.durationFrames = 24;
                    spec.distStart = 1.00f; spec.distEnd = 0.95f;
                    spec.xStart = 0.f; spec.xEnd = 0.13f;
                    spec.yawStart = 0.f; spec.yawEnd = 13.f;
                    spec.twoShot = true;
                    spec.needs25D = true;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::ForegroundOcclusionPass:
                    spec.id = "camera_motion_foreground_occlusion_pass";
                    spec.family = CameraMotionFamily::Transition;
                    spec.durationFrames = 22;
                    spec.distStart = 1.00f; spec.distEnd = 0.70f;
                    spec.xStart = 0.f; spec.xEnd = 0.18f;
                    spec.twoShot = true;
                    spec.needsMultiPlane = true;
                    spec.needsOccluder = true;
                    spec.snapIn = true;
                    spec.easing = "smooth";
                    break;
                case CameraMotionPreset::FocusHandoff:
                    spec.id = "camera_motion_focus_handoff";
                    spec.family = CameraMotionFamily::Transition;
                    spec.durationFrames = 28;
                    spec.focusStart = 15.f; spec.focusEnd = 95.f;
                    spec.twoShot = true;
                    spec.needsDof = true;
                    spec.easing = "smooth";
                    break;
            }
            return spec;
        }

        // The resolved offsets of one leg endpoint: distance fraction already
        // intensity-scaled around 1.0, lateral/vertical fractions scaled, yaw /
        // pitch / roll in degrees scaled, focus percent unscaled.
        struct LegPose {
            float dist{1.f};
            float x{0.f};
            float y{0.f};
            float yaw{0.f};
            float pitch{0.f};
            float roll{0.f};
            float focus{-1.f};
        };

        [[nodiscard]] LegPose resolveLeg(float dist, float x, float y, float yaw, float pitch,
                                         float roll, float focus, float k) {
            LegPose leg;
            leg.dist = 1.f + (dist - 1.f) * k;
            leg.x = x * k;
            leg.y = y * k;
            leg.yaw = yaw * k;
            leg.pitch = pitch * k;
            leg.roll = roll * k;
            leg.focus = focus;
            return leg;
        }

        // Lower one leg endpoint onto a rig pose: rest framing plus the
        // lateral pan, orbit swing and dolly. Y+ fractions sit below the
        // anchor (title-pack sign convention).
        [[nodiscard]] CameraPose poseFor(const CameraPose& rest, const CameraMotionSubject& subject,
                                         float ref, float frameW, float frameH, const LegPose& leg) {
            CameraPose pose = rest;
            CameraRig::pan(pose, Vector2(leg.x * frameW, -leg.y * frameH));
            if (leg.yaw != 0.f || leg.pitch != 0.f) {
                CameraRig::orbitAround(pose, subject.center, degToRad(leg.yaw), degToRad(leg.pitch));
            }
            CameraRig::dolly(pose, ref * (1.f - leg.dist));
            return pose;
        }

        [[nodiscard]] float focusFor(float percent, float near, float far) {
            return near + (far - near) * (percent / 100.f);
        }

        [[nodiscard]] bool hasMid(float v) { return v > kNoMid * 0.5f; }

    }// namespace

    const char* cameraMotionPresetId(CameraMotionPreset preset) noexcept {
        return specFor(preset).id;
    }

    std::vector<std::string> cameraMotionPresetIds() {
        std::vector<std::string> ids;
        ids.reserve(50);
        for (const CameraMotionPreset preset : {
                     CameraMotionPreset::SoftPushIn, CameraMotionPreset::SoftPullBack,
                     CameraMotionPreset::EditorialDriftLeft, CameraMotionPreset::EditorialDriftRight,
                     CameraMotionPreset::TitleRise, CameraMotionPreset::TitleDescend,
                     CameraMotionPreset::QuietDiagonalDrift, CameraMotionPreset::TypeDepthFocus,
                     CameraMotionPreset::TypeMicroOrbit, CameraMotionPreset::ImpactPunchSettle,
                     CameraMotionPreset::KenBurnsIn, CameraMotionPreset::KenBurnsOut,
                     CameraMotionPreset::PortraitUpwardTrack, CameraMotionPreset::PortraitDownwardTrack,
                     CameraMotionPreset::PhotoRevealLeft, CameraMotionPreset::PhotoRevealRight,
                     CameraMotionPreset::LowAnglePhotoReveal, CameraMotionPreset::PortraitHeroArc,
                     CameraMotionPreset::DocumentaryParallax, CameraMotionPreset::PhotoRackFocus,
                     CameraMotionPreset::MapRegionPush, CameraMotionPreset::MapRegionPull,
                     CameraMotionPreset::MapEastwardTrack, CameraMotionPreset::MapWestwardTrack,
                     CameraMotionPreset::MapNorthwardTrack, CameraMotionPreset::MapSouthwardTrack,
                     CameraMotionPreset::RouteCameraSweep, CameraMotionPreset::CountryFocusLock,
                     CameraMotionPreset::CountryComparisonPan, CameraMotionPreset::GeopoliticalTiltReveal,
                     CameraMotionPreset::UiPanelPush, CameraMotionPreset::DashboardPan,
                     CameraMotionPreset::CardStackParallax, CameraMotionPreset::CornerDetailInspect,
                     CameraMotionPreset::DataDetailZoom, CameraMotionPreset::UiOverviewPull,
                     CameraMotionPreset::SideBySideCompare, CameraMotionPreset::PanelAngledPeek,
                     CameraMotionPreset::ChartTraverse, CameraMotionPreset::ProductUiMicroFloat,
                     CameraMotionPreset::WhipPanLeft, CameraMotionPreset::WhipPanRight,
                     CameraMotionPreset::WhipPanUp, CameraMotionPreset::WhipPanDown,
                     CameraMotionPreset::FastDollyThrough, CameraMotionPreset::ReverseDollyReveal,
                     CameraMotionPreset::RollMatchCut, CameraMotionPreset::OrbitHandoff,
                     CameraMotionPreset::ForegroundOcclusionPass, CameraMotionPreset::FocusHandoff}) {
            ids.emplace_back(cameraMotionPresetId(preset));
        }
        return ids;
    }

    CameraMotionFamily cameraMotionFamily(CameraMotionPreset preset) {
        return specFor(preset).family;
    }

    int cameraMotionDuration(CameraMotionPreset preset) {
        return specFor(preset).durationFrames;
    }

    const CameraMotionSpec& cameraMotionSpecFor(CameraMotionPreset preset) {
        static const CameraMotionSpec kEmpty{};
        // The table is the authority: resolve once per preset into statics.
        // (A switch-built static keeps the row next to its preset.)
        static bool initialised = false;
        static CameraMotionSpec table[50];
        if (!initialised) {
            int index = 0;
            for (const CameraMotionPreset value : {
                         CameraMotionPreset::SoftPushIn, CameraMotionPreset::SoftPullBack,
                         CameraMotionPreset::EditorialDriftLeft, CameraMotionPreset::EditorialDriftRight,
                         CameraMotionPreset::TitleRise, CameraMotionPreset::TitleDescend,
                         CameraMotionPreset::QuietDiagonalDrift, CameraMotionPreset::TypeDepthFocus,
                         CameraMotionPreset::TypeMicroOrbit, CameraMotionPreset::ImpactPunchSettle,
                         CameraMotionPreset::KenBurnsIn, CameraMotionPreset::KenBurnsOut,
                         CameraMotionPreset::PortraitUpwardTrack, CameraMotionPreset::PortraitDownwardTrack,
                         CameraMotionPreset::PhotoRevealLeft, CameraMotionPreset::PhotoRevealRight,
                         CameraMotionPreset::LowAnglePhotoReveal, CameraMotionPreset::PortraitHeroArc,
                         CameraMotionPreset::DocumentaryParallax, CameraMotionPreset::PhotoRackFocus,
                         CameraMotionPreset::MapRegionPush, CameraMotionPreset::MapRegionPull,
                         CameraMotionPreset::MapEastwardTrack, CameraMotionPreset::MapWestwardTrack,
                         CameraMotionPreset::MapNorthwardTrack, CameraMotionPreset::MapSouthwardTrack,
                         CameraMotionPreset::RouteCameraSweep, CameraMotionPreset::CountryFocusLock,
                         CameraMotionPreset::CountryComparisonPan, CameraMotionPreset::GeopoliticalTiltReveal,
                         CameraMotionPreset::UiPanelPush, CameraMotionPreset::DashboardPan,
                         CameraMotionPreset::CardStackParallax, CameraMotionPreset::CornerDetailInspect,
                         CameraMotionPreset::DataDetailZoom, CameraMotionPreset::UiOverviewPull,
                         CameraMotionPreset::SideBySideCompare, CameraMotionPreset::PanelAngledPeek,
                         CameraMotionPreset::ChartTraverse, CameraMotionPreset::ProductUiMicroFloat,
                         CameraMotionPreset::WhipPanLeft, CameraMotionPreset::WhipPanRight,
                         CameraMotionPreset::WhipPanUp, CameraMotionPreset::WhipPanDown,
                         CameraMotionPreset::FastDollyThrough, CameraMotionPreset::ReverseDollyReveal,
                         CameraMotionPreset::RollMatchCut, CameraMotionPreset::OrbitHandoff,
                         CameraMotionPreset::ForegroundOcclusionPass, CameraMotionPreset::FocusHandoff}) {
                table[index++] = specFor(value);
            }
            initialised = true;
        }
        const int ordinal = static_cast<int>(preset);
        if (ordinal < 0 || ordinal >= 50) return kEmpty;
        return table[ordinal];
    }

    float cameraMotionIntensityFactor(CameraMotionIntensity intensity) noexcept {
        switch (intensity) {
            case CameraMotionIntensity::Subtle: return 0.5f;
            case CameraMotionIntensity::Normal: return 1.0f;
            case CameraMotionIntensity::Strong: return 1.5f;
        }
        return 1.0f;
    }

    float cameraMotionReferenceDistance(const CameraMotionSubject& subject, float fovDegrees,
                                        const Vector2& viewport, float frameFill) {
        if (!finiteSubject(subject) || subject.halfWidth <= 0.f || subject.halfHeight <= 0.f) {
            throw std::invalid_argument("cameraMotionReferenceDistance: subject must be finite with positive extents");
        }
        if (!(fovDegrees > 0.f) || !(viewport.x > 0.f) || !(viewport.y > 0.f)) {
            throw std::invalid_argument("cameraMotionReferenceDistance: fov and viewport must be positive");
        }
        if (!(frameFill > 0.f) || frameFill > 1.f) {
            throw std::invalid_argument("cameraMotionReferenceDistance: frameFill must be in (0, 1]");
        }
        const float halfFovRad = fovDegrees * 0.5f * kPi / 180.f;
        const float tanHalf = std::tan(std::max(halfFovRad, 1e-4f));
        const float fitWidth = subject.halfWidth * 2.f;
        const float fitHeight = subject.halfHeight * 2.f * (viewport.x / viewport.y);
        const float fit = std::max(fitWidth, fitHeight);
        return fit / (2.f * tanHalf * (viewport.x / viewport.y) * frameFill);
    }

    Easing cameraMotionEasingFor(const std::string& name) {
        if (name == "cinematic" || name == "smooth") return Easing::easeInOut();
        if (name == "gentle_out") return Easing::easeOut();
        if (name == "snappy_out" || name == "whip_out") return Easing::expoOut();
        if (name == "whip_in") return Easing::easeIn();
        throw std::invalid_argument("cameraMotionEasingFor: unknown easing " + name);
    }

    std::vector<CameraMotionPreset> cameraMotionSuggestions(CameraContentKind kind) {
        using P = CameraMotionPreset;
        switch (kind) {
            case CameraContentKind::TitleOnWhite:
                return {P::SoftPushIn, P::SoftPullBack, P::TitleRise, P::TitleDescend};
            case CameraContentKind::ImpactWord:
                return {P::ImpactPunchSettle, P::DataDetailZoom};
            case CameraContentKind::SinglePortrait:
                return {P::KenBurnsIn, P::PortraitUpwardTrack, P::PortraitHeroArc};
            case CameraContentKind::PortraitBuildingText:
                return {P::PortraitHeroArc, P::DocumentaryParallax};
            case CameraContentKind::ArchivePhoto:
                return {P::KenBurnsIn, P::KenBurnsOut, P::PhotoRevealLeft, P::PhotoRevealRight};
            case CameraContentKind::MapCountry:
                return {P::MapRegionPush, P::CountryFocusLock};
            case CameraContentKind::MapTwoCountries:
                return {P::MapEastwardTrack, P::MapWestwardTrack, P::CountryComparisonPan};
            case CameraContentKind::MapRoute:
                return {P::RouteCameraSweep};
            case CameraContentKind::DashboardChart:
                return {P::UiPanelPush, P::DashboardPan, P::DataDetailZoom, P::ChartTraverse};
            case CameraContentKind::PremiumUI3D:
                return {P::CardStackParallax, P::PanelAngledPeek, P::ProductUiMicroFloat};
            case CameraContentKind::FastCut:
                return {P::WhipPanLeft, P::WhipPanRight, P::WhipPanUp, P::WhipPanDown};
            case CameraContentKind::ObjectPass:
                return {P::FastDollyThrough, P::ForegroundOcclusionPass};
            case CameraContentKind::BlurPass:
                return {P::FocusHandoff};
        }
        return {};
    }

    std::vector<CameraContentKind> cameraContentKinds() {
        return {CameraContentKind::TitleOnWhite, CameraContentKind::ImpactWord,
                CameraContentKind::SinglePortrait, CameraContentKind::PortraitBuildingText,
                CameraContentKind::ArchivePhoto, CameraContentKind::MapCountry,
                CameraContentKind::MapTwoCountries, CameraContentKind::MapRoute,
                CameraContentKind::DashboardChart, CameraContentKind::PremiumUI3D,
                CameraContentKind::FastCut, CameraContentKind::ObjectPass,
                CameraContentKind::BlurPass};
    }

    namespace {

        // Key one leg endpoint (position + target lock, roll, focus) at `t`.
        void keyLeg(CameraRig& rig, const CameraPose& pose, float roll, bool hasRoll,
                    float focus, bool hasFocus, float t, const Easing& easing) {
            rig.positionTrack().add(t, pose.position, easing);
            rig.targetTrack().add(t, pose.target, Easing::easeInOut());
            if (hasRoll) rig.rollTrack().add(t, roll, easing);
            if (hasFocus) rig.focusDistanceTrack().add(t, focus, easing);
        }

        void applySingleShot(TemplateScene& scene, const CameraMotionSpec& spec,
                             const CameraMotionShot& shot, int duration) {
            CameraRig& rig = scene.camera().rig();
            const float fps = scene.fps();
            const Vector2 viewport = scene.canvas();
            const float k = cameraMotionIntensityFactor(shot.intensity);
            const float ref = cameraMotionReferenceDistance(shot.subject, shot.fov, viewport);

            CameraPose rest;
            rest.position = Vector3(shot.subject.center.x, shot.subject.center.y,
                                    shot.subject.center.z + ref);
            rest.hasTarget = true;
            rest.target = shot.subject.center;
            rest.fov = shot.fov;

            const LegPose start = resolveLeg(spec.distStart, spec.xStart, spec.yStart,
                                             spec.yawStart, spec.pitchStart, spec.rollStart,
                                             spec.focusStart, k);
            const LegPose end = resolveLeg(spec.distEnd, spec.xEnd, spec.yEnd,
                                           spec.yawEnd, spec.pitchEnd, spec.rollEnd,
                                           spec.focusEnd, k);
            const bool hasDistMid = hasMid(spec.distMid);
            const bool hasPosMid = hasMid(spec.xMid) || hasMid(spec.yMid);
            const LegPose mid = resolveLeg(hasDistMid ? spec.distMid : (spec.distStart + spec.distEnd) * 0.5f,
                                           hasMid(spec.xMid) ? spec.xMid : (spec.xStart + spec.xEnd) * 0.5f,
                                           hasMid(spec.yMid) ? spec.yMid : (spec.yStart + spec.yEnd) * 0.5f,
                                           (spec.yawStart + spec.yawEnd) * 0.5f,
                                           (spec.pitchStart + spec.pitchEnd) * 0.5f,
                                           (spec.rollStart + spec.rollEnd) * 0.5f,
                                           (spec.focusStart + spec.focusEnd) * 0.5f, k);
            const bool useMid = hasDistMid || hasPosMid;
            const bool hasRoll = spec.rollStart != 0.f || hasMid(spec.rollPeak) || spec.rollEnd != 0.f;
            const bool hasFocus = spec.focusStart >= 0.f && spec.focusEnd >= 0.f;

            const int in = shot.inFrame;
            const int t0 = in;
            const int tTravel0 = in + static_cast<int>(std::round(duration * spec.travelStart));
            const int tTravel1 = in + static_cast<int>(std::round(duration * spec.travelEnd));
            const int tEnd = in + duration;
            const Easing travel = cameraMotionEasingFor(spec.easing);

            const CameraPose startPose = poseFor(rest, shot.subject, ref, viewport.x, viewport.y, start);
            const CameraPose midPose = poseFor(rest, shot.subject, ref, viewport.x, viewport.y, mid);
            const CameraPose endPose = poseFor(rest, shot.subject, ref, viewport.x, viewport.y, end);

            const float rollStart = degToRad(start.roll);
            const float rollMid = degToRad(mid.roll);
            const float rollEnd = degToRad(end.roll);
            const float focusStart = hasFocus ? focusFor(start.focus, shot.focusNear, shot.focusFar) : 0.f;
            const float focusMid = hasFocus ? focusFor(mid.focus, shot.focusNear, shot.focusFar) : 0.f;
            const float focusEnd = hasFocus ? focusFor(end.focus, shot.focusNear, shot.focusFar) : 0.f;
            if (hasFocus && !(shot.focusFar > shot.focusNear)) {
                throw std::invalid_argument("applyCameraMotionShot: focusFar must exceed focusNear");
            }

            const Easing firstHalf = useMid ? ((std::string(spec.easing) == "snappy_out")
                    ? Easing::expoOut() : Easing::easeIn()) : travel;
            const Easing secondHalf = useMid ? Easing::easeOut() : travel;
            keyLeg(rig, startPose, rollStart, hasRoll, focusStart, hasFocus, at(t0, fps), firstHalf);
            if (tTravel0 != t0) {
                keyLeg(rig, startPose, rollStart, hasRoll, focusStart, hasFocus, at(tTravel0, fps), firstHalf);
            }
            if (useMid) {
                const int tMid = in + static_cast<int>(std::round(
                        duration * (hasDistMid ? spec.distMidAt : spec.posMidAt)));
                keyLeg(rig, midPose, rollMid, hasRoll, focusMid, hasFocus, at(tMid, fps), secondHalf);
                if (hasRoll && hasMid(spec.rollPeak)) {
                    rig.rollTrack().add(at(tMid, fps), degToRad(spec.rollPeak * k), travel);
                }
            } else if (hasRoll && hasMid(spec.rollPeak)) {
                const int tMid = (tTravel0 + tTravel1) / 2;
                rig.rollTrack().add(at(tMid, fps), degToRad(spec.rollPeak * k), travel);
            }
            keyLeg(rig, endPose, rollEnd, hasRoll, focusEnd, hasFocus, at(tTravel1, fps), secondHalf);
            // Settle hold: the endpoint, decelerating into the hold.
            keyLeg(rig, endPose, rollEnd, hasRoll, focusEnd, hasFocus, at(tEnd, fps), Easing::linear());

            rig.setTarget(rest.target);
            rig.setPosition(endPose.position);
            rig.setFov(shot.fov);

            for (const float v : {ref, endPose.position.x, endPose.position.y, endPose.position.z}) {
                if (!std::isfinite(v)) {
                    throw std::invalid_argument("applyCameraMotionShot: non-finite resolved key");
                }
            }
        }

        void applyTwoShot(TemplateScene& scene, const CameraMotionSpec& spec,
                          const CameraMotionShot& shot, int duration) {
            CameraRig& rig = scene.camera().rig();
            const float fps = scene.fps();
            const float dt = 1.f / fps;
            const Vector2 viewport = scene.canvas();
            const float k = cameraMotionIntensityFactor(shot.intensity);
            const float ref = cameraMotionReferenceDistance(shot.subject, shot.fov, viewport);

            CameraPose rest;
            rest.position = Vector3(shot.subject.center.x, shot.subject.center.y,
                                    shot.subject.center.z + ref);
            rest.hasTarget = true;
            rest.target = shot.subject.center;
            rest.fov = shot.fov;

            // OUT leg: rest → out end. IN leg: mirrored out end → rest.
            const LegPose outEnd = resolveLeg(spec.distEnd, spec.xEnd, spec.yEnd,
                                              spec.yawEnd, spec.pitchEnd, spec.rollEnd,
                                              spec.focusEnd, k);
            LegPose inStart = outEnd;
            inStart.x = -outEnd.x;
            inStart.y = -outEnd.y;
            inStart.yaw = -outEnd.yaw;
            inStart.pitch = -outEnd.pitch;
            inStart.roll = -outEnd.roll;
            const LegPose inEnd{1.f, 0.f, 0.f, 0.f, 0.f, 0.f,
                                spec.focusStart >= 0.f ? spec.focusStart : -1.f};

            const bool hasRoll = spec.rollStart != 0.f || spec.rollEnd != 0.f;
            const bool hasFocus = spec.focusStart >= 0.f && spec.focusEnd >= 0.f;
            if (hasFocus && !(shot.focusFar > shot.focusNear)) {
                throw std::invalid_argument("applyCameraMotionShot: focusFar must exceed focusNear");
            }

            const int in = shot.inFrame;
            const int tCut = in + static_cast<int>(std::round(duration * spec.cutAt));
            const int tEnd = in + duration;
            const float fCut = at(tCut, fps);
            const float fInStart = fCut + dt;
            const Easing outEase = (std::string(spec.easing) == "whip_in")
                    ? Easing::easeIn() : Easing::easeInOut();

            const CameraPose restPose = rest;
            const CameraPose outPose = poseFor(rest, shot.subject, ref, viewport.x, viewport.y, outEnd);
            const CameraPose inPose = poseFor(rest, shot.subject, ref, viewport.x, viewport.y, inStart);

            const float rollOut = degToRad(outEnd.roll);
            const float rollIn = degToRad(inStart.roll);
            const float focusOut = hasFocus ? focusFor(outEnd.focus, shot.focusNear, shot.focusFar) : 0.f;
            const float focusIn = hasFocus ? focusFor(inStart.focus, shot.focusNear, shot.focusFar) : 0.f;
            const float focusRest = hasFocus ? focusFor(inEnd.focus, shot.focusNear, shot.focusFar) : 0.f;

            // OUT leg: rest at t0, out end held discretely through the cut.
            keyLeg(rig, restPose, degToRad(spec.rollStart * k), hasRoll,
                   hasFocus ? focusFor(spec.focusStart, shot.focusNear, shot.focusFar) : 0.f,
                   hasFocus, at(in, fps), outEase);
            rig.positionTrack().add(fCut, outPose.position, outEase);
            rig.targetTrack().add(fCut, outPose.target, Easing::easeInOut());
            if (hasRoll) rig.rollTrack().add(fCut, rollOut, outEase);
            if (hasFocus) rig.focusDistanceTrack().add(fCut, focusOut, outEase);
            // IN leg: mirrored start one frame after the cut, then the
            // composed settle — loud for whips and pass-throughs, eased
            // for reveals, rolls, arcs and focus returns.
            const Easing inEase = spec.snapIn ? Easing::expoOut() : Easing::easeInOut();
            keyLeg(rig, inPose, rollIn, hasRoll, focusIn, hasFocus, fInStart, inEase);
            keyLeg(rig, restPose, 0.f, hasRoll, focusRest, hasFocus, at(tEnd, fps), Easing::linear());

            rig.setTarget(rest.target);
            rig.setPosition(restPose.position);
            rig.setFov(shot.fov);
        }

    }// namespace

    void applyCameraMotionShot(TemplateScene& scene, CameraMotionPreset preset,
                               const CameraMotionShot& shot) {
        const CameraMotionSpec& spec = cameraMotionSpecFor(preset);
        if (spec.id == nullptr) {
            throw std::invalid_argument("applyCameraMotionShot: unknown preset");
        }
        const int duration = shot.durationOverride > 0 ? shot.durationOverride : spec.durationFrames;
        if (duration < 8) {
            throw std::invalid_argument("applyCameraMotionShot: duration must be at least 8 frames");
        }
        if (shot.inFrame < 0) {
            throw std::invalid_argument("applyCameraMotionShot: inFrame must be non-negative");
        }
        if (!finiteSubject(shot.subject) || shot.subject.halfWidth <= 0.f || shot.subject.halfHeight <= 0.f) {
            throw std::invalid_argument("applyCameraMotionShot: subject must be finite with positive extents");
        }
        if (!(shot.fov > 0.f) || !std::isfinite(shot.fov)) {
            throw std::invalid_argument("applyCameraMotionShot: fov must be positive and finite");
        }
        if (!(spec.travelStart >= 0.f) || !(spec.travelEnd <= 1.f) || !(spec.travelEnd > spec.travelStart)) {
            throw std::invalid_argument("applyCameraMotionShot: corrupt travel window");
        }
        if (spec.twoShot && (!(spec.cutAt > 0.f) || !(spec.cutAt < 1.f))) {
            throw std::invalid_argument("applyCameraMotionShot: cutAt must be inside (0, 1)");
        }
        if (spec.twoShot) {
            applyTwoShot(scene, spec, shot, duration);
        } else {
            applySingleShot(scene, spec, shot, duration);
        }
    }

}// namespace chronontemplate
