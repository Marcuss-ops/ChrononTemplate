// ChrononTemplate / tools/geometric_glow
//
// Native C++ + Blend2D recreation of the minimalist neon motion-graphics
// sequence captured in reference frames 51..66 of
// visual_venture_channel_archive/02_Disturbing_Webpages_Deleted_From_Internet
// (source sampling: 1 fps, 640x360).
//
// Design:
//   * 16 measured keyframes (one per reference frame), each holding the exact
//     geometry/color/alpha measured from the PNGs.
//   * Keyframe k lands exactly at t = k seconds (frame 30k); in-between frames
//     are ease-in-out-cubic interpolations, so the motion is real:
//       - the flowchart box morphs/shrinks into the rounded square
//       - the two spheres travel, warm up white -> pink -> saturated red
//       - the dot row (10 dots) morphs row -> smile arc -> orbiting ring
//       - elements crossfade in/out exactly where the reference cuts them
//   * Post: procedural star dust, soft halo, radial vignette, film grain.
//
// Pure C++ / Blend2D. No Python anywhere in the render path.

#include <blend2d.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <random>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace chronon::geometric_glow {

constexpr double kPi = 3.14159265358979323846;
constexpr int kW = 640;              // logical width  (matches reference)
constexpr int kH = 360;              // logical height (matches reference)
constexpr int kScale = 2;            // device scale (output 1280x720)
constexpr int kFps = 30;
constexpr int kKeys = 16;            // f51..f66 @ 1 fps
constexpr int kHold = kFps;          // 1 s hold on the last keyframe
constexpr int kTotalFrames = (kKeys - 1) * kFps + kHold;  // 480 = 16 s

// ───────────────────────────────── state ─────────────────────────────────────

struct State {
    // dashed flowchart border + 3 stacked blocks (f51/f52)
    double dashedA = 0.0;
    double flowA   = 0.0;     // blocks + connectors
    double flowFill = 0.0;    // 0 = outlined blocks, 1 = solid white blocks

    // main rounded rectangle outline (morphs f51->f55, returns f59->f62)
    double boxA = 0.0;
    double boxX = 260.0, boxY = 106.0, boxW = 116.0, boxH = 151.0;
    double boxGap = 0.0;      // 0..1 -> open gap on the right of the top edge

    double haloA = 0.10;      // soft radial halo behind the subject
    double beamA = 0.0;       // conical light beam under the top bar (f57/f58)

    // detached top-bar capsule (f56..f58)
    double barA = 0.0, barX = 0.0, barY = 0.0, barW = 0.0, barH = 0.0;

    // vertical line segment (f56 remnant, f63 right rail)
    double vlA = 0.0, vlX = 0.0, vlY0 = 0.0, vlY1 = 0.0;

    // main sphere (white -> pink -> red)
    double bigA = 0.0, bigX = 307.0, bigY = 195.0, bigR = 12.0;
    double bigCR = 255.0, bigCG = 255.0, bigCB = 255.0;
    double bigHot = 0.55;    // white-hot core mix

    // small companion dot (grey in the reference)
    double dotA = 0.0, dotX = 336.0, dotY = 180.0, dotR = 7.5;

    // the 10 indicator dots (row -> arc -> ring)
    double dotsA = 0.0, dotsR = 5.0;
    std::array<double, 10> dx{};
    std::array<double, 10> dy{};

    // final dark slab (f66)
    double tileA = 0.0;
};

using Arr10 = std::array<double, 10>;

inline void setRow(State& s, double y, double x0, double step) {
    for (int i = 0; i < 10; ++i) { s.dx[i] = x0 + step * i; s.dy[i] = y; }
}

inline void setArc(State& s) {
    // measured smile arc (f63), 10 dots
    const double xs[10] = {247, 275, 305, 335, 366, 397, 429, 460, 490, 519};
    const double ys[10] = {262, 271, 277, 283, 286, 286, 285, 282, 276, 269};
    for (int i = 0; i < 10; ++i) { s.dx[i] = xs[i]; s.dy[i] = ys[i]; }
}

inline void setRing(State& s, double cx, double cy, double R) {
    // measured ring (f64/f65): 10 dots, 36 deg apart, first at -176 deg
    for (int i = 0; i < 10; ++i) {
        const double th = (-176.0 + 36.0 * i) * kPi / 180.0;
        s.dx[i] = cx + R * std::cos(th);
        s.dy[i] = cy + R * std::sin(th);
    }
}

