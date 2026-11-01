// ui_shots_figma_notion.cpp — 15 native Figma/Notion-style UI compositions.
//
// Renders to ChrononTemplate/artifacts/ui_shots_figma_notion_v1/<scene>/:
//   frames/frame_####.png  still.png  <scene>.mp4
// plus contact_sheet.png and manifest.json at the pack root.
//
// Usage: ui_shots_figma_notion.exe [--keep-frames] [--stills] [--out DIR] [scene ids...]
// With no scene ids every scene renders.

#include "ui_pack.hpp"

#include <cmath>
#include <cctype>
#include <clocale>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace chronon::uipack {

using std::string;
using std::clamp;

// ---------------------------------------------------------------- colors -- //
static const BLRgba32 kInkBg{30, 30, 32, 255};          // dark canvas
static const BLRgba32 kPageC{255, 255, 255, 255};
static const BLRgba32 kCream{250, 249, 246, 255};       // warm article page
static const BLRgba32 kPaper{249, 246, 240, 255};       // notion-cream
static const BLRgba32 kDeep{13, 17, 23, 255};           // github-ish panel
static const BLRgba32 kNight{15, 16, 19, 255};
static const BLRgba32 kBlue{59, 130, 246, 255};
static const BLRgba32 kFigmaBlue{37, 99, 235, 255};
static const BLRgba32 kGreenC{16, 163, 84, 255};
static const BLRgba32 kOrangeC{245, 166, 35, 255};
static const BLRgba32 kVioletC{159, 75, 224, 255};

// ------------------------------------------------------------- dispatch -- //
struct Catalog {
    int id; const char* name; const char* desc;
    double z0, z1, cx, cy, stillT;
    void (*draw)(BLContext&, double, int);
};

// ------------------------------------------------------------------ 01 -- //
// Cursor selects a settings card on a dark dot-grid canvas.
static void s01(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.06, .5, .49}, t);
    c.setFillStyle(kInkBg); c.fillRect(0, 0, kW, kH);
    dotGrid(c, 56, BLRgba32(255, 255, 255, 18), 2.6);

    const double cx = 1240, cy = 660, cw = 1360, ch = 780;
    softShadow(c, cx, cy, cw, ch, 36);
    card(c, cx, cy, cw, ch, 36, kPageC);

    fillText(c, face("bold", 68), cx + 96, cy + 156, "Getting started", rgba(23, 23, 27));
    fillText(c, face("reg", 46), cx + 96, cy + 256, "Invite your team to collaborate in one workspace",
             rgba(156, 156, 163));
    fillText(c, face("med", 46), cx + 96, cy + 330, "Slides, reports and assets live in this project.",
             rgba(120, 120, 128));

    const double bx = cx + 96, by = cy + 540, bw = 520, bh = 120;
    card(c, bx, by, bw, bh, 24, kBlue);
    textC(c, face("semi", 48), bx + bw * .5, by + 78, "Invite members", kPageC);
    card(c, bx + bw + 44, by, 250, bh, 24, kPageC, false, BLRgba32(0, 0, 0, 26));
    textC(c, face("med", 48), bx + bw + 44 + 125, by + 78, "Skip", rgba(95, 95, 104));

    const double px = lerp(700.0, bx + bw * .5, easeInOutCubic(wind(t, 0.0, 0.42)));
    const double py = lerp(1980.0, by + bh * .5, easeInOutCubic(wind(t, 0.0, 0.42)));
    ripple(c, bx + bw * .5, by + bh * .5, wind(t, 0.44, 0.62), kFigmaBlue);
    handles(c, cx - 18, cy - 18, cw + 36, ch + 36, wind(t, 0.55, 0.78), kFigmaBlue);
    pointer(c, px, py, "You", kBlue, 1.0);
}

// ------------------------------------------------------------------ 02 -- //
// Slash-menu typing inside a Notion doc.
static void s02(BLContext& c, double t, int fr) {
    cam(c, {1.02, 1.05, .47, .48}, t);
    c.setFillStyle(kPageC); c.fillRect(0, 0, kW, kH);

    const double x0 = 1040;
    fillText(c, face("black", 156), x0, 560, "Weekly sync", rgba(23, 23, 23));
    fillText(c, face("reg", 60), x0, 764, "Notes from this morning:", rgba(55, 53, 47));

    const BLFont fbody = face("reg", 60);
    fillText(c, fbody, x0, 888, "**", rgba(23, 23, 23));
    const string typedPart = typed("Planning montage", wind(t, 0.10, 0.44));
    fillText(c, fbody, x0 + textW(fbody, "**") + 14, 888, typedPart, rgba(23, 23, 23));
    if ((fr % 24) < 15 && t < 0.52) {
        const double tx = x0 + textW(fbody, "**") + textW(fbody, typedPart) + 16;
        c.setFillStyle(kBlue); c.fillRect(BLRect(tx, 834, 10, 66));
    }

    // faint page skeleton under the popup
    for (int i = 0; i < 3; ++i) {
        c.setFillStyle(BLRgba32(233, 232, 229, 255));
        c.fillRect(BLRect(x0, 1560 + i * 84, 1700 * (1 - i * 0.12), 18));
    }

    // slash menu popup
    const double me = easeInOutCubic(wind(t, 0.52, 0.66));
    double mx = x0 + 24, my = 970;
    if (me > 0.004) {
        mx = 1064; my = 970 - (1 - me) * 60;
        softShadow(c, mx, my, 760, 500, 30, 30, 56, 50);
        card(c, mx, my, 760, 500, 30, kPageC, false, BLRgba32(0, 0, 0, 24));
        fillText(c, face("semi", 36), mx + 44, my + 88, "actions", rgba(150, 146, 140));
        const char* rows[4] = {"Create database", "To-do list", "Toggle list", "Heading 2"};
        for (int i = 0; i < 4; ++i) {
            const double ry = my + 128 + i * 92;
            if (i == 0) {
                c.setFillStyle(BLRgba32(241, 241, 239, 255));
                c.fillRoundRect(BLRoundRect(mx + 28, ry - 14, 704, 78, 18, 18));
            }
            fillText(c, face("reg", 46), mx + 64, ry + 40, rows[i], rgba(74, 74, 72));
            fillText(c, face("play", 34), mx + 640, ry + 38, i == 0 ? "go" : "block", rgba(160, 158, 154));
        }
    }

    if (me > 0.5) {
        const double cp = easeInOutCubic(wind(t, 0.62, 0.92));
        pointer(c, lerp(2560, mx + 380, cp), lerp(1880, my + 210, cp), "", kBlue, 1.0, clamp01(me * 2.0));
    }
}

