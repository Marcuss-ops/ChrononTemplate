#include "chronontemplate/map/MapPack.hpp"

#include "chrononmotion/motion/Presets.hpp"
#include "chrononmotion/math/MathUtils.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace chronontemplate {

    namespace {

        using chrononmotion::Vector2;

        /// The part of the timeline the camera spends travelling; the rest is hold.
        [[nodiscard]] float travelFraction(MapMotion motion) {
            switch (motion) {
                case MapMotion::HoldStatic: return 0.f;
                case MapMotion::DivePush: return 0.6f;
                case MapMotion::OrbitSettle: return 0.7f;
                case MapMotion::LateralDrift: return 0.5f;
                case MapMotion::PullBackReveal: return 0.5f;
            }
            return 0.f;
        }

    }// namespace

    const char* mapMotionId(MapMotion motion) noexcept {
        switch (motion) {
            case MapMotion::HoldStatic: return "map_hold_static";
            case MapMotion::DivePush: return "map_dive_push";
            case MapMotion::OrbitSettle: return "map_orbit_settle";
            case MapMotion::LateralDrift: return "map_lateral_drift";
            case MapMotion::PullBackReveal: return "map_pull_back_reveal";
        }
        return "unknown";
    }

    std::vector<MapMotion> mapMotions() {
        return {MapMotion::HoldStatic, MapMotion::DivePush, MapMotion::OrbitSettle,
                MapMotion::LateralDrift, MapMotion::PullBackReveal};
    }

    MapComposition addMapMotion(TemplateScene& scene, const MapSpec& spec) {
        if (spec.platePath.empty()) {
            throw std::invalid_argument("addMapMotion: the plate path is required");
        }
        if (spec.duration <= 0) {
            throw std::invalid_argument("addMapMotion: the duration must be positive");
        }
        if (!(spec.plateSize.x > 0.f) || !(spec.plateSize.y > 0.f) ||
            !std::isfinite(spec.plateSize.x) || !std::isfinite(spec.plateSize.y)) {
            throw std::invalid_argument("addMapMotion: the plate size must be positive and finite");
        }
        for (const MapMarker& marker : spec.markers) {
            if (!std::isfinite(marker.position.x) || !std::isfinite(marker.position.y) ||
                !(marker.size > 0.f) || !std::isfinite(marker.size)) {
                throw std::invalid_argument("addMapMotion: marker positions must be finite and sized");
            }
        }

        const Vector2 canvas = scene.canvas();
        const float fps = scene.fps();
        const int inFrame = spec.inFrame;
        const int endFrame = spec.inFrame + spec.duration;
        const int travel = static_cast<int>(static_cast<float>(spec.duration) * travelFraction(spec.motion));
        const int enterFrames = std::max(1, spec.duration / 10);
        const int exitFrames = std::max(1, std::min(18, spec.duration / 8));

        MapComposition out;
        out.inFrame = inFrame;
        out.endFrame = endFrame;

        LayerHandle& plate = scene.image(ImageSpec{
                .path = spec.platePath,
                .name = "map_plate",
                .targetSize = spec.plateSize});
        plate.position(canvas.x * 0.5f, canvas.y * 0.5f);
        plate.alive(inFrame, endFrame);
        plate.animate(FadeIn{.inFrame = inFrame, .duration = enterFrames});
        plate.animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
        out.plate = &plate;

        // Markers: small rounded blocks that pop in after the plate has settled.
        const int markerStagger = std::max(1, spec.duration / (static_cast<int>(spec.markers.size()) + 2));
        for (std::size_t i = 0; i < spec.markers.size(); ++i) {
            const MapMarker& marker = spec.markers[i];
            LayerHandle& block = scene.shape(ShapeSpec{
                    .size = Vector2(marker.size, marker.size),
                    .fillColor = marker.color,
                    .name = "map_marker_" + std::to_string(i),
                    .cornerRadius = marker.size * 0.5f});
            block.position(marker.position.x, marker.position.y);
            block.alive(inFrame, endFrame);
            block.animate(ScalePop{.inFrame = inFrame + enterFrames + static_cast<int>(i) * markerStagger,
                                   .duration = std::max(2, markerStagger),
                                   .from = 0.4f, .to = 1.f})
                    .animate(FadeIn{.inFrame = inFrame + enterFrames, .duration = enterFrames});
            block.animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
            out.markers.push_back(&block);
        }

        if (!spec.title.empty()) {
            LayerHandle& title = scene.text(TextSpec{.text = spec.title,
                                                     .font = spec.titleFont,
                                                     .fontSize = spec.titleFontSize,
                                                     .color = spec.titleColor,
                                                     .name = "map_title"});
            title.position(canvas.x * 0.5f, canvas.y - spec.titleOffset);
            title.alive(inFrame, endFrame);
            title.animate(FadeIn{.inFrame = inFrame, .duration = enterFrames});
            title.animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
            out.title = &title;
        }

        // The camera is the only thing that moves. Each move lowers onto the rig.
        switch (spec.motion) {
            case MapMotion::HoldStatic:
                break;
            case MapMotion::DivePush:
                scene.camera().push(320.f).between(inFrame, inFrame + travel);
                break;
            case MapMotion::OrbitSettle:
                scene.camera().orbit(0.05f, 0.02f).between(inFrame, inFrame + travel);
                break;
            case MapMotion::LateralDrift:
                chrononmotion::motion::presets::cameraPan(
                        scene.cameraRig(), inFrame, travel, Vector2(180.f, 0.f), fps);
                break;
            case MapMotion::PullBackReveal:
                scene.camera().push(-420.f).between(inFrame, inFrame + travel);
                break;
        }

        return out;
    }

}// namespace chronontemplate
