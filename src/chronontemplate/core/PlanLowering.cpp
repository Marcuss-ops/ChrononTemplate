#include "chronontemplate/core/PlanLowering.hpp"

#include <chronon3d/render_plan/color_utils.hpp>
#include <chrononmotion/motion/SceneImport.hpp>

#include <algorithm>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

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
        !std::isfinite(request.vignette) || request.vignette < 0.f || request.vignette > 1.f ||
        !std::isfinite(request.lightLeak) || request.lightLeak < 0.f || request.lightLeak > 1.f ||
        !std::isfinite(request.channelSplit) || request.channelSplit < 0.f || request.channelSplit > 128.f ||
        request.channelTrail > 16 || !std::isfinite(request.sliceDisplace) ||
        request.sliceDisplace < 0.f || request.sliceDisplace > 1.f ||
        !std::isfinite(request.tornEdgeAmount) || request.tornEdgeAmount < 0.f || request.tornEdgeAmount > 64.f ||
        !std::isfinite(request.tornEdgeScale) || request.tornEdgeScale < 0.f || request.tornEdgeScale > 1024.f ||
        (request.tornEdgeAmount == 0.f && (request.tornEdgeScale != 8.f || request.tornEdgeSeed != 0)) ||
        (request.tornEdgeAmount > 0.f && request.tornEdgeScale <= 0.f) ||
        !std::isfinite(request.scanlineIntensity) || request.scanlineIntensity < 0.f || request.scanlineIntensity > 0.25f ||
        !std::isfinite(request.scanlineSpacing) || request.scanlineSpacing < 0.002f || request.scanlineSpacing > 1.f ||
        (request.scanlineIntensity == 0.f && request.scanlineSpacing != 0.035f) ||
        request.mosaicBlockSize > 64 || (request.mosaicBlockSize == 1) ||
        !std::isfinite(request.lensCurvature) || request.lensCurvature < -1.f ||
        request.lensCurvature > 1.f ||
        !std::isfinite(request.lensScale) || request.lensScale < 1.f ||
        request.lensScale > 2.f ||
        !std::isfinite(request.softBlur) || request.softBlur < 0.f ||
        request.softBlur > 32.f)
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
    if (request.lightLeak > 0.f) {
        LayerPlan::EffectPlan rays;
        rays.kind = LayerPlan::EffectKindPlan::LightRays;
        rays.light_rays_origin = {1.0f, 0.42f};
        rays.light_rays_length = 0.8f * std::max(handle.metrics.naturalSize.x,
                                                 handle.metrics.naturalSize.y);
        rays.light_rays_density = 0.42f + request.lightLeak * 0.45f;
        rays.light_rays_color = {1.0f, 0.55f, 0.22f, request.lightLeak};
        rays.light_rays_decay = 0.88f;
        layer.effects.push_back(std::move(rays));
        LayerPlan::EffectPlan glow;
        glow.kind = LayerPlan::EffectKindPlan::Glow;
        glow.radius = 18.f;
        glow.glow_intensity = request.lightLeak * 0.65f;
        glow.effect_color = {1.f, 0.48f, 0.2f, request.lightLeak};
        layer.effects.push_back(std::move(glow));
    }
    // Archival optical lens first: the content warps, then splits, then
    // softens — the pipeline order the look depends on.
    if (request.lensCurvature != 0.f) {
        LayerPlan::EffectPlan lens;
        lens.kind = LayerPlan::EffectKindPlan::LensDistortion;
        lens.lens_curvature = request.lensCurvature;
        lens.lens_center = {0.5f, 0.5f};
        lens.lens_scale = request.lensScale;
        layer.effects.push_back(std::move(lens));
    }
    if (request.channelSplit > 0.f) {
        LayerPlan::EffectPlan split;
        split.kind = LayerPlan::EffectKindPlan::ChromaticAberration;
        split.chromatic_red_offset = request.channelSplit;
        split.chromatic_blue_offset = -request.channelSplit;
        split.chromatic_offset_mode = 1;
        layer.effects.push_back(std::move(split));
    }
    if (request.softBlur > 0.f) {
        LayerPlan::EffectPlan blur;
        blur.kind = LayerPlan::EffectKindPlan::GaussianBlur;
        blur.radius = request.softBlur;
        layer.effects.push_back(std::move(blur));
    }
    if (request.channelTrail > 0) {
        LayerPlan::EffectPlan trail;
        trail.kind = LayerPlan::EffectKindPlan::Echo;
        trail.echoes = request.channelTrail;
        trail.decay = 0.48f;
        trail.time_offset_frames = 1;
        layer.effects.push_back(std::move(trail));
    }
    if (request.tornEdgeAmount > 0.f) {
        LayerPlan::EffectPlan torn;
        torn.kind = LayerPlan::EffectKindPlan::RoughenEdges;
        torn.amount = request.tornEdgeAmount;
        torn.roughen_scale = request.tornEdgeScale;
        torn.roughen_complexity = 3;
        torn.warp_evolution = 0.f;
        torn.roughen_seed = request.tornEdgeSeed;
        layer.effects.push_back(std::move(torn));
    }
    if (request.sliceDisplace > 0.f) {
        LayerPlan::EffectPlan slices;
        slices.kind = LayerPlan::EffectKindPlan::MeshWarp;
        slices.mesh_cols = 8;
        slices.mesh_rows = 8;
        slices.mesh_smoothness = 0.f;
        slices.mesh_offsets.reserve(8U * 8U * 2U);
        for (std::uint32_t row = 0; row < 8; ++row) {
            const float offset = (row % 2U == 0U ? 1.f : -1.f) *
                request.sliceDisplace * 0.025f;
            for (std::uint32_t col = 0; col < 8; ++col) {
                slices.mesh_offsets.push_back(offset);
                slices.mesh_offsets.push_back(0.f);
            }
        }
        layer.effects.push_back(std::move(slices));
    }
    if (request.scanlineIntensity > 0.f) {
        LayerPlan::EffectPlan scan;
        scan.kind = LayerPlan::EffectKindPlan::WaveWarp;
        scan.amount = request.scanlineIntensity;
        scan.warp_wavelength = request.scanlineSpacing;
        scan.warp_direction = {0.f, 1.f};
        scan.wave_type = 2;
        layer.effects.push_back(std::move(scan));
    }
    if (request.mosaicBlockSize >= 2) {
        LayerPlan::EffectPlan mosaic;
        mosaic.kind = LayerPlan::EffectKindPlan::Mosaic;
        mosaic.block_size = request.mosaicBlockSize;
        layer.effects.push_back(std::move(mosaic));
    }
    return layer;
}

