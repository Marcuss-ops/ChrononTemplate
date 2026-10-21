// ChrononTemplate — the title-camera documentary pack, implementation.
//
// Twenty editorial recipes over six camera primitives. Every recipe:
//   - keys the rig's position/target/FOV/focus/roll channels only;
//   - aims every sampled pose at the anchor (target lock) — the look-at
//     convention of the rig is the lock, so drifting the body never rotates
//     or translates the title;
//   - never touches the title layer, whose transform stays empty;
//   - ends with a settle: the last beat decelerates so the move lands instead
//     of stopping dead, the documentary grammar the family exists for.
//
// The camera is the only animated thing: `applyTitleCameraShot` writes rig
// tracks and nothing else, which is the contract the P0 test pins.

#include "chronontemplate/camera_roll/TitleCameraPack.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace chronontemplate {

    using chrononmotion::Vector3;

    namespace {

        [[nodiscard]] bool finiteAnchor(const TitleShotAnchor& anchor) {
            return std::isfinite(anchor.center.x) && std::isfinite(anchor.center.y) &&
                   std::isfinite(anchor.center.z) && std::isfinite(anchor.halfWidth) &&
                   std::isfinite(anchor.halfHeight);
        }

        [[nodiscard]] TitleCameraPlan planFor(TitleCameraMove move, const TitleCameraShot& shot) {
            using namespace chrononmotion::motion::camera;
            return chrononmotion::motion::camera::resolveTitleCameraPlan(
                    move, chrononmotion::motion::camera::TitleRecipeShot{shot.framing, shot.intensity, 55.f});
        }

    }// namespace

    const char* titleCameraMoveId(TitleCameraMove move) noexcept {
        switch (move) {
            case TitleCameraMove::SlowPush:        return "title_camera_slow_push";
            case TitleCameraMove::SlowPullOut:     return "title_camera_slow_pull_out";
            case TitleCameraMove::LeftDrift:       return "title_camera_left_drift";
            case TitleCameraMove::RightDrift:      return "title_camera_right_drift";
            case TitleCameraMove::VerticalRise:    return "title_camera_vertical_rise";
            case TitleCameraMove::VerticalDescend: return "title_camera_vertical_descend";
            case TitleCameraMove::MicroOrbitLeft:  return "title_camera_micro_orbit_left";
            case TitleCameraMove::MicroOrbitRight: return "title_camera_micro_orbit_right";
            case TitleCameraMove::ArcPush:         return "title_camera_arc_push";
            case TitleCameraMove::ArcPull:         return "title_camera_arc_pull";
            case TitleCameraMove::LowAnglePush:    return "title_camera_low_angle_push";
            case TitleCameraMove::HighAngleSettle: return "title_camera_high_angle_settle";
            case TitleCameraMove::RollSettle:      return "title_camera_roll_settle";
            case TitleCameraMove::RollPass:        return "title_camera_roll_pass";
            case TitleCameraMove::DollyZoomSubtle: return "title_camera_dolly_zoom_subtle";
            case TitleCameraMove::FocusPush:       return "title_camera_focus_push";
            case TitleCameraMove::ParallaxSide:    return "title_camera_parallax_side";
            case TitleCameraMove::ParallaxPush:    return "title_camera_parallax_push";
            case TitleCameraMove::WhipSettle:      return "title_camera_whip_settle";
            case TitleCameraMove::CornerReveal:    return "title_camera_corner_reveal";
            case TitleCameraMove::CrashPush:       return "title_camera_crash_push";
            case TitleCameraMove::TopDownSettle:  return "title_camera_top_down_settle";
            case TitleCameraMove::HandheldMicro:  return "title_camera_handheld_micro";
            case TitleCameraMove::OrbitWide:       return "title_camera_orbit_wide";
            case TitleCameraMove::FloorRise:       return "title_camera_floor_rise";
        }
        return "title_camera_unknown";
    }

    std::vector<std::string> titleCameraMoveIds() {
        std::vector<std::string> ids;
        ids.reserve(25);
        for (const TitleCameraMove move : {
                     TitleCameraMove::SlowPush, TitleCameraMove::SlowPullOut,
                     TitleCameraMove::LeftDrift, TitleCameraMove::RightDrift,
                     TitleCameraMove::VerticalRise, TitleCameraMove::VerticalDescend,
                     TitleCameraMove::MicroOrbitLeft, TitleCameraMove::MicroOrbitRight,
                     TitleCameraMove::ArcPush, TitleCameraMove::ArcPull,
                     TitleCameraMove::LowAnglePush, TitleCameraMove::HighAngleSettle,
                     TitleCameraMove::RollSettle, TitleCameraMove::RollPass,
                     TitleCameraMove::DollyZoomSubtle, TitleCameraMove::FocusPush,
                     TitleCameraMove::ParallaxSide, TitleCameraMove::ParallaxPush,
                     TitleCameraMove::WhipSettle, TitleCameraMove::CornerReveal,
                     TitleCameraMove::CrashPush, TitleCameraMove::TopDownSettle,
                     TitleCameraMove::HandheldMicro, TitleCameraMove::OrbitWide,
                     TitleCameraMove::FloorRise}) {
            ids.emplace_back(titleCameraMoveId(move));
        }
        return ids;
    }

    float titleCameraDistance(TitleFraming framing, float fovDegrees) {
        return chrononmotion::motion::camera::titleFramingDistance(framing, fovDegrees);
    }

    TitleCameraPlan titleCameraPlanFor(TitleCameraMove move, const TitleCameraShot& shot) {
        return planFor(move, shot);
    }

    void applyTitleCameraShot(TemplateScene& scene, TitleCameraMove move,
                              const TitleCameraShot& shot) {
        if (!finiteAnchor(shot.anchor)) {
            throw std::invalid_argument("applyTitleCameraShot: the anchor must be finite");
        }

        chrononmotion::motion::presets::author(scene.motion(), titleCameraMoveId(move), [&] {
        using namespace chrononmotion::motion::camera;
        applyTitleCameraRequest(scene.camera().rig(), TitleCameraRequest{
            move, TitleRecipeShot{shot.framing, shot.intensity, 55.f}, shot.anchor.center,
            shot.inFrame, shot.duration, scene.fps(), scene.canvas()
        });
        });
    }

}// namespace chronontemplate