inline const std::array<State, kKeys>& keyframes() {
    static const std::array<State, kKeys> K = [] {
        std::array<State, kKeys> a{};

        // k0 — f51: dashed outer box + 3 outlined blocks + connectors
        {
            State& s = a[0];
            s.dashedA = 1.0; s.flowA = 1.0; s.flowFill = 0.0;
            s.boxX = 260; s.boxY = 106; s.boxW = 116; s.boxH = 151;
            s.haloA = 0.10;
        }
        // k1 — f52: same box (smaller), blocks now solid white
        {
            State& s = a[1];
            s.dashedA = 1.0; s.flowA = 1.0; s.flowFill = 1.0;
            s.boxX = 265; s.boxY = 112; s.boxW = 107; s.boxH = 139;
            s.haloA = 0.10;
        }
        // k2 — f53: blocks gone, rounded square outline + two spheres
        {
            State& s = a[2];
            s.boxA = 1.0;
            s.boxX = 265; s.boxY = 124; s.boxW = 107; s.boxH = 111;
            s.haloA = 0.18;
            s.bigA = 1.0; s.bigX = 307; s.bigY = 195; s.bigR = 12;
            s.dotA = 1.0; s.dotX = 336; s.dotY = 180; s.dotR = 7.5;
        }
        // k3 — f54: box taller, spheres travelled down
        {
            State& s = a[3];
            s.boxA = 1.0;
            s.boxX = 265; s.boxY = 128; s.boxW = 107; s.boxH = 124;
            s.haloA = 0.18;
            s.bigA = 1.0; s.bigX = 306; s.bigY = 213; s.bigR = 13;
            s.dotA = 1.0; s.dotX = 337; s.dotY = 205; s.dotR = 7.5;
        }
        // k4 — f55: settled pill box
        {
            State& s = a[4];
            s.boxA = 1.0;
            s.boxX = 264; s.boxY = 128; s.boxW = 108; s.boxH = 126;
            s.haloA = 0.18;
            s.bigA = 1.0; s.bigX = 308; s.bigY = 217; s.bigR = 13.5;
            s.dotA = 1.0; s.dotX = 337; s.dotY = 211; s.dotR = 7.5;
        }
        // k5 — f56: box broken: top bar detached, right rail, spheres merged view
        {
            State& s = a[5];
            s.boxA = 0.0;
            s.boxX = 264; s.boxY = 128; s.boxW = 108; s.boxH = 126;
            s.haloA = 0.20;
            s.barA = 1.0; s.barX = 302; s.barY = 84; s.barW = 27; s.barH = 6;
            s.vlA = 1.0; s.vlX = 368; s.vlY0 = 135; s.vlY1 = 222;
            s.bigA = 1.0; s.bigX = 319; s.bigY = 217; s.bigR = 14;
            s.dotA = 1.0; s.dotX = 355; s.dotY = 219.5; s.dotR = 7.5;
        }
        // k6 — f57: bar widens, beam on, rail shrinks to a stub
        {
            State& s = a[6];
            s.haloA = 0.20;
            s.barA = 1.0; s.barX = 299; s.barY = 84; s.barW = 33; s.barH = 8;
            s.vlA = 0.55; s.vlX = 368; s.vlY0 = 135; s.vlY1 = 141;
            s.beamA = 0.55;
            s.bigA = 1.0; s.bigX = 322; s.bigY = 217; s.bigR = 15;
            s.dotA = 1.0; s.dotX = 360; s.dotY = 219.6; s.dotR = 7.5;
        }
        // k7 — f58: beam brighter, indicator row starts to appear
        {
            State& s = a[7];
            s.haloA = 0.20;
            s.barA = 1.0; s.barX = 299; s.barY = 85; s.barW = 34; s.barH = 9;
            s.vlA = 0.5; s.vlX = 368; s.vlY0 = 135; s.vlY1 = 141;
            s.beamA = 0.85;
            s.bigA = 1.0; s.bigX = 322; s.bigY = 217; s.bigR = 15;
            s.dotA = 1.0; s.dotX = 360; s.dotY = 219.6; s.dotR = 7.5;
            s.dotsA = 0.25; s.dotsR = 5; setRow(s, 253.5, 227.7, 20.44);
        }
        // k8 — f59: box back with a gap in the top edge; sphere turns pink;
        //      full indicator row below
        {
            State& s = a[8];
            s.boxA = 1.0;
            s.boxX = 265; s.boxY = 104; s.boxW = 106; s.boxH = 124;
            s.boxGap = 1.0;
            s.haloA = 0.18;
            s.bigA = 1.0; s.bigX = 309; s.bigY = 192; s.bigR = 14;
            s.bigCR = 255; s.bigCG = 175; s.bigCB = 175; s.bigHot = 0.35;
            s.dotA = 1.0; s.dotX = 338; s.dotY = 195; s.dotR = 7.5;
            s.dotsA = 0.80; s.dotsR = 5; setRow(s, 253.5, 227.7, 20.44);
        }
        // k9 — f60: box intact, sphere light red and higher, row brighter
        {
            State& s = a[9];
            s.boxA = 1.0;
            s.boxX = 265; s.boxY = 101; s.boxW = 107; s.boxH = 125;
            s.haloA = 0.18;
            s.bigA = 1.0; s.bigX = 307; s.bigY = 172; s.bigR = 19;
            s.bigCR = 250; s.bigCG = 125; s.bigCB = 125; s.bigHot = 0.25;
            s.dotA = 1.0; s.dotX = 336; s.dotY = 192; s.dotR = 8;
            s.dotsA = 1.0; s.dotsR = 7; setRow(s, 251, 227.7, 20.44);
        }
        // k10 — f61: sphere saturated red, larger
        {
            State& s = a[10];
            s.boxA = 1.0;
            s.boxX = 265; s.boxY = 101; s.boxW = 107; s.boxH = 125;
            s.haloA = 0.18;
            s.bigA = 1.0; s.bigX = 307; s.bigY = 157; s.bigR = 24;
            s.bigCR = 245; s.bigCG = 50; s.bigCB = 50; s.bigHot = 0.18;
            s.dotA = 1.0; s.dotX = 336; s.dotY = 192; s.dotR = 8;
            s.dotsA = 1.0; s.dotsR = 7.5; setRow(s, 251, 227.7, 20.44);
        }
        // k11 — f62: same, sphere at peak
        {
            State& s = a[11];
            s.boxA = 1.0;
            s.boxX = 265; s.boxY = 101; s.boxW = 107; s.boxH = 125;
            s.haloA = 0.18;
            s.bigA = 1.0; s.bigX = 307; s.bigY = 153; s.bigR = 26;
            s.bigCR = 242; s.bigCG = 25; s.bigCB = 25; s.bigHot = 0.15;
            s.dotA = 1.0; s.dotX = 336; s.dotY = 192; s.dotR = 8;
            s.dotsA = 1.0; s.dotsR = 7.5; setRow(s, 251, 227.7, 20.44);
        }
        // k12 — f63: box dissolved to a right rail, row bends into a smile arc
        {
            State& s = a[12];
            s.boxA = 0.0;
            s.haloA = 0.18;
            s.vlA = 1.0; s.vlX = 378; s.vlY0 = 131; s.vlY1 = 246;
            s.bigA = 1.0; s.bigX = 317.5; s.bigY = 176.5; s.bigR = 26;
            s.bigCR = 242; s.bigCG = 25; s.bigCB = 25; s.bigHot = 0.15;
            s.dotA = 1.0; s.dotX = 346; s.dotY = 215; s.dotR = 8;
            s.dotsA = 1.0; s.dotsR = 7.5; setArc(s);
        }
        // k13 — f64: red core + 10-dot orbit ring (R=58)
        {
            State& s = a[13];
            s.haloA = 0.20;
            s.bigA = 1.0; s.bigX = 320; s.bigY = 182; s.bigR = 26;
            s.bigCR = 242; s.bigCG = 25; s.bigCB = 25; s.bigHot = 0.15;
            s.dotsA = 1.0; s.dotsR = 8; setRing(s, 320, 181, 58);
        }
        // k14 — f65: constellation shrinks (ring R=44, smaller core)
        {
            State& s = a[14];
            s.haloA = 0.20;
            s.bigA = 1.0; s.bigX = 319.5; s.bigY = 181.5; s.bigR = 19.5;
            s.bigCR = 242; s.bigCG = 25; s.bigCB = 25; s.bigHot = 0.15;
            s.dotsA = 1.0; s.dotsR = 6.5; setRing(s, 320, 181, 44);
        }
        // k15 — f66: cut to the dark slab device
        {
            State& s = a[15];
            s.haloA = 0.06;
            s.tileA = 1.0;
        }
        return a;
    }();
    return K;
}

