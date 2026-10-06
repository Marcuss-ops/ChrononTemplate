#include "chronontemplate/core/RenderPlanContentHost.hpp"

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
    if (request.stroke) {
        if (!std::isfinite(request.stroke->width) || request.stroke->width < 0.f ||
            request.stroke->width > 64.f || request.stroke->color.empty())
            throw std::invalid_argument("RenderPlanContentHost: text stroke must have a color and width in [0, 64]");
        StrokeStyle stroke;
        stroke.color = request.stroke->color;
        stroke.width = request.stroke->width;
        style.stroke = std::move(stroke);
    }
    if (request.shadow) {
        const auto& shadow = *request.shadow;
        if (!std::isfinite(shadow.opacity) || shadow.opacity < 0.f || shadow.opacity > 1.f ||
            !std::isfinite(shadow.blur) || shadow.blur < 0.f || shadow.blur > 256.f ||
            !std::isfinite(shadow.offset.x) || !std::isfinite(shadow.offset.y) ||
            std::abs(shadow.offset.x) > 256.f || std::abs(shadow.offset.y) > 256.f ||
            shadow.color.empty())
            throw std::invalid_argument("RenderPlanContentHost: text shadow values are outside supported ranges");
        ShadowStyle lowered;
        lowered.color = shadow.color;
        lowered.opacity = shadow.opacity;
        lowered.blur = shadow.blur;
        lowered.offset = {shadow.offset.x, shadow.offset.y};
        lowered.offset_dimensions = 2;
        style.shadow = std::move(lowered);
    }
    if (request.glow) {
        const auto& glow = *request.glow;
        if (!std::isfinite(glow.radius) || glow.radius < 0.f || glow.radius > 256.f ||
            !std::isfinite(glow.intensity) || glow.intensity < 0.f || glow.intensity > 4.f ||
            glow.color.empty())
            throw std::invalid_argument("RenderPlanContentHost: text glow values are outside supported ranges");
        style.glow = GlowStyle{glow.radius, glow.intensity, glow.color};
    }
    if (request.background) {
        const auto& background = *request.background;
        if (!std::isfinite(background.opacity) || background.opacity < 0.f || background.opacity > 1.f ||
            !std::isfinite(background.radius) || background.radius < 0.f || background.radius > 512.f ||
            !std::isfinite(background.padding.x) || !std::isfinite(background.padding.y) ||
            background.padding.x < 0.f || background.padding.y < 0.f || background.color.empty())
            throw std::invalid_argument("RenderPlanContentHost: text background values are outside supported ranges");
        BackgroundStyle lowered;
        lowered.color = background.color;
        lowered.opacity = background.opacity;
        lowered.radius = background.radius;
        lowered.padding = {background.padding.x, background.padding.y};
        lowered.padding_dimensions = 2;
        style.background = std::move(lowered);
    }
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
