// ChrononTemplate — Social V2 C++ Emitter
// Broadcast-grade animated social media callouts (YouTube, TikTok, Reddit, Instagram).
// Native Chronon RenderPlan V3 with FreeType exact typography, vector SVG-style paths,
// crisp shadows, staggered spring/cubic motion, interactive like/heart bursts & reply reveals.
//
// Usage: emit_social_v2 <repo-root> <out-dir> [preset_id ...]

#include <nlohmann/json.hpp>
#include <ft2build.h>
#include FT_FREETYPE_H

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
using json = nlohmann::ordered_json;
namespace fs = std::filesystem;

constexpr int W = 1920;
constexpr int H = 1080;
constexpr int FPS = 60;
constexpr int FR = 390; // 6.5s @ 60fps

json rgba(const std::string& hex, double a = 1.0) {
    unsigned long v = std::stoul(hex.substr(1), nullptr, 16);
    return json::array({
        ((v >> 16) & 0xFF) / 255.0,
        ((v >> 8) & 0xFF) / 255.0,
        (v & 0xFF) / 255.0,
        a
    });
}

double textWidth(FT_Library lib, const fs::path& font, int size, const std::string& text) {
    FT_Face face;
    if (FT_New_Face(lib, font.c_str(), 0, &face)) {
        throw std::runtime_error("cannot open font " + font.string());
    }
    FT_Set_Pixel_Sizes(face, 0, size);
    double w = 0.0;
    FT_UInt prev = 0;
    for (unsigned char ch : text) {
        const FT_UInt g = FT_Get_Char_Index(face, ch);
        if (prev && FT_HAS_KERNING(face)) {
            FT_Vector k;
            FT_Get_Kerning(face, prev, g, FT_KERNING_DEFAULT, &k);
            w += k.x / 64.0;
        }
        FT_Load_Glyph(face, g, FT_LOAD_DEFAULT);
        w += face->glyph->advance.x / 64.0;
        prev = g;
    }
    FT_Done_Face(face);
    return w;
}

json track1d(const std::string& prop, const std::vector<std::pair<int, double>>& keys, const std::string& easing = "out_cubic") {
    json k = json::array();
    for (const auto& [f, v] : keys) {
        k.push_back({{"frame", f}, {"value", v}});
    }
    return {{"property", prop}, {"keyframes", k}, {"easing", easing}};
}

json track2d(const std::string& prop, const std::vector<std::pair<int, std::pair<double, double>>>& keys, const std::string& easing = "out_cubic") {
    json k = json::array();
    for (const auto& [f, v] : keys) {
        k.push_back({{"frame", f}, {"value", {v.first, v.second}}});
    }
    return {{"property", prop}, {"keyframes", k}, {"easing", easing}};
}

// Helper: 2D rect / rounded_rect positioned by top-left (x, y) and size (w, h)
json rectLayer(const std::string& id, double x, double y, double w, double h, const std::string& fillHex,
               double alpha = 1.0, double radius = 0.0, const std::string& strokeHex = "", double strokeW = 0.0) {
    json shape;
    if (radius > 0.0) {
        shape = {
            {"type", "rounded_rect"},
            {"corner_radius", {radius, radius, radius, radius}},
            {"fill", rgba(fillHex, alpha)}
        };
    } else {
        shape = {
            {"type", "rect"},
            {"fill", rgba(fillHex, alpha)}
        };
    }
    if (!strokeHex.empty() && strokeW > 0.0) {
        shape["stroke"] = {{"color", strokeHex}, {"width", strokeW}};
    }
    return {
        {"id", id},
        {"type", "shape"},
        {"size", {w, h}},
        {"position", {x + w * 0.5, y + h * 0.5}},
        {"start_frame", 0},
        {"duration_frames", FR},
        {"shape", shape}
    };
}

// Helper: 2D ellipse positioned by top-left (x, y) and size (w, h)
json ellipseLayer(const std::string& id, double x, double y, double w, double h, const std::string& fillHex,
                  double alpha = 1.0, const std::string& strokeHex = "", double strokeW = 0.0) {
    json shape = {
        {"type", "ellipse"},
        {"fill", rgba(fillHex, alpha)}
    };
    if (!strokeHex.empty() && strokeW > 0.0) {
        shape["stroke"] = {{"color", strokeHex}, {"width", strokeW}};
    }
    return {
        {"id", id},
        {"type", "shape"},
        {"size", {w, h}},
        {"position", {x + w * 0.5, y + h * 0.5}},
        {"start_frame", 0},
        {"duration_frames", FR},
        {"shape", shape}
    };
}

