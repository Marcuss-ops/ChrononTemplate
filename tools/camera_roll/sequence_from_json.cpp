// ChrononTemplate — author a scene-camera sequence from JSON.
//
// The pre-configured maps live as data: one
// `chronontemplate.scene-camera-sequence.v1` document names the beats (kind,
// centre, half-extents, hold) and the transition, and this tool authors it
// with `applySceneCameraSequence` on a real TemplateScene rig, then prints the
// same per-frame row contract as `dump_scene_camera_poses`:
//
//   sequence_id | total_frames
//   frame | px py pz | rx ry rz (degrees) | fov | focus
//
// Validation is fail-closed: an unknown schema, an unknown transition id, an
// unknown subject kind, a beat count below two, a hold below six frames, a
// non-positive travel/intensity or any non-finite geometry aborts with a
// path-qualified message on stderr and exit status 1.
//
// The `content` block of each beat (the phrase text, the image asset, the
// card shape) is the render side's business and is deliberately never read
// here: the camera map and the content stay separate concerns.
//
// Usage:
//   chronontemplate_sequence_from_json <sequence.json> [--id override]

#include <nlohmann/json.hpp>

#include "chronontemplate/camera_roll/SceneCameraPack.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

    using json = nlohmann::json;
    using namespace chronontemplate;
    using namespace chrononmotion;
    using namespace chrononmotion::motion;

    constexpr float kFps = 30.f;

    class SilentHost final : public ContentHost {
    public:
        ContentHandle createText(const TextRequest&) override { return {}; }
        ContentHandle createImage(const ImageRequest&) override { return {}; }
        ContentHandle createVideo(const VideoRequest&) override { return {}; }
        std::string currentFingerprint(const ContentId&) const override { return "scene-sequence-json"; }
    };

    [[noreturn]] void fail(const std::string& where, const std::string& message) {
        throw std::runtime_error("sequence_from_json: " + where + ": " + message);
    }

    const json& require(const json& document, const char* key, const std::string& where) {
        if (!document.contains(key)) fail(where, std::string("missing key '") + key + "'");
        return document.at(key);
    }

    float requireFiniteNumber(const json& value, const std::string& where, const char* key) {
        if (!value.is_number()) fail(where, std::string("'") + key + "' must be a number");
        const float v = value.get<float>();
        if (!std::isfinite(v)) fail(where, std::string("'") + key + "' must be finite");
        return v;
    }

    int requireNonNegativeInt(const json& value, const std::string& where, const char* key) {
        if (!value.is_number_integer()) fail(where, std::string("'") + key + "' must be an integer");
        const int v = value.get<int>();
        if (v < 0) fail(where, std::string("'") + key + "' must be >= 0");
        return v;
    }

    SceneSubject parseSubject(const json& beat, const std::string& where) {
        const std::string kind = require(beat, "kind", where).get<std::string>();
        SubjectKind subjectKind;
        if (kind == "phrase") subjectKind = SubjectKind::Phrase;
        else if (kind == "image") subjectKind = SubjectKind::Image;
        else if (kind == "text") subjectKind = SubjectKind::Text;
        else if (kind == "card") subjectKind = SubjectKind::Card;
        else fail(where, "unknown kind '" + kind + "' (phrase | image | text | card)");

        const json& center = require(beat, "center", where);
        if (!center.is_array() || center.size() != 3) {
            fail(where, "'center' must be an array of three numbers");
        }
        SceneSubject subject;
        subject.kind = subjectKind;
        subject.center = Vector3(requireFiniteNumber(center[0], where, "center[0]"),
                                 requireFiniteNumber(center[1], where, "center[1]"),
                                 requireFiniteNumber(center[2], where, "center[2]"));
        subject.halfWidth = requireFiniteNumber(require(beat, "half_width", where), where, "half_width");
        subject.halfHeight = requireFiniteNumber(require(beat, "half_height", where), where, "half_height");
        if (subject.halfWidth <= 0.f || subject.halfHeight <= 0.f) {
            fail(where, "half extents must be positive");
        }
        return subject;
    }

    SceneCameraSequence parseSequence(const json& document, const std::string& where) {
        if (!document.is_object()) fail(where, "the document must be a JSON object");
        const std::string schema = require(document, "schema", where).get<std::string>();
        if (schema != "chronontemplate.scene-camera-sequence.v1") {
            fail(where, "unknown schema '" + schema + "' (expected "
                         "chronontemplate.scene-camera-sequence.v1)");
        }

        const std::string transitionId = require(document, "transition", where).get<std::string>();
        bool known = false;
        SceneCameraTransition transition{};
        for (const std::string& id : sceneCameraTransitionIds()) {
            if (id == transitionId) {
                known = true;
                break;
            }
        }
        if (!known) fail(where, "unknown transition '" + transitionId + "'");

        const json& beats = require(document, "beats", where);
        if (!beats.is_array() || beats.size() < 2) {
            fail(where, "'beats' must be an array of at least two beats");
        }
        SceneCameraSequence sequence;
        sequence.transition = transition;
        for (std::size_t i = 0; i < beats.size(); ++i) {
            const std::string beatWhere = where + ".beats[" + std::to_string(i) + "]";
            const json& beat = beats[i];
            if (!beat.is_object()) fail(beatWhere, "must be an object");
            SceneBeat parsed;
            parsed.subject = parseSubject(beat, beatWhere);
            const int hold = requireNonNegativeInt(require(beat, "hold", beatWhere), beatWhere, "hold");
            if (hold < 6) fail(beatWhere, "'hold' must be at least 6 frames");
            parsed.hold = hold;
            sequence.beats.push_back(parsed);
        }

        if (document.contains("intensity")) {
            sequence.intensity = requireFiniteNumber(document.at("intensity"), where, "intensity");
            if (sequence.intensity <= 0.f) fail(where, "'intensity' must be positive");
        }
        if (document.contains("travel_frames")) {
            const int travel = requireNonNegativeInt(document.at("travel_frames"), where, "travel_frames");
            if (travel <= 0) fail(where, "'travel_frames' must be positive");
            sequence.travelFrames = travel;
        }
        if (document.contains("in_frame")) {
            sequence.inFrame = requireNonNegativeInt(document.at("in_frame"), where, "in_frame");
        }
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

    void dumpRows(const std::string& id, const SceneCameraSequence& sequence) {
        SilentHost host;
        TemplateScene scene("scene_sequence_json", kFps, host, 1920.f, 1080.f);
        applySceneCameraSequence(scene, sequence);

        int total = 0;
        for (std::size_t i = 0; i < sequence.beats.size(); ++i) {
            total += sequence.beats[i].hold;
            if (i + 1 < sequence.beats.size()) total += sequence.travelFrames;
        }
        std::cout << id << ' ' << total << '\n';
        for (int f = 0; f < total; ++f) {
            const CameraPose pose = scene.camera().rig().sample(static_cast<float>(f) / kFps);
            const Vector3 r = eulerDegrees(pose.orientation);
            const float focus = pose.hasTarget ? (pose.position - pose.target).length()
                                               : 0.f;
            std::cout << f << ' ' << pose.position.x << ' ' << pose.position.y << ' '
                      << pose.position.z << ' ' << r.x << ' ' << r.y << ' ' << r.z << ' '
                      << pose.fov << ' ' << focus << '\n';
        }
    }

}// namespace

int main(int argc, char** argv) {
    std::string path;
    std::string idOverride;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--id" && i + 1 < argc) {
            idOverride = argv[++i];
        } else if (!arg.empty() && arg[0] != '-') {
            path = arg;
        }
    }
    if (path.empty()) {
        std::cerr << "usage: chronontemplate_sequence_from_json <sequence.json> [--id override]\n";
        return 2;
    }

    try {
        std::ifstream input(path);
        if (!input) fail(path, "cannot open file");
        json document;
        input >> document;

        std::string id = idOverride;
        if (id.empty() && document.is_object() && document.contains("name") &&
            document.at("name").is_string()) {
            id = document.at("name").get<std::string>();
        }
        if (id.empty()) {
            id = std::filesystem::path(path).stem().string();
        }

        dumpRows(id, parseSequence(document, path));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