inline double easeInOutCubic(double t) {
    return t < 0.5 ? 4.0 * t * t * t : 1.0 - std::pow(-2.0 * t + 2.0, 3) / 2.0;
}

inline double lerpD(double a, double b, double t) { return a + (b - a) * t; }

inline State lerpS(const State& A, const State& B, double t) {
    State r;
#define GG_L(f) r.f = lerpD(A.f, B.f, t)
    GG_L(dashedA); GG_L(flowA); GG_L(flowFill);
    GG_L(boxA); GG_L(boxX); GG_L(boxY); GG_L(boxW); GG_L(boxH); GG_L(boxGap);
    GG_L(haloA); GG_L(beamA);
    GG_L(barA); GG_L(barX); GG_L(barY); GG_L(barW); GG_L(barH);
    GG_L(vlA); GG_L(vlX); GG_L(vlY0); GG_L(vlY1);
    GG_L(bigA); GG_L(bigX); GG_L(bigY); GG_L(bigR);
    GG_L(bigCR); GG_L(bigCG); GG_L(bigCB); GG_L(bigHot);
    GG_L(dotA); GG_L(dotX); GG_L(dotY); GG_L(dotR);
    GG_L(dotsA); GG_L(dotsR);
    GG_L(tileA);
#undef GG_L
    for (int i = 0; i < 10; ++i) { r.dx[i] = lerpD(A.dx[i], B.dx[i], t); r.dy[i] = lerpD(A.dy[i], B.dy[i], t); }
    return r;
}