// ------------------------------------------------------------------ 03 -- //
// Notion to-do list: checkboxes tick through in sequence.
static void s03(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .5, .47}, t);
    c.setFillStyle(kPageC); c.fillRect(0, 0, kW, kH);

    const double x0 = 560;
    fillText(c, face("bold", 84), x0, 430, "Launch checklist", rgba(23, 23, 23));

    const char* items[4] = {"Record planning demo", "Fix legend contrast issue",
                            "Coordinate with the PA", "Final mix sign-off"};
    for (int i = 0; i < 4; ++i) {
        const double y = 640 + i * 150;
        const double rxc = x0 + 26, ryc = y - 26 + 46;  // ring center of the checkbox row
        c.setFillStyle(BLRgba32(240, 239, 237, 255)); c.fillCircle(BLCircle(rxc, ryc, 26));
        c.setFillStyle(kPageC); c.fillCircle(BLCircle(rxc, ryc, 21));
        fillText(c, face("reg", 60), rxc + 70, y, items[i], rgba(63, 62, 59));

        const double st = 0.12 + double(i) * 0.16;
        checkMark(c, rxc, ryc, 40, clamp01((t - st) / 0.12), rgba(23, 23, 23), 9);
        const double sp = easeInOutCubic(wind(t, st + 0.05, st + 0.14));
        if (sp > 0.004) {
            const BLFont fi = face("reg", 60);
            c.setFillStyle(BLRgba32(185, 185, 182, 255));
            c.fillRect(BLRect(rxc + 70, y - 18, textW(fi, items[i]) * sp, 5));
        }
    }
}

// ------------------------------------------------------------------ 04 -- //
// Gradient presentation hero with per-word reveal (serif display).
static void s04(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.06, 1.0, .5, .47}, t);
    fillGrad(c, 0, 0, kW, kH, BLRgba32(255, 233, 216, 255), BLRgba32(255, 247, 238, 255));

    const double hx = lerp(640.0, 1900.0, easeInOutCubic(t));
    const double hy = 760 + 60 * std::sin(t * 4.2);
    BLGradientStop warm[2] = {{0.0, BLRgba32(246, 198, 164, 190)}, {1.0, BLRgba32(246, 198, 164, 0)}};
    BLRadialGradientValues rw(hx, hy, hx, hy, 0.0, 1000.0);
    BLGradient gw(rw, BL_EXTEND_MODE_PAD, warm, 2);
    c.setFillStyle(gw); c.fillRect(0, 0, kW, kH);
    BLGradientStop coolS[2] = {{0.0, BLRgba32(231, 217, 247, 170)}, {1.0, BLRgba32(231, 217, 247, 0)}};
    BLRadialGradientValues cw(kW - hx, kH - hy, kW - hx, kH - hy, 0.0, 1100.0);
    BLGradient gc(cw, BL_EXTEND_MODE_PAD, coolS, 2);
    c.setFillStyle(gc); c.fillRect(0, 0, kW, kH);

    const BLFont meas = face("serifBold", 320);
    const double w1 = textW(meas, "Design");
    const double space = 56.0;
    const double total = w1 + space + textW(meas, "faster.");
    const double x0 = (kW - total) * .5;
    const double e1 = easeInOutCubic(wind(t, 0.05, 0.30));
    const double e2 = easeInOutCubic(wind(t, 0.20, 0.46));
    fillText(c, meas, x0, 1080 - (1 - e1) * 50, "Design", rgba(32, 30, 28), e1);
    fillText(c, meas, x0 + w1 + space, 1080 - (1 - e2) * 50, "faster.", rgba(32, 30, 28), e2);

    textC(c, face("reg", 64), kW * .5, 1300, "Presentation feel for native UI shots",
          rgba(111, 106, 100), wind(t, 0.45, 0.75));

    const double pa = clamp01(wind(t, 0.55, 0.8));
    pill(c, 160, 180, 760, 96, BLRgba32(255, 255, 255, 140), pa);
    fillText(c, face("semi", 44), 200, 244, "FIELD GUIDE 01", rgba(90, 86, 79), pa);
    fillText(c, face("med", 40), 160, 1980, "ChrononTemplate pack v1", rgba(110, 107, 102), 1.0);
}

