#include "chronontemplate/map/MapFxPack.hpp"

#include "chrononmotion/motion/Easing.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

namespace chronontemplate {
namespace {

using chrononmotion::Vector2;
using chrononmotion::Vector3;
using chrononmotion::motion::Easing;

constexpr int kMinFxFrames = 18;
constexpr int kMaxAnchors = 8;

bool validHexColor(const std::string& color) {
    if (color.size() != 7 || color.front() != '#') return false;
    return std::all_of(color.begin() + 1, color.end(),
                       [](unsigned char c) { return std::isxdigit(c) != 0; });
}

void validateSpec(const MapFxSpec& spec) {
    if (!std::isfinite(spec.intensity) || spec.intensity < 0.05f || spec.intensity > 2.f)
        throw std::invalid_argument("addMapFx: intensity must be in [0.05, 2]");
    if (!std::isfinite(spec.radius) || spec.radius < 8.f || spec.radius > 600.f)
        throw std::invalid_argument("addMapFx: radius must be in [8, 600]");
    if (!std::isfinite(spec.ringWidth) || spec.ringWidth < 0.5f || spec.ringWidth > 24.f)
        throw std::invalid_argument("addMapFx: ring width must be in [0.5, 24]");
    if (spec.ringCount < 1 || spec.ringCount > 6)
        throw std::invalid_argument("addMapFx: ring count must be in [1, 6]");
    if (!validHexColor(spec.accent) || !validHexColor(spec.secondary))
        throw std::invalid_argument("addMapFx: accent and secondary must be #RRGGBB colors");
}

void validateAnchors(MapFxKind kind, const std::vector<Vector2>& anchors, const Vector2& canvas) {
    const std::size_t minimum = kind == MapFxKind::CityNetworkExpansion ? 2u : 1u;
    const std::size_t maximum = kind == MapFxKind::CityNetworkExpansion ? kMaxAnchors : 1u;
    if (anchors.size() < minimum || anchors.size() > maximum)
        throw std::invalid_argument(std::string("addMapFx: ") + mapFxId(kind) +
                                    (minimum == maximum ? " requires exactly one anchor"
                                                        : " requires 2..8 anchors"));
    for (const Vector2& anchor : anchors) {
        if (!std::isfinite(anchor.x) || !std::isfinite(anchor.y) ||
            anchor.x < 0.f || anchor.y < 0.f || anchor.x > canvas.x || anchor.y > canvas.y)
            throw std::invalid_argument("addMapFx: anchors must be finite and inside the canvas");
    }
}

float clamp01(float value) {
    return std::max(0.f, std::min(1.f, value));
}

// start/duration are in frames; the tracks use seconds, like every other pack.
void addPulse(LayerHandle& layer, float fps, int start, int duration,
              float fromScale, float toScale, float peakOpacity) {
    const float t0 = static_cast<float>(start) / fps;
    const float t1 = static_cast<float>(start + std::max(1, duration)) / fps;
    auto& scale = layer.layer().tracks.scale;
    scale.add(t0, Vector3(fromScale, fromScale, 1.f), Easing::easeOut());
    scale.add(t1, Vector3(toScale, toScale, 1.f), Easing::easeOut());

    auto& opacity = layer.layer().tracks.opacity;
    opacity.add(t0, 0.f, Easing::easeOut());
    opacity.add(static_cast<float>(start + std::min(2, duration)) / fps,
                clamp01(peakOpacity), Easing::easeOut());
    opacity.add(t1, 0.f, Easing::easeOut());
}

LayerHandle& ring(TemplateScene& scene, const std::string& name, Vector2 center, float diameter,
                  const MapFxSpec& spec, int inFrame, int outFrame) {
    ShapeSpec shape;
    shape.size = Vector2(diameter, diameter);
    shape.fillColor = spec.accent;
    shape.name = name;
    shape.fillEnabled = false;
    shape.geometry = ShapeGeometry::Ellipse;
    shape.strokeColor = spec.accent;
    shape.strokeWidth = spec.ringWidth;
    shape.glowColor = spec.accent;
    shape.glowRadius = 12.f * clamp01(spec.intensity);
    shape.glowIntensity = 0.55f * clamp01(spec.intensity);
    LayerHandle& layer = scene.shape(shape);
    layer.position(center.x, center.y).alive(inFrame, outFrame);
    return layer;
}

LayerHandle& softGlow(TemplateScene& scene, const std::string& name, Vector2 center, float diameter,
                      const MapFxSpec& spec, int inFrame, int outFrame, float opacity) {
    ShapeSpec shape;
    shape.size = Vector2(diameter, diameter);
    shape.fillColor = spec.accent;
    shape.name = name;
    shape.geometry = ShapeGeometry::Ellipse;
    shape.glowColor = spec.accent;
    shape.glowRadius = 20.f * clamp01(spec.intensity);
    shape.glowIntensity = 0.35f * clamp01(spec.intensity);
    shape.radialGradient = ShapeRadialGradient{
        .center = Vector2(0.5f, 0.5f),
        .radius = 0.5f,
        .stops = {
            ShapeGradientStop{0.f, spec.accent, clamp01(opacity)},
            ShapeGradientStop{0.55f, spec.accent, clamp01(opacity * 0.35f)},
            ShapeGradientStop{1.f, spec.accent, 0.f},
        },
    };
    LayerHandle& layer = scene.shape(shape);
    layer.position(center.x, center.y).alive(inFrame, outFrame).opacity(clamp01(opacity));
    return layer;
}

void addFadeOut(LayerHandle& layer, float fps, int outFrame, int frames, float from) {
    auto& opacity = layer.layer().tracks.opacity;
    opacity.add(static_cast<float>(outFrame - frames) / fps, from, Easing::easeInOut());
    opacity.add(static_cast<float>(outFrame) / fps, 0.f, Easing::easeInOut());
}

void addAreaGlowPulse(TemplateScene& scene, const MapFxSpec& spec,
                      const std::vector<Vector2>& anchors, int start, int end, float fps,
                      MapFxComposition& out) {
    const Vector2 center = anchors.front();
    LayerHandle& glow = softGlow(scene, "map_fx_area_glow", center, spec.radius * 2.6f,
                                 spec, start, end, 0.42f * spec.intensity);
    addFadeOut(glow, fps, end, std::max(6, (end - start) / 6), 0.42f * spec.intensity);
    out.layers.push_back(&glow);

    const int stagger = std::max(1, (end - start) / std::max(1, spec.ringCount * 2));
    for (int index = 0; index < spec.ringCount; ++index) {
        const int ringStart = start + index * stagger;
        const int pulseEnd = std::min(end, ringStart + std::max(kMinFxFrames, (end - start) / 2));
        if (pulseEnd <= ringStart) break;
        LayerHandle& layer = ring(scene, "map_fx_area_ring_" + std::to_string(index), center,
                                  spec.radius * 2.f, spec, ringStart, end);
        addPulse(layer, fps, ringStart, pulseEnd - ringStart, 0.55f, 1.55f,
                 0.62f * spec.intensity);
        out.layers.push_back(&layer);
    }
}

void addRadarLocationReveal(TemplateScene& scene, const MapFxSpec& spec,
                            const std::vector<Vector2>& anchors, int start, int end, float fps,
                            MapFxComposition& out) {
    const Vector2 center = anchors.front();
    LayerHandle& glow = softGlow(scene, "map_fx_radar_glow", center, spec.radius * 2.4f,
                                 spec, start, end, 0.30f * spec.intensity);
    addFadeOut(glow, fps, end, std::max(6, (end - start) / 6), 0.30f * spec.intensity);
    out.layers.push_back(&glow);

    const int stagger = std::max(1, (end - start) / std::max(2, spec.ringCount * 3));
    for (int index = 0; index < spec.ringCount; ++index) {
        const int ringStart = start + index * stagger;
        const int pulseEnd = std::min(end, ringStart + std::max(kMinFxFrames, (end - start) / 2));
        if (pulseEnd <= ringStart) break;
        LayerHandle& layer = ring(scene, "map_fx_radar_ring_" + std::to_string(index), center,
                                  spec.radius * 2.f, spec, ringStart, end);
        addPulse(layer, fps, ringStart, pulseEnd - ringStart, 0.22f, 1.6f,
                 0.55f * spec.intensity);
        out.layers.push_back(&layer);
    }

    ShapeSpec horizontal;
    horizontal.size = Vector2(spec.radius * 2.f, std::max(1.f, spec.ringWidth * 0.8f));
    horizontal.fillColor = spec.accent;
    horizontal.name = "map_fx_radar_crosshair_x";
    horizontal.cornerRadius = horizontal.size.y * 0.5f;
    horizontal.glowColor = spec.accent;
    horizontal.glowRadius = 10.f * clamp01(spec.intensity);
    horizontal.glowIntensity = 0.4f * clamp01(spec.intensity);
    LayerHandle& crossX = scene.shape(horizontal);
    crossX.position(center.x, center.y).alive(start, end)
          .animate(FadeIn{.inFrame = start, .duration = std::max(2, (end - start) / 12)});
    addFadeOut(crossX, fps, end, std::max(6, (end - start) / 8), 1.f);
    out.layers.push_back(&crossX);

    ShapeSpec vertical = horizontal;
    vertical.size = Vector2(std::max(1.f, spec.ringWidth * 0.8f), spec.radius * 2.f);
    vertical.name = "map_fx_radar_crosshair_y";
    vertical.cornerRadius = vertical.size.x * 0.5f;
    LayerHandle& crossY = scene.shape(vertical);
    crossY.position(center.x, center.y).alive(start, end)
          .animate(FadeIn{.inFrame = start, .duration = std::max(2, (end - start) / 12)});
    addFadeOut(crossY, fps, end, std::max(6, (end - start) / 8), 1.f);
    out.layers.push_back(&crossY);

    ShapeSpec dot;
    dot.size = Vector2(std::max(6.f, spec.radius * 0.22f), std::max(6.f, spec.radius * 0.22f));
    dot.fillColor = spec.secondary;
    dot.name = "map_fx_radar_dot";
    dot.geometry = ShapeGeometry::Ellipse;
    dot.glowColor = spec.secondary;
    dot.glowRadius = 18.f * clamp01(spec.intensity);
    dot.glowIntensity = 0.7f * clamp01(spec.intensity);
    LayerHandle& centerDot = scene.shape(dot);
    centerDot.position(center.x, center.y).alive(start, end)
             .animate(ScalePop{.inFrame = start, .duration = std::max(4, (end - start) / 6),
                               .from = 0.2f, .to = 1.f})
             .animate(FadeIn{.inFrame = start, .duration = std::max(2, (end - start) / 12)});
    addFadeOut(centerDot, fps, end, std::max(6, (end - start) / 8), 1.f);
    out.layers.push_back(&centerDot);
}

void addLightBeamDrop(TemplateScene& scene, const MapFxSpec& spec,
                      const std::vector<Vector2>& anchors, int start, int end, float fps,
                      MapFxComposition& out) {
    const Vector2 center = anchors.front();
    const float height = std::max(80.f, spec.radius * 2.f);
    const int dropFrames = std::min(std::max(8, (end - start) / 5), 24);

    ShapeSpec beam;
    beam.size = Vector2(std::max(2.f, spec.ringWidth * 1.4f), height);
    beam.fillColor = spec.accent;
    beam.name = "map_fx_energy_beam";
    beam.cornerRadius = beam.size.x * 0.5f;
    beam.glowColor = spec.accent;
    beam.glowRadius = 16.f * clamp01(spec.intensity);
    beam.glowIntensity = 0.8f * clamp01(spec.intensity);
    LayerHandle& beamLayer = scene.shape(beam);
    beamLayer.position(center.x, center.y + height * 0.5f).alive(start, end)
             .animatePosition(start, dropFrames, Vector3(0.f, height, 0.f), Easing::easeOut())
             .animateOpacity(start, std::max(2, dropFrames / 2), 0.f, 0.9f);
    addFadeOut(beamLayer, fps, end, std::max(6, (end - start) / 8), 0.9f);
    out.layers.push_back(&beamLayer);

    const int impact = std::min(end - 2, start + dropFrames);
    ShapeSpec dot;
    dot.size = Vector2(18.f, 18.f);
    dot.fillColor = spec.secondary;
    dot.name = "map_fx_beam_impact";
    dot.geometry = ShapeGeometry::Ellipse;
    dot.glowColor = spec.secondary;
    dot.glowRadius = 22.f * clamp01(spec.intensity);
    dot.glowIntensity = 0.9f * clamp01(spec.intensity);
    LayerHandle& impactDot = scene.shape(dot);
    impactDot.position(center.x, center.y).alive(impact, end)
             .animate(ScalePop{.inFrame = impact, .duration = 14, .from = 0.15f, .to = 1.f})
             .animate(FadeIn{.inFrame = impact, .duration = 4});
    addFadeOut(impactDot, fps, end, std::max(6, (end - start) / 8), 1.f);
    out.layers.push_back(&impactDot);

    LayerHandle& impactRing = ring(scene, "map_fx_beam_ring", center, spec.radius * 1.25f,
                                   spec, impact, end);
    addPulse(impactRing, fps, impact, std::max(kMinFxFrames, end - impact), 0.3f, 1.45f,
             0.5f * spec.intensity);
    out.layers.push_back(&impactRing);
}

void addCityNetworkExpansion(TemplateScene& scene, const MapFxSpec& spec,
                             const std::vector<Vector2>& anchors, int start, int end, float fps,
                             MapFxComposition& out) {
    const int segmentCount = static_cast<int>(anchors.size()) - 1;
    const int step = std::max(1, (end - start) / std::max(1, segmentCount));
    // The last node may be scheduled at the very end of the effect. Its pop
    // must fit inside the layer lifetime, otherwise the motion track extends
    // the whole composition past the map's declared duration.
    const int nodeDuration = std::min(std::max(6, step / 2), end - start);

    for (std::size_t index = 0; index < anchors.size(); ++index) {
        ShapeSpec dot;
        dot.size = Vector2(16.f, 16.f);
        dot.fillColor = spec.accent;
        dot.name = "map_fx_network_node_" + std::to_string(index);
        dot.geometry = ShapeGeometry::Ellipse;
        dot.glowColor = spec.accent;
        dot.glowRadius = 16.f * clamp01(spec.intensity);
        dot.glowIntensity = 0.8f * clamp01(spec.intensity);
        int nodeStart = start + static_cast<int>(index) * step;
        if (nodeStart + nodeDuration > end) nodeStart = end - nodeDuration;
        nodeStart = std::max(start, nodeStart);
        const int nodeLife = end - nodeStart;
        if (nodeLife <= 0) continue;
        LayerHandle& node = scene.shape(dot);
        node.position(anchors[index].x, anchors[index].y).alive(nodeStart, end)
            .animate(ScalePop{.inFrame = nodeStart, .duration = std::min(nodeDuration, nodeLife),
                               .from = 0.2f, .to = 1.f})
            .animate(FadeIn{.inFrame = nodeStart, .duration = std::max(2, nodeLife / 4)});
        addFadeOut(node, fps, end, std::max(6, (end - start) / 8), 1.f);
        out.layers.push_back(&node);
    }

    for (int index = 0; index < segmentCount; ++index) {
        const Vector2 from = anchors[static_cast<std::size_t>(index)];
        const Vector2 to = anchors[static_cast<std::size_t>(index) + 1];
        const Vector2 middle((from.x + to.x) * 0.5f, (from.y + to.y) * 0.5f);
        const Vector2 delta(to.x - from.x, to.y - from.y);
        const int segmentStart = start + index * step;
        const int segmentEnd = std::min(end, segmentStart + std::max(10, step));
        if (segmentEnd <= segmentStart) break;

        ShapeSpec path;
        path.size = Vector2(std::max(2.f, std::abs(delta.x)), std::max(2.f, std::abs(delta.y)));
        path.fillColor = spec.accent;
        path.name = "map_fx_network_link_" + std::to_string(index);
        path.fillEnabled = false;
        path.geometry = ShapeGeometry::Path;
        path.strokeColor = spec.accent;
        path.strokeWidth = spec.ringWidth;
        path.strokeCap = "round";
        path.glowColor = spec.accent;
        path.glowRadius = 10.f * clamp01(spec.intensity);
        path.glowIntensity = 0.45f * clamp01(spec.intensity);
        path.path = {
            ShapePathCommand::moveTo(from.x - middle.x, from.y - middle.y),
            ShapePathCommand::lineTo(to.x - middle.x, to.y - middle.y),
        };
        path.trim = ShapeTrimSpec{
            .start = 0.f,
            .end = 0.02f,
            .offset = 0.f,
            .easing = "in_out_cubic",
            .keyframes = {
                ShapeTrimKeyframe{0, 0.f, 0.02f, 0.f},
                ShapeTrimKeyframe{segmentEnd - segmentStart, 0.f, 1.f, 0.f},
            },
        };
        LayerHandle& link = scene.shape(path);
        link.position(middle.x, middle.y).alive(segmentStart, end);
        out.layers.push_back(&link);
    }
}

} // namespace

const char* mapFxId(MapFxKind kind) noexcept {
    switch (kind) {
        case MapFxKind::AreaGlowPulse: return "area_glow_pulse";
        case MapFxKind::RadarLocationReveal: return "radar_location_reveal";
        case MapFxKind::LightBeamDrop: return "light_beam_drop";
        case MapFxKind::CityNetworkExpansion: return "city_network_expansion";
    }
    return "unknown";
}

std::vector<MapFxKind> mapFxKinds() {
    return {MapFxKind::AreaGlowPulse, MapFxKind::RadarLocationReveal,
            MapFxKind::LightBeamDrop, MapFxKind::CityNetworkExpansion};
}

MapFxKind mapFxKindFromId(const std::string& id) {
    for (const MapFxKind kind : mapFxKinds()) {
        if (id == mapFxId(kind)) return kind;
    }
    throw std::invalid_argument("mapFxKindFromId: unknown map fx id \"" + id + "\"");
}

const char* mapFxAnchorPolicy(MapFxKind kind) noexcept {
    switch (kind) {
        case MapFxKind::CityNetworkExpansion: return "2..8";
        case MapFxKind::AreaGlowPulse:
        case MapFxKind::RadarLocationReveal:
        case MapFxKind::LightBeamDrop: return "1";
    }
    return "unknown";
}

MapFxComposition addMapFx(TemplateScene& scene, const MapFxSpec& spec,
                          const std::vector<Vector2>& anchors, int baseInFrame, int baseDuration) {
    if (baseInFrame < 0 || baseDuration <= 0 ||
        baseInFrame > std::numeric_limits<int>::max() - baseDuration)
        throw std::invalid_argument("addMapFx: base frame window must be positive and non-negative");
    if (spec.delayFrames < 0 || spec.delayFrames >= baseDuration)
        throw std::invalid_argument("addMapFx: delay must fall inside the map window");
    validateSpec(spec);
    validateAnchors(spec.kind, anchors, scene.canvas());

    const int start = baseInFrame + spec.delayFrames;
    const int available = baseDuration - spec.delayFrames;
    const int duration = spec.durationFrames > 0 ? spec.durationFrames : available;
    if (duration < kMinFxFrames || duration > available)
        throw std::invalid_argument("addMapFx: duration must be at least 18 frames and fit the map window");
    const int end = start + duration;

    MapFxComposition composition;
    composition.inFrame = start;
    composition.endFrame = end;
    const float fps = scene.fps();
    switch (spec.kind) {
        case MapFxKind::AreaGlowPulse:
            addAreaGlowPulse(scene, spec, anchors, start, end, fps, composition);
            break;
        case MapFxKind::RadarLocationReveal:
            addRadarLocationReveal(scene, spec, anchors, start, end, fps, composition);
            break;
        case MapFxKind::LightBeamDrop:
            addLightBeamDrop(scene, spec, anchors, start, end, fps, composition);
            break;
        case MapFxKind::CityNetworkExpansion:
            addCityNetworkExpansion(scene, spec, anchors, start, end, fps, composition);
            break;
    }
    return composition;
}

} // namespace chronontemplate
