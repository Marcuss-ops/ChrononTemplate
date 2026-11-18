#include "chronontemplate/map/EditorialMapPack.hpp"

#include "chrononmotion/motion/Easing.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace chronontemplate {
namespace {

using chrononmotion::Vector2;
using chrononmotion::Vector3;
using chrononmotion::motion::Easing;
using Json = nlohmann::json;

constexpr std::size_t kMaxRings = 20000;
constexpr std::size_t kMaxPoints = 200000;
constexpr float kPathPadding = 2.f;

bool validHexColor(const std::string& color) {
    if (color.size() != 7 || color.front() != '#') return false;
    return std::all_of(color.begin() + 1, color.end(), [](unsigned char c) {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
               (c >= 'A' && c <= 'F');
    });
}

std::string colorOr(const std::string& color, const char* fallback) {
    return validHexColor(color) ? color : std::string(fallback);
}

float readFloat(const Json& object, const char* key, float fallback = 0.f) {
    const auto found = object.find(key);
    if (found == object.end() || found->is_null()) return fallback;
    if (!found->is_number()) throw std::invalid_argument(std::string("field '") + key + "' must be a number");
    return found->get<float>();
}

std::string readString(const Json& object, const char* key, const std::string& fallback = {}) {
    const auto found = object.find(key);
    if (found == object.end() || found->is_null()) return fallback;
    if (!found->is_string()) throw std::invalid_argument(std::string("field '") + key + "' must be a string");
    return found->get<std::string>();
}

EditorialMapPoint readPoint(const Json& value) {
    if (!value.is_array() || value.size() != 2 || !value[0].is_number() ||
        !value[1].is_number())
        throw std::invalid_argument("editorial map point must be [x, y] numbers");
    return {value[0].get<float>(), value[1].get<float>()};
}

std::vector<EditorialMapRing> readRings(const Json& value) {
    if (!value.is_array()) throw std::invalid_argument("editorial ring list must be an array");
    std::vector<EditorialMapRing> rings;
    for (const Json& ringValue : value) {
        if (!ringValue.is_array() || ringValue.size() < 3)
            throw std::invalid_argument("editorial ring must contain at least three points");
        EditorialMapRing ring;
        ring.points.reserve(ringValue.size());
        for (const Json& point : ringValue) ring.points.push_back(readPoint(point));
        rings.push_back(std::move(ring));
    }
    return rings;
}

std::vector<EditorialMapPolygon> readPolygons(const Json& value) {
    if (!value.is_array()) throw std::invalid_argument("editorial polygon list must be an array");
    std::vector<EditorialMapPolygon> polygons;
    for (const Json& polygonValue : value) {
        EditorialMapPolygon polygon;
        polygon.rings = readRings(polygonValue);
        polygons.push_back(std::move(polygon));
    }
    return polygons;
}

std::vector<EditorialMapFeature> readFeatures(const Json& value) {
    if (!value.is_array()) throw std::invalid_argument("editorial feature list must be an array");
    std::vector<EditorialMapFeature> features;
    for (const Json& featureValue : value) {
        if (!featureValue.is_object() || !featureValue.contains("polygons"))
            throw std::invalid_argument("editorial feature must be an object with polygons");
        EditorialMapFeature feature;
        feature.polygons = readPolygons(featureValue["polygons"]);
        features.push_back(std::move(feature));
    }
    return features;
}

std::vector<EditorialMapSegment> readSegments(const Json& value) {
    if (!value.is_array()) throw std::invalid_argument("editorial segment list must be an array");
    std::vector<EditorialMapSegment> segments;
    for (const Json& segmentValue : value) {
        if (!segmentValue.is_array() || segmentValue.size() != 2)
            throw std::invalid_argument("editorial segment must be a pair of points");
        EditorialMapSegment segment;
        segment.from = readPoint(segmentValue[0]);
        segment.to = readPoint(segmentValue[1]);
        segments.push_back(std::move(segment));
    }
    return segments;
}

std::vector<EditorialMapSegment> readAccents(const Json& value) {
    if (!value.is_array()) throw std::invalid_argument("editorial accent list must be an array");
    std::vector<EditorialMapSegment> segments;
    for (const Json& segmentValue : value) {
        if (!segmentValue.is_object())
            throw std::invalid_argument("editorial accent must be an object");
        EditorialMapSegment segment;
        segment.from = readPoint(segmentValue.at("from"));
        segment.to = readPoint(segmentValue.at("to"));
        segment.color = readString(segmentValue, "color", "#FFFFFF");
        segment.width = readFloat(segmentValue, "width", 1.f);
        segments.push_back(std::move(segment));
    }
    return segments;
}

std::vector<EditorialMapFrame> readFrames(const Json& value) {
    if (!value.is_array()) throw std::invalid_argument("editorial frame list must be an array");
    std::vector<EditorialMapFrame> frames;
    for (const Json& frameValue : value) {
        if (!frameValue.is_object()) throw std::invalid_argument("editorial frame must be an object");
        EditorialMapFrame frame;
        frame.x = readFloat(frameValue, "x");
        frame.y = readFloat(frameValue, "y");
        frame.width = readFloat(frameValue, "width");
        frame.height = readFloat(frameValue, "height");
        frame.fill = readString(frameValue, "fill");
        frame.stroke = readString(frameValue, "stroke");
        frame.strokeWidth = readFloat(frameValue, "stroke_width", 1.f);
        frames.push_back(std::move(frame));
    }
    return frames;
}

std::vector<EditorialMapPin> readPins(const Json& value) {
    if (!value.is_array()) throw std::invalid_argument("editorial pin list must be an array");
    std::vector<EditorialMapPin> pins;
    for (const Json& pinValue : value) {
        if (!pinValue.is_object()) throw std::invalid_argument("editorial pin must be an object");
        EditorialMapPin pin;
        pin.x = readFloat(pinValue, "x");
        pin.y = readFloat(pinValue, "y");
        pin.labelX = readFloat(pinValue, "label_x", pin.x);
        pin.labelY = readFloat(pinValue, "label_y", pin.y);
        pin.radius = readFloat(pinValue, "radius", 8.f);
        pin.label = readString(pinValue, "label");
        pin.fill = readString(pinValue, "fill", "#FFFFFF");
        pin.ring = readString(pinValue, "ring", "#FFFFFF");
        pin.style = readString(pinValue, "style", "dot");
        pins.push_back(std::move(pin));
    }
    return pins;
}

std::vector<EditorialMapLabel> readLabels(const Json& value) {
    if (!value.is_array()) throw std::invalid_argument("editorial label list must be an array");
    std::vector<EditorialMapLabel> labels;
    for (const Json& labelValue : value) {
        if (!labelValue.is_object()) throw std::invalid_argument("editorial label must be an object");
        EditorialMapLabel label;
        label.text = readString(labelValue, "text");
        label.font = readString(labelValue, "font", "sans_regular");
        label.color = readString(labelValue, "color", "#FFFFFF");
        label.align = readString(labelValue, "align", "left");
        label.stroke = readString(labelValue, "stroke");
        label.role = readString(labelValue, "role", "data");
        label.x = readFloat(labelValue, "x");
        label.y = readFloat(labelValue, "y");
        label.width = readFloat(labelValue, "width", 0.f);
        label.size = readFloat(labelValue, "size", 16.f);
        label.opacity = readFloat(labelValue, "opacity", 1.f);
        label.strokeWidth = readFloat(labelValue, "stroke_width", 0.f);
        label.tracking = static_cast<int>(readFloat(labelValue, "tracking", 0.f));
        labels.push_back(std::move(label));
    }
    return labels;
}

EditorialMapPalette readPalette(const Json& value) {
    if (!value.is_object()) throw std::invalid_argument("editorial palette must be an object");
    EditorialMapPalette palette;
    palette.background = readString(value, "background");
    palette.accent = readString(value, "accent");
    palette.ink = readString(value, "ink");
    palette.muted = readString(value, "muted");
    palette.paper = readString(value, "paper");
    palette.countriesFill = readString(value, "countries_fill");
    palette.countriesStroke = readString(value, "countries_stroke");
    palette.statesFill = readString(value, "states_fill");
    palette.statesStroke = readString(value, "states_stroke");
    palette.highlightFill = readString(value, "highlight_fill");
    palette.highlightStroke = readString(value, "highlight_stroke");
    palette.grid = readString(value, "grid");
    palette.hatch = readString(value, "hatch");
    palette.panelFill = readString(value, "panel_fill");
    palette.panelStroke = readString(value, "panel_stroke");
    palette.shadow = readString(value, "shadow");
    return palette;
}

std::optional<EditorialMapArc> readArc(const Json& value) {
    if (value.is_null()) return std::nullopt;
    if (!value.is_object()) throw std::invalid_argument("editorial arc must be an object or null");
    EditorialMapArc arc;
    arc.from = readPoint(value.at("from"));
    arc.to = readPoint(value.at("to"));
    arc.control1 = readPoint(value.at("control1"));
    arc.control2 = readPoint(value.at("control2"));
    arc.distanceText = readString(value, "distance_text");
    arc.distanceX = readFloat(value, "distance_x");
    arc.distanceY = readFloat(value, "distance_y");
    return arc;
}

std::optional<EditorialMapLeader> readLeader(const Json& value) {
    if (value.is_null()) return std::nullopt;
    if (!value.is_object() || !value.contains("points") || !value["points"].is_array())
        throw std::invalid_argument("editorial leader must be an object with points");
    EditorialMapLeader leader;
    for (const Json& point : value["points"]) leader.points.push_back(readPoint(point));
    leader.anchorRadius = readFloat(value, "anchor_radius", 4.f);
    return leader;
}

std::optional<EditorialMapRadar> readRadar(const Json& value) {
    if (value.is_null()) return std::nullopt;
    if (!value.is_object()) throw std::invalid_argument("editorial radar must be an object or null");
    EditorialMapRadar radar;
    radar.x = readFloat(value, "x");
    radar.y = readFloat(value, "y");
    radar.maxRadius = readFloat(value, "max_radius", 160.f);
    radar.color = readString(value, "color", "#38BDF8");
    return radar;
}

std::optional<EditorialMapShadow> readShadow(const Json& value) {
    if (value.is_null()) return std::nullopt;
    if (!value.is_object()) throw std::invalid_argument("editorial shadow must be an object or null");
    EditorialMapShadow shadow;
    const auto offset = value.find("offset");
    if (offset != value.end()) {
        if (!offset->is_array() || offset->size() != 2)
            throw std::invalid_argument("editorial shadow offset must be [x, y]");
        shadow.offsetX = (*offset)[0].get<float>();
        shadow.offsetY = (*offset)[1].get<float>();
    }
    shadow.blur = readFloat(value, "blur", 0.f);
    shadow.opacity = readFloat(value, "opacity", 0.f);
    shadow.scale = readFloat(value, "scale", 1.f);
    shadow.color = readString(value, "color");
    return shadow;
}

// ── Lowering helpers ────────────────────────────────────────────────────────

struct Bounds {
    float minX{std::numeric_limits<float>::max()};
    float minY{std::numeric_limits<float>::max()};
    float maxX{std::numeric_limits<float>::lowest()};
    float maxY{std::numeric_limits<float>::lowest()};

