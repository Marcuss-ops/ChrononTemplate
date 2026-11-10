// Native C++ authoring for the five-category vector motion suite.
//
// The suite is authored as pure RenderPlan V3 data: tactical route/HUD,
// node graph, validation burst, technical callout, wireframe-to-solid logo.
// Python is only the render/verify/upload driver.
//
// Usage:
//   chronontemplate_emit_vector_motion_suite <output-dir>

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <initializer_list>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using json = nlohmann::ordered_json;

namespace {

constexpr int WIDTH = 1920;
constexpr int HEIGHT = 1080;
constexpr int FPS = 30;
constexpr int MAX_FRAMES = 300;
constexpr double PI = 3.14159265358979323846;
constexpr double CX = WIDTH / 2.0;
constexpr double CY = HEIGHT / 2.0;

json rgba(const std::string& hex, double alpha = 1.0) {
    auto nibble = [](char c) -> int {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        return 0;
    };
    auto channel = [&](std::size_t offset) {
        return (nibble(hex[offset]) * 16 + nibble(hex[offset + 1])) / 255.0;
    };
    return json::array({channel(1), channel(3), channel(5), alpha});
}

json pair(double x, double y) { return json::array({x, y}); }

// Shape layers are positioned relative to the canvas centre, while text and
// colour layers use canvas coordinates. Keep this conversion in one place.
json offsetPair(double x, double y) { return pair(x - CX, y - CY); }

json keyframe(int frame, json value) {
    return json{{"frame", frame}, {"value", std::move(value)}};
}

json track(const std::string& property, json keys,
           const std::string& easing = "out_cubic") {
    return json{{"property", property}, {"easing", easing},
                {"keyframes", std::move(keys)}};
}

json animation(std::initializer_list<json> tracks) {
    return json{{"tracks", json(tracks)}};
}

json trimOperator(int begin, int end, double from = 0.0, double to = 1.0,
                  const std::string& easing = "in_out_cubic") {
    json keys = json::array({
        keyframe(begin, json::array({0.0, from, 0.0})),
        keyframe(end, json::array({0.0, to, 0.0})),
    });
    return json{{"kind", "trim"},
                {"params", json{{"start", 0.0}, {"end", 1.0},
                                {"offset", 0.0},
                                {"animation", json{{"easing", easing},
                                                   {"keyframes", keys}}}}}};
}

json glowEffect(double radius, const std::string& hex, double intensity = 0.55) {
    return json{{"type", "glow"}, {"radius", radius},
                {"intensity", intensity}, {"color", rgba(hex, 1.0)}};
}

json vignette(double amount = 0.34, double radius = 0.7) {
    return json{{"type", "vignette"}, {"radius", radius},
                {"softness", 0.72}, {"amount", amount},
                {"color", rgba("#000000", 1.0)}};
}

json base(const std::string& id, const std::string& type, double x, double y,
          double w, double h, int start, int duration, double opacity = 1.0) {
    return json{{"id", id}, {"type", type}, {"position", pair(x, y)},
                {"size", pair(w, h)}, {"start_frame", start},
                {"duration_frames", duration}, {"opacity", opacity}};
}

json colorLayer(const std::string& id, const std::string& hex, int frames,
                double opacity = 1.0) {
    json layer = base(id, "color", 0, 0, WIDTH, HEIGHT, 0, frames, opacity);
    layer["color"] = rgba(hex);
    layer["position"] = pair(0, 0);
    layer["effects"] = json::array({vignette()});
    return layer;
}

json textLayer(const std::string& id, const std::string& text, double x, double y,
               double w, double h, const std::string& font, double size,
               const std::string& hex, const std::string& align, int start,
               int duration, double opacity = 1.0, double glowRadius = 0.0) {
    // A zero here means "let the start_frame own the reveal"; keeping it at
    // zero would make the label permanently invisible.
    if (opacity <= 0.0) opacity = 1.0;
    json layer = base(id, "text", x, y, w, h, start, duration, opacity);
    layer["text"] = text;
    json style = {{"font", font}, {"font_size", size},
                  {"fill", hex}, {"text_align", align},
                  {"min_font_size", size}, {"max_font_size", size},
                  {"fit_mode", "shrink_only"}};
    if (glowRadius > 0.0) {
        style["glow"] = json{{"radius", glowRadius}, {"intensity", 0.5},
                             {"color", hex}};
    }
    layer["style"] = style;
    return layer;
}

json pathShape(const std::string& id, double x, double y, double w, double h,
               json commands, const std::string& stroke, double width,
               int start, int duration, double opacity = 1.0,
               double fillAlpha = 0.0, double glowRadius = 0.0) {
    json shape = {{"type", "path"}, {"path", std::move(commands)},
                  {"fill", rgba("#000000", fillAlpha)}};
    if (width > 0.0) {
        shape["stroke"] = json{{"color", rgba(stroke)},
                                {"width", width},
                                {"cap", "round"},
                                {"join", "round"}};
    }
    json layer = base(id, "shape", x - CX, y - CY, w, h, start, duration,
                      opacity);
    layer["shape"] = shape;
    if (glowRadius > 0.0) {
        layer["effects"] = json::array({glowEffect(glowRadius, stroke)});
    }
    return layer;
}

json ellipseShape(const std::string& fill, double fillAlpha,
                  const std::string& stroke, double strokeWidth) {
    json shape = {{"type", "ellipse"}};
    if (fillAlpha > 0.0) shape["fill"] = rgba(fill, fillAlpha);
    if (strokeWidth > 0.0) {
        shape["stroke"] = json{{"color", rgba(stroke)},
                               {"width", strokeWidth}};
    }
    return shape;
}

json ellipseLayer(const std::string& id, double x, double y, double w, double h,
                  const std::string& fill, double fillAlpha,
                  const std::string& stroke, double strokeWidth, int start,
                  int duration, double opacity = 1.0,
                  double glowRadius = 0.0) {
    json layer = base(id, "shape", x - CX, y - CY, w, h, start, duration,
                      opacity);
    layer["shape"] = ellipseShape(fill, fillAlpha, stroke, strokeWidth);
    if (glowRadius > 0.0) {
        layer["effects"] = json::array(
            {glowEffect(glowRadius, stroke.empty() ? fill : stroke)});
    }
    return layer;
}

json roundedRectLayer(const std::string& id, double x, double y, double w,
                      double h, double radius, const std::string& fill,
                      double fillAlpha, const std::string& stroke,
                      double strokeWidth, int start, int duration,
                      double opacity = 1.0) {
    json shape = {{"type", "rounded_rect"}, {"radius", radius},
                  {"fill", rgba(fill, fillAlpha)}};
    if (strokeWidth > 0.0) {
        shape["stroke"] = json{{"color", rgba(stroke)},
                               {"width", strokeWidth}};
    }
    json layer = base(id, "shape", x - CX, y - CY, w, h, start, duration,
                      opacity);
    layer["shape"] = shape;
    return layer;
}

json ringSegmentLayer(const std::string& id, double x, double y, double size,
                      double innerRatio, double startDeg, double sweepDeg,
                      const std::string& stroke, double width, int start,
                      int duration, double opacity = 1.0) {
    json shape = {{"type", "ring_segment"},
                  {"fill", rgba("#000000", 0.0)},
                  {"inner_radius_ratio", innerRatio},
                  {"start_degrees", startDeg},
                  {"sweep_degrees", sweepDeg},
                  {"stroke", json{{"color", rgba(stroke)}, {"width", width}}}};
    json layer = base(id, "shape", x, y, size, size, start, duration, opacity);
    layer["shape"] = shape;
    return layer;
}

json moveTo(double x, double y) {
    return json{{"type", "move_to"}, {"point", pair(x, y)}};
}

json lineTo(double x, double y) {
    return json{{"type", "line_to"}, {"point", pair(x, y)}};
}

json cubicTo(double c1x, double c1y, double c2x, double c2y, double x,
             double y) {
    return json{{"type", "cubic_to"}, {"control1", pair(c1x, c1y)},
                {"control2", pair(c2x, c2y)}, {"point", pair(x, y)}};
}

double rad(double degrees) { return degrees * PI / 180.0; }

json arcPath(double radius, double startDeg, double endDeg, int segments) {
    json commands = json::array();
    const double step = (endDeg - startDeg) / segments;
    for (int i = 0; i <= segments; ++i) {
        const double angle = rad(startDeg + step * i);
        const double x = std::cos(angle) * radius;
        const double y = std::sin(angle) * radius;
        if (i == 0) {
            commands.push_back(moveTo(x, y));
            continue;
        }
        const double k = 4.0 / 3.0 * std::tan(rad(step) / 4.0) * radius;
        const double a0 = rad(startDeg + step * (i - 1));
        const double a1 = angle;
        commands.push_back(cubicTo(
            std::cos(a0) * radius - std::sin(a0) * k,
            std::sin(a0) * radius + std::cos(a0) * k,
            std::cos(a1) * radius + std::sin(a1) * k,
            std::sin(a1) * radius - std::cos(a1) * k, x, y));
    }
    return commands;
}

json circlePath(double radius, int segments = 8) {
    return arcPath(radius, -90.0, 270.0, segments);
}

struct Bezier {
    double ax, ay, bx, by, cx, cy, dx, dy;
};

json bezierCommands(const std::vector<Bezier>& segments) {
    json commands = json::array();
    for (std::size_t i = 0; i < segments.size(); ++i) {
        const Bezier& s = segments[i];
        if (i == 0) commands.push_back(moveTo(s.ax, s.ay));
        commands.push_back(cubicTo(s.bx, s.by, s.cx, s.cy, s.dx, s.dy));
    }
    return commands;
}

json bezierCommandsCentered(const std::vector<Bezier>& segments) {
    json commands = json::array();
    for (std::size_t i = 0; i < segments.size(); ++i) {
        const Bezier& s = segments[i];
        if (i == 0) commands.push_back(moveTo(s.ax - CX, s.ay - CY));
        commands.push_back(cubicTo(s.bx - CX, s.by - CY, s.cx - CX,
                                   s.cy - CY, s.dx - CX, s.dy - CY));
    }
    return commands;
}

struct PathSampler {
    std::vector<std::pair<double, double>> points;
    std::vector<double> lengths;