chronon3d::render_plan::LayerPlan makeShapeLayerPlan(
        const ShapeRequest& request, const ContentHandle& handle) {
    using namespace chronon3d::render_plan;
    if (handle.empty() || !std::isfinite(request.size.x) || !std::isfinite(request.size.y) ||
        request.size.x <= 0.f || request.size.y <= 0.f ||
        !std::isfinite(request.cornerRadius) || request.cornerRadius < 0.f ||
        request.cornerRadius > std::min(request.size.x, request.size.y) * 0.5f ||
        (request.geometry != ShapeGeometry::Rectangle && request.geometry != ShapeGeometry::Ellipse &&
         request.geometry != ShapeGeometry::Grid && request.geometry != ShapeGeometry::DotGrid &&
         request.geometry != ShapeGeometry::Polygon && request.geometry != ShapeGeometry::Path))
        throw std::invalid_argument("makeShapeLayerPlan: a measured shape and positive finite size are required");
    const auto fill = parse_hex_color(request.fillColor);
    const bool grid = request.geometry == ShapeGeometry::Grid;
    const bool dotGrid = request.geometry == ShapeGeometry::DotGrid;
    const bool polygon = request.geometry == ShapeGeometry::Polygon;
    const bool pathGeom = request.geometry == ShapeGeometry::Path;
    if (pathGeom && request.svgAsset.empty() && request.path.empty())
        throw std::invalid_argument("makeShapeLayerPlan: path geometry requires svgAsset or path commands");
    if (!pathGeom && (!request.svgAsset.empty() || !request.path.empty() || request.trim.has_value()))
        throw std::invalid_argument("makeShapeLayerPlan: svgAsset, path commands and trim require ShapeGeometry::Path");
    if (request.fillEnabled && !fill && !request.radialGradient && !request.gradientMesh && !request.field)
        throw std::invalid_argument("makeShapeLayerPlan: fill color must be #RRGGBB");
    if (!std::isfinite(request.noiseAmount) || request.noiseAmount < 0.f || request.noiseAmount > 1.f ||
        !std::isfinite(request.noiseSize) || request.noiseSize <= 0.f || request.noiseSize > 256.f ||
        !std::isfinite(request.contrast) || request.contrast < 0.f || request.contrast > 4.f ||
        !std::isfinite(request.glowRadius) || request.glowRadius < 0.f || request.glowRadius > 256.f ||
        !std::isfinite(request.glowIntensity) || request.glowIntensity < 0.f || request.glowIntensity > 4.f ||
        !std::isfinite(request.bloomThreshold) || request.bloomThreshold < 0.f || request.bloomThreshold > 1.f ||
        !std::isfinite(request.bloomRadius) || request.bloomRadius < 0.f || request.bloomRadius > 256.f ||
        !std::isfinite(request.bloomIntensity) || request.bloomIntensity < 0.f || request.bloomIntensity > 4.f)
        throw std::invalid_argument("makeShapeLayerPlan: native grain/contrast/glow/bloom settings are outside supported ranges");
    if ((grid || dotGrid) && (!std::isfinite(request.gridSpacing) ||
        request.gridSpacing < 4.f || request.gridSpacing > 512.f))
        throw std::invalid_argument("makeShapeLayerPlan: grid spacing must be in [4, 512]");
    if (grid && (request.strokeColor.empty() || !std::isfinite(request.strokeWidth) ||
                 request.strokeWidth < 0.25f || request.strokeWidth > 32.f ||
                 !parse_hex_color(request.strokeColor)))
        throw std::invalid_argument("makeShapeLayerPlan: grid requires a valid stroke color and width");
    if (dotGrid && (!std::isfinite(request.dotRadius) || request.dotRadius < 0.5f || request.dotRadius > 64.f))
        throw std::invalid_argument("makeShapeLayerPlan: dot radius must be in [0.5, 64]");
    if (polygon && (request.polygonPoints < 3 || request.polygonPoints > 64 ||
                    !std::isfinite(request.polygonRotationDegrees)))
        throw std::invalid_argument("makeShapeLayerPlan: polygon points or rotation are invalid");
    if (request.field && (request.field->operators.size() > 8 ||
        (request.fieldRenderScale != 1 && request.fieldRenderScale != 2 && request.fieldRenderScale != 4)))
        throw std::invalid_argument("makeShapeLayerPlan: field operator count or render scale is invalid");
    if (request.fieldRamp && !request.field)
        throw std::invalid_argument("makeShapeLayerPlan: field ramp requires field data");
    if (request.gradientMesh && (request.gradientMesh->nodes.empty() || request.gradientMesh->nodes.size() > 256 ||
                                 request.field || request.radialGradient))
        throw std::invalid_argument("makeShapeLayerPlan: gradient mesh conflicts with another fill or exceeds node budget");
    if ((request.radialGradient && request.gradientMesh) || (request.radialGradient && request.field))
        throw std::invalid_argument("makeShapeLayerPlan: shape fill modes are mutually exclusive");
    LayerPlan layer;
    layer.type = LayerType::Shape;
    layer.size = {request.size.x, request.size.y};
    layer.size_dimensions = 2;
    ShapeContentPlan shape;
    switch (request.geometry) {
        case ShapeGeometry::Ellipse: shape.type = ShapeContentTypePlan::Ellipse; break;
        case ShapeGeometry::Grid: shape.type = ShapeContentTypePlan::Grid; break;
        case ShapeGeometry::DotGrid: shape.type = ShapeContentTypePlan::DotGrid; break;
        case ShapeGeometry::Polygon: shape.type = ShapeContentTypePlan::Polygon; break;
        case ShapeGeometry::Path: shape.type = ShapeContentTypePlan::Path; break;
        case ShapeGeometry::Rectangle:
            shape.type = request.cornerRadius > 0.f
                             ? ShapeContentTypePlan::RoundedRect
                             : ShapeContentTypePlan::Rect;
            break;
    }
    if (pathGeom) {
        shape.fill_rule = request.fillRule == ShapeFillRule::NonZero
                              ? ShapeFillRulePlan::NonZero
                              : ShapeFillRulePlan::EvenOdd;
        if (!request.svgAsset.empty()) {
            shape.svg_asset = request.svgAsset;
        }
        shape.path.reserve(request.path.size());
        for (const auto& cmd : request.path) {
            ShapePathCommandPlan loweredCmd;
            switch (cmd.type) {
                case ShapePathCommandType::MoveTo: loweredCmd.type = ShapePathCommandTypePlan::MoveTo; break;
                case ShapePathCommandType::LineTo: loweredCmd.type = ShapePathCommandTypePlan::LineTo; break;
                case ShapePathCommandType::QuadraticTo: loweredCmd.type = ShapePathCommandTypePlan::QuadraticTo; break;
                case ShapePathCommandType::CubicTo: loweredCmd.type = ShapePathCommandTypePlan::CubicTo; break;
                case ShapePathCommandType::Close: loweredCmd.type = ShapePathCommandTypePlan::Close; break;
            }
            loweredCmd.point = {cmd.point.x, cmd.point.y};
            loweredCmd.control1 = {cmd.control1.x, cmd.control1.y};
            loweredCmd.control2 = {cmd.control2.x, cmd.control2.y};
            shape.path.push_back(loweredCmd);
        }
        if (request.trim) {
            const auto& trimSpec = *request.trim;
            if (!std::isfinite(trimSpec.start) || trimSpec.start < 0.f || trimSpec.start > 1.f ||
                !std::isfinite(trimSpec.end) || trimSpec.end < trimSpec.start || trimSpec.end > 1.f ||
                !std::isfinite(trimSpec.offset))
                throw std::invalid_argument("makeShapeLayerPlan: trim parameters are outside supported ranges");
            PathOperatorPlan op;
            op.kind = PathOperatorKindPlan::Trim;
            op.trim_start = trimSpec.start;
            op.trim_end = trimSpec.end;
            op.trim_offset = trimSpec.offset;
            if (!trimSpec.keyframes.empty()) {
                AnimationTrackPlan track;
                track.property = "trim";
                track.easing = trimSpec.easing.empty() ? "linear" : trimSpec.easing;
                track.keyframes.reserve(trimSpec.keyframes.size());
                for (const auto& kf : trimSpec.keyframes) {
                    AnimationKeyframePlan key;
                    key.frame = chronon3d::Frame{kf.frame};
                    key.value = {kf.start, kf.end, kf.offset};
                    track.keyframes.push_back(std::move(key));
                }
                op.trim_animation = std::move(track);
            }
            shape.operators.push_back(std::move(op));
        }
    }
    if (request.radialGradient) {
        const auto& source = *request.radialGradient;
        if ((request.geometry != ShapeGeometry::Ellipse && request.geometry != ShapeGeometry::Path) ||
            !std::isfinite(source.center.x) ||
            !std::isfinite(source.center.y) || source.center.x < 0.f || source.center.x > 1.f ||
            source.center.y < 0.f || source.center.y > 1.f || !std::isfinite(source.radius) ||
            source.radius <= 0.f || source.radius > 2.f || source.stops.size() < 2 ||
            source.stops.size() > 16)
            throw std::invalid_argument("makeShapeLayerPlan: radial gradient geometry is outside supported ranges");
        std::vector<chronon3d::graphics::GradientStop> stops;
        std::vector<chronon3d::graphics::OpacityStop> opacityStops;
        stops.reserve(source.stops.size());
        opacityStops.reserve(source.stops.size());
        float previousPosition = -1.f;
        for (const auto& stop : source.stops) {
            const auto color = stop.color.size() == 7 && stop.color.front() == '#'
                                   ? chronon3d::Color::try_from_hex(stop.color.c_str())
                                   : std::nullopt;
            if (!color || !std::isfinite(stop.position) || stop.position < previousPosition ||
                stop.position < 0.f || stop.position > 1.f || !std::isfinite(stop.opacity) ||
                stop.opacity < 0.f || stop.opacity > 1.f)
                throw std::invalid_argument("makeShapeLayerPlan: radial gradient stops must be ordered and valid");
            stops.push_back({stop.position, *color});
            opacityStops.push_back({stop.position, stop.opacity});
            previousPosition = stop.position;
        }
        shape.gradient = chronon3d::graphics::GradientDefinition::radial(
            {source.center.x, source.center.y}, source.radius, std::move(stops));
        shape.gradient->opacity_stops = std::move(opacityStops);
        shape.fill_color.reset();
    } else if (request.fillEnabled && fill) {
        shape.fill_color = std::array<float, 4>{fill->r, fill->g, fill->b, fill->a};
    }
    if (request.geometry == ShapeGeometry::Grid) {
        StrokeStyle stroke;
        stroke.color = request.strokeColor;
        stroke.width = request.strokeWidth;
        shape.stroke = std::move(stroke);
        shape.fill_color.reset();
        shape.grid_spacing = request.gridSpacing;
    } else if (request.geometry == ShapeGeometry::DotGrid) {
        shape.grid_spacing = request.gridSpacing;
        shape.dot_radius = request.dotRadius;
    } else if (request.geometry == ShapeGeometry::Polygon) {
        shape.points = request.polygonPoints;
        shape.shape_rotation_deg = request.polygonRotationDegrees;
    }
    if (!request.strokeColor.empty() && !grid) {
        if (!parse_hex_color(request.strokeColor) || !std::isfinite(request.strokeWidth) ||
            request.strokeWidth < 0.25f || request.strokeWidth > 10000.f)
            throw std::invalid_argument("makeShapeLayerPlan: shape stroke is invalid");
        StrokeStyle stroke;
        stroke.color = request.strokeColor;
        stroke.width = request.strokeWidth;
        stroke.cap = request.strokeCap;
        stroke.join = request.strokeJoin;
        stroke.dash_array = request.strokeDashArray;
        stroke.dash_offset = request.strokeDashOffset;
        stroke.taper_start = request.strokeTaperStart;
        stroke.taper_end = request.strokeTaperEnd;
        shape.stroke = std::move(stroke);
    }
    if (request.field) {
        shape.fill_color.reset();
        shape.field = request.field;
        shape.field_ramp = request.fieldRamp;
        shape.field_render_scale = request.fieldRenderScale;
        shape.field_drift = request.fieldDrift;
    }
    if (request.gradientMesh) {
        shape.gradient_mesh = request.gradientMesh;
        shape.fill_color.reset();
    }
    if (!request.fillEnabled && !request.field && !request.gradientMesh && !grid) {
        shape.fill_color.reset();
    }
    if (request.glowRadius > 0.f && request.glowIntensity > 0.f) {
        const auto glowCol = parse_hex_color(request.glowColor);
        if (!glowCol)
            throw std::invalid_argument("makeShapeLayerPlan: glowColor must be #RRGGBB");
        LayerPlan::EffectPlan glow;
        glow.kind = LayerPlan::EffectKindPlan::Glow;
        glow.radius = request.glowRadius;
        glow.glow_intensity = request.glowIntensity;
        glow.effect_color = {glowCol->r, glowCol->g, glowCol->b, 1.f};
        layer.effects.push_back(std::move(glow));
    }
    if (request.bloomRadius > 0.f && request.bloomIntensity > 0.f) {
        LayerPlan::EffectPlan bloom;
        bloom.kind = LayerPlan::EffectKindPlan::Bloom;
        bloom.bloom_threshold = request.bloomThreshold;
        bloom.radius = request.bloomRadius;
        bloom.bloom_intensity = request.bloomIntensity;
        layer.effects.push_back(std::move(bloom));
    }
    if (request.noiseAmount > 0.f) {
        LayerPlan::EffectPlan noise;
        noise.kind = LayerPlan::EffectKindPlan::Noise;
        noise.amount = request.noiseAmount;
        noise.seed = request.noiseSeed;
        noise.animated = request.animatedNoise;
        noise.noise_size = request.noiseSize;
        layer.effects.push_back(std::move(noise));
    }
    if (request.contrast != 1.f) {
        LayerPlan::EffectPlan contrast;
        contrast.kind = LayerPlan::EffectKindPlan::Catalog;
        contrast.canonical_effect_id = "color.contrast";
        contrast.canonical_params.push_back({"value", request.contrast});
        layer.effects.push_back(std::move(contrast));
    }
    if (shape.type == ShapeContentTypePlan::RoundedRect) {
        shape.radius = request.cornerRadius;
    }
    layer.shape = std::move(shape);
    return layer;
}