inline State stateAt(double t) {
    const auto& K = keyframes();
    if (t <= 0.0) return K[0];
    const int k = static_cast<int>(t);
    if (k >= kKeys - 1) return K[kKeys - 1];
    return lerpS(K[k], K[k + 1], easeInOutCubic(t - k));
}

// ───────────────────────────── drawing helpers ───────────────────────────────

inline uint8_t a8(double a) {
    return static_cast<uint8_t>(std::clamp(a, 0.0, 1.0) * 255.0 + 0.5);
}

// Multi-pass white neon stroke (glow bloom + hot core).
inline void neonStroke(BLContext& c, const BLPath& p, double w, double a) {
    if (a <= 0.004) return;
    c.setStrokeCaps(BL_STROKE_CAP_ROUND);
    c.setStrokeJoin(BL_STROKE_JOIN_ROUND);
    c.setStrokeStyle(BLRgba32(255, 255, 255, a8(a * 0.09)));
    c.setStrokeWidth(w * 5.0);
    c.strokePath(p);
    c.setStrokeStyle(BLRgba32(255, 255, 255, a8(a * 0.20)));
    c.setStrokeWidth(w * 2.6);
    c.strokePath(p);
    c.setStrokeStyle(BLRgba32(255, 255, 255, a8(a * 0.48)));
    c.setStrokeWidth(w * 1.4);
    c.strokePath(p);
    c.setStrokeStyle(BLRgba32(255, 255, 255, a8(a)));
    c.setStrokeWidth(w);
    c.strokePath(p);
}

// Multi-pass glowing sphere. hot = white-hot core mix (0 for pure red).
inline void glowSphere(BLContext& c, double x, double y, double r,
                       double cr, double cg, double cb, double a, double hot) {
    if (a <= 0.004 || r <= 0.01) return;
    c.setFillStyle(BLRgba32(a8(cr), a8(cg), a8(cb), a8(a * 0.10)));
    c.fillCircle(BLCircle(x, y, r * 2.7));
    c.setFillStyle(BLRgba32(a8(cr), a8(cg), a8(cb), a8(a * 0.22)));
    c.fillCircle(BLCircle(x, y, r * 1.5));
    c.setFillStyle(BLRgba32(a8(cr), a8(cg), a8(cb), a8(a)));
    c.fillCircle(BLCircle(x, y, r));
    if (hot > 0.01) {
        const double hc = 255.0 * hot;
        c.setFillStyle(BLRgba32(a8(hc + cr * (1.0 - hot)),
                                a8(hc + cg * (1.0 - hot)),
                                a8(hc + cb * (1.0 - hot)), a8(a * 0.55)));
        c.fillCircle(BLCircle(x, y, r * 0.45));
    }
}

// Small indicator dot with a tight halo (measured glow radius ~1.25x core).
inline void glowDot(BLContext& c, double x, double y, double r,
                    double cr, double cg, double cb, double a) {
    if (a <= 0.004 || r <= 0.01) return;
    c.setFillStyle(BLRgba32(a8(cr), a8(cg), a8(cb), a8(a * 0.12)));
    c.fillCircle(BLCircle(x, y, r * 1.9));
    c.setFillStyle(BLRgba32(a8(cr), a8(cg), a8(cb), a8(a * 0.30)));
    c.fillCircle(BLCircle(x, y, r * 1.25));
    c.setFillStyle(BLRgba32(a8(cr), a8(cg), a8(cb), a8(a)));
    c.fillCircle(BLCircle(x, y, r));
}