    explicit PathSampler(const std::vector<Bezier>& segments, int perSegment = 96) {
        for (const Bezier& s : segments) {
            for (int i = 0; i <= perSegment; ++i) {
                if (!points.empty() && i == 0) continue;
                const double t = static_cast<double>(i) / perSegment;
                const double u = 1.0 - t;
                const double x = u * u * u * s.ax + 3 * u * u * t * s.bx +
                                 3 * u * t * t * s.cx + t * t * t * s.dx;
                const double y = u * u * u * s.ay + 3 * u * u * t * s.by +
                                 3 * u * t * t * s.cy + t * t * t * s.dy;
                if (!points.empty()) {
                    const auto& p = points.back();
                    lengths.push_back(lengths.back() +
                                      std::hypot(x - p.first, y - p.second));
                } else {
                    lengths.push_back(0.0);
                }
                points.emplace_back(x, y);
            }
        }
    }

    std::pair<double, double> at(double progress) const {
        const double target = std::clamp(progress, 0.0, 1.0) * lengths.back();
        auto it = std::lower_bound(lengths.begin(), lengths.end(), target);
        if (it == lengths.begin()) return points.front();
        if (it == lengths.end()) return points.back();
        const std::size_t i = static_cast<std::size_t>(it - lengths.begin());
        const double span = lengths[i] - lengths[i - 1];
        const double t = span > 1e-9 ? (target - lengths[i - 1]) / span : 1.0;
        const auto& a = points[i - 1];
        const auto& b = points[i];
        return {a.first + (b.first - a.first) * t,
                a.second + (b.second - a.second) * t};
    }
};

json moveTrack(const PathSampler& sampler, int begin, int end, int step = 3,
               double from = 0.0, double to = 1.0) {
    json keys = json::array();
    for (int frame = begin; frame < end; frame += step) {
        const double u = from + (to - from) *
                                  (static_cast<double>(frame - begin) /
                                   std::max(1, end - begin));
        const auto position = sampler.at(u);
        keys.push_back(keyframe(frame, offsetPair(position.first,
                                                  position.second)));
    }
    const auto finalPoint = sampler.at(to);
    keys.push_back(keyframe(end, offsetPair(finalPoint.first, finalPoint.second)));
    return track("position", keys, "linear");
}

json gridCommands(double step, double inset) {
    json commands = json::array();
    for (double x = inset; x <= WIDTH - inset + 0.5; x += step) {
        commands.push_back(moveTo(x - CX, inset - CY));
        commands.push_back(lineTo(x - CX, HEIGHT - inset - CY));
    }
    for (double y = inset; y <= HEIGHT - inset + 0.5; y += step) {
        commands.push_back(moveTo(inset - CX, y - CY));
        commands.push_back(lineTo(WIDTH - inset - CX, y - CY));
    }
    return commands;
}

json frameBrackets(double inset = 46.0, double arm = 42.0) {
    json commands = json::array();
    const std::array<std::array<double, 2>, 4> corners{{
        {inset, inset}, {WIDTH - inset, inset},
        {WIDTH - inset, HEIGHT - inset}, {inset, HEIGHT - inset}}};
    const std::array<double, 4> sx{{1, -1, -1, 1}};
    const std::array<double, 4> sy{{1, 1, -1, -1}};
    for (std::size_t i = 0; i < corners.size(); ++i) {
        const double x = corners[i][0] - CX;
        const double y = corners[i][1] - CY;
        commands.push_back(moveTo(x + sx[i] * arm, y));
        commands.push_back(lineTo(x, y));
        commands.push_back(lineTo(x, y + sy[i] * arm));
    }
    return commands;
}

std::string padded(int value) {
    return value < 10 ? "0" + std::to_string(value) : std::to_string(value);
}

struct Clip {
    int index;
    std::string slug;
    std::string label;
    std::string category;
    std::string note;
    std::string background;
    int frames;
    json plan;
};

std::string videoName(const Clip& clip) {
    const int seconds = static_cast<int>(std::lround(clip.frames / double(FPS)));
    return "VectorMotion_" + padded(clip.index) + "_" + clip.slug +
           "_1920x1080_" + std::to_string(seconds) + "s_v1.mp4";
}

std::string planName(const Clip& clip) {
    return padded(clip.index) + "_" + clip.slug + ".plan.json";
}

json finishPlan(const Clip& clip) {
    json plan = clip.plan;
    plan["schema"] = "chronon.render-plan.v3";
    plan["version"] = 3;
    plan["job_id"] = "vector_motion_" + padded(clip.index) + "_" + clip.slug;
    plan["canvas"] = json{{"width", WIDTH}, {"height", HEIGHT},
                          {"fps_num", FPS}, {"fps_den", 1},
                          {"duration_frames", clip.frames}};
    plan["output"] = json{{"path", videoName(clip)},
                          {"format", "mp4"}, {"codec", "h264"}};
    return plan;
}

json makeTacticalRoute() {
    const int frames = 300;
    json layers = json::array();
    layers.push_back(colorLayer("backdrop", "#05080D", frames));

    layers.push_back(pathShape("grid", CX, CY, WIDTH, HEIGHT,
                               gridCommands(80.0, 40.0), "#213245", 1.0, 0,
                               frames, 0.32));
    layers.push_back(pathShape("hud_frame", CX, CY, WIDTH, HEIGHT,
                               frameBrackets(), "#7FD4FF", 1.2, 0, frames,
                               0.45));
    layers.push_back(pathShape("landmass_fill", CX, CY, WIDTH, HEIGHT,
                               json::array({
                                   moveTo(-620, 170), lineTo(-430, 40),
                                   lineTo(-160, -20), lineTo(330, -205),
                                   lineTo(520, -80), lineTo(620, 120),
                                   lineTo(160, 330),
                               }), "#3E7F68", 0.0, 0, frames, 0.85, 0.055));
    layers.push_back(pathShape("map_landmass", CX, CY, WIDTH, HEIGHT,
                               json::array({
                                   moveTo(-620, 170), lineTo(-430, 40),
                                   lineTo(-160, -20), lineTo(80, -150),
                                   lineTo(330, -205), lineTo(520, -80),
                                   lineTo(620, 120), lineTo(430, 290),
                                   lineTo(160, 330), lineTo(-90, 280),
                                   lineTo(-360, 330), lineTo(-560, 250),
                                   lineTo(-620, 170),
                               }), "#3E7F68", 1.6, 0, frames, 0.85, 0.0));

    const std::vector<Bezier> route{{
        {320, 740, 430, 700, 480, 650, 570, 610},
        {570, 610, 670, 580, 700, 690, 775, 660},
        {775, 660, 875, 625, 895, 515, 985, 480},
        {985, 480, 1085, 445, 1125, 550, 1215, 520},
        {1215, 520, 1320, 480, 1370, 395, 1470, 365},
        {1470, 365, 1530, 348, 1575, 405, 1625, 430},
    }};
    PathSampler sampler(route);

    json trail = pathShape("route_trail", CX, CY, WIDTH, HEIGHT,
                           bezierCommandsCentered(route), "#46C79A", 2.0, 0, frames,
                           0.28);
    trail["shape"]["stroke"]["dash_array"] = json::array({10.0, 9.0});
    trail["shape"]["stroke"]["dash_offset"] = 0.0;
    trail["animation"] = animation({track("opacity", json::array({
        keyframe(0, 0.0), keyframe(18, 0.28), keyframe(frames - 1, 0.28)}))});
    layers.push_back(trail);

    json underlay = pathShape("route_glow", CX, CY, WIDTH, HEIGHT,
                              bezierCommandsCentered(route), "#6FFFD2", 9.0, 0, frames,
                              1.0);
    underlay["opacity"] = 0.16;
    underlay["blend_mode"] = "screen";
    underlay["shape"]["operators"] = json::array({trimOperator(20, 155)});
    layers.push_back(underlay);

    json routeLine = pathShape("route_line", CX, CY, WIDTH, HEIGHT,
                               bezierCommandsCentered(route), "#9CFFDF", 3.2, 0, frames);
    routeLine["shape"]["operators"] = json::array({trimOperator(20, 155)});
    routeLine["effects"] = json::array({glowEffect(12, "#6FFFD2", 0.5)});
    layers.push_back(routeLine);

    json marker = ellipseLayer("route_marker", 320, 740, 18, 18, "#E9FFF7",
                               1.0, "#6FFFD2", 2.0, 0, frames, 1.0, 18.0);
    marker["animation"] = animation({
        moveTrack(sampler, 20, 155, 3),
        track("opacity", json::array({keyframe(0, 0.0), keyframe(20, 1.0),
                                      keyframe(frames - 1, 1.0)})),
        track("scale", json::array({keyframe(20, pair(0.55, 0.55)),
                                    keyframe(30, pair(1.0, 1.0)),
                                    keyframe(frames - 1, pair(1.0, 1.0))})),
    });
    layers.push_back(marker);

    for (int i = 0; i < 3; ++i) {
        const int begin = 150 + i * 17;
        json ping = pathShape("radar_ping_" + std::to_string(i), 1470, 365,
                              140, 140, circlePath(70), "#6FFFD2", 2.0,
                              begin, 70, 0.85, 0.0, 8.0);
        ping["animation"] = animation({
            track("scale", json::array({keyframe(begin, pair(0.25, 0.25)),
                                        keyframe(begin + 58, pair(4.4, 4.4))})),
            track("opacity", json::array({keyframe(begin, 0.8),
                                          keyframe(begin + 58, 0.0)})),
        });
        layers.push_back(ping);
    }

    json reticle = pathShape("target_reticle", 1470, 365, 220, 220,
                             json::array({
                                 moveTo(-82, -82), lineTo(-50, -82),
                                 moveTo(-82, -82), lineTo(-82, -50),
                                 moveTo(82, -82), lineTo(50, -82),
                                 moveTo(82, -82), lineTo(82, -50),
                                 moveTo(82, 82), lineTo(50, 82),
                                 moveTo(82, 82), lineTo(82, 50),
                                 moveTo(-82, 82), lineTo(-50, 82),
                                 moveTo(-82, 82), lineTo(-82, 50),
                             }), "#E9FFF7", 3.0, 0, frames);
    reticle["animation"] = animation({
        track("scale", json::array({keyframe(105, pair(1.8, 1.8)),
                                    keyframe(140, pair(1.0, 1.0)),
                                    keyframe(frames - 1, pair(1.0, 1.0))}),
              "out_back"),
        track("rotation", json::array({keyframe(105, json::array({0.0, 0.0, 45.0})),
                                       keyframe(140, json::array({0.0, 0.0, 0.0})),
                                       keyframe(frames - 1,
                                                json::array({0.0, 0.0, 0.0}))})),
        track("opacity", json::array({keyframe(105, 0.0), keyframe(116, 1.0),
                                      keyframe(frames - 1, 1.0)})),
    });
    layers.push_back(reticle);

    json tickRing = pathShape("target_tick_ring", 1470, 365, 172, 172,
                              circlePath(86), "#7FD4FF", 2.0, 0, frames,
                              0.55);
    tickRing["shape"]["stroke"]["dash_array"] = json::array({5.0, 9.0});
    tickRing["animation"] = animation({
        track("scale", json::array({keyframe(0, pair(1.0, 1.0)),
                                    keyframe(150, pair(1.06, 1.06)),
                                    keyframe(frames - 1, pair(1.0, 1.0))}),
              "in_out_sine"),
        track("opacity", json::array({keyframe(0, 0.30),
                                      keyframe(150, 0.60),
                                      keyframe(frames - 1, 0.45)})),
    });
    layers.push_back(tickRing);
    layers.push_back(ellipseLayer("target_dot", 1470, 365, 10, 10, "#FFD166",
                                  1.0, "#FFD166", 0.0, 140, 160, 0.0, 16.0));

    layers.push_back(textLayer("top_left", "TACTICAL TRACE // SECTOR 07", 300,
                               92, 560, 40, "assets/fonts/DejaVuSansMono-Bold.ttf",
                               24, "#8FD6FF", "left", 0, frames, 0.85));
    layers.push_back(textLayer("top_right", "OSINT / LIVE", 1640, 92, 360, 40,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 24,
                               "#FFC46B", "right", 0, frames, 0.8));
    layers.push_back(textLayer("target_label", "TARGET LOCKED", 1470, 285, 420,
                               42, "assets/fonts/DejaVuSansMono-Bold.ttf", 22,
                               "#E9FFF7", "center", 140, 160, 0.0));
    layers.push_back(textLayer("target_coords", "35.6895 N / 139.6917 E", 1470,
                               318, 460, 38,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 19,
                               "#9CFFDF", "center", 148, 152, 0.0));
    layers.push_back(textLayer("bottom_left", "ROUTE 04 / SOURCE TO DESTINATION",
                               382, 1002, 720, 40,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 20,
                               "#7E9BAF", "left", 36, frames - 36, 0.0));
    layers.push_back(textLayer("bottom_right", "TRACE 00:09:58:12", 1620, 1002,
                               400, 40, "assets/fonts/DejaVuSansMono-Bold.ttf",
                               20, "#7E9BAF", "right", 0, frames, 0.6));

    json plan = {{"layers", layers}};
    return plan;
}

json makeNodeGraph() {
    const int frames = 240;
    json layers = json::array();
    layers.push_back(colorLayer("backdrop", "#060A14", frames, 1.0));
    layers.push_back(pathShape("grid", CX, CY, WIDTH, HEIGHT,
                               gridCommands(96.0, 48.0), "#1F3B57", 1.0, 0,
                               frames, 0.45));

    for (double radius : {190.0, 340.0, 500.0}) {
        layers.push_back(pathShape("orbit_" + std::to_string(int(radius)),
                                   CX, CY, radius * 2, radius * 2,
                                   circlePath(radius), "#1F4E73", 1.0, 0,
                                   frames, 0.30));
    }

    struct Branch {
        Bezier curve;
        int drawStart;
        int drawEnd;
        const char* name;
    };
    const std::vector<Branch> branches = {
        {{CX, CY, 820, 470, 650, 380, 470, 300}, 20, 70, "SHELL CO"},
        {{CX, CY, 1100, 470, 1270, 390, 1450, 320}, 32, 82, "TRUST 02"},
        {{CX, CY, 820, 610, 650, 700, 500, 800}, 44, 94, "OFFSHORE"},
        {{CX, CY, 1100, 610, 1270, 690, 1430, 760}, 56, 106, "LEDGER"},
        {{CX, CY, 960, 640, 960, 760, 960, 880}, 68, 118, "WITNESS"},
    };
    const std::array<std::array<double, 2>, 5> nodes{{
        {470, 300}, {1450, 320}, {500, 800}, {1430, 760}, {960, 880}}};

    for (std::size_t i = 0; i < branches.size(); ++i) {
        const Branch& branch = branches[i];
        json edge = pathShape("edge_" + std::to_string(i), CX, CY, WIDTH, HEIGHT,
                              bezierCommandsCentered({branch.curve}),
                              "#8FE9FF", 2.6, 0, frames);
        edge["shape"]["operators"] =
            json::array({trimOperator(branch.drawStart, branch.drawEnd)});
        layers.push_back(edge);

    }

    json core = ellipseLayer("core_node", CX, CY, 96, 96, "#0B1B2C", 1.0,
                             "#8FE9FF", 3.0, 0, frames, 1.0, 0.0);
    core["animation"] = animation({
        track("scale", json::array({keyframe(0, pair(0.15, 0.15)),
                                    keyframe(14, pair(1.10, 1.10)),
                                    keyframe(24, pair(1.0, 1.0)),
                                    keyframe(frames - 1, pair(1.0, 1.0))}),
              "out_back"),
        track("opacity", json::array({keyframe(0, 0.0), keyframe(8, 1.0),
                                      keyframe(frames - 1, 1.0)})),
    });
    layers.push_back(core);
    layers.push_back(ellipseLayer("core_dot", CX, CY, 18, 18, "#FFD166", 1.0,
                                  "#FFD166", 0.0, 8, 232, 1.0, 0.0));

    json coreRing = pathShape("core_ring", CX, CY, 196, 196,
                              circlePath(98), "#7FD4FF", 1.6, 0, frames,
                              0.45);
    coreRing["shape"]["stroke"]["dash_array"] = json::array({4.0, 10.0});
    coreRing["animation"] = animation({
        track("scale", json::array({keyframe(0, pair(0.92, 0.92)),
                                    keyframe(120, pair(1.06, 1.06)),
                                    keyframe(frames - 1, pair(0.96, 0.96))}),
              "in_out_sine"),
    });
    layers.push_back(coreRing);

    for (std::size_t i = 0; i < nodes.size(); ++i) {
        const int begin = branches[i].drawEnd - 4;
        json node = ellipseLayer("node_" + std::to_string(i), nodes[i][0],
                                 nodes[i][1], 54, 54, "#0B1B2C", 1.0, "#8FE9FF",
                                 2.4, 0, frames, 1.0, 0.0);
        node["animation"] = animation({
            track("scale", json::array({keyframe(begin, pair(0.01, 0.01)),
                                        keyframe(begin + 12, pair(1.12, 1.12)),
                                        keyframe(begin + 20, pair(1.0, 1.0)),
                                        keyframe(frames - 1, pair(1.0, 1.0))}),
                  "out_back"),
            track("opacity", json::array({keyframe(begin, 0.0),
                                          keyframe(begin + 4, 1.0),
                                          keyframe(frames - 1, 1.0)})),
        });
        layers.push_back(node);
    }

    layers.push_back(textLayer("title", "NETWORK / FLOW", CX, 100, 620, 50,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 26,
                               "#BFEAFF", "center", 0, frames, 0.85));
    layers.push_back(textLayer("counter", "5 NODES  /  5 EDGES  /  4.2M TRACKED",
                               960, 1002, 800, 40,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 19,
                               "#7E9BAF", "center", 120, 120, 0.0));
    layers.push_back(textLayer("amount", "TRANSFER +4.2M", 1450, 430, 320, 36,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 19,
                               "#FFD166", "center", 90, 150, 0.0));

    // Endpoint accents and branch labels: the graph is not finished until the
    // five destinations carry both. Keep the dots in one pass and the labels
    // in a second one so the layer order matches the authored plan.
    for (std::size_t i = 0; i < nodes.size(); ++i) {
        const int begin = branches[i].drawEnd - 4;
        json dot = ellipseLayer("dot_" + std::to_string(i), nodes[i][0],
                                nodes[i][1], 12, 12, "#FFD166", 1.0, "", 0.0,
                                begin, frames - begin);
        dot["animation"] = animation({
            track("scale", json::array({keyframe(begin, pair(0.01, 0.01)),
                                        keyframe(begin + 10, pair(1.15, 1.15)),
                                        keyframe(begin + 16, pair(1.0, 1.0)),
                                        keyframe(frames - 1, pair(1.0, 1.0))}),
                  "out_back"),
            track("opacity", json::array({keyframe(begin, 0.0),
                                          keyframe(begin + 4, 1.0),
                                          keyframe(frames - 1, 1.0)})),
        });
        layers.push_back(dot);
    }

    for (std::size_t i = 0; i < nodes.size(); ++i) {
        const int begin = branches[i].drawEnd;
        json label = textLayer("label_" + std::to_string(i), branches[i].name,
                               nodes[i][0], nodes[i][1] + 62, 320, 32,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 18,
                               "#8FE9FF", "center", begin, frames - begin);
        label["animation"] = animation({
            track("opacity", json::array({keyframe(begin, 0.0),
                                          keyframe(begin + 6, 1.0),
                                          keyframe(frames - 1, 1.0)})),
        });
        layers.push_back(label);
    }

    return json{{"layers", layers}};
}

json makeValidationBurst() {
    const int frames = 180;
    json layers = json::array();
    layers.push_back(colorLayer("backdrop", "#05090C", frames, 1.0));
    layers.push_back(pathShape("grid", CX, CY, WIDTH, HEIGHT,
                               gridCommands(120.0, 60.0), "#13302C", 1.0, 0,
                               frames, 0.24));

    const double cx = 960, cy = 500;
    json circleGlow = pathShape("circle_glow", cx, cy, 420, 420,
                                circlePath(160), "#6FFFD2", 11.0, 0, frames,
                                0.28);
    circleGlow["blend_mode"] = "screen";
    circleGlow["shape"]["operators"] = json::array({trimOperator(12, 62)});
    layers.push_back(circleGlow);

    json circle = pathShape("circle", cx, cy, 420, 420, circlePath(160),
                            "#B9FFE4", 4.5, 0, frames);
    circle["shape"]["operators"] = json::array({trimOperator(12, 62)});
    circle["effects"] = json::array({glowEffect(14, "#6FFFD2", 0.45)});
    layers.push_back(circle);

    json checkGlow = pathShape("check_glow", cx, cy, 300, 300,
                               json::array({moveTo(-64, 2), lineTo(-16, 52),
                                            lineTo(80, -58)}),
                               "#6FFFD2", 22.0, 0, frames, 0.30);
    checkGlow["blend_mode"] = "screen";
    checkGlow["shape"]["operators"] = json::array({trimOperator(58, 78)});
    layers.push_back(checkGlow);

    json check = pathShape("check", cx, cy, 300, 300,
                           json::array({moveTo(-64, 2), lineTo(-16, 52),
                                        lineTo(80, -58)}),
                           "#E9FFF7", 13.0, 0, frames);
    check["shape"]["operators"] = json::array({trimOperator(58, 78)});
    check["effects"] = json::array({glowEffect(12, "#B9FFE4", 0.55)});
    check["animation"] = animation({
        track("scale", json::array({keyframe(58, pair(0.72, 0.72)),
                                    keyframe(72, pair(1.12, 1.12)),
                                    keyframe(82, pair(1.0, 1.0)),
                                    keyframe(frames - 1, pair(1.0, 1.0))}),
              "out_back"),
    });
    layers.push_back(check);

    json burstCommands = json::array();
    for (int i = 0; i < 10; ++i) {
        const double angle = rad(i * 36.0);
        const double cosA = std::cos(angle);
        const double sinA = std::sin(angle);
        burstCommands.push_back(moveTo(cosA * 185, sinA * 185));
        burstCommands.push_back(lineTo(cosA * 268, sinA * 268));
    }
    json burst = pathShape("burst", cx, cy, 620, 620, burstCommands,
                           "#C9FFE8", 2.2, 0, frames, 0.0);
    burst["blend_mode"] = "screen";
    burst["animation"] = animation({
        track("scale", json::array({keyframe(72, pair(0.78, 0.78)),
                                    keyframe(100, pair(1.28, 1.28))})),
        track("opacity", json::array({keyframe(72, 0.0), keyframe(78, 0.9),
                                      keyframe(102, 0.0)})),
    });
    layers.push_back(burst);

    json verified = textLayer("verified", "VERIFIED", cx, 700, 420, 50,
                              "assets/fonts/DejaVuSansMono-Bold.ttf", 24,
                              "#9CFFDF", "center", 78, 102, 0.0);
    layers.push_back(verified);

    auto badgeAnimation = [] {
        return animation({
            track("position", json::array({keyframe(96, offsetPair(960, 820)),
                                           keyframe(114, offsetPair(960, 820)),
                                           keyframe(117, offsetPair(953, 827)),
                                           keyframe(120, offsetPair(967, 813)),
                                           keyframe(123, offsetPair(960, 820)),
                                           keyframe(179, offsetPair(960, 820))}),
                  "out_expo"),
            track("scale", json::array({keyframe(96, pair(2.5, 2.5)),
                                        keyframe(114, pair(1.0, 1.0)),
                                        keyframe(119, pair(1.045, 1.045)),
                                        keyframe(124, pair(1.0, 1.0)),
                                        keyframe(179, pair(1.0, 1.0))}),
                  "out_back"),
            track("rotation", json::array({keyframe(96, json::array({0.0, 0.0, -12.0})),
                                           keyframe(114, json::array({0.0, 0.0, -8.0})),
                                           keyframe(179, json::array({0.0, 0.0, -8.0}))})),
            track("opacity", json::array({keyframe(96, 0.0), keyframe(102, 1.0),
                                          keyframe(179, 1.0)})),
        });
    };

    json badgeOuter = roundedRectLayer("badge_outer", 960, 820, 700, 170, 8,
                                       "#000000", 0.0, "#FF6B6B", 4.0, 0,
                                       frames);
    badgeOuter["animation"] = badgeAnimation();
    layers.push_back(badgeOuter);
    json badgeInner = roundedRectLayer("badge_inner", 960, 820, 674, 146, 5,
                                       "#000000", 0.0, "#FF6B6B", 1.5, 0,
                                       frames);
    badgeInner["animation"] = badgeAnimation();
    layers.push_back(badgeInner);
    json badgeText = textLayer("badge_text", "DECLASSIFIED", 960, 823, 620, 80,
                               "assets/fonts/Inter-Bold.ttf", 54, "#FF9A88",
                               "center", 0, frames, 1.0);
    badgeText["animation"] = badgeAnimation();
    layers.push_back(badgeText);

    layers.push_back(textLayer("header", "EVIDENCE 03 // AUTHENTICATED", 960,
                               140, 820, 44,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 24,
                               "#9CFFDF", "center", 0, frames, 0.9));
    layers.push_back(textLayer("footer", "CHAIN OF CUSTODY COMPLETE", 960, 1000,
                               720, 40,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 20,
                               "#7E9BAF", "center", 118, 62, 0.0));

    return json{{"layers", layers}};
}

json makeTechnicalCallout() {
    const int frames = 240;
    json layers = json::array();
    layers.push_back(colorLayer("backdrop", "#0B0C10", frames, 1.0));

    layers.push_back(roundedRectLayer("paper", 780, 570, 760, 620, 6,
                                      "#E9E1D2", 0.96, "#B8AD98", 1.0, 0,
                                      frames));
    layers.push_back(textLayer("paper_header", "THE RECORD / FILE 1998-14",
                               630, 292, 460, 34,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 15,
                               "#5C5448", "left", 4, frames - 4, 0.85));

    json headline = pathShape("headline", 780, 360, 700, 120,
                              json::array({moveTo(-330, -28),
                                           lineTo(300, -28),
                                           moveTo(-330, 16),
                                           lineTo(200, 16),
                                           moveTo(-330, 58),
                                           lineTo(90, 58)}),
                              "#2A2621", 14.0, 0, frames, 0.82);
    headline["animation"] = animation(
        {track("opacity", json::array({keyframe(0, 0.0), keyframe(18, 0.82),
                                       keyframe(frames - 1, 0.82)}))});
    layers.push_back(headline);

    json bodyCommands = json::array();
    for (int row = 0; row < 13; ++row) {
        const double y = -120 + row * 24;
        const double x1 = (row % 5 == 4) ? 170 : 330;
        bodyCommands.push_back(moveTo(-330, y));
        bodyCommands.push_back(lineTo(x1, y));
    }
    json body = pathShape("body_lines", 780, 570, 760, 620, bodyCommands,
                          "#5A5247", 4.0, 0, frames, 0.45);
    body["animation"] = animation(
        {track("opacity", json::array({keyframe(0, 0.0), keyframe(24, 0.45),
                                       keyframe(frames - 1, 0.45)}))});
    layers.push_back(body);

    layers.push_back(roundedRectLayer("redaction", 700, 500, 250, 22, 2,
                                      "#141210", 0.92, "#000000", 0.0, 10,
                                      frames - 10));
    layers.push_back(roundedRectLayer("redaction_2", 860, 596, 180, 22, 2,
                                      "#141210", 0.92, "#000000", 0.0, 16,
                                      frames - 16));

    layers.push_back(pathShape("crop_marks", 780, 570, 760, 620,
                               json::array({
                                   moveTo(-380, -280), lineTo(-380, -240),
                                   moveTo(-380, -280), lineTo(-340, -280),
                                   moveTo(380, -280), lineTo(380, -240),
                                   moveTo(380, -280), lineTo(340, -280),
                                   moveTo(380, 280), lineTo(380, 240),
                                   moveTo(380, 280), lineTo(340, 280),
                                   moveTo(-380, 280), lineTo(-380, 240),
                                   moveTo(-380, 280), lineTo(-340, 280),
                               }), "#F2C14E", 1.2, 0, frames, 0.55));

    const double anchorX = 1020, anchorY = 400;
    json anchorPulse = ellipseLayer("anchor_pulse", anchorX, anchorY, 90, 90,
                                    "#000000", 0.0, "#FF5A4E", 2.0, 22, 64,
                                    0.8);
    anchorPulse["animation"] = animation({
        track("scale", json::array({keyframe(22, pair(0.3, 0.3)),
                                    keyframe(74, pair(2.6, 2.6))})),
        track("opacity", json::array({keyframe(22, 0.8), keyframe(74, 0.0)})),
    });
    layers.push_back(anchorPulse);
    layers.push_back(ellipseLayer("anchor_dot", anchorX, anchorY, 12, 12,
                                  "#FF5A4E", 1.0, "#FF5A4E", 0.0, 16, 224,
                                  1.0, 14.0));

    json leaderGlow = pathShape("leader_glow", CX, CY, WIDTH, HEIGHT,
                                json::array({moveTo(anchorX - CX, anchorY - CY),
                                             lineTo(1120 - CX, 320 - CY),
                                             lineTo(1270 - CX, 320 - CY)}),
                                "#F2C14E", 9.0, 0, frames, 0.22);
    leaderGlow["blend_mode"] = "screen";
    leaderGlow["shape"]["operators"] = json::array({
        trimOperator(28, 58, 0.0, 0.45), trimOperator(58, 82, 0.45, 1.0)});
    layers.push_back(leaderGlow);

    json leader = pathShape("leader", CX, CY, WIDTH, HEIGHT,
                            json::array({moveTo(anchorX - CX, anchorY - CY),
                                         lineTo(1120 - CX, 320 - CY),
                                         lineTo(1270 - CX, 320 - CY)}),
                            "#FFD98A", 2.4, 0, frames);
    leader["shape"]["operators"] = json::array({
        trimOperator(28, 58, 0.0, 0.45), trimOperator(58, 82, 0.45, 1.0)});
    layers.push_back(leader);

    json card = roundedRectLayer("callout_card", 1510, 250, 440, 180, 6,
                                 "#11100E", 0.15, "#F2C14E", 1.4, 62, 178,
                                 1.0);
    card["animation"] = animation({
        track("opacity", json::array({keyframe(62, 0.0), keyframe(78, 1.0),
                                      keyframe(239, 1.0)})),
        track("position", json::array({keyframe(62, offsetPair(1510, 262)),
                                       keyframe(82, offsetPair(1510, 250)),
                                       keyframe(239, offsetPair(1510, 250))})),
    });
    layers.push_back(card);

    layers.push_back(textLayer("card_kicker", "SOURCE 14", 1510, 198, 380, 30,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 17,
                               "#F2C14E", "center", 70, frames - 70, 0.0));
    layers.push_back(textLayer("card_title", "Archive camera roll", 1510, 242,
                               400, 44, "assets/fonts/Inter-Bold.ttf", 27,
                               "#F7F0E3", "center", 74, frames - 74, 0.0));
    layers.push_back(textLayer("card_meta", "recovered 03:14 UTC", 1510, 286,
                               380, 30,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 16,
                               "#B9AD9A", "center", 78, frames - 78, 0.0));

    json highlightCommands = json::array();
    const int highlightPoints = 54;
    for (int i = 0; i <= highlightPoints; ++i) {
        const double angle = 2.0 * PI * i / highlightPoints;
        const double wobble = 1.0 + 0.045 * std::sin(i * 2.3) +
                              0.025 * std::sin(i * 5.1);
        const double x = std::cos(angle) * 300.0 * wobble;
        const double y = std::sin(angle) * 86.0 * wobble;
        if (i == 0) {
            highlightCommands.push_back(moveTo(x, y));
        } else {
            highlightCommands.push_back(lineTo(x, y));
        }
    }
    json highlight = pathShape("hand_highlight", 780, 356, 700, 260,
                               highlightCommands, "#FFD166", 14.0, 0, frames,
                               0.55);
    highlight["shape"]["operators"] =
        json::array({trimOperator(118, 158)});
    highlight["animation"] = animation({
        track("opacity", json::array({keyframe(118, 0.0), keyframe(124, 0.58),
                                      keyframe(239, 0.58)})),
        track("rotation", json::array({keyframe(118, json::array({0.0, 0.0, -1.6})),
                                       keyframe(239, json::array({0.0, 0.0, -1.6}))})),
    });
    layers.push_back(highlight);

    layers.push_back(textLayer("top_right", "ARCHIVE / 1998", 1700, 100, 380, 36,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 20,
                               "#8A8174", "right", 0, frames, 0.7));
    layers.push_back(textLayer("caption", "FIG. 02 - ORIGIN OF THE TRANSFER",
                               960, 1004, 820, 38,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 19,
                               "#8A8174", "center", 98, 142, 0.0));

    return json{{"layers", layers}};
}

json makeWireframeLogo() {
    const int frames = 240;
    json layers = json::array();
    layers.push_back(colorLayer("backdrop", "#06090F", frames, 1.0));

    layers.push_back(pathShape("logo_aura", 960, 470, 760, 760,
                               circlePath(380), "#1D5BFF", 1.0, 0, frames,
                               0.20, 0.0, 40.0));

    for (int i = 0; i < 2; ++i) {
        const double size = 560 + i * 70;
        json orbit = pathShape("orbit_" + std::to_string(i), 960, 470, size,
                               size, circlePath(size / 2.0),
                               i == 0 ? "#3E8FFF" : "#7FD4FF", 1.2, 0,
                               frames, 0.30);
        orbit["shape"]["stroke"]["dash_array"] = json::array({7.0, 13.0});
        orbit["blend_mode"] = "screen";
        orbit["animation"] = animation({
            track("scale", json::array({keyframe(0, pair(0.96, 0.96)),
                                        keyframe(120, pair(1.04, 1.04)),
                                        keyframe(frames - 1,
                                                 pair(0.98, 0.98))}),
                  "in_out_sine"),
            track("opacity", json::array({keyframe(0, 0.18),
                                          keyframe(120, 0.34),
                                          keyframe(frames - 1, 0.26)})),
        });
        layers.push_back(orbit);
    }

    json hexPoints = json::array();
    for (int i = 0; i < 6; ++i) {
        const double angle = rad(-90.0 + i * 60.0);
        const double x = std::cos(angle) * 190.0;
        const double y = std::sin(angle) * 190.0;
        hexPoints.push_back(i == 0 ? moveTo(x, y) : lineTo(x, y));
    }
    json close = json{{"type", "close"}};
    hexPoints.push_back(close);

    json hexFill = pathShape("hex_fill", 960, 470, 460, 460, hexPoints,
                             "#1D5BFF", 0.0, 112, 128, 1.0, 0.92, 0.0);
    hexFill["blend_mode"] = "screen";
    hexFill["animation"] = animation({
        track("opacity", json::array({keyframe(112, 0.0), keyframe(146, 0.92),
                                      keyframe(239, 0.92)})),
        track("scale", json::array({keyframe(112, pair(1.0, 0.05)),
                                    keyframe(148, pair(1.0, 1.0)),
                                    keyframe(239, pair(1.0, 1.0))}),
              "out_cubic"),
    });
    layers.push_back(hexFill);

    json hexGlow = pathShape("hex_glow", 960, 470, 460, 460, hexPoints,
                             "#4C9BFF", 12.0, 0, frames, 0.24);
    hexGlow["blend_mode"] = "screen";
    hexGlow["shape"]["operators"] = json::array({trimOperator(15, 86)});
    layers.push_back(hexGlow);

    json hexOutline = pathShape("hex_outline", 960, 470, 460, 460, hexPoints,
                                "#9FE8FF", 3.2, 0, frames);
    hexOutline["shape"]["operators"] = json::array({trimOperator(15, 86)});
    hexOutline["effects"] = json::array({glowEffect(14, "#7FD4FF", 0.45)});
    layers.push_back(hexOutline);

    json innerGlow = pathShape("inner_glow", 960, 470, 300, 300,
                               arcPath(96, 45, 315, 6), "#5CFFC9", 18.0, 0,
                               frames, 0.26);
    innerGlow["blend_mode"] = "screen";
    innerGlow["shape"]["operators"] = json::array({trimOperator(80, 122)});
    layers.push_back(innerGlow);

    json inner = pathShape("inner_c", 960, 470, 300, 300,
                           arcPath(96, 45, 315, 6), "#C9F3FF", 9.0, 0, frames);
    inner["shape"]["operators"] = json::array({trimOperator(80, 122)});
    inner["effects"] = json::array({glowEffect(10, "#7FD4FF", 0.5)});
    layers.push_back(inner);

    json scan = roundedRectLayer("scan_bar", 960, 470, 330, 4, 2, "#C9F3FF",
                                 0.8, "#C9F3FF", 0.0, 0, frames, 1.0);
    scan["blend_mode"] = "screen";
    scan["animation"] = animation({
        track("position", json::array({keyframe(114, offsetPair(960, 285)),
                                       keyframe(158, offsetPair(960, 655))}),
              "in_out_cubic"),
        track("opacity", json::array({keyframe(114, 0.0), keyframe(122, 0.9),
                                      keyframe(154, 0.9), keyframe(160, 0.0)})),
    });
    layers.push_back(scan);

    json sweep = roundedRectLayer("light_sweep", 960, 470, 4, 520, 2, "#FFFFFF",
                                  1.0, "#FFFFFF", 0.0, 0, frames, 1.0);
    sweep["rotation"] = json::array({0.0, 0.0, 34.0});
    sweep["enable_3d"] = true;
    sweep["blend_mode"] = "screen";
    sweep["animation"] = animation({
        track("position", json::array({keyframe(150, offsetPair(700, 470)),
                                       keyframe(196, offsetPair(1220, 470))})),
        track("opacity", json::array({keyframe(150, 0.0), keyframe(162, 0.32),
                                      keyframe(190, 0.32), keyframe(198, 0.0)})),
    });
    layers.push_back(sweep);

    json finalPulse = pathShape("final_pulse", 960, 470, 440, 440,
                                circlePath(220), "#7FD4FF", 2.0, 186, 54,
                                1.0);
    finalPulse["animation"] = animation({
        track("scale", json::array({keyframe(186, pair(0.8, 0.8)),
                                    keyframe(240, pair(2.1, 2.1))})),
        track("opacity", json::array({keyframe(186, 0.55), keyframe(240, 0.0)})),
    });
    layers.push_back(finalPulse);

    layers.push_back(textLayer("wordmark", "CHRONON", 960, 790, 700, 110,
                               "assets/fonts/Inter-ExtraBold.ttf", 84,
                               "#EAF6FF", "center", 0, frames, 0.0));
    layers.push_back(textLayer("subline", "VECTOR MOTION SYSTEM", 960, 858, 700,
                               40, "assets/fonts/DejaVuSansMono-Bold.ttf", 20,
                               "#9FE8FF", "center", 0, frames, 0.0));
    layers.push_back(textLayer("build_tag", "BUILD 05 / WIREFRAME TO SOLID", 322,
                               96, 620, 34,
                               "assets/fonts/DejaVuSansMono-Bold.ttf", 18,
                               "#4F7C99", "left", 0, frames, 0.7));

    auto fade = [](int begin, int end) {
        return animation({track("opacity", json::array({
            keyframe(0, 0.0), keyframe(begin, 0.0), keyframe(end, 1.0),
            keyframe(239, 1.0)}))});
    };
    layers.back()["animation"] = fade(168, 194);
    layers[layers.size() - 2]["animation"] = fade(180, 204);
    layers[layers.size() - 3]["animation"] = fade(166, 190);

    return json{{"layers", layers}};
}

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

void validateClip(const Clip& clip) {
    const json& plan = clip.plan;
    require(plan.at("schema") == "chronon.render-plan.v3",
            clip.slug + ": wrong schema");
    require(plan.at("canvas").at("width") == WIDTH,
            clip.slug + ": width is not 1920");
    require(plan.at("canvas").at("height") == HEIGHT,
            clip.slug + ": height is not 1080");
    require(plan.at("canvas").at("fps_num") == FPS,
            clip.slug + ": fps is not 30");
    require(clip.frames >= 1 && clip.frames <= MAX_FRAMES,
            clip.slug + ": outside 1..300 frames");
    require(plan.at("layers").size() >= 8,
            clip.slug + ": too few layers for a finished composition");
    require(plan.at("output").at("path") == videoName(clip),
            clip.slug + ": output name mismatch");
    const std::string output = plan.at("output").at("path").get<std::string>();
    require(output.find("_1920x1080_") != std::string::npos,
            clip.slug + ": output misses the canvas tag");
    require(output.size() > 7 &&
                output.substr(output.size() - 7) == "_v1.mp4",
            clip.slug + ": output is not a v1 mp4");
}

json seriesEntry(const Clip& clip) {
    const int seconds = static_cast<int>(std::lround(clip.frames / double(FPS)));
    return json{
        {"id", padded(clip.index) + "_" + clip.slug},
        {"index", clip.index},
        {"slug", clip.slug},
        {"label", clip.label},
        {"category", clip.category},
        {"note", clip.note},
        {"background_rgb", json::array({rgba(clip.background)[0],
                                        rgba(clip.background)[1],
                                        rgba(clip.background)[2]})},
        {"frames", clip.frames},
        {"duration_s", seconds},
        {"plan", "plans/" + planName(clip)},
        {"mp4", "mp4/" + videoName(clip)},
        {"drive_name", videoName(clip)},
    };
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            std::cerr << "usage: " << argv[0] << " <output-dir>\n";
            return 2;
        }
        const fs::path outDir = argv[1];
        fs::create_directories(outDir / "plans");