namespace {
chronon3d::render_plan::RenderPlan lowerToRenderPlanImpl(
        TemplateScene& scene,
        const std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan>& contentLayers,
        std::string jobId,
        std::string outputPath,
        bool bakeCameraSamples,
        std::vector<double> cameraSampleFrames = {}) {
    chrononmotion::motion::RenderPlanLoweringOptions options;
    const auto canvas = scene.canvas();
    options.width = static_cast<int>(canvas.x);
    options.height = static_cast<int>(canvas.y);
    options.jobId = std::move(jobId);
    options.outputPath = std::move(outputPath);
    options.schema = chronon3d::render_plan::kRenderPlanSchemaV3;
    options.cameraRig = &scene.cameraRig();
    options.bakeResolvedCameraSamples = bakeCameraSamples;
    // Materialized Template plans use resolved per-frame layer transforms as
    // well as resolved camera samples. Keep the runtime-provider overload
    // separate: it deliberately evaluates the rig through its provider.
    options.requireResolvedLayerSamples = bakeCameraSamples;
    options.cameraSampleFrames = std::move(cameraSampleFrames);

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
} // namespace

chronon3d::render_plan::RenderPlan lowerToRenderPlan(
        TemplateScene& scene,
        const std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan>& contentLayers,
        std::string jobId,
        std::string outputPath) {
    return lowerToRenderPlanImpl(scene, contentLayers, std::move(jobId),
                                 std::move(outputPath), true);
}

chronon3d::render_plan::RenderPlan lowerToRenderPlan(
        TemplateScene& scene,
        const std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan>& contentLayers,
        std::string jobId,
        std::string outputPath,
        std::vector<double> cameraSampleFrames) {
    if (cameraSampleFrames.empty())
        throw std::invalid_argument("TemplateScene -> RenderPlan: explicit camera sample frames must not be empty");
    return lowerToRenderPlanImpl(scene, contentLayers, std::move(jobId),
                                 std::move(outputPath), true, std::move(cameraSampleFrames));
}

RuntimeRenderPlan lowerToRuntimeRenderPlan(
        TemplateScene& scene,
        const std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan>& contentLayers,
        std::string cameraFingerprint,
        std::string jobId,
        std::string outputPath) {
    auto plan = lowerToRenderPlanImpl(scene, contentLayers, std::move(jobId),
                                      std::move(outputPath), false);
    if (!plan.camera)
        throw std::logic_error("TemplateScene runtime lowering did not produce a camera snapshot");
    auto rig = std::make_shared<const chrononmotion::motion::CameraRig>(scene.cameraRig());
    chronon3d::render_plan::RuntimeCameraSampleProvider provider;
    if (rig->layer().parentId == chrononmotion::motion::Layer::kRoot) {
        provider = chrononmotion::motion::makeCameraSampleProvider(
            std::move(rig), scene.fps(), std::move(cameraFingerprint),
            plan.camera->near, plan.camera->far);
    } else {
        // The project-file round trip creates a separate evaluation context,
        // so the provider survives the template and never races its authoring
        // scene. Unsupported project-file data is rejected, not approximated.
        auto snapshot = std::make_shared<chrononmotion::motion::MotionScene>(
            chrononmotion::motion::sceneFromJson(scene.motion().toJson()));
        provider = chrononmotion::motion::makeCameraSampleProvider(
            std::move(rig), std::move(snapshot), std::move(cameraFingerprint),
            plan.camera->near, plan.camera->far);
    }
    return RuntimeRenderPlan{std::move(plan), std::move(provider)};
}

} // namespace chronontemplate
