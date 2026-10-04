#include "chronontemplate/PlanLowering.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace chronontemplate {

chronon3d::render_plan::LayerPlan makeImageLayerPlan(
        const ImageRequest& request, const ContentHandle& handle) {
    using namespace chronon3d::render_plan;
    if (handle.empty() || handle.kind != chrononmotion::motion::ContentKind::Image ||
        !std::isfinite(handle.metrics.naturalSize.x) || !std::isfinite(handle.metrics.naturalSize.y) ||
        handle.metrics.naturalSize.x <= 0.f || handle.metrics.naturalSize.y <= 0.f)
        throw std::invalid_argument("makeImageLayerPlan: a measured image handle is required");
    const bool targetUnset = request.targetSize.x == 0.f && request.targetSize.y == 0.f;
    if (!std::isfinite(request.targetSize.x) || !std::isfinite(request.targetSize.y) ||
        (!targetUnset && (request.targetSize.x <= 0.f || request.targetSize.y <= 0.f)) ||
        !std::isfinite(request.cornerRadius) || request.cornerRadius < 0.f ||
        !std::isfinite(request.borderWidth) || request.borderWidth < 0.f ||
        !std::isfinite(request.saturation) || request.saturation < 0.f || request.saturation > 4.f ||
        !std::isfinite(request.contrast) || request.contrast < 0.f || request.contrast > 16.f ||
        !std::isfinite(request.grain) || request.grain < 0.f || request.grain > 1.f ||
        !std::isfinite(request.vignette) || request.vignette < 0.f || request.vignette > 1.f)
        throw std::invalid_argument("makeImageLayerPlan: request style or target viewport is outside supported ranges");
    if (request.crop.enabled &&
        (!std::isfinite(request.crop.origin.x) || !std::isfinite(request.crop.origin.y) ||
         !std::isfinite(request.crop.size.x) || !std::isfinite(request.crop.size.y) ||
         request.crop.origin.x < 0.f || request.crop.origin.y < 0.f ||
         request.crop.size.x <= 0.f || request.crop.size.y <= 0.f ||
         request.crop.origin.x + request.crop.size.x > 1.f ||
         request.crop.origin.y + request.crop.size.y > 1.f))
        throw std::invalid_argument("makeImageLayerPlan: crop must be a normalized positive rectangle");

    LayerPlan layer;
    layer.type = LayerType::Image;
    layer.asset = handle.id;
    layer.size_dimensions = 2;
    const float naturalWidth = handle.metrics.naturalSize.x;
    const float naturalHeight = handle.metrics.naturalSize.y;
    float cropX = request.crop.enabled ? request.crop.origin.x : 0.f;
    float cropY = request.crop.enabled ? request.crop.origin.y : 0.f;
    float cropWidth = request.crop.enabled ? request.crop.size.x : 1.f;
    float cropHeight = request.crop.enabled ? request.crop.size.y : 1.f;
    if (request.fit == ImageFitMode::Cover && request.targetSize.x > 0.f &&
        request.targetSize.y > 0.f) {
        const float targetAspect = request.targetSize.x / request.targetSize.y;
        const float cropAspect = naturalWidth * cropWidth / (naturalHeight * cropHeight);
        if (cropAspect > targetAspect) {
            const float fittedWidth = naturalHeight * cropHeight * targetAspect / naturalWidth;
            cropX += (cropWidth - fittedWidth) * 0.5f;
            cropWidth = fittedWidth;
        } else if (cropAspect < targetAspect) {
            const float fittedHeight = naturalWidth * cropWidth / targetAspect / naturalHeight;
            cropY += (cropHeight - fittedHeight) * 0.5f;
            cropHeight = fittedHeight;
        }
    }
    const float contentWidth = naturalWidth * cropWidth;
    const float contentHeight = naturalHeight * cropHeight;
    float scale = 1.f;
    if (request.targetSize.x > 0.f && request.targetSize.y > 0.f) {
        const float sx = request.targetSize.x / contentWidth;
        const float sy = request.targetSize.y / contentHeight;
        scale = request.fit == ImageFitMode::Contain ? std::min(sx, sy) : std::max(sx, sy);
        if (request.fit == ImageFitMode::Stretch) scale = 1.f;
        if (request.fit == ImageFitMode::None) scale = 1.f;
        if (!std::isfinite(scale) || scale <= 0.f)
            throw std::invalid_argument("makeImageLayerPlan: image placement scale is invalid");
        layer.size = {request.targetSize.x / scale, request.targetSize.y / scale};
    } else {
        layer.size = {naturalWidth, naturalHeight};
    }

    switch (request.fit) {
        case ImageFitMode::Contain: layer.fit = FitMode::Contain; break;
        case ImageFitMode::Cover: layer.fit = FitMode::Cover; break;
        case ImageFitMode::Stretch: layer.fit = FitMode::Stretch; break;
        case ImageFitMode::None: layer.fit = FitMode::None; break;
        default: throw std::invalid_argument("makeImageLayerPlan: unsupported image fit mode");
    }
    if (request.crop.enabled || request.crop.flipX || cropX > 0.f || cropY > 0.f ||
        cropWidth < 1.f || cropHeight < 1.f) {
        ImageCropPlan crop;
        crop.enabled = true;
        crop.origin = {cropX, cropY};
        crop.size = {cropWidth, cropHeight};
        crop.flip_x = request.crop.flipX;
        layer.crop = crop;
    }
    if (request.cornerRadius > 0.f) layer.radius = request.cornerRadius;
    if (request.borderWidth > 0.f) {
        if (!parse_hex_color(request.borderColor))
            throw std::invalid_argument("makeImageLayerPlan: border color must be #RRGGBB when border width is positive");
        LayerStylePlan style;
        BackgroundStyle frame;
        frame.color = request.borderColor;
        frame.radius = request.cornerRadius + request.borderWidth;
        frame.padding = {request.borderWidth, request.borderWidth};
        frame.padding_dimensions = 2;
        style.background = std::move(frame);
        layer.style = std::move(style);
    }
    const auto addCatalog = [&](std::string effectId, float value) {
        LayerPlan::EffectPlan effect;
        effect.kind = LayerPlan::EffectKindPlan::Catalog;
        effect.canonical_effect_id = std::move(effectId);
        effect.canonical_params.push_back({"value", value});
        layer.effects.push_back(std::move(effect));
    };
    if (request.saturation != 1.f) addCatalog("color.saturation", request.saturation);
    if (request.contrast != 1.f) addCatalog("color.contrast", request.contrast);
    if (request.grain > 0.f) {
        LayerPlan::EffectPlan grain;
        grain.kind = LayerPlan::EffectKindPlan::Noise;
        grain.amount = request.grain;
        grain.seed = request.grainSeed;
        layer.effects.push_back(std::move(grain));
    }
    if (request.vignette > 0.f) {
        LayerPlan::EffectPlan vignette;
        vignette.kind = LayerPlan::EffectKindPlan::Vignette;
        vignette.amount = request.vignette;
        vignette.radius = 0.72f;
        vignette.softness = 0.55f;
        vignette.effect_color = {0.f, 0.f, 0.f, 1.f};
        layer.effects.push_back(std::move(vignette));
    }
    return layer;
}

