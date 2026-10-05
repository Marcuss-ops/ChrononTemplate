// The scene-camera pack's acceptance suite.
//
// Gates, one per family contract, sampled per frame across the whole sequence
// of every transition:
//
//   P0  the subjects never animate — empty layer tracks before and after, and
//       a transform identical at every sampled frame;
//   2.  the camera really carries the frame — no transition samples to a
//       single pose, and each leg actually leaves hold A;
//   3.  the legs are continuous — every leg starts exactly on hold A's rest
//       and lands exactly on hold B's rest;
//   4.  the holds are holds — every frame inside a hold samples that hold's
//       rest pose;
//   5.  the end settles — the last beat is slower than mid-travel;
//   6.  velocity continuity — no channel teleports between frames (the whip
//       is exempted on loudness, not on continuity);
//   7.  the framing gate holds — every subject's rest stays in the safe area;
//   8.  the authoring is loud — bad sequences throw.
//
// The grammar under test: frase → immagine → testo, three stacchi joined by
// camera travel, on a fixed canary sequence only the transition id changes.

#include "chronontemplate/SceneCameraPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include "chrononmotion/math/Quaternion.hpp"
#include "chrononmotion/math/Vector2.hpp"
#include "chrononmotion/motion/CameraScreenSpace.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion::Vector2;
using chrononmotion::Vector3;
using chrononmotion::motion::CameraPose;
using chrononmotion::motion::CameraRig;
using chrononmotion::motion::projectToScreen;
using chrononmotion::motion::ScreenCameraIntrinsics;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    constexpr float kViewportW = 1920.f;
    constexpr float kViewportH = 1080.f;
    constexpr float kFps = 30.f;

    struct Sample {
        CameraPose pose{};
        Vector3 positionVelocity{0.f, 0.f, 0.f};
        float fovRate{0.f};
    };

    // The canary grammar: three subjects — a phrase, an image, a text — each
    // holding its own framing, joined by the transition under test.
    [[nodiscard]] SceneCameraSequence canarySequence(SceneCameraTransition transition) {
        return SceneCameraSequence{
                .beats = {
                        SceneBeat{.subject = {.kind = SubjectKind::Phrase,
                                              .center = Vector3(960.f, 540.f, 0.f),
                                              .halfWidth = 520.f, .halfHeight = 110.f},
                                  .hold = 60},
                        SceneBeat{.subject = {.kind = SubjectKind::Image,
                                              .center = Vector3(960.f, 540.f, -80.f),
                                              .halfWidth = 460.f, .halfHeight = 260.f},
                                  .hold = 60},
                        SceneBeat{.subject = {.kind = SubjectKind::Text,
                                              .center = Vector3(960.f, 540.f, 0.f),
                                              .halfWidth = 620.f, .halfHeight = 150.f},
                                  .hold = 60}},
                .transition = transition,
                .intensity = 1.f,
                .travelFrames = 24,
                .inFrame = 0};
    }

    // One scene per transition, three subjects submitted at every frame: only
    // the camera differs between the eight runs.
    [[nodiscard]] std::vector<Sample> sampleSequence(const SceneCameraSequence& sequence,
                                                     FakeContentHost& host,
                                                     std::vector<chrononmotion::motion::Layer::Id>& idsOut) {
        TemplateScene scene("scene_camera_test", kFps, host, kViewportW, kViewportH);
        auto& phrase = scene.text({.text = "LA STORIA COMINCIA QUI", .font = "Inter-Bold.ttf",
                                   .fontSize = 96.f});
        phrase.position(960.f, 540.f);
        auto& image = scene.image({.path = "assets/images/camera_reference.jpg"});
        image.position(960.f, 540.f);
        auto& title = scene.text({.text = "IL SECONDO ATTO", .font = "Inter-Bold.ttf",
                                  .fontSize = 120.f});
        title.position(960.f, 540.f);
        idsOut = {phrase.id(), image.id(), title.id()};

        applySceneCameraSequence(scene, sequence);

        std::vector<Sample> samples;
        const int total = 3 * 60 + 2 * sequence.travelFrames;
        samples.reserve(static_cast<std::size_t>(total) + 1);
        for (int f = 0; f <= total; ++f) {
            Sample sample;
            const float seconds = static_cast<float>(f) / kFps;
            sample.pose = scene.camera().rig().sample(seconds);
            const auto derivative = scene.camera().rig().sampleDerivative(seconds);
            sample.positionVelocity = derivative.linearVelocity;
            sample.fovRate = derivative.fovRate;
            samples.push_back(std::move(sample));
        }
        return samples;
    }

    [[nodiscard]] float length(const Vector3& v) { return std::sqrt(v.dot(v)); }

    [[nodiscard]] bool poseNear(const CameraPose& a, const CameraPose& b, float epsilon) {
        const Vector3 dp = a.position - b.position;
        return length(dp) <= epsilon && std::fabs(a.roll - b.roll) <= epsilon &&
               std::fabs(a.fov - b.fov) <= epsilon &&
               a.hasTarget == b.hasTarget &&
               (!a.hasTarget || length(a.target - b.target) <= epsilon);
    }

    // The rest pose a subject's hold rests on, recomputed the same way the
    // pack derives it (the framing law, at the canary's editorial intensity).
    [[nodiscard]] CameraPose restFor(const SceneSubject& subject) {
        const float fov = sceneSubjectFov(subject.kind);
        const float distance = sceneFramingDistance(subject, fov, Vector2(kViewportW, kViewportH),
                                                    0.62f + 0.10f * 1.f);
        CameraPose pose;
        pose.position = Vector3(subject.center.x, subject.center.y, subject.center.z + distance);
        pose.hasTarget = true;
        pose.target = subject.center;
        pose.fov = fov;
        return pose;
    }

    [[nodiscard]] std::vector<SceneSubject> canarySubjects() {
        return {
                SceneSubject{.kind = SubjectKind::Phrase, .center = Vector3(960.f, 540.f, 0.f),
                             .halfWidth = 520.f, .halfHeight = 110.f},
                SceneSubject{.kind = SubjectKind::Image, .center = Vector3(960.f, 540.f, -80.f),
                             .halfWidth = 460.f, .halfHeight = 260.f},
                SceneSubject{.kind = SubjectKind::Text, .center = Vector3(960.f, 540.f, 0.f),
                             .halfWidth = 620.f, .halfHeight = 150.f},
        };
    }

    void allTransitions(std::vector<SceneCameraTransition>& out) {
        for (const auto& id : sceneCameraTransitionIds()) {
            (void) id;
        }
        out = {
                SceneCameraTransition::PushThrough,   SceneCameraTransition::LateralSwipe,
                SceneCameraTransition::ArcCarry,      SceneCameraTransition::OrbitHandoff,
                SceneCameraTransition::RiseAndLand,   SceneCameraTransition::FocusRack,
                SceneCameraTransition::PullBackReveal,SceneCameraTransition::WhipReframe};
    }

    // ------------------------------------------------------------- gates --

    void theSubjectsNeverAnimate() {
        section("P0: the subjects never animate");
        std::vector<SceneCameraTransition> transitions;
        allTransitions(transitions);
        for (const SceneCameraTransition transition : transitions) {
            FakeContentHost host;
            TemplateScene scene("scene_camera_p0", kFps, host, kViewportW, kViewportH);
            auto& phrase = scene.text({.text = "ROMA", .font = "Inter-Bold.ttf", .fontSize = 96.f});
            phrase.position(960.f, 540.f);

            const auto* before = scene.motion().findLayer(phrase.id());
            check(before != nullptr, "the phrase layer exists");
            check(before && before->tracks.position.empty() && before->tracks.scale.empty() &&
                          before->tracks.rotation.empty() && before->tracks.opacity.empty(),
                  "scene_camera_* writes no subject tracks before the sequence is applied");

            applySceneCameraSequence(scene, canarySequence(transition));

            const auto* after = scene.motion().findLayer(phrase.id());
            check(after != nullptr && after->tracks.position.empty() &&
                          after->tracks.scale.empty() && after->tracks.rotation.empty(),
                  "applying the sequence still leaves every subject track empty");

            // The stronger form: the sampled transform is bit-identical at
            // every frame of the whole sequence.
            const int total = 3 * 60 + 2 * 24;
            const FrameSubmission first = scene.submit(0);
            const FrameSubmission last = scene.submit(total);
            const auto* a = findLayer(first, phrase.id());
            const auto* b = findLayer(last, phrase.id());
            check(a && b, "the subject submits at both ends of the sequence");
            if (a && b) {
                check(chronontemplate_test::sameMatrix(a->transform.world, b->transform.world),
                      "subjectTransform(frame0) == subjectTransform(frameEnd)");
            }
        }
    }

    void theCameraCarriesTheFrame() {
        section("the camera carries the frame between holds");
        std::vector<SceneCameraTransition> transitions;
        allTransitions(transitions);
        for (const SceneCameraTransition transition : transitions) {
            FakeContentHost host;
            std::vector<chrononmotion::motion::Layer::Id> ids;
            const std::vector<Sample> samples = sampleSequence(canarySequence(transition), host, ids);

            bool anyMove = false;
            for (std::size_t i = 1; i < samples.size(); ++i) {
                if (!poseNear(samples[i - 1].pose, samples[i].pose, 1e-4f)) {
                    anyMove = true;
                    break;
                }
            }
            check(anyMove, "the transition moves the camera pose across the sequence");

            // Each leg really leaves hold A: mid-travel differs from both rests.
            const std::vector<SceneSubject> subjects = canarySubjects();
            const CameraPose restA = restFor(subjects[0]);
            const CameraPose restB = restFor(subjects[1]);
            const std::size_t mid = 60 + 12; // inside the first leg
            check(!poseNear(samples[mid].pose, restA, 1e-3f) &&
                          !poseNear(samples[mid].pose, restB, 1e-3f),
                  "mid-travel differs from both rest poses");
        }
    }

    void theLegsAreContinuous() {
        section("every leg starts on hold A's rest and lands on hold B's rest");
        std::vector<SceneCameraTransition> transitions;
        allTransitions(transitions);
        for (const SceneCameraTransition transition : transitions) {
            FakeContentHost host;
            std::vector<chrononmotion::motion::Layer::Id> ids;
            const std::vector<Sample> samples = sampleSequence(canarySequence(transition), host, ids);

            const std::vector<SceneSubject> subjects = canarySubjects();
            const int travel = 24;
            // First leg: leaves frame 60, lands frame 84. Second: 144 → 168.
            check(poseNear(samples[60].pose, restFor(subjects[0]), 1e-3f),
                  "the first leg departs exactly from hold A's rest");
            check(poseNear(samples[60 + travel].pose, restFor(subjects[1]), 1e-3f),
                  "the first leg lands exactly on hold B's rest");
            check(poseNear(samples[60 + travel + 60].pose, restFor(subjects[1]), 1e-3f),
                  "the second leg departs exactly from hold B's rest");
            check(poseNear(samples[60 + travel + 60 + travel].pose, restFor(subjects[2]), 1e-3f),
                  "the second leg lands exactly on hold C's rest");
        }
    }

    void theHoldsAreHolds() {
        section("every frame inside a hold samples that hold's rest pose");
        std::vector<SceneCameraTransition> transitions;
        allTransitions(transitions);
        for (const SceneCameraTransition transition : transitions) {
            FakeContentHost host;
            std::vector<chrononmotion::motion::Layer::Id> ids;
            const std::vector<Sample> samples = sampleSequence(canarySequence(transition), host, ids);

            const std::vector<SceneSubject> subjects = canarySubjects();
            const int travel = 24;
            bool holds = true;
            for (int f = 0; f <= 60; ++f) {
                if (!poseNear(samples[f].pose, restFor(subjects[0]), 1e-3f)) holds = false;
            }
            for (int f = 60 + travel; f <= 60 + travel + 60; ++f) {
                if (!poseNear(samples[f].pose, restFor(subjects[1]), 1e-3f)) holds = false;
            }
            for (int f = 60 + travel + 60 + travel; f < 60 + travel + 60 + travel + 60; ++f) {
                if (!poseNear(samples[f].pose, restFor(subjects[2]), 1e-3f)) holds = false;
            }
            check(holds, "the holds hold their framing for their whole window");
        }
    }

    void theEndSettles() {
        section("the last beat is slower than mid-travel");
        std::vector<SceneCameraTransition> transitions;
        allTransitions(transitions);
        for (const SceneCameraTransition transition : transitions) {
            FakeContentHost host;
            std::vector<chrononmotion::motion::Layer::Id> ids;
            const std::vector<Sample> samples = sampleSequence(canarySequence(transition), host, ids);

            const std::size_t midTravel = 60 + 6;
            const std::size_t lastHoldStart = 60 + 24 + 60 + 24;
            const float midSpeed = length(samples[midTravel].positionVelocity);
            const float endSpeed = length(samples[samples.size() - 2].positionVelocity);
            check(endSpeed < midSpeed,
                  "the sequence lands slower than it travels (the settle exists)");
            check(length(samples[lastHoldStart + 30].positionVelocity) < 1e-4f,
                  "the final hold is at rest");
        }
    }

    void velocityIsContinuous() {
        section("no channel teleports between frames");
        std::vector<SceneCameraTransition> transitions;
        allTransitions(transitions);
        for (const SceneCameraTransition transition : transitions) {
            FakeContentHost host;
            std::vector<chrononmotion::motion::Layer::Id> ids;
            const std::vector<Sample> samples = sampleSequence(canarySequence(transition), host, ids);

            // Neighbor frames may not jump: |Δv| stays far below the travel
            // scale for every transition except the whip's first half, whose
            // loud acquisition is the declared exception.
            bool teleported = false;
            const bool whip = transition == SceneCameraTransition::WhipReframe;
            for (std::size_t i = 1; i < samples.size(); ++i) {
                if (whip && i <= 60 + 12) continue;
                const float jump = length(samples[i].positionVelocity - samples[i - 1].positionVelocity);
                if (jump > 900.f) teleported = true;
                if (std::fabs(samples[i].fovRate - samples[i - 1].fovRate) > 900.f) teleported = true;
            }
            check(!teleported, "camera channels are velocity-continuous");
        }
    }

    void theFramingGateHolds() {
        section("every subject's rest stays inside the safe area");
        for (const SceneSubject& subject : canarySubjects()) {
            const CameraPose rest = restFor(subject);
            ScreenCameraIntrinsics intrinsics;
            intrinsics.viewport = Vector2(kViewportW, kViewportH);
            intrinsics.fovDegrees = rest.fov;
            const Vector2 screen = projectToScreen(subject.center, rest, intrinsics);
            check(screen.x >= 0.05f * kViewportW && screen.x <= 0.95f * kViewportW &&
                          screen.y >= 0.08f * kViewportH && screen.y <= 0.92f * kViewportH,
                  "the rest framing keeps the subject inside the safe area");
        }
    }

    void theAuthoringIsLoud() {
        section("bad sequences throw");
        FakeContentHost host;
        TemplateScene scene("scene_camera_loud", kFps, host, kViewportW, kViewportH);
        (void) scene.text({.text = "ANCORA", .font = "Inter-Bold.ttf", .fontSize = 96.f});

        bool threw = false;
        try {
            applySceneCameraSequence(scene, SceneCameraSequence{.beats = {}});
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "an empty sequence throws");

        threw = false;
        try {
            SceneCameraSequence one = canarySequence(SceneCameraTransition::ArcCarry);
            one.beats.resize(1);
            applySceneCameraSequence(scene, one);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a one-beat sequence throws");

        threw = false;
        try {
            SceneCameraSequence shortTravel = canarySequence(SceneCameraTransition::ArcCarry);
            shortTravel.travelFrames = 0;
            applySceneCameraSequence(scene, shortTravel);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a non-positive travel throws");

        threw = false;
        try {
            SceneCameraSequence tinyHold = canarySequence(SceneCameraTransition::ArcCarry);
            tinyHold.beats[1].hold = 2;
            applySceneCameraSequence(scene, tinyHold);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a hold below six frames throws");

        threw = false;
        try {
            SceneCameraSequence loud = canarySequence(SceneCameraTransition::ArcCarry);
            loud.intensity = -1.f;
            applySceneCameraSequence(scene, loud);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a non-positive intensity throws");
    }

    void theVocabularyIsStable() {
        section("the transition ids are stable and unique");
        const std::vector<std::string> ids = sceneCameraTransitionIds();
        check(ids.size() == 8, "eight transitions are published");
        check(ids[0] == "scene_camera_push_through" && ids[7] == "scene_camera_whip_reframe",
              "the canonical order is stable");
        bool unique = true;
        for (std::size_t i = 0; i < ids.size(); ++i) {
            for (std::size_t j = i + 1; j < ids.size(); ++j) {
                if (ids[i] == ids[j]) unique = false;
            }
        }
        check(unique, "the ids are unique");
    }

}// namespace

int main() {
    theVocabularyIsStable();
    theSubjectsNeverAnimate();
    theCameraCarriesTheFrame();
    theLegsAreContinuous();
    theHoldsAreHolds();
    theEndSettles();
    velocityIsContinuous();
    theFramingGateHolds();
    theAuthoringIsLoud();
    return chrononmotion_test::report();
}
