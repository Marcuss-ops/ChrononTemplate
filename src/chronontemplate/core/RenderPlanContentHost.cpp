#include "chronontemplate/core/RenderPlanContentHost.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <array>
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
    plan.screen_space = request.screenSpace;
    LayerStylePlan style;
    style.font = request.font;
    style.font_size = request.fontSize;
    style.fill = request.color;
    if (request.stroke) {
        if (!std::isfinite(request.stroke->width) || request.stroke->width < 0.f ||
            request.stroke->width > 64.f || request.stroke->color.empty())
            throw std::invalid_argument("RenderPlanContentHost: text stroke must have a color and width in [0, 64]");
        if (!request.stroke->mode.empty() &&
            request.stroke->mode != "auto" && request.stroke->mode != "distance" &&
            request.stroke->mode != "vector")
            throw std::invalid_argument("RenderPlanContentHost: text stroke mode must be auto, distance, or vector");
        StrokeStyle stroke;
        stroke.color = request.stroke->color;
        stroke.width = request.stroke->width;
        style.stroke = std::move(stroke);
        if (!request.stroke->mode.empty())
            style.stroke_mode = request.stroke->mode;
    }
    if (request.wear) {
        const auto& wear = *request.wear;
        if (!std::isfinite(wear.amount) || wear.amount < 0.f || wear.amount > 1.f ||
            !std::isfinite(wear.scale) || wear.scale <= 0.f || wear.scale > 128.f ||
            !std::isfinite(wear.softness) || wear.softness < 0.f || wear.softness > 1.f)
            throw std::invalid_argument("RenderPlanContentHost: text wear values are outside supported ranges");
        chronon3d::render_plan::TextWearStyle loweredWear;
        loweredWear.amount = wear.amount;
        loweredWear.scale = wear.scale;
        loweredWear.seed = wear.seed;
        loweredWear.softness = wear.softness;
        style.wear = loweredWear;
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
    if (request.material) {
        const auto& material = *request.material;
        if (!std::isfinite(material.extrusionDepth) || material.extrusionDepth < 0.f ||
            material.extrusionDepth > 256.f)
            throw std::invalid_argument("RenderPlanContentHost: text extrusion depth is outside [0, 256]");
        if (material.gelSurface) {
            style.gel_surface = true;
            style.gel_transmission_enabled = material.gelTransmission;
            style.gel_soft_fusion = material.gelSoftFusion;
            style.gel_material_profile = material.gelReference20261107
                ? "reference_20261107" : "current";
        }
        if (material.extrusionDepth > 0.f) {
            style.extruded_text = true;
            style.extrusion_depth = material.extrusionDepth;
        }
    }

    const auto parseEffectColor = [](const std::string& hex, const char* what) {
        const auto parsed = chronon3d::render_plan::parse_hex_color(hex);
        if (!parsed)
            throw std::invalid_argument(std::string("RenderPlanContentHost: ") + what + " must be #RRGGBB");
        return *parsed;
    };
    if (request.dropShadow) {
        const auto& shadow = *request.dropShadow;
        if (!std::isfinite(shadow.opacity) || shadow.opacity < 0.f || shadow.opacity > 1.f ||
            !std::isfinite(shadow.blur) || shadow.blur < 0.f || shadow.blur > 256.f ||
            !std::isfinite(shadow.offset.x) || !std::isfinite(shadow.offset.y) ||
            std::abs(shadow.offset.x) > 256.f || std::abs(shadow.offset.y) > 256.f)
            throw std::invalid_argument("RenderPlanContentHost: text drop shadow values are outside supported ranges");
        const auto color = parseEffectColor(shadow.color, "drop shadow color");
        LayerPlan::EffectPlan effect;
        effect.kind = LayerPlan::EffectKindPlan::DropShadow;
        effect.radius = shadow.blur;
        effect.offset = {shadow.offset.x, shadow.offset.y};
        effect.effect_color = {color.r, color.g, color.b, shadow.opacity};
        plan.effects.push_back(std::move(effect));
    }
    if (request.chromaticAberration) {
        const auto& chromatic = *request.chromaticAberration;
        const auto finiteShift = [](const chrononmotion::Vector2& shift) {
            return std::isfinite(shift.x) && std::isfinite(shift.y) &&
                   std::abs(shift.x) <= 256.f && std::abs(shift.y) <= 256.f;
        };
        if (!std::isfinite(chromatic.redOffset) || !std::isfinite(chromatic.blueOffset) ||
            std::abs(chromatic.redOffset) > 256.f || std::abs(chromatic.blueOffset) > 256.f ||
            !finiteShift(chromatic.redShift) || !finiteShift(chromatic.greenShift) ||
            !finiteShift(chromatic.blueShift))
            throw std::invalid_argument("RenderPlanContentHost: chromatic aberration values are outside supported ranges");
        LayerPlan::EffectPlan effect;
        effect.kind = LayerPlan::EffectKindPlan::ChromaticAberration;
        effect.chromatic_red_offset = chromatic.redOffset;
        effect.chromatic_blue_offset = chromatic.blueOffset;
        effect.chromatic_red_transform = {chromatic.redShift.x, chromatic.redShift.y, 1.f, 1.f, 0.f, 1.f};
        effect.chromatic_green_transform = {chromatic.greenShift.x, chromatic.greenShift.y, 1.f, 1.f, 0.f, 1.f};
        effect.chromatic_blue_transform = {chromatic.blueShift.x, chromatic.blueShift.y, 1.f, 1.f, 0.f, 1.f};
        plan.effects.push_back(std::move(effect));
    }
    if (request.bloom) {
        const auto& bloom = *request.bloom;
        if (!std::isfinite(bloom.threshold) || bloom.threshold < 0.f || bloom.threshold > 1.f ||
            !std::isfinite(bloom.radius) || bloom.radius < 0.f || bloom.radius > 256.f ||
            !std::isfinite(bloom.intensity) || bloom.intensity < 0.f || bloom.intensity > 16.f)
            throw std::invalid_argument("RenderPlanContentHost: text bloom values are outside supported ranges");
        LayerPlan::EffectPlan effect;
        effect.kind = LayerPlan::EffectKindPlan::Bloom;
        effect.bloom_threshold = bloom.threshold;
        effect.radius = bloom.radius;
        effect.bloom_intensity = bloom.intensity;
        plan.effects.push_back(std::move(effect));
    }
    if (request.lightRays) {
        const auto& rays = *request.lightRays;
        if (!std::isfinite(rays.originX) || rays.originX < 0.f || rays.originX > 1.f ||
            !std::isfinite(rays.originY) || rays.originY < 0.f || rays.originY > 1.f ||
            !std::isfinite(rays.length) || rays.length < 0.f || rays.length > 4096.f ||
            !std::isfinite(rays.density) || rays.density < 0.f || rays.density > 8.f ||
            !std::isfinite(rays.decay) || rays.decay < 0.f || rays.decay > 1.f ||
            !std::isfinite(rays.opacity) || rays.opacity < 0.f || rays.opacity > 1.f)
            throw std::invalid_argument("RenderPlanContentHost: light ray values are outside supported ranges");
        const auto color = parseEffectColor(rays.color, "light rays color");
        LayerPlan::EffectPlan effect;
        effect.kind = LayerPlan::EffectKindPlan::LightRays;
        effect.light_rays_origin = {rays.originX, rays.originY};
        effect.light_rays_length = rays.length;
        effect.light_rays_density = rays.density;
        effect.light_rays_decay = rays.decay;
        effect.light_rays_color = {color.r, color.g, color.b, rays.opacity};
        plan.effects.push_back(std::move(effect));
    }
    if (request.lensFlare) {
        const auto& flare = *request.lensFlare;
        if (!std::isfinite(flare.threshold) || flare.threshold < 0.f || flare.threshold > 1.f ||
            !std::isfinite(flare.intensity) || flare.intensity < 0.f || flare.intensity > 16.f ||
            !std::isfinite(flare.radius) || flare.radius < 0.f || flare.radius > 4.f ||
            !std::isfinite(flare.halo) || flare.halo < 0.f || flare.halo > 4.f ||
            !std::isfinite(flare.ghost) || flare.ghost < 0.f || flare.ghost > 4.f ||
            !std::isfinite(flare.streak) || flare.streak < 0.f || flare.streak > 4.f)
            throw std::invalid_argument("RenderPlanContentHost: text lens flare values are outside supported ranges");
        LayerPlan::EffectPlan effect;
        effect.kind = LayerPlan::EffectKindPlan::Catalog;
        effect.canonical_effect_id = "light.lens_flare";
        effect.canonical_params = {
            {"threshold", flare.threshold},
            {"intensity", flare.intensity},
            {"radius", flare.radius},
            {"halo", flare.halo},
            {"ghost", flare.ghost},
            {"streak", flare.streak}};
        plan.effects.push_back(std::move(effect));
    }
    if (request.halation) {
        const auto& halation = *request.halation;
        if (!std::isfinite(halation.threshold) || halation.threshold < 0.f || halation.threshold > 1.f ||
            !std::isfinite(halation.softness) || halation.softness < 0.f || halation.softness > 1.f ||
            !std::isfinite(halation.radiusPx) || halation.radiusPx < 0.f || halation.radiusPx > 64.f ||
            !std::isfinite(halation.intensity) || halation.intensity < 0.f || halation.intensity > 8.f)
            throw std::invalid_argument("RenderPlanContentHost: text halation values are outside supported ranges");
        LayerPlan::EffectPlan effect;
        effect.kind = LayerPlan::EffectKindPlan::Halation;
        effect.halation_threshold = halation.threshold;
        effect.halation_softness = halation.softness;
        effect.halation_radius = halation.radiusPx;
        effect.halation_intensity = halation.intensity;
        effect.halation_tint = halation.tint;
        plan.effects.push_back(std::move(effect));
    }
    if (request.effectGlow) {
        const auto& glow = *request.effectGlow;
        if (!std::isfinite(glow.radius) || glow.radius < 0.f || glow.radius > 256.f ||
            !std::isfinite(glow.intensity) || glow.intensity < 0.f || glow.intensity > 4.f)
            throw std::invalid_argument("RenderPlanContentHost: text effect glow values are outside supported ranges");
        const auto color = parseEffectColor(glow.color, "text effect glow color");
        LayerPlan::EffectPlan effect;
        effect.kind = LayerPlan::EffectKindPlan::Glow;
        effect.radius = glow.radius;
        effect.glow_intensity = glow.intensity;
        effect.effect_color = {color.r, color.g, color.b, 1.f};
        plan.effects.push_back(std::move(effect));
    }
    if (request.gaussianBlurRadius) {
        const float radius = *request.gaussianBlurRadius;
        if (!std::isfinite(radius) || radius < 0.f || radius > 256.f)
            throw std::invalid_argument("RenderPlanContentHost: text gaussian blur radius is outside [0, 256]");
        if (radius > 0.f) {
            LayerPlan::EffectPlan effect;
            effect.kind = LayerPlan::EffectKindPlan::GaussianBlur;
            effect.radius = radius;
            plan.effects.push_back(std::move(effect));
        }
    }
    for (const auto& catalog : request.catalogEffects) {
        if (catalog.effectId.empty())
            throw std::invalid_argument("RenderPlanContentHost: catalog effect id is required");
        LayerPlan::EffectPlan effect;
        effect.kind = LayerPlan::EffectKindPlan::Catalog;
        effect.canonical_effect_id = catalog.effectId;
        for (const auto& [param, value] : catalog.params) {
            if (param.empty() || !std::isfinite(value))
                throw std::invalid_argument("RenderPlanContentHost: catalog effect parameters must be finite and named");
            effect.canonical_params.push_back({param, value});
        }
        plan.effects.push_back(std::move(effect));
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