    void add(const Vector2& point) {
        minX = std::min(minX, point.x);
        minY = std::min(minY, point.y);
        maxX = std::max(maxX, point.x);
        maxY = std::max(maxY, point.y);
    }

    [[nodiscard]] bool valid() const { return minX <= maxX && minY <= maxY; }
};

struct Polyline {
    std::vector<Vector2> points{};
    bool closed{true};
};

using Lines = std::vector<Polyline>;

struct BuiltPath {
    ShapeSpec shape{};
    Vector2 origin{};
    bool valid{false};
};

Vector2 toScene(const Vector2& canvasPoint, const Vector2& canvas) {
    return Vector2(canvasPoint.x - canvas.x * 0.5f,
                   canvasPoint.y - canvas.y * 0.5f);
}

Vector2 canvasPoint(const EditorialMapPoint& point) {
    return Vector2(point.x, point.y);
}

Lines linesFromPolygons(const std::vector<EditorialMapPolygon>& polygons) {
    Lines lines;
    for (const EditorialMapPolygon& polygon : polygons) {
        for (const EditorialMapRing& ring : polygon.rings) {
            if (ring.points.size() < 2) continue;
            Polyline line;
            line.points.reserve(ring.points.size());
            for (const EditorialMapPoint& point : ring.points)
                line.points.push_back(canvasPoint(point));
            line.closed = true;
            lines.push_back(std::move(line));
        }
    }
    return lines;
}

Lines linesFromFeatures(const std::vector<EditorialMapFeature>& features) {
    Lines lines;
    for (const EditorialMapFeature& feature : features) {
        const Lines featureLines = linesFromPolygons(feature.polygons);
        lines.insert(lines.end(), featureLines.begin(), featureLines.end());
    }
    return lines;
}

Lines linesFromSegments(const std::vector<EditorialMapSegment>& segments) {
    Lines lines;
    lines.reserve(segments.size());
    for (const EditorialMapSegment& segment : segments) {
        Polyline line;
        line.points = {canvasPoint(segment.from), canvasPoint(segment.to)};
        line.closed = false;
        lines.push_back(std::move(line));
    }
    return lines;
}

Lines transformed(Lines lines, float scale, float offsetX, float offsetY) {
    Bounds bounds;
    for (const Polyline& line : lines)
        for (const Vector2& point : line.points) bounds.add(point);
    if (!bounds.valid()) return lines;
    const Vector2 center((bounds.minX + bounds.maxX) * 0.5f,
                         (bounds.minY + bounds.maxY) * 0.5f);
    for (Polyline& line : lines) {
        for (Vector2& point : line.points) {
            point.x = center.x + (point.x - center.x) * scale + offsetX;
            point.y = center.y + (point.y - center.y) * scale + offsetY;
        }
    }
    return lines;
}

BuiltPath buildPath(Lines lines, const std::string& name) {
    BuiltPath built;
    Bounds bounds;
    for (const Polyline& line : lines)
        for (const Vector2& point : line.points) bounds.add(point);
    if (!bounds.valid()) return built;

    built.origin = Vector2(bounds.minX - kPathPadding, bounds.minY - kPathPadding);
    built.shape.size = Vector2(
        std::max(2.f, bounds.maxX - bounds.minX + kPathPadding * 2.f),
        std::max(2.f, bounds.maxY - bounds.minY + kPathPadding * 2.f));
    built.shape.name = name;
    built.shape.geometry = ShapeGeometry::Path;
    built.shape.fillRule = ShapeFillRule::EvenOdd;
    built.shape.strokeCap = "round";
    built.shape.strokeJoin = "round";
    built.shape.path.reserve(4096);
    for (const Polyline& line : lines) {
        if (line.points.empty()) continue;
        built.shape.path.push_back(ShapePathCommand::moveTo(
            line.points.front().x - built.origin.x,
            line.points.front().y - built.origin.y));
        for (std::size_t i = 1; i < line.points.size(); ++i) {
            built.shape.path.push_back(ShapePathCommand::lineTo(
                line.points[i].x - built.origin.x,
                line.points[i].y - built.origin.y));
        }
        if (line.closed) built.shape.path.push_back(ShapePathCommand::close());
    }
    built.valid = true;
    return built;
}

ShapeTrimSpec revealTrim(int startFrame, int endFrame) {
    return ShapeTrimSpec{
        .start = 0.f,
        .end = 0.02f,
        .offset = 0.f,
        .easing = "in_out_cubic",
        .keyframes = {
            ShapeTrimKeyframe{startFrame, 0.f, 0.02f, 0.f},
            ShapeTrimKeyframe{endFrame, 0.f, 1.f, 0.f},
        },
    };
}

LayerHandle* addPath(TemplateScene& scene, const Vector2& canvas, const Lines& lines,
                     const std::string& name, const std::string& fill,
                     const std::string& stroke, float width, bool fillEnabled,
                     bool strokeEnabled, int inFrame, int outFrame,
                     const std::string& glowColor = {}, float glowRadius = 0.f,
                     float glowIntensity = 0.f,
                     const std::optional<ShapeTrimSpec>& trim = std::nullopt) {
    BuiltPath built = buildPath(lines, name);
    if (!built.valid) return nullptr;
    built.shape.fillColor = colorOr(fill, "#FFFFFF");
    built.shape.fillEnabled = fillEnabled;
    // An empty strokeColor is how the scene contract disables a stroke; a
    // non-empty color must carry a drawable width.
    built.shape.strokeColor = strokeEnabled ? colorOr(stroke, "#FFFFFF") : "";
    built.shape.fillRule = ShapeFillRule::EvenOdd;
    built.shape.strokeWidth = strokeEnabled ? std::max(0.25f, width) : 0.f;
    if (!glowColor.empty() && glowRadius > 0.f) {
        built.shape.glowColor = colorOr(glowColor, "#FFFFFF");
        built.shape.glowRadius = glowRadius;
        built.shape.glowIntensity = std::clamp(glowIntensity, 0.f, 1.f);
    }
    if (trim) built.shape.trim = *trim;
    LayerHandle& layer = scene.shape(built.shape);
    const Vector2 origin = toScene(built.origin, canvas);
    layer.position(origin.x, origin.y).alive(inFrame, outFrame);
    return &layer;
}

LayerHandle* addCubicPath(TemplateScene& scene, const Vector2& canvas,
                          const Vector2& from, const Vector2& c1, const Vector2& c2,
                          const Vector2& to, const std::string& name,
                          const std::string& stroke, float width,
                          const std::optional<ShapeTrimSpec>& trim, int inFrame,
                          int outFrame, const std::string& glowColor = {},
                          float glowRadius = 0.f, float glowIntensity = 0.f) {
    Bounds bounds;
    for (const Vector2& point : {from, c1, c2, to}) bounds.add(point);
    if (!bounds.valid()) return nullptr;
    const Vector2 origin(bounds.minX - kPathPadding, bounds.minY - kPathPadding);
    ShapeSpec shape;
    shape.size = Vector2(std::max(2.f, bounds.maxX - bounds.minX + kPathPadding * 2.f),
                         std::max(2.f, bounds.maxY - bounds.minY + kPathPadding * 2.f));
    shape.name = name;
    shape.geometry = ShapeGeometry::Path;
    shape.fillEnabled = false;
    shape.strokeColor = colorOr(stroke, "#FFFFFF");
    shape.strokeWidth = std::max(0.25f, width);
    shape.strokeCap = "round";
    shape.strokeJoin = "round";
    if (!glowColor.empty() && glowRadius > 0.f) {
        shape.glowColor = colorOr(glowColor, "#FFFFFF");
        shape.glowRadius = glowRadius;
        shape.glowIntensity = std::clamp(glowIntensity, 0.f, 1.f);
    }
    shape.path = {
        ShapePathCommand::moveTo(from.x - origin.x, from.y - origin.y),
        ShapePathCommand::cubicTo(c1.x - origin.x, c1.y - origin.y,
                                  c2.x - origin.x, c2.y - origin.y,
                                  to.x - origin.x, to.y - origin.y),
    };
    if (trim) shape.trim = *trim;
    LayerHandle& layer = scene.shape(shape);
    const Vector2 sceneOrigin = toScene(origin, canvas);
    layer.position(sceneOrigin.x, sceneOrigin.y).alive(inFrame, outFrame);
    return &layer;
}

LayerHandle* addRect(TemplateScene& scene, const Vector2& canvas, float x, float y,
                     float width, float height, const std::string& fill,
                     const std::string& stroke, float strokeWidth,
                     const std::string& name, int inFrame, int outFrame) {
    ShapeSpec shape;
    shape.size = Vector2(std::max(1.f, width), std::max(1.f, height));
    shape.fillColor = colorOr(fill, "#FFFFFF");
    shape.fillEnabled = validHexColor(fill);
    shape.strokeColor = strokeWidth > 0.f ? colorOr(stroke, "#FFFFFF") : "";
    shape.strokeWidth = strokeWidth > 0.f ? std::max(0.25f, strokeWidth) : 0.f;
    shape.name = name;
    LayerHandle& layer = scene.shape(shape);
    const Vector2 origin = toScene(Vector2(x, y), canvas);
    layer.position(origin.x, origin.y).alive(inFrame, outFrame);
    return &layer;
}

LayerHandle* addEllipse(TemplateScene& scene, const Vector2& canvas, float x, float y,
                        float radius, const std::string& fill,
                        const std::string& stroke, float strokeWidth,
                        const std::string& name, int inFrame, int outFrame,
                        const std::string& glowColor = {}, float glowRadius = 0.f,
                        float glowIntensity = 0.f) {
    ShapeSpec shape;
    shape.size = Vector2(std::max(1.f, radius * 2.f), std::max(1.f, radius * 2.f));
    shape.geometry = ShapeGeometry::Ellipse;
    shape.fillColor = colorOr(fill, "#FFFFFF");
    shape.fillEnabled = validHexColor(fill);
    shape.strokeColor = strokeWidth > 0.f ? colorOr(stroke, "#FFFFFF") : "";
    shape.strokeWidth = strokeWidth > 0.f ? std::max(0.25f, strokeWidth) : 0.f;
    if (!glowColor.empty() && glowRadius > 0.f) {
        shape.glowColor = colorOr(glowColor, "#FFFFFF");
        shape.glowRadius = glowRadius;
        shape.glowIntensity = std::clamp(glowIntensity, 0.f, 1.f);
    }
    shape.name = name;
    LayerHandle& layer = scene.shape(shape);
    const Vector2 center = toScene(Vector2(x, y), canvas);
    layer.position(center.x, center.y).alive(inFrame, outFrame);
    return &layer;
}

void fadeIn(LayerHandle& layer, float fps, int startFrame, int endFrame,
            float targetOpacity) {
    targetOpacity = std::clamp(targetOpacity, 0.f, 1.f);
    if (endFrame <= startFrame) {
        layer.opacity(targetOpacity);
        return;
    }
    auto& track = layer.layer().tracks.opacity;
    track.add(static_cast<float>(startFrame) / fps, 0.f, Easing::easeOut());
    track.add(static_cast<float>(endFrame) / fps, targetOpacity, Easing::easeOut());
}

void pulse(LayerHandle& layer, float fps, int startFrame, int endFrame,
           float fromScale, float toScale, float peakOpacity) {
    const float t0 = static_cast<float>(startFrame) / fps;
    const float t1 = static_cast<float>(std::max(startFrame + 1, endFrame)) / fps;
    auto& scale = layer.layer().tracks.scale;
    scale.add(t0, Vector3(fromScale, fromScale, 1.f), Easing::easeOut());
    scale.add(t1, Vector3(toScale, toScale, 1.f), Easing::easeOut());
    auto& opacity = layer.layer().tracks.opacity;
    opacity.add(t0, 0.f, Easing::easeOut());
    opacity.add(std::min(t1, t0 + 2.f / fps), std::clamp(peakOpacity, 0.f, 1.f),
                Easing::easeOut());
    opacity.add(t1, 0.f, Easing::easeOut());
}

std::string fontPath(const std::string& role) {
    if (role == "serif_bold") return "assets/fonts/PlayfairDisplay-Bold.ttf";
    if (role == "sans_semibold") return "assets/fonts/Inter-SemiBold.ttf";
    if (role == "mono") return "assets/fonts/LiberationMono-Bold.ttf";
    return "assets/fonts/Inter-Regular.ttf";
}

int frameAt(double fraction, int frameCount) {
    return std::clamp(static_cast<int>(std::lround(fraction * (frameCount - 1))), 0,
                      std::max(0, frameCount - 1));
}

LayerHandle* addLabel(TemplateScene& scene, const Vector2& canvas,
                      const EditorialMapLabel& label, const std::string& name,
                      int fadeStartFrame, int fadeEndFrame, int endFrame,
                      float fps) {
    if (label.text.empty() || !std::isfinite(label.size) || label.size < 4.f ||
        label.size > 256.f)
        return nullptr;
    TextSpec spec;
    spec.text = label.text;
    spec.font = fontPath(label.font);
    spec.fontSize = label.size;
    spec.color = colorOr(label.color, "#FFFFFF");
    spec.name = name;
    // The native RenderPlan writer does not serialize text shadows yet; the
    // pack keeps the DTO's stroke (which the writer does carry) and leaves the
    // soft shadow to a future core extension.
    if (label.strokeWidth > 0.f && validHexColor(label.stroke))
        spec.stroke = TextStrokeStyle{label.stroke, label.strokeWidth};

    float x = label.x;
    if (label.align == "right") x -= label.width * 0.5f;
    else if (label.align != "center") x += label.width * 0.5f;
    const float y = label.y - label.size * 0.36f;
    LayerHandle& layer = scene.text(spec);
    const Vector2 point = toScene(Vector2(x, y), canvas);
    layer.position(point.x, point.y).alive(0, endFrame);
    fadeIn(layer, fps, fadeStartFrame, fadeEndFrame, label.opacity);
    return &layer;
}

void addPin(TemplateScene& scene, const Vector2& canvas, const EditorialMapPin& pin,
            const std::string& name, int fadeStartFrame, int fadeEndFrame,
            int endFrame, float fps, std::vector<LayerHandle*>& layers) {
    const float radius = std::max(2.f, pin.radius);
    auto push = [&layers](LayerHandle* layer) {
        if (layer != nullptr) layers.push_back(layer);
    };
    if (pin.style == "crosshair") {
        const std::string color = colorOr(pin.fill, "#FFFFFF");
        LayerHandle* ring = addEllipse(scene, canvas, pin.x, pin.y, radius, "",
                                       color, 1.5f, name + "_ring", 0, endFrame);
        if (ring != nullptr) {
            fadeIn(*ring, fps, fadeStartFrame, fadeEndFrame, 0.9f);
            push(ring);
        }
        Lines arms;
        const float inner = radius + 2.f;
        const float outer = radius + 10.f;
        arms.push_back({{Vector2(pin.x - outer, pin.y), Vector2(pin.x - inner, pin.y)},
                        false});
        arms.push_back({{Vector2(pin.x + inner, pin.y), Vector2(pin.x + outer, pin.y)},
                        false});
        arms.push_back({{Vector2(pin.x, pin.y - outer), Vector2(pin.x, pin.y - inner)},
                        false});
        arms.push_back({{Vector2(pin.x, pin.y + inner), Vector2(pin.x, pin.y + outer)},
                        false});
        LayerHandle* cross = addPath(scene, canvas, arms, name + "_arms", "", color,
                                     1.5f, false, true, 0, endFrame);
        if (cross != nullptr) {
            fadeIn(*cross, fps, fadeStartFrame, fadeEndFrame, 1.f);
            push(cross);
        }
        LayerHandle* center = addEllipse(scene, canvas, pin.x, pin.y, 2.f, color, "",
                                         0.f, name + "_center", 0, endFrame);
        if (center != nullptr) {
            fadeIn(*center, fps, fadeStartFrame, fadeEndFrame, 1.f);
            push(center);
        }
        return;
    }

    LayerHandle* shadow = addEllipse(scene, canvas, pin.x + 2.f, pin.y + 3.f,
                                     radius + 2.f, "#1F2937", "", 0.f,
                                     name + "_shadow", 0, endFrame);
    if (shadow != nullptr) {
        fadeIn(*shadow, fps, fadeStartFrame, fadeEndFrame, 0.16f);
        push(shadow);
    }
    LayerHandle* ring = addEllipse(scene, canvas, pin.x, pin.y, radius,
                                   colorOr(pin.ring, "#FFFFFF"), "", 0.f,
                                   name + "_ring", 0, endFrame);
    if (ring != nullptr) {
        fadeIn(*ring, fps, fadeStartFrame, fadeEndFrame, 1.f);
        push(ring);
    }
    LayerHandle* dot = addEllipse(scene, canvas, pin.x, pin.y, radius * 0.44f,
                                  colorOr(pin.fill, "#111827"), "", 0.f,
                                  name + "_dot", 0, endFrame);
    if (dot != nullptr) {
        fadeIn(*dot, fps, fadeStartFrame, fadeEndFrame, 1.f);
        push(dot);
    }
}

void addShadowCopies(TemplateScene& scene, const Vector2& canvas, const Lines& base,
                     const EditorialMapShadow& shadow, const std::string& name,
                     int endFrame, float fps, std::vector<LayerHandle*>& layers) {
    if (!validHexColor(shadow.color) || shadow.opacity <= 0.f) return;
    const float opacity = std::clamp(shadow.opacity, 0.f, 1.f);
    const float blur = std::clamp(shadow.blur, 0.f, 128.f);
    for (int copy = 0; copy < 2; ++copy) {
        const float factor = copy == 0 ? 1.f : 0.55f;
        Lines lines = transformed(base, shadow.scale,
                                  shadow.offsetX * factor, shadow.offsetY * factor);
        LayerHandle* layer = addPath(
            scene, canvas, lines, name + "_shadow_" + std::to_string(copy),
            shadow.color, "", 0.f, true, false, 0, endFrame, shadow.color,
            blur * 0.55f, 0.55f);
        if (layer == nullptr) continue;
        fadeIn(*layer, fps, 0, std::max(1, endFrame / 6),
               copy == 0 ? opacity : opacity * 0.45f);
        layers.push_back(layer);
    }
}

void addRadar(TemplateScene& scene, const Vector2& canvas,
              const EditorialMapRadar& radar, const std::string& accent,
              float fps, int endFrame, std::vector<LayerHandle*>& layers) {
    const float maxRadius = std::max(24.f, radar.maxRadius);
    const std::string color = colorOr(radar.color, "#38BDF8");
    const int hudStart = frameAt(0.02, endFrame + 1);
    const int hudEnd = frameAt(0.08, endFrame + 1);
    for (float radius = 52.f; radius >= 14.f; radius -= 8.f) {
        LayerHandle* halo = addEllipse(
            scene, canvas, radar.x, radar.y, radius, color, "", 0.f,
            "editorial_radar_halo_" + std::to_string(static_cast<int>(radius)), 0,
            endFrame);
        if (halo == nullptr) continue;
        fadeIn(*halo, fps, hudStart, hudEnd,
               std::clamp(0.03f + (52.f - radius) * 0.002f, 0.f, 0.3f));
        layers.push_back(halo);
    }
    LayerHandle* ring = addEllipse(scene, canvas, radar.x, radar.y, 19.f, "",
                                   color, 1.2f, "editorial_radar_ring", 0, endFrame,
                                   color, 8.f, 0.55f);
    if (ring != nullptr) {
        fadeIn(*ring, fps, hudStart, hudEnd, 0.85f);
        layers.push_back(ring);
    }
    LayerHandle* center = addEllipse(scene, canvas, radar.x, radar.y, 6.f,
                                     color, "", 0.f, "editorial_radar_center", 0,
                                     endFrame);
    if (center != nullptr) {
        fadeIn(*center, fps, hudStart, hudEnd, 1.f);
        layers.push_back(center);
    }
    LayerHandle* white = addEllipse(scene, canvas, radar.x, radar.y, 2.f,
                                    "#FFFFFF", "", 0.f, "editorial_radar_core", 0,
                                    endFrame);
    if (white != nullptr) {
        fadeIn(*white, fps, hudStart, hudEnd, 1.f);
        layers.push_back(white);
    }

    const int span = endFrame + 1;
    const std::array<double, 4> starts{0.00, 0.18, 0.50, 0.68};
    for (std::size_t index = 0; index < starts.size(); ++index) {
        const int start = frameAt(starts[index], span);
        const int end = std::min(endFrame, start + frameAt(0.40, span));
        ShapeSpec shape;
        shape.size = Vector2(maxRadius * 2.f, maxRadius * 2.f);
        shape.geometry = ShapeGeometry::Ellipse;
        shape.fillEnabled = false;
        shape.strokeColor = color;
        shape.strokeWidth = 2.f;
        shape.glowColor = color;
        shape.glowRadius = 12.f;
        shape.glowIntensity = 0.45f;
        shape.name = "editorial_radar_pulse_" + std::to_string(index);
        LayerHandle& layer = scene.shape(shape);
        const Vector2 centerPoint = toScene(Vector2(radar.x, radar.y), canvas);
        layer.position(centerPoint.x, centerPoint.y).alive(0, endFrame);
        pulse(layer, fps, start, end, 24.f / maxRadius, 1.f, 0.85f);
        layers.push_back(&layer);
    }
    (void)accent;
}

}  // namespace