// Rounded-rect outline path, optionally broken by a gap on the top edge.
// gapFrom/gapTo are fractions of the width (-1 = no gap).
inline BLPath roundRectPath(double x, double y, double w, double h, double r,
                            double gapFrom = -1.0, double gapTo = -1.0) {
    BLPath p;
    const bool gap = gapFrom >= 0.0;
    const double gx0 = x + w * gapFrom, gx1 = x + w * gapTo;
    bool started = false;
    auto emit = [&](double px, double py) {
        if (gap && py <= y + 0.01 && px >= gx0 && px <= gx1) { started = false; return; }
        if (!started) { p.moveTo(px, py); started = true; }
        else p.lineTo(px, py);
    };
    const int NE = 20;   // straight edges
    const int NC = 6;    // corner quarters
    // top edge (L->R)
    for (int i = 0; i <= NE; ++i) emit(x + r + (w - 2 * r) * i / NE, y);
    // top-right corner
    for (int i = 0; i <= NC; ++i) {
        const double a = -kPi / 2 + (kPi / 2) * i / NC;
        emit(x + w - r + r * std::cos(a), y + r + r * std::sin(a));
    }
    // right edge
    for (int i = 1; i <= NE; ++i) emit(x + w, y + r + (h - 2 * r) * i / NE);
    // bottom-right corner
    for (int i = 1; i <= NC; ++i) {
        const double a = (kPi / 2) * i / NC;
        emit(x + w - r + r * std::cos(a), y + h - r + r * std::sin(a));
    }
    // bottom edge (R->L)
    for (int i = 1; i <= NE; ++i) emit(x + w - r - (w - 2 * r) * i / NE, y + h);
    // bottom-left corner
    for (int i = 1; i <= NC; ++i) {
        const double a = kPi / 2 + (kPi / 2) * i / NC;
        emit(x + r + r * std::cos(a), y + h - r + r * std::sin(a));
    }
    // left edge (B->T)
    for (int i = 1; i <= NE; ++i) emit(x, y + h - r - (h - 2 * r) * i / NE);
    // top-left corner
    for (int i = 0; i <= NC; ++i) {
        const double a = kPi + (kPi / 2) * i / NC;
        emit(x + r + r * std::cos(a), y + r + r * std::sin(a));
    }
    return p;
}

// Dashed rounded border (manual dashes — this Blend2D build has no dash API).
inline void dashedRect(BLContext& c, double x, double y, double w, double h,
                       double r, double a) {
    if (a <= 0.004) return;
    const double dash = 7.0, gap = 6.0, th = 1.5;
    BLPath p;
    auto edge = [&](double x0, double y0, double x1, double y1) {
        const double len = std::hypot(x1 - x0, y1 - y0);
        const double ux = (x1 - x0) / len, uy = (y1 - y0) / len;
        for (double s = dash * 0.5; s + dash * 0.5 < len; s += dash + gap) {
            const double t0 = s, t1 = std::min(s + dash, len);
            p.moveTo(x0 + ux * t0, y0 + uy * t0);
            p.lineTo(x0 + ux * t1, y0 + uy * t1);
        }
    };
    edge(x + r, y, x + w - r, y);
    edge(x + w, y + r, x + w, y + h - r);
    edge(x + w - r, y + h, x + r, y + h);
    edge(x, y + h - r, x, y + r);
    neonStroke(c, p, th, a * 0.9);
}

// ─────────────────────────────── background ──────────────────────────────────

using Dust = std::array<double, 4>;   // x, y, r, alpha/255

inline std::vector<Dust> makeDust() {
    std::mt19937 rng(20261030u);
    std::uniform_real_distribution<double> ux(2.0, kW - 2.0), uy(2.0, kH - 2.0);
    std::uniform_real_distribution<double> ur(0.45, 1.15), ua(0.25, 0.75);
    std::vector<Dust> d;
    d.reserve(85);
    for (int i = 0; i < 85; ++i) d.push_back({ux(rng), uy(rng), ur(rng), ua(rng)});
    return d;
}