// Helper: 2D text positioned by top-left (x, y) and box (w, h), left-aligned by placing center at x + tw/2
// Note: Chronon text layers center-align their text box around `position`, so we measure exact width with FreeType
// and pass size = {tw + 16, h} and position = {x + (tw + 16)/2, y + h/2} for pixel-accurate left alignment!
json textLeftLayer(FT_Library lib, const fs::path& fontsDir, const std::string& id, const std::string& text,
                   double x, double y, int fontSize, const std::string& fillHex,
                   const std::string& fontFile = "RobotoS-Regular.ttf", double lineH = 0.0) {
    double tw = textWidth(lib, fontsDir / fontFile, fontSize, text);
    double boxW = std::max(tw + 20.0, 20.0);
    double boxH = lineH > 0.0 ? lineH : fontSize * 1.35;
    return {
        {"id", id},
        {"type", "text"},
        {"text", text},
        {"size", {boxW, boxH}},
        {"position", {x + boxW * 0.5 - 10.0, y + boxH * 0.5}},
        {"start_frame", 0},
        {"duration_frames", FR},
        {"style", {
            {"font", "assets/fonts/" + fontFile},
            {"font_size", fontSize},
            {"fill", fillHex}
        }}
    };
}

// Helper: pre-rasterized anti-aliased RGBA icon image centered at (cx, cy) with size (w, h)
json iconLayer(const std::string& id, const std::string& iconName, double cx, double cy, double w, double h) {
    return {
        {"id", id},
        {"type", "image"},
        {"asset", "assets/images/social_v2/icons/" + iconName},
        {"size", {w, h}},
        {"position", {cx, cy}},
        {"start_frame", 0},
        {"duration_frames", FR}
    };
}

// Helper: circular avatar image positioned by top-left (x, y) and diameter d
json avatarLayer(const std::string& id, const std::string& asset, double x, double y, double d) {
    return {
        {"id", id},
        {"type", "image"},
        {"asset", asset},
        {"size", {d, d}},
        {"position", {x + d * 0.5, y + d * 0.5}},
        {"start_frame", 0},
        {"duration_frames", FR}
    };
}

void addFadeSlideIn(json& layer, int f0, int f1, double dy = 18.0, double targetOpacity = 1.0) {
    json tracks = json::array();
    tracks.push_back(track1d("opacity", {{0, 0.0}, {f0, 0.0}, {f1, targetOpacity}}, "out_cubic"));
    if (std::abs(dy) > 0.01) {
        tracks.push_back(track1d("position_y", {{0, dy}, {f0, dy}, {f1, 0.0}}, "out_cubic"));
    }
    layer["animation"] = {{"tracks", tracks}};
}

// YouTube Thumbs Up SVG-style path in [-12, 12] local coords
json ytThumbsUpPath(double s = 1.0) {
    auto pt = [&](double x, double y) { return json::array({x * s, y * s}); };
    return json::array({
        {{"type", "move_to"}, {"point", pt(-9.5, -1.5)}},
        {{"type", "line_to"}, {"point", pt(-5.0, -1.5)}},
        {{"type", "line_to"}, {"point", pt(-5.0, 9.5)}},
        {{"type", "line_to"}, {"point", pt(-9.5, 9.5)}},
        {{"type", "close"}},
        {{"type", "move_to"}, {"point", pt(-2.8, -1.5)}},
        {{"type", "line_to"}, {"point", pt(1.2, -9.2)}},
        {{"type", "cubic_to"}, {"control1", pt(2.4, -9.6)}, {"control2", pt(3.6, -8.5)}, {"point", pt(3.2, -6.5)}},
        {{"type", "line_to"}, {"point", pt(2.3, -2.5)}},
        {{"type", "line_to"}, {"point", pt(8.2, -2.5)}},
        {{"type", "cubic_to"}, {"control1", pt(10.0, -2.5)}, {"control2", pt(10.8, -1.0)}, {"point", pt(10.3, 0.8)}},
        {{"type", "line_to"}, {"point", pt(8.4, 7.6)}},
        {{"type", "cubic_to"}, {"control1", pt(8.0, 9.0)}, {"control2", pt(6.8, 9.5)}, {"point", pt(5.3, 9.5)}},
        {{"type", "line_to"}, {"point", pt(-2.8, 9.5)}},
        {{"type", "close"}}
    });
}

