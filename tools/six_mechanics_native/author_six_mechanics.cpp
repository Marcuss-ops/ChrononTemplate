// Native Chronon3D RenderPlan V3 authoring for the six ChrononMotion mechanics.
// No Python, no Pillow, no external image assets: every frame is vector data
// rendered by Chronon3D's Vulkan backend.
#include "chronontemplate/core/NativePrimitives.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <tuple>
#include <string>
#include <utility>
#include <vector>

using nlohmann::json;
using chronontemplate::native::TemplateComposition;
using Keys = std::vector<std::pair<int, double>>;

namespace {

constexpr int W = 1920;
constexpr int H = 1080;
constexpr double CX = W * 0.5;
constexpr double CY = H * 0.5;
constexpr int FPS = 30;
constexpr double PI = 3.14159265358979323846;
constexpr double F = 1500.0;

double clamp01(double x) { return std::min(1.0, std::max(0.0, x)); }

double smoothstep(double a, double b, double x) {
    if (b == a) return x < a ? 0.0 : 1.0;
    const double t = clamp01((x - a) / (b - a));
    return t * t * (3.0 - 2.0 * t);
}

double ease_out_cubic(double x) {
    x = clamp01(x);
    return 1.0 - std::pow(1.0 - x, 3.0);
}

double ease_in_out(double x) {
    x = clamp01(x);
    return x * x * (3.0 - 2.0 * x);
}

json C(double r, double g, double b, double a = 1.0) {
    return json::array({r, g, b, a});
}

json P(double x, double y) { return json::array({x, y}); }

json mv(double x, double y) { return json{{"type", "move_to"}, {"point", P(x, y)}}; }
json ln(double x, double y) { return json{{"type", "line_to"}, {"point", P(x, y)}}; }
json cu(double c1x, double c1y, double c2x, double c2y, double x, double y) {
    return json{{"type", "cubic_to"}, {"control1", P(c1x, c1y)},
                {"control2", P(c2x, c2y)}, {"point", P(x, y)}};
}
json qd(double cx, double cy, double x, double y) {
    return json{{"type", "quadratic_to"}, {"control1", P(cx, cy)}, {"point", P(x, y)}};
}
json cl() { return json{{"type", "close"}}; }

json rectPath(double w, double h) {
    const double x = w * 0.5, y = h * 0.5;
    return json::array({mv(-x, -y), ln(x, -y), ln(x, y), ln(-x, y), cl()});
}

json roundPath(double w, double h, double r) {
    r = std::max(0.0, std::min(r, std::min(w, h) * 0.5));
    const double x = w * 0.5, y = h * 0.5, k = 0.5522847498307936 * r;
    json p = json::array();
    p.push_back(mv(-x + r, -y));
    p.push_back(ln(x - r, -y));
    p.push_back(cu(x - r + k, -y, x, -y + r - k, x, -y + r));
    p.push_back(ln(x, y - r));
    p.push_back(cu(x, y - r + k, x - r + k, y, x - r, y));
    p.push_back(ln(-x + r, y));
    p.push_back(cu(-x + r - k, y, -x, y - r + k, -x, y - r));
    p.push_back(ln(-x, -y + r));
    p.push_back(cu(-x, -y + r - k, -x + r - k, -y, -x + r, -y));
    p.push_back(cl());
    return p;
}

json discPoly(double r, int sides = 10) {
    json p = json::array();
    for (int i = 0; i < sides; ++i) {
        const double a = 2.0 * PI * i / sides;
        const double x = std::cos(a) * r, y = std::sin(a) * r;
        p.push_back(i == 0 ? mv(x, y) : ln(x, y));
    }
    p.push_back(cl());
    return p;
}

json ellipsePath(double rx, double ry) {
    const double k = 0.5522847498307936;
    return json::array({
        mv(rx, 0),
        cu(rx, k * ry, k * rx, ry, 0, ry),
        cu(-k * rx, ry, -rx, k * ry, -rx, 0),
        cu(-rx, -k * ry, -k * rx, -ry, 0, -ry),
        cu(k * rx, -ry, rx, -k * ry, rx, 0),
        cl()});
}

json polygon(std::vector<std::pair<double, double>> pts) {
    json p = json::array();
    if (pts.empty()) return p;
    p.push_back(mv(pts[0].first, pts[0].second));
    for (std::size_t i = 1; i < pts.size(); ++i) p.push_back(ln(pts[i].first, pts[i].second));
    p.push_back(cl());
    return p;
}

json gradient(double x0, double y0, double x1, double y1,
              std::vector<std::tuple<double, double, double, double>> stops) {
    json cs = json::array();
    for (const auto& [pos, r, g, b] : stops) {
        cs.push_back(json{{"position", pos}, {"color", C(r, g, b, 1.0)}});
    }
    return json{{"type", "linear"}, {"start", P(x0, y0)}, {"end", P(x1, y1)},
                {"color_stops", cs}};
}

json basePlan(const std::string& id, int frames) {
    return json{{"schema", "chronon.render-plan.v3"},
                {"version", 3},
                {"job_id", id},
                {"canvas", json{{"width", W}, {"height", H}, {"fps_num", FPS},
                                {"fps_den", 1}, {"duration_frames", frames}}},
                {"output", json{{"path", id + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}},
                {"layers", json::array()}};
}

json baseLayer(const std::string& id, double cx, double cy, double w, double h, int frames) {
    return json{{"id", id},
                {"type", "shape"},
                {"position", P(cx - CX, cy - CY)},
                {"size", P(w, h)},
                {"start_frame", 0},
                {"duration_frames", frames},
                {"screen_space", true},
                {"enable_3d", false},
                {"opacity", 1.0}};
}

json track(const std::string& prop, const Keys& keys, const std::string& easing = "linear") {
    json kfs = json::array();
    for (const auto& [f, v] : keys) kfs.push_back(json{{"frame", f}, {"value", v}});
    return json{{"property", prop}, {"easing", easing}, {"keyframes", kfs}};
}

void animate(json& layer, const json& tracks) {
    layer["animation"] = json{{"tracks", tracks}};
}

void add(json& plan, const json& layer) { plan["layers"].push_back(layer); }

json rectLayer(const std::string& id, double cx, double cy, double w, double h,
               const json& fill, int frames, const json& effects = json::array()) {
    json l = baseLayer(id, cx, cy, w, h, frames);
    l["shape"] = json{{"type", "rect"}, {"fill", fill}};
    if (!effects.empty()) l["effects"] = effects;
    return l;
}

json roundLayer(const std::string& id, double cx, double cy, double w, double h, double r,
                const json& fill, int frames, const json& effects = json::array(),
                const json& stroke = json()) {
    json l = baseLayer(id, cx, cy, w, h, frames);
    l["shape"] = json{{"type", "rounded_rect"}, {"radius", r}, {"fill", fill}};
    if (!stroke.is_null()) l["shape"]["stroke"] = stroke;
    if (!effects.empty()) l["effects"] = effects;
    return l;
}

json ellipseLayer(const std::string& id, double cx, double cy, double rx, double ry,
                  const json& fill, int frames, const json& effects = json::array(),
                  const json& stroke = json()) {
    json l = baseLayer(id, cx, cy, rx * 2.0, ry * 2.0, frames);
    l["shape"] = json{{"type", "path"}, {"fill", fill}, {"path", ellipsePath(rx, ry)}};
    if (!stroke.is_null()) l["shape"]["stroke"] = stroke;
    if (!effects.empty()) l["effects"] = effects;
    return l;
}

json pathLayer(const std::string& id, double cx, double cy, double w, double h,
               const json& path, const json& fill, int frames,
               const json& effects = json::array(), const json& stroke = json()) {
    json l = baseLayer(id, cx, cy, w, h, frames);
    l["shape"] = json{{"type", "path"}, {"fill", fill}, {"path", path}};
    if (!stroke.is_null()) l["shape"]["stroke"] = stroke;
    if (!effects.empty()) l["effects"] = effects;
    return l;
}

json shiftPath(json path, double dx, double dy) {
    for (auto& cmd : path) {
        for (const char* key : {"point", "control1", "control2"}) {
            if (!cmd.contains(key)) continue;
            cmd[key][0] = cmd[key][0].get<double>() + dx;
            cmd[key][1] = cmd[key][1].get<double>() + dy;
        }
    }
    return path;
}

void appendPath(json& dst, const json& src) {
    for (const auto& cmd : src) dst.push_back(cmd);
}

json glow(double radius, double intensity, const json& color) {
    return json{{"type", "glow"},
                {"radius", std::min(256.0, radius)},
                {"intensity", std::clamp(intensity, 0.0, 4.0)},
                {"color", color}};
}

json shadow(double radius, double dx, double dy, const json& color) {
    return json{{"type", "drop_shadow"}, {"radius", radius}, {"offset", P(dx, dy)},
                {"color", color}};
}

json stroke(const json& color, double width, const std::string& cap = "round") {
    return json{{"color", color}, {"width", width}, {"cap", cap}, {"join", "round"}};
}

Keys fadeKeys(int frames, int inFrames = 12, int outFrames = 12) {
    Keys k;
    if (inFrames > 0) {
        k.emplace_back(0, 0.0);
        k.emplace_back(inFrames, 1.0);
    } else {
        k.emplace_back(0, 1.0);
    }
    if (outFrames > 0 && frames > outFrames) {
        k.emplace_back(frames - 1 - outFrames, 1.0);
        k.emplace_back(frames - 1, 0.0);
    }
    return k;
}

// ---------------------------------------------------------------- scene 01
json scene01() {
    const int frames = 240;
    json plan = basePlan("01_native_2p5d_parallax", frames);

    // Deep background: a vertical gradient plus three soft light plates.
    json bg = baseLayer("bg", CX, CY, W, H, frames);
    bg["type"] = "shape";
    bg["shape"] = json{{"type", "rect"},
                       {"fill", gradient(-W / 2, -H / 2, W / 2, H / 2,
                                         {{0.0, 0.015, 0.035, 0.065},
                                          {0.55, 0.035, 0.085, 0.095},
                                          {1.0, 0.010, 0.020, 0.030}})}};
    add(plan, bg);

    struct Blob { double x, y, z, r; json c; };
    const std::vector<Blob> blobs = {
        {-420, -220, 2100, 520, C(0.10, 0.35, 0.38, 0.18)},
        {520, 260, 1700, 440, C(0.55, 0.30, 0.16, 0.15)},
        {780, -300, 1450, 360, C(0.14, 0.26, 0.42, 0.16)},
        {-760, 340, 1900, 420, C(0.32, 0.18, 0.30, 0.12)}};
    int bi = 0;
    for (const auto& b : blobs) {
        json l = ellipseLayer("bg_blob_" + std::to_string(bi++), b.x, b.y, b.r, b.r, b.c,
                              frames, json::array({glow(b.r * 0.8, 0.55, b.c)}));
        Keys px, py, sx;
        for (int f = 0; f < frames; f += 3) {
            const double t = f / double(FPS);
            const double k = 900.0 / b.z;
            px.emplace_back(f, b.x * k * 0.35 + 26.0 * std::sin(0.11 * t + bi));
            py.emplace_back(f, b.y * k * 0.35 + 18.0 * std::cos(0.09 * t + bi));
            sx.emplace_back(f, k);
        }
        animate(l, json::array({track("position_x", px), track("position_y", py),
                                track("scale_x", sx), track("scale_y", sx)}));
        add(plan, l);
    }

    // 2.5D cards.
    struct Card { double x, y, z, omega, phase; json fill, accent; };
    const std::vector<Card> cards = {
        {-360, -210, 600, 0.55, 0.0, C(0.085, 0.20, 0.24), C(0.72, 0.47, 0.26)},
        {360, -230, 720, 0.71, PI * 0.5, C(0.16, 0.10, 0.20), C(0.72, 0.42, 0.48)},
        {-380, 250, 840, 0.87, PI, C(0.09, 0.17, 0.14), C(0.70, 0.60, 0.34)},
        {390, 260, 960, 1.03, PI * 1.5, C(0.20, 0.11, 0.09), C(0.78, 0.50, 0.29)}};
    int ci = 0;
    for (const auto& c : cards) {
        const double cw = 300, ch = 420;
        Keys px, py, sx, rot;
        for (int f = 0; f < frames; f += 2) {
            const double t = f / double(FPS);
            const double move = std::min(t, 6.0) / 6.0;
            const double camz = 150.0 * smoothstep(0.0, 1.0, move);
            const double camx = 80.0 * std::sin(2.0 * PI * move);
            double x = CX + F * (c.x - camx) / (c.z - camz);
            double y = CY - F * c.y / (c.z - camz);
            x += 12.0 * std::sin(c.omega * t + c.phase);
            y += 18.0 * std::cos(1.31 * c.omega * t + c.phase);
            const double s = 0.93 * 900.0 / (c.z - camz);
            px.emplace_back(f, x - CX);
            py.emplace_back(f, y - CY);
            sx.emplace_back(f, s);
            rot.emplace_back(f, 3.5 * std::sin(0.73 * c.omega * t));
        }
        const std::string tag = "card_" + std::to_string(ci++);
        json sh = roundLayer(tag + "_shadow", c.x, c.y, cw, ch, 34.0,
                             C(0.0, 0.0, 0.0, 0.55), frames, json::array());
        animate(sh, json::array({track("position_x", px), track("position_y", py),
                                 track("scale_x", sx), track("scale_y", sx),
                                 track("rotation_z", rot),
                                 track("opacity", {{0, 0.0}, {10, 0.55}, {frames - 13, 0.55}, {frames - 1, 0.0}})}));
        add(plan, sh);

        json card = roundLayer(tag, c.x, c.y, cw, ch, 28.0, c.fill, frames,
                               json::array({shadow(26.0, 18.0, 24.0, C(0, 0, 0, 0.55))}),
                               stroke(C(1, 1, 1, 0.10), 2.0));
        animate(card, json::array({track("position_x", px), track("position_y", py),
                                   track("scale_x", sx), track("scale_y", sx),
                                   track("rotation_z", rot),
                                   track("opacity", {{0, 0.0}, {12, 1.0}, {frames - 13, 1.0}, {frames - 1, 0.0}})}));
        add(plan, card);

        json band = roundLayer(tag + "_band", c.x, c.y, cw - 52.0, 8.0, 4.0, c.accent, frames);
        animate(band, json::array({track("position_x", px), track("position_y", py),
                                   track("scale_x", sx), track("scale_y", sx),
                                   track("rotation_z", rot),
                                   track("opacity", {{0, 0.0}, {18, 0.9}, {frames - 13, 0.9}, {frames - 1, 0.0}})}));
        add(plan, band);

        json disc = ellipseLayer(tag + "_disc", c.x, c.y, 52.0, 52.0, C(0, 0, 0, 0), frames,
                                 json::array({glow(28.0, 0.35, c.accent)}),
                                 stroke(c.accent, 3.0));
        animate(disc, json::array({track("position_x", px), track("position_y", py),
                                   track("scale_x", sx), track("scale_y", sx),
                                   track("rotation_z", rot),
                                   track("opacity", {{0, 0.0}, {22, 0.8}, {frames - 13, 0.8}, {frames - 1, 0.0}})}));
        add(plan, disc);
    }

    // Foreground subject: an abstract lens/orb with rings.
    Keys spx, spy, ss, srot;
    for (int f = 0; f < frames; f += 2) {
        const double t = f / double(FPS);
        const double move = std::min(t, 6.0) / 6.0;
        const double camz = 150.0 * smoothstep(0.0, 1.0, move);
        const double camx = 80.0 * std::sin(2.0 * PI * move);
        const double z = 900.0;
        spx.emplace_back(f, F * (0.0 - camx) / (z - camz) + 8.0 * std::sin(0.6 * t));
        spy.emplace_back(f, 10.0 * std::cos(0.5 * t));
        ss.emplace_back(f, 900.0 / (z - camz) * 0.92);
        srot.emplace_back(f, 2.0 * std::sin(0.35 * t));
    }
    const json orbTrack = json::array({track("position_x", spx), track("position_y", spy),
                                       track("scale_x", ss), track("scale_y", ss),
                                       track("rotation_z", srot),
                                       track("opacity", {{0, 0.0}, {16, 1.0}, {frames - 16, 1.0}, {frames - 1, 0.0}})});
    json halo = ellipseLayer("subject_halo", CX, CY, 270, 300, C(0.03, 0.11, 0.14, 0.0),
                             frames, json::array({glow(110.0, 0.65, C(0.22, 0.72, 0.78, 0.9))}));
    animate(halo, orbTrack);
    add(plan, halo);

    json body = ellipseLayer("subject_body", CX, CY, 205, 248, C(0.035, 0.09, 0.11, 1.0),
                             frames, json::array(), stroke(C(0.55, 0.85, 0.82, 0.55), 3.0));
    animate(body, orbTrack);
    add(plan, body);

    json ring1 = ellipseLayer("subject_ring_a", CX, CY, 238, 238, C(0, 0, 0, 0), frames,
                              json::array({glow(24.0, 0.4, C(0.75, 0.55, 0.30, 0.8))}),
                              stroke(C(0.88, 0.68, 0.40, 0.85), 5.0));
    animate(ring1, orbTrack);
    add(plan, ring1);

    json ring2 = ellipseLayer("subject_ring_b", CX, CY, 180, 180, C(0, 0, 0, 0), frames,
                              json::array(), stroke(C(0.85, 0.92, 0.88, 0.35), 2.0));
    animate(ring2, orbTrack);
    add(plan, ring2);

    json core = ellipseLayer("subject_core", CX - 20, CY - 30, 62, 62, C(0.72, 0.88, 0.82, 0.75),
                             frames, json::array({glow(34.0, 0.8, C(0.7, 0.95, 0.9, 0.8))}));
    animate(core, orbTrack);
    add(plan, core);

    // Sparse foreground motes.
    std::mt19937 rng(101);
    std::uniform_real_distribution<double> ux(0.0, W), uy(0.0, H);
    for (int i = 0; i < 28; ++i) {
        const double x = ux(rng), y = uy(rng), r = 1.0 + (i % 3);
        json m = ellipseLayer("mote_" + std::to_string(i), x, y, r, r,
                              C(0.91, 0.78, 0.58, 0.22), frames);
        Keys mx, my, mo;
        for (int f = 0; f < frames; f += 4) {
            const double t = f / double(FPS);
            mx.emplace_back(f, x - CX + 14.0 * std::sin(0.4 * t + i));
            my.emplace_back(f, y - CY + 19.0 * std::cos(0.3 * t + i * 0.7));
        }
        mo = {{0, 0.0}, {20, 0.28}, {frames - 20, 0.28}, {frames - 1, 0.0}};
        animate(m, json::array({track("position_x", mx), track("position_y", my),
                                track("opacity", mo)}));
        add(plan, m);
    }
    return plan;
}

// ---------------------------------------------------------------- scene 02
struct Curve { std::vector<std::pair<double, double>> pts; json color; double delay; };

json scene02() {
    const int frames = 240;
    json plan = basePlan("02_native_spline_network", frames);

    json bg = baseLayer("bg", CX, CY, W, H, frames);
    bg["shape"] = json{{"type", "rect"},
                       {"fill", gradient(-W / 2, -H / 2, W / 2, H / 2,
                                         {{0.0, 0.012, 0.022, 0.045},
                                          {0.6, 0.020, 0.055, 0.080},
                                          {1.0, 0.010, 0.018, 0.030}})}};
    add(plan, bg);

    json gridPath = json::array();
    for (int i = 0; i < 36; ++i) {
        const double x = 90.0 + (i * 271.0);
        const double y = 70.0 + std::fmod(i * 197.0, 940.0);
        appendPath(gridPath, shiftPath(ellipsePath(1.7, 1.7),
                                       std::fmod(x, 1850.0) + 35.0 - CX, y - CY));
    }
    add(plan, pathLayer("grid", CX, CY, W, H, gridPath, C(0.55, 0.75, 0.85, 0.18), frames,
                        json::array(), stroke(C(0.55, 0.75, 0.85, 0.18), 1.0)));

    const std::vector<Curve> curves = {
        {{{220, 760}, {700, 120}, {1200, 960}, {1700, 300}}, C(0.35, 0.78, 1.0, 1.0), 0.38},
        {{{220, 540}, {760, 540}, {1120, 540}, {1700, 540}}, C(0.42, 0.92, 0.86, 1.0), 0.45},
        {{{220, 320}, {700, 960}, {1200, 120}, {1700, 780}}, C(0.52, 0.68, 1.0, 1.0), 0.52}};

    const int segs = 120;
    int layerId = 0;
    for (const auto& curve : curves) {
        // Sample cubic Bezier at uniform parameter.
        std::vector<std::pair<double, double>> pts;
        for (int i = 0; i <= segs; ++i) {
            const double u = i / double(segs), v = 1.0 - u;
            const double x = v*v*v*curve.pts[0].first + 3*v*v*u*curve.pts[1].first +
                             3*v*u*u*curve.pts[2].first + u*u*u*curve.pts[3].first;
            const double y = v*v*v*curve.pts[0].second + 3*v*v*u*curve.pts[1].second +
                             3*v*u*u*curve.pts[2].second + u*u*u*curve.pts[3].second;
            pts.emplace_back(x, y);
        }
        const std::string tag = "curve_" + std::to_string(layerId++);

        const double cr = curve.color[0].get<double>();
        const double cg = curve.color[1].get<double>();
        const double cb = curve.color[2].get<double>();
        const json localPath = json::array({
            mv(curve.pts[0].first - CX, curve.pts[0].second - CY),
            cu(curve.pts[1].first - CX, curve.pts[1].second - CY,
               curve.pts[2].first - CX, curve.pts[2].second - CY,
               curve.pts[3].first - CX, curve.pts[3].second - CY)});
        json guide = pathLayer(tag + "_guide", CX, CY, W, H, localPath,
                               C(0, 0, 0, 0), frames, json::array(),
                               stroke(C(cr, cg, cb, 0.16), 1.5));
        animate(guide, json::array({track("opacity", {{0, 0.0}, {12, 1.0}, {frames - 12, 1.0}, {frames - 1, 0.0}})}));
        add(plan, guide);

        const int revealStart = int(std::round(curve.delay * FPS));
        const int revealEnd = int(std::round((curve.delay + 2.65) * FPS));
        json trimOp = {{"kind", "trim"},
                       {"params", json{{"start", 0.0}, {"end", 1.0}, {"offset", 0.0},
                           {"animation", json{{"keyframes", json::array({
                               json{{"frame", 0}, {"value", json::array({0, 0.02})}},
                               json{{"frame", revealStart}, {"value", json::array({0, 0.02})}},
                               json{{"frame", revealEnd}, {"value", json::array({0, 1.0})}}
                           })}}}}}};
        json ink = pathLayer(tag, CX, CY, W, H, localPath, C(0, 0, 0, 0), frames,
                             json::array({glow(22.0, 0.55, curve.color)}),
                             stroke(curve.color, 8.0));
        ink["shape"]["operators"] = json::array({trimOp});
        animate(ink, json::array({track("opacity",
            {{0, 0.0}, {revealStart, 0.0}, {revealStart + 6, 1.0},
             {frames - 13, 1.0}, {frames - 1, 0.0}})}));
        add(plan, ink);

        // Travelling head glow.
        json head = ellipseLayer(tag + "_head", pts[0].first, pts[0].second, 15, 15,
                                 C(0.95, 0.98, 1.0, 1.0), frames,
                                 json::array({glow(44.0, 1.0, curve.color)}),
                                 stroke(C(0.95, 0.98, 1.0, 1.0), 1.0));
        Keys hx, hy, ho;
        for (int f = 0; f < frames; f += 2) {
            const double t = f / double(FPS);
            const double u = clamp01((t - curve.delay) / 2.65);
            const double idx = u * segs;
            const int i0 = std::min(segs, std::max(0, int(idx)));
            const int i1 = std::min(segs, i0 + 1);
            const double frac = idx - i0;
            hx.emplace_back(f, pts[i0].first * (1 - frac) + pts[i1].first * frac - CX);
            hy.emplace_back(f, pts[i0].second * (1 - frac) + pts[i1].second * frac - CY);
            ho.emplace_back(f, (t > curve.delay && t < curve.delay + 2.8) ? 1.0 : 0.0);
        }
        animate(head, json::array({track("position_x", hx), track("position_y", hy),
                                   track("opacity", ho)}));
        add(plan, head);
    }

    // Left node rings.
    const std::vector<std::pair<double, double>> nodes = {{220, 760}, {220, 540}, {220, 320}};
    const std::vector<json> nodeCols = {C(0.35, 0.78, 1.0, 1.0), C(0.42, 0.92, 0.86, 1.0),
                                        C(0.52, 0.68, 1.0, 1.0)};
    for (int i = 0; i < 3; ++i) {
        json halo = ellipseLayer("node_halo_" + std::to_string(i), nodes[i].first, nodes[i].second,
                                 108, 108, C(0, 0, 0, 0), frames,
                                 json::array({glow(34.0, 0.4, nodeCols[i])}),
                                 stroke(nodeCols[i], 2.0));
        Keys s, o;
        for (int f = 0; f < frames; f += 4) {
            const double t = f / double(FPS);
            s.emplace_back(f, 1.0 + 0.035 * std::sin(t * 1.8 + i));
            o.emplace_back(f, 0.55 + 0.25 * std::sin(t * 1.8 + i));
        }
        animate(halo, json::array({track("scale_x", s), track("scale_y", s), track("opacity", o)}));
        add(plan, halo);
        json dot = ellipseLayer("node_dot_" + std::to_string(i), nodes[i].first, nodes[i].second,
                                9, 9, nodeCols[i], frames,
                                json::array({glow(14.0, 0.8, nodeCols[i])}));
        add(plan, dot);
    }

    // Pentagon target.
    const double tx = 1540, ty = 540, rad = 190;
    std::vector<std::pair<double, double>> pent;
    for (int i = 0; i < 5; ++i) {
        const double a = -PI * 0.5 + 2.0 * PI * i / 5.0;
        pent.emplace_back(rad * std::cos(a), rad * std::sin(a));
    }
    json pg = pathLayer("pentagon_fill", tx, ty, 430, 430, polygon(pent), C(0.012, 0.025, 0.035, 0.78),
                        frames, json::array(), stroke(C(0.88, 0.68, 0.38, 0.9), 6.0));
    add(plan, pg);
    json pgGlow = pathLayer("pentagon_glow", tx, ty, 500, 500, polygon(pent), C(0, 0, 0, 0),
                            frames, json::array({glow(34.0, 0.55, C(0.95, 0.70, 0.30, 0.8))}),
                            stroke(C(1.0, 0.86, 0.58, 0.9), 3.0));
    Keys po;
    for (int f = 0; f < frames; f += 2) {
        const double t = f / double(FPS);
        po.emplace_back(f, 0.35 + 0.25 * std::sin(t * 2.0));
    }
    animate(pgGlow, json::array({track("opacity", po)}));
    add(plan, pgGlow);

    // Arrival emission ring.
    json burst = ellipseLayer("arrival_burst", tx, ty, 120, 120, C(0, 0, 0, 0), frames,
                              json::array({glow(38.0, 0.9, C(1.0, 0.80, 0.45, 0.9))}),
                              stroke(C(1.0, 0.88, 0.62, 1.0), 8.0));
    Keys bs, bo;
    for (int f = 0; f < frames; f += 2) {
        const double t = f / double(FPS);
        const double u = clamp01((t - 3.15) / 1.15);
        bs.emplace_back(f, 0.35 + 2.3 * u);
        bo.emplace_back(f, u <= 0.0 ? 0.0 : std::pow(1.0 - u, 2.0) * 0.95);
    }
    animate(burst, json::array({track("scale_x", bs), track("scale_y", bs), track("opacity", bo)}));
    add(plan, burst);
    return plan;
}

// ---------------------------------------------------------------- scene 03
double springScale(double tau) {
    if (tau <= 0.0) return 0.0;
    const double zeta = 0.5176, wn = 18.0;
    const double wd = wn * std::sqrt(1.0 - zeta * zeta);
    return 1.0 - std::exp(-zeta * wn * tau) *
                         (std::cos(wd * tau) + (zeta * wn / wd) * std::sin(wd * tau));
}

json scene03() {
    const int frames = 240;
    json plan = basePlan("03_native_badge_spring", frames);
    json bg = baseLayer("bg", CX, CY, W, H, frames);
    bg["shape"] = json{{"type", "rect"},
                       {"fill", gradient(-W / 2, -H / 2, W / 2, H / 2,
                                         {{0.0, 0.010, 0.020, 0.050},
                                          {0.55, 0.025, 0.055, 0.100},
                                          {1.0, 0.010, 0.015, 0.030}})}};
    add(plan, bg);

    std::mt19937 rng(303);
    std::uniform_real_distribution<double> ux(40.0, W - 40.0), uy(30.0, H - 30.0);
    std::uniform_real_distribution<double> ur(25.0, 95.0), ua(0.05, 0.20);
    for (int i = 0; i < 20; ++i) {
        const double x = ux(rng), y = uy(rng), r = ur(rng), a = ua(rng);
        const bool warm = (i % 3) != 0;
        const json col = warm ? C(0.95, 0.72, 0.46, a) : C(0.48, 0.70, 0.92, a);
        json b = roundLayer("bokeh_" + std::to_string(i), x, y, r * 2.0, r * 2.0, r, col, frames,
                            json::array({glow(r * 1.35, 0.32, col)}), stroke(col, 1.0));
        Keys bx, by;
        for (int f = 0; f < frames; f += 20) {
            const double t = f / double(FPS);
            bx.emplace_back(f, x - CX + 16.0 * std::sin(t * 0.18 + i));
            by.emplace_back(f, y - CY + 11.0 * std::cos(t * 0.15 + i * 0.7));
        }
        animate(b, json::array({track("position_x", bx), track("position_y", by)}));
        add(plan, b);
    }

    // Midground silhouette: head, shoulders and rim light.
    json head = roundLayer("bust_head", 760, 380, 180, 244, 90,
                           C(0.060, 0.100, 0.130, 1.0), frames,
                           json::array({glow(26.0, 0.35, C(0.30, 0.65, 0.72, 0.8))}),
                           stroke(C(0.45, 0.75, 0.80, 0.75), 4.0));
    add(plan, head);
    json neck = roundLayer("bust_neck", 760, 560, 140, 130, 30, C(0.035, 0.060, 0.075, 1.0), frames,
                           json::array(), stroke(C(0.32, 0.58, 0.62, 0.35), 2.0));
    add(plan, neck);
    const json shoulders = polygon({{-200, 110}, {-170, -40}, {-100, -110}, {100, -110},
                                    {170, -40}, {200, 110}});
    json torso = pathLayer("bust_torso", 760, 730, 440, 300, shoulders,
                           C(0.025, 0.045, 0.060, 1.0), frames, json::array(),
                           stroke(C(0.28, 0.46, 0.50, 0.35), 2.0));
    add(plan, torso);
    json rim = pathLayer("bust_rim", 760, 730, 440, 300, shoulders, C(0, 0, 0, 0), frames,
                         json::array({glow(22.0, 0.35, C(0.35, 0.75, 0.80, 0.6))}),
                         stroke(C(0.40, 0.80, 0.82, 0.55), 3.0));
    add(plan, rim);

    // Spring-driven badge and pill.
    auto springKeys = [&](double start) {
        Keys s;
        for (int f = 0; f < frames; ++f) {
            const double v = springScale(f / double(FPS) - start);
            s.emplace_back(f, std::max(0.0, v));
        }
        return s;
    };
    const Keys iconScale = springKeys(0.55);
    const Keys pillScale = springKeys(0.72);
    const json iconOpacity = {{0, 0.0}, {17, 0.0}, {25, 1.0}, {frames - 14, 1.0}, {frames - 1, 0.0}};
    const json pillOpacity = {{0, 0.0}, {22, 0.0}, {30, 1.0}, {frames - 14, 1.0}, {frames - 1, 0.0}};

    json iconShadow = roundLayer("badge_shadow", 1320, 422, 230, 230, 50,
                                 C(0, 0, 0, 0.55), frames, json::array({glow(30.0, 0.25, C(0,0,0,0.5))}));
    animate(iconShadow, json::array({track("scale_x", iconScale), track("scale_y", iconScale),
                                     track("opacity", iconOpacity)}));
    add(plan, iconShadow);

    json badge = roundLayer("badge_icon", 1300, 400, 220, 220, 48,
                            C(0.055, 0.115, 0.190, 1.0), frames,
                            json::array({shadow(28.0, 18.0, 22.0, C(0, 0, 0, 0.55)),
                                         glow(30.0, 0.45, C(0.30, 0.72, 0.82, 0.8))}),
                            stroke(C(0.65, 0.85, 0.90, 0.40), 2.0));
    animate(badge, json::array({track("scale_x", iconScale), track("scale_y", iconScale),
                                track("opacity", iconOpacity)}));
    add(plan, badge);

    const json star = polygon({{0, -62}, {13, -13}, {62, 0}, {13, 13}, {0, 62},
                               {-13, 13}, {-62, 0}, {-13, -13}});
    json glyph = pathLayer("badge_glyph", 1300, 400, 160, 160, star,
                           C(0.96, 0.91, 0.78, 1.0), frames,
                           json::array({glow(18.0, 0.45, C(1.0, 0.85, 0.55, 0.7))}));
    animate(glyph, json::array({track("scale_x", iconScale), track("scale_y", iconScale),
                                track("opacity", iconOpacity)}));
    add(plan, glyph);

    json pill = roundLayer("badge_pill", 1300, 640, 360, 92, 46,
                           C(0.90, 0.85, 0.72, 1.0), frames,
                           json::array({shadow(22.0, 14.0, 18.0, C(0, 0, 0, 0.50))}));
    animate(pill, json::array({track("scale_x", pillScale), track("scale_y", pillScale),
                               track("opacity", pillOpacity)}));
    add(plan, pill);
    for (int i = 0; i < 3; ++i) {
        json dot = ellipseLayer("pill_dot_" + std::to_string(i), 1230 + i * 70, 640, 14, 14,
                                C(0.12, 0.18, 0.22, 1.0), frames);
        animate(dot, json::array({track("scale_x", pillScale), track("scale_y", pillScale),
                                  track("opacity", pillOpacity)}));
        add(plan, dot);
    }
    return plan;
}

// ---------------------------------------------------------------- scene 04
json scene04() {
    const int frames = 240;
    json plan = basePlan("04_native_deckled_desk", frames);
    json bg = baseLayer("bg", CX, CY, W, H, frames);
    bg["shape"] = json{{"type", "rect"},
                       {"fill", gradient(-W / 2, -H / 2, W / 2, H / 2,
                                         {{0.0, 0.055, 0.035, 0.024},
                                          {0.6, 0.110, 0.068, 0.040},
                                          {1.0, 0.028, 0.018, 0.014}})}};
    add(plan, bg);
    json vign = ellipseLayer("desk_vignette", CX, CY, 1050, 720, C(0, 0, 0, 0), frames,
                             json::array({glow(220.0, 0.20, C(0.0, 0.0, 0.0, 0.65))}),
                             stroke(C(0.0, 0.0, 0.0, 0.0), 1.0));
    add(plan, vign);

    const double pw = 1620, ph = 880;
    std::vector<std::pair<double, double>> deckle;
    std::mt19937 prng(404);
    std::uniform_real_distribution<double> jitter(-11.0, 11.0);
    const int edge = 42;
    for (int i = 0; i <= edge; ++i) deckle.emplace_back(-pw / 2 + pw * i / edge, -ph / 2 + jitter(prng));
    for (int i = 1; i <= edge; ++i) deckle.emplace_back(pw / 2 + jitter(prng), -ph / 2 + ph * i / edge);
    for (int i = 1; i <= edge; ++i) deckle.emplace_back(pw / 2 - pw * i / edge, ph / 2 + jitter(prng));
    for (int i = 1; i <= edge; ++i) deckle.emplace_back(-pw / 2 + jitter(prng), ph / 2 - ph * i / edge);
    json paper = pathLayer("deckled_paper", CX, CY, pw + 40, ph + 40, polygon(deckle),
                           C(0.90, 0.86, 0.76, 1.0), frames,
                           json::array({shadow(26.0, 12.0, 18.0, C(0, 0, 0, 0.45))}),
                           stroke(C(0.98, 0.95, 0.87, 0.55), 2.0));
    add(plan, paper);

    for (int i = 0; i < 16; ++i) {
        const double x = -720 + std::fmod(i * 293.0, 1440.0);
        const double y = -360 + std::fmod(i * 181.0, 720.0);
        const double len = 60 + std::fmod(i * 47.0, 120.0);
        json fiber = pathLayer("fiber_" + std::to_string(i), CX + x, CY + y, len + 8, 8,
                               json::array({mv(-len / 2, 0), ln(len / 2, 0)}),
                               C(0, 0, 0, 0), frames, json::array(),
                               stroke(C(0.72, 0.66, 0.54, 0.14), 1.2));
        add(plan, fiber);
    }

    struct Photo { double cx, cy, ang, s; };
    auto photoAt = [](double t) {
        const double u = (t - 2.0) / 0.9;
        if (u <= 0.0) return Photo{2110, 1260, 42, 0.72};
        const double e = ease_out_cubic(u);
        return Photo{2110 + (1310 - 2110) * e, 1260 + (560 - 1260) * e,
                     42 + (18 - 42) * e, 0.72 + 0.28 * e};
    };
    auto photoChild = [&](json layer, double ox, double oy) {
        Keys px, py, sx, rot;
        for (int f = 0; f < frames; f += 2) {
            const Photo p = photoAt(f / double(FPS));
            const double a = p.ang * PI / 180.0;
            const double rx = ox * std::cos(a) - oy * std::sin(a);
            const double ry = ox * std::sin(a) + oy * std::cos(a);
            px.emplace_back(f, p.cx + rx * p.s - CX);
            py.emplace_back(f, p.cy + ry * p.s - CY);
            sx.emplace_back(f, p.s);
            rot.emplace_back(f, p.ang);
        }
        animate(layer, json::array({track("position_x", px), track("position_y", py),
                                   track("scale_x", sx), track("scale_y", sx),
                                   track("rotation_z", rot)}));
        add(plan, layer);
    };

    json ps = roundLayer("photo_shadow", 1310, 590, 590, 410, 18, C(0, 0, 0, 0.55), frames,
                         json::array({glow(38.0, 0.30, C(0, 0, 0, 0.6))}));
    photoChild(ps, 28.0, 36.0);
    photoChild(roundLayer("photo_frame", 1310, 560, 570, 410, 18, C(0.94, 0.90, 0.81, 1.0), frames,
                          json::array({shadow(24.0, 10.0, 14.0, C(0, 0, 0, 0.35))})), 0.0, 0.0);
    photoChild(rectLayer("photo_sky", 1310, 500, 530, 270, C(0.20, 0.45, 0.58, 1.0), frames), 0.0, -55.0);
    photoChild(ellipseLayer("photo_sun", 1420, 410, 38, 38, C(0.98, 0.80, 0.46, 1.0), frames,
                            json::array({glow(30.0, 0.45, C(1.0, 0.78, 0.38, 0.8))})), 110.0, -150.0);
    const json mountBack = polygon({{-265, 50}, {-150, -90}, {-30, 30}, {90, -55}, {265, 55}});
    photoChild(pathLayer("photo_mount_back", 1310, 600, 530, 250, mountBack,
                         C(0.20, 0.30, 0.32, 1.0), frames), 0.0, 40.0);
    const json mountFront = polygon({{-270, 90}, {-90, -35}, {20, 45}, {150, -20}, {270, 95}});
    photoChild(pathLayer("photo_mount_front", 1310, 640, 540, 260, mountFront,
                         C(0.10, 0.18, 0.20, 1.0), frames), 0.0, 80.0);
    photoChild(rectLayer("photo_lake", 1310, 735, 530, 95, C(0.24, 0.42, 0.46, 1.0), frames), 0.0, 175.0);

    json contact = ellipseLayer("contact_shadow", 1310, 872, 230, 26, C(0, 0, 0, 0.55), frames);
    animate(contact, json::array({track("opacity", {{0, 0.0}, {59, 0.0}, {63, 0.32}, {frames - 13, 0.32}, {frames - 1, 0.0}})}));
    add(plan, contact);
    return plan;
}

// ---------------------------------------------------------------- scene 05
std::vector<std::pair<double, double>> inkBlob() {
    std::vector<std::pair<double, double>> pts;
    for (int i = 0; i < 32; ++i) {
        const double a = 2.0 * PI * i / 32.0;
        const double r = 260 + 65 * std::sin(3.0 * a + 0.7) + 38 * std::cos(5.0 * a + 1.9);
        pts.emplace_back(r * std::cos(a), r * std::sin(a));
    }
    return pts;
}

json scene05() {
    const int frames = 180;
    json plan = basePlan("05_native_ink_wipe", frames);

    json sky = baseLayer("normal_sky", CX, CY, W, H, frames);
    sky["shape"] = json{{"type", "rect"},
                       {"fill", gradient(-W / 2, -H / 2, W / 2, H / 2,
                                         {{0.0, 0.18, 0.36, 0.48}, {0.55, 0.55, 0.65, 0.62},
                                          {1.0, 0.86, 0.66, 0.42}})}};
    add(plan, sky);
    add(plan, roundLayer("normal_sun", 1250, 300, 216, 216, 108, C(0.98, 0.80, 0.50, 0.95), frames,
                         json::array({glow(80.0, 0.45, C(1.0, 0.78, 0.42, 0.7))}),
                         stroke(C(0.98, 0.80, 0.50, 0.95), 1.0)));
    const json backRange = polygon({{-980, -40}, {-650, -320}, {-280, -180}, {80, -360},
                                    {470, -200}, {820, -330}, {980, -40}, {980, 0}, {-980, 0}});
    add(plan, pathLayer("normal_back_range", CX, 560, 1960, 700, backRange, C(0.16, 0.26, 0.30, 1.0), frames,
                        json::array(), stroke(C(0.16, 0.26, 0.30, 1.0), 1.0)));
    const json frontRange = polygon({{-980, -40}, {-720, -260}, {-310, -120}, {30, -220},
                                     {410, -140}, {760, -280}, {980, -40}, {980, 0}, {-980, 0}});
    add(plan, pathLayer("normal_front_range", CX, 620, 1960, 620, frontRange, C(0.07, 0.13, 0.16, 1.0), frames,
                        json::array(), stroke(C(0.07, 0.13, 0.16, 1.0), 1.0)));
    add(plan, rectLayer("normal_lake", CX, 830, W, 240, C(0.10, 0.28, 0.32, 1.0), frames));
    add(plan, rectLayer("normal_shore", CX, 1000, W, 160, C(0.04, 0.07, 0.08, 1.0), frames));

    // Ink core and rim.
    const auto blob = inkBlob();
    json ink = pathLayer("ink_core", 960, 560, 1000, 1000, polygon(blob),
                         C(0.012, 0.008, 0.009, 1.0), frames,
                         json::array({glow(60.0, 0.18, C(0.35, 0.04, 0.02, 0.8))}),
                         stroke(C(0.30, 0.035, 0.02, 0.65), 3.0));
    Keys is, io, ir;
    for (int f = 0; f < frames; f += 2) {
        const double u = smoothstep(0.35, 4.5, f / double(FPS));
        is.emplace_back(f, 0.02 + 2.75 * u);
        io.emplace_back(f, 0.0 + 1.0 * smoothstep(0.0, 0.18, u));
        ir.emplace_back(f, 18.0 * u);
    }
    animate(ink, json::array({track("scale_x", is), track("scale_y", is),
                              track("opacity", io), track("rotation_z", ir)}));
    // Solarized landscape is revealed at the moving ink threshold.
    auto solarScale = [&](double delay) {
        Keys s, o;
        for (int f = 0; f < frames; f += 2) {
            const double t = f / double(FPS);
            const double u = smoothstep(delay, delay + 3.2, t);
            s.emplace_back(f, 0.01 + 1.15 * u);
            o.emplace_back(f, u > 0.0 ? 1.0 : 0.0);
        }
        return std::pair<Keys, Keys>{s, o};
    };
    auto addSolar = [&](json layer, double delay) {
        auto [s, o] = solarScale(delay);
        animate(layer, json::array({track("scale_x", s), track("scale_y", s), track("opacity", o)}));
        add(plan, layer);
    };
    json ss = baseLayer("solar_sky", CX, CY, W, H, frames);
    ss["shape"] = json{{"type", "rect"},
                       {"fill", gradient(-W / 2, -H / 2, W / 2, H / 2,
                                         {{0.0, 0.015, 0.010, 0.012}, {0.55, 0.30, 0.045, 0.020},
                                          {1.0, 0.85, 0.45, 0.12}})}};
    Keys sso;
    for (int f = 0; f < frames; f += 2) {
        const double t = f / double(FPS);
        sso.emplace_back(f, smoothstep(0.55, 2.8, t));
    }
    animate(ss, json::array({track("opacity", sso)}));
    add(plan, ss);
    addSolar(roundLayer("solar_sun", 1250, 300, 236, 236, 118, C(1.0, 0.93, 0.70, 1.0), frames,
                        json::array({glow(90.0, 0.55, C(1.0, 0.55, 0.15, 0.9))}),
                        stroke(C(1.0, 0.93, 0.70, 1.0), 1.0)), 0.8);
    addSolar(pathLayer("solar_back_range", CX, 560, 1960, 700, backRange,
                       C(0.24, 0.070, 0.025, 1.0), frames, json::array(),
                       stroke(C(0.55, 0.20, 0.06, 1.0), 1.0)), 1.0);
    addSolar(pathLayer("solar_front_range", CX, 620, 1960, 620, frontRange,
                       C(0.025, 0.010, 0.008, 1.0), frames, json::array(),
                       stroke(C(0.40, 0.12, 0.04, 1.0), 1.0)), 1.25);
    addSolar(rectLayer("solar_lake", CX, 830, W, 240, C(0.82, 0.28, 0.07, 1.0), frames), 1.5);
    addSolar(rectLayer("solar_shore", CX, 1000, W, 160, C(0.015, 0.010, 0.012, 1.0), frames), 1.7);

    // The dark threshold consumes the solarized landscape; rim trails it.
    add(plan, ink);
    json rim = pathLayer("ink_rim", 960, 560, 1080, 1080, polygon(blob), C(0, 0, 0, 0), frames,
                         json::array({glow(34.0, 0.75, C(1.0, 0.28, 0.08, 0.9))}),
                         stroke(C(1.0, 0.32, 0.10, 0.95), 7.0));
    Keys rs, ro;
    for (int f = 0; f < frames; f += 2) {
        const double u = smoothstep(0.35, 4.5, f / double(FPS));
        rs.emplace_back(f, 0.04 + 2.85 * u);
        ro.emplace_back(f, u <= 0.0 ? 0.0 : (1.0 - 0.55 * u));
    }
    animate(rim, json::array({track("scale_x", rs), track("scale_y", rs), track("opacity", ro)}));
    add(plan, rim);

    std::mt19937 trng(505);
    std::uniform_real_distribution<double> ta(-PI, PI), tl(260.0, 720.0);
    for (int i = 0; i < 10; ++i) {
        const double a = ta(trng), len = tl(trng);
        const double ex = std::cos(a) * len, ey = std::sin(a) * len * 0.72;
        json tendril = pathLayer("tendril_" + std::to_string(i), 960, 560, 1000, 800,
                                 json::array({mv(0, 0), cu(ex * 0.25, ey * 0.55, ex * 0.65, ey * 0.35, ex, ey)}),
                                 C(0, 0, 0, 0), frames, json::array(),
                                 stroke(C(0.55, 0.10, 0.04, 0.75), 5.0));
        Keys ts, to;
        for (int f = 0; f < frames; f += 2) {
            const double u = smoothstep(0.55 + i * 0.12, 3.2 + i * 0.12, f / double(FPS));
            ts.emplace_back(f, 0.02 + 0.98 * u);
            to.emplace_back(f, 0.75 * u);
        }
        animate(tendril, json::array({track("scale_x", ts), track("scale_y", ts), track("opacity", to)}));
        add(plan, tendril);
    }
    return plan;
}

// ---------------------------------------------------------------- scene 06
struct DustMote { double ox, oy, r; };
struct DustGroup { double x, y, z, phase, base_o; std::array<DustMote, 7> motes; };

json scene06() {
    const int frames = 240;
    json plan = basePlan("06_native_dust_field", frames);
    json bg = baseLayer("bg", CX, CY, W, H, frames);
    bg["shape"] = json{{"type", "rect"},
                       {"fill", gradient(-W / 2, -H / 2, W / 2, H / 2,
                                         {{0.0, 0.006, 0.008, 0.016}, {0.55, 0.025, 0.018, 0.020},
                                          {1.0, 0.050, 0.028, 0.018}})}};
    add(plan, bg);

    // 50 native groups x 7 contours = 350 individually shaped dust motes.
    // Keeping seven contours in one layer avoids the Vulkan per-layer surface
    // ceiling while the group centroid follows the curl field.
    constexpr int groups = 50;
    std::vector<DustGroup> dust(groups);
    std::mt19937 rng(909), brng(303);
    std::uniform_real_distribution<double> ux(-900.0, 900.0), uy(-620.0, 620.0);
    std::uniform_real_distribution<double> uz(420.0, 1700.0), up(0.0, 2.0 * PI);
    std::uniform_real_distribution<double> uo(0.55, 0.95), ur(3.0, 10.0);
    std::uniform_real_distribution<double> uoff(-85.0, 85.0), uscale(0.7, 1.35);
    for (auto& g : dust) {
        g.x = ux(rng); g.y = uy(rng); g.z = uz(rng);
        g.phase = up(rng); g.base_o = uo(rng);
        for (auto& m : g.motes) m = {uoff(rng), uoff(rng), ur(rng) * uscale(rng)};
    }

    std::vector<Keys> gx(groups), gy(groups), gr(groups), go(groups);
    for (int f = 0; f < frames; f += 2) {
        const double t = f / double(FPS), dt = 2.0 / FPS;
        for (int i = 0; i < groups; ++i) {
            auto& g = dust[i];
            const double kx = 1.0 / 430.0, ky = 1.0 / 360.0, kz = 1.0 / 500.0;
            const double vx = (-ky * std::sin(kx * g.x + t * 0.6 + g.phase) *
                                   std::sin(ky * g.y + t * 0.5) -
                               kz * std::cos(kz * g.z + t * 0.9) *
                                   std::cos(kx * g.x + t * 0.3));
            const double vy = (-kz * std::sin(ky * g.y + t * 0.7) *
                                   std::sin(kz * g.z + t * 0.4) -
                               kx * std::cos(kx * g.x + t * 0.6) *
                                   std::cos(ky * g.y + t * 0.5));
            g.x += vx * 34.0 * dt;
            g.y += vy * 26.0 * dt;
            if (g.x < -980.0) g.x += 1960.0;
            if (g.x > 980.0) g.x -= 1960.0;
            if (g.y < -660.0) g.y += 1320.0;
            if (g.y > 660.0) g.y -= 1320.0;
            const double sx = CX + g.x;
            const double sy = CY + g.y;
            const double edge = smoothstep(0.0, 140.0, sx) *
                                (1.0 - smoothstep(W - 140.0, W, sx)) *
                                smoothstep(0.0, 110.0, sy) *
                                (1.0 - smoothstep(H - 110.0, H, sy));
            gx[i].emplace_back(f, sx - CX);
            gy[i].emplace_back(f, sy - CY);
            gr[i].emplace_back(f, 8.0 * std::sin(t * 0.35 + g.phase));
            go[i].emplace_back(f, g.base_o * edge * smoothstep(0.0, 0.7, t) *
                                      (1.0 - smoothstep(7.2, 8.0, t)));
        }
    }

    for (int i = 0; i < groups; ++i) {
        const double warmth = clamp01((dust[i].z - 500.0) / 1200.0);
        const json col = C(0.95 * (1.0 - warmth) + 0.55 * warmth,
                           0.78 * (1.0 - warmth) + 0.76 * warmth,
                           0.55 * (1.0 - warmth) + 0.96 * warmth, 0.90);
        const double rr = std::max(7.0, dust[i].motes[0].r);
        json layer = roundLayer("dust_group_" + std::to_string(i), CX, CY,
                                rr * 2.0, rr * 2.0, rr, col, frames,
                                json::array({glow(30.0, 0.55, col)}),
                                stroke(col, 1.0));
        animate(layer, json::array({track("position_x", gx[i]), track("position_y", gy[i]),
                                    track("rotation_z", gr[i]), track("opacity", go[i])}));
        add(plan, layer);
    }

    std::uniform_real_distribution<double> bx(80.0, W - 80.0), by(60.0, H - 60.0);
    std::uniform_real_distribution<double> br(18.0, 60.0), ba(0.05, 0.14);
    for (int i = 0; i < 8; ++i) {
        const double x = bx(brng), y = by(brng), r = br(brng), a = ba(brng);
        const json col = (i % 3) ? C(0.95, 0.72, 0.46, a) : C(0.45, 0.68, 0.92, a);
        add(plan, roundLayer("soft_bokeh_" + std::to_string(i), x, y, r * 2.0, r * 2.0, r, col, frames,
                             json::array({glow(r * 1.2, 0.25, col)}),
                             stroke(col, 1.0)));
    }
    return plan;
}

json finalize(const std::string& id, int frames, const json& plan) {
    json out = TemplateComposition::renderPlan(id, W, H, FPS, frames, plan["layers"]);
    out["output"]["path"] = id + ".mp4";
    return out;
}

} // namespace

int main(int argc, char** argv) {
    const std::filesystem::path out = argc > 1 ? argv[1] : "plans";
    std::filesystem::create_directories(out);
    const std::vector<std::tuple<std::string, int, json>> scenes = {
        {"01_2p5d_parallax_native.plan.json", 240, finalize("01_native_2p5d_parallax", 240, scene01())},
        {"02_spline_network_native.plan.json", 240, finalize("02_native_spline_network", 240, scene02())},
        {"03_badge_spring_native.plan.json", 240, finalize("03_native_badge_spring", 240, scene03())},
        {"04_deckled_desk_native.plan.json", 240, finalize("04_native_deckled_desk", 240, scene04())},
        {"05_ink_wipe_native.plan.json", 180, finalize("05_native_ink_wipe", 180, scene05())},
        {"06_dust_field_native.plan.json", 240, finalize("06_native_dust_field", 240, scene06())}};
    for (const auto& [name, frames, plan] : scenes) {
        std::ofstream f(out / name);
        f << plan.dump(2) << "\n";
        std::error_code ec;
        const auto bytes = std::filesystem::file_size(out / name, ec);
        std::cout << name << " " << bytes << " bytes, " << plan["layers"].size()
                  << " layers, " << frames << " frames\n";
    }
    return 0;
}
