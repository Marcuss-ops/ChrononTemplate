// Deterministic TemplateScene -> Chronon3D RenderPlan adapter.
#ifndef CHRONONTEMPLATE_PLAN_LOWERING_HPP
#define CHRONONTEMPLATE_PLAN_LOWERING_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <chrononmotion/motion/RenderPlanLowering.hpp>

#include <cstdint>
#include <string>
#include <unordered_map>

namespace chronontemplate {

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

} // namespace chronontemplate

#endif
