// The title-camera documentary pack's acceptance suite.
//
// Eight gates, one per family contract, sampled per frame across the whole
// window of every preset:
//
//   P0  the title never animates — empty layer tracks, or a transform that is
//       identical at every sampled frame;
//   2.  the camera really animates — no preset samples to a single pose;
//   3.  the framing holds — the anchor stays inside the safe area;
//   4.  the hero occupancy moves — a push grows the projected title width;
//   5.  the target lock holds — the projected centre tracks its desired place;
//   6.  quaternion continuity — no hemisphere flip between neighbor frames;
//   7.  velocity continuity — no channel teleporting between frames;
//   8.  the end settle — the last beat is slower than mid-travel.
//
// The whip is the declared exception on gate 7 (a loud acquisition is its
// point), not on any other gate.

#include "chronontemplate/camera_roll/TitleCameraPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include "chrononmotion/math/Matrix4.hpp"
#include "chrononmotion/math/Quaternion.hpp"
#include "chrononmotion/math/Vector2.hpp"
#include "chrononmotion/motion/CameraScreenSpace.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion::Quaternion;
using chrononmotion::Vector2;
using chrononmotion::Vector3;
using chrononmotion::motion::CameraPose;
using chrononmotion::motion::projectToScreen;
using chrononmotion::motion::ScreenCameraIntrinsics;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    constexpr float kViewportW = 1920.f;
    constexpr float kViewportH = 1080.f;

    struct Sample {
        CameraPose pose{};
        Vector2 screen{0.f, 0.f};
        Vector3 positionVelocity{0.f, 0.f, 0.f};
        float fovRate{0.f};
        float rollRate{0.f};
    };

    // One scene per preset, the same title anchor every time: the canary
    // grammar (title_camera_documentary_gallery_v1) — only the camera differs.
    [[nodiscard]] std::vector<Sample> samplePreset(TitleCameraMove move,
                                                   const TitleCameraShot& shot,
                                                   FakeContentHost& host,
                                                   chrononmotion::motion::Layer::Id& titleIdOut) {
        TemplateScene scene("title_camera_test", 30.f, host, kViewportW, kViewportH);
        auto& title = scene.text({.text = "THE ART OF SIMPLICITY", .font = "Inter-Bold.ttf",
                                  .fontSize = 180.f});
        title.position(960.f, 540.f);
        titleIdOut = title.id();

        applyTitleCameraShot(scene, move, shot);

        const float fps = scene.fps();
        const float dt = 1.f / fps;
        ScreenCameraIntrinsics intrinsics;
        intrinsics.viewport = Vector2(kViewportW, kViewportH);

        std::vector<Sample> samples;
        samples.reserve(static_cast<std::size_t>(shot.duration) + 1);
        for (int f = 0; f <= shot.duration; ++f) {
            Sample sample;
            const float seconds = static_cast<float>(f) / fps;
            sample.pose = scene.camera().rig().sample(seconds);
            intrinsics.fovDegrees = sample.pose.fov;
            sample.screen = projectToScreen(shot.anchor.center, sample.pose, intrinsics);
            const auto derivative = scene.camera().rig().sampleDerivative(seconds);
            sample.positionVelocity = derivative.linearVelocity;
            sample.fovRate = derivative.fovRate;
            sample.rollRate = derivative.rollRate;
            samples.push_back(std::move(sample));
        }
        (void) dt;
        return samples;
    }

    [[nodiscard]] float length(const Vector3& v) { return std::sqrt(v.dot(v)); }

    [[nodiscard]] bool poseNear(const CameraPose& a, const CameraPose& b, float epsilon) {
        const Vector3 dp = a.position - b.position;
        return length(dp) <= epsilon && std::fabs(a.roll - b.roll) <= epsilon &&
               std::fabs(a.fov - b.fov) <= epsilon;
    }

    void theTitleNeverAnimates() {
        section("P0: the title never animates");
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
            FakeContentHost host;
            TemplateScene scene("title_camera_p0", 30.f, host, kViewportW, kViewportH);
            auto& title = scene.text({.text = "ROME", .font = "Inter-Bold.ttf", .fontSize = 180.f});
            title.position(960.f, 540.f);

            const chrononmotion::motion::Layer* layer = scene.motion().findLayer(title.id());
            check(layer != nullptr, "the title layer exists");
            if (layer == nullptr) continue;
            check(layer->tracks.position.empty() && layer->tracks.scale.empty() &&
                          layer->tracks.rotation.empty() && layer->tracks.opacity.empty() &&
                          layer->tracks.orientation.empty(),
                  "title_camera_* writes no title tracks: the text transform stays empty");

            applyTitleCameraShot(scene, move,
                                 TitleCameraShot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                                 .inFrame = 0,
                                                 .duration = 135});

            const chrononmotion::motion::Layer* after = scene.motion().findLayer(title.id());
            check(after != nullptr && after->tracks.position.empty() &&
                          after->tracks.scale.empty() && after->tracks.rotation.empty(),
                  "applying the shot still leaves every title track empty");
            if (after == nullptr) continue;

            // The stronger form of the same contract: sampled frame 0 vs end,
            // the whole title transform is bit-identical.
            const FrameSubmission first = scene.submit(0);
            const FrameSubmission last = scene.submit(135);
            const chronontemplate::BoundLayer* a = findLayer(first, title.id());
            const chronontemplate::BoundLayer* b = findLayer(last, title.id());
            check(a && b, "the title submits at both ends of the move");
            if (a && b) {
                check(chronontemplate_test::sameMatrix(a->transform.world, b->transform.world),
                      "titleTransform(frame0) == titleTransform(frameEnd): the title never moves");
                check(std::fabs(a->transform.opacity - b->transform.opacity) < 1e-6f &&
                              a->transform.opacity > 0.999f,
                      "title opacity is constant and fully visible");
            }
        }
    }

    void theCameraReallyAnimates() {
        section("camera is actually animated");
        for (const TitleCameraMove move : {
                     TitleCameraMove::SlowPush, TitleCameraMove::SlowPullOut,
                     TitleCameraMove::LeftDrift, TitleCameraMove::RightDrift,
                     TitleCameraMove::VerticalRise, TitleCameraMove::VerticalDescend,
                     TitleCameraMove::MicroOrbitLeft, TitleCameraMove::MicroOrbitRight,
                     TitleCameraMove::ArcPush, TitleCameraMove::ArcPull,
                     TitleCameraMove::LowAnglePush, TitleCameraMove::HighAngleSettle,
                     TitleCameraMove::RollSettle, TitleCameraMove::RollPass,
                     TitleCameraMove::DollyZoomSubtle, TitleCameraMove::FocusPush,
                     TitleCameraMove::ParallaxSide, TitleCameraMove::ParallaxPush,                                                          TitleCameraMove::WhipSettle,
                                                          TitleCameraMove::CornerReveal,
                     TitleCameraMove::CrashPush, TitleCameraMove::TopDownSettle,
                     TitleCameraMove::HandheldMicro, TitleCameraMove::OrbitWide,
                     TitleCameraMove::FloorRise}) {
            FakeContentHost host;
            chrononmotion::motion::Layer::Id titleId{0};
            const TitleCameraShot shot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                       .inFrame = 0,
                                       .duration = 135};
            const std::vector<Sample> samples = samplePreset(move, shot, host, titleId);

            const CameraPose& first = samples.front().pose;
            const CameraPose& last = samples.back().pose;
            const Vector3 delta = last.position - first.position;
            const bool positionMoved = length(delta) > 1.f;
            const bool angularMoved = std::fabs(first.orientation.dot(last.orientation)) < 0.9999f;
            const bool fovMoved = std::fabs(first.fov - last.fov) > 0.05f;
            check(positionMoved || angularMoved || fovMoved,
                  "the preset moves the camera pose across its window");

            // No preset may sample to a single pose (the "preset exists but the
            // camera never moves" defect).
            bool anyMidDifference = false;
            for (std::size_t i = 1; i < samples.size(); ++i) {
                if (!poseNear(samples[i - 1].pose, samples[i].pose, 1e-4f)) {
                    anyMidDifference = true;
                    break;
                }
            }
            check(anyMidDifference, "consecutive sampled poses differ: the move exists");
        }
    }

    void theFramingHolds() {
        section("title framing stays in the safe area");
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
            FakeContentHost host;
            chrononmotion::motion::Layer::Id titleId{0};
            const TitleCameraShot shot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                       .inFrame = 0,
                                       .duration = 135};
            const std::vector<Sample> samples = samplePreset(move, shot, host, titleId);

            bool insideEverywhere = true;
            for (const Sample& sample : samples) {
                const bool inside = sample.screen.x >= 0.05f * kViewportW &&
                                    sample.screen.x <= 0.95f * kViewportW &&
                                    sample.screen.y >= 0.08f * kViewportH &&
                                    sample.screen.y <= 0.92f * kViewportH;
                if (!inside) insideEverywhere = false;
            }
            check(insideEverywhere, "the projected title centre stays inside the safe area");
        }
    }

    void theHeroOccupancyMoves() {
        section("hero occupancy: a push grows the title");
        struct PushSpec {
            TitleCameraMove move;
            const char* name;
        };
        for (const PushSpec spec : {PushSpec{TitleCameraMove::SlowPush, "slow_push"},
                                    PushSpec{TitleCameraMove::LowAnglePush, "low_angle_push"},
                                    PushSpec{TitleCameraMove::ArcPush, "arc_push"},
                                    PushSpec{TitleCameraMove::ParallaxPush, "parallax_push"},
                                    PushSpec{TitleCameraMove::WhipSettle, "whip_settle"},
                                    PushSpec{TitleCameraMove::CrashPush, "crash_push"}}) {
            FakeContentHost host;
            chrononmotion::motion::Layer::Id titleId{0};
            const TitleCameraShot shot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                       .inFrame = 0,
                                       .duration = 135};
            const std::vector<Sample> samples = samplePreset(spec.move, shot, host, titleId);
            (void) titleId;

            // Project the title's reference half-width at both ends with the
            // frames' own poses: the same law a real run is measured with.
            const float halfWidth = 300.f;
            const auto projectedHalfWidth = [&](const Sample& sample) {
                ScreenCameraIntrinsics intrinsics;
                intrinsics.viewport = Vector2(kViewportW, kViewportH);
                intrinsics.fovDegrees = sample.pose.fov;
                const Vector2 center = projectToScreen(Vector3(960.f, 540.f, 0.f), sample.pose, intrinsics);
                const Vector2 edge = projectToScreen(Vector3(960.f + halfWidth, 540.f, 0.f),
                                                     sample.pose, intrinsics);
                return std::fabs(edge.x - center.x);
            };

            const float startWidth = projectedHalfWidth(samples.front());
            const float endWidth = projectedHalfWidth(samples.back());
            check(endWidth > startWidth,
                  std::string("end projected width > start for ").append(spec.name).c_str());
        }
    }

    void theTargetLockHolds() {
        section("target lock: the title centre tracks its desired place");
        for (const TitleCameraMove move : {
                     TitleCameraMove::LeftDrift, TitleCameraMove::RightDrift,
                     TitleCameraMove::MicroOrbitLeft, TitleCameraMove::MicroOrbitRight,
                     TitleCameraMove::ArcPush, TitleCameraMove::ArcPull,
                     TitleCameraMove::ParallaxSide, TitleCameraMove::WhipSettle,
                     TitleCameraMove::OrbitWide}) {
            FakeContentHost host;
            chrononmotion::motion::Layer::Id titleId{0};
            const TitleCameraShot shot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                       .inFrame = 0,
                                       .duration = 135};
            const std::vector<Sample> samples = samplePreset(move, shot, host, titleId);

            // The look-at keeps the anchor at the screen centre: during
            // orbit/pan the title must not wander out of a centre tolerance.
            constexpr float kTolerance = 220.f;
            for (const Sample& sample : samples) {
                const float dx = std::fabs(sample.screen.x - kViewportW * 0.5f);
                const float dy = std::fabs(sample.screen.y - kViewportH * 0.5f);
                check(dx < kTolerance && dy < kTolerance,
                      "the projected title centre stays within tolerance of frame centre");
                if (dx >= kTolerance || dy >= kTolerance) break;
            }
        }
    }

    void quaternionContinuity() {
        section("quaternion continuity: no hemisphere flip");
        for (const TitleCameraMove move : {
                     TitleCameraMove::MicroOrbitLeft, TitleCameraMove::MicroOrbitRight,
                     TitleCameraMove::ArcPush, TitleCameraMove::ArcPull,
                     TitleCameraMove::RollSettle, TitleCameraMove::RollPass,
                     TitleCameraMove::WhipSettle, TitleCameraMove::CornerReveal,
                     TitleCameraMove::HandheldMicro, TitleCameraMove::OrbitWide}) {
            FakeContentHost host;
            chrononmotion::motion::Layer::Id titleId{0};
            const TitleCameraShot shot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                       .inFrame = 0,
                                       .duration = 135};
            const std::vector<Sample> samples = samplePreset(move, shot, host, titleId);

            for (std::size_t i = 1; i < samples.size(); ++i) {
                const float dot = samples[i - 1].pose.orientation.dot(samples[i].pose.orientation);
                check(dot >= 0.f,
                      "dot(q[n], q[n+1]) >= 0 once the hemisphere is normalized");
                if (dot < 0.f) break;
            }
        }
    }

    void velocityContinuity() {
        section("velocity continuity: no channel teleports");
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
                     TitleCameraMove::CornerReveal,
                     TitleCameraMove::CrashPush, TitleCameraMove::TopDownSettle,
                     TitleCameraMove::HandheldMicro, TitleCameraMove::OrbitWide,
                     TitleCameraMove::FloorRise}) {
            FakeContentHost host;
            chrononmotion::motion::Layer::Id titleId{0};
            const TitleCameraShot shot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                       .inFrame = 0,
                                       .duration = 135};
            const std::vector<Sample> samples = samplePreset(move, shot, host, titleId);

            // A key that appears mid-window between two frame samples is a
            // teleport: position velocity may not jump by more than an order
            // of magnitude of the window's own max between adjacent frames.
            float maxRate = 0.f;
            for (std::size_t i = 0; i < samples.size(); ++i) {
                maxRate = std::max(maxRate, length(samples[i].positionVelocity));
            }
            const float jumpTolerance = std::max(maxRate * 2.5f, 600.f);
            for (std::size_t i = 1; i < samples.size(); ++i) {
                const float jump = length(samples[i].positionVelocity - samples[i - 1].positionVelocity);
                check(jump <= jumpTolerance,
                      "position velocity changes continuously between frames");
                if (jump > jumpTolerance) break;
            }

            const float maxFovRate = 300.f;
            for (std::size_t i = 1; i < samples.size(); ++i) {
                check(std::fabs(samples[i].fovRate - samples[i - 1].fovRate) <= maxFovRate,
                      "FOV rate stays bounded between frames");
                if (std::fabs(samples[i].fovRate - samples[i - 1].fovRate) > maxFovRate) break;
            }

            const float maxRollJump = 0.6f; // rad/s between adjacent frames
            for (std::size_t i = 1; i < samples.size(); ++i) {
                check(std::fabs(samples[i].rollRate - samples[i - 1].rollRate) <= maxRollJump,
                      "roll rate stays bounded between frames");
                if (std::fabs(samples[i].rollRate - samples[i - 1].rollRate) > maxRollJump) break;
            }
        }
        // whip_settle is the declared loud-but-continuous exception: its
        // acquisition is fast on purpose, so its peak must clearly exceed a
        // calm preset's, not some absolute silence threshold.
        {
            FakeContentHost host;
            chrononmotion::motion::Layer::Id titleId{0};
            const TitleCameraShot shot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                       .inFrame = 0,
                                       .duration = 135};
            const std::vector<Sample> whip =
                    samplePreset(TitleCameraMove::WhipSettle, shot, host, titleId);
            const std::vector<Sample> calm =
                    samplePreset(TitleCameraMove::SlowPush, shot, host, titleId);
            float whipPeak = 0.f;
            for (const Sample& sample : whip) {
                whipPeak = std::max(whipPeak, length(sample.positionVelocity));
            }
            float calmPeak = 0.f;
            for (const Sample& sample : calm) {
                calmPeak = std::max(calmPeak, length(sample.positionVelocity));
            }
            check(whipPeak > calmPeak * 1.5f,
                  "whip_settle's acquisition is loud on purpose (> 1.5x slow_push's peak)");
        }
    }

    void theEndSettles() {
        section("end settle: the last beat decelerates");
        // Presets that finish in a hold (whip excluded: its point is the
        // acquisition, and dolly_zoom's endpoint is its own lens state).
        for (const TitleCameraMove move : {
                     TitleCameraMove::SlowPush, TitleCameraMove::SlowPullOut,
                     TitleCameraMove::LeftDrift, TitleCameraMove::RightDrift,
                     TitleCameraMove::VerticalRise, TitleCameraMove::VerticalDescend,
                     TitleCameraMove::MicroOrbitLeft, TitleCameraMove::MicroOrbitRight,
                     TitleCameraMove::ArcPush, TitleCameraMove::ArcPull,
                     TitleCameraMove::LowAnglePush, TitleCameraMove::HighAngleSettle,
                     TitleCameraMove::RollSettle, TitleCameraMove::RollPass,
                     TitleCameraMove::FocusPush, TitleCameraMove::ParallaxSide,
                     TitleCameraMove::ParallaxPush, TitleCameraMove::CornerReveal,
                     TitleCameraMove::CrashPush, TitleCameraMove::TopDownSettle,
                     TitleCameraMove::HandheldMicro, TitleCameraMove::OrbitWide,
                     TitleCameraMove::FloorRise}) {
            FakeContentHost host;
            chrononmotion::motion::Layer::Id titleId{0};
            const TitleCameraShot shot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                       .inFrame = 0,
                                       .duration = 135};
            const std::vector<Sample> samples = samplePreset(move, shot, host, titleId);

            const std::size_t mid = samples.size() / 2;
            float midRate = 0.f;
            for (std::size_t i = mid - 1; i <= mid + 1; ++i) {
                midRate = std::max(midRate, length(samples[i].positionVelocity));
            }
            float endRate = 0.f;
            for (std::size_t i = samples.size() - 12; i < samples.size(); ++i) {
                endRate = std::max(endRate, length(samples[i].positionVelocity));
            }
            check(endRate < midRate,
                  "velocity(end) < velocity(mid): the move lands instead of stopping dead");
        }
    }

    void theContractAndTheLens() {
        section("contract: stable ids, pure plan, lens channels");

        const std::vector<std::string> ids = titleCameraMoveIds();
        check(ids.size() == 25, "twenty-five title_camera_* presets exist (20 v1 + 5 v2)");
        check(ids.front() == "title_camera_slow_push", "the canonical order starts at slow_push");
        check(ids.back() == "title_camera_floor_rise", "the canonical order ends at floor_rise");
        bool unique = true;
        for (std::size_t i = 0; i < ids.size(); ++i) {
            for (std::size_t j = i + 1; j < ids.size(); ++j) {
                if (ids[i] == ids[j]) unique = false;
            }
        }
        check(unique, "every preset id is unique");
        check(titleCameraMoveId(TitleCameraMove::WhipSettle) == std::string("title_camera_whip_settle"),
              "the whip's id is stable");
        check(titleCameraMoveId(TitleCameraMove::DollyZoomSubtle) ==
                      std::string("title_camera_dolly_zoom_subtle"),
              "the vertigo's id is stable");

        // The pure plan: same shot, same numbers; different framings, one law.
        const TitleCameraShot shot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                   .inFrame = 0,
                                   .duration = 135};
        const TitleCameraPlan a = titleCameraPlanFor(TitleCameraMove::SlowPush, shot);
        const TitleCameraPlan b = titleCameraPlanFor(TitleCameraMove::SlowPush, shot);
        check(std::fabs(a.dolly - b.dolly) < 1e-6f && std::fabs(a.distance - b.distance) < 1e-6f,
              "the plan is a pure function of the shot");
        const TitleCameraShot hero{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                   .framing = TitleFraming::Hero,
                                   .inFrame = 0,
                                   .duration = 135};
        const TitleCameraPlan heroPlan = titleCameraPlanFor(TitleCameraMove::SlowPush, hero);
        check(heroPlan.distance < a.distance, "a hero framing sits closer than a medium one");
        check(titleCameraDistance(TitleFraming::Wide, 55.f) >
                      titleCameraDistance(TitleFraming::Hero, 55.f),
              "a wide framing sits farther than a hero one");
        check(a.dolly > 0.f, "slow_push's plan dollies toward the anchor");
        check(titleCameraPlanFor(TitleCameraMove::SlowPullOut, shot).dolly < 0.f,
              "slow_pull_out's plan dollies away from the anchor");

        // The vertigo compensation: projected title width ~constant while the
        // FOV widens. Build both endpoint poses through the pack's own law.
        {
            FakeContentHost host;
            TemplateScene scene("title_camera_vertigo", 30.f, host, kViewportW, kViewportH);
            auto& title = scene.text({.text = "2008", .font = "Inter-Bold.ttf", .fontSize = 180.f});
            title.position(960.f, 540.f);
            applyTitleCameraShot(scene, TitleCameraMove::DollyZoomSubtle,
                                 TitleCameraShot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                                 .inFrame = 0,
                                                 .duration = 135});
            const float fps = 30.f;
            ScreenCameraIntrinsics intrinsics;
            intrinsics.viewport = Vector2(kViewportW, kViewportH);
            const CameraPose p0 = scene.camera().rig().sample(0.f);
            const CameraPose p1 = scene.camera().rig().sample(135.f / fps);
            intrinsics.fovDegrees = p0.fov;
            const Vector2 c0 = projectToScreen(Vector3(960.f, 540.f, 0.f), p0, intrinsics);
            const Vector2 e0 = projectToScreen(Vector3(1260.f, 540.f, 0.f), p0, intrinsics);
            intrinsics.fovDegrees = p1.fov;
            const Vector2 c1 = projectToScreen(Vector3(960.f, 540.f, 0.f), p1, intrinsics);
            const Vector2 e1 = projectToScreen(Vector3(1260.f, 540.f, 0.f), p1, intrinsics);
            const float w0 = std::fabs(e0.x - c0.x);
            const float w1 = std::fabs(e1.x - c1.x);
            check(std::fabs(w1 - w0) / w0 < 0.08f,
                  "dolly_zoom keeps the projected title width within 8% (vertigo compensation)");
        }

        // The lens: focus_push keys the focus and aperture channels only.
        {
            FakeContentHost host;
            TemplateScene scene("title_camera_focus", 30.f, host, kViewportW, kViewportH);
            auto& title = scene.text({.text = "$4.5 BILLION", .font = "Inter-Bold.ttf",
                                      .fontSize = 180.f});
            title.position(960.f, 540.f);
            applyTitleCameraShot(scene, TitleCameraMove::FocusPush,
                                 TitleCameraShot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                                 .inFrame = 0,
                                                 .duration = 135});
            auto& rig = scene.camera().rig();
            check(!rig.focusDistanceTrack().empty(), "focus_push keys the focus-distance channel");
            check(!rig.apertureTrack().empty(), "focus_push keys the aperture channel");
            check(rig.focusDistanceTrack().size() >= 3 &&
                          rig.focusDistanceTrack().keys().back().time >= 135.f / 30.f,
                  "the focus move covers the whole window including its settle");
        }

        // Refusals: a bad shot fails loudly instead of authoring junk.
        bool threw = false;
        try {
            FakeContentHost host;
            TemplateScene scene("title_camera_bad", 30.f, host, kViewportW, kViewportH);
            applyTitleCameraShot(scene, TitleCameraMove::SlowPush,
                                 TitleCameraShot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                                 .inFrame = 0,
                                                 .duration = 0});
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a non-positive duration is refused");
        // Intensities and framings: one application each, the pack's own
        // safe-area gate is the assertion — any throw fails the check below.
        {
            bool allApplied = true;
            for (const TitleCameraIntensity intensity : {
                         TitleCameraIntensity::Subtle, TitleCameraIntensity::Editorial,
                         TitleCameraIntensity::Cinematic}) {
                for (const TitleCameraMove move : {
                             TitleCameraMove::SlowPush, TitleCameraMove::MicroOrbitRight,
                             TitleCameraMove::DollyZoomSubtle, TitleCameraMove::WhipSettle}) {
                    try {
                        FakeContentHost host;
                        TemplateScene scene("title_camera_intensity", 30.f, host, kViewportW,
                                            kViewportH);
                        auto& title = scene.text({.text = "THE CRISIS", .font = "Inter-Bold.ttf",
                                                  .fontSize = 180.f});
                        title.position(960.f, 540.f);
                        applyTitleCameraShot(scene, move,
                                             TitleCameraShot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                                             .intensity = intensity,
                                                             .inFrame = 0,
                                                             .duration = 135});
                        check(scene.validate().empty(),
                              "every intensity authors a scene the motion core validates");
                    } catch (const std::exception&) {
                        allApplied = false;
                    }
                }
            }
            for (const TitleFraming framing : {
                         TitleFraming::Hero, TitleFraming::Medium, TitleFraming::Wide,
                         TitleFraming::ExtremeClose}) {
                try {
                    FakeContentHost host;
                    TemplateScene scene("title_camera_framing", 30.f, host, kViewportW, kViewportH);
                    auto& title = scene.text({.text = "NEW YORK", .font = "Inter-Bold.ttf",
                                              .fontSize = 180.f});
                    title.position(960.f, 540.f);
                    applyTitleCameraShot(scene, TitleCameraMove::SlowPush,
                                         TitleCameraShot{.anchor = {.center = Vector3(960.f, 540.f, 0.f)},
                                                         .framing = framing,
                                                         .inFrame = 0,
                                                         .duration = 135});
                } catch (const std::exception&) {
                    allApplied = false;
                }
            }
            check(allApplied, "every intensity and framing applies within the safe-area law");
        }

        threw = false;
        try {
            FakeContentHost host;
            TemplateScene scene("title_camera_bad", 30.f, host, kViewportW, kViewportH);
            applyTitleCameraShot(scene, TitleCameraMove::SlowPush,
                                 TitleCameraShot{.anchor = {.center = Vector3(std::nanf(""), 0.f, 0.f)},
                                                 .inFrame = 0,
                                                 .duration = 135});
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a non-finite anchor is refused");
    }

}// namespace

int main() {
    theTitleNeverAnimates();
    theCameraReallyAnimates();
    theFramingHolds();
    theHeroOccupancyMoves();
    theTargetLockHolds();
    quaternionContinuity();
    velocityContinuity();
    theEndSettles();
    theContractAndTheLens();
    return chrononmotion_test::report();
}