// ------------------------------------------------------------------ 05 -- //
// Auto-layout frame assembles, Figma spec annotations fade in.
static void s05(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .48, .47}, t);
    c.setFillStyle(BLRgba32(44, 44, 46, 255)); c.fillRect(0, 0, kW, kH);
    lineGrid(c, 128, BLRgba32(255, 255, 255, 12));

    c.setFillStyle(BLRgba32(79, 163, 247, 255)); c.fillRect(BLRect(1260, 444, 30, 30));
    fillText(c, face("med", 48), 1310, 476, "Hero / Auto-layout", BLRgba32(140, 180, 235, 255));

    c.setFillStyle(BLRgba32(53, 53, 55, 255));
    c.fillRoundRect(BLRoundRect(1260, 560, 1360, 950, 16, 16));
    c.setStrokeStyle(BLRgba32(0, 153, 255, 230)); c.setStrokeWidth(6);
    c.strokeRect(BLRect(1260, 560, 1360, 950));

    auto block = [&](double bx, double by, double bw, double bh, double sp) {
        if (sp <= 0.004) return;
        c.save(); c.setGlobalAlpha(float(sp));
        c.setFillStyle(BLRgba32(64, 64, 68, 255));
        c.fillRoundRect(BLRoundRect(bx, by + (1 - sp) * 52, bw, bh, 18, 18));
        c.restore();
    };
    const double hp = easeInOutCubic(wind(t, 0.04, 0.20));
    block(1310, 620, 1260, 190, hp);
    if (hp > 0.004) {
        c.save(); c.setGlobalAlpha(float(hp));
        c.setFillStyle(BLRgba32(112, 112, 118, 255)); c.fillCircle(BLCircle(1370, 715, 42));
        c.setFillStyle(BLRgba32(88, 88, 92, 255)); c.fillRoundRect(BLRoundRect(1440, 686, 420, 26, 13, 13));
        c.setFillStyle(BLRgba32(78, 78, 82, 255)); c.fillRoundRect(BLRoundRect(1440, 730, 640, 44, 12, 12));
        c.restore();
    }
    const double c1 = easeInOutCubic(wind(t, 0.18, 0.34));
    const double c2 = easeInOutCubic(wind(t, 0.24, 0.40));
    block(1310, 950, 600, 500, c1);
    block(1970, 950, 600, 500, c2);
    for (int i = 0; i < 2; ++i) {
        const double cp = i == 0 ? c1 : c2;
        if (cp <= 0.004) continue;
        c.save(); c.setGlobalAlpha(float(cp));
        const double bx = i == 0 ? 1310 : 1970, by = 950 + (1 - cp) * 40;
        c.setFillStyle(BLRgba32(90, 90, 95, 255)); c.fillCircle(BLCircle(bx + 78, by + 170, 44));
        c.setFillStyle(BLRgba32(76, 76, 80, 255)); c.fillRoundRect(BLRoundRect(bx + 60, by + 260, 460, 30, 15, 15));
        c.setFillStyle(BLRgba32(68, 68, 72, 255)); c.fillRoundRect(BLRoundRect(bx + 60, by + 320, 340, 30, 15, 15));
        c.setFillStyle(BLRgba32(60, 60, 64, 255)); c.fillRoundRect(BLRoundRect(bx + 60, by + 380, 480, 56, 14, 14));
        c.restore();
    }

    const double se = clamp01(wind(t, 0.55, 0.75));
    if (se > 0.004) {
        c.save(); c.setGlobalAlpha(float(se));
        c.setStrokeStyle(BLRgba32(255, 82, 82, 255)); c.setStrokeWidth(5);
        c.strokeLine(BLPoint(1918, 818), BLPoint(1918, 944));
        fillText(c, face("play", 42), 1944, 892, "60", BLRgba32(255, 138, 138, 255));
        c.strokeLine(BLPoint(1264, 740), BLPoint(1306, 740));
        fillText(c, face("play", 42), 1268, 706, "50", BLRgba32(255, 138, 138, 255));
        c.strokeLine(BLPoint(2574, 1160), BLPoint(2616, 1160));
        fillText(c, face("play", 42), 2578, 1126, "42", BLRgba32(255, 138, 138, 255));
        c.restore();
    }

    if (t > 0.68) {
        const double cp = easeInOutCubic(wind(t, 0.68, 1.0));
        pointer(c, lerp(3320, 2140, cp), lerp(1620, 1120, cp), "Simona", kGreenC, 1.0);
    }
}

// ------------------------------------------------------------------ 06 -- //
// Editorial serif callout card (Notion quote block).
static void s06(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.03, 1.06, .5, .47}, t);
    c.setFillStyle(kCream); c.fillRect(0, 0, kW, kH);

    textC(c, face("semi", 44), kW * .5, 330, "FROM THE JOURNAL - ISSUE 04", rgba(154, 150, 145),
          clamp01(wind(t, 0.0, 0.2)));
    textC(c, face("serifBold", 150), kW * .5, 520, "The craft of the quiet interface",
          rgba(35, 33, 30), clamp01(wind(t, 0.05, 0.3)));
    c.setFillStyle(BLRgba32(35, 33, 30, 255));
    c.fillRect(BLRect(kW * .5 - 150, 590, 300, 6));

    const double pop = easeInOutCubic(wind(t, 0.08, 0.30));
    if (pop > 0.004) {
        c.save(); c.setGlobalAlpha(float(pop));
        softShadow(c, 820, 1120 + (1 - pop) * 40, 2200, 440, 30, 30, 56, 50);
        c.setFillStyle(BLRgba32(251, 239, 203, 255));
        c.fillRoundRect(BLRoundRect(820, 1120 + (1 - pop) * 40, 2200, 440, 32, 32));
        c.setFillStyle(BLRgba32(227, 198, 77, 255));
        c.fillRect(BLRect(838, 1150, 12, 380 * clamp01(wind(t, 0.1, 0.34))));
        c.setFillStyle(BLRgba32(227, 198, 77, 255)); c.fillCircle(BLCircle(950, 1340, 46));
        c.setFillStyle(kPageC);
        BLPath star;
        star.moveTo(950, 1318); star.lineTo(972, 1340); star.lineTo(950, 1362); star.lineTo(928, 1340);
        star.close(); c.fillPath(star);
        c.restore();
    }

    const BLFont fq = face("serifMedIt", 92);
    fillText(c, fq, 1020, 1300, typed("Make the canvas feel invisible -", wind(t, 0.18, 0.52)),
             rgba(58, 54, 46));
    fillText(c, fq, 1020, 1420, typed("then the work becomes the hero.", wind(t, 0.42, 0.76)),
             rgba(58, 54, 46));
    fillText(c, face("reg", 46), 1020, 1680, "- Inside the Craft, ch. 4", rgba(138, 133, 126),
             clamp01(wind(t, 0.6, 0.85)));
}

// ------------------------------------------------------------------ 07 -- //
// Marquee select + multiplayer drag on a light canvas.
static void s07(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .5, .48}, t);
    c.setFillStyle(BLRgba32(247, 247, 248, 255)); c.fillRect(0, 0, kW, kH);
    lineGrid(c, 112, BLRgba32(0, 0, 0, 16));

    card(c, 940, 640, 480, 340, 24, BLRgba32(220, 233, 253, 255));
    card(c, 1480, 1260, 560, 260, 24, BLRgba32(217, 243, 228, 255));

    const double mp = easeInOutCubic(wind(t, 0.55, 0.88));
    const double ocx = 2020, ocy = 860;
    const double ncx = lerp(ocx, 2400.0, mp), ncy = lerp(ocy, 600.0, mp);
    if (mp > 0.004) {
        c.save(); c.setGlobalAlpha(float(0.30));
        c.setFillStyle(BLRgba32(246, 217, 180, 255)); c.fillCircle(BLCircle(ocx, ocy, 144));
        c.restore();
    }
    c.setFillStyle(BLRgba32(246, 217, 180, 255)); c.fillCircle(BLCircle(ncx, ncy, 144));

    const double sel = easeInOutCubic(wind(t, 0.36, 0.52));
    handles(c, 940 - 16, 640 - 16, 480 + 32, 340 + 32, sel, kFigmaBlue);
    handles(c, 1480 - 16, 1260 - 16, 560 + 32, 260 + 32, sel, kFigmaBlue);
    if (mp > 0.004) handles(c, ncx - 160, ncy - 160, 320, 320, mp, kFigmaBlue);

    const double mt = easeInOutCubic(wind(t, 0.02, 0.34));
    const double mx0 = 860, my0 = 500, mw = (2640 - 860) * mt, mh = (1160 - 500) * mt;
    if (mw > 4 && mh > 4) {
        c.setFillStyle(BLRgba32(47, 107, 255, 34)); c.fillRect(BLRect(mx0, my0, mw, mh));
        c.setStrokeStyle(BLRgba32(47, 107, 255, 165)); c.setStrokeWidth(5);
        c.strokeRect(BLRect(mx0, my0, mw, mh));
    }

    if (t > 0.46) {
        const double qp = easeInOutCubic(wind(t, 0.46, 0.66));
        pointer(c, lerp(640, ncx + 32, qp), lerp(430, ncy + 40, qp), "Maya", kOrangeC, 1.0);
    }
    const double up = easeInOutCubic(wind(t, 0.0, 0.4));
    pointer(c, lerp(3140, 2320, up), lerp(1740, 960, up), "You", kBlue, 1.0);
}

