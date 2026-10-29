// ChrononTemplate — text_kinetic_showcase: 20+ modern typography recipes.
//
// Native C++ / Blend2D rebuild of the text-animation vocabulary from the two
// After Effects kinetic-typography tutorials (range-selector ramp sweeps with
// ease-high/ease-low, per-word animators with overshoot, skew-on-settle,
// squash-bounce full stop, path-option ring text, kinetic camera typography
// with a grid canvas), expressed the way the other youtuber_style scenes are:
// authored in a 3840x2160 logical space, rasterized at 1920x1080.
//
// Usage:
//   text_kinetic_showcase                  render every demo sequentially
//   text_kinetic_showcase --demo 5         render only demo 5 (1-based)
//   text_kinetic_showcase --out <dir>      alternate output root
//
// Frames land in <out>/<slug>/frame_0001.png ... (30 fps).

#include <blend2d.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <functional>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

constexpr int kW = 3840;
constexpr int kH = 2160;
constexpr double kPi = 3.14159265358979323846;
constexpr double kFitWidth = 3080.0;
constexpr int kFps = 30;

inline const std::string kFontsDir = "C:/Users/pater/Pyt/Chronon3d/assets/fonts";

using Color = BLRgba32;

const Color kInk(246, 249, 253);
const Color kGray(96, 104, 122);
const Color kAmber(255, 201, 60);
const Color kCyan(122, 214, 255);

// ---------------------------------------------------------------- easing ----

inline double clamp01(double x) { return std::clamp(x, 0.0, 1.0); }
inline double lerp(double a, double b, double t) { return a + (b - a) * t; }

inline double smoothstep(double e0, double e1, double x) {
    if (e1 <= e0) return x >= e1 ? 1.0 : 0.0;
    const double t = clamp01((x - e0) / (e1 - e0));
    return t * t * (3.0 - 2.0 * t);
}

inline double easeOutCubic(double t) { t = clamp01(t); return 1.0 - std::pow(1.0 - t, 3.0); }
inline double easeOutQuint(double t) { t = clamp01(t); return 1.0 - std::pow(1.0 - t, 5.0); }
inline double easeOutExpo(double t) { t = clamp01(t); return t >= 1.0 ? 1.0 : 1.0 - std::exp(-10.0 * t); }
inline double easeInCubic(double t) { t = clamp01(t); return t * t * t; }
inline double easeInOutCubic(double t) {
    t = clamp01(t);
    return t < 0.5 ? 4.0 * t * t * t : 1.0 - std::pow(-2.0 * t + 2.0, 3.0) / 2.0;
}

inline double easeOutBack(double x) {
    constexpr double c1 = 1.70158;
    constexpr double c3 = c1 + 1.0;
    const double p = clamp01(x);
    return 1.0 + c3 * std::pow(p - 1.0, 3.0) + c1 * std::pow(p - 1.0, 2.0);
}

inline double bounceOut(double x) {
    x = clamp01(x);
    constexpr double n1 = 7.5625;
    constexpr double d1 = 2.75;
    if (x < 1.0 / d1) return n1 * x * x;
    if (x < 2.0 / d1) return n1 * (x -= 1.5 / d1) * x + 0.75;
    if (x < 2.5 / d1) return n1 * (x -= 2.25 / d1) * x + 0.9375;
    return n1 * (x -= 2.625 / d1) * x + 0.984375;
}

inline double elasticOut(double x) {
    x = clamp01(x);
    if (x <= 0.0) return 0.0;
    if (x >= 1.0) return 1.0;
    const double c4 = 2.0 * kPi / 0.36;
    return std::pow(2.0, -9.0 * x) * std::sin((x * 9.7 - 0.72) * c4) + 1.0;
}

inline Color withAlpha(Color c, double a) {
    return BLRgba32(c.r(), c.g(), c.b(), uint8_t(std::lround(clamp01(a) * 255.0)));
}

inline Color mixColor(Color a, Color b, double t) {
    t = clamp01(t);
    return BLRgba32(uint8_t(std::lround(lerp(double(a.r()), double(b.r()), t))),
                    uint8_t(std::lround(lerp(double(a.g()), double(b.g()), t))),
                    uint8_t(std::lround(lerp(double(a.b()), double(b.b()), t))), 255);
}

inline uint64_t mix64(uint64_t x) {
    x += 0x9E3779B97F4A7C15ULL;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
    return x ^ (x >> 31);
}

// ----------------------------------------------------------------- fonts ----

inline double textWidth(const BLFont& font, const std::string& text) {
    BLGlyphBuffer gb;
    gb.setUtf8Text(text.c_str(), text.size());
    font.shape(gb);
    BLTextMetrics tm;
    font.getTextMetrics(gb, tm);
    return tm.advance.x;
}

std::vector<std::string> splitCodePoints(const std::string& text) {
    std::vector<std::string> out;
    for (size_t i = 0; i < text.size();) {
        const unsigned char lead = static_cast<unsigned char>(text[i]);
        size_t len = 1;
        if ((lead & 0xE0) == 0xC0) len = 2;
        else if ((lead & 0xF0) == 0xE0) len = 3;
        else if ((lead & 0xF8) == 0xF0) len = 4;
        len = std::min(len, text.size() - i);
        out.push_back(text.substr(i, len));
        i += len;
    }
    return out;
}

struct GlyphSlot {
    std::string cp;
    double adv = 0.0;
    double x = 0.0;
    double baseline = 0.0;
    double cx = 0.0;   // glyph anchor box center
    double cy = 0.0;
    int word = 0;
};

struct RunLayout {
    std::vector<GlyphSlot> slots;
    double width = 0.0;
    double fontSize = 0.0;
    double capHeight = 0.0;
    double centerX = 0.0;
    double centerY = 0.0;
};

struct PreparedRun {
    BLFont font;
    RunLayout run;
};

// Layout at a fixed size, horizontally centered on centerX, vertical center of
// the cap band at centerY.
PreparedRun makeRun(const BLFontFace& face, const std::string& text, double fontSize,
                    double centerX, double centerY, double tracking = 0.0) {
    BLFont font;
    font.createFromFace(face, float(fontSize));
    PreparedRun p;
    p.font = font;
    p.run.fontSize = fontSize;
    p.run.capHeight = font.metrics().capHeight;

    const double spaceAdv = textWidth(font, " ");
    std::vector<std::string> words;
    {
        std::string word;
        for (const auto& cp : splitCodePoints(text)) {
            if (cp == " " || cp == "\t") {
                if (!word.empty()) { words.push_back(word); word.clear(); }
            } else {
                word += cp;
            }
        }
        if (!word.empty()) words.push_back(word);
    }

    double cx = 0.0;
    int wi = 0;
    for (size_t w = 0; w < words.size(); ++w) {
        if (w > 0) {
            GlyphSlot s;
            s.cp = " "; s.adv = spaceAdv + tracking; s.x = cx; s.word = wi;
            p.run.slots.push_back(s);
            cx += s.adv;
        } else {
            wi = 0;
        }
        for (const auto& cp : splitCodePoints(words[w])) {
            GlyphSlot s;
            s.cp = cp;
            s.adv = textWidth(font, cp) + tracking;
            s.x = cx;
            s.cx = cx + s.adv * 0.5;
            s.word = wi;
            p.run.slots.push_back(s);
            cx += s.adv;
        }
        ++wi;
    }
    // word indices must restart per word streak: recompute sequentially
    p.run.width = cx;
    p.run.centerX = cx * 0.5;
    p.run.centerY = centerY;
    const double dx = centerX - p.run.centerX;
    for (auto& s : p.run.slots) {
        s.x += dx;
        s.cx += dx;
        s.baseline = centerY + p.run.capHeight * 0.5;
        s.cy = centerY;
        // word index at slot:
    }
    // recompute word indices across slots (spaces keep the following word idx)
    int acc = 0;
    bool inSpace = false;
    for (auto& s : p.run.slots) {
        if (s.cp == " ") { inSpace = true; continue; }
        if (inSpace) { ++acc; inSpace = false; }
        s.word = acc;
    }
    return p;
}

