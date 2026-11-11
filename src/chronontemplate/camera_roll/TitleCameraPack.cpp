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

#include "chrononmotion/motion/CameraValidation.hpp"

#include <algorithm>
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

        void validateShot(const TitleCameraShot& shot) {
            if (shot.duration <= 0) {
                throw std::invalid_argument(
                    "applyTitleCameraShot: duration must be positive");
            }
            if (shot.inFrame < 0) {
                throw std::invalid_argument(
                    "applyTitleCameraShot: inFrame must be non-negative");
            }
            if (!std::isfinite(shot.minVisible) || shot.minVisible < 0.f ||
                shot.minVisible > 1.f) {
                throw std::invalid_argument(
                    "applyTitleCameraShot: minVisible must be finite and within [0, 1]");
            }
            if (!finiteAnchor(shot.anchor)) {
                throw std::invalid_argument(
                    "applyTitleCameraShot: the anchor must be finite");
            }
            if (shot.anchor.halfWidth < 0.f || shot.anchor.halfHeight < 0.f) {
                throw std::invalid_argument(
                    "applyTitleCameraShot: half extents must be non-negative");
            }
            if (shot.minVisible > 0.f &&
                (shot.anchor.halfWidth == 0.f || shot.anchor.halfHeight == 0.f)) {
                throw std::invalid_argument(
                    "applyTitleCameraShot: half extents must be positive when minVisible > 0");
            }
        }

        [[nodiscard]] TitleCameraPlan planFor(TitleCameraMove move, const TitleCameraShot& shot) {
            using namespace chrononmotion::motion::camera;
            return chrononmotion::motion::camera::resolveTitleCameraPlan(
                    move, chrononmotion::motion::camera::TitleRecipeShot{shot.framing, shot.intensity, 55.f});
        }

        void authorShotRequest(chrononmotion::motion::CameraRig& rig,
                               const TemplateScene& scene, TitleCameraMove move,
                               const TitleCameraShot& shot) {
            using namespace chrononmotion::motion::camera;
            applyTitleCameraRequest(rig, TitleCameraRequest{
                move, TitleRecipeShot{shot.framing, shot.intensity, 55.f},
                shot.anchor.center, shot.inFrame, shot.duration, scene.fps(),
                scene.canvas()
            });
        }

    }// namespace

    const char* titleCameraMoveId(TitleCameraMove move) noexcept {
        return chrononmotion::motion::camera::titleMoveId(move).data();
    }

    std::vector<std::string> titleCameraMoveIds() {
        std::vector<std::string> ids;
        const auto moves = chrononmotion::motion::camera::titleCameraMoves();
        ids.reserve(moves.size());
        for (const TitleCameraMove move : moves) {
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

    TitleCameraFramingReport titleCameraFramingReport(
        TemplateScene& scene, TitleCameraMove move, const TitleCameraShot& shot) {
        using namespace chrononmotion::motion;

        TitleCameraFramingReport out;
        if (shot.duration <= 0 || shot.inFrame < 0) {
            out.passed = false;
            out.failure =
                "TitleCameraFramingInvalid: duration must be positive and inFrame non-negative";
            return out;
        }
        if (!std::isfinite(shot.minVisible) || shot.minVisible < 0.f ||
            shot.minVisible > 1.f) {
            out.passed = false;
            out.failure =
                "TitleCameraFramingInvalid: minVisible must be finite and within [0, 1]";
            return out;
        }
        if (!finiteAnchor(shot.anchor) || shot.anchor.halfWidth < 0.f ||
            shot.anchor.halfHeight < 0.f) {
            out.passed = false;
            out.failure =
                "TitleCameraFramingInvalid: anchor must be finite with non-negative half extents";
            return out;
        }
        if (shot.minVisible > 0.f &&
            (shot.anchor.halfWidth == 0.f || shot.anchor.halfHeight == 0.f)) {
            out.passed = false;
            out.failure =
                "TitleCameraFramingInvalid: half extents must be positive when minVisible > 0";
            return out;
        }
        if (shot.minVisible == 0.f) return out;

        chrononmotion::motion::CameraRig probe = scene.cameraRig();
        authorShotRequest(probe, scene, move, shot);

        CameraValidator validator;
        validator.addBounds(CameraValidationBounds{
                                .name = "title",
                                .center = shot.anchor.center,
                                .halfExtent = {shot.anchor.halfWidth,
                                               shot.anchor.halfHeight, 0.f}})
            .requireVisible("title", shot.minVisible);

        const float fps = scene.fps();
        for (int frame = shot.inFrame; frame <= shot.inFrame + shot.duration; ++frame) {
            const CameraPose pose = probe.sample(
                static_cast<float>(frame) / fps);
            const CameraValidationReport report =
                validator.validate(pose, scene.canvas());
            const auto it = std::find_if(
                report.layers.begin(), report.layers.end(),
                [](const CameraValidationLayerReport& layer) {
                    return layer.name == "title";
                });
            if (it == report.layers.end()) continue;
            if (it->visibleRatio < out.worstVisible) {
                out.worstVisible = it->visibleRatio;
                out.worstFrame = frame;
            }
            if (!report.passed) {
                out.passed = false;
                out.failure =
                    "TitleCameraFramingLost: move '" +
                    std::string(titleCameraMoveId(move)) + "' frame " +
                    std::to_string(frame) + " keeps only " +
                    std::to_string(std::lround(it->visibleRatio * 100.f)) +
                    "% of the title in frame (minimum " +
                    std::to_string(std::lround(shot.minVisible * 100.f)) +
                    "%); choose a wider framing or a move that does not leave the subject";
                return out;
            }
        }
        return out;
    }

    void applyTitleCameraShot(TemplateScene& scene, TitleCameraMove move,
                              const TitleCameraShot& shot) {
        validateShot(shot);

        // Validate the proposed shot before touching the scene. The report
        // authors a private copy of the rig, so a framing loss leaves no keys
        // behind and `apply` is transactional for the common failure case.
        const TitleCameraFramingReport framing =
            titleCameraFramingReport(scene, move, shot);
        if (!framing.passed) {
            throw TitleCameraFramingLost(framing.failure);
        }

        // The probe already proved the shot is valid, so the real authoring
        // pass is the first and only mutation of the scene rig. A framing loss
        // can no longer leave partial camera keys behind.
        chrononmotion::motion::presets::author(
            scene.motion(), titleCameraMoveId(move), [&] {
                authorShotRequest(scene.cameraRig(), scene, move, shot);
            });
    }

}// namespace chronontemplate
