#include "chronontemplate/map/TacticalFillPack.hpp"

#include "chrononmotion/motion/Easing.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>

namespace chronontemplate {
namespace {

using chrononmotion::Vector2;
using chrononmotion::Vector3;
using chrononmotion::motion::Easing;

constexpr float kPathPadding = 64.f;
constexpr int kMinFrames = 24;
constexpr std::size_t kMaxRegions = 32;
constexpr std::size_t kMaxPoints = 4096;

bool validHexColor(const std::string& color) {
    if (color.size() != 7 || color.front() != '#') return false;
    return std::all_of(color.begin() + 1, color.end(), [](unsigned char c) {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
               (c >= 'A' && c <= 'F');
    });
}

void validateTypography(const MapTypography& type, const char* owner) {
    if (type.font.empty() || !validHexColor(type.color) ||
        !std::isfinite(type.fontSize) || type.fontSize < 8.f || type.fontSize > 256.f)
        throw std::invalid_argument(std::string(owner) +
                                    ": font, colour and size must be valid");
    if (type.stroke &&
        (!validHexColor(type.stroke->color) || !std::isfinite(type.stroke->width) ||
         type.stroke->width < 0.f || type.stroke->width > 16.f))
        throw std::invalid_argument(std::string(owner) + ": invalid text stroke");
    if (type.shadow &&
        (!validHexColor(type.shadow->color) || !std::isfinite(type.shadow->opacity) ||
         type.shadow->opacity < 0.f || type.shadow->opacity > 1.f ||
         !std::isfinite(type.shadow->blur) || type.shadow->blur < 0.f ||
         type.shadow->blur > 64.f || !std::isfinite(type.shadow->offset.x) ||
         !std::isfinite(type.shadow->offset.y)))
        throw std::invalid_argument(std::string(owner) + ": invalid text shadow");
    if (type.glow &&
        (!validHexColor(type.glow->color) || !std::isfinite(type.glow->radius) ||
         type.glow->radius < 0.f || type.glow->radius > 128.f ||
         !std::isfinite(type.glow->intensity) || type.glow->intensity < 0.f ||
         type.glow->intensity > 1.f))
        throw std::invalid_argument(std::string(owner) + ": invalid text glow");
    if (type.background &&
        (!validHexColor(type.background->color) ||
         !std::isfinite(type.background->opacity) || type.background->opacity < 0.f ||
         type.background->opacity > 1.f || !std::isfinite(type.background->radius) ||
         type.background->radius < 0.f || type.background->radius > 128.f ||
         !std::isfinite(type.background->padding.x) || type.background->padding.x < 0.f ||
         !std::isfinite(type.background->padding.y) || type.background->padding.y < 0.f))
        throw std::invalid_argument(std::string(owner) + ": invalid text background");
}

TextSpec textSpec(const std::string& text, const MapTypography& typography,
                  const std::string& name) {
    return TextSpec{.text = text, .font = typography.font,
                    .fontSize = typography.fontSize, .color = typography.color,
                    .name = name, .stroke = typography.stroke,
                    .shadow = typography.shadow, .glow = typography.glow,
                    .background = typography.background};
}

struct Bounds {
    float minX{0.f};
    float minY{0.f};
    float maxX{0.f};
    float maxY{0.f};
};

Bounds boundsOf(const std::vector<Vector2>& points) {
    Bounds out{points.front().x, points.front().y, points.front().x, points.front().y};
    for (const Vector2& point : points) {
        out.minX = std::min(out.minX, point.x);
        out.minY = std::min(out.minY, point.y);
        out.maxX = std::max(out.maxX, point.x);
        out.maxY = std::max(out.maxY, point.y);
    }
    return out;
}

Vector2 centroidOf(const std::vector<Vector2>& points) {
    double twiceArea = 0.0;
    double x = 0.0;
    double y = 0.0;
    for (std::size_t i = 0; i < points.size(); ++i) {
        const Vector2& a = points[i];
        const Vector2& b = points[(i + 1) % points.size()];
        const double cross = static_cast<double>(a.x) * b.y -
                             static_cast<double>(b.x) * a.y;
        twiceArea += cross;
        x += (static_cast<double>(a.x) + b.x) * cross;
        y += (static_cast<double>(a.y) + b.y) * cross;
    }
    if (std::abs(twiceArea) > 1e-6) {
        const double area = twiceArea * 0.5;
        return Vector2(static_cast<float>(x / (6.0 * area)),
                       static_cast<float>(y / (6.0 * area)));
    }
    // Degenerate/self-intersecting rings still get a deterministic reveal
    // centre rather than a division by zero.
    Vector2 fallback{};
    for (const Vector2& point : points) {
        fallback.x += point.x;
        fallback.y += point.y;
    }
    return Vector2(fallback.x / static_cast<float>(points.size()),
                   fallback.y / static_cast<float>(points.size()));
}

std::vector<Vector2> closedRing(const TacticalFillRegion& region) {
    if (region.points.size() < 3 || region.points.size() > kMaxPoints)
        throw std::invalid_argument("addTacticalFill: each region needs 3..4096 points");
    std::vector<Vector2> points = region.points;
    for (const Vector2& point : points) {
        if (!std::isfinite(point.x) || !std::isfinite(point.y) ||
            std::abs(point.x) > 1e6f || std::abs(point.y) > 1e6f)
            throw std::invalid_argument("addTacticalFill: polygon points must be finite");
    }
    // A caller may hand us a GeoJSON-style closed ring. The path emitter closes
    // it itself, so drop the duplicate last vertex instead of making a zero edge.
    const Vector2& first = points.front();
    const Vector2& last = points.back();
    if (std::abs(first.x - last.x) < 0.001f && std::abs(first.y - last.y) < 0.001f)
        points.pop_back();
    if (points.size() < 3)
        throw std::invalid_argument("addTacticalFill: a region needs at least three distinct points");
    const Bounds bounds = boundsOf(points);
    if (bounds.maxX - bounds.minX < 0.5f || bounds.maxY - bounds.minY < 0.5f)
        throw std::invalid_argument("addTacticalFill: a region has no drawable area");
    return points;
}

void addReveal(LayerHandle& layer, const Vector2& from, const Vector2& to,
               int inFrame, int revealFrames, float fps) {
    const float start = static_cast<float>(inFrame) / fps;
    const float end = static_cast<float>(inFrame + revealFrames) / fps;
    auto& scale = layer.layer().tracks.scale;
    // Never key an exact zero: a singular transform is invalid in the render
    // plan contract. The tiny start still reads as "grown out of the centre".
    scale.add(start, Vector3(0.002f, 0.002f, 1.f), Easing::easeOut());
    scale.add(end, Vector3(1.f, 1.f, 1.f), Easing::easeOut());
    // Scaling pivots on the layer origin, not on the polygon centroid. Moving
    // the origin from the centroid to the bbox corner on the same curve keeps
    // the territory visually anchored while it grows.
    auto& position = layer.layer().tracks.position;
    position.add(start, Vector3(from.x, from.y, 0.f), Easing::easeOut());
    position.add(end, Vector3(to.x, to.y, 0.f), Easing::easeOut());
}

ShapeSpec pathShape(const std::vector<ShapePathCommand>& path,
                    const Vector2& size, const std::string& name) {
    ShapeSpec shape;
    shape.size = size;
    shape.name = name;
    shape.geometry = ShapeGeometry::Path;
    shape.fillRule = ShapeFillRule::NonZero;
    shape.path = path;
    shape.strokeCap = "round";
    shape.strokeJoin = "round";
    return shape;
}

std::vector<ShapePathCommand> localPath(const std::vector<Vector2>& points,
                                        const Vector2& origin) {
    // Shape paths are authored in the layer's top-left local space, unlike
    // image/text content which carries a centred anchor. Keep every point
    // inside [0,size] so the renderer does not clip the territory away.
    std::vector<ShapePathCommand> path;
    path.reserve(points.size() + 2);
    path.push_back(ShapePathCommand::moveTo(points.front().x - origin.x,
                                            points.front().y - origin.y));
    for (std::size_t i = 1; i < points.size(); ++i)
        path.push_back(ShapePathCommand::lineTo(points[i].x - origin.x,
                                                points[i].y - origin.y));
    path.push_back(ShapePathCommand::close());
    return path;
}

Vector2 toScene(const Vector2& canvasPoint, const Vector2& canvas) {
    // TemplateScene positions are canvas-centred: (0,0) is the frame centre.
    // Public specs stay in top-left canvas coordinates, so every authored
    // position crosses this boundary exactly once.
    return Vector2(canvasPoint.x - canvas.x * 0.5f,
                   canvasPoint.y - canvas.y * 0.5f);
}

std::vector<ShapePathCommand> gridPath(const Vector2& canvas, float spacing) {
    // The decoder's Grid primitive generates a path centred on zero, while
    // authored-origin shape layers clip to [0,size]. Author the same grid as
    // a path in 0..size instead, so the full frame survives the layer bbox.
    std::vector<ShapePathCommand> path;
    const int columns = static_cast<int>(std::floor(canvas.x / spacing));
    const int rows = static_cast<int>(std::floor(canvas.y / spacing));
    path.reserve(static_cast<std::size_t>((columns + rows + 2) * 2));
    for (int column = 0; column <= columns; ++column) {
        const float x = std::min(static_cast<float>(column) * spacing, canvas.x);
        path.push_back(ShapePathCommand::moveTo(x, 0.f));
        path.push_back(ShapePathCommand::lineTo(x, canvas.y));
    }
    for (int row = 0; row <= rows; ++row) {
        const float y = std::min(static_cast<float>(row) * spacing, canvas.y);
        path.push_back(ShapePathCommand::moveTo(0.f, y));
        path.push_back(ShapePathCommand::lineTo(canvas.x, y));
    }
    return path;
}

} // namespace

const char* tacticalFillId() noexcept {
    return "territory_tactical_fill";
}

TacticalFillComposition addTacticalFill(TemplateScene& scene,
                                        const TacticalFillSpec& spec) {
    if (spec.regions.empty())
        throw std::invalid_argument("addTacticalFill: at least one territory region is required");
    if (spec.regions.size() > kMaxRegions)
        throw std::invalid_argument("addTacticalFill: too many territory regions");
    if (spec.inFrame < 0 || spec.duration < kMinFrames ||
        spec.inFrame > std::numeric_limits<int>::max() - spec.duration)
        throw std::invalid_argument("addTacticalFill: frame window must be non-negative and at least 24 frames");
    if (!std::isfinite(spec.revealFraction) || spec.revealFraction < 0.1f ||
        spec.revealFraction > 1.f)
        throw std::invalid_argument("addTacticalFill: reveal fraction must be in [0.1,1]");
    if (!std::isfinite(spec.textRevealStart) || !std::isfinite(spec.textRevealEnd) ||
        spec.textRevealStart < 0.f || spec.textRevealEnd > 1.f ||
        spec.textRevealEnd <= spec.textRevealStart)
        throw std::invalid_argument("addTacticalFill: text reveal window must be ordered inside the clip");
    if (!validHexColor(spec.background) || !validHexColor(spec.minorGrid) ||
        !validHexColor(spec.majorGrid) || !validHexColor(spec.fill) ||
        !validHexColor(spec.outline) || !validHexColor(spec.glow) ||
        !validHexColor(spec.innerGlow))
        throw std::invalid_argument("addTacticalFill: every colour must be #RRGGBB");
    if (!std::isfinite(spec.gridSpacing) || spec.gridSpacing < 8.f ||
        spec.gridSpacing > 512.f || spec.majorGridEvery < 1 ||
        spec.majorGridEvery > 8 ||
        spec.gridSpacing * static_cast<float>(spec.majorGridEvery) > 512.f)
        throw std::invalid_argument("addTacticalFill: grid spacing and major interval are outside supported bounds");
    if (!std::isfinite(spec.outlineWidth) || spec.outlineWidth < 0.5f ||
        spec.outlineWidth > 24.f || !std::isfinite(spec.glowWidth) ||
        spec.glowWidth < 1.f || spec.glowWidth > 48.f ||
        !std::isfinite(spec.innerGlowWidth) || spec.innerGlowWidth < 1.f ||
        spec.innerGlowWidth > 32.f || !std::isfinite(spec.glowRadius) ||
        spec.glowRadius < 0.f || spec.glowRadius > 128.f ||
        !std::isfinite(spec.innerGlowRadius) || spec.innerGlowRadius < 0.f ||
        spec.innerGlowRadius > 128.f || !std::isfinite(spec.glowIntensity) ||
        spec.glowIntensity < 0.1f || spec.glowIntensity > 3.f)
        throw std::invalid_argument("addTacticalFill: glow or outline parameters are outside supported bounds");

    if (!spec.title.empty()) validateTypography(spec.titleTypography, "addTacticalFill");
    if (!spec.subtitle.empty()) validateTypography(spec.subtitleTypography, "addTacticalFill");

    const auto canvas = scene.canvas();
    if (!std::isfinite(canvas.x) || !std::isfinite(canvas.y) ||
        canvas.x <= 0.f || canvas.y <= 0.f)
        throw std::invalid_argument("addTacticalFill: canvas must be finite and positive");

    std::vector<std::vector<Vector2>> rings;
    rings.reserve(spec.regions.size());
    for (const TacticalFillRegion& region : spec.regions)
        rings.push_back(closedRing(region));

    // The public window is exclusive; FrameRange is inclusive. Keeping those
    // separate stops a 120-frame plan from authoring a 121st frame.
    const int endFrame = spec.inFrame + spec.duration;
    const int lastFrame = endFrame - 1;
    const int revealFrames = std::min(
        std::max(1, static_cast<int>(std::lround(
            static_cast<double>(spec.duration) * spec.revealFraction))),
        lastFrame - spec.inFrame);
    const int textStart = std::min(
        spec.inFrame + static_cast<int>(std::lround(
            static_cast<double>(spec.duration) * spec.textRevealStart)),
        lastFrame);
    const int textEnd = std::min(
        spec.inFrame + static_cast<int>(std::lround(
            static_cast<double>(spec.duration) * spec.textRevealEnd)),
        lastFrame);
    const int textFade = std::max(1, textEnd - textStart);
    const float fps = scene.fps();

    TacticalFillComposition result;
    result.inFrame = spec.inFrame;
    result.endFrame = endFrame;

    ShapeSpec background;
    background.size = canvas;
    background.fillColor = spec.background;
    background.name = "tactical_fill_background";
    LayerHandle& backgroundLayer = scene.shape(background);
    backgroundLayer.position(0.f, 0.f).alive(spec.inFrame, lastFrame);
    result.background = &backgroundLayer;

    const Vector2 canvasOrigin = toScene(Vector2(0.f, 0.f), canvas);

    ShapeSpec minor;
    minor.size = canvas;
    minor.fillEnabled = false;
    minor.geometry = ShapeGeometry::Path;
    minor.path = gridPath(canvas, spec.gridSpacing);
    minor.strokeColor = spec.minorGrid;
    minor.strokeWidth = 1.f;
    minor.strokeCap = "butt";
    minor.strokeJoin = "miter";
    minor.name = "tactical_fill_grid_minor";
    LayerHandle& minorLayer = scene.shape(minor);
    minorLayer.position(canvasOrigin.x, canvasOrigin.y).alive(spec.inFrame, lastFrame);
    result.minorGrid = &minorLayer;

    ShapeSpec major;
    major.size = canvas;
    major.fillEnabled = false;
    major.geometry = ShapeGeometry::Path;
    major.path = gridPath(canvas, spec.gridSpacing * static_cast<float>(spec.majorGridEvery));
    major.strokeColor = spec.majorGrid;
    major.strokeWidth = 1.f;
    major.strokeCap = "butt";
    major.strokeJoin = "miter";
    major.name = "tactical_fill_grid_major";
    LayerHandle& majorLayer = scene.shape(major);
    majorLayer.position(canvasOrigin.x, canvasOrigin.y).alive(spec.inFrame, lastFrame);
    result.majorGrid = &majorLayer;

    for (std::size_t index = 0; index < rings.size(); ++index) {
        const auto& points = rings[index];
        const Bounds bounds = boundsOf(points);
        const Vector2 bboxCenter((bounds.minX + bounds.maxX) * 0.5f,
                                 (bounds.minY + bounds.maxY) * 0.5f);
        const Vector2 centroid = centroidOf(points);
        const Vector2 size(bounds.maxX - bounds.minX + kPathPadding * 2.f,
                           bounds.maxY - bounds.minY + kPathPadding * 2.f);
        const Vector2 origin(bounds.minX - kPathPadding, bounds.minY - kPathPadding);
        // RenderPlan cannot carry a transformed anchor offset. A null
        // controller at the centroid is the representable way to make the
        // territory grow from its actual centroid instead of its bbox centre.
        const Vector2 sceneOrigin = toScene(origin, canvas);
        const Vector2 sceneCentroid = toScene(centroid, canvas);
        const auto path = localPath(points, origin);
        const std::string suffix = "_" + std::to_string(index);

        ShapeSpec outer = pathShape(path, size, "tactical_fill_territory" + suffix + "_outer_glow");
        outer.fillColor = spec.glow;
        outer.fillEnabled = false;
        outer.strokeColor = spec.glow;
        outer.strokeWidth = spec.glowWidth;
        outer.glowColor = spec.glow;
        outer.glowRadius = spec.glowRadius;
        outer.glowIntensity = spec.glowIntensity;
        LayerHandle& outerLayer = scene.shape(outer);
        outerLayer.position(sceneOrigin.x, sceneOrigin.y)
            .alive(spec.inFrame, lastFrame)
            .opacity(0.92f);
        addReveal(outerLayer, sceneCentroid, sceneOrigin,
                  spec.inFrame, revealFrames, fps);

        ShapeSpec inner = pathShape(path, size, "tactical_fill_territory" + suffix + "_inner_glow");
        inner.fillColor = spec.innerGlow;
        inner.fillEnabled = false;
        inner.strokeColor = spec.innerGlow;
        inner.strokeWidth = spec.innerGlowWidth;
        inner.glowColor = spec.innerGlow;
        inner.glowRadius = spec.innerGlowRadius;
        inner.glowIntensity = spec.glowIntensity * 0.72f;
        LayerHandle& innerLayer = scene.shape(inner);
        innerLayer.position(sceneOrigin.x, sceneOrigin.y)
            .alive(spec.inFrame, lastFrame);
        addReveal(innerLayer, sceneCentroid, sceneOrigin,
                  spec.inFrame, revealFrames, fps);

        ShapeSpec fill = pathShape(path, size, "tactical_fill_territory" + suffix + "_fill");
        fill.fillColor = spec.fill;
        fill.fillEnabled = true;
        fill.strokeColor = spec.outline;
        fill.strokeWidth = spec.outlineWidth;
        LayerHandle& fillLayer = scene.shape(fill);
        fillLayer.position(sceneOrigin.x, sceneOrigin.y)
            .alive(spec.inFrame, lastFrame);
        addReveal(fillLayer, sceneCentroid, sceneOrigin,
                  spec.inFrame, revealFrames, fps);

        result.territories.push_back(
            TacticalFillTerritory{&outerLayer, &innerLayer, &fillLayer});
    }

    const Vector2 titlePosition = spec.titlePosition.value_or(
        Vector2(canvas.x * 0.16f, canvas.y * 0.48f));
    const Vector2 subtitlePosition = spec.subtitlePosition.value_or(
        Vector2(canvas.x * 0.15f, titlePosition.y + 48.f));
    for (const Vector2& position : {titlePosition, subtitlePosition}) {
        if (!std::isfinite(position.x) || !std::isfinite(position.y))
            throw std::invalid_argument("addTacticalFill: text positions must be finite");
    }

    const Vector2 titleScene = toScene(titlePosition, canvas);
    const Vector2 subtitleScene = toScene(subtitlePosition, canvas);
    if (!spec.title.empty()) {
        LayerHandle& title = scene.text(textSpec(spec.title, spec.titleTypography,
                                                 "tactical_fill_title"));
        title.position(titleScene.x, titleScene.y)
            .alive(spec.inFrame, lastFrame)
            .animate(FadeIn{.inFrame = textStart, .duration = textFade});
        result.title = &title;
    }
    if (!spec.subtitle.empty()) {
        LayerHandle& subtitle = scene.text(textSpec(spec.subtitle, spec.subtitleTypography,
                                                    "tactical_fill_subtitle"));
        subtitle.position(subtitleScene.x, subtitleScene.y)
            .alive(spec.inFrame, lastFrame)
            .animate(FadeIn{.inFrame = textStart, .duration = textFade});
        result.subtitle = &subtitle;
    }

    return result;
}

} // namespace chronontemplate