inline void drawBackground(BLContext& c, const std::vector<Dust>& dust, double haloA) {
    c.setFillStyle(BLRgba32(0, 0, 0));
    c.fillRect(BLRect(0, 0, kW, kH));

    // star dust
    for (const auto& d : dust) {
        c.setFillStyle(BLRgba32(235, 238, 245, a8(d[3])));
        c.fillCircle(BLCircle(d[0], d[1], d[2]));
    }

    // radial vignette (concentric soft rings darkening toward the corners)
    for (int i = 0; i < 10; ++i) {
        const double r = 200.0 + 26.0 * i;
        const double k = i / 9.0;
        const double a = 0.34 * k * k;
        BLPath p;
        p.addCircle(BLCircle(kW * 0.5, kH * 0.5, r));
        c.setStrokeStyle(BLRgba32(0, 0, 0, a8(a)));
        c.setStrokeWidth(30.0);
        c.strokePath(p);
    }

    // soft halo behind the subject
    if (haloA > 0.004) {
        const double rs[4] = {270.0, 200.0, 140.0, 90.0};
        const double as[4] = {0.18, 0.22, 0.26, 0.30};
        for (int i = 0; i < 4; ++i) {
            c.setFillStyle(BLRgba32(232, 238, 255, a8(haloA * as[i])));
            c.fillCircle(BLCircle(kW * 0.5, kH * 0.5, rs[i]));
        }
    }
}

// ──────────────────────────────── elements ───────────────────────────────────

inline void drawFlow(BLContext& c, const State& s) {
    if (s.dashedA > 0.004)
        dashedRect(c, s.boxX, s.boxY, s.boxW, s.boxH, 9.0, s.dashedA);
    if (s.flowA <= 0.004) return;

    const double bx0 = s.boxX + s.boxW * 0.17;
    const double bw  = s.boxW * 0.66;
    const double by0 = s.boxY + s.boxH * 0.07;
    const double bh  = s.boxH * 0.22;
    const double conn = (s.boxH * 0.86 - 3.0 * bh) * 0.5;
    const double alpha[3] = {1.0, 0.80, 0.62};
    double top = 0.0, bottom = 0.0;

    for (int i = 0; i < 3; ++i) {
        const double by = by0 + i * (bh + conn);
        const double a = s.flowA * alpha[i];
        BLPath blk = roundRectPath(bx0, by, bw, bh, 6.0);
        if (s.flowFill > 0.01) {
            c.setFillStyle(BLRgba32(255, 255, 255, a8(a * s.flowFill)));
            c.fillPath(blk);
        }
        neonStroke(c, blk, 1.5, a * (1.0 - 0.25 * s.flowFill));
        if (i == 0) { top = by + bh; }
        if (i == 1) {
            bottom = by;
            BLPath link;
            link.moveTo(bx0 + bw * 0.5, top);
            link.lineTo(bx0 + bw * 0.5, bottom);
            neonStroke(c, link, 1.4, s.flowA * (i == 0 ? 1.0 : 0.7));
        }
        if (i == 2) {
            BLPath link;
            link.moveTo(bx0 + bw * 0.5, by0 + 2.0 * (bh + conn) + bh);
            link.lineTo(bx0 + bw * 0.5, by);
            neonStroke(c, link, 1.4, s.flowA * 0.62);
        }
    }
}

inline void drawBeam(BLContext& c, const State& s) {
    if (s.beamA <= 0.004) return;
    const double cx = s.barX + s.barW * 0.5;
    const double y0 = s.barY + s.barH;
    const double y1 = 228.0;
    auto tri = [&](double topHalf, double botHalf) {
        BLPath p;
        p.moveTo(cx - topHalf, y0);
        p.lineTo(cx + topHalf, y0);
        p.lineTo(cx + botHalf, y1);
        p.lineTo(cx - botHalf, y1);
        p.close();
        return p;
    };
    c.setCompOp(BL_COMP_OP_PLUS);
    c.setFillStyle(BLRgba32(235, 240, 255, a8(0.055 * s.beamA)));
    c.fillPath(tri(6.0, 30.0));
    c.setFillStyle(BLRgba32(245, 248, 255, a8(0.06 * s.beamA)));
    c.fillPath(tri(3.0, 14.0));
    c.setCompOp(BL_COMP_OP_SRC_OVER);
}

inline void drawBar(BLContext& c, const State& s) {
    if (s.barA <= 0.004) return;
    const double r = s.barH * 0.5;
    auto cap = [&](double grow) {
        return BLRoundRect(s.barX - grow, s.barY - grow,
                           s.barW + 2 * grow, s.barH + 2 * grow,
                           r + grow, r + grow);
    };
    c.setFillStyle(BLRgba32(255, 255, 255, a8(s.barA * 0.10)));
    c.fillRoundRect(cap(6.0));
    c.setFillStyle(BLRgba32(255, 255, 255, a8(s.barA * 0.26)));
    c.fillRoundRect(cap(2.4));
    c.setFillStyle(BLRgba32(255, 255, 255, a8(s.barA)));
    c.fillRoundRect(cap(0.0));
}