// YouTube Thumbs Down SVG-style path (flipped vertically)
json ytThumbsDownPath(double s = 1.0) {
    auto pt = [&](double x, double y) { return json::array({x * s, -y * s}); };
    return json::array({
        {{"type", "move_to"}, {"point", pt(-9.5, -1.5)}},
        {{"type", "line_to"}, {"point", pt(-5.0, -1.5)}},
        {{"type", "line_to"}, {"point", pt(-5.0, 9.5)}},
        {{"type", "line_to"}, {"point", pt(-9.5, 9.5)}},
        {{"type", "close"}},
        {{"type", "move_to"}, {"point", pt(-2.8, -1.5)}},
        {{"type", "line_to"}, {"point", pt(1.2, -9.2)}},
        {{"type", "cubic_to"}, {"control1", pt(2.4, -9.6)}, {"control2", pt(3.6, -8.5)}, {"point", pt(3.2, -6.5)}},
        {{"type", "line_to"}, {"point", pt(2.3, -2.5)}},
        {{"type", "line_to"}, {"point", pt(8.2, -2.5)}},
        {{"type", "cubic_to"}, {"control1", pt(10.0, -2.5)}, {"control2", pt(10.8, -1.0)}, {"point", pt(10.3, 0.8)}},
        {{"type", "line_to"}, {"point", pt(8.4, 7.6)}},
        {{"type", "cubic_to"}, {"control1", pt(8.0, 9.0)}, {"control2", pt(6.8, 9.5)}, {"point", pt(5.3, 9.5)}},
        {{"type", "line_to"}, {"point", pt(-2.8, 9.5)}},
        {{"type", "close"}}
    });
}

// Heart icon path
json heartPath(double s = 1.0) {
    auto pt = [&](double x, double y) { return json::array({x * s, y * s}); };
    return json::array({
        {{"type", "move_to"}, {"point", pt(0.0, 8.5)}},
        {{"type", "cubic_to"}, {"control1", pt(-5.5, 4.5)}, {"control2", pt(-10.0, 0.5)}, {"point", pt(-10.0, -4.0)}},
        {{"type", "cubic_to"}, {"control1", pt(-10.0, -7.8)}, {"control2", pt(-6.5, -9.5)}, {"point", pt(-3.5, -9.5)}},
        {{"type", "cubic_to"}, {"control1", pt(-1.4, -9.5)}, {"control2", pt(0.0, -7.6)}, {"point", pt(0.0, -6.2)}},
        {{"type", "cubic_to"}, {"control1", pt(0.0, -7.6)}, {"control2", pt(1.4, -9.5)}, {"point", pt(3.5, -9.5)}},
        {{"type", "cubic_to"}, {"control1", pt(6.5, -9.5)}, {"control2", pt(10.0, -7.8)}, {"point", pt(10.0, -4.0)}},
        {{"type", "cubic_to"}, {"control1", pt(10.0, 0.5)}, {"control2", pt(5.5, 4.5)}, {"point", pt(0.0, 8.5)}},
        {{"type", "close"}}
    });
}

// Verified Checkmark path
json checkPath(double s = 1.0) {
    auto pt = [&](double x, double y) { return json::array({x * s, y * s}); };
    return json::array({
        {{"type", "move_to"}, {"point", pt(-4.5, 0.2)}},
        {{"type", "line_to"}, {"point", pt(-1.2, 3.6)}},
        {{"type", "line_to"}, {"point", pt(4.8, -3.2)}}
    });
}

