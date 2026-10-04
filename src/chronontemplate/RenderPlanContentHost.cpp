#include "chronontemplate/RenderPlanContentHost.hpp"

#include <cmath>
#include <stdexcept>
#include <utility>

namespace chronontemplate {

RenderPlanContentHost::RenderPlanContentHost(RenderPlanContentBackend backend)
        : m_backend(std::move(backend)) {
    if (!m_backend.createText || !m_backend.createImage || !m_backend.createVideo ||
        !m_backend.createShape || !m_backend.currentFingerprint)
        throw std::invalid_argument("RenderPlanContentHost: all content and fingerprint callbacks are required");
}

ContentHandle RenderPlanContentHost::remember(
        ContentHandle handle, chronon3d::render_plan::LayerPlan plan) {
    if (handle.empty() || handle.wireId == 0 || handle.metrics.fingerprint.empty() ||
        !std::isfinite(handle.metrics.naturalSize.x) || !std::isfinite(handle.metrics.naturalSize.y) ||
        handle.metrics.naturalSize.x <= 0.f || handle.metrics.naturalSize.y <= 0.f)
        throw std::invalid_argument("RenderPlanContentHost: backend must return a unique wire id and measured content");
    plan.id.clear(); // ChrononMotion assigns the stable Motion layer identity.
    if (!m_plansByWireId.emplace(handle.wireId, std::move(plan)).second)
        throw std::invalid_argument("RenderPlanContentHost: backend reused a wire id for multiple content requests");
    return handle;
}

ContentHandle RenderPlanContentHost::createText(const TextRequest& request) {
    auto handle = m_backend.createText(request);
    using namespace chronon3d::render_plan;
    LayerPlan plan;
    plan.type = LayerType::Text;
    plan.text = request.text;
    plan.size = {handle.metrics.naturalSize.x, handle.metrics.naturalSize.y};
    plan.size_dimensions = 2;
    LayerStylePlan style;
    style.font = request.font;
    style.font_size = request.fontSize;
    style.fill = request.color;
    plan.style = std::move(style);
    return remember(std::move(handle), std::move(plan));
}

ContentHandle RenderPlanContentHost::createImage(const ImageRequest& request) {
    auto handle = m_backend.createImage(request);
    auto plan = makeImageLayerPlan(request, handle);
    return remember(std::move(handle), std::move(plan));
}

ContentHandle RenderPlanContentHost::createVideo(const VideoRequest& request) {
    auto handle = m_backend.createVideo(request);
    using namespace chronon3d::render_plan;
    LayerPlan plan;
    plan.type = LayerType::Video;
    plan.source = handle.id;
    plan.size = {handle.metrics.naturalSize.x, handle.metrics.naturalSize.y};
    plan.size_dimensions = 2;
    return remember(std::move(handle), std::move(plan));
}

ContentHandle RenderPlanContentHost::createShape(const ShapeRequest& request) {
    auto handle = m_backend.createShape(request);
    auto plan = makeShapeLayerPlan(request, handle);
    return remember(std::move(handle), std::move(plan));
}

std::string RenderPlanContentHost::currentFingerprint(const ContentId& content) const {
    return m_backend.currentFingerprint(content);
}

std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan>
RenderPlanContentHost::layerPlans(const BindingRegistry& bindings) const {
    std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan> output;
    output.reserve(bindings.size());
    for (const auto& binding : bindings.bindings()) {
        const auto found = m_plansByWireId.find(binding.wireContent);
        if (binding.wireContent == 0 || found == m_plansByWireId.end())
            throw std::invalid_argument("RenderPlanContentHost: no native plan payload for Motion content binding");
        output.emplace(binding.layer, found->second);
    }
    return output;
}

chronon3d::render_plan::RenderPlan lowerToRenderPlan(
        TemplateScene& scene, const RenderPlanContentHost& host,
        std::string jobId, std::string outputPath) {
    return lowerToRenderPlan(scene, host.layerPlans(scene.bindings()),
                             std::move(jobId), std::move(outputPath));
}

} // namespace chronontemplate
