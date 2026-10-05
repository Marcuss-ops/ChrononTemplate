// ChrononTemplate — the scene-camera pack, implementation.
//
// The sequence model, stated once: a chain of *holds* (the stacchi — one rest
// pose per beat, derived from the beat's own subject) joined by *travel legs*.
// Every leg is keyed from the exact rest pose of beat N to the exact rest pose
// of beat N+1, so no matter how many beats the chain is continuous at every
// boundary — the pose a hold ends on is the pose the next leg starts from.
//
// Each transition is a plan of numeric deltas applied to the two rest poses
// with the rig's own pure moves (`pan`, `dolly`, `orbitAround`, `roll`), then
// keyed with a 3-key shaped path (approach / apex / land) whose halves are
// eased so the velocity is continuous through the apex. A short settle keys
// the last frames of every hold so a landing decelerates instead of stopping
// dead — the documentary grammar the title-camera pack established.
//
// The rig's static pose ends on the FIRST rest (the opening hold), so frames
// before the first leg sample the first framing.

#include "chronontemplate/SceneCameraPack.hpp"

#include "chrononmotion/math/MathUtils.hpp"
#include "chrononmotion/motion/CameraScreenSpace.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

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

        [[nodiscard]] bool finiteSubject(const SceneSubject& s) {
            return std::isfinite(s.center.x) && std::isfinite(s.center.y) && std::isfinite(s.center.z) &&
                   std::isfinite(s.halfWidth) && std::isfinite(s.halfHeight);
        }

        // The full plan of one leg: both rest poses plus the shaped travel
        // deltas. Derived per pair of beats by the transition table.
        struct LegPlan {
            CameraPose restA{};   ///< the pose beat A's hold rests on
            CameraPose restB{};   ///< the pose beat B's hold rests on
            // Travel shape, in the deltas the rig's pure moves consume.
            float lateral{0.f};   ///< mid-travel lateral bow (world units, camera plane)
            float height{0.f};    ///< mid-travel vertical bow (world units)
            float dollyApex{0.f}; ///< extra dolly at the apex (negative = pull away)
            float yaw{0.f};       ///< orbit sweep about the seam pivot (radians)
            float rollPeak{0.f};  ///< roll at the apex (radians, returns to 0)
            float fovPeak{0.f};   ///< fov at the apex (0 = untouched)
            float focusShift{0.f};///< focus-distance delta applied over the leg (A → B focus)
            float aperture{0.f};  ///< aperture keyed during the leg (0 = untouched)
            bool aimBoth{true};   ///< false: mid-travel aim interpolates between the centres
            float travelEase{0.f};///< >0: one loud acquisition (whip) on the first half
        };

        // ------------------------------------------------------- the rests --
        //
        // One rest pose per subject, derived from the subject itself: the
        // camera sits straight-on along +Z from the centre at the framing
        // distance, aimed at it, on the kind's lens. The framing law keeps the
        // subject at `frameFill` of the tighter frame axis, so a phrase, an
        // image and a title each frame at their own correct tightness from one
        // function.

        [[nodiscard]] CameraPose restPoseFor(const SceneSubject& subject, const Vector2& viewport,
                                             float intensity) {
            const float fov = sceneSubjectFov(subject.kind);
            const float fill = 0.62f + 0.10f * intensity; // louder = closer
            const float distance = sceneFramingDistance(subject, fov, viewport, fill);
            CameraPose pose;
            pose.position = Vector3(subject.center.x, subject.center.y, subject.center.z + distance);
            pose.hasTarget = true;
            pose.target = subject.center;
            pose.fov = fov;
            return pose;
        }

        // ------------------------------------------------ the transition plans

        [[nodiscard]] LegPlan planLeg(SceneCameraTransition transition, const CameraPose& restA,
                                      const CameraPose& restB, const SceneSubject& a,
                                      const SceneSubject& b, float loudness, const Vector2& viewport) {
            LegPlan plan;
            plan.restA = restA;
            plan.restB = restB;
            // The seam between the two holds: the world midpoint the travel
            // shapes itself around.
            const Vector3 seam{(restA.position + restB.position) * 0.5f};

            switch (transition) {
                case SceneCameraTransition::PushThrough: {
                    // Dive through the seam: pull back slightly, accelerate
                    // forward through the midpoint, land on B's framing.
                    plan.dollyApex = -(restA.position - restA.target).length() * 0.10f * loudness;
                    plan.fovPeak = restA.fov + 4.f * loudness;
                    break;
                }
                case SceneCameraTransition::LateralSwipe: {
                    // The body crosses sideways past the seam while the aim
                    // already walks from A to B; the world slides under a
                    // locked lens.
                    plan.lateral = 190.f * loudness;
                    plan.aimBoth = false;
                    break;
                }
                case SceneCameraTransition::ArcCarry: {
                    // A curved perpendicular bow: approach eases in, apex
                    // carries, land eases out — the elegant default.
                    plan.lateral = 230.f * loudness;
                    plan.height = 60.f * loudness;
                    break;
                }
                case SceneCameraTransition::OrbitHandoff: {
                    // The camera orbits the seam pivot a quarter turn while
                    // the framing travels A → B; the world rotates past.
                    plan.yaw = degToRad(26.f) * loudness;
                    break;
                }
                case SceneCameraTransition::RiseAndLand: {
                    // Lift over the seam and settle down onto the next hold:
                    // the vertical counterpart of the arc.
                    plan.height = 150.f * loudness;
                    plan.dollyApex = -(restA.position - restA.target).length() * 0.06f * loudness;
                    break
                    ;
                }
                case SceneCameraTransition::FocusRack: {
                    // A near-still frame: the position barely breathes, the
                    // lens hands focus (and attention) from A to B.
                    plan.lateral = 26.f * loudness;
                    plan.focusShift = 1.f; // marker: focus keyed A → B
                    plan.aperture = 14.f;
                    break;
                }
                case SceneCameraTransition::PullBackReveal: {
                    // Leave A tight with a small roll, pull back to see both,
                    // land wide on B. Tight-leave + wide-land is the reveal.
                    plan.dollyApex = -(restA.position - restA.target).length() * 0.22f * loudness;
                    plan.rollPeak = degToRad(-2.5f) * loudness;
                    plan.fovPeak = std::max(restA.fov, restB.fov) + 6.f * loudness;
                    break;
                }
                case SceneCameraTransition::WhipReframe: {
                    // One loud acquisition swing, then a long settle onto B.
                    // Continuous by construction; the rate is deliberately
                    // loud at the start (expoOut concentrates the rate early
                    // and spends the back half settling).
                    plan.lateral = 120.f * loudness;
                    plan.travelEase = 1.f;
                    break;
                }
            }
            (void) seam;
            (void) a;
            (void) b;
            (void) viewport;
            return plan;
        }

        /// The apex pose of a leg: the rests shaped by the plan's mid-travel
        /// deltas, aimed between the two subjects (or locked ahead on a swipe).
        [[nodiscard]] CameraPose apexPose(const LegPlan& plan, const SceneSubject& a,
                                          const SceneSubject& b, float progress) {
            CameraPose pose = plan.restA;
            CameraRig::pan(pose, Vector2(plan.lateral * 0.5f, plan.height * 0.5f));
            if (plan.dollyApex != 0.f) CameraRig::dolly(pose, plan.dollyApex);
            if (plan.yaw != 0.f) {
                CameraRig::orbitAround(pose, (plan.restA.target + plan.restB.target) * 0.5f,
                                       plan.yaw * progress, 0.f);
            }
            if (plan.rollPeak != 0.f) CameraRig::roll(pose, plan.rollPeak);

            // The aim: locked ahead on a swipe, interpolated between centres
            // otherwise — and the focus rides the same blend.
            pose.target = plan.aimBoth ? Vector3(plan.restA.target + plan.restB.target) * 0.5f
                                       : plan.restB.target;
            if (plan.focusShift != 0.f) {
                const float distA = (plan.restA.position - plan.restA.target).length();
                const float distB = (plan.restB.position - plan.restB.target).length();
                pose.focusDistance = distA + (distB - distA) * progress;
            }
            if (plan.fovPeak != 0.f) pose.fov = plan.fovPeak;
            (void) a;
            (void) b;
            return pose;
        }

        /// Key one travel leg onto the rig: from `restA` exactly, through the
        /// shaped apex, to `restB` exactly, then let the next hold take over.
        void keyLeg(CameraRig& rig, const LegPlan& plan, const SceneSubject& a, const SceneSubject& b,
                    int inFrame, int travelFrames, float fps) {
            const float t0 = at(inFrame, fps);
            const float tApex = at(inFrame + travelFrames / 2, fps);
            const float t1 = at(inFrame + travelFrames, fps);

            const CameraPose apex = apexPose(plan, a, b, 0.5f);

            // Position + target: a shaped 3-key path whose halves have
            // *matched* slopes. The approach ends where the land begins (the
            // same normalized slope M on both halves), so the sampled velocity
            // is continuous through the apex — an easeIn|easeOut pair would
            // stall at the key and surge out of it. The whip swaps the
            // approach for the loud acquisition: a fast start decaying into
            // the same apex slope, loud in rate yet still continuous.
            auto& position = rig.positionTrack();
            auto& target = rig.targetTrack();
            const Easing approach = plan.travelEase > 0.f ? Easing::cubicBezier(0.7f, 0.9f, 0.7f, 0.9f)
                                                          : Easing::cubicBezier(0.5f, 0.f, 0.7f, 0.9f);
            const Easing land = Easing::cubicBezier(0.3f, 0.1f, 0.5f, 1.f);
            position.add(t0, plan.restA.position, approach);
            position.add(tApex, apex.position, land);
            position.add(t1, plan.restB.position, Easing::easeInOut());
            target.add(t0, plan.restA.target, approach);
            target.add(tApex, apex.target, land);
            target.add(t1, plan.restB.target, Easing::easeInOut());

            // Roll: a peak at the apex, resolved by the land.
            if (plan.rollPeak != 0.f) {
                auto& roll = rig.rollTrack();
                roll.add(t0, 0.f, Easing::easeInOut());
                roll.add(tApex, plan.rollPeak, Easing::easeOut());
                roll.add(t1, 0.f, Easing::easeInOut());
            }

            // FOV: a peak at the apex, resolved by the land.
            if (plan.fovPeak != 0.f) {
                auto& fov = rig.fovTrack();
                fov.add(t0, plan.restA.fov, Easing::easeInOut());
                fov.add(tApex, plan.fovPeak, Easing::easeOut());
                fov.add(t1, plan.restB.fov, Easing::easeInOut());
            }

            // The lens: focus rides A → B; a rack holds the aperture open for
            // the whole leg so the handoff is visible.
            if (plan.focusShift != 0.f || plan.aperture != 0.f) {
                const float distA = (plan.restA.position - plan.restA.target).length();
                const float distB = (plan.restB.position - plan.restB.target).length();
                auto& focus = rig.focusDistanceTrack();
                focus.add(t0, distA, Easing::easeInOut());
                focus.add(tApex, (distA + distB) * 0.5f, Easing::easeInOut());
                focus.add(t1, distB, Easing::easeInOut());
                if (plan.aperture != 0.f) {
                    auto& aperture = rig.apertureTrack();
                    aperture.add(t0, 0.f, Easing::easeInOut());
                    aperture.add(t1, plan.aperture, Easing::easeInOut());
                }
            }
        }

    }// namespace

    const char* sceneCameraTransitionId(SceneCameraTransition transition) noexcept {
        switch (transition) {
            case SceneCameraTransition::PushThrough:    return "scene_camera_push_through";
            case SceneCameraTransition::LateralSwipe:   return "scene_camera_lateral_swipe";
            case SceneCameraTransition::ArcCarry:       return "scene_camera_arc_carry";
            case SceneCameraTransition::OrbitHandoff:   return "scene_camera_orbit_handoff";
            case SceneCameraTransition::RiseAndLand:    return "scene_camera_rise_and_land";
            case SceneCameraTransition::FocusRack:      return "scene_camera_focus_rack";
            case SceneCameraTransition::PullBackReveal: return "scene_camera_pull_back_reveal";
            case SceneCameraTransition::WhipReframe:    return "scene_camera_whip_reframe";
        }
        return "scene_camera_unknown";
    }

    std::vector<std::string> sceneCameraTransitionIds() {
        return {
                sceneCameraTransitionId(SceneCameraTransition::PushThrough),
                sceneCameraTransitionId(SceneCameraTransition::LateralSwipe),
                sceneCameraTransitionId(SceneCameraTransition::ArcCarry),
                sceneCameraTransitionId(SceneCameraTransition::OrbitHandoff),
                sceneCameraTransitionId(SceneCameraTransition::RiseAndLand),
                sceneCameraTransitionId(SceneCameraTransition::FocusRack),
                sceneCameraTransitionId(SceneCameraTransition::PullBackReveal),
                sceneCameraTransitionId(SceneCameraTransition::WhipReframe),
        };
    }

    float sceneSubjectFov(SubjectKind kind) {
        switch (kind) {
            case SubjectKind::Phrase: return 50.f;
            case SubjectKind::Image:  return 62.f;
            case SubjectKind::Text:   return 44.f;
            case SubjectKind::Card:   return 56.f;
        }
        return 55.f;
    }

    float sceneFramingDistance(const SceneSubject& subject, float fovDegrees,
                               const Vector2& viewport, float frameFill) {
        // A subject of half-extents (hw, hh) at depth d spans
        // 2·d·tan(fov/2) vertically and 2·d·tan(fov/2)·aspect horizontally, so
        // fitting `frameFill` of the *tighter* frame axis gives one distance
        // for every subject shape and every aspect.
        const float halfFovRad = std::max(fovDegrees * 0.5f * kPi / 180.f, 1e-4f);
        const float tanHalf = std::tan(halfFovRad);
        const float aspect = viewport.x / std::max(viewport.y, 1.f);
        const float fill = std::clamp(frameFill, 0.1f, 0.98f);
        const float distV = subject.halfHeight / (tanHalf * fill);
        const float distH = subject.halfWidth / (tanHalf * fill * aspect);
        return std::max(distV, distH);
    }

    void applySceneCameraSequence(TemplateScene& scene, const SceneCameraSequence& sequence) {
        if (sequence.beats.size() < 2) {
            throw std::invalid_argument("applySceneCameraSequence: a sequence needs at least two beats");
        }
        if (sequence.travelFrames <= 0) {
            throw std::invalid_argument("applySceneCameraSequence: travelFrames must be positive");
        }
        if (sequence.intensity <= 0.f || !std::isfinite(sequence.intensity)) {
            throw std::invalid_argument("applySceneCameraSequence: intensity must be positive and finite");
        }
        for (const SceneBeat& beat : sequence.beats) {
            if (beat.hold < 6) {
                throw std::invalid_argument(
                        "applySceneCameraSequence: every hold must be at least 6 frames");
            }
            if (!finiteSubject(beat.subject)) {
                throw std::invalid_argument("applySceneCameraSequence: subjects must be finite");
            }
        }

        CameraRig& rig = scene.camera().rig();
        const float fps = scene.fps();
        const Vector2 viewport = scene.canvas();
        const float loudness = sequence.intensity;
        const int travel = sequence.travelFrames;

        int frame = sequence.inFrame;
        CameraPose previousRest{};
        bool first = true;

        for (std::size_t i = 0; i + 1 < sequence.beats.size(); ++i) {
            const SceneBeat& a = sequence.beats[i];
            const SceneBeat& b = sequence.beats[i + 1];
            const CameraPose restA = restPoseFor(a.subject, viewport, loudness);
            const CameraPose restB = restPoseFor(b.subject, viewport, loudness);
            if (first) {
                previousRest = restA;
                first = false;
            }

            // -- the hold on A ------------------------------------------------
            // Lock the framing: position and target sit on the rest pose for
            // the whole hold, with a settling tail so the previous leg's
            // arrival (and this hold's exit) decelerate into the rest.
            const int holdEnd = frame + a.hold;
            {
                auto& position = rig.positionTrack();
                auto& target = rig.targetTrack();
                const float tIn = at(frame, fps);
                const float tSettle = at(frame + std::min(a.hold - 2, 8), fps);
                const float tOut = at(holdEnd, fps);
                position.add(tIn, restA.position, Easing::linear());
                position.add(tSettle, restA.position, Easing::easeInOut());
                position.add(tOut, restA.position, Easing::linear());
                target.add(tIn, restA.target, Easing::linear());
                target.add(tSettle, restA.target, Easing::easeInOut());
                target.add(tOut, restA.target, Easing::linear());

                // The kind's lens holds for the hold, so a leg's FOV always
                // starts from the value the previous key ends on.
                auto& fov = rig.fovTrack();
                fov.add(tIn, restA.fov, Easing::linear());
                fov.add(tOut, restA.fov, Easing::linear());
            }

            // -- the travel leg ------------------------------------------------
            const LegPlan plan = planLeg(sequence.transition, restA, restB, a.subject, b.subject,
                                         loudness, viewport);
            keyLeg(rig, plan, a.subject, b.subject, holdEnd, travel, fps);
            frame = holdEnd + travel;
        }

        // -- the final hold ------------------------------------------------------
        {
            const SceneBeat& last = sequence.beats.back();
            const CameraPose rest = restPoseFor(last.subject, viewport, loudness);
            const float tIn = at(frame, fps);
            const float tOut = at(frame + last.hold, fps);
            auto& position = rig.positionTrack();
            auto& target = rig.targetTrack();
            position.add(tIn, rest.position, Easing::linear());
            position.add(tIn + 8.f / fps, rest.position, Easing::easeInOut());
            position.add(tOut, rest.position, Easing::linear());
            target.add(tIn, rest.target, Easing::linear());
            target.add(tIn + 8.f / fps, rest.target, Easing::easeInOut());
            target.add(tOut, rest.target, Easing::linear());
            auto& fov = rig.fovTrack();
            fov.add(tIn, rest.fov, Easing::linear());
            fov.add(tOut, rest.fov, Easing::linear());
        }

        // The rig's static pose agrees with the FIRST rest, so frames before
        // the first keyed instant sample the opening framing.
        rig.setTarget(previousRest.target);
        rig.setPosition(previousRest.position);
        rig.setFov(previousRest.fov);
        rig.setAspect(viewport.x / std::max(viewport.y, 1.f));

        // The framing gate: every subject stays inside the safe area while its
        // own hold rests on it. A plan that breaks it fails loudly here.
        ScreenCameraIntrinsics intrinsics;
        intrinsics.viewport = viewport;
        for (const SceneBeat& beat : sequence.beats) {
            const CameraPose rest = restPoseFor(beat.subject, viewport, loudness);
            intrinsics.fovDegrees = rest.fov;
            const Vector2 screen = chrononmotion::motion::projectToScreen(beat.subject.center, rest, intrinsics);
            const bool inside = screen.x >= 0.05f * viewport.x && screen.x <= 0.95f * viewport.x &&
                                screen.y >= 0.08f * viewport.y && screen.y <= 0.92f * viewport.y;
            if (!inside) {
                throw std::invalid_argument(
                        std::string("applySceneCameraSequence: the rest framing of ") +
                        sceneCameraTransitionId(sequence.transition) +
                        " leaves a subject outside the safe area");
            }
        }
    }

}// namespace chronontemplate