PreparedRun makeRunFitted(const BLFontFace& face, const std::string& text, double startSize,
                          double centerX, double centerY, double tracking = 0.0) {
    double size = startSize;
    PreparedRun p = makeRun(face, text, size, centerX, centerY, tracking);
    while (p.run.width > kFitWidth && size > 70.0) {
        size *= 0.94;
        p = makeRun(face, text, size, centerX, centerY, tracking);
    }
    return p;
}

// ---------------------------------------------------------------- drawing ---

void drawGlyph(BLContext& ctx, const BLFont& font, const GlyphSlot& s,
               double dx, double dy, double scaleX, double scaleY, double rot,
               double skew, Color color) {
    if (s.cp == " " || color.a() == 0) return;
    ctx.save();
    ctx.translate(s.cx + dx, s.cy + dy);
    if (rot != 0.0) ctx.rotate(rot);
    if (skew != 0.0) ctx.postSkew(skew, 0.0);
    if (scaleX != 1.0 || scaleY != 1.0) ctx.scale(scaleX, scaleY);
    ctx.translate(-s.cx, -s.cy);
    ctx.setFillStyle(color);
    ctx.fillUtf8Text(BLPoint(s.x, s.baseline), font, s.cp.c_str(), s.cp.size());
    ctx.restore();
}

void drawGlyphRaw(BLContext& ctx, const BLFont& font, double x, double baseline,
                  const std::string& cp, Color color) {
    if (cp == " " || color.a() == 0) return;
    ctx.setFillStyle(color);
    ctx.fillUtf8Text(BLPoint(x, baseline), font, cp.c_str(), cp.size());
}

void darkBackground(BLContext& ctx) {
    BLGradient bg(BLLinearGradientValues(0.0, 0.0, 0.0, double(kH)));
    bg.addStop(0.0, BLRgba32(13, 16, 24));
    bg.addStop(0.55, BLRgba32(8, 10, 15));
    bg.addStop(1.0, BLRgba32(4, 5, 8));
    ctx.setFillStyle(bg);
    ctx.fillRect(BLRect(0, 0, kW, kH));
}

void darkVignette(BLContext& ctx) {
    BLGradient vignette(BLRadialGradientValues(kW * 0.5, kH * 0.5, kW * 0.5, kH * 0.5,
                                               kW * 0.72, kW * 0.28));
    vignette.addStop(0.0, BLRgba32(0, 0, 0, 0));
    vignette.addStop(0.6, BLRgba32(0, 0, 0, 38));
    vignette.addStop(1.0, BLRgba32(0, 0, 0, 190));
    ctx.setFillStyle(vignette);
    ctx.fillRect(BLRect(0, 0, kW, kH));
}

// --------------------------------------------------------------- demo spec --

enum class BgStyle { Dark, Light };

struct DemoSpec {
    const char* slug = "";
    const char* title = "";
    const char* text = "";
    double seconds = 2.5;
    double fontSize = 320.0;
    double revealStart = 0.08;   // seconds at demo-local scale (t goes 0..1*S)
    double revealSpan = 0.50;
    double charDur = 0.40;
    BgStyle bg = BgStyle::Dark;
    Color accent = kAmber;
    double glow = 0.62;          // bloom strength (0 disables, light scenes)
    int kind = 0;                // 0 = per-char/word painter <id>, see switch
};

enum class DemoId {
    RampUp = 0, WordPop, SkewStop, BarHighlight, DotBounce, FlipIn, FadeSlideWords,
    BlurIn, RotateWheel, DropBounce, Tracking, ColorSweep, WaveBreathe, GlitchRgb,
    SplitReveal, MaskWipe, SlamZoom, KineticCamera, CirclePath, CaretTypewriter,
    Count,
};

const int kTotalDemos = int(DemoId::Count);

DemoSpec specFor(DemoId id) {
    DemoSpec s;
    s.accent = kAmber;
    switch (id) {
        case DemoId::RampUp:
            s.slug = "01_ramp_up_reveal"; s.title = "RAMP UP REVEAL";
            s.text = "RIDE THE RAMP"; s.fontSize = 340; s.glow = 0.80;
            s.revealStart = 0.06; s.revealSpan = 0.42; s.charDur = 0.38; s.seconds = 3.0;
            break;
        case DemoId::WordPop:
            s.slug = "02_word_pop_overshoot"; s.title = "WORD POP / OVERSHOOT";
            s.text = "POP GOES TYPE"; s.fontSize = 330;
            s.seconds = 2.6;
            break;
        case DemoId::SkewStop:
            s.slug = "03_skew_on_stop"; s.title = "SKEW ON STOP";
            s.text = "AND THEN IT STOPS"; s.fontSize = 300; s.seconds = 2.8;
            break;
        case DemoId::BarHighlight:
            s.slug = "04_bar_highlight_wipe"; s.title = "BAR HIGHLIGHT WIPE";
            s.text = "MARK MY WORDS"; s.fontSize = 310; s.seconds = 2.9;
            break;
        case DemoId::DotBounce:
            s.slug = "05_dot_bounce_impact"; s.title = "DOT BOUNCE IMPACT";
            s.text = "STILL FALLING"; s.fontSize = 330; s.seconds = 3.2;
            break;
        case DemoId::FlipIn:
            s.slug = "06_flip_page_in"; s.title = "FLIP PAGE IN";
            s.text = "PAGE BY PAGE"; s.fontSize = 330;
            s.revealStart = 0.06; s.revealSpan = 0.48; s.charDur = 0.42; s.seconds = 2.5;
            break;
        case DemoId::FadeSlideWords:
            s.slug = "07_fade_slide_words"; s.title = "FADE SLIDE WORDS";
            s.text = "GO FAST NOW"; s.fontSize = 340;
            s.seconds = 2.5;
            break;
        case DemoId::BlurIn:
            s.slug = "08_blur_focus_in"; s.title = "BLUR FOCUS IN";
            s.text = "COMING INTO FOCUS"; s.fontSize = 300;
            s.revealStart = 0.10; s.revealSpan = 0.26; s.charDur = 0.55; s.seconds = 2.8;
            break;
        case DemoId::RotateWheel:
            s.slug = "09_rotational_spin"; s.title = "ROTATIONAL SPIN";
            s.text = "SPIN THE CYCLE"; s.fontSize = 320;
            s.revealStart = 0.04; s.revealSpan = 0.55; s.charDur = 0.60; s.seconds = 2.6;
            break;
        case DemoId::DropBounce:
            s.slug = "10_gravity_drop"; s.title = "GRAVITY DROP";
            s.text = "GRAVITY DOES WORK"; s.fontSize = 300;
            s.revealStart = 0.04; s.revealSpan = 0.55; s.charDur = 0.80; s.seconds = 3.0;
            break;
        case DemoId::Tracking:
            s.slug = "11_tracking_expand"; s.title = "TRACKING EXPAND";
            s.text = "WIDER AND WIDER"; s.fontSize = 250; s.seconds = 2.9;
            break;
        case DemoId::ColorSweep:
            s.slug = "12_color_sweep_underline"; s.title = "COLOR SWEEP + RULE";
            s.text = "GOOD CONTRAST"; s.fontSize = 330;
            s.revealStart = 0.08; s.revealSpan = 0.40; s.charDur = 0.34; s.seconds = 2.9;
            break;
        case DemoId::WaveBreathe:
            s.slug = "13_wave_breathe"; s.title = "WAVE BREATHE";
            s.text = "RIDERS ON THE WAVE"; s.fontSize = 300; s.seconds = 3.4; s.glow = 0.72;
            break;
        case DemoId::GlitchRgb:
            s.slug = "14_glitch_rgb_split"; s.title = "GLITCH RGB SPLIT";
            s.text = "SIGNAL INTERRUPTED"; s.fontSize = 300; s.seconds = 2.8;
            break;
        case DemoId::SplitReveal:
            s.slug = "15_split_reveal"; s.title = "SPLIT REVEAL";
            s.text = "MEET IN THE MIDDLE"; s.fontSize = 310; s.seconds = 2.6;
            break;
        case DemoId::MaskWipe:
            s.slug = "16_masked_wipe"; s.title = "MASKED WIPE";
            s.text = "ON THE RECORD"; s.fontSize = 330; s.seconds = 2.8;
            break;
        case DemoId::SlamZoom:
            s.slug = "17_expo_slam_zoom"; s.title = "EXPO SLAM ZOOM";
            s.text = "SLAM IT HARD"; s.fontSize = 340; s.glow = 0.85;
            s.revealStart = 0.05; s.revealSpan = 0.30; s.charDur = 0.50; s.seconds = 2.6;
            break;
        case DemoId::KineticCamera:
            s.slug = "18_kinetic_camera_grid"; s.title = "KINETIC CAMERA GRID";
            s.text = ""; s.seconds = 4.0; s.bg = BgStyle::Light; s.kind = 2; s.glow = 0.0;
            break;
        case DemoId::CirclePath:
            s.slug = "19_circle_path_rotate"; s.title = "CIRCLE PATH ROTATE";
            s.text = ""; s.seconds = 3.4; s.kind = 3; s.glow = 0.78;
            break;
        case DemoId::CaretTypewriter:
            s.slug = "20_typewriter_caret"; s.title = "TYPEWRITER CARET";
            s.text = "TYPE IT OUT"; s.fontSize = 330; s.seconds = 2.7;
            break;
        default:
            break;
    }
    return s;
}

