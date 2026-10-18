// ChrononTemplate — the camera motion pack, implementation.
//
// Fifteen recipes, one resolver. Every preset is a row of spec numbers
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

        // Preset data is authored once in CameraMotionPresets.def and
        // projected below into the executable spec table.
        struct AuthoredCameraMotionPreset {
            CameraMotionPreset preset;
            const char* id;
            CameraMotionFamily family;
            CameraMotionSpec spec;
        };

        constexpr AuthoredCameraMotionPreset kAuthoredCameraMotionPresets[] = {
#define CAMERA_MOTION_PRESET(key, id, family, ...) \
            {CameraMotionPreset::key, id, CameraMotionFamily::family, [] { \
                CameraMotionSpec spec; __VA_ARGS__ return spec; }()},
#include "chronontemplate/camera_roll/CameraMotionPresets.def"
#undef CAMERA_MOTION_PRESET
        };

        constexpr std::size_t kCameraMotionPresetCount =
                sizeof(kAuthoredCameraMotionPresets) / sizeof(kAuthoredCameraMotionPresets[0]);

        [[nodiscard]] const AuthoredCameraMotionPreset* rosterEntry(CameraMotionPreset preset) noexcept {
            const auto ordinal = static_cast<std::size_t>(preset);
            if (ordinal >= kCameraMotionPresetCount || kAuthoredCameraMotionPresets[ordinal].preset != preset) return nullptr;
            return &kAuthoredCameraMotionPresets[ordinal];
        }

        [[nodiscard]] CameraMotionSpec specFor(const AuthoredCameraMotionPreset& row) {
            CameraMotionSpec spec = row.spec;
            spec.id = row.id;
            spec.family = row.family;
            return spec;
        }

        [[nodiscard]] CameraMotionSpec specFor(CameraMotionPreset preset) {
            const auto* entry = rosterEntry(preset);
            return entry == nullptr ? CameraMotionSpec{} : specFor(*entry);
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

    // The canonical roster and fully-authored rows are above.


    std::vector<CameraMotionPreset> cameraMotionPresets() {
        std::vector<CameraMotionPreset> presets;
        presets.reserve(kCameraMotionPresetCount);
        for (const auto& entry : kAuthoredCameraMotionPresets) presets.push_back(entry.preset);
        return presets;
    }

    const char* cameraMotionPresetId(CameraMotionPreset preset) noexcept {
        const auto* entry = rosterEntry(preset);
        return entry == nullptr ? nullptr : entry->id;
    }

    std::vector<std::string> cameraMotionPresetIds() {
        std::vector<std::string> ids;
        ids.reserve(kCameraMotionPresetCount);
        for (const auto& entry : kAuthoredCameraMotionPresets) ids.emplace_back(entry.id);
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
        // Function-local static initialization is guaranteed thread-safe by
        // C++11. Keep the canonical enum order here: the public preset values
        // are stable ordinals consumed by the generated catalog.
        static const std::array<CameraMotionSpec, kCameraMotionPresetCount> table = [] {
            std::array<CameraMotionSpec, kCameraMotionPresetCount> rows{};
            for (std::size_t index = 0; index < kCameraMotionPresetCount; ++index) {
                rows[index] = specFor(kAuthoredCameraMotionPresets[index]);
            }
            return rows;
        }();
        const auto* entry = rosterEntry(preset);
        if (entry == nullptr) return kEmpty;
        return table[static_cast<std::size_t>(preset)];
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
                return {P::TitleSlowPush, P::TitleLateralDrift, P::TitleRiseSettle};
            case CameraContentKind::ImpactWord:
                return {P::TitleSlowPush, P::TitleRiseSettle};
            case CameraContentKind::SinglePortrait:
                return {P::PortraitArc, P::RackFocusPortrait};
            case CameraContentKind::PortraitBuildingText:
                return {P::PortraitArc, P::RackFocusPortrait};
            case CameraContentKind::ArchivePhoto:
                return {P::ArchiveReveal, P::RackFocusPortrait};
            case CameraContentKind::MapCountry:
                return {P::MapRegionPush, P::MapCountryTilt};
            case CameraContentKind::MapTwoCountries:
                return {P::MapRouteTrack, P::MapRegionPush};
            case CameraContentKind::MapRoute:
                return {P::MapRouteTrack};
            case CameraContentKind::DashboardChart:
                return {P::UiPanelPush, P::UiCardParallax};
            case CameraContentKind::PremiumUI3D:
                return {P::UiCardParallax, P::UiMicroFloat, P::Web3DProductPush,
                        P::Web3DOrbit, P::Web3DSlowDrift};
            case CameraContentKind::Web3DObject:
                return {P::Web3DProductPush, P::Web3DOrbit, P::Web3DArcLeft,
                        P::Web3DArcRight, P::Web3DRiseReveal, P::Web3DTopDown,
                        P::Web3DLateralSlide, P::Web3DDollyArc, P::Web3DCraneDown,
                        P::Web3DSlowDrift};
            case CameraContentKind::FastCut:
                return {P::WhipPanLeft, P::WhipPanRight};
            case CameraContentKind::ObjectPass:
                return {P::DollyHandoff};
            case CameraContentKind::BlurPass:
                return {P::RackFocusPortrait};
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
                CameraContentKind::BlurPass, CameraContentKind::Web3DObject};
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

            // Every travel segment follows the declared easing. A mid-leg key is
            // a waypoint on that same curve, not a forced easeIn/easeOut split.
            keyLeg(rig, startPose, rollStart, hasRoll, focusStart, hasFocus, at(t0, fps), travel);
            if (tTravel0 != t0) {
                keyLeg(rig, startPose, rollStart, hasRoll, focusStart, hasFocus, at(tTravel0, fps), travel);
            }
            if (useMid) {
                const int tMid = in + static_cast<int>(std::round(
                        duration * (hasDistMid ? spec.distMidAt : spec.posMidAt)));
                // One key per instant: the peak roll replaces the mid roll when present.
                const float rollAtMid = hasMid(spec.rollPeak) ? degToRad(spec.rollPeak * k) : rollMid;
                keyLeg(rig, midPose, rollAtMid, hasRoll, focusMid, hasFocus, at(tMid, fps), travel);
            } else if (hasRoll && hasMid(spec.rollPeak)) {
                const int tMid = (tTravel0 + tTravel1) / 2;
                rig.rollTrack().add(at(tMid, fps), degToRad(spec.rollPeak * k), travel);
            }
            keyLeg(rig, endPose, rollEnd, hasRoll, focusEnd, hasFocus, at(tTravel1, fps), travel);
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
        chrononmotion::motion::presets::author(scene.motion(), spec.id, [&] {
            if (spec.twoShot) {
                applyTwoShot(scene, spec, shot, duration);
            } else {
                applySingleShot(scene, spec, shot, duration);
            }
        });
    }

}// namespace chronontemplate
