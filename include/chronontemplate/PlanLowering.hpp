// Deterministic TemplateScene -> Chronon3D RenderPlan adapter.
#ifndef CHRONONTEMPLATE_PLAN_LOWERING_HPP
#define CHRONONTEMPLATE_PLAN_LOWERING_HPP

#include "chronontemplate/TemplateScene.hpp"

#include <chrononmotion/motion/RenderPlanLowering.hpp>

#include <cstdint>
#include <string>
#include <unordered_map>

namespace chronontemplate {

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