// ------------------------------------------------------------ shared bits ---

struct Chrome {
    BLFont label;
    void draw(BLContext& ctx, int index, const std::string& title, BgStyle bg) const {
        const bool light = bg == BgStyle::Light;
        const Color base = light ? BLRgba32(16, 20, 26) : BLRgba32(255, 255, 255);
        char ord[16];
        std::snprintf(ord, sizeof(ord), "%02d", index);
        const std::string left = std::string("CHRONONTEMPLATE \xC2\xB7 TEXT SHOWCASE \xC2\xB7 ") + ord + " / 20";

        ctx.setFillStyle(withAlpha(base, 0.46));
        ctx.fillUtf8Text(BLPoint(kW * 0.055, 150.0), label, left.c_str(), left.size());

        const double w = textWidth(label, title);
        ctx.setFillStyle(withAlpha(base, 0.34));
        ctx.fillUtf8Text(BLPoint(kW * 0.945 - w, 150.0), label, title.c_str(), title.size());

        ctx.setFillStyle(withAlpha(base, 0.18));
        ctx.fillRect(BLRect(kW * 0.055, 178.0, kW * 0.89, 3.0));
    }
};

struct SlotCtx {
    const PreparedRun* p = nullptr;
    const DemoSpec* spec = nullptr;
    double t = 0.0;
    int count = 0;
};

inline double slotStart(const SlotCtx& c, int slot) {
    const int n = std::max(1, c.count);
    if (n <= 1) return c.spec->revealStart;
    return c.spec->revealStart + c.spec->revealSpan * (double(slot) / double(n - 1));
}

// ================================================================= PAINTERS ==

void paintRampUp(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    const double rise = 640.0;
    // entry sweep, then the whole line drifts out right like the AE null exit.
    const double exitU = clamp01((t - 0.78) / 0.22);
    const double exitDx = easeInCubic(exitU) * 1500.0;
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i))) / C.spec->charDur);
        const double e = easeOutCubic(local);
        drawGlyph(ctx, p.font, sl, exitDx, (1.0 - e) * rise, 1.0, 1.0, 0.0, 0.0,
                  withAlpha(kInk, e));
    }
}

void paintWordPop(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    const int nw = std::max(1, [&] {
        int m = 0;
        for (const auto& sl : p.run.slots) m = std::max(m, sl.word + 1);
        return m;
    }());
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double wStart = C.spec->revealStart +
            C.spec->revealSpan * (double(sl.word) / double(std::max(1, nw - 1)));
        const double u = clamp01((t - wStart) / 0.45);
        if (u <= 0.0) continue;
        const double scale = lerp(0.40, 1.0, easeOutBack(u));
        drawGlyph(ctx, p.font, sl, 0.0, (1.0 - clamp01(u * 1.6)) * 36.0,
                  scale, scale, 0.0, 0.0, withAlpha(kInk, clamp01(u * 2.2)));
    }
}

void paintSkewStop(BLContext& ctx, double t, const SlotCtx& C, Chrome& chrome) {
    const PreparedRun& p = *C.p;
    const double slideStart = 0.06;
    const double slideEnd = 0.42;
    const double u = clamp01((t - slideStart) / (slideEnd - slideStart));
    const double xoff = -(1.0 - easeOutExpo(u)) * 1500.0;

    double env = 0.0;
    if (t >= slideStart && t < slideEnd) env = 1.0 - 0.22 * u;
    else if (t >= slideEnd) env = std::exp(-4.6 * (t - slideEnd)) * 0.80 + 0.02;
    const double skew = -0.42 * env;
    const double alpha = smoothstep(0.02, 0.10, t);

    for (const auto& sl : p.run.slots) {
        drawGlyph(ctx, p.font, sl, xoff, 0.0, 1.0, 1.0, 0.0, skew,
                  withAlpha(kInk, alpha));
    }

    // amber runway brake bar under the baseline.
    const double barU = clamp01((t - slideEnd + 0.05) / 0.32);
    if (barU > 0.0) {
        const double w = p.run.width * easeOutCubic(barU);
        ctx.setFillStyle(C.spec->accent);
        ctx.fillRect(BLRect(p.run.centerX - p.run.width * 0.5, p.run.centerY + p.run.capHeight * 0.78,
                            w, 16.0));
    }
    (void)chrome;
}

