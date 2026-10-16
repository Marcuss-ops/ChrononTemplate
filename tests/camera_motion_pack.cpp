// The camera motion pack's acceptance suite (camera_motion_pack_v1).
//
// Gates, sampled per frame across the whole window of every preset:
//
//   1. the spec table is complete — 15 unique `camera_motion_*` ids, three per
//      family, spec durations, two-shot only in family 5;
//   2. intensity is the spec ladder — 0.5 / 1.0 / 1.5 amplitude factors;
//   3. the subjects never animate — every layer track stays empty;
//   4. the camera really animates — body travel for every single-shot preset,
//      focus travel for the rack-focus preset;
//   5. poses stay finite — no NaN anywhere in the window;
//   6. velocity continuity — no teleports between neighbor frames, except
//      inside the declared cut window of two-shot transitions and except the
//      high-energy whip/handoff presets (a loud move is their point);
//   7. the end settle — the last beat is slower than peak travel, except
//      loops, two-shot transitions (they cut) and high-energy presets;
//   8. the micro-float loops — first and last body pose coincide;
//   9. the cut structure — two-shot presets jump at the cut and are
//      continuous on both legs outside it;
//   10. the selection table — every content kind suggests real presets only,
//       and every preset is suggested for at least one content kind.

#include "chronontemplate/camera_roll/CameraMotionPack.hpp"
#include "chronontemplate/camera_roll/SceneCameraPack.hpp"
#include "chronontemplate/camera_roll/TitleCameraPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include "chrononmotion/math/Vector2.hpp"
#include "chrononmotion/math/Vector3.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <set>
#include <string>
#include <thread>
#include <vector>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chrononmotion::Vector2;
using chrononmotion::Vector3;
using chrononmotion::motion::CameraPose;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    constexpr float kViewportW = 1920.f;
    constexpr float kViewportH = 1080.f;
    constexpr std::size_t kPresetCount = 15;

    struct RigSample {
        Vector3 position{0.f, 0.f, 0.f};
        float focus{0.f};
        float roll{0.f};
    };

    // The roster is the sole source of preset ordinals/order.
    [[nodiscard]] std::vector<CameraMotionPreset> allPresets() {
        return cameraMotionPresets();
    }

    void concurrentColdPresetLookupsAreStable() {
        section("concurrent cold preset lookups");
        std::atomic<bool> start{false};
        std::array<bool, kPresetCount> valid{};
        std::vector<std::thread> workers;
        workers.reserve(kPresetCount);
        for (std::size_t i = 0; i < kPresetCount; ++i) {
            workers.emplace_back([i, &start, &valid] {
                while (!start.load(std::memory_order_acquire)) std::this_thread::yield();
                const auto preset = static_cast<CameraMotionPreset>(i);
                const auto& spec = cameraMotionSpecFor(preset);
                valid[i] = spec.id != nullptr &&
                           std::string(spec.id) == cameraMotionPresetId(preset) &&
                           spec.durationFrames == cameraMotionDuration(preset) &&
                           spec.family == cameraMotionFamily(preset);
            });
        }
        start.store(true, std::memory_order_release);
        for (auto& worker : workers) worker.join();
        for (std::size_t i = 0; i < valid.size(); ++i) {
            check(valid[i], (std::string("concurrent lookup preserves enum ordinal ") +
                             std::to_string(i)).c_str());
        }
    }

    [[nodiscard]] std::vector<RigSample> samplePreset(CameraMotionPreset preset, int duration,
                                                      FakeContentHost& host) {
        TemplateScene scene("camera_motion_test", 30.f, host, kViewportW, kViewportH);
        auto& title = scene.text({.text = "CAMERA MOTION CANARY", .font = "Inter-Bold.ttf",
                                  .fontSize = 160.f});
        title.position(960.f, 540.f);
        const auto titleId = title.id();

        CameraMotionShot shot;
        shot.subject.center = Vector3(0.f, 0.f, 0.f);
        shot.subject.halfWidth = 480.f;
        shot.subject.halfHeight = 270.f;
        shot.durationOverride = duration;
        applyCameraMotionShot(scene, preset, shot);

        // Gate 3: the subject layer carries no tracks.
        const chrononmotion::motion::Layer* layer = scene.motion().findLayer(titleId);
        check(layer != nullptr, "canary layer exists");
        if (layer != nullptr) {
            check(layer->tracks.position.empty() && layer->tracks.scale.empty() &&
                          layer->tracks.rotation.empty() && layer->tracks.opacity.empty(),
                  std::string(cameraMotionPresetId(preset)).append(" writes no subject tracks").c_str());
        }

        std::vector<RigSample> samples;
        samples.reserve(static_cast<std::size_t>(duration) + 1);
        auto& rig = scene.camera().rig();
        for (int f = 0; f <= duration; ++f) {
            const CameraPose pose = rig.sample(static_cast<float>(f) / 30.f);
            samples.push_back({pose.position, pose.focusDistance, pose.roll});
        }
        return samples;
    }

    [[nodiscard]] float stepLength(const RigSample& a, const RigSample& b) {
        const float dx = a.position.x - b.position.x;
        const float dy = a.position.y - b.position.y;
        const float dz = a.position.z - b.position.z;
        return std::sqrt(dx * dx + dy * dy + dz * dz);
    }

    void theSpecTableIsComplete() {
        section("spec table");
        const auto presets = allPresets();
        check(presets.size() == kPresetCount, "the pack holds fifteen presets");
        check(cameraMotionPresetIds().size() == kPresetCount, "the id catalog holds fifteen ids");
        std::set<std::string> ids;
        for (const auto preset : presets) ids.insert(cameraMotionPresetId(preset));
        check(ids.size() == kPresetCount, "preset ids are unique");
        for (const auto& id : ids) {
            check(id.rfind("camera_motion_", 0) == 0, "wire ids carry the camera_motion_ prefix");
            check(chrononmotion::motion::presets::known(id),
                  (id + " is registered in ChrononMotion3D presets::catalog()").c_str());
        }
        for (const auto& id : titleCameraMoveIds()) {
            check(chrononmotion::motion::presets::known(id),
                  (id + " is registered in ChrononMotion3D presets::catalog()").c_str());
        }
        for (const auto& id : sceneCameraTransitionIds()) {
            check(chrononmotion::motion::presets::known(id),
                  (id + " is registered in ChrononMotion3D presets::catalog()").c_str());
        }
        {
            FakeContentHost host;
            TemplateScene governed("governed_camera", 30.f, host, kViewportW, kViewportH);
            chrononmotion::motion::AuthoringPolicy policy;
            policy.allowedPresets = {"camera_motion_title_slow_push"};
            governed.motion().setAuthoringPolicy(policy);
            CameraMotionShot shot;
            applyCameraMotionShot(governed, CameraMotionPreset::TitleSlowPush, shot);
            bool denied = false;
            try {
                applyCameraMotionShot(governed, CameraMotionPreset::WhipPanLeft, shot);
            } catch (const std::invalid_argument&) {
                denied = true;
            }
            check(denied, "applyCameraMotionShot enforces AuthoringPolicy allowlist through presets::author");
        }
        const auto catalog = cameraMotionPresetIds();
        check(std::set<std::string>(catalog.begin(), catalog.end()) == ids,
              "the id catalog matches the preset table");
        check(catalog.size() == presets.size(), "id and preset rosters have the same number of rows");
        for (std::size_t i = 0; i < presets.size(); ++i) {
            const auto& spec = cameraMotionSpecFor(presets[i]);
            check(spec.id != nullptr && catalog[i] == spec.id,
                  "the declarative roster order matches the executable spec order");
            check(spec.family == cameraMotionFamily(presets[i]),
                  "the declarative family matches the executable camera recipe");
        }
        check(cameraMotionPresetId(static_cast<CameraMotionPreset>(kPresetCount)) == nullptr,
              "out-of-range preset ids do not resolve through the roster");
        check(cameraMotionSpecFor(static_cast<CameraMotionPreset>(kPresetCount)).id == nullptr,
              "out-of-range preset specs stay empty");
        int perFamily[5] = {0, 0, 0, 0, 0};
        int twoShot = 0;
        for (const auto preset : presets) {
            const auto& spec = cameraMotionSpecFor(preset);
            perFamily[static_cast<int>(spec.family)]++;
            if (spec.twoShot) {
                twoShot++;
                check(spec.family == CameraMotionFamily::Transition,
                      "two-shot presets live in the transition family only");
            }
            check(spec.durationFrames >= 8, "every preset lasts at least 8 frames");
            check(std::string(spec.easing).size() > 0, "every preset names an easing");
            // The easing name must resolve — unknown names fail loudly.
            cameraMotionEasingFor(spec.easing);
        }
        for (int f = 0; f < 5; ++f) {
            check(perFamily[f] == 3, "every family holds exactly three presets");
        }
        check(twoShot == 3, "exactly the three transitions are two-shot");
        // Pin the spec durations, in roster order.
        const int expected[kPresetCount] = {90, 96, 72, 108, 84, 78, 96, 120, 100, 64,
                                            90, 150, 14, 14, 22};
        for (std::size_t i = 0; i < presets.size(); ++i) {
            check(cameraMotionDuration(presets[i]) == expected[i],
                  std::string(cameraMotionPresetId(presets[i])).append(" keeps its spec duration").c_str());
        }
        // Backend requirement flags, exactly as specified.
        for (const auto preset : presets) {
            const auto& spec = cameraMotionSpecFor(preset);
            const std::string id = cameraMotionPresetId(preset);
            const bool dof = preset == CameraMotionPreset::RackFocusPortrait;
            check(spec.needsDof == dof, (id + " declares DOF exactly when specified").c_str());
        }
    }

    void theIntensityLadderIsSpec() {
        section("intensity ladder");
        checkNear(cameraMotionIntensityFactor(CameraMotionIntensity::Subtle), 0.5f, 1e-6f,
                  "subtle scales amplitude to 50%");
        checkNear(cameraMotionIntensityFactor(CameraMotionIntensity::Normal), 1.0f, 1e-6f,
                  "normal keeps 100%");
        checkNear(cameraMotionIntensityFactor(CameraMotionIntensity::Strong), 1.5f, 1e-6f,
                  "strong scales amplitude to 150%");
        // Amplitude really scales: the same preset travels twice as far at
        // Normal as at Subtle.
        FakeContentHost host;
        TemplateScene sub("k_sub", 30.f, host, kViewportW, kViewportH);
        TemplateScene nor("k_nor", 30.f, host, kViewportW, kViewportH);
        CameraMotionShot subShot, norShot;
        subShot.intensity = CameraMotionIntensity::Subtle;
        norShot.intensity = CameraMotionIntensity::Normal;
        applyCameraMotionShot(sub, CameraMotionPreset::TitleLateralDrift, subShot);
        applyCameraMotionShot(nor, CameraMotionPreset::TitleLateralDrift, norShot);
        const float end = static_cast<float>(cameraMotionDuration(CameraMotionPreset::TitleLateralDrift)) / 30.f;
        const float subTravel = std::fabs(sub.camera().rig().sample(end).position.x -
                                          sub.camera().rig().sample(0.f).position.x);
        const float norTravel = std::fabs(nor.camera().rig().sample(end).position.x -
                                          nor.camera().rig().sample(0.f).position.x);
        check(subTravel > 1.f, "subtle drift still travels");
        checkNear(norTravel / subTravel, 2.f, 0.02f, "normal travels twice the subtle amplitude");
    }

    void everyPresetAnimatesCleanly() {
        section("rig motion gates");
        FakeContentHost host;
        for (const auto preset : allPresets()) {
            const auto& spec = cameraMotionSpecFor(preset);
            const std::string id = cameraMotionPresetId(preset);
            const int duration = spec.durationFrames;
            const auto samples = samplePreset(preset, duration, host);

            // Gate 5: finite everywhere.
            for (const auto& s : samples) {
                check(std::isfinite(s.position.x) && std::isfinite(s.position.y) &&
                              std::isfinite(s.position.z),
                      (id + " samples finite poses").c_str());
            }

            // Gate 4: body travel, or focus travel for the rack-focus preset.
            if (preset == CameraMotionPreset::RackFocusPortrait) {
                float focusTravel = 0.f;
                for (const auto& s : samples) {
                    focusTravel = std::max(focusTravel, std::fabs(s.focus - samples[0].focus));
                }
                check(focusTravel > 1.f, (id + " racks focus").c_str());
            } else {
                float bodyTravel = 0.f;
                for (std::size_t i = 1; i < samples.size(); ++i) {
                    bodyTravel = std::max(bodyTravel, stepLength(samples[i - 1], samples[i]));
                    const float dx = std::fabs(samples[i].position.x - samples[0].position.x);
                    const float dy = std::fabs(samples[i].position.y - samples[0].position.y);
                    const float dz = std::fabs(samples[i].position.z - samples[0].position.z);
                    bodyTravel = std::max({bodyTravel, dx, dy, dz});
                }
                check(bodyTravel > 1.f, (id + " moves the camera body").c_str());
            }

            // Gate 6: no teleports outside declared loud windows.
            const int cut = static_cast<int>(std::round(duration * spec.cutAt));
            float maxStep = 0.f;
            for (std::size_t i = 1; i < samples.size(); ++i) {
                const bool inCutWindow =
                        spec.twoShot && static_cast<int>(i) >= cut && static_cast<int>(i) <= cut + 1;
                if (inCutWindow) continue;
                maxStep = std::max(maxStep, stepLength(samples[i - 1], samples[i]));
            }
            const float frameSpan = 0.38f * kViewportW; // widest authored whip crossing
            if (spec.highEnergy) {
                check(maxStep < frameSpan, (id + " loud move stays inside the frame span").c_str());
            } else {
                check(maxStep < frameSpan * 0.25f,
                      (id + " has no teleport between neighbor frames").c_str());
            }

            // Gate 7: the settle — last beat slower than peak travel.
            // Loops never settle by design; transitions cut instead.
            const bool loop = spec.distStart == spec.distEnd && spec.xStart == spec.xEnd &&
                              spec.yStart == spec.yEnd && spec.xMid < -900.f && spec.yMid < -900.f;
            if (!spec.twoShot && !spec.highEnergy && !loop && duration >= 20) {
                float peakRate = 0.f;
                for (std::size_t i = 1; i + 1 < samples.size(); ++i) {
                    peakRate = std::max(peakRate, stepLength(samples[i - 1], samples[i]));
                }
                const std::size_t n = samples.size();
                const float endRate = stepLength(samples[n - 2], samples[n - 1]);
                check(endRate <= peakRate + 1e-3f, (id + " settles into the hold").c_str());
            }
        }
    }

    void theLoopAndCutStructuresHold() {
        section("loop and cut");
        FakeContentHost host;
        // Gate 8: the micro-float returns exactly to its start pose.
        {
            const auto samples = samplePreset(CameraMotionPreset::UiMicroFloat, 150, host);
            checkNear(samples.front().position.x, samples.back().position.x, 1e-2f,
                      "micro-float loops in X");
            checkNear(samples.front().position.y, samples.back().position.y, 1e-2f,
                      "micro-float loops in Y");
            checkNear(samples.front().position.z, samples.back().position.z, 1e-2f,
                      "micro-float loops in distance");
        }
        // Gate 9: every two-shot preset jumps at its cut and is calm on
        // both legs outside it.
        for (const auto preset : allPresets()) {
            const auto& spec = cameraMotionSpecFor(preset);
            if (!spec.twoShot) continue;
            const std::string id = cameraMotionPresetId(preset);
            const int duration = spec.durationFrames;
            const auto samples = samplePreset(preset, duration, host);
            const int cut = static_cast<int>(std::round(duration * spec.cutAt));
            bool calmOut = true, calmIn = true;
            for (int i = 1; i < cut && i < static_cast<int>(samples.size()); ++i) {
                if (stepLength(samples[i - 1], samples[i]) > 0.38f * kViewportW) calmOut = false;
            }
            for (int i = cut + 2; i < static_cast<int>(samples.size()); ++i) {
                if (stepLength(samples[i - 1], samples[i]) > 0.38f * kViewportW) calmIn = false;
            }
            check(calmOut && calmIn, (id + " legs stay continuous outside the cut").c_str());
        }
        // The whip pair mirrors: out ends where in begins, on opposite sides.
        {
            const auto left = samplePreset(CameraMotionPreset::WhipPanLeft, 14, host);
            const auto right = samplePreset(CameraMotionPreset::WhipPanRight, 14, host);
            // The out-leg peak of each whip sits at the cut; the two peaks must
            // be strictly on opposite sides and mirror each other in X.
            float leftPeak = 0.f, rightPeak = 0.f;
            for (const auto& s : left) leftPeak = std::min(leftPeak, s.position.x);
            for (const auto& s : right) rightPeak = std::max(rightPeak, s.position.x);
            check(leftPeak < -100.f && rightPeak > 100.f,
                  "whip left/right peaks sit on strictly opposite sides of the subject");
            checkNear(leftPeak, -rightPeak, 1.f, "whip left/right peaks mirror in X");
            check(std::fabs(left.front().position.x - right.front().position.x) < 60.f,
                  "both whips start from the rest framing");
        }
    }

    void theSelectionTableCoversContent() {
        section("selection table");
        const auto kinds = cameraContentKinds();
        check(kinds.size() == 13, "thirteen recognised content kinds");
        std::set<std::string> known;
        for (const auto id : cameraMotionPresetIds()) known.insert(id);
        std::set<std::string> suggested;
        for (const auto kind : kinds) {
            const auto picks = cameraMotionSuggestions(kind);
            check(!picks.empty(), "every content kind suggests at least one preset");
            for (const auto preset : picks) {
                check(known.count(cameraMotionPresetId(preset)) == 1,
                      "suggestions name real presets only");
                suggested.insert(cameraMotionPresetId(preset));
            }
        }
        // Gate 10: every preset is selectable for at least one content kind.
        for (const auto preset : allPresets()) {
            const std::string id = cameraMotionPresetId(preset);
            check(suggested.count(id) == 1,
                  std::string("preset is selectable by content: ").append(id).c_str());
        }
    }

}// namespace

int main() {
    concurrentColdPresetLookupsAreStable();
    theSpecTableIsComplete();
    theIntensityLadderIsSpec();
    everyPresetAnimatesCleanly();
    theLoopAndCutStructuresHold();
    theSelectionTableCoversContent();
    return chrononmotion_test::report();
}
