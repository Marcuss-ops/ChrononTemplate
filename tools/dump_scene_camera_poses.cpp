// ChrononTemplate — dump the scene-camera pack's sequencer poses.
//
// Authors the canary sequences with applySceneCameraSequence on real
// TemplateScene rigs and prints, per sequence, one row per frame:
//
//   sequence_id | frame | px py pz | rx ry rz (degrees) | fov | focus
//
// The rows are the contract render_scene_camera_sequencer_v1.py lowers into
// chronon.render-plan.v3 camera_animation tracks. Positions and Euler angles
// are canvas-authored (centre at 960,540); the Python side performs the same
// render-plan lowering as the title-camera pack.

#include "chronontemplate/SceneCameraPack.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <string>
#include <vector>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;

namespace {

    class Host final : public ContentHost {
    public:
        ContentHandle createText(const TextRequest& r) override {
            ContentHandle h;
            h.id = "text/" + r.text;
            h.kind = ContentKind::Text;
            h.metrics.naturalSize = Vector2(1100.f, 180.f);
            h.metrics.anchor = Vector2(0.5f, 0.5f);
            h.metrics.fingerprint = "scene-camera-sequencer-v1";
            return h;
        }
        ContentHandle createImage(const ImageRequest&) override {
            ContentHandle h;
            h.id = "image/scene";
            h.kind = ContentKind::Image;
            h.metrics.naturalSize = Vector2(1280.f, 720.f);
            h.metrics.anchor = Vector2(0.5f, 0.5f);
            h.metrics.fingerprint = "scene-camera-sequencer-v1";
            return h;
        }
        ContentHandle createVideo(const VideoRequest&) override { return {}; }
        ContentHandle createShape(const ShapeRequest& r) override {
            ContentHandle h;
            h.id = "shape/" + r.name;
            h.kind = ContentKind::Image;
            h.metrics.naturalSize = r.size;
            h.metrics.anchor = Vector2(0.5f, 0.5f);
            h.metrics.fingerprint = "scene-camera-sequencer-v1";
            return h;
        }
        std::string currentFingerprint(const ContentId&) const override {
            return "scene-camera-sequencer-v1";
        }
    };

    constexpr float kFps = 30.f;

    SceneSubject phraseSubject(const Vector3& center) {
        return SceneSubject{.kind = SubjectKind::Phrase, .center = center,
                            .halfWidth = 520.f, .halfHeight = 110.f};
    }

    SceneSubject imageSubject(const Vector3& center) {
        return SceneSubject{.kind = SubjectKind::Image, .center = center,
                            .halfWidth = 460.f, .halfHeight = 260.f};
    }

    SceneSubject textSubject(const Vector3& center) {
        return SceneSubject{.kind = SubjectKind::Text, .center = center,
                            .halfWidth = 620.f, .halfHeight = 150.f};
    }

    // The gallery grammar: frase → immagine → testo, three holds of 60 frames
    // joined by the transition under test.
    SceneCameraSequence canaryFor(SceneCameraTransition transition) {
        SceneCameraSequence sequence;
        sequence.beats = {
                SceneBeat{.subject = phraseSubject(Vector3(960.f, 540.f, 0.f)), .hold = 60},
                SceneBeat{.subject = imageSubject(Vector3(960.f, 540.f, -80.f)), .hold = 60},
                SceneBeat{.subject = textSubject(Vector3(960.f, 540.f, 0.f)), .hold = 60}};
        sequence.transition = transition;
        sequence.intensity = 1.f;
        sequence.travelFrames = 24;
        sequence.inFrame = 0;
        return sequence;
    }

    Vector3 eulerDegrees(const Quaternion& q) {
        constexpr float radToDeg = 57.29577951308232f;
        // RenderPlan's camera looks along +Z, while CameraRig poses look along
        // -Z: lower the inverse orientation before extracting XYZ Euler angles.
        Quaternion camera = q;
        camera.invert();
        const float x = std::atan2(2.f * (camera.w * camera.x - camera.y * camera.z),
                                   1.f - 2.f * (camera.x * camera.x + camera.y * camera.y));
        const float s = std::clamp(2.f * (camera.w * camera.y + camera.z * camera.x), -1.f, 1.f);
        const float y = std::asin(s);
        const float z = std::atan2(2.f * (camera.w * camera.z - camera.x * camera.y),
                                   1.f - 2.f * (camera.y * camera.y + camera.z * camera.z));
        return Vector3(x * radToDeg, y * radToDeg, z * radToDeg);
    }