// ------------------------------------------------------------------ 08 -- //
// Design-token palette window with staggered swatches + copy ring.
static void s08(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.03, 1.05, .5, .47}, t);
    c.setFillStyle(kDeep); c.fillRect(0, 0, kW, kH);

    const double wx = 720, wy = 320, ww = 2400, wh = 1460;
    softShadow(c, wx, wy, ww, wh, 36, 44, 72, 60);
    card(c, wx, wy, ww, wh, 30, BLRgba32(22, 27, 34, 255));
    const uint32_t traffic[3] = {0xFFFF5F57, 0xFFFEBC2E, 0xFF28C840};
    for (int i = 0; i < 3; ++i) {
        c.setFillStyle(BLRgba32(uint8_t(traffic[i] >> 16), uint8_t(traffic[i] >> 8), uint8_t(traffic[i]), 255));
        c.fillCircle(BLCircle(wx + 52 + i * 50, wy + 62, 15));
    }
    textC(c, face("med", 42), kW * .5, wy + 76, "palette.json - design tokens", rgba(174, 184, 196));
    fillText(c, face("reg", 34), wx + 52, wy + 168, "6 swatches exported as CSS custom properties",
             rgba(110, 122, 139));
    c.setFillStyle(BLRgba32(34, 39, 47, 255)); c.fillRect(BLRect(wx, wy + 208, ww, 2));

    static const uint32_t cols[6] = {0xFF0FA958, 0xFFF5A623, 0xFF2A7BFF, 0xFF9F4BE0, 0xFFF22F6E, 0xFF20C4CB};
    static const char* names[6] = {"moss 500", "amber 500", "indigo 500", "violet 500", "rose 500", "teal 500"};
    static const char* hexes[6] = {"#0FA958", "#F5A623", "#2A7BFF", "#9F4BE0", "#F22F6E", "#20C4CB"};
    const double x0 = wx + 52, sw = 340, gap = 51;

    for (int i = 0; i < 6; ++i) {
        const double sp = easeInOutCubic(wind(t, 0.08 + i * 0.055, 0.26 + i * 0.055));
        const double cx = x0 + double(i) * (sw + gap) + sw * .5;
        if (sp > 0.004) {
            c.save(); c.setGlobalAlpha(float(sp));
            c.setFillStyle(BLRgba32(uint8_t(cols[i] >> 16), uint8_t(cols[i] >> 8), uint8_t(cols[i]), 255));
            c.fillRoundRect(BLRoundRect(cx - sw * .5 * sp, 770 - sw * .5 * sp, sw * sp, sw * sp, 24 * sp, 24 * sp));
            c.restore();
        }
        textC(c, face("semi", 40), cx, 1000, names[i], rgba(215, 222, 231), clamp01(sp));
        textC(c, face("play", 34), cx, 1070, typed(hexes[i], wind(t, 0.5 + i * 0.06, 0.66 + i * 0.06)),
              rgba(125, 140, 163));
    }
    // selected copy ring on the teal swatch
    const double se = clamp01(wind(t, 0.84, 1.0));
    if (se > 0.004) {
        const double cx = x0 + 5 * (sw + gap) + sw * .5;
        c.save(); c.setGlobalAlpha(float(se));
        c.setStrokeStyle(kPageC); c.setStrokeWidth(8);
        c.strokeRoundRect(BLRoundRect(cx - sw * .5 - 16, 754, sw + 32, sw + 32, 30, 30));
        c.setFillStyle(kPageC); c.fillCircle(BLCircle(cx + sw * .5 - 8, 762, 52));
        c.restore();
        checkMark(c, cx + sw * .5 - 8, 762, 44, se, kFigmaBlue, 10);
        textC(c, face("reg", 36), kW * .5, wy + wh - 70, "click to copy", rgba(110, 122, 139), se);
    }
    if (t > 0.5) {
        const double cp = easeInOutCubic(wind(t, 0.55, 0.88));
        pointer(c, lerp(3420, x0 + 5 * (sw + gap) + sw - 30, cp), lerp(2020, 700, cp), "", kVioletC, 1.0);
    }
}

// ------------------------------------------------------------------ 09 -- //
// Zoom-to-fit: the canvas pulls back from 220% into frame.
static void s09(BLContext& c, double t, int fr) {
    (void)fr;
    c.setFillStyle(kInkBg); c.fillRect(0, 0, kW, kH);
    dotGrid(c, 64, BLRgba32(255, 255, 255, 14), 2.6);

    const double s = 2.2 - 1.2 * easeInOutCubic(clamp01(t / 0.8));
    c.save();
    c.translate(1920, 1080); c.scale(s, s); c.translate(-1920, -1080);
    softShadow(c, 1400, 660, 1040, 640, 26);
    card(c, 1400, 660, 1040, 640, 26, kPageC);
    fillText(c, face("bold", 62), 1470, 762, "checkout - v2", rgba(23, 23, 27));
    c.setFillStyle(BLRgba32(231, 231, 234, 255));
    c.fillRoundRect(BLRoundRect(1470, 820, 700, 34, 17, 17));
    c.fillRoundRect(BLRoundRect(1470, 884, 520, 34, 17, 17));
    c.setFillStyle(BLRgba32(238, 241, 244, 255));
    c.fillRoundRect(BLRoundRect(1470, 980, 900, 250, 20, 20));
    c.setFillStyle(BLRgba32(205, 215, 226, 255)); c.fillCircle(BLCircle(1920, 1105, 64));
    c.restore();

    std::ostringstream zz; zz << int(std::lround(s * 100)) << "%";
    textC(c, face("semi", 48), 260, 180, zz.str(), rgba(140, 143, 148));

    const double pe = clamp01(wind(t, 0.52, 0.76));
    if (pe > 0.004) {
        pill(c, 1420, 1940 - (1 - pe) * 60, 1020, 130, BLRgba32(75, 76, 79, 205), pe);
        textC(c, face("med", 48), 1930, 2016 - (1 - pe) * 60, "zoom to fit - shift 1", kPageC, pe);
    }
}