void paintBarHighlight(BLContext& ctx, double t, const SlotCtx& C, Chrome& chrome) {
    const PreparedRun& p = *C.p;
    const double wipe = easeOutCubic(clamp01((t - 0.12) / 0.55));
    const double barW = p.run.width * wipe * 1.06;
    const double barX = p.run.centerX - p.run.width * 0.53;
    const double barH = p.run.fontSize * 0.92;

    // fast gray reveal first
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i)) * 0.55) / 0.28);
        drawGlyph(ctx, p.font, sl, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0,
                  withAlpha(kGray, clamp01(local * 2.0)));
    }
    if (barW > 1.0) {
        ctx.setFillStyle(C.spec->accent);
        ctx.fillRect(BLRect(barX, p.run.centerY - barH * 0.46, barW, barH));
        // ink letters where the bar already passed, stagger left->right
        for (size_t i = 0; i < p.run.slots.size(); ++i) {
            const GlyphSlot& sl = p.run.slots[i];
            const double covered = smoothstep(sl.cx, sl.cx + sl.adv, barX + barW) ;
            (void)covered;
            if (sl.cx + sl.adv * 0.5 <= barX + barW) {
                const double local = clamp01((t - slotStart(C, int(i)) * 0.55) / 0.28);
                drawGlyph(ctx, p.font, sl, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0,
                          withAlpha(BLRgba32(40, 26, 8), clamp01(local * 2.0)));
            }
        }
    }
    (void)chrome;
}

void paintFlipIn(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i))) / C.spec->charDur);
        const double e = easeOutBack(local);
        const double foreshort = std::abs(std::cos((1.0 - clamp01(local)) * kPi * 0.5)) * 0.9 + 0.1;
        const double sx = std::max(0.06, e) * foreshort;
        drawGlyph(ctx, p.font, sl, 0.0, 0.0, sx, 0.94 + 0.06 * e, 0.0, 0.0,
                  withAlpha(kInk, clamp01(local * 2.6)));
    }
}

void paintFadeSlideWords(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    const int nw = std::max(1, [&] {
        int m = 0;
        for (const auto& sl : p.run.slots) m = std::max(m, sl.word + 1);
        return m; }());
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double wStart = C.spec->revealStart +
            C.spec->revealSpan * (double(sl.word) / double(std::max(1, nw - 1)));
        const double u = clamp01((t - wStart) / 0.45);
        const double e = easeOutQuint(u);
        const double dir = (sl.word % 2 == 0) ? -1.0 : 1.0;
        drawGlyph(ctx, p.font, sl, dir * (1.0 - e) * 520.0, 0.0, 1.0, 1.0, 0.0, 0.0,
                  withAlpha(kInk, smoothstep(0.0, 0.6, u)));
    }
}

void paintBlurIn(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i))) / C.spec->charDur);
        if (local <= 0.0) continue;
        const double defocus = 1.0 - easeOutCubic(local);
        if (defocus > 0.01) {
            const double radius = 54.0 * defocus;
            for (int k = 0; k < 10; ++k) {
                const double ang = kPi * 2.0 * (double(k) / 10.0) + double(i) * 0.7;
                drawGlyphRaw(ctx, p.font,
                             sl.x + std::cos(ang) * radius,
                             sl.baseline + std::sin(ang) * radius,
                             sl.cp, withAlpha(kCyan, 0.16 * defocus));
            }
        }
        drawGlyph(ctx, p.font, sl, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0,
                  withAlpha(kInk, clamp01(local * 1.5)));
    }
}

void paintRotateWheel(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i))) / C.spec->charDur);
        const double e = elasticOut(local);
        drawGlyph(ctx, p.font, sl, 0.0, 0.0,
                  0.35 + 0.65 * clamp01(local * 2.2), 0.35 + 0.65 * clamp01(local * 2.2),
                  -(1.0 - e) * 2.4, 0.0, withAlpha(kInk, clamp01(local * 3.2)));
    }
}

void paintDropBounce(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i))) / C.spec->charDur);
        const double e = bounceOut(local);
        const double impact = clamp01(1.0 - std::abs(e - 0.0) * 60.0) * 0.0;
        (void)impact;
        drawGlyph(ctx, p.font, sl, 0.0, -(1.0 - e) * 780.0,
                  1.0, 1.0, 0.0, 0.0, withAlpha(kInk, clamp01(local * 5.0)));
    }
}

void paintTracking(BLContext& ctx, double t, const SlotCtx& C, const BLFontFace& bold) {
    const DemoSpec& spec = *C.spec;
    // re-layout each frame with expanding tracking; alpha pours out from center.
    const double tracking = (1.0 - easeOutCubic(clamp01((t - 0.06) / 0.85))) * spec.fontSize * 0.85;
    PreparedRun p = makeRun(bold, spec.text, spec.fontSize, kW * 0.5, kH * 0.545, tracking);
    const int n = int(p.run.slots.size());
    for (int i = 0; i < n; ++i) {
        const GlyphSlot& sl = p.run.slots[size_t(i)];
        const double fromCenter = std::abs(double(i) - double(n - 1) * 0.5) / double(std::max(1, n - 1));
        const double local = clamp01((t - (0.05 + 0.55 * fromCenter)) / 0.35);
        if (local <= 0.0) continue;
        drawGlyph(ctx, p.font, sl, 0.0, (1.0 - easeOutCubic(local)) * 40.0,
                  1.0, 1.0, 0.0, 0.0, withAlpha(kInk, local));
    }
}

void paintColorSweep(BLContext& ctx, double t, const SlotCtx& C, Chrome& chrome) {
    const PreparedRun& p = *C.p;
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i))) / C.spec->charDur);
        Color c = mixColor(BLRgba32(84, 92, 108), kInk, easeOutCubic(local));
        // hot accent edge that travels with the sweep
        if (local > 0.35 && local < 0.95) {
            c = mixColor(c, C.spec->accent, std::sin((local - 0.35) / 0.6 * kPi) * 0.65);
        }
        drawGlyph(ctx, p.font, sl, 0.0, (1.0 - easeOutCubic(local)) * 30.0,
                  1.0, 1.0, 0.0, 0.0, c);
    }
    const double ruleU = clamp01((t - 0.62) / 0.30);
    if (ruleU > 0.0) {
        const double w = p.run.width * 1.03 * easeOutCubic(ruleU);
        ctx.setFillStyle(C.spec->accent);
        ctx.fillRect(BLRect(p.run.centerX - p.run.width * 0.515,
                            p.run.centerY + p.run.capHeight * 0.80, w, 12.0));
    }
    (void)chrome;
}

void paintWaveBreathe(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    const double in = smoothstep(0.0, 0.22, t);
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double phase = t * kPi * 1.9 - double(i) * 0.42;
        const double dy = std::sin(phase) * 70.0 * in;
        const double rot = std::cos(phase) * 0.10 * in;
        Color c = kInk;
        if (std::sin(phase) > 0.55) {
            c = mixColor(c, kCyan, smoothstep(0.55, 1.0, std::sin(phase)) * 0.75);
        }
        drawGlyph(ctx, p.font, sl, 0.0, dy, 1.0, 1.0, rot, 0.0, withAlpha(c, in));
    }
}

