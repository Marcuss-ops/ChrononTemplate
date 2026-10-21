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

        [[nodiscard]] TitleCameraPlan planFor(TitleCameraMove move, const TitleCameraShot& shot) {
            using namespace chrononmotion::motion::camera;
            return chrononmotion::motion::camera::resolveTitleCameraPlan(
                    move, chrononmotion::motion::camera::TitleRecipeShot{shot.framing, shot.intensity, 55.f});
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

    void applyTitleCameraShot(TemplateScene& scene, TitleCameraMove move,
                              const TitleCameraShot& shot) {
        if (!finiteAnchor(shot.anchor)) {
            throw std::invalid_argument("applyTitleCameraShot: the anchor must be finite");
        }

        chrononmotion::motion::presets::author(scene.motion(), titleCameraMoveId(move), [&] {
        using namespace chrononmotion::motion::camera;
        applyTitleCameraRequest(scene.camera().rig(), TitleCameraRequest{
            move, TitleRecipeShot{shot.framing, shot.intensity, 55.f}, shot.anchor.center,
            shot.inFrame, shot.duration, scene.fps(), scene.canvas()
        });
        });
    }

}// namespace chronontemplate
