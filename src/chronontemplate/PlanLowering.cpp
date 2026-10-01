#include "chronontemplate/PlanLowering.hpp"

#include <stdexcept>
#include <string>
#include <unordered_map>

namespace chronontemplate {

chronon3d::render_plan::RenderPlan lowerToRenderPlan(
        TemplateScene& scene,
        const std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan>& contentLayers,
        std::string jobId,
        std::string outputPath) {
    chrononmotion::motion::RenderPlanLoweringOptions options;
    const auto canvas = scene.canvas();
    options.width = static_cast<int>(canvas.x);
    options.height = static_cast<int>(canvas.y);
    options.jobId = std::move(jobId);
    options.outputPath = std::move(outputPath);
    options.schema = chronon3d::render_plan::kRenderPlanSchemaV3;
    options.cameraRig = &scene.cameraRig();

    std::unordered_map<MotionLayerId, bool> expected;
    for (const auto& binding : scene.bindings().bindings()) {
        expected.emplace(binding.layer, true);
        const auto supplied = contentLayers.find(binding.layer);
        if (supplied == contentLayers.end())
            throw std::invalid_argument("TemplateScene -> RenderPlan: missing content plan for layer " +
                                        std::to_string(binding.layer) + " (" + binding.content + ")");
        options.contentLayers.emplace(std::to_string(binding.layer), supplied->second);
    }
    for (const auto& [layerId, unused] : contentLayers) {
        (void)unused;
        if (!expected.contains(layerId))
            throw std::invalid_argument("TemplateScene -> RenderPlan: content plan supplied for unbound layer " +
                                        std::to_string(layerId));
    }
    return chrononmotion::motion::lowerToRenderPlan(scene.motion(), options);
}

} // namespace chronontemplate