void paintGlitchRgb(BLContext& ctx, double t, const SlotCtx& C, Chrome& chrome) {
    const PreparedRun& p = *C.p;
    const bool burst = std::fmod(t * 11.0, 1.0) < 0.14;
    const double jitter = burst ? ((double(mix64(uint64_t(std::llround(t * 137.0)))) / double(UINT32_MAX)) - 0.5) * 44.0 : 0.0;

    if (burst) {
        const double dxs[3] = {-26.0, 0.0, 26.0};
        const Color cols[3] = {BLRgba32(255, 66, 96), BLRgba32(88, 255, 148), BLRgba32(90, 140, 255)};
        for (int c = 0; c < 3; ++c) {
            for (size_t i = 0; i < p.run.slots.size(); ++i) {
                const GlyphSlot& sl = p.run.slots[i];
                const double local = clamp01((t - slotStart(C, int(i))) / 0.25);
                drawGlyph(ctx, p.font, sl, dxs[c] + jitter * 0.5, 0.0, 1.0, 1.0, 0.0, 0.0,
                          withAlpha(cols[c], 0.70 * clamp01(local * 3.0)));
            }
        }
        for (int k = 0; k < 5; ++k) {
            const double y = kH * (0.27 + 0.10 * double(k)) +
                             (double(mix64(uint64_t(k + 3) ^ uint64_t(std::llround(t * 91.0)))) / double(UINT32_MAX)) * 90.0;
            ctx.setFillStyle(withAlpha(BLRgba32(4, 5, 8), 0.55));
            ctx.fillRect(BLRect(0.0, y, double(kW), 12.0 + 22.0 * double(mix64(uint64_t(k) ^ uint64_t(t * 7)) % 2)));
        }
    }
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i))) / 0.25);
        drawGlyph(ctx, p.font, sl, jitter * 0.18, 0.0, 1.0, 1.0, 0.0, 0.0,
                  withAlpha(kInk, clamp01(local * 2.4)));
    }
    (void)chrome;
}

void paintSplitReveal(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i))) / C.spec->charDur);
        const double e = easeOutQuint(local);
        const double dir = (double(i) + 0.5 < double(p.run.slots.size()) * 0.5) ? -1.0 : 1.0;
        drawGlyph(ctx, p.font, sl, dir * (1.0 - e) * 680.0, 0.0, 1.0, 1.0, 0.0, 0.0,
                  withAlpha(kInk, smoothstep(0.0, 0.5, local)));
    }
}

void paintMaskWipe(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    const double wipe = easeInOutCubic(clamp01((t - 0.10) / 0.80));
    const double cx0 = kW * 0.05 + (kW * 0.90) * wipe;
    ctx.save();
    ctx.clipToRect(BLRect(0.0, 0.0, cx0, double(kH)));
    for (const auto& sl : p.run.slots) {
        drawGlyph(ctx, p.font, sl, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, kInk);
    }
    ctx.restore();
    if (wipe > 0.001 && wipe < 0.999) {
        ctx.setFillStyle(BLRgba32(255, 201, 60, 235));
        ctx.fillRect(BLRect(cx0 - 3.0, p.run.centerY - p.run.fontSize * 0.62, 8.0, p.run.fontSize * 1.24));
    }
}

void paintSlamZoom(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i))) / C.spec->charDur);
        if (local <= 0.0) continue;
        const double e = easeOutExpo(local);
        const double scale = lerp(2.6, 1.0, e);
        if (local > 0.0 && local < 0.12) {
            // hot flash right at impact
            drawGlyph(ctx, p.font, sl, 0.0, 0.0, scale, scale, 0.0, 0.0,
                      withAlpha(C.spec->accent, (0.12 - local) * 2.2));
        }
        drawGlyph(ctx, p.font, sl, 0.0, 0.0, scale, scale, 0.0, 0.0,
                  withAlpha(kInk, clamp01(local * 2.6)));
    }
}

void paintCaretTypewriter(BLContext& ctx, double t, const SlotCtx& C, Chrome& chrome) {
    const PreparedRun& p = *C.p;
    const int n = int(p.run.slots.size());
    const double typeSpan = 1.05;
    double caretX = p.run.slots.front().x;
    double caretBaseline = p.run.slots.front().baseline;
    bool any = false;
    for (int i = 0; i < n; ++i) {
        const GlyphSlot& sl = p.run.slots[size_t(i)];
        const double lTime = C.spec->revealStart + typeSpan * (double(i) / double(std::max(1, n - 1)));
        if (t < lTime) break;
        const double settle = smoothstep(lTime, lTime + 0.12, t);
        const double scale = 1.0 + 0.30 * (1.0 - settle);
        drawGlyph(ctx, p.font, sl, 0.0, 0.0, scale, scale, 0.0, 0.0, kInk);
        caretX = sl.x + sl.adv;
        caretBaseline = sl.baseline;
        any = true;
    }
    if (!any) {
        caretX = p.run.slots.front().x;
        caretBaseline = p.run.slots.front().baseline;
    }
    const double origenX = p.run.centerX - p.run.width * 0.5;
    const double edge = p.run.centerX + p.run.width * 0.5;
    const double baseX = p.run.centerX + (caretX - (p.run.centerX - p.run.width * 0.5));
    (void)origenX; (void)edge;
    // block caret blinks fast while typing, holds, fades
    const bool typing = t < C.spec->revealStart + typeSpan;
    const bool blinkOn = !typing || (std::fmod(t, 0.24) < 0.14);
    const double caretFade = 1.0 - smoothstep(2.15, 2.45, t);
    if (blinkOn && caretFade > 0.01) {
        const double top = caretBaseline - p.run.capHeight * 1.02;
        const double bottom = caretBaseline + p.run.fontSize * 0.16;
        const double cw = std::max(6.0, p.run.fontSize * 0.045);
        ctx.setFillStyle(withAlpha(kCyan, 0.15 * caretFade));
        ctx.fillRect(BLRect(baseX - cw * 1.4, top - 8.0, cw * 2.8, (bottom - top) + 16.0));
        ctx.setFillStyle(withAlpha(kCyan, 0.92 * caretFade));
        ctx.fillRect(BLRect(baseX, top, cw, bottom - top));
    }
    (void)chrome;
}

// ------------------------------------------------------------ bespoke fns ---

void paintDotBounce(BLContext& ctx, double t, const SlotCtx& C) {
    const PreparedRun& p = *C.p;
    // text pops quickly
    for (size_t i = 0; i < p.run.slots.size(); ++i) {
        const GlyphSlot& sl = p.run.slots[i];
        const double local = clamp01((t - slotStart(C, int(i)) * 0.6) / 0.28);
        drawGlyph(ctx, p.font, sl, 0.0, (1.0 - easeOutCubic(local)) * 24.0, 1.0, 1.0, 0.0, 0.0,
                  withAlpha(kInk, clamp01(local * 2.2)));
    }
    // the amber full stop with squash + shadow + ripples (VC-reflect homage)
    const double pStart = 0.34;
    const double pSpan = 0.72;
    const double prog = clamp01((t - pStart) / pSpan);
    if (prog <= 0.0) return;

    const double maxH = kH * 0.33;
    const double r = p.run.fontSize * 0.115;
    const double rightEdge = p.run.centerX + p.run.width * 0.5;
    const double dotX = rightEdge + r * 3.0;
    const double groundY = p.run.centerY + p.run.capHeight * 0.5 - r;

    const double h = (1.0 - bounceOut(prog)) * maxH;
    const double hNext = (1.0 - bounceOut(clamp01(prog + 0.004))) * maxH;
    const double speed = std::abs(h - hNext);
    double squash = clamp01(speed * 30.0);
    if (h <= 1.0 && prog < 1.0) squash = std::max(squash, 0.75);
    const double sy = 1.0 - 0.55 * squash;
    const double sx = 1.0 + 0.34 * squash;
    const double cy = groundY - h + r * (sy - 1.0);

    if (h > 0.5) {
        const double shadowA = 0.36 - 0.30 * (h / maxH);
        ctx.setFillStyle(withAlpha(BLRgba32(0, 0, 0), shadowA));
        ctx.fillEllipse(dotX, groundY + r * 0.55, r * (1.10 + 1.6 * (h / maxH)), r * 0.28);
    }

    static const double impacts[3] = {2.75 / 2.75, 2.0 / 2.75, 2.5 / 2.75};
    (void)impacts;
    // impact ripples at each ground contact
    const double kImpacts[3] = {1.0 / 2.75, 2.0 / 2.75, 2.5 / 2.75};
    for (double ip : kImpacts) {
        const double it = pStart + ip * pSpan;
        if (t > it && t < it + 0.55) {
            const double age = (t - it) / 0.55;
            ctx.setStrokeStyle(withAlpha(C.spec->accent, (1.0 - age) * 0.55));
            ctx.setStrokeWidth(9.0 * (1.0 - age) + 2.0);
            ctx.strokeEllipse(dotX, groundY, double(r + age * p.run.fontSize * 2.4),
                              double((r + age * p.run.fontSize * 2.4) * 0.30));
        }
    }

    ctx.save();
    ctx.translate(dotX, cy);
    ctx.scale(sx, sy);
    ctx.setFillStyle(C.spec->accent);
    ctx.fillEllipse(0.0, 0.0, r, r);
    ctx.restore();
}

