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

#include "chrononmotion/math/MathUtils.hpp"
#include "chrononmotion/motion/CameraScreenSpace.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace chronontemplate {

    using chrononmotion::Vector2;
    using chrononmotion::Vector3;
    using chrononmotion::motion::CameraPose;
    using chrononmotion::motion::CameraRig;
    using chrononmotion::motion::Easing;
    using chrononmotion::motion::ScreenCameraIntrinsics;
    using chrononmotion::math::degToRad;

    namespace {

        constexpr float kPi = 3.14159265358979323846f;

        [[nodiscard]] float at(int frame, float fps) { return static_cast<float>(frame) / fps; }

        [[nodiscard]] bool finiteAnchor(const TitleShotAnchor& anchor) {
            return std::isfinite(anchor.center.x) && std::isfinite(anchor.center.y) &&
                   std::isfinite(anchor.center.z) && std::isfinite(anchor.halfWidth) &&
                   std::isfinite(anchor.halfHeight);
        }

        // ------------------------------------------------- the 20 plans ----
        // One row per preset: the whole recipe as numbers. The rows state the
        // *end* pose relative to the frontal rest framing (`distance`, `fov`)
        // plus, where the move needs one, its start offset.

        [[nodiscard]] TitleCameraPlan planFor(TitleCameraMove move, const TitleCameraShot& shot) {
            // The loudness ladder: the same move, three strengths.
            float loudness = 1.f;
            switch (shot.intensity) {
                case TitleCameraIntensity::Subtle:    loudness = 0.55f; break;
                case TitleCameraIntensity::Editorial: loudness = 1.f;    break;
                case TitleCameraIntensity::Cinematic: loudness = 1.9f;   break;
            }

            TitleCameraPlan plan;
            plan.distance = titleCameraDistance(shot.framing, plan.fov);

            switch (move) {
                case TitleCameraMove::SlowPush:
                    // Medium → close: the title slowly fills more frame.
                    plan.dolly = plan.distance * 0.34f * loudness;
                    break;
                case TitleCameraMove::SlowPullOut:
                    // Title enormous first, then the context appears.
                    plan.dolly = -plan.distance * 0.30f * loudness;
                    break;
                case TitleCameraMove::LeftDrift:
                    // The body crosses past the title, aimed at it throughout.
                    plan.panX = 320.f * loudness;
                    break;
                case TitleCameraMove::RightDrift:
                    plan.panX = -320.f * loudness;
                    break;
                case TitleCameraMove::VerticalRise:
                    // From below the title up to the frontal rest pose.
                    plan.heightOffset = -110.f * loudness;
                    break;
                case TitleCameraMove::VerticalDescend:
                    plan.heightOffset = 110.f * loudness;
                    break;
                case TitleCameraMove::MicroOrbitLeft:
                    // +8° → −4° about the anchor; the title never moves.
                    plan.yawStart = degToRad(8.f) * loudness;
                    plan.yawEnd = degToRad(-4.f) * loudness;
                    break;
                case TitleCameraMove::MicroOrbitRight:
                    plan.yawStart = degToRad(-8.f) * loudness;
                    plan.yawEnd = degToRad(4.f) * loudness;
                    break;
                case TitleCameraMove::ArcPush:
                    // Dolly forward + lateral arc: not a plain zoom.
                    plan.restLateral = -140.f * loudness;
                    plan.arcBow = 150.f * loudness;
                    plan.dolly = plan.distance * 0.26f * loudness;
                    break;
                case TitleCameraMove::ArcPull:
                    plan.restLateral = 140.f * loudness;
                    plan.arcBow = -150.f * loudness;
                    plan.dolly = -plan.distance * 0.24f * loudness;
                    break;
                case TitleCameraMove::LowAnglePush:
                    // Slightly below, looking up; the title reads monumental.
                    // The offset is retained: the move is a push, not a rise.
                    plan.heightOffset = -70.f * loudness;
                    plan.heightEnd = plan.heightOffset;
                    plan.dolly = plan.distance * 0.24f * loudness;
                    break;
                case TitleCameraMove::HighAngleSettle:
                    plan.heightOffset = 100.f * loudness;
                    plan.heightEnd = plan.heightOffset * 0.25f;
                    break;
                case TitleCameraMove::RollSettle:
                    // The camera rolls back to level, not the text.
                    plan.rollStart = degToRad(-3.f) * loudness;
                    plan.rollEnd = 0.f;
                    plan.dolly = plan.distance * 0.08f * loudness;
                    break;
                case TitleCameraMove::RollPass:
                    // −2.5° → +2.5° → 0 during a small push.
                    plan.rollStart = degToRad(-2.5f) * loudness;
                    plan.rollPeak = degToRad(2.5f) * loudness;
                    plan.rollEnd = 0.f;
                    plan.dolly = plan.distance * 0.10f * loudness;
                    break;
                case TitleCameraMove::DollyZoomSubtle: {
                    // Mini vertigo: the title keeps its size, the background
                    // perspective changes. Projected width scales with
                    // 1 / (d · tan(fov/2)), so widening the FOV is compensated
                    // by dollying *in* by the exact tan ratio.
                    const float widen = 9.f * loudness;
                    plan.fovEnd = plan.fov + widen;
                    const float ratio = std::tan(plan.fov * 0.5f * kPi / 180.f) /
                                        std::tan(plan.fovEnd * 0.5f * kPi / 180.f);
                    plan.dolly = plan.distance * (1.f - ratio);
                    break;
                }
                case TitleCameraMove::FocusPush:
                    // Push while the background falls out of focus: the lens
                    // makes the title matter, not a glow on the text.
                    plan.dolly = plan.distance * 0.20f * loudness;
                    plan.focusPull = plan.distance * 0.20f * loudness;
                    plan.aperture = 12.f;
                    break;
                case TitleCameraMove::ParallaxSide:
                    // Layers behind move faster than the static title.
                    plan.panX = 260.f * loudness;
                    break;
                case TitleCameraMove::ParallaxPush:
                    plan.dolly = plan.distance * 0.30f * loudness;
                    break;
                case TitleCameraMove::WhipSettle: {
                    // Fast off-axis acquisition, then a long settle onto the
                    // frontal rest pose. Continuous by construction; the
                    // acquisition angle is what makes beat one loud.
                    plan.whipAcquisition = 0.25f;
                    plan.yawStart = degToRad(-24.f);
                    plan.dolly = plan.distance * 0.12f * loudness;
                    break;
                }
                case TitleCameraMove::CornerReveal:
                    // Arrive from the side where a foreground element hid the
                    // title; the diagonal pass reveals it fully.
                    plan.restLateral = -240.f * loudness;
                    plan.arcBow = -170.f * loudness;
                    plan.panX = 300.f * loudness;
                    plan.dolly = plan.distance * 0.16f * loudness;
                    break;
            }
            return plan;
        }

        /// The frontal rest pose: straight-on along +Z at the framing distance,
        /// aimed at the anchor. The pose every move starts from or lands on.
        [[nodiscard]] CameraPose restPose(const TitleCameraPlan& plan, const TitleShotAnchor& anchor) {
            CameraPose pose;
            pose.position = Vector3(anchor.center.x, anchor.center.y,
                                    anchor.center.z + plan.distance);
            pose.hasTarget = true;
            pose.target = anchor.center;
            pose.fov = plan.fov;
            return pose;
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
        }
        return "title_camera_unknown";
    }

    std::vector<std::string> titleCameraMoveIds() {
        std::vector<std::string> ids;
        ids.reserve(20);
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
                     TitleCameraMove::WhipSettle, TitleCameraMove::CornerReveal}) {
            ids.emplace_back(titleCameraMoveId(move));
        }
        return ids;
    }

    float titleCameraDistance(TitleFraming framing, float fovDegrees) {
        // The rest pose is authored so a 900-unit-wide subject fills the
        // `coverage` fraction of the frame width at the delivery aspect. One
        // scale so every preset and every title share the same optical law.
        constexpr float kReferenceWidth = 900.f;
        float coverage = 0.9f;
        switch (framing) {
            case TitleFraming::Hero:         coverage = 0.72f; break;
            case TitleFraming::Medium:       coverage = 0.55f; break;
            case TitleFraming::Wide:         coverage = 0.40f; break;
            case TitleFraming::ExtremeClose: coverage = 0.88f; break;
        }
        const float halfFovRad = fovDegrees * 0.5f * kPi / 180.f;
        const float tanHalf = std::tan(std::max(halfFovRad, 1e-4f));
        const float aspect = 1920.f / 1080.f;
        // A subject of width W at depth d fills W / (2·d·tan(fov/2)·aspect)
        // of the frame width, so the coverage fraction is the *denominator*
        // correction: tighter framing (more coverage) sits closer.
        return kReferenceWidth / (2.f * tanHalf * aspect * coverage);
    }

    TitleCameraPlan titleCameraPlanFor(TitleCameraMove move, const TitleCameraShot& shot) {
        return planFor(move, shot);
    }

    void applyTitleCameraShot(TemplateScene& scene, TitleCameraMove move,
                              const TitleCameraShot& shot) {
        if (shot.duration <= 0) {
            throw std::invalid_argument("applyTitleCameraShot: duration must be positive");
        }
        if (shot.duration < 12) {
            throw std::invalid_argument(
                    "applyTitleCameraShot: duration must allow a travel and a settle beat");
        }
        if (!finiteAnchor(shot.anchor)) {
            throw std::invalid_argument("applyTitleCameraShot: the anchor must be finite");
        }

        CameraRig& rig = scene.camera().rig();
        const float fps = scene.fps();
        const TitleCameraPlan plan = planFor(move, shot);
        const TitleShotAnchor& anchor = shot.anchor;

        const int in = shot.inFrame;
        const int settleFrames = std::clamp(shot.duration * 2 / 10, 6, 12);
        const int travelEnd = in + shot.duration - settleFrames;
        const int end = in + shot.duration;
        const float t0 = at(in, fps);
        const float t1 = at(travelEnd, fps);
        const float t2 = at(end, fps);
        const bool hasRoll = plan.rollStart != 0.f || plan.rollPeak != 0.f || plan.rollEnd != 0.f;
        const bool hasFov = plan.fovEnd != 0.f;
        const bool hasFocus = plan.focusPull != 0.f;
        const bool whip = plan.whipAcquisition > 0.f;
        const bool orbits = whip || plan.yawStart != 0.f || plan.yawEnd != 0.f;

        // --- the endpoint poses --------------------------------------------
        // `rest` is the frontal framing; `start` and `end` are the move's two
        // poses, both built from the same optical law. Every pose aims at the
        // anchor: the look-at is the target lock, so drifting the body never
        // rotates or translates the title.
        const CameraPose rest = restPose(plan, anchor);
        const CameraPose start = [&] {
            CameraPose pose = rest;
            Vector2 pan;
            if (orbits) {
                CameraRig::orbitAround(pose, anchor.center, plan.yawStart, 0.f);
            } else if (plan.arcBow != 0.f) {
                pan = Vector2(plan.restLateral, 0.f);
                CameraRig::pan(pose, pan);
            } else {
                // Drifts cross past the anchor; rises/angle moves start at
                // their authored height offset (negative = below the anchor).
                pan = Vector2(-plan.panX * 0.5f, plan.heightOffset);
                CameraRig::pan(pose, pan);
            }
            return pose;
        }();
        const CameraPose endPose = [&] {
            CameraPose pose = rest;
            if (orbits) {
                CameraRig::orbitAround(pose, anchor.center, plan.yawEnd, 0.f);
            } else if (plan.arcBow != 0.f) {
                // The arc lands on the straight-on rest framing: the bow was
                // the mid-travel shape, not a lateral end offset.
            } else {
                CameraRig::pan(pose, Vector2(plan.panX * 0.5f, plan.heightEnd));
            }
            CameraRig::dolly(pose, plan.dolly);
            if (plan.arcBow != 0.f) {
                // The endpoint keeps a small residual body offset so the arc's
                // chord reads as travel, while the aim stays on the anchor.
                CameraRig::pan(pose, Vector2(plan.restLateral * -0.35f, 0.f));
            }
            return pose;
        }();

        // Mid-travel pose: the arc's bow, or the orbit's mid swing.
        const float tMid = at((in + travelEnd) / 2, fps);
        const CameraPose midPose = [&] {
            CameraPose pose = rest;
            CameraRig::pan(pose, Vector2(
                    plan.arcBow != 0.f ? plan.restLateral + plan.arcBow * 0.5f : plan.panX * 0.5f,
                    (plan.heightOffset + plan.heightEnd) * 0.5f));
            if (orbits) {
                CameraRig::orbitAround(pose, anchor.center,
                                       (plan.yawStart + plan.yawEnd) * 0.5f, 0.f);
            }
            CameraRig::dolly(pose, plan.dolly * 0.5f);
            return pose;
        }();

        // --- position + target lock ----------------------------------------
        auto& position = rig.positionTrack();
        auto& target = rig.targetTrack();

        if (whip) {
            // Three beats: swing out fast, re-acquire, settle. The pose chain
            // is continuous; the *velocity* is deliberately loud on beat one
            // (expoOut concentrates the rate at the top of the whip).
            position.add(t0, start.position, Easing::expoOut());
            position.add(tMid, midPose.position, Easing::easeInOut());
            position.add(t1, endPose.position, Easing::easeInOut());
            target.add(t0, anchor.center, Easing::easeInOut());
            target.add(t1, anchor.center, Easing::linear());
        } else if (plan.arcBow != 0.f || orbits) {
            // A curved path: ease up to the apex, ease down from it, so the
            // velocity is continuous through the mid key (an ease-in-out on
            // both halves would dip to zero at the apex — a stall mid-move).
            position.add(t0, start.position, Easing::easeIn());
            position.add(tMid, midPose.position, Easing::easeOut());
            position.add(t1, endPose.position, Easing::easeInOut());
            target.add(t0, anchor.center, Easing::easeInOut());
            target.add(t1, anchor.center, Easing::linear());
        } else {
            position.add(t0, start.position, Easing::easeInOut());
            position.add(t1, endPose.position, Easing::easeInOut());
            target.add(t0, anchor.center, Easing::easeInOut());
            target.add(t1, anchor.center, Easing::linear());
        }
        // The settle beat: hold the endpoint, decelerating into the hold.
        position.add(t2, endPose.position, Easing::linear());
        target.add(t2, anchor.center, Easing::linear());

        // --- roll ------------------------------------------------------------
        if (hasRoll) {
            auto& roll = rig.rollTrack();
            roll.add(t0, plan.rollStart, Easing::easeInOut());
            if (plan.rollPeak != 0.f) roll.add(tMid, plan.rollPeak, Easing::easeInOut());
            roll.add(t1, plan.rollEnd, Easing::easeInOut());
            roll.add(t2, plan.rollEnd, Easing::linear());
        }

        // --- fov ---------------------------------------------------------------
        if (hasFov) {
            auto& fov = rig.fovTrack();
            fov.add(t0, plan.fov, Easing::easeInOut());
            fov.add(t1, plan.fovEnd, Easing::easeInOut());
            fov.add(t2, plan.fovEnd, Easing::linear());
        }

        // --- the lens: focus + aperture ----------------------------------------
        if (hasFocus) {
            auto& focus = rig.focusDistanceTrack();
            focus.add(t0, plan.distance, Easing::easeInOut());
            focus.add(t1, plan.distance - plan.focusPull, Easing::easeInOut());
            focus.add(t2, plan.distance - plan.focusPull, Easing::linear());
        }
        if (plan.aperture != 0.f) {
            auto& aperture = rig.apertureTrack();
            aperture.add(t0, 0.f, Easing::easeInOut());
            aperture.add(t1, plan.aperture, Easing::easeInOut());
            aperture.add(t2, plan.aperture, Easing::linear());
        }

        // The rig's static pose agrees with where the move lands, so frames
        // outside the window sample the settled framing.
        rig.setTarget(rest.target);
        rig.setPosition(endPose.position);
        rig.setFov(hasFov ? plan.fovEnd : plan.fov);

        // The framing law: the title anchor stays inside the safe area for the
        // whole window. A plan that breaks it fails loudly here, instead of
        // shipping an unreadable title.
        ScreenCameraIntrinsics intrinsics;
        intrinsics.viewport = scene.canvas();
        for (int f = in; f <= end; ++f) {
            const CameraPose pose = rig.sample(at(f, fps));
            intrinsics.fovDegrees = pose.fov;
            const Vector2 screen =
                    chrononmotion::motion::projectToScreen(anchor.center, pose, intrinsics);
            const bool inside = screen.x >= 0.05f * intrinsics.viewport.x &&
                                screen.x <= 0.95f * intrinsics.viewport.x &&
                                screen.y >= 0.08f * intrinsics.viewport.y &&
                                screen.y <= 0.92f * intrinsics.viewport.y;
            if (!inside) {
                throw std::invalid_argument(
                        std::string("applyTitleCameraShot: ") + titleCameraMoveId(move) +
                        " leaves the title anchor outside the safe area");
            }
        }
    }

}// namespace chronontemplate
