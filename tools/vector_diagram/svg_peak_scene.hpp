// ChrononTemplate: shared scene model for the SVG-parity tools.
//
// This header is the single source of truth for the documentary SVG peak
// scene. Both `svg_peak_parity_emitter.cpp` (RenderPlan V3 emission) and
// `render_svg_parity_blend2d.cpp` (diagnostic Blend2D renderer) consume it,
// so geometry, framing, timing, easing and camera can never drift apart
// between the two paths (certification tests SVG-02/03, INT-02).
//
// Data sources, in order of authority:
//   1. The SVG asset  — path geometry (`#peak_line`) and checkpoint circles.
//      No scene coordinate is ever duplicated in C++ (SVG-03).
//   2. The preset     — `chronontemplate.svg_scene_catalog.v1` JSON: canvas,
//      framing, trim timing, follow-path marker timing, checkpoints and
//      camera tracks. Changing any of these is data-only (SCALE-04).
//
// Error policy (SVG-08): every parse or validation failure throws SceneError
// with an explicit message. Nothing here aborts, crashes or silently clamps.

#pragma once

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace chronon::svg_parity {

// Explicit, catchable scene errors. main() turns these into a clear
// "[ERROR]" line and exit code 1 — never a crash.
struct SceneError : std::runtime_error {
    explicit SceneError(const std::string& what) : std::runtime_error(what) {}
};

struct Vec2 {
    double x = 0.0;
    double y = 0.0;
};

inline double vecDistance(const Vec2& a, const Vec2& b) {
    return std::hypot(a.x - b.x, a.y - b.y);
}

// ── Easing (names match chronon.render-plan.v3 animation_easing) ─────────────

inline double easingValue(const std::string& name, double t) {
    t = std::clamp(t, 0.0, 1.0);
    if (name == "linear") return t;
    if (name == "hold") return t >= 1.0 ? 1.0 : 0.0;
    if (name == "in_quad") return t * t;
    if (name == "out_quad") return t * (2.0 - t);
    if (name == "in_out_quad") return t < 0.5 ? 2.0 * t * t : -1.0 + (4.0 - 2.0 * t) * t;
    if (name == "in_cubic") return t * t * t;
    if (name == "out_cubic") return 1.0 - std::pow(1.0 - t, 3.0);
    if (name == "in_out_cubic") {
        return t < 0.5 ? 4.0 * t * t * t : 1.0 - std::pow(-2.0 * t + 2.0, 3.0) / 2.0;
    }
    if (name == "in_expo") return t <= 0.0 ? 0.0 : std::pow(2.0, 10.0 * t - 10.0);
    if (name == "out_expo") return t >= 1.0 ? 1.0 : 1.0 - std::pow(2.0, -10.0 * t);
    if (name == "in_out_expo") {
        if (t <= 0.0) return 0.0;
        if (t >= 1.0) return 1.0;
        return t < 0.5 ? std::pow(2.0, 20.0 * t - 10.0) / 2.0
                       : (2.0 - std::pow(2.0, -20.0 * t + 10.0)) / 2.0;
    }
    if (name == "in_sine") return 1.0 - std::cos(t * 1.5707963267948966);
    if (name == "out_sine") return std::sin(t * 1.5707963267948966);
    if (name == "in_out_sine") return -(std::cos(3.1415926535897932) * t - 1.0) / 2.0;
    if (name == "smoothstep") return t * t * (3.0 - 2.0 * t);
    throw SceneError("unknown easing name: " + name);
}

// ── Keyframe track ───────────────────────────────────────────────────────────

// Two-or-more keyframes, per-segment eased interpolation. The same evaluator
// drives trim progress, follow-path progress and camera tracks.
struct Track {
    std::string easing = "linear";
    std::vector<std::pair<int, double>> keyframes; // (frame, value), sorted

    double valueAt(int frame) const {
        if (keyframes.empty()) {
            throw SceneError("track has no keyframes");
        }
        if (frame <= keyframes.front().first) return keyframes.front().second;
        if (frame >= keyframes.back().first) return keyframes.back().second;
        for (std::size_t i = 0; i + 1 < keyframes.size(); ++i) {
            const auto& k0 = keyframes[i];
            const auto& k1 = keyframes[i + 1];
            if (frame >= k0.first && frame <= k1.first) {
                const double span = static_cast<double>(k1.first - k0.first);
                if (span <= 0.0) return k1.second;
                const double t = static_cast<double>(frame - k0.first) / span;
                return k0.second + (k1.second - k0.second) * easingValue(easing, t);
            }
        }
        return keyframes.back().second;
    }
};

// ── SVG source of truth ──────────────────────────────────────────────────────

struct SvgMarker {
    std::string id;
    Vec2 center; // SVG user units
    double r = 0.0;
    std::array<double, 4> fill{0.94, 0.17, 0.24, 1.0}; // from the fill attribute
};

struct SvgScene {
    Vec2 viewBox; // (width, height) from the SVG viewBox
    std::vector<Vec2> peakPoints; // `#peak_line` in SVG user units
    std::vector<SvgMarker> circles;
    std::array<double, 4> peakStroke{0.910, 0.922, 0.941, 1.0}; // #E8EBF0
    double peakStrokeWidth = 3.0;
};

namespace detail {

inline std::string trimCopy(const std::string& s) {
    const char* ws = " \t\r\n";
    const auto b = s.find_first_not_of(ws);
    if (b == std::string::npos) return "";
    return s.substr(b, s.find_last_not_of(ws) - b + 1);
}

inline bool isPathSeparator(char c) {
    return c == ' ' || c == ',' || c == '\t' || c == '\r' || c == '\n';
}

// Minimal M/L path-data reader. Curves and arcs are rejected with an explicit
// message instead of being silently mis-read (SVG-08): the documentary scene
// contract accepts straight segments only, mirroring the Python registry.
inline std::vector<Vec2> parsePathData(const std::string& d) {
    std::vector<Vec2> points;
    std::size_t i = 0;
    const std::size_t len = d.size();
    auto skip = [&] { while (i < len && isPathSeparator(d[i])) ++i; };

    auto readNumber = [&](double& out) -> bool {
        skip();
        if (i >= len) return false;
        const std::size_t start = i;
        if (d[i] == '+' || d[i] == '-') ++i;
        bool digits = false;
        while (i < len && std::isdigit(static_cast<unsigned char>(d[i]))) { digits = true; ++i; }
        if (i < len && d[i] == '.') {
            ++i;
            while (i < len && std::isdigit(static_cast<unsigned char>(d[i]))) { digits = true; ++i; }
        }
        if (!digits) { i = start; return false; }
        if (i < len && (d[i] == 'e' || d[i] == 'E')) {
            const std::size_t eStart = i;
            ++i;
            if (i < len && (d[i] == '+' || d[i] == '-')) ++i;
            bool expDigits = false;
            while (i < len && std::isdigit(static_cast<unsigned char>(d[i]))) { expDigits = true; ++i; }
            if (!expDigits) i = eStart;
        }
        try {
            out = std::stod(d.substr(start, i - start));
        } catch (...) {
            i = start;
            return false;
        }
        return true;
    };

    char command = 0;
    skip();
    if (i < len && (d[i] == 'M' || d[i] == 'm')) {
        command = d[i++];
    } else {
        throw SceneError("#peak_line path data must start with an M command");
    }

    while (true) {
        skip();
        if (i >= len) break;
        if (std::isalpha(static_cast<unsigned char>(d[i]))) {
            command = d[i++];
            if (!(command == 'M' || command == 'm' || command == 'L' || command == 'l')) {
                throw SceneError(std::string("#peak_line uses unsupported path command '") +
                                 command + "'; only M/L is accepted");
            }
        }
        double x = 0.0, y = 0.0;
        if (!readNumber(x) || !readNumber(y)) {
            throw SceneError("#peak_line path data has a malformed coordinate pair");
        }
        if (command == 'm' || command == 'l') {
            if (points.empty()) {
                throw SceneError("#peak_line uses a relative command before the first point");
            }
            x += points.back().x;
            y += points.back().y;
        }
        points.push_back({x, y});
        // SVG allows repeated coordinate pairs after M: they continue as lines.
        if (command == 'M') command = 'L';
        else if (command == 'm') command = 'l';
    }

    if (points.size() < 2) {
        throw SceneError("#peak_line needs at least two points");
    }
    return points;
}

inline std::string xmlTagAttribute(const std::string& tag, const std::string& attr) {
    const std::string key = attr + "=\"";
    std::size_t at = tag.find(key);
    while (at != std::string::npos) {
        // Require an attribute-name boundary so `d=` never matches inside `id=`.
        const bool boundary = at == 0 || std::isspace(static_cast<unsigned char>(tag[at - 1]));
        if (boundary) break;
        at = tag.find(key, at + 1);
    }
    if (at == std::string::npos) return "";
    const std::size_t begin = at + key.size();
    const std::size_t end = tag.find('"', begin);
    if (end == std::string::npos) return "";
    return tag.substr(begin, end - begin);
}

} // namespace detail

// Loads the SVG asset and extracts the scene geometry: exactly one
// `#peak_line` path plus the checkpoint `<circle>` elements.
inline SvgScene loadSvgScene(const std::string& svgPath) {
    std::ifstream file(svgPath);
    if (!file.is_open()) {
        throw SceneError("cannot open SVG asset: " + svgPath);
    }
    const std::string content((std::istreambuf_iterator<char>(file)),
                              std::istreambuf_iterator<char>());

    SvgScene scene;

    // viewBox
    const std::size_t svgTagAt = content.find("<svg");
    if (svgTagAt == std::string::npos) {
        throw SceneError("SVG asset has no <svg> root element: " + svgPath);
    }
    const std::size_t svgTagEnd = content.find('>', svgTagAt);
    const std::string svgTag = content.substr(svgTagAt, svgTagEnd - svgTagAt + 1);
    const std::string viewBoxText = detail::xmlTagAttribute(svgTag, "viewBox");
    {
        std::istringstream iss(viewBoxText);
        double vx = 0, vy = 0, vw = 0, vh = 0;
        if (!(iss >> vx >> vy >> vw >> vh) || vw <= 0.0 || vh <= 0.0) {
            throw SceneError("documentary SVG needs a positive four-value viewBox");
        }
        scene.viewBox = {vw, vh};
    }

    // #peak_line — exactly one, M/L only
    int peakCount = 0;
    std::size_t pos = 0;
    while ((pos = content.find("<path", pos)) != std::string::npos) {
        const std::size_t tagEnd = content.find('>', pos);
        if (tagEnd == std::string::npos) break;
        const std::string tag = content.substr(pos, tagEnd - pos + 1);
        if (detail::xmlTagAttribute(tag, "id") == "peak_line") {
            ++peakCount;
            const std::string d = detail::xmlTagAttribute(tag, "d");
            if (d.empty()) {
                throw SceneError("#peak_line path has no d attribute");
            }
            scene.peakPoints = detail::parsePathData(d);
            const std::string stroke = detail::xmlTagAttribute(tag, "stroke");
            if (!stroke.empty()) {
                if (stroke.size() == 7 && stroke[0] == '#') {
                    for (int c = 0; c < 3; ++c) {
                        try {
                            scene.peakStroke[c] = std::stoi(stroke.substr(1 + c * 2, 2), nullptr, 16) / 255.0;
                        } catch (...) {
                            throw SceneError("#peak_line has a malformed stroke color");
                        }
                    }
                } else {
                    throw SceneError("#peak_line uses an unsupported stroke; only #RRGGBB is accepted");
                }
            }
            const std::string strokeWidth = detail::xmlTagAttribute(tag, "stroke-width");
            if (!strokeWidth.empty()) {
                try {
                    scene.peakStrokeWidth = std::stod(strokeWidth);
                } catch (...) {
                    throw SceneError("#peak_line has a non-numeric stroke-width");
                }
                if (!(std::isfinite(scene.peakStrokeWidth) && scene.peakStrokeWidth > 0.0)) {
                    throw SceneError("#peak_line stroke-width must be positive");
                }
            }
        }
        pos = tagEnd + 1;
    }
    if (peakCount == 0) {
        throw SceneError("documentary SVG must contain exactly one #peak_line path (none found)");
    }
    if (peakCount > 1) {
        throw SceneError("documentary SVG must contain exactly one #peak_line path (found " +
                         std::to_string(peakCount) + ")");
    }

    // checkpoint circles
    pos = 0;
    while ((pos = content.find("<circle", pos)) != std::string::npos) {
        const std::size_t tagEnd = content.find('>', pos);
        if (tagEnd == std::string::npos) break;
        const std::string tag = content.substr(pos, tagEnd - pos + 1);
        SvgMarker marker;
        marker.id = detail::xmlTagAttribute(tag, "id");
        try {
            marker.center.x = std::stod(detail::xmlTagAttribute(tag, "cx"));
            marker.center.y = std::stod(detail::xmlTagAttribute(tag, "cy"));
            marker.r = std::stod(detail::xmlTagAttribute(tag, "r"));
        } catch (...) {
            throw SceneError("SVG circle '" + marker.id + "' has non-numeric cx/cy/r");
        }
        if (!(std::isfinite(marker.center.x) && std::isfinite(marker.center.y) &&
              std::isfinite(marker.r) && marker.r > 0.0)) {
            throw SceneError("SVG circle '" + marker.id + "' needs finite cx/cy and r > 0");
        }
        const std::string fill = detail::xmlTagAttribute(tag, "fill");
        if (!fill.empty()) {
            if (fill.size() == 7 && fill[0] == '#') {
                for (int c = 0; c < 3; ++c) {
                    try {
                        marker.fill[c] = std::stoi(fill.substr(1 + c * 2, 2), nullptr, 16) / 255.0;
                    } catch (...) {
                        throw SceneError("SVG circle '" + marker.id + "' has a malformed fill color");
                    }
                }
            } else {
                throw SceneError("SVG circle '" + marker.id +
                                 "' uses an unsupported fill; only #RRGGBB is accepted");
            }
        }
        scene.circles.push_back(marker);
        pos = tagEnd + 1;
    }

    return scene;
}

// ── Preset (chronontemplate.svg_scene_catalog.v1) ────────────────────────────

struct CheckpointSpec {
    std::string id;
    Vec2 center;   // canvas pixels (framing applied)
    double radius = 0.0;
    int startFrame = 0;
    std::array<double, 4> fill{0.94, 0.17, 0.24, 1.0};
};

struct CameraSpec {
    // Semantic camera tracks: "camera.position.x" / ".y" (pan in canvas px)
    // and "camera.position.z" (dolly; zoom = 1 + z / 1000).
    Track panX;
    Track panY;
    Track dollyZ;
    bool enabled = false;
};

struct SceneSpec {
    int width = 0;
    int height = 0;
    int fps = 30;
    int frames = 0;
    std::array<double, 4> background{0, 0, 0, 1};

    std::string jobId;
    std::string assetName; // bare SVG file name, as the plan references it
    double framingScale = 1.0;   // as declared by the preset, kept for plan emission
    std::array<double, 2> framingOffset{0.0, 0.0};

    std::vector<Vec2> pathPoints; // canvas pixels, framing applied
    Vec2 svgViewBox;
    std::array<double, 4> peakStroke{0.910, 0.922, 0.941, 1.0}; // from the SVG asset
    double peakStrokeWidth = 3.0;                               // SVG user units

    Track trim;   // 0 → 1 across [start, end]
    Track marker; // 0 → progress_end across [start, end]
    std::string markerId;
    double markerSize = 0.0; // canvas px (layer size = diameter)
    std::array<double, 4> markerFill{1, 1, 1, 1};
    struct {
        bool enabled = false;
        double radius = 0.0;
        double intensity = 0.0;
        std::array<double, 4> color{1, 1, 1, 1};
    } markerGlow;

    std::vector<CheckpointSpec> checkpoints;
    CameraSpec camera;
};

namespace detail {

inline double finiteNumber(const nlohmann::json& j, const std::string& what) {
    if (!j.is_number()) throw SceneError(what + " must be a number");
    const double v = j.get<double>();
    if (!std::isfinite(v)) throw SceneError(what + " must be finite");
    return v;
}

inline std::array<double, 4> rgbaArray(const nlohmann::json& j, const std::string& what) {
    if (!j.is_array() || j.size() != 4) {
        throw SceneError(what + " must be four RGBA values");
    }
    std::array<double, 4> out{};
    for (std::size_t i = 0; i < 4; ++i) {
        out[i] = finiteNumber(j[i], what);
        if (out[i] < 0.0 || out[i] > 1.0) {
            throw SceneError(what + " values must be within [0,1]");
        }
    }
    return out;
}

inline Track parseTrack(const nlohmann::json& j, const std::string& what) {
    if (!j.is_object() || !j.contains("keyframes") || !j["keyframes"].is_array() ||
        j["keyframes"].empty()) {
        throw SceneError(what + " needs a non-empty keyframes array");
    }
    Track track;
    track.easing = j.value("easing", "linear");
    easingValue(track.easing, 0.5); // validate the name now, not at frame time
    int previous = -1;
    for (const auto& key : j["keyframes"]) {
        if (!key.contains("frame") || !key.contains("value")) {
            throw SceneError(what + " keyframes need frame and value");
        }
        const int frame = key["frame"].get<int>();
        const double value = finiteNumber(key["value"], what + " keyframe value");
        if (frame < 0 || frame <= previous) {
            throw SceneError(what + " keyframes must have increasing non-negative frames");
        }
        previous = frame;
        track.keyframes.emplace_back(frame, value);
    }
    return track;
}

} // namespace detail

// Loads and validates the scene preset. Every failure is an explicit
// SceneError: missing fields, out-of-range values and unknown ids.
inline SceneSpec loadSceneSpec(const std::string& svgPath, const std::string& presetPath) {
    std::ifstream file(presetPath);
    if (!file.is_open()) {
        throw SceneError("cannot open scene preset: " + presetPath);
    }
    nlohmann::json preset;
    try {
        file >> preset;
    } catch (const std::exception& e) {
        throw SceneError("scene preset is not valid JSON: " + std::string(e.what()));
    }

    if (preset.value("schema", "") != "chronontemplate.svg_scene_catalog.v1") {
        throw SceneError("unsupported scene preset schema (expected chronontemplate.svg_scene_catalog.v1)");
    }

    SceneSpec spec;
    spec.jobId = preset.value("id", "svg_peak_scene");

    // canvas
    const auto& canvas = preset.at("canvas");
    spec.width = canvas.at("width").get<int>();
    spec.height = canvas.at("height").get<int>();
    spec.fps = canvas.at("fps").get<int>();
    spec.frames = canvas.at("duration_frames").get<int>();
    if (std::min({spec.width, spec.height, spec.fps, spec.frames}) <= 0) {
        throw SceneError("canvas dimensions, fps and duration must be positive");
    }
    spec.background = detail::rgbaArray(canvas.at("background"), "canvas background");

    // timing blocks
    const auto& trim = preset.at("trim");
    const auto& marker = preset.at("marker");
    const int trimStart = trim.at("start_frame").get<int>();
    const int trimEnd = trim.at("end_frame").get<int>();
    const int markerStart = marker.at("start_frame").get<int>();
    const int markerEnd = marker.at("end_frame").get<int>();
    if (!(0 <= trimStart && trimStart < trimEnd && 0 <= markerStart && markerStart < markerEnd)) {
        throw SceneError("trim and marker keyframes must be ordered within the canvas duration");
    }
    const double progressEnd = detail::finiteNumber(marker.at("progress_end"), "marker progress_end");
    if (progressEnd < 0.0 || progressEnd > 1.0) {
        throw SceneError("marker progress_end must be within [0,1]");
    }
    spec.trim.easing = trim.value("easing", "linear");
    spec.marker.easing = marker.value("easing", "linear");
    easingValue(spec.trim.easing, 0.5);   // validate names up front (SVG-08)
    easingValue(spec.marker.easing, 0.5);
    spec.trim.keyframes = {{trimStart, 0.0}, {trimEnd, 1.0}};
    spec.marker.keyframes = {{markerStart, 0.0}, {markerEnd, progressEnd}};
    if (trimEnd >= spec.frames || markerEnd >= spec.frames) {
        throw SceneError("trim and marker keyframes must fit within the canvas duration");
    }

    spec.markerId = marker.at("id").get<std::string>();
    spec.markerSize = detail::finiteNumber(marker.at("size"), "marker size");
    if (spec.markerSize < 0.5 || spec.markerSize > 512.0) {
        throw SceneError("marker size must be within [0.5,512]");
    }
    spec.markerFill = detail::rgbaArray(marker.at("fill"), "marker fill");
    const auto& glow = marker.at("glow");
    spec.markerGlow.enabled = glow.value("enabled", false);
    if (spec.markerGlow.enabled) {
        spec.markerGlow.radius = detail::finiteNumber(glow.at("radius"), "marker glow radius");
        spec.markerGlow.intensity = detail::finiteNumber(glow.at("intensity"), "marker glow intensity");
        if (spec.markerGlow.radius < 0.0 || spec.markerGlow.radius > 256.0 ||
            spec.markerGlow.intensity < 0.0 || spec.markerGlow.intensity > 4.0) {
            throw SceneError("marker glow is outside supported bounds");
        }
        spec.markerGlow.color = detail::rgbaArray(glow.at("color"), "marker glow color");
    }

    // framing → canvas mapping (identical to documentary_svg_peak_registry.py)
    const auto& framing = preset.at("framing");
    const double scale = detail::finiteNumber(framing.at("scale"), "framing scale");
    if (scale < 0.01 || scale > 100.0) {
        throw SceneError("framing scale is outside supported bounds");
    }
    const auto& offset = framing.at("offset");
    if (!offset.is_array() || offset.size() != 2) {
        throw SceneError("framing offset must be two values");
    }
    const double offsetX = detail::finiteNumber(offset[0], "framing offset");
    const double offsetY = detail::finiteNumber(offset[1], "framing offset");
    if (std::max(std::abs(offsetX), std::abs(offsetY)) > 100000.0) {
        throw SceneError("framing offset is outside supported bounds");
    }
    spec.framingScale = scale;
    spec.framingOffset = {offsetX, offsetY};

    // geometry from the SVG (the only place scene coordinates live)
    const SvgScene svg = loadSvgScene(svgPath);
    spec.svgViewBox = svg.viewBox;
    const std::size_t slash = svgPath.find_last_of("/\\");
    spec.assetName = slash == std::string::npos ? svgPath : svgPath.substr(slash + 1);

    const double sx = spec.width / svg.viewBox.x;
    const double sy = spec.height / svg.viewBox.y;
    auto toCanvas = [&](const Vec2& p) {
        return Vec2{spec.width / 2.0 + (p.x * sx - spec.width / 2.0) * scale + offsetX,
                    spec.height / 2.0 + (p.y * sy - spec.height / 2.0) * scale + offsetY};
    };
    spec.pathPoints.reserve(svg.peakPoints.size());
    for (const Vec2& point : svg.peakPoints) {
        spec.pathPoints.push_back(toCanvas(point));
    }
    spec.peakStroke = svg.peakStroke;
    spec.peakStrokeWidth = svg.peakStrokeWidth * sx * scale;

    // checkpoints: position/radius from SVG circles, timing from the preset
    if (preset.contains("checkpoints")) {
        if (!preset["checkpoints"].is_array()) {
            throw SceneError("preset checkpoints must be an array");
        }
        for (const auto& entry : preset["checkpoints"]) {
            CheckpointSpec checkpoint;
            checkpoint.id = entry.at("id").get<std::string>();
            checkpoint.startFrame = entry.at("start_frame").get<int>();
            if (checkpoint.startFrame < 0 || checkpoint.startFrame >= spec.frames) {
                throw SceneError("checkpoint '" + checkpoint.id + "' start_frame is outside the canvas duration");
            }
            const auto found = std::find_if(svg.circles.begin(), svg.circles.end(),
                                            [&](const SvgMarker& m) { return m.id == checkpoint.id; });
            if (found == svg.circles.end()) {
                throw SceneError("checkpoint '" + checkpoint.id + "' has no matching <circle> in the SVG");
            }
            checkpoint.center = toCanvas(found->center);
            checkpoint.radius = found->r * (sx + sy) * 0.5 * scale;
            checkpoint.fill = found->fill;
            spec.checkpoints.push_back(checkpoint);
        }
    }

    // optional semantic camera
    if (preset.contains("camera")) {
        const auto& camera = preset["camera"];
        if (!camera.contains("tracks") || !camera["tracks"].is_array()) {
            throw SceneError("preset camera needs a tracks array");
        }
        for (const auto& entry : camera["tracks"]) {
            const std::string property = entry.at("property").get<std::string>();
            Track track = detail::parseTrack(entry, "camera track " + property);
            if (property == "camera.position.x") spec.camera.panX = track;
            else if (property == "camera.position.y") spec.camera.panY = track;
            else if (property == "camera.position.z") spec.camera.dollyZ = track;
            else throw SceneError("unknown camera track property: " + property);
            spec.camera.enabled = true;
        }
    }

    return spec;
}

// ── Camera (one transform shared by every scene element) ─────────────────────

struct CameraState {
    double panX = 0.0;
    double panY = 0.0;
    double zoom = 1.0;
};

inline CameraState cameraAt(const SceneSpec& spec, int frame) {
    CameraState state;
    if (!spec.camera.enabled) return state;
    state.panX = spec.camera.panX.keyframes.empty() ? 0.0 : spec.camera.panX.valueAt(frame);
    state.panY = spec.camera.panY.keyframes.empty() ? 0.0 : spec.camera.panY.valueAt(frame);
    const double dollyZ = spec.camera.dollyZ.keyframes.empty() ? 0.0 : spec.camera.dollyZ.valueAt(frame);
    state.zoom = std::max(0.01, 1.0 + dollyZ / 1000.0);
    return state;
}

// World (canvas) → screen. Every element that shares the scene space must go
// through this exact function (FX-08).
inline Vec2 applyCamera(const CameraState& cam, const Vec2& world, const Vec2& center) {
    return {center.x + (world.x - center.x) * cam.zoom + cam.panX,
            center.y + (world.y - center.y) * cam.zoom + cam.panY};
}

// ── Polyline geometry: arc-length sampling and trim ──────────────────────────

// Independent implementations of the two canonical primitives. Both tools use
// these; the Python test suite re-derives the same math independently.
inline Vec2 samplePolyline(const std::vector<Vec2>& points, double progress) {
    if (points.empty()) throw SceneError("cannot sample an empty path");
    if (progress <= 0.0) return points.front();
    if (progress >= 1.0) return points.back();

    std::vector<double> segmentLengths;
    double total = 0.0;
    for (std::size_t i = 0; i + 1 < points.size(); ++i) {
        const double d = vecDistance(points[i], points[i + 1]);
        segmentLengths.push_back(d);
        total += d;
    }
    if (total <= 0.0) return points.front();

    double remaining = progress * total;
    for (std::size_t i = 0; i < segmentLengths.size(); ++i) {
        if (remaining <= segmentLengths[i]) {
            const double t = segmentLengths[i] > 0.0 ? remaining / segmentLengths[i] : 0.0;
            return {points[i].x + (points[i + 1].x - points[i].x) * t,
                    points[i].y + (points[i + 1].y - points[i].y) * t};
        }
        remaining -= segmentLengths[i];
    }
    return points.back();
}

// Trim Path: the partial polyline covering [0, progress] of the total length.
inline std::vector<Vec2> trimPolyline(const std::vector<Vec2>& points, double progress) {
    std::vector<Vec2> out;
    if (points.empty() || progress <= 0.0) return out;
    out.push_back(points.front());
    if (progress >= 1.0) {
        out.insert(out.end(), points.begin() + 1, points.end());
        return out;
    }

    std::vector<double> segmentLengths;
    double total = 0.0;
    for (std::size_t i = 0; i + 1 < points.size(); ++i) {
        const double d = vecDistance(points[i], points[i + 1]);
        segmentLengths.push_back(d);
        total += d;
    }

    double remaining = progress * total;
    for (std::size_t i = 0; i < segmentLengths.size(); ++i) {
        if (remaining >= segmentLengths[i]) {
            out.push_back(points[i + 1]);
            remaining -= segmentLengths[i];
        } else if (remaining > 0.0) {
            const double t = remaining / segmentLengths[i];
            out.push_back({points[i].x + (points[i + 1].x - points[i].x) * t,
                           points[i].y + (points[i + 1].y - points[i].y) * t});
            break;
        } else {
            break;
        }
    }
    return out;
}

// Total polyline length (canvas px) — used by tests and diagnostics.
inline double polylineLength(const std::vector<Vec2>& points) {
    double total = 0.0;
    for (std::size_t i = 0; i + 1 < points.size(); ++i) {
        total += vecDistance(points[i], points[i + 1]);
    }
    return total;
}

} // namespace chronon::svg_parity