struct KinWord {
    PreparedRun run;
    Color color;
    double rotDeg = 0.0;
};

void paintKineticCamera(BLContext& ctx, double t, const std::vector<KinWord>& words) {
    struct Anchor { double x, y, zoom, rotDeg; };
    static const Anchor anchors[5] = {
        {1500.0, 800.0, 1.40, -3.0},
        {700.0, 1700.0, 1.52, 5.0},
        {3050.0, 1800.0, 1.44, -5.0},
        {3700.0, 2650.0, 1.46, 4.0},
        {2400.0, 1600.0, 0.58, 0.0},
    };
    static const double segTimes[5] = {0.05, 0.95, 1.85, 2.75, 3.55};

    int seg = 0;
    double u = 0.0;
    for (int i = 0; i < 4; ++i) {
        if (t >= segTimes[i]) {
            seg = i;
            if (i == 3) u = clamp01((t - segTimes[3]) / (3.9 - segTimes[3]));
            else u = clamp01((t - segTimes[i]) / (segTimes[i + 1] - segTimes[i]));
        }
    }
    const double e = easeInOutCubic(u);
    const double camX = lerp(anchors[seg].x, anchors[seg + 1].x, e);
    const double camY = lerp(anchors[seg].y, anchors[seg + 1].y, e);
    const double camZ = lerp(anchors[seg].zoom, anchors[seg + 1].zoom, e);
    const double camR = lerp(anchors[seg].rotDeg, anchors[seg + 1].rotDeg, e) * kPi / 180.0;

    ctx.save();
    ctx.translate(kW * 0.5, kH * 0.5);
    ctx.rotate(camR);
    ctx.scale(camZ);
    ctx.translate(-camX, -camY);

    // paper + grid canvas, larger than the visible frame on every stop.
    ctx.setFillStyle(BLRgba32(250, 250, 247));
    ctx.fillRect(BLRect(-1600.0, -1100.0, 8000.0, 5600.0));
    ctx.setFillStyle(BLRgba32(20, 26, 34, 32));
    for (double gx = -1600.0; gx <= 6400.0; gx += 300.0)
        ctx.fillRect(BLRect(gx - 1.5, -1100.0, 3.0, 5600.0));
    for (double gy = -1100.0; gy <= 4500.0; gy += 300.0)
        ctx.fillRect(BLRect(-1600.0, gy - 1.5, 8000.0, 3.0));

    static const double popStart[6] = {0.10, 3.62, 1.02, 1.98, 3.80, 2.90};
    for (size_t w = 0; w < words.size(); ++w) {
        const double pu = clamp01((t - popStart[w]) / 0.34);
        if (pu <= 0.0) continue;
        const KinWord& kw = words[w];
        const PreparedRun& p = kw.run;
        ctx.save();
        ctx.translate(p.run.centerX, p.run.centerY);
        ctx.rotate(kw.rotDeg * kPi / 180.0);
        const double scale = lerp(0.38, 1.0, easeOutBack(pu));
        ctx.scale(scale);
        ctx.translate(-p.run.centerX, -p.run.centerY);
        for (const auto& sl : p.run.slots) {
            drawGlyph(ctx, p.font, sl, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0,
                      withAlpha(kw.color, clamp01(pu * 2.2)));
        }
        ctx.restore();
    }
    ctx.restore();
}

void paintCirclePath(BLContext& ctx, double t, const BLFontFace& bold, const DemoSpec& spec) {
    const double cx = kW * 0.5;
    const double cy = kH * 0.5;
    const double R = 760.0;

    const std::string phrase = "KINETIC TEXT ON A CIRCLE PATH \xE2\x80\xA2 READY TO GO \xE2\x80\xA2";
    const std::vector<std::string> cps = splitCodePoints(phrase);
    const int N = int(cps.size());
    const double spin0 = 2.5;
    const double sweep = -1.30 * 2.0 * kPi * easeOutQuint(clamp01(t / 2.05));
    const double drift = clamp01(std::max(0.0, t - 2.05)) * 0.09;

    BLFont ringFont;
    ringFont.createFromFace(bold, 100.0f);
    for (int i = 0; i < N; ++i) {
        const double theta = spin0 + sweep + drift + (double(i) / double(N)) * 2.0 * kPi;
        const double x = cx + R * std::cos(theta);
        const double y = cy + R * std::sin(theta);
        const double rot = theta + kPi * 0.5;
        const double alpha = clamp01(t * 2.8 - (double(i) / double(N)) * 0.9) * 0.95;
        if (alpha <= 0.01 || cps[i] == " " || cps[i] == "\xE2\x80\xA2" ) {
            if (cps[i] == "\xE2\x80\xA2") {
                // dots stay, they anchor the ring
            }
        }
        if (alpha <= 0.01 || cps[i] == " ") continue;
        GlyphSlot s;
        s.cp = cps[i]; s.x = x; s.baseline = y; s.cx = x; s.cy = y; s.adv = 1.0;
        drawGlyph(ctx, ringFont, s, 0.0, 0.0, 1.0, 1.0, rot, 0.0,
                  withAlpha(kInk, alpha));
    }

    const double popU = clamp01((t - 0.35) / 0.45);
    if (popU > 0.0) {
        const double scale = lerp(0.30, 1.0, easeOutBack(popU));
        ctx.save();
        ctx.translate(cx, cy);
        ctx.scale(scale);
        ctx.translate(-cx, -cy);
        ctx.setFillStyle(BLRgba32(8, 10, 14));
        ctx.fillRect(BLRect(cx - 880.0 + 26.0, cy - 240.0 + 26.0, 1760.0, 480.0));
        ctx.setFillStyle(spec.accent);
        ctx.fillRect(BLRect(cx - 880.0, cy - 240.0, 1760.0, 480.0));
        const PreparedRun title = makeRun(bold, "CIRCLE PATH", 250.0, cx, cy, 0.0);
        for (const auto& sl : title.run.slots) {
            drawGlyph(ctx, title.font, sl, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, BLRgba32(26, 20, 8));
        }
        ctx.restore();
    }
}