// ------------------------------------------------------------------ 10 -- //
// Notion toggle block expanding with children.
static void s10(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .46, .46}, t);
    c.setFillStyle(kPageC); c.fillRect(0, 0, kW, kH);
    const double x0 = 600;
    fillText(c, face("bold", 80), x0, 400, "Product overview", rgba(55, 53, 47));
    c.setFillStyle(BLRgba32(239, 238, 236, 255)); c.fillRect(BLRect(x0, 700, 2640, 2));

    caretTriangle(c, x0 + 14, 596, 44, t, rgba(123, 122, 118));
    fillText(c, face("semi", 60), x0 + 100, 620, "Roadmap Q4", rgba(55, 53, 47));

    const BLFont frow = face("semi", 60);
    const double hintx = x0 + 100 + textW(frow, "Roadmap Q4") + 60;
    const double ha = 1.0 - clamp01(wind(t, 0.30, 0.55));
    if (ha > 0.004) {
        const BLFont fh = face("reg", 40);
        const double hw = textW(fh, "toggle open") + 64;
        pill(c, hintx, 570, hw, 88, BLRgba32(242, 241, 239, 255), ha);
        fillText(c, fh, hintx + 32, 614, "toggle open", rgba(180, 178, 174), ha);
    }

    static const char* kids[3] = {"Board view freezes under load", "Component library audit",
                                  "Latency budget ledger"};
    for (int i = 0; i < 3; ++i) {
        const double p = easeInOutCubic(wind(t, 0.24 + i * 0.09, 0.46 + i * 0.09));
        if (p <= 0.004) continue;
        c.save(); c.setGlobalAlpha(float(p));
        const double yy = 860 + i * 130 - (1 - p) * 28;
        c.setFillStyle(BLRgba32(201, 199, 196, 255)); c.fillCircle(BLCircle(x0 + 150, yy - 16, 12));
        fillText(c, face("reg", 48), x0 + 200, yy, kids[i], rgba(92, 91, 88));
        c.restore();
    }
}

// ------------------------------------------------------------------ 11 -- //
// Kanban: card lifted from column A and dragged into column B.
static void s11(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.03, 1.05, .5, .47}, t);
    c.setFillStyle(BLRgba32(251, 251, 249, 255)); c.fillRect(0, 0, kW, kH);

    auto head = [&](double hx, const char* label, const char* count) {
        card(c, hx, 360, 1280, 130, 26, BLRgba32(241, 241, 239, 255));
        fillText(c, face("semi", 52), hx + 72, 444, label, rgba(55, 53, 47));
        textC(c, face("med", 48), hx + 1280 - 84, 442, count, rgba(155, 154, 150));
    };
    head(560, "To do", "3");
    head(2000, "In progress", "2");

    auto greycard = [&](double gx, double gy, const char* label, uint32_t tag) {
        softShadow(c, gx, gy, 1280, 240, 24, 26, 34, 46);
        card(c, gx, gy, 1280, 240, 24, kPageC);
        c.setFillStyle(BLRgba32(uint8_t(tag >> 16), uint8_t(tag >> 8), uint8_t(tag), 255));
        c.fillRect(BLRect(gx + 24, gy + 44, 14, 152));
        fillText(c, face("med", 52), gx + 92, gy + 116, label, rgba(38, 37, 34));
    };
    greycard(560, 560, "Polish empty states", 0xFF0C59E8);
    greycard(560, 1072, "CSP headers review", 0xFF54A30F);
    greycard(2000, 560, "Motion tokens sweep", 0xFFE04B9F);
    greycard(2000, 816, "Fit logic rework", 0xFFCBC420);

    // moving card "Icon set v2" is fully owned by the anim pass
    double px = 560, py = 816;
    const double lift = wind(t, 0.10, 0.26);
    double shadowGrow = lift;
    if (t > 0.26) {
        const double tv = easeInOutCubic(wind(t, 0.28, 0.62));
        px = lerp(560, 2000, tv);
        py = lerp(816 - 20, 1072, tv);
        shadowGrow = lift * (1 - wind(t, 0.62, 0.75));
    }
    softShadow(c, px, py, 1280, 240, 24, 26 + 34 * shadowGrow, 34 + 52 * shadowGrow,
               int(46 + 60 * shadowGrow));
    card(c, px, py, 1280, 240, 24, kPageC);
    c.setFillStyle(BLRgba32(42, 123, 255, 255));
    c.fillRect(BLRect(px + 24, py + 44, 14, 152));
    fillText(c, face("med", 52), px + 92, py + 116, "Icon set v2", rgba(38, 37, 34));
    if (t > 0.26) dashedRect(c, 2000, 1072, 1280, 240, BLRgba32(201, 199, 195, 200));
    pointer(c, px + 74, py - 34, "You", kBlue, 1.0);
}