    void dumpSequence(const std::string& id, const SceneCameraSequence& sequence,
                      TemplateScene& scene) {
        applySceneCameraSequence(scene, sequence);
        const int total = static_cast<int>(sequence.beats.size()) * 60 +
                          static_cast<int>(sequence.beats.size() - 1) * sequence.travelFrames;
        std::cout << id << ' ' << total << '\n';
        for (int f = 0; f < total; ++f) {
            const CameraPose pose = scene.camera().rig().sample(static_cast<float>(f) / kFps);
            const Vector3 r = eulerDegrees(pose.orientation);
            const float focus = pose.hasTarget
                                        ? (pose.position - pose.target).length()
                                        : (pose.position - sequence.beats.back().subject.center).length();
            std::cout << f << ' ' << pose.position.x << ' ' << pose.position.y << ' '
                      << pose.position.z << ' ' << r.x << ' ' << r.y << ' ' << r.z << ' '
                      << pose.fov << ' ' << focus << '\n';
        }
    }

}// namespace

int main() {
    Host host;

    // ---- the gallery: every transition on the same three-stacco grammar ----
    std::vector<SceneCameraTransition> transitions{
            SceneCameraTransition::PushThrough,    SceneCameraTransition::LateralSwipe,
            SceneCameraTransition::ArcCarry,       SceneCameraTransition::OrbitHandoff,
            SceneCameraTransition::RiseAndLand,    SceneCameraTransition::FocusRack,
            SceneCameraTransition::PullBackReveal, SceneCameraTransition::WhipReframe};
    for (const SceneCameraTransition transition : transitions) {
        TemplateScene scene("scene_camera_gallery", kFps, host, 1920.f, 1080.f);
        auto& phrase = scene.text({.text = "LA STORIA COMINCIA QUI", .font = "Inter-Bold.ttf",
                                   .fontSize = 96.f});
        phrase.position(960.f, 540.f);
        auto& image = scene.image({.path = "assets/images/camera_reference.jpg"});
        image.position(960.f, 540.f);
        auto& title = scene.text({.text = "IL SECONDO ATTO", .font = "Inter-Bold.ttf",
                                  .fontSize = 120.f});
        title.position(960.f, 540.f);

        dumpSequence(sceneCameraTransitionId(transition), canaryFor(transition), scene);
    }

    // ---- the master canary: five stacchi, one continuous documentary chain ----
    {
        TemplateScene scene("scene_camera_master", kFps, host, 1920.f, 1080.f);
        auto& phrase = scene.text({.text = "TUTTO COMINCIA DA UN LUOGO", .font = "Inter-Bold.ttf",
                                   .fontSize = 84.f});
        phrase.position(960.f, 540.f);
        auto& image = scene.image({.path = "assets/images/camera_reference.jpg"});
        image.position(960.f, 540.f);
        auto& quote = scene.text({.text = "\"IL CORAGGIO DI CAMBIARE\"", .font = "Inter-Bold.ttf",
                                  .fontSize = 72.f});
        quote.position(960.f, 540.f);
        auto& card = scene.shape({.size = Vector2(920.f, 520.f), .fillColor = "#101820",
                                  .name = "stat-card", .cornerRadius = 18.f});
        card.position(960.f, 540.f);
        auto& title = scene.text({.text = "E FINISCE COME UNA DOMANDA", .font = "Inter-Bold.ttf",
                                  .fontSize = 108.f});
        title.position(960.f, 540.f);

        SceneCameraSequence master;
        master.beats = {
                SceneBeat{.subject = phraseSubject(Vector3(960.f, 540.f, 0.f)), .hold = 66},
                SceneBeat{.subject = imageSubject(Vector3(960.f, 540.f, -80.f)), .hold = 66},
                SceneBeat{.subject = textSubject(Vector3(960.f, 540.f, -40.f)), .hold = 66},
                SceneBeat{.subject = {.kind = SubjectKind::Card,
                                      .center = Vector3(960.f, 540.f, -120.f),
                                      .halfWidth = 460.f, .halfHeight = 260.f},
                          .hold = 66},
                SceneBeat{.subject = textSubject(Vector3(960.f, 540.f, 0.f)), .hold = 66}};
        master.transition = SceneCameraTransition::ArcCarry;
        master.intensity = 1.f;
        master.travelFrames = 30;
        master.inFrame = 0;
        dumpSequence("master_five_stacchi_arc_carry", master, scene);
    }

    return 0;
}