inline void drawVLine(BLContext& c, const State& s) {
    if (s.vlA <= 0.004) return;
    BLPath p;
    p.moveTo(s.vlX, s.vlY0);
    p.lineTo(s.vlX, s.vlY1);
    neonStroke(c, p, 1.8, s.vlA);
}

inline void drawBox(BLContext& c, const State& s) {
    if (s.boxA <= 0.004) return;
    BLPath p = roundRectPath(s.boxX, s.boxY, s.boxW, s.boxH, 9.0,
                             s.boxGap > 0.01 ? 0.55 : -1.0,
                             s.boxGap > 0.01 ? 0.55 + 0.20 * s.boxGap : -1.0);
    neonStroke(c, p, 1.6, s.boxA);
}

// Final dark slab device (f66): concave-edged slab, metallic top highlight,
// centre inset with wood-grain striations and a faint amber LED.
inline void drawTile(BLContext& c, double a) {
    if (a <= 0.004) return;
    const double x0 = 221, x1 = 418, y0 = 88, y1 = 223;
    const double bowY = 5.0, bowX = 4.0;
    const int N = 24;

    BLPath slab;
    for (int i = 0; i <= N; ++i) {
        const double t = double(i) / N;
        const double px = x0 + (x1 - x0) * t, py = y0 + bowY * std::sin(kPi * t);
        if (i == 0) slab.moveTo(px, py); else slab.lineTo(px, py);
    }
    for (int i = 1; i <= N; ++i) {
        const double t = double(i) / N;
        slab.lineTo(x1 - bowX * std::sin(kPi * t), y0 + (y1 - y0) * t);
    }
    for (int i = 1; i <= N; ++i) {
        const double t = double(i) / N;
        slab.lineTo(x1 - (x1 - x0) * t, y1 - bowY * std::sin(kPi * t));
    }
    for (int i = 1; i <= N; ++i) {
        const double t = double(i) / N;
        slab.lineTo(x0 + bowX * std::sin(kPi * t), y1 - (y1 - y0) * t);
    }
    slab.close();

    c.save();
    c.setGlobalAlpha(float(a));
    c.setFillStyle(BLRgba32(26, 26, 29));
    c.fillPath(slab);
    c.setFillStyle(BLRgba32(14, 14, 16));
    c.fillRoundRect(BLRoundRect(x0 + 4, y0 + (y1 - y0) * 0.55, x1 - x0 - 8, (y1 - y0) * 0.45, 6, 6));

    // metallic top highlight
    BLPath top;
    for (int i = 0; i <= N; ++i) {
        const double t = double(i) / N;
        const double px = x0 + (x1 - x0) * t, py = y0 + bowY * std::sin(kPi * t);
        if (i == 0) top.moveTo(px, py); else top.lineTo(px, py);
    }
    neonStroke(c, top, 1.6, 0.95);

    // side streaks
    BLPath sides;
    sides.moveTo(x0 + 3.5, y0 + 14); sides.lineTo(x0 + 3.5, y1 - 16);
    sides.moveTo(x1 - 3.5, y0 + 14); sides.lineTo(x1 - 3.5, y1 - 16);
    c.setStrokeCaps(BL_STROKE_CAP_ROUND);
    c.setStrokeStyle(BLRgba32(255, 255, 255, 90));
    c.setStrokeWidth(1.2);
    c.strokePath(sides);

    // centre inset with striations
    const double ix = 302, iy = 150, iw = 36, ih = 36;
    c.setFillStyle(BLRgba32(58, 48, 40));
    c.fillRoundRect(BLRoundRect(ix, iy, iw, ih, 3, 3));
    for (int i = 0; i < 7; ++i) {
        const double sx = ix + 3 + i * 4.6;
        c.setFillStyle(BLRgba32(i % 2 ? 78 : 44, i % 2 ? 66 : 36, i % 2 ? 54 : 30));
        c.fillRect(BLRect(int(sx), int(iy + 3), int(sx + 2), int(iy + ih - 3)));
    }
    c.setStrokeStyle(BLRgba32(120, 104, 88, 200));
    c.setStrokeWidth(1.0);
    BLPath inset = roundRectPath(ix, iy, iw, ih, 3.0);
    c.strokePath(inset);

    // amber LED
    glowDot(c, 315, 184, 2.6, 255, 130, 60, 0.75);
    c.restore();
}