// ------------------------------------------------------------------ 12 -- //
// Heading transform: H1 shrinks while the "turn into" menu opens.
static void s12(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .48, .46}, t);
    c.setFillStyle(kPaper); c.fillRect(0, 0, kW, kH);

    const double p = easeInOutCubic(wind(t, 0.20, 0.55));
    const BLFont fh = face("black", lerp(192, 116, p));
    fillText(c, fh, 600, lerp(520, 560, p), "The one-file forecast", rgba(43, 42, 39));

    fillText(c, face("reg", 56), 1560, 1010, "written to be printed and pinned, then", rgba(86, 83, 77));
    fillText(c, face("reg", 56), 1448, 1096, "duplicated once a week.", rgba(86, 83, 77));

    const double me = easeInOutCubic(wind(t, 0.58, 0.72));
    if (me > 0.004) {
        const double hx = 700, hy = 640 - (1 - me) * 40;
        softShadow(c, hx, hy, 660, 560, 28, 26, 44, 44);
        card(c, hx, hy, 660, 560, 28, kPageC, false, BLRgba32(0, 0, 0, 22));
        fillText(c, face("semi", 36), hx + 44, hy + 74, "turn into", rgba(150, 146, 140));
        fillText(c, face("reg", 52), hx + 52, hy + 190, "Text", rgba(55, 53, 47));
        fillText(c, face("bold", 54), hx + 52, hy + 310, "Heading 1", rgba(55, 53, 47));
        fillText(c, face("semi", 50), hx + 52, hy + 420, "Heading 2", rgba(55, 53, 47));
        const double ho = clamp01(wind(t, 0.80, 0.95));
        if (ho > 0.004) {
            c.save(); c.setGlobalAlpha(float(ho));
            c.setFillStyle(BLRgba32(241, 241, 239, 255));
            c.fillRoundRect(BLRoundRect(hx + 22, hy + 452, 616, 88, 16, 16));
            c.restore();
        }
        fillText(c, face("semi", 46), hx + 52, hy + 526, "Heading 3", rgba(55, 53, 47));
        const double cp = easeInOutCubic(wind(t, 0.55, 0.85));
        pointer(c, lerp(2980, hx + 420, cp), lerp(1700, hy + 470, cp), "", kGreenC, 1.0);
    }
    fillText(c, face("light", 40), 600, 1900, "type ahead - motion pack 03", rgba(162, 156, 147));
}

// ------------------------------------------------------------------ 13 -- //
// Multiplayer cursors converge; a chat bubble pops near one of them.
static void s13(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.03, 1.05, .5, .48}, t);
    fillGrad(c, 0, 0, kW, kH, BLRgba32(253, 234, 224, 255), BLRgba32(243, 244, 248, 255), false);
    fillText(c, face("med", 44), 240, 210, "review - motion pack", rgba(139, 133, 126));

    const double up = easeInOutCubic(wind(t, 0.0, 0.40));
    pointer(c, lerp(600, 1700, up), lerp(1880, 960, up), "You", kBlue, 1.0);
    const double mpX = lerp(3560, 2420, easeInOutCubic(wind(t, 0.10, 0.50)));
    const double mpY = lerp(480, 784, easeInOutCubic(wind(t, 0.10, 0.50)));
    pointer(c, mpX, mpY, "Maya", kOrangeC, 1.0);
    pointer(c, lerp(480, 1960, easeInOutCubic(wind(t, 0.20, 0.70))),
            lerp(520, 1280, easeInOutCubic(wind(t, 0.20, 0.70))), "Priya", kGreenC,
            1.0, clamp01(wind(t, 0.20, 0.4)));

    const double pop = easeInOutCubic(wind(t, 0.60, 0.74));
    if (pop > 0.004) {
        const double bx = 2452, by = 470 - (1 - pop) * 40;
        const BLFont fb = face("semi", 52);
        const string msg = typed("Ship it faster.", wind(t, 0.60, 0.86));
        const double bw = (textW(fb, "Ship it faster.") + 120) * easeOutCubic(wind(t, 0.60, 0.68));
        softShadow(c, bx, by, bw, 130, 26, 22, 30, 60);
        c.save(); c.setGlobalAlpha(float(clamp01(pop)));
        c.setFillStyle(BLRgba32(255, 255, 255, 240));
        c.fillRoundRect(BLRoundRect(bx, by, bw, 130, 28, 28));
        BLPath tail; tail.moveTo(bx + 26, by + 130); tail.lineTo(bx - 12, by + 214); tail.lineTo(bx + 96, by + 130);
        tail.close(); c.fillPath(tail);
        fillText(c, fb, bx + 60, by + 86, msg, rgba(31, 29, 27));
        c.restore();
    }
}

// ------------------------------------------------------------------ 14 -- //
// Kinetic poster: huge impact lines + mono stat chips.
static void s14(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.05, 1.0, .5, .48}, t);
    c.setFillStyle(kNight); c.fillRect(0, 0, kW, kH);
    dotGrid(c, 68, BLRgba32(255, 255, 255, 14), 2.4);

    const double p1 = easeInOutCubic(wind(t, 0.05, 0.28));
    const double p2 = easeInOutCubic(wind(t, 0.17, 0.40));
    fillText(c, face("impact", 300), 190, 800 - (1 - p1) * 90, "STOP SUGARCOATING", kPageC, p1);
    fillText(c, face("impact", 300), 190, 1230 - (1 - p2) * 90, "LATENCY, NOT VIBES.", kPageC, p2);
    if (p1 > 0.98) {
        const double sw = easeInOutCubic(wind(t, 0.55, 0.78));
        c.setFillStyle(kBlue); c.fillRect(BLRect(190, 1276, 430 * sw, 16));
    }
    fillText(c, face("reg", 64), 190, 1500, "Design the budget first - then hold ship dates to it.",
             rgba(155, 160, 168), clamp01(wind(t, 0.42, 0.7)));

    static const char* chips[3] = {"p95 142ms", "budget 120ms", "delta +18%"};
    for (int i = 0; i < 3; ++i) {
        const double a = clamp01(wind(t, 0.62 + i * 0.06, 0.74 + i * 0.06));
        if (a <= 0.004) continue;
        const double x = 190 + i * 640;
        c.save(); c.setGlobalAlpha(float(a));
        c.setStrokeStyle(BLRgba32(70, 74, 84, 255)); c.setStrokeWidth(5);
        c.strokeRoundRect(BLRoundRect(x, 1740, 500, 130, 65, 65));
        const BLRgba32 cc = i == 2 ? BLRgba32(242, 201, 76, 255) : BLRgba32(159, 167, 179, 255);
        textC(c, face("play", 52), x + 250, 1824, chips[i], cc);
        c.restore();
    }
}