// Pin icon path
json pinPath(double s = 1.0) {
    auto pt = [&](double x, double y) { return json::array({x * s, y * s}); };
    return json::array({
        {{"type", "move_to"}, {"point", pt(-4.0, -6.0)}},
        {{"type", "line_to"}, {"point", pt(4.0, -6.0)}},
        {{"type", "line_to"}, {"point", pt(3.0, -1.0)}},
        {{"type", "line_to"}, {"point", pt(5.5, 2.0)}},
        {{"type", "line_to"}, {"point", pt(0.8, 2.0)}},
        {{"type", "line_to"}, {"point", pt(0.0, 8.0)}},
        {{"type", "line_to"}, {"point", pt(-0.8, 2.0)}},
        {{"type", "line_to"}, {"point", pt(-5.5, 2.0)}},
        {{"type", "line_to"}, {"point", pt(-3.0, -1.0)}},
        {{"type", "close"}}
    });
}

json buildYouTubeCommentsDark(FT_Library lib, const fs::path& fontsDir) {
    json layers = json::array();

    // 1. Deep documentary studio backdrop (pre-rendered GPU-native image plate)
    layers.push_back({
        {"id", "studio_bg"},
        {"type", "image"},
        {"asset", "assets/images/social_v2/bg_dark_studio.png"},
        {"size", {W, H}},
        {"position", {W * 0.5, H * 0.5}},
        {"start_frame", 0},
        {"duration_frames", FR}
    });

    // Card layout metrics
    const double cw = 1220.0;
    const double ch = 740.0;
    const double cx = (W - cw) * 0.5;   // 350
    const double cy = (H - ch) * 0.5;   // 170
    const double padX = 52.0;

    // 2. Main Elevated YouTube Card (with crisp border & multi-layered drop shadow)
    json card = rectLayer("yt_card", cx, cy, cw, ch, "#161618", 1.0, 24.0, "#2C2C32", 1.5);
    card["style"] = {
        {"shadow", {
            {"color", "#000000"},
            {"offset", {0.0, 28.0}},
            {"opacity", 0.65},
            {"blur", 42.0}
        }}
    };
    card["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {18, 1.0}}, "out_cubic"),
        track1d("position_y", {{0, 42.0}, {32, 0.0}, {FR - 1, -6.0}}, "out_cubic"),
        track2d("scale", {{0, {0.94, 0.94}}, {32, {1.0, 1.0}}, {FR - 1, {1.018, 1.018}}}, "out_cubic")
    }}};
    layers.push_back(card);

    // Subtle top highlight accent line inside card
    json topShine = rectLayer("yt_top_shine", cx + 28, cy + 1, cw - 56, 2.0, "#FFFFFF", 0.08, 1.0);
    addFadeSlideIn(topShine, 8, 28, 42.0, 0.08);
    layers.push_back(topShine);

    // 3. Header: "Comments" + "14,820" + Sort icon
    double hx = cx + padX;
    double hy = cy + 36.0;
    json hTitle = textLeftLayer(lib, fontsDir, "yt_hdr_title", "Comments", hx, hy, 28, "#F1F1F1", "RobotoS-Bold.ttf", 36);
    addFadeSlideIn(hTitle, 14, 34, 14.0);
    layers.push_back(hTitle);

    double wTitle = textWidth(lib, fontsDir / "RobotoS-Bold.ttf", 28, "Comments");
    json hCount = textLeftLayer(lib, fontsDir, "yt_hdr_count", "14,820", hx + wTitle + 18.0, hy + 2.0, 24, "#9A9AA0", "RobotoS-Regular.ttf", 34);
    addFadeSlideIn(hCount, 18, 38, 14.0);
    layers.push_back(hCount);

    // Sort icon (3 bars) + "Sort by" on right
    double sx = cx + cw - padX - 120.0;
    for (int i = 0; i < 3; ++i) {
        double bw = 22.0 - i * 5.0;
        json bar = rectLayer("yt_sort_bar_" + std::to_string(i), sx, hy + 10.0 + i * 7.0, bw, 2.5, "#F1F1F1", 1.0, 1.2);
        addFadeSlideIn(bar, 18, 38, 14.0);
        layers.push_back(bar);
    }
    json sortTxt = textLeftLayer(lib, fontsDir, "yt_sort_txt", "Sort by", sx + 32.0, hy + 5.0, 19, "#F1F1F1", "RobotoS-Medium.ttf", 28);
    addFadeSlideIn(sortTxt, 18, 38, 14.0);
    layers.push_back(sortTxt);

    // Hairline divider
    json div = rectLayer("yt_hdr_div", cx + padX, hy + 54.0, cw - padX * 2.0, 1.2, "#28282E", 1.0);
    addFadeSlideIn(div, 16, 36, 10.0);
    layers.push_back(div);

    // 4. Main Featured Comment
    double mx = cx + padX;
    double my = hy + 78.0;

    // Pinned indicator
    json pinIcon = iconLayer("yt_pin_icon", "pin_grey.png", mx + 86.0, my + 10.0, 18.0, 18.0);
    addFadeSlideIn(pinIcon, 26, 46, 12.0);
    layers.push_back(pinIcon);

    json pinTxt = textLeftLayer(lib, fontsDir, "yt_pin_txt", "Pinned by @MarcoValenti", mx + 104.0, my - 1.0, 16, "#AAAAAA", "RobotoS-Medium.ttf", 22);
    addFadeSlideIn(pinTxt, 26, 46, 12.0);
    layers.push_back(pinTxt);

    // Main Avatar (64x64) + subtle ring
    double avY = my + 34.0;
    json avRing = ellipseLayer("yt_main_av_ring", mx - 2.0, avY - 2.0, 68.0, 68.0, "#2E2E36", 1.0);
    avRing["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {24, 0.0}, {42, 1.0}}, "out_cubic"),
        track2d("scale", {{0, {0.75, 0.75}}, {24, {0.75, 0.75}}, {48, {1.0, 1.0}}}, "out_back")
    }}};
    layers.push_back(avRing);

    json av = avatarLayer("yt_main_av", "assets/images/social_v2/avatar_1.png", mx, avY, 64.0);
    av["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {24, 0.0}, {42, 1.0}}, "out_cubic"),
        track2d("scale", {{0, {0.75, 0.75}}, {24, {0.75, 0.75}}, {48, {1.0, 1.0}}}, "out_back")
    }}};
    layers.push_back(av);

    // Author handle + verified badge + timestamp
    double tx = mx + 86.0;
    double ty = avY + 2.0;
    std::string authorHandle = "@lorenzo_b";
    json authTxt = textLeftLayer(lib, fontsDir, "yt_main_author", authorHandle, tx, ty, 20, "#F1F1F1", "RobotoS-Medium.ttf", 28);
    addFadeSlideIn(authTxt, 28, 48, 12.0);
    layers.push_back(authTxt);

    double wAuth = textWidth(lib, fontsDir / "RobotoS-Medium.ttf", 20, authorHandle);
    double vx = tx + wAuth + 10.0;
    json vCircle = iconLayer("yt_main_ver", "verified_yt_dark.png", vx + 9.0, ty + 13.0, 19.0, 19.0);
    addFadeSlideIn(vCircle, 30, 50, 12.0);
    layers.push_back(vCircle);

    json timeTxt = textLeftLayer(lib, fontsDir, "yt_main_time", "2 days ago", vx + 28.0, ty + 1.0, 18, "#9A9AA0", "RobotoS-Regular.ttf", 26);
    addFadeSlideIn(timeTxt, 32, 52, 12.0);
    layers.push_back(timeTxt);

    // Comment Body (Line 1 with inline blue timestamp "04:12", Line 2)
    double by = ty + 38.0;
    std::string l1a = "Nobody talks about how clean that transition at ";
    std::string l1ts = "04:12";
    std::string l1b = " actually is.";
    std::string l2 = "You can tell months of sound design went into just those ten seconds.";

    json body1a = textLeftLayer(lib, fontsDir, "yt_body_1a", l1a, tx, by, 24, "#F1F1F1", "RobotoS-Regular.ttf", 34);
    addFadeSlideIn(body1a, 38, 60, 14.0);
    layers.push_back(body1a);

    double w1a = textWidth(lib, fontsDir / "RobotoS-Regular.ttf", 24, l1a);
    double w1ts = textWidth(lib, fontsDir / "RobotoS-Medium.ttf", 24, l1ts);

    // Subtle timestamp pill behind 04:12
    json tsPill = rectLayer("yt_ts_pill", tx + w1a - 4.0, by + 2.0, w1ts + 10.0, 30.0, "#3EA6FF", 0.14, 6.0);
    addFadeSlideIn(tsPill, 42, 62, 14.0, 0.14);
    layers.push_back(tsPill);

    json body1ts = textLeftLayer(lib, fontsDir, "yt_body_1ts", l1ts, tx + w1a + 1.0, by, 24, "#3EA6FF", "RobotoS-Medium.ttf", 34);
    addFadeSlideIn(body1ts, 40, 62, 14.0);
    layers.push_back(body1ts);

    json body1b = textLeftLayer(lib, fontsDir, "yt_body_1b", l1b, tx + w1a + w1ts + 4.0, by, 24, "#F1F1F1", "RobotoS-Regular.ttf", 34);
    addFadeSlideIn(body1b, 42, 64, 14.0);
    layers.push_back(body1b);

    json body2 = textLeftLayer(lib, fontsDir, "yt_body_2", l2, tx, by + 38.0, 24, "#F1F1F1", "RobotoS-Regular.ttf", 34);
    addFadeSlideIn(body2, 46, 68, 14.0);
    layers.push_back(body2);

    // 5. Action Bar (Thumbs Up interactive + Like Odometer + Thumbs Down + Creator Heart + Reply)
    double ay = by + 94.0;
    double likeCx = tx + 14.0;
    double likeCy = ay + 14.0;

    // Expanding ring burst when liked at frame 95
    json likeBurst = ellipseLayer("yt_like_burst", likeCx - 16.0, likeCy - 16.0, 32.0, 32.0, "#3EA6FF", 0.0, "#3EA6FF", 2.5);
    likeBurst["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {94, 0.0}, {98, 0.85}, {122, 0.0}}, "out_cubic"),
        track2d("scale", {{0, {0.5, 0.5}}, {94, {0.5, 0.5}}, {122, {2.1, 2.1}}}, "out_cubic")
    }}};
    layers.push_back(likeBurst);

    // Unliked outline thumbs up (fades out at frame 96)
    json likeOff = iconLayer("yt_like_off", "yt_like_off.png", likeCx, likeCy, 26.0, 26.0);
    likeOff["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {54, 0.0}, {72, 1.0}, {94, 1.0}, {98, 0.0}}, "linear"),
        track1d("position_y", {{0, 10.0}, {54, 10.0}, {72, 0.0}}, "out_cubic")
    }}};
    layers.push_back(likeOff);

    // Liked filled blue thumbs up (pops in with out_back at frame 95)
    json likeOn = iconLayer("yt_like_on", "yt_like_on.png", likeCx, likeCy, 26.0, 26.0);
    likeOn["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {94, 0.0}, {97, 1.0}}, "linear"),
        track2d("scale", {{0, {0.5, 0.5}}, {94, {0.5, 0.5}}, {108, {1.28, 1.28}}, {122, {1.0, 1.0}}}, "out_back")
    }}};
    layers.push_back(likeOn);

    // Odometer Like Count: "2,418" slides out up, "2,419" slides in from bottom at frame 96-112
    json cntOld = textLeftLayer(lib, fontsDir, "yt_cnt_old", "2,418", tx + 38.0, ay + 1.0, 18, "#AAAAAA", "RobotoS-Medium.ttf", 26);
    cntOld["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {54, 0.0}, {72, 1.0}, {95, 1.0}, {108, 0.0}}, "out_cubic"),
        track1d("position_y", {{0, 10.0}, {54, 10.0}, {72, 0.0}, {95, 0.0}, {108, -14.0}}, "out_cubic")
    }}};
    layers.push_back(cntOld);

    json cntNew = textLeftLayer(lib, fontsDir, "yt_cnt_new", "2,419", tx + 38.0, ay + 1.0, 18, "#3EA6FF", "RobotoS-Medium.ttf", 26);
    cntNew["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {95, 0.0}, {110, 1.0}}, "out_cubic"),
        track1d("position_y", {{0, 14.0}, {95, 14.0}, {110, 0.0}}, "out_cubic")
    }}};
    layers.push_back(cntNew);

    // Thumbs down
    json dislike = iconLayer("yt_dislike", "yt_dislike_off.png", tx + 132.0, likeCy + 1.0, 26.0, 26.0);
    addFadeSlideIn(dislike, 56, 74, 10.0);
    layers.push_back(dislike);

    // Creator Heart Badge (pops in at frame 135)
    double hbx = tx + 186.0;
    double hby = ay - 2.0;
    json hAv = avatarLayer("yt_heart_av", "assets/images/social_v2/avatar_3.png", hbx, hby, 30.0);
    hAv["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {132, 0.0}, {144, 1.0}}, "out_cubic"),
        track2d("scale", {{0, {0.4, 0.4}}, {132, {0.4, 0.4}}, {152, {1.0, 1.0}}}, "out_back")
    }}};
    layers.push_back(hAv);

    json hBadgeBg = ellipseLayer("yt_heart_bg", hbx + 17.0, hby + 15.0, 19.0, 19.0, "#161618", 1.0);
    hBadgeBg["animation"] = hAv["animation"];
    layers.push_back(hBadgeBg);

    json hIcon = iconLayer("yt_heart_icon", "heart_yt_red.png", hbx + 26.5, hby + 24.5, 16.0, 16.0);
    hIcon["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {134, 0.0}, {144, 1.0}}, "out_cubic"),
        track2d("scale", {{0, {0.2, 0.2}}, {134, {0.2, 0.2}}, {154, {1.25, 1.25}}, {168, {1.0, 1.0}}}, "out_back")
    }}};
    layers.push_back(hIcon);

    // "Reply" text button
    json replyBtn = textLeftLayer(lib, fontsDir, "yt_reply_btn", "Reply", tx + 244.0, ay + 1.0, 18, "#F1F1F1", "RobotoS-Medium.ttf", 26);
    addFadeSlideIn(replyBtn, 60, 78, 10.0);
    layers.push_back(replyBtn);

    // 6. Expandable Reply Thread ("2 replies" + 2 staggered replies)
    double ry0 = ay + 52.0;
    json repliesPill = textLeftLayer(lib, fontsDir, "yt_replies_toggle", "2 replies", tx, ry0, 19, "#3EA6FF", "RobotoS-Medium.ttf", 28);
    addFadeSlideIn(repliesPill, 165, 185, 10.0);
    layers.push_back(repliesPill);

    // Vertical thread line growing downward
    json threadLine = rectLayer("yt_thread_line", tx + 21.0, ry0 + 44.0, 2.0, 195.0, "#2D2D34", 1.0, 1.0);
    threadLine["animation"] = {{"tracks", {
        track1d("opacity", {{0, 0.0}, {178, 0.0}, {205, 1.0}}, "out_cubic"),
        track1d("position_y", {{0, 20.0}, {178, 20.0}, {205, 0.0}}, "out_cubic")
    }}};
    layers.push_back(threadLine);

    // Reply 1 (Frame 185)
    double r1y = ry0 + 44.0;
    double rtx = tx + 62.0;
    json r1Av = avatarLayer("yt_r1_av", "assets/images/social_v2/avatar_2.png", tx, r1y, 44.0);
    addFadeSlideIn(r1Av, 182, 204, 16.0);
    layers.push_back(r1Av);

    std::string r1Auth = "@chiara_films";
    json r1AuthTxt = textLeftLayer(lib, fontsDir, "yt_r1_auth", r1Auth, rtx, r1y, 18, "#F1F1F1", "RobotoS-Medium.ttf", 24);
    addFadeSlideIn(r1AuthTxt, 186, 208, 14.0);
    layers.push_back(r1AuthTxt);

    double wr1 = textWidth(lib, fontsDir / "RobotoS-Medium.ttf", 18, r1Auth);
    json r1Time = textLeftLayer(lib, fontsDir, "yt_r1_time", "1 day ago", rtx + wr1 + 14.0, r1y + 1.0, 16, "#9A9AA0", "RobotoS-Regular.ttf", 22);
    addFadeSlideIn(r1Time, 188, 210, 14.0);
    layers.push_back(r1Time);

    json r1Body = textLeftLayer(lib, fontsDir, "yt_r1_body", "Agreed, the pacing in the second half feels like a feature documentary.", rtx, r1y + 29.0, 21, "#E4E4E7", "RobotoS-Regular.ttf", 28);
    addFadeSlideIn(r1Body, 190, 212, 14.0);
    layers.push_back(r1Body);

    json r1Like = iconLayer("yt_r1_like", "yt_like_off.png", rtx + 10.0, r1y + 72.0, 20.0, 20.0);
    addFadeSlideIn(r1Like, 194, 216, 12.0);
    layers.push_back(r1Like);

    json r1Cnt = textLeftLayer(lib, fontsDir, "yt_r1_cnt", "184", rtx + 28.0, r1y + 60.0, 16, "#AAAAAA", "RobotoS-Regular.ttf", 22);
    addFadeSlideIn(r1Cnt, 194, 216, 12.0);
    layers.push_back(r1Cnt);

    // Reply 2 — Creator Reply with pill badge (Frame 220)
    double r2y = r1y + 106.0;
    json r2Av = avatarLayer("yt_r2_av", "assets/images/social_v2/avatar_3.png", tx, r2y, 44.0);
    addFadeSlideIn(r2Av, 218, 240, 16.0);
    layers.push_back(r2Av);

    std::string r2Auth = "@MarcoValenti";
    double wr2 = textWidth(lib, fontsDir / "RobotoS-Medium.ttf", 17, r2Auth);
    json r2Pill = rectLayer("yt_r2_pill", rtx, r2y - 1.0, wr2 + 38.0, 28.0, "#3F3F46", 1.0, 14.0);
    addFadeSlideIn(r2Pill, 222, 244, 14.0);
    layers.push_back(r2Pill);

    json r2AuthTxt = textLeftLayer(lib, fontsDir, "yt_r2_auth", r2Auth, rtx + 12.0, r2y + 2.0, 17, "#FFFFFF", "RobotoS-Medium.ttf", 22);
    addFadeSlideIn(r2AuthTxt, 222, 244, 14.0);
    layers.push_back(r2AuthTxt);

    json r2Ver = iconLayer("yt_r2_ver", "verified_yt_dark.png", rtx + wr2 + 22.0, r2y + 13.0, 16.0, 16.0);
    addFadeSlideIn(r2Ver, 224, 246, 14.0);
    layers.push_back(r2Ver);

    json r2Time = textLeftLayer(lib, fontsDir, "yt_r2_time", "18 hours ago", rtx + wr2 + 48.0, r2y + 2.0, 16, "#9A9AA0", "RobotoS-Regular.ttf", 22);
    addFadeSlideIn(r2Time, 224, 246, 14.0);
    layers.push_back(r2Time);

    json r2Body = textLeftLayer(lib, fontsDir, "yt_r2_body", "Appreciate it! Took 3 weeks just to nail the sound design.", rtx, r2y + 32.0, 21, "#E4E4E7", "RobotoS-Regular.ttf", 28);
    addFadeSlideIn(r2Body, 226, 248, 14.0);
    layers.push_back(r2Body);

    json r2Like = iconLayer("yt_r2_like", "yt_like_off.png", rtx + 10.0, r2y + 74.0, 20.0, 20.0);
    addFadeSlideIn(r2Like, 230, 252, 12.0);
    layers.push_back(r2Like);

    json r2Cnt = textLeftLayer(lib, fontsDir, "yt_r2_cnt", "412", rtx + 28.0, r2y + 62.0, 16, "#AAAAAA", "RobotoS-Regular.ttf", 22);
    addFadeSlideIn(r2Cnt, 230, 252, 12.0);
    layers.push_back(r2Cnt);

    return {
        {"schema", "chronon.render-plan.v3"},
        {"version", 3},
        {"job_id", "yt_comments_dark_v2"},
        {"canvas", {
            {"width", W},
            {"height", H},
            {"fps_num", FPS},
            {"fps_den", 1},
            {"duration_frames", FR}
        }},
        {"layers", layers},
        {"output", {
            {"path", "yt_comments_dark_v2.mp4"},
            {"format", "mp4"},
            {"codec", "h264"}
        }}
    };
}
} // namespace

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "usage: emit_social_v2 <repo-root> <out-dir>\n";
        return 2;
    }
    const fs::path repo = argv[1];
    const fs::path out = argv[2];
    fs::create_directories(out);

    FT_Library lib;
    if (FT_Init_FreeType(&lib)) {
        std::cerr << "FT_Init_FreeType failed\n";
        return 1;
    }

    const fs::path fontsDir = repo / "Chronon3d/assets/fonts";
    json plan = buildYouTubeCommentsDark(lib, fontsDir);
    std::ofstream(out / "yt_comments_dark_v2.plan.json") << plan.dump(1);
    std::cout << "emitted yt_comments_dark_v2\n";

    FT_Done_FreeType(lib);
    return 0;
}