        std::vector<Clip> clips;
        clips.push_back({1, "Tactical_Route", "Tactical route & HUD",
                         "tactical_map_hud",
                         "OSINT trace: dashed trail, trim-drawn Bezier route, "
                         "radar pings, converging reticle, coordinate HUD",
                         "#05080D", 300, makeTacticalRoute()});
        clips.push_back({2, "Node_Graph", "Node graph expansion",
                         "network_nodes",
                         "Spring pop center, staggered Bezier edges, cascade "
                         "nodes and travelling data pulses",
                         "#060A14", 240, makeNodeGraph()});
        clips.push_back({3, "Validation_Burst", "Validation burst",
                         "validation_badge",
                         "Trim-drawn ring, check snap with overshoot, radial "
                         "burst, declassified stamp with screen shake",
                         "#05090C", 180, makeValidationBurst()});
        clips.push_back({4, "Technical_Callout", "Technical callout",
                         "callout_annotation",
                         "Two-beat leader line, paper plate, callout card and "
                         "hand-drawn highlight with multiply blend",
                         "#0B0C10", 240, makeTechnicalCallout()});
        clips.push_back({5, "Wireframe_Logo", "Wireframe to solid logo",
                         "logo_morph",
                         "Trim-drawn hex wireframe, inner C, fill wipe with "
                         "scan bar, specular sweep and orbit rings",
                         "#06090F", 240, makeWireframeLogo()});