// ------------------------------------------------------------------ 15 -- //
// Notion database table rows cascading in.
static void s15(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .48, .47}, t);
    c.setFillStyle(kPageC); c.fillRect(0, 0, kW, kH);

    const double x0 = 600;
    fillText(c, face("bold", 68), x0, 280, "Shipping tracker", rgba(31, 30, 27));
    static const char* tabs[3] = {"Table", "Board", "Calendar"};
    const double tab0w = textW(face("reg", 42), tabs[0]);
    for (int i = 0; i < 3; ++i) {
        const double tx = x0 + (i == 0 ? 0 : tab0w + 290 + (i - 1) * 250);
        if (i == 0) {
            c.setFillStyle(BLRgba32(239, 239, 237, 255));
            c.fillRoundRect(BLRoundRect(tx - 24, 356, tab0w + 48, 92, 46, 46));
        }
        fillText(c, face("reg", 42), tx, 424, tabs[i], i == 0 ? rgba(76, 75, 72) : rgba(160, 159, 156));
    }

    fillText(c, face("semi", 40), x0, 606, "name", rgba(110, 109, 106));
    fillText(c, face("semi", 40), 1760, 606, "status", rgba(110, 109, 106));
    fillText(c, face("semi", 40), 2160, 606, "owner", rgba(110, 109, 106));
    fillText(c, face("semi", 40), 2640, 606, "due", rgba(110, 109, 106));
    c.setFillStyle(BLRgba32(231, 230, 227, 255)); c.fillRect(BLRect(x0, 650, 2460, 2));

    static const char* names[5] = {"Empty-state pass", "Legend contrast fix", "PA coordination",
                                   "Mix sign-off", "Loudness pass"};
    static const int stt[5] = {0, 1, 1, 2, 2};           // 0 done, 1 in progress, 2 to-do
    static const uint32_t ownC[5] = {0xFF2A7BFF, 0xFF9F4BE0, 0xFF0FA958, 0xFFF5A623, 0xFFF22F6E};
    static const char* initials[5] = {"AZ", "TM", "JV", "SC", "RD"};
    static const char* dues[5] = {"Oct 29", "Oct 30", "Nov 02", "Nov 05", "Nov 07"};

    for (int i = 0; i < 5; ++i) {
        const double p = easeInOutCubic(wind(t, 0.08 + i * 0.10, 0.30 + i * 0.10));
        if (p <= 0.004) continue;
        const double y = 800 + i * 168 - (1 - p) * 40;
        c.save(); c.setGlobalAlpha(float(p));
        c.setFillStyle(kPageC); c.fillRoundRect(BLRoundRect(x0, y - 44, 44, 44, 10, 10));
        c.setStrokeStyle(BLRgba32(197, 195, 191, 255));
        c.setStrokeWidth(5); c.strokeRoundRect(BLRoundRect(x0, y - 44, 44, 44, 10, 10));
        if (i == 0) {
            c.setFillStyle(kFigmaBlue); c.fillRoundRect(BLRoundRect(x0, y - 44, 44, 44, 10, 10));
            checkMark(c, x0 + 22, y - 20, 30, 1.0, kPageC, 7);
        }
        fillText(c, face("reg", 48), x0 + 96, y, names[i], rgba(51, 50, 47));
        const double sp = easeOutCubic(clamp01((t - (0.14 + i * 0.10)) / 0.12));
        const double pillX = 1800, pillY = y - 16;
        if (stt[i] == 0) statusPill(c, pillX, pillY, "Done", sp, BLRgba32(219, 237, 219, 255), BLRgba32(32, 128, 63, 255), 0.9);
        if (stt[i] == 1) statusPill(c, pillX, pillY, "In progress", sp, BLRgba32(251, 240, 205, 255), BLRgba32(170, 127, 10, 255), 0.9);
        if (stt[i] == 2) statusPill(c, pillX, pillY, "To do", sp, BLRgba32(235, 234, 231, 255), BLRgba32(121, 120, 117, 255), 0.9);
        c.setFillStyle(BLRgba32(uint8_t(ownC[i] >> 16), uint8_t(ownC[i] >> 8), uint8_t(ownC[i]), 255));
        c.fillCircle(BLCircle(2188, y - 14, 40));
        textC(c, face("semi", 30), 2188, y - 4, initials[i], kPageC, 1.0);
        fillText(c, face("reg", 40), 2640, y, dues[i], rgba(140, 139, 136));
        if (i < 4) {
            c.setFillStyle(BLRgba32(237, 236, 234, uint8_t(255 * p)));
            c.fillRect(BLRect(x0, y + 96, 2460, 2));
        }
        c.restore();
    }
    if (t > 0.86) {
        const double cp = easeInOutCubic(wind(t, 0.86, 1.0));
        pointer(c, lerp(3200, 1520, cp), lerp(1900, 980, cp), "", kBlue, 1.0);
    }
}

// ---------------------------------------------------------------- runner -- //

static const Catalog kCatalog[15] = {
    {1, "01_card_select_cursor", "Figma dark canvas: cursor clicks the primary button, card gets a selection frame", 1.02, 1.06, .5, .49, 0.98, s01},
    {2, "02_slashmenu_typing", "Notion doc: typed edit after ** with blinking caret and slash-menu popup", 1.02, 1.05, .47, .48, 0.95, s02},
    {3, "03_todo_checks", "Notion to-do list: checkbox ticks cascade in with strikethrough sweeps", 1.02, 1.05, .5, .47, 0.98, s03},
    {4, "04_gradient_hero", "Presentation hero: serif display reveal on a drifting pastel gradient", 1.06, 1.0, .5, .47, 0.98, s04},
    {5, "05_autolayout_specs", "Auto-layout frame assembles while red measurement specs fade in", 1.02, 1.05, .48, .47, 0.95, s05},
    {6, "06_editorial_callout", "Editorial callout card: serif italic quote types under a gold accent bar", 1.03, 1.06, .5, .47, 0.97, s06},
    {7, "07_marquee_multiplayer", "Marquee select catches three shapes; a multiplayer cursor drags one away", 1.02, 1.05, .5, .48, 0.95, s07},
    {8, "08_token_swatches", "Design-token window: swatches stagger in, hex codes type out, copy ring lands", 1.03, 1.05, .5, .47, 0.98, s08},
    {9, "09_zoomtofit", "Canvas pulls back from 220% to frame with a zoom-to-fit pill", 1.0, 1.0, .5, .5, 0.95, s09},
    {10, "10_toggle_expand", "Notion toggle block: caret rotates, children cascade in, hint pill fades", 1.02, 1.05, .46, .46, 0.95, s10},
    {11, "11_kanban_drag", "Kanban board: card lifts with shadow and is dragged across columns into a slot", 1.03, 1.05, .5, .47, 0.98, s11},
    {12, "12_heading_menu", "Heading morphs from H1 while the turn-into menu opens and highlights Heading 3", 1.02, 1.05, .48, .46, 0.95, s12},
    {13, "13_cursor_bubble_chat", "Three multiplayer cursors converge and a chat bubble types near one", 1.03, 1.05, .5, .48, 0.95, s13},
    {14, "14_kinetic_impact", "Kinetic poster: huge Impact lines reveal with an underline sweep and mono chips", 1.05, 1.0, .5, .48, 0.92, s14},
    {15, "15_database_rows", "Database table rows cascade in with status pills, owner badges and due dates", 1.02, 1.05, .48, .47, 0.95, s15},
};