// True-glow bloom: reads the finished frame, thresholds+blurs the bright
// text into a small RGBA buffer and composites it back additively (PLUS comp
// op) — the real After Effects Glow instead of stacked glyph rings.
void applyBloom(BLContext& ctx, const BLImage& frame, double strength) {
    if (strength <= 0.001) return;
    constexpr int bw = 480;
    constexpr int bh = 270;
    constexpr int kThreshold = 70;
    constexpr float kSpread = 255.0f / 185.0f;

    BLImage small(bw, bh, BL_FORMAT_PRGB32);
    if (BLImage::scale(small, frame, BLSizeI(bw, bh), BL_IMAGE_SCALE_FILTER_BILINEAR) != BL_SUCCESS)
        return;

    BLImageData sd;
    if (small.makeMutable(&sd) != BL_SUCCESS) return;
    uint32_t* px = static_cast<uint32_t*>(sd.pixelData);
    const int strideWords = int(sd.stride / 4);

    // bright -> additive halo; rgb carries the glow, alpha 0 so PLUS never
    // tints the matte.
    for (int y = 0; y < bh; ++y) {
        uint32_t* row = px + y * strideWords;
        for (int x = 0; x < bw; ++x) {
            const uint32_t c = row[x];
            const int r = int(c >> 16) & 255;
            const int g = int(c >> 8) & 255;
            const int b = int(c) & 255;
            const int m = std::max(r, std::max(g, b));
            if (m <= kThreshold) { row[x] = 0; continue; }
            const float k = std::min(1.0f, (float(m - kThreshold) * kSpread / 255.0f)) * float(strength);
            const uint32_t rr = uint32_t(std::min(255.0f, float(r) * 0.62f * k * 255.0f)) & 255;
            const uint32_t gg = uint32_t(std::min(255.0f, float(g) * 0.62f * k * 255.0f)) & 255;
            const uint32_t bb = uint32_t(std::min(255.0f, float(b) * 0.62f * k * 255.0f)) & 255;
            row[x] = (rr << 16) | (gg << 8) | bb;
        }
    }

    // separable box blur x2 for a soft, wide halo
    for (int iter = 0; iter < 2; ++iter) {
        std::vector<uint32_t> tmp(size_t(bw) * size_t(bh));
        for (int y = 0; y < bh; ++y) {
            const uint32_t* row = px + y * strideWords;
            for (int x = 0; x < bw; ++x) {
                int r = 0, g = 0, b = 0, n = 0;
                for (int k = -2; k <= 2; ++k) {
                    const int xx = std::clamp(x + k, 0, bw - 1);
                    const uint32_t c = row[xx];
                    r += int(c >> 16) & 255; g += int(c >> 8) & 255; b += int(c) & 255; ++n;
                }
                tmp[size_t(y) * bw + x] = (uint32_t(r / n) << 16) | (uint32_t(g / n) << 8) | uint32_t(b / n);
            }
        }
        for (int y = 0; y < bh; ++y) {
            for (int x = 0; x < bw; ++x) {
                int r = 0, g = 0, b = 0, n = 0;
                for (int k = -2; k <= 2; ++k) {
                    const int yy = std::clamp(y + k, 0, bh - 1);
                    const uint32_t c = tmp[size_t(yy) * bw + x];
                    r += int(c >> 16) & 255; g += int(c >> 8) & 255; b += int(c) & 255; ++n;
                }
                px[y * strideWords + x] = (uint32_t(r / n) << 16) | (uint32_t(g / n) << 8) | uint32_t(b / n);
            }
        }
    }

    // read-only external-data image: no copy, buffer stays alive in scope
    BLImage glow;
    if (glow.createFromData(bw, bh, BL_FORMAT_PRGB32, px, sd.stride, BL_DATA_ACCESS_READ) != BL_SUCCESS)
        return;

    ctx.setCompOp(BL_COMP_OP_PLUS);
    ctx.blitImage(BLRect(0, 0, kW, kH), glow);
    ctx.setCompOp(BL_COMP_OP_SRC_OVER);
}

// ------------------------------------------------------------- frame loop ---

void renderFrames(const DemoSpec& spec, const std::string& outDir,
                  const std::function<void(BLContext&, double, int)>& painter) {
    fs::create_directories(outDir);
    const int frames = std::max(2, int(std::lround(spec.seconds * double(kFps))));
    for (int frame = 0; frame < frames; ++frame) {
        const double t = double(frame) / double(frames - 1);
        BLImage image(kW / 2, kH / 2, BL_FORMAT_PRGB32);
        BLContext ctx(image);
        ctx.clearAll();
        ctx.scale(0.5);
        painter(ctx, t, frame);
        applyBloom(ctx, image, spec.glow);
        ctx.end();

        std::ostringstream path;
        path << outDir << "/frame_" << std::setw(4) << std::setfill('0') << (frame + 1) << ".png";
        if (image.writeToFile(path.str().c_str()) != BL_SUCCESS) {
            std::cerr << "write failed: " << path.str() << std::endl;
            std::exit(3);
        }
    }
    std::cout << "  " << spec.slug << " -> " << frames << " frames" << std::endl;
}

}  // namespace