        json series = {
            {"schema", "chronontemplate.vector-motion-suite.v1"},
            {"generator", "chronontemplate_emit_vector_motion_suite"},
            {"canvas", json{{"width", WIDTH}, {"height", HEIGHT},
                            {"fps", FPS}}},
            {"rules", json{{"max_frames", MAX_FRAMES},
                           {"authoring", "C++ RenderPlan V3, native shape/path "
                                         "primitives only"},
                           {"motion", "no linear entrances; out_cubic/out_back/"
                                      "out_expo and trim paths"}}},
            {"clips", json::array()},
        };

        for (Clip& clip : clips) {
            clip.plan = finishPlan(clip);
            validateClip(clip);
            const fs::path planPath = outDir / "plans" / planName(clip);
            std::ofstream handle(planPath);
            require(handle.good(), "cannot write " + planPath.string());
            handle << clip.plan.dump(2) << '\n';
            handle.close();
            require(handle.good(), "failed writing " + planPath.string());
            series["clips"].push_back(seriesEntry(clip));
            std::cout << planPath.string() << "  " << clip.frames << "f  "
                      << videoName(clip) << '\n';
        }

        const fs::path seriesPath = outDir / "plans" / "series.json";
        std::ofstream handle(seriesPath);
        require(handle.good(), "cannot write " + seriesPath.string());
        handle << series.dump(2) << '\n';
        handle.close();
        std::cout << seriesPath.string() << "  " << series["clips"].size()
                  << " clips authored in C++\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "vector motion suite: " << error.what() << '\n';
        return 1;
    }
}