chronon3d::render_plan::LayerPlan makeShapeLayerPlan(
        const ShapeRequest& request, const ContentHandle& handle) {
    using namespace chronon3d::render_plan;
    if (handle.empty() || !std::isfinite(request.size.x) || !std::isfinite(request.size.y) ||
        request.size.x <= 0.f || request.size.y <= 0.f ||
        !std::isfinite(request.cornerRadius) || request.cornerRadius < 0.f ||
        request.cornerRadius > std::min(request.size.x, request.size.y) * 0.5f)
        throw std::invalid_argument("makeShapeLayerPlan: a measured shape and positive finite size are required");
    const auto fill = parse_hex_color(request.fillColor);
    if (!fill) throw std::invalid_argument("makeShapeLayerPlan: fill color must be #RRGGBB");
    LayerPlan layer;
    layer.type = LayerType::Shape;
    layer.size = {request.size.x, request.size.y};
    layer.size_dimensions = 2;
    ShapeContentPlan shape;
    shape.type = request.cornerRadius > 0.f
                     ? ShapeContentTypePlan::RoundedRect
                     : ShapeContentTypePlan::Rect;
    shape.fill_color = std::array<float, 4>{fill->r, fill->g, fill->b, fill->a};
    shape.radius = request.cornerRadius;
    layer.shape = std::move(shape);
    return layer;
}

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
    auto plan = chrononmotion::motion::lowerToRenderPlan(scene.motion(), options);
    if (const auto& blur = scene.temporalMotionBlur())
        plan.temporal_motion_blur = chronon3d::render_plan::MotionBlurPlan{
            blur->shutterAngle, blur->samples};
    return plan;
}

} // namespace chronontemplate