inline int runScene(const Catalog& sc, const string& outRoot, bool stillsOnly, bool keepFrames) {
    const string outDir = outRoot + "/" + sc.name;
    fs::create_directories(outDir + "/frames");
    const int n = 90;
    for (int i = 0; i < n; ++i) {
        const double t = double(i) / double(n - 1);
        BLImage img(kW / 2, kH / 2, BL_FORMAT_PRGB32);
        BLContext ctx(img);
        ctx.clearAll();
        ctx.scale(0.5);
        sc.draw(ctx, t, i);
        ctx.end();
        std::ostringstream path;
        path << outDir << "/frames/frame_" << std::setw(4) << std::setfill('0') << i << ".png";
        if (img.writeToFile(path.str().c_str()) != BL_SUCCESS) {
            std::cerr << "write failed: " << path.str() << std::endl;
            return 3;
        }
    }
    // hero still
    {
        BLImage img(kW / 2, kH / 2, BL_FORMAT_PRGB32);
        BLContext ctx(img);
        ctx.clearAll(); ctx.scale(0.5);
        sc.draw(ctx, sc.stillT, int(sc.stillT * (n - 1)));
        ctx.end();
        if (img.writeToFile((outDir + "/still.png").c_str()) != BL_SUCCESS) return 3;
    }
    if (stillsOnly) { fs::remove_all(outDir + "/frames"); std::cout << "[stills] " << sc.name << std::endl; return 0; }
    const string mp4 = outDir + "/" + sc.name + ".mp4";
    const string cmd = "ffmpeg -y -v error -framerate 30 -start_number 0 -i \"" + outDir +
                       "/frames/frame_%04d.png\" -c:v libx264 -pix_fmt yuv420p -crf 18 \"" + mp4 + "\"";
    if (std::system(cmd.c_str()) != 0) { std::cerr << "ffmpeg failed for " << sc.name << std::endl; return 4; }
    if (!keepFrames) fs::remove_all(outDir + "/frames");
    std::cout << "[render] " << sc.name << std::endl;
    return 0;
}

inline bool writeCollateral(const string& outRoot) {
    fs::create_directories(outRoot);
    const int cellW = 640, cellH = 360, labelH = 44, pad = 24;
    const int cols = 3, rows = 5;
    BLImage sheet(cols * cellW + pad * 2, rows * (cellH + labelH) + pad * 2, BL_FORMAT_PRGB32);
    BLContext ctx(sheet);
    ctx.clearAll();
    ctx.setFillStyle(BLRgba32(18, 18, 20, 255));
    ctx.fillRect(0, 0, kW, kH);   // over-filled; cropped by the bitmap
    for (int i = 0; i < 15; ++i) {
        BLImage still;
        if (still.readFromFile((outRoot + "/" + kCatalog[i].name + "/still.png").c_str()) != BL_SUCCESS) continue;
        const int cc = i % cols, rr = i / cols;
        ctx.blitImage(BLRect(pad + cc * cellW, pad + rr * (cellH + labelH), cellW, cellH), still);
        const BLFont lab = face("semi", 26);
        ctx.setFillStyle(BLRgba32(215, 215, 220, 255));
        ctx.fillUtf8Text(BLPoint(pad + cc * cellW + 8, pad + rr * (cellH + labelH) + cellH + 32),
                         lab, kCatalog[i].name, std::strlen(kCatalog[i].name));
    }
    ctx.end();
    sheet.writeToFile((outRoot + "/contact_sheet.png").c_str());

    json manifest;
    manifest["schema"] = "chronon.ui-shots-figma-notion.v1";
    manifest["pack"] = "ui_shots_figma_notion_v1";
    manifest["count"] = 15;
    manifest["deliver"] = {{"width", 1920}, {"height", 1080}, {"fps", 30}, {"seconds", 3.0}};
    manifest["source_policy"] = "native vector composition; no reference screenshot is loaded";
    json shots = json::array();
    for (const auto& sc : kCatalog) {
        json e;
        e["id"] = sc.id;
        e["shot"] = sc.name;
        e["description"] = sc.desc;
        e["seconds"] = 3.0; e["fps"] = 30; e["frames"] = 90;
        e["camera"] = {{"zoom_from", sc.z0}, {"zoom_to", sc.z1}, {"center", {sc.cx, sc.cy}}};
        e["still"] = string(sc.name) + "/still.png";
        e["clip"] = string(sc.name) + "/" + string(sc.name) + ".mp4";
        shots.push_back(e);
    }
    manifest["shots"] = shots;
    std::ofstream f(outRoot + "/manifest.json");
    f << manifest.dump(2) << std::endl;
    std::cout << "[collateral] contact_sheet.png + manifest.json -> " << outRoot << std::endl;
    return fs::exists(outRoot + "/manifest.json");
}

} // namespace chronon::uipack

int main(int argc, char** argv) {
    using namespace chronon::uipack;
    if (!fonts().valid) { std::cerr << "fonts missing" << std::endl; return 2; }
    string outRoot = kPackRoot;
    bool keepFrames = false, stillsOnly = false, wantCollateral = false;
    std::vector<int> ids;
    for (int i = 1; i < argc; ++i) {
        const string a = argv[i];
        if (a == "--keep-frames") keepFrames = true;
        else if (a == "--stills") stillsOnly = true;
        else if (a == "--out") { if (i + 1 < argc) outRoot = argv[++i]; }
        else if (a == "--collateral") wantCollateral = true;
        else ids.push_back(std::atoi(a.c_str()));
    }
    for (int id : ids) {
        if (id < 1 || id > 15) { std::cerr << "bad scene id " << id << std::endl; return 1; }
    }
    const bool all = ids.empty();
    for (const auto& sc : kCatalog) {
        if (!all && std::find(ids.begin(), ids.end(), sc.id) == ids.end()) continue;
        const int rc = runScene(sc, outRoot, stillsOnly, keepFrames);
        if (rc != 0) return rc;
    }
    if ((all && !stillsOnly) || wantCollateral) {
        writeCollateral(outRoot);
        return fs::exists(outRoot + "/manifest.json") ? 0 : 1;
    }
    return 0;
}
