// ChrononTemplate — the scene-camera pack, implementation.
//
// The sequence model, stated once: a chain of *holds* (the stacchi — one rest
// pose per beat, derived from the beat's own subject) joined by *travel legs*.
// Every leg is keyed from the exact rest pose of beat N to the exact rest pose
// of beat N+1, so no matter how many beats the chain is continuous at every
// boundary — the pose a hold ends on is the pose the next leg starts from.
//
// Template owns the beat sequence and transition vocabulary. ChrononMotion3D
// evaluates the transition curves, framing, focus and CameraRig tracks.

#include "chronontemplate/camera_roll/SceneCameraPack.hpp"

#include "chrononmotion/motion/CameraSequence.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace chronontemplate {

    using chrononmotion::Vector2;
    using chrononmotion::Vector3;

    namespace {
        chrononmotion::motion::camera::Handoff toHandoff(SceneCameraTransition transition) {
            using H = chrononmotion::motion::camera::Handoff;
            switch (transition) {
                case SceneCameraTransition::PushThrough: return H::PushThrough;
                case SceneCameraTransition::LateralSwipe: return H::LateralSwipe;
                case SceneCameraTransition::ArcCarry: return H::ArcCarry;
                case SceneCameraTransition::OrbitHandoff: return H::OrbitHandoff;
                case SceneCameraTransition::RiseAndLand: return H::RiseAndLand;
                case SceneCameraTransition::FocusRack: return H::FocusRack;
                case SceneCameraTransition::PullBackReveal: return H::PullBackReveal;
                case SceneCameraTransition::WhipReframe: return H::WhipReframe;
            }
            throw std::invalid_argument("applySceneCameraSequence: unknown transition");
        }
    }

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

    SceneSubject sceneSubjectFromLayer(TemplateScene& scene, const LayerHandle& handle,
                                       SubjectKind kind, int frame) {
        if (frame < 0) throw std::invalid_argument("sceneSubjectFromLayer: frame must be non-negative");
        const auto submission = scene.submit(frame);
        const auto found = std::find_if(submission.layers.begin(), submission.layers.end(),
            [&](const BoundLayer& bound) { return bound.transform.id == handle.id(); });
        if (found == submission.layers.end())
            throw std::invalid_argument("sceneSubjectFromLayer: layer is not in the compiled scene");
        const float width = found->content.metrics.naturalSize.x;
        const float height = found->content.metrics.naturalSize.y;
        if (found->content.empty() || !std::isfinite(width) || !std::isfinite(height) ||
            width <= 0.f || height <= 0.f) {
            throw std::invalid_argument("sceneSubjectFromLayer: layer needs measured positive content bounds");
        }

        Vector3 corners[] = {Vector3(0.f, 0.f, 0.f), Vector3(width, 0.f, 0.f),
                             Vector3(0.f, height, 0.f), Vector3(width, height, 0.f)};
        for (Vector3& corner : corners) corner.applyMatrix4(found->transform.world);
        float minX = corners[0].x, maxX = corners[0].x;
        float minY = corners[0].y, maxY = corners[0].y;
        float minZ = corners[0].z, maxZ = corners[0].z;
        for (const Vector3& corner : corners) {
            minX = std::min(minX, corner.x); maxX = std::max(maxX, corner.x);
            minY = std::min(minY, corner.y); maxY = std::max(maxY, corner.y);
            minZ = std::min(minZ, corner.z); maxZ = std::max(maxZ, corner.z);
        }
        return SceneSubject{kind,
            Vector3((minX + maxX) * 0.5f, (minY + maxY) * 0.5f, (minZ + maxZ) * 0.5f),
            (maxX - minX) * 0.5f, (maxY - minY) * 0.5f};
    }

    float sceneFramingDistance(const SceneSubject& subject, float fovDegrees,
                               const Vector2& viewport, float frameFill) {
        chrononmotion::motion::camera::SequenceSubject resolved;
        resolved.center = subject.center;
        resolved.halfWidth = subject.halfWidth;
        resolved.halfHeight = subject.halfHeight;
        resolved.fov = fovDegrees;
        return chrononmotion::motion::camera::framingDistance(resolved, viewport, frameFill);
    }

    void applySceneCameraSequence(TemplateScene& scene, const SceneCameraSequence& sequence) {
        chrononmotion::motion::camera::CameraSequence resolved;
        resolved.handoff = toHandoff(sequence.transition);
        resolved.intensity = sequence.intensity;
        resolved.travelFrames = sequence.travelFrames;
        resolved.inFrame = sequence.inFrame;
        resolved.beats.reserve(sequence.beats.size());
        for (const SceneBeat& beat : sequence.beats) {
            chrononmotion::motion::camera::SequenceBeat item;
            item.subject.center = beat.subject.center;
            item.subject.halfWidth = beat.subject.halfWidth;
            item.subject.halfHeight = beat.subject.halfHeight;
            item.subject.fov = sceneSubjectFov(beat.subject.kind);
            item.hold = beat.hold;
            resolved.beats.push_back(item);
        }
        chrononmotion::motion::presets::author(scene.motion(), sceneCameraTransitionId(sequence.transition), [&] {
            chrononmotion::motion::camera::applySequence(
                    scene.camera().rig(), resolved, scene.fps(), scene.canvas());
        });
    }

}// namespace chronontemplate