const char* editorialMapSceneSchemaId() noexcept {
    return "chrononplugin.editorial-map-scene.v1";
}

EditorialMapScene loadEditorialMapScene(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("could not open editorial map scene: " + path);
    Json document;
    try {
        input >> document;
    } catch (const std::exception& error) {
        throw std::runtime_error("invalid editorial map scene JSON: " + path + ": " +
                                 error.what());
    }
    if (!document.is_object())
        throw std::invalid_argument("editorial map scene must be a JSON object");
    const std::string schema = readString(document, "schema");
    if (schema != editorialMapSceneSchemaId())
        throw std::invalid_argument("editorial map scene schema must be " +
                                    std::string(editorialMapSceneSchemaId()));

    EditorialMapScene scene;
    scene.style = readString(document, "style");
    const auto canvas = document.find("canvas");
    if (canvas == document.end() || !canvas->is_array() || canvas->size() != 2 ||
        !(*canvas)[0].is_number() || !(*canvas)[1].is_number())
        throw std::invalid_argument("editorial map scene canvas must be [width, height]");
    scene.canvas = Vector2((*canvas)[0].get<float>(), (*canvas)[1].get<float>());
    scene.fps = readFloat(document, "fps", 30.f);
    scene.frameCount = static_cast<int>(readFloat(document, "frame_count", 240.f));
    scene.title = readString(document, "title");
    scene.subtitle = readString(document, "subtitle");
    if (document.contains("palette")) scene.palette = readPalette(document["palette"]);
    if (document.contains("states")) scene.states = readFeatures(document["states"]);
    if (document.contains("countries"))
        scene.countries = readFeatures(document["countries"]);
    if (document.contains("highlight")) {
        const Json& highlight = document["highlight"];
        if (!highlight.is_object() || !highlight.contains("polygons"))
            throw std::invalid_argument("editorial highlight must contain polygons");
        scene.highlight = readPolygons(highlight["polygons"]);
    }
    if (document.contains("hatch_segments"))
        scene.hatchSegments = readSegments(document["hatch_segments"]);
    if (document.contains("graticule_segments"))
        scene.graticuleSegments = readSegments(document["graticule_segments"]);
    if (document.contains("accent_segments"))
        scene.accentSegments = readAccents(document["accent_segments"]);
    if (document.contains("frames")) scene.frames = readFrames(document["frames"]);
    if (document.contains("pins")) scene.pins = readPins(document["pins"]);
    if (document.contains("labels")) scene.labels = readLabels(document["labels"]);
    if (document.contains("arc")) scene.arc = readArc(document["arc"]);
    if (document.contains("leader")) scene.leader = readLeader(document["leader"]);
    if (document.contains("radar")) scene.radar = readRadar(document["radar"]);
    if (document.contains("shadow")) scene.shadow = readShadow(document["shadow"]);
    return scene;
}