// ─────────────────────────────── the scene ───────────────────────────────────

inline void drawScene(BLContext& c, const State& s, int frameIdx,
                      const std::vector<Dust>& dust, bool grain) {
    drawBackground(c, dust, s.haloA);
    drawBeam(c, s);
    drawFlow(c, s);
    drawBox(c, s);
    drawBar(c, s);
    drawVLine(c, s);
    if (s.dotA > 0.004) glowDot(c, s.dotX, s.dotY, s.dotR, 168, 168, 172, s.dotA);
    if (s.bigA > 0.004)
        glowSphere(c, s.bigX, s.bigY, s.bigR, s.bigCR, s.bigCG, s.bigCB, s.bigA, s.bigHot);
    if (s.dotsA > 0.004) {
        for (int i = 0; i < 10; ++i)
            glowDot(c, s.dx[i], s.dy[i], s.dotsR, 255, 255, 255, s.dotsA);
    }
    drawTile(c, s.tileA);

    if (grain) {
        std::mt19937 rng(0x9E3779B9u ^ (static_cast<unsigned>(frameIdx) * 2654435761u));
        for (int i = 0; i < 2200; ++i) {
            const double x = double(rng() % kW);
            const double y = double(rng() % kH);
            if (i & 1) {
                c.setFillStyle(BLRgba32(255, 255, 255, uint8_t(8 + rng() % 26)));
            } else {
                c.setFillStyle(BLRgba32(0, 0, 0, uint8_t(8 + rng() % 24)));
            }
            c.fillCircle(BLCircle(x + 0.5, y + 0.5, 0.55));
        }
    }
}

// ────────────────────────────────── main ─────────────────────────────────────

int main(int argc, char** argv) {
    const std::string outDir = argc > 1 ? argv[1] : "out";
    std::error_code ec;
    fs::create_directories(outDir, ec);
    if (ec) {
        std::fprintf(stderr, "cannot create output dir '%s': %s\n", outDir.c_str(), ec.message().c_str());
        return 1;
    }

    const std::vector<Dust> dust = makeDust();

    for (int f = 0; f < kTotalFrames; ++f) {
        const State s = stateAt(double(f) / kFps);
        BLImage img(kW * kScale, kH * kScale, BL_FORMAT_PRGB32);
        BLContext ctx(img);
        ctx.scale(double(kScale), double(kScale));
        drawScene(ctx, s, f, dust, true);
        ctx.end();

        char name[64];
        std::snprintf(name, sizeof(name), "frame_%04d.png", f);
        const fs::path path = fs::path(outDir) / name;
        if (img.writeToFile(path.string().c_str()) != BL_SUCCESS) {
            std::fprintf(stderr, "failed to write %s\n", path.string().c_str());
            return 2;
        }
        if (f % 60 == 0) std::printf("frame %3d / %d\n", f, kTotalFrames);
    }

    // 4x4 contact sheet of the 16 keyframes (review artifact)
    {
        BLImage sheet(4 * (kW / 2), 4 * (kH / 2), BL_FORMAT_PRGB32);
        BLContext sc(sheet);
        sc.clearAll();
        sc.setFillStyle(BLRgba32(8, 8, 10));
        sc.fillRect(BLRect(0, 0, 4 * (kW / 2), 4 * (kH / 2)));
        const auto& K = keyframes();
        for (int k = 0; k < kKeys; ++k) {
            sc.save();
            sc.clipToRect(BLRect(kW / 2 * (k % 4), kH / 2 * (k / 4), kW / 2, kH / 2));
            sc.translate(kW / 2 * (k % 4), kH / 2 * (k / 4));
            sc.scale(0.5, 0.5);
            drawScene(sc, K[k], k * kFps, dust, false);
            sc.restore();
        }
        sc.end();
        const fs::path sp = fs::path(outDir) / "_keyframes_sheet.png";
        if (sheet.writeToFile(sp.string().c_str()) != BL_SUCCESS)
            std::fprintf(stderr, "failed to write %s\n", sp.string().c_str());
    }

    std::printf("done: %d frames (%d s @ %d fps) -> %s\n", kTotalFrames,
                kTotalFrames / kFps, kFps, outDir.c_str());
    return 0;
}

}  // namespace chronon::geometric_glow

int main(int argc, char** argv) { return chronon::geometric_glow::main(argc, argv); }