int main(int argc, char** argv) {
    // display face (titles) falls back Poppins -> Inter; ui face falls back
    // DM Sans -> Inter. Both live in Chronon3D's font tree.
    BLFontFace bold;
    BLFontFace reg;
    if (bold.createFromFile((kFontsDir + "/Poppins-Bold.ttf").c_str()) != BL_SUCCESS)
        bold.createFromFile((kFontsDir + "/Inter-Bold.ttf").c_str());
    if (reg.createFromFile((kFontsDir + "/DMSans-Regular.ttf").c_str()) != BL_SUCCESS)
        reg.createFromFile((kFontsDir + "/Inter-Regular.ttf").c_str());
    if (!bold.isValid() || !reg.isValid()) {
        std::cerr << "No display/ui text font found in " << kFontsDir << std::endl;
        return 2;
    }
    Chrome chrome;
    if (chrome.label.createFromFace(reg, 62.0f) != BL_SUCCESS) {
        std::cerr << "failed to create label font" << std::endl;
        return 2;
    }

    std::string only;
    std::string outRoot = "out/text_kinetic_showcase";
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--demo" && i + 1 < argc) only = argv[++i];
        else if (a == "--out" && i + 1 < argc) outRoot = argv[++i];
    }

    const double baselineY = kH * 0.545;

    for (int i = 0; i < kTotalDemos; ++i) {
        const DemoId id = DemoId(i);
        const DemoSpec spec = specFor(id);
        const bool wanted = only.empty() || only == "all" || std::to_string(i + 1) == only ||
                            only == spec.slug;
        if (!wanted) continue;

        PreparedRun run;
        if (spec.text[0] != '\0') {
            run = makeRunFitted(bold, spec.text, spec.fontSize, kW * 0.5, baselineY);
        }
        const SlotCtx C{&run, &spec, 0.0, int(run.run.slots.size())};

        const std::string dir = outRoot + "/" + spec.slug;

        switch (id) {
            case DemoId::RampUp:
            case DemoId::WordPop:
            case DemoId::FlipIn:
            case DemoId::FadeSlideWords:
            case DemoId::RotateWheel:
            case DemoId::DropBounce:
            case DemoId::SplitReveal: {
                SlotCtx cc = C;
                DemoSpec sp = spec;
                renderFrames(sp, dir, [&](BLContext& ctx, double t, int) {
                    (void)sp;
                    darkBackground(ctx);
                    cc.t = t;
                    cc.spec = &sp;
                    chrome.draw(ctx, i + 1, sp.title, sp.bg);
                    SlotCtx local = cc;
                    switch (id) {
                        case DemoId::RampUp: paintRampUp(ctx, t, local); break;
                        case DemoId::WordPop: paintWordPop(ctx, t, local); break;
                        case DemoId::FlipIn: paintFlipIn(ctx, t, local); break;
                        case DemoId::FadeSlideWords: paintFadeSlideWords(ctx, t, local); break;
                        case DemoId::RotateWheel: paintRotateWheel(ctx, t, local); break;
                        case DemoId::DropBounce: paintDropBounce(ctx, t, local); break;
                        default: paintSplitReveal(ctx, t, local); break;
                    }
                    darkVignette(ctx);
                });
                break;
            }

            case DemoId::SkewStop:
            case DemoId::BarHighlight:
            case DemoId::Tracking:
            case DemoId::ColorSweep:
            case DemoId::CaretTypewriter:
            case DemoId::DotBounce: {
                DemoSpec sp = spec;
                PreparedRun rr = run;
                renderFrames(sp, dir, [&](BLContext& ctx, double t, int) {
                    darkBackground(ctx);
                    SlotCtx local{&rr, &sp, t, int(rr.run.slots.size())};
                    chrome.draw(ctx, i + 1, sp.title, sp.bg);
                    switch (id) {
                        case DemoId::SkewStop: paintSkewStop(ctx, t, local, chrome); break;
                        case DemoId::BarHighlight: paintBarHighlight(ctx, t, local, chrome); break;
                        case DemoId::Tracking: paintTracking(ctx, t, local, bold); break;
                        case DemoId::ColorSweep: paintColorSweep(ctx, t, local, chrome); break;
                        case DemoId::CaretTypewriter: paintCaretTypewriter(ctx, t, local, chrome); break;
                        default: paintDotBounce(ctx, t, local); break;
                    }
                    darkVignette(ctx);
                });
                break;
            }

            case DemoId::BlurIn: {
                DemoSpec sp = spec;
                PreparedRun rr = run;
                renderFrames(sp, dir, [&](BLContext& ctx, double t, int) {
                    darkBackground(ctx);
                    SlotCtx local{&rr, &sp, t, int(rr.run.slots.size())};
                    chrome.draw(ctx, i + 1, sp.title, sp.bg);
                    paintBlurIn(ctx, t, local);
                    darkVignette(ctx);
                });
                break;
            }

            case DemoId::WaveBreathe: {
                DemoSpec sp = spec;
                PreparedRun rr = run;
                renderFrames(sp, dir, [&](BLContext& ctx, double t, int) {
                    darkBackground(ctx);
                    SlotCtx local{&rr, &sp, t, int(rr.run.slots.size())};
                    chrome.draw(ctx, i + 1, sp.title, sp.bg);
                    paintWaveBreathe(ctx, t, local);
                    darkVignette(ctx);
                });
                break;
            }

            case DemoId::GlitchRgb: {
                DemoSpec sp = spec;
                PreparedRun rr = run;
                renderFrames(sp, dir, [&](BLContext& ctx, double t, int) {
                    darkBackground(ctx);
                    SlotCtx local{&rr, &sp, t, int(rr.run.slots.size())};
                    chrome.draw(ctx, i + 1, sp.title, sp.bg);
                    paintGlitchRgb(ctx, t, local, chrome);
                    darkVignette(ctx);
                });
                break;
            }

            case DemoId::MaskWipe: {
                DemoSpec sp = spec;
                PreparedRun rr = run;
                renderFrames(sp, dir, [&](BLContext& ctx, double t, int) {
                    darkBackground(ctx);
                    SlotCtx local{&rr, &sp, t, int(rr.run.slots.size())};
                    chrome.draw(ctx, i + 1, sp.title, sp.bg);
                    paintMaskWipe(ctx, t, local);
                    darkVignette(ctx);
                });
                break;
            }

            case DemoId::SlamZoom: {
                DemoSpec sp = spec;
                PreparedRun rr = run;
                renderFrames(sp, dir, [&](BLContext& ctx, double t, int) {
                    darkBackground(ctx);
                    SlotCtx local{&rr, &sp, t, int(rr.run.slots.size())};
                    chrome.draw(ctx, i + 1, sp.title, sp.bg);
                    paintSlamZoom(ctx, t, local);
                    darkVignette(ctx);
                });
                break;
            }

            case DemoId::KineticCamera: {
                DemoSpec sp = spec;
                std::vector<KinWord> words;
                struct K { const char* t; double cx, cy, size, rot; };
                static const K ks[6] = {
                    {"MAKE", 1500.0, 800.0, 220.0, -3.0},
                    {"THE", 2900.0, 620.0, 190.0, 4.0},
                    {"TEXT", 700.0, 1700.0, 260.0, -5.0},
                    {"MOVE", 3050.0, 1800.0, 240.0, 6.0},
                    {"LOOK", 1600.0, 2750.0, 210.0, -4.0},
                    {"HUGE", 3700.0, 2650.0, 270.0, 5.0},
                };
                const Color cols[6] = {
                    BLRgba32(18, 24, 34), BLRgba32(18, 24, 34),
                    BLRgba32(214, 75, 58), BLRgba32(240, 168, 8),
                    BLRgba32(18, 24, 34), BLRgba32(18, 24, 34),
                };
                for (int w = 0; w < 6; ++w) {
                    KinWord kw;
                    kw.run = makeRun(bold, ks[w].t, ks[w].size, 0.0, 0.0);
                    const double shx = ks[w].cx - kw.run.run.centerX;
                    for (auto& sl : kw.run.run.slots) { sl.x += shx; sl.cx += shx; }
                    kw.run.run.centerX = ks[w].cx;
                    kw.run.run.centerY = ks[w].cy;
                    for (auto& sl : kw.run.run.slots) {
                        sl.baseline = ks[w].cy + kw.run.run.capHeight * 0.5;
                        sl.cy = ks[w].cy;
                    }
                    kw.color = cols[w];
                    kw.rotDeg = ks[w].rot;
                    words.push_back(kw);
                }
                renderFrames(sp, dir, [&](BLContext& ctx, double t, int) {
                    ctx.setFillStyle(BLRgba32(9, 11, 15));
                    ctx.fillRect(BLRect(0, 0, kW, kH));
                    chrome.draw(ctx, i + 1, sp.title, sp.bg);
                    paintKineticCamera(ctx, t, words);
                    // light-scene subtle edge falloff
                    BLGradient vignette(BLRadialGradientValues(kW * 0.5, kH * 0.5, kW * 0.5, kH * 0.5,
                                                               kW * 0.85, kW * 0.5));
                    vignette.addStop(0.0, BLRgba32(0, 0, 0, 0));
                    vignette.addStop(1.0, BLRgba32(0, 0, 0, 60));
                    ctx.setFillStyle(vignette);
                    ctx.fillRect(BLRect(0, 0, kW, kH));
                });
                break;
            }

            case DemoId::CirclePath: {
                DemoSpec sp = spec;
                renderFrames(sp, dir, [&](BLContext& ctx, double t, int) {
                    darkBackground(ctx);
                    chrome.draw(ctx, i + 1, sp.title, sp.bg);
                    paintCirclePath(ctx, t, bold, sp);
                    darkVignette(ctx);
                });
                break;
            }

            default:
                break;
        }
    }

    std::cout << "text_kinetic_showcase complete -> " << outRoot << std::endl;
    return 0;
}