EditorialMapComposition addEditorialMap(TemplateScene& scene,
                                        const EditorialMapScene& spec) {
    if (!std::isfinite(spec.canvas.x) || !std::isfinite(spec.canvas.y) ||
        spec.canvas.x < 64.f || spec.canvas.y < 64.f || spec.canvas.x > 8192.f ||
        spec.canvas.y > 8192.f)
        throw std::invalid_argument("addEditorialMap: canvas must be 64..8192 pixels");
    if (!std::isfinite(spec.fps) || spec.fps <= 0.f || spec.fps > 240.f)
        throw std::invalid_argument("addEditorialMap: fps must be in 1..240");
    if (spec.frameCount < 2)
        throw std::invalid_argument("addEditorialMap: frame count must be at least 2");
    const std::string& style = spec.style;
    if (style != "editorial_vox" && style != "paper_cutout" && style != "dark_radar" &&
        style != "blueprint" && style != "connection_arc" &&
        style != "floating_island")
        throw std::invalid_argument("addEditorialMap: unsupported style '" + style + "'");
    if (!validHexColor(spec.palette.background))
        throw std::invalid_argument("addEditorialMap: background must be #RRGGBB");
    if ((style == "editorial_vox" || style == "paper_cutout" ||
         style == "blueprint" || style == "floating_island") &&
        spec.highlight.empty())
        throw std::invalid_argument("addEditorialMap: style needs highlight geometry");
    if (style == "connection_arc" && !spec.arc)
        throw std::invalid_argument("addEditorialMap: connection_arc needs an arc");
    if (style == "dark_radar" && !spec.radar)
        throw std::invalid_argument("addEditorialMap: dark_radar needs a radar centre");
    if (style == "floating_island" && !spec.leader)
        throw std::invalid_argument("addEditorialMap: floating_island needs a leader");

    const Vector2 canvas = spec.canvas;
    const float fps = spec.fps;
    const int endFrame = spec.frameCount - 1;
    const int span = spec.frameCount;
    const auto at = [&](double fraction) { return frameAt(fraction, span); };
    const int inFrame = 0;

    const EditorialMapPalette& palette = spec.palette;
    EditorialMapComposition result;
    result.endFrame = endFrame;
    auto push = [&result](LayerHandle* layer) {
        if (layer != nullptr) result.layers.push_back(layer);
    };

    LayerHandle* background = addRect(scene, canvas, 0.f, 0.f, canvas.x, canvas.y,
                                      palette.background, "", 0.f,
                                      "editorial_background", inFrame, endFrame);
    if (background == nullptr)
        throw std::invalid_argument("addEditorialMap: background could not be built");
    result.background = background;
    result.layers.push_back(background);

    const Lines countries = linesFromFeatures(spec.countries);
    const Lines states = linesFromFeatures(spec.states);
    const Lines highlight = linesFromPolygons(spec.highlight);

    if (style == "editorial_vox") {
        if (!countries.empty() && validHexColor(palette.countriesFill)) {
            LayerHandle* layer = addPath(
                scene, canvas, countries, "editorial_countries", palette.countriesFill,
                palette.countriesStroke, 1.f, true,
                validHexColor(palette.countriesStroke), inFrame, endFrame);
            push(layer);
        }
        if (!states.empty() && validHexColor(palette.statesFill)) {
            LayerHandle* layer = addPath(
                scene, canvas, states, "editorial_states", palette.statesFill,
                palette.statesStroke, 1.2f, true,
                validHexColor(palette.statesStroke), inFrame, endFrame);
            push(layer);
        }
        LayerHandle* highlightLayer = addPath(
            scene, canvas, highlight, "editorial_highlight", palette.highlightFill,
            palette.highlightStroke, 2.6f, true, true, inFrame, endFrame);
        if (highlightLayer != nullptr) {
            fadeIn(*highlightLayer, fps, at(0.04), at(0.12), 1.f);
            result.highlight = highlightLayer;
            push(highlightLayer);
        }
        for (std::size_t i = 0; i < spec.accentSegments.size(); ++i) {
            const EditorialMapSegment& segment = spec.accentSegments[i];
            Lines line = {{{canvasPoint(segment.from), canvasPoint(segment.to)}, false}};
            LayerHandle* layer = addPath(scene, canvas, line,
                                         "editorial_accent_" + std::to_string(i), "",
                                         segment.color, segment.width, false, true,
                                         inFrame, endFrame);
            if (layer == nullptr) continue;
            fadeIn(*layer, fps, at(0.02), at(0.09), 1.f);
            push(layer);
        }
        int pinIndex = 0;
        for (std::size_t i = 0; i < spec.labels.size(); ++i) {
            const EditorialMapLabel& label = spec.labels[i];
            int start = at(0.09);
            int end = at(0.16);
            if (label.role == "title" || label.role == "subtitle" ||
                label.role == "micro") {
                start = at(0.02);
                end = at(0.09);
            } else if (label.role == "pin") {
                start = at(0.15);
                end = at(0.21);
            }
            push(addLabel(scene, canvas, label,
                          "editorial_label_" + std::to_string(i), start, end,
                          endFrame, fps));
        }
        for (const EditorialMapPin& pin : spec.pins)
            addPin(scene, canvas, pin,
                   "editorial_pin_" + std::to_string(pinIndex++), at(0.10),
                   at(0.15), endFrame, fps, result.layers);
    } else if (style == "paper_cutout") {
        if (!states.empty() && validHexColor(palette.statesFill)) {
            LayerHandle* layer = addPath(
                scene, canvas, states, "paper_states", palette.statesFill,
                palette.statesStroke, 1.2f, true,
                validHexColor(palette.statesStroke), inFrame, endFrame);
            push(layer);
        }
        if (spec.shadow) {
            addShadowCopies(scene, canvas, highlight, *spec.shadow, "paper_island",
                            endFrame, fps, result.layers);
        }
        LayerHandle* plate = addPath(
            scene, canvas,
            transformed(highlight, spec.shadow ? spec.shadow->scale : 1.f, 2.f, 3.f),
            "paper_plate", "#CFC4B1", "", 0.f, true, false, inFrame, endFrame);
        if (plate != nullptr) {
            fadeIn(*plate, fps, at(0.04), at(0.12), 1.f);
            push(plate);
        }
        LayerHandle* highlightLayer = addPath(
            scene, canvas, highlight, "paper_highlight", palette.highlightFill,
            palette.highlightStroke, 2.4f, true, true, inFrame, endFrame);
        if (highlightLayer != nullptr) {
            fadeIn(*highlightLayer, fps, at(0.04), at(0.12), 1.f);
            result.highlight = highlightLayer;
            push(highlightLayer);
        }
        for (std::size_t i = 0; i < spec.accentSegments.size(); ++i) {
            const EditorialMapSegment& segment = spec.accentSegments[i];
            Lines line = {{{canvasPoint(segment.from), canvasPoint(segment.to)}, false}};
            LayerHandle* layer = addPath(scene, canvas, line,
                                         "paper_accent_" + std::to_string(i), "",
                                         segment.color, segment.width, false, true,
                                         inFrame, endFrame);
            if (layer == nullptr) continue;
            fadeIn(*layer, fps, at(0.02), at(0.09), 1.f);
            push(layer);
        }
        int pinIndex = 0;
        for (std::size_t i = 0; i < spec.labels.size(); ++i) {
            const EditorialMapLabel& label = spec.labels[i];
            int start = at(0.02);
            int end = at(0.09);
            if (label.role == "pin") {
                start = at(0.17);
                end = at(0.23);
            }
            push(addLabel(scene, canvas, label,
                          "paper_label_" + std::to_string(i), start, end, endFrame,
                          fps));
        }
        for (const EditorialMapPin& pin : spec.pins)
            addPin(scene, canvas, pin, "paper_pin_" + std::to_string(pinIndex++),
                   at(0.12), at(0.18), endFrame, fps, result.layers);
    } else if (style == "dark_radar") {
        if (!spec.graticuleSegments.empty() && validHexColor(palette.grid)) {
            LayerHandle* grid = addPath(
                scene, canvas, linesFromSegments(spec.graticuleSegments),
                "radar_graticule", "", palette.grid, 1.f, false, true, inFrame,
                endFrame);
            push(grid);
        }
        if (!states.empty() && validHexColor(palette.statesFill)) {
            LayerHandle* layer = addPath(
                scene, canvas, states, "radar_states", palette.statesFill,
                palette.statesStroke, 1.2f, true,
                validHexColor(palette.statesStroke), inFrame, endFrame);
            push(layer);
        }
        addRadar(scene, canvas, *spec.radar, palette.accent, fps, endFrame,
                 result.layers);
        for (std::size_t i = 0; i < spec.accentSegments.size(); ++i) {
            const EditorialMapSegment& segment = spec.accentSegments[i];
            Lines line = {{{canvasPoint(segment.from), canvasPoint(segment.to)}, false}};
            LayerHandle* layer = addPath(scene, canvas, line,
                                         "radar_accent_" + std::to_string(i), "",
                                         segment.color, segment.width, false, true,
                                         inFrame, endFrame);
            if (layer == nullptr) continue;
            fadeIn(*layer, fps, at(0.02), at(0.08), 1.f);
            push(layer);
        }
        for (std::size_t i = 0; i < spec.labels.size(); ++i) {
            const EditorialMapLabel& label = spec.labels[i];
            const int start = label.role == "hud" ? at(0.02) : at(0.09);
            const int end = label.role == "hud" ? at(0.08) : at(0.15);
            push(addLabel(scene, canvas, label,
                          "radar_label_" + std::to_string(i), start, end, endFrame,
                          fps));
        }
    } else if (style == "blueprint") {
        if (!spec.graticuleSegments.empty() && validHexColor(palette.grid)) {
            LayerHandle* grid = addPath(
                scene, canvas, linesFromSegments(spec.graticuleSegments),
                "blueprint_graticule", "", palette.grid, 1.f, false, true,
                inFrame, endFrame);
            push(grid);
        }
        for (std::size_t i = 0; i < spec.frames.size(); ++i) {
            const EditorialMapFrame& frame = spec.frames[i];
            LayerHandle* layer = addRect(
                scene, canvas, frame.x, frame.y, frame.width, frame.height,
                frame.fill, frame.stroke, frame.strokeWidth,
                "blueprint_frame_" + std::to_string(i), inFrame, endFrame);
            if (layer == nullptr) continue;
            fadeIn(*layer, fps, at(0.03), at(0.09), 1.f);
            push(layer);
        }
        if (!states.empty() && validHexColor(palette.statesStroke)) {
            LayerHandle* outlines = addPath(
                scene, canvas, states, "blueprint_states", "", palette.statesStroke,
                1.2f, false, true, inFrame, endFrame);
            push(outlines);
        }
        if (!spec.hatchSegments.empty() && validHexColor(palette.hatch)) {
            LayerHandle* hatch = addPath(
                scene, canvas, linesFromSegments(spec.hatchSegments),
                "blueprint_hatch", "", palette.hatch, 1.f, false, true, inFrame,
                endFrame);
            if (hatch != nullptr) {
                fadeIn(*hatch, fps, at(0.06), at(0.14), 0.92f);
                push(hatch);
            }
        }
        LayerHandle* darkOutline = addPath(
            scene, canvas, highlight, "blueprint_outline_dark", "",
            palette.highlightStroke, 7.f, false, true, inFrame, endFrame,
            "#061726", 6.f, 0.4f);
        if (darkOutline != nullptr) {
            fadeIn(*darkOutline, fps, at(0.06), at(0.14), 1.f);
            push(darkOutline);
        }
        LayerHandle* lightOutline = addPath(
            scene, canvas, highlight, "blueprint_outline_light", "",
            palette.highlightStroke, 3.f, false, true, inFrame, endFrame);
        if (lightOutline != nullptr) {
            fadeIn(*lightOutline, fps, at(0.06), at(0.14), 1.f);
            result.highlight = lightOutline;
            push(lightOutline);
        }
        for (std::size_t i = 0; i < spec.accentSegments.size(); ++i) {
            const EditorialMapSegment& segment = spec.accentSegments[i];
            Lines line = {{{canvasPoint(segment.from), canvasPoint(segment.to)}, false}};
            LayerHandle* layer = addPath(scene, canvas, line,
                                         "blueprint_accent_" + std::to_string(i), "",
                                         segment.color, segment.width, false, true,
                                         inFrame, endFrame);
            if (layer == nullptr) continue;
            fadeIn(*layer, fps, at(0.03), at(0.09), 1.f);
            push(layer);
        }
        int pinIndex = 0;
        for (std::size_t i = 0; i < spec.labels.size(); ++i) {
            const EditorialMapLabel& label = spec.labels[i];
            int start = at(0.12);
            int end = at(0.18);
            if (label.role == "title") {
                start = at(0.03);
                end = at(0.09);
            }
            push(addLabel(scene, canvas, label,
                          "blueprint_label_" + std::to_string(i), start, end,
                          endFrame, fps));
        }
        for (const EditorialMapPin& pin : spec.pins)
            addPin(scene, canvas, pin, "blueprint_pin_" + std::to_string(pinIndex++),
                   at(0.12), at(0.18), endFrame, fps, result.layers);
    } else if (style == "connection_arc") {
        if (!countries.empty() && validHexColor(palette.countriesFill)) {
            LayerHandle* layer = addPath(
                scene, canvas, countries, "arc_countries", palette.countriesFill,
                palette.countriesStroke, 1.f, true,
                validHexColor(palette.countriesStroke), inFrame, endFrame);
            push(layer);
        }
        if (!states.empty() && validHexColor(palette.statesFill)) {
            LayerHandle* layer = addPath(
                scene, canvas, states, "arc_states", palette.statesFill,
                palette.statesStroke, 1.2f, true,
                validHexColor(palette.statesStroke), inFrame, endFrame);
            push(layer);
        }
        const EditorialMapArc& arc = *spec.arc;
        const Vector2 from = canvasPoint(arc.from);
        const Vector2 to = canvasPoint(arc.to);
        const Vector2 c1 = canvasPoint(arc.control1);
        const Vector2 c2 = canvasPoint(arc.control2);
        const int trimStart = at(0.10);
        const int trimEnd = at(0.42);
        const ShapeTrimSpec trim = revealTrim(trimStart, trimEnd);

        LayerHandle* groundA = addCubicPath(
            scene, canvas, from + Vector2(0.f, 8.f), c1 + Vector2(0.f, 8.f),
            c2 + Vector2(0.f, 8.f), to + Vector2(0.f, 8.f), "arc_ground_wide",
            "#1F2937", 22.f, trim, inFrame, endFrame);
        if (groundA != nullptr) {
            fadeIn(*groundA, fps, trimStart, trimEnd, 0.08f);
            push(groundA);
        }
        LayerHandle* groundB = addCubicPath(
            scene, canvas, from + Vector2(0.f, 8.f), c1 + Vector2(0.f, 8.f),
            c2 + Vector2(0.f, 8.f), to + Vector2(0.f, 8.f), "arc_ground",
            "#1F2937", 12.f, trim, inFrame, endFrame);
        if (groundB != nullptr) {
            fadeIn(*groundB, fps, trimStart, trimEnd, 0.16f);
            push(groundB);
        }
        LayerHandle* glow = addCubicPath(scene, canvas, from, c1, c2, to,
                                         "arc_glow", palette.accent, 10.f, trim,
                                         inFrame, endFrame, palette.accent, 18.f, 0.6f);
        if (glow != nullptr) {
            fadeIn(*glow, fps, trimStart, trimEnd, 0.34f);
            push(glow);
        }
        LayerHandle* white = addCubicPath(scene, canvas, from, c1, c2, to,
                                          "arc_underlay", palette.paper, 7.f, trim,
                                          inFrame, endFrame);
        if (white != nullptr) {
            fadeIn(*white, fps, trimStart, trimEnd, 1.f);
            push(white);
        }
        LayerHandle* accent = addCubicPath(scene, canvas, from, c1, c2, to,
                                           "arc_accent", palette.accent, 4.f, trim,
                                           inFrame, endFrame);
        if (accent != nullptr) {
            fadeIn(*accent, fps, trimStart, trimEnd, 1.f);
            push(accent);
        }
        int pinIndex = 0;
        for (std::size_t i = 0; i < spec.labels.size(); ++i) {
            const EditorialMapLabel& label = spec.labels[i];
            int start = at(0.02);
            int end = at(0.08);
            if (label.role == "pin") {
                start = pinIndex == 0 ? at(0.06) : at(0.36);
                end = pinIndex == 0 ? at(0.11) : at(0.43);
                ++pinIndex;
            } else if (label.role == "data") {
                start = at(0.34);
                end = at(0.42);
            }
            push(addLabel(scene, canvas, label, "arc_label_" + std::to_string(i),
                          start, end, endFrame, fps));
        }
        pinIndex = 0;
        for (const EditorialMapPin& pin : spec.pins) {
            const int start = pinIndex == 0 ? at(0.06) : at(0.36);
            const int end = pinIndex == 0 ? at(0.11) : at(0.43);
            addPin(scene, canvas, pin, "arc_pin_" + std::to_string(pinIndex++),
                   start, end, endFrame, fps, result.layers);
        }
    } else if (style == "floating_island") {
        if (spec.shadow) {
            addShadowCopies(scene, canvas, highlight, *spec.shadow, "island_shadow",
                            endFrame, fps, result.layers);
        }
        LayerHandle* highlightLayer = addPath(
            scene, canvas, highlight, "island_highlight", palette.highlightFill,
            palette.highlightStroke, 2.6f, true, true, inFrame, endFrame);
        if (highlightLayer != nullptr) {
            fadeIn(*highlightLayer, fps, at(0.10), at(0.20), 1.f);
            result.highlight = highlightLayer;
            push(highlightLayer);
        }
        const EditorialMapLeader& leader = *spec.leader;
        if (leader.points.size() >= 2) {
            Lines line;
            Polyline path;
            path.closed = false;
            for (const EditorialMapPoint& point : leader.points)
                path.points.push_back(canvasPoint(point));
            line.push_back(std::move(path));
            LayerHandle* leaderLayer = addPath(
                scene, canvas, line, "island_leader", "", palette.ink, 2.f, false,
                true, inFrame, endFrame, "", 0.f, 0.f,
                revealTrim(at(0.10), at(0.22)));
            if (leaderLayer != nullptr) {
                fadeIn(*leaderLayer, fps, at(0.10), at(0.22), 1.f);
                push(leaderLayer);
            }
            const Vector2 anchor = canvasPoint(leader.points.front());
            LayerHandle* dot = addEllipse(scene, canvas, anchor.x, anchor.y,
                                          std::max(2.f, leader.anchorRadius),
                                          palette.accent, "", 0.f, "island_anchor",
                                          inFrame, endFrame);
            if (dot != nullptr) {
                fadeIn(*dot, fps, at(0.10), at(0.22), 1.f);
                push(dot);
            }
        }
        for (std::size_t i = 0; i < spec.accentSegments.size(); ++i) {
            const EditorialMapSegment& segment = spec.accentSegments[i];
            Lines line = {{{canvasPoint(segment.from), canvasPoint(segment.to)}, false}};
            LayerHandle* layer = addPath(scene, canvas, line,
                                         "island_accent_" + std::to_string(i), "",
                                         segment.color, segment.width, false, true,
                                         inFrame, endFrame);
            if (layer == nullptr) continue;
            fadeIn(*layer, fps, at(0.20), at(0.27), 1.f);
            push(layer);
        }
        for (std::size_t i = 0; i < spec.labels.size(); ++i) {
            push(addLabel(scene, canvas, spec.labels[i],
                          "island_label_" + std::to_string(i), at(0.20), at(0.27),
                          endFrame, fps));
        }
    }

    return result;
}

}  // namespace chronontemplate
