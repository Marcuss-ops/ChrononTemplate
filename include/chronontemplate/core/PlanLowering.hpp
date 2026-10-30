// Deterministic TemplateScene -> Chronon3D RenderPlan adapter.
#ifndef CHRONONTEMPLATE_PLAN_LOWERING_HPP
#define CHRONONTEMPLATE_PLAN_LOWERING_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <chrononmotion/motion/RenderPlanLowering.hpp>

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace chronontemplate {

    /// Runtime handoff for applications that compile a plan in-process.
    /// Template supplies layer/content data; the CameraSampleProvider keeps
    /// camera evaluation in ChrononMotion3D through C3D's shutter samples.
    struct RuntimeRenderPlan {
        chronon3d::render_plan::RenderPlan plan;
        chronon3d::render_plan::RuntimeCameraSampleProvider camera;
    };

    /// Map a measured host image request to the native image layer payload.
    /// The Motion lowerer supplies transform, identity and camera animation.
    [[nodiscard]] chronon3d::render_plan::LayerPlan makeImageLayerPlan(
            const ImageRequest& request, const ContentHandle& handle);

    /// Map a measured host shape request to a native procedural rectangle.
    [[nodiscard]] chronon3d::render_plan::LayerPlan makeShapeLayerPlan(
            const ShapeRequest& request, const ContentHandle& handle);

    /// The content owner supplies renderer-facing style/asset data by template
    /// layer id. Motion and camera data are lowered from the scene itself.
    /// Every bound content layer must have exactly one entry; controller layers
    /// must not have one. Unrepresentable data is rejected by the canonical
    /// Motion -> RenderPlan lowerer.
    [[nodiscard]] chronon3d::render_plan::RenderPlan lowerToRenderPlan(
            TemplateScene& scene,
            const std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan>& contentLayers,
            std::string jobId = "chronontemplate",
            std::string outputPath = "output.png");

    /// Offline bake at the exact absolute frame times supplied by the render
    /// job's shutter scheduler. The list must be non-empty and strictly
    /// increasing. Only the camera is sampled at these times; layer tracks
    /// still use the integer-frame bake and are approximate between frames.
    [[nodiscard]] chronon3d::render_plan::RenderPlan lowerToRenderPlan(
            TemplateScene& scene,
            const std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan>& contentLayers,
            std::string jobId,
            std::string outputPath,
            std::vector<double> cameraSampleFrames);

    /// Lower content/layer state for runtime rendering and attach a camera
    /// provider backed by an immutable snapshot of the TemplateScene rig.
    /// For a parented rig, a dedicated MotionScene project-file snapshot owns
    /// the hierarchy; unsupported project-file data fails closed. The caller's
    /// `cameraFingerprint` must identify the rig, hierarchy and timing.
    /// Unlike the offline lowering API, this omits dense camera keyframes.
    [[nodiscard]] RuntimeRenderPlan lowerToRuntimeRenderPlan(
            TemplateScene& scene,
            const std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan>& contentLayers,
            std::string cameraFingerprint,
            std::string jobId = "chronontemplate",
            std::string outputPath = "output.png");

} // namespace chronontemplate

#endif
