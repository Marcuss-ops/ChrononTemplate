// web_yt_elegant.cpp — 15 native "elegant web" compositions for YouTube b-roll.
//
// The classic web_shots_rebuild style (articles, quotes, headlines, images)
// redrawn in the modern Figma/Notion look with Blend2D, in pure C++. Every
// pixel is vector geometry and native text; no reference asset is loaded.
//
// Renders to ChrononTemplate/artifacts/web_yt_elegant_v1/<scene>/:
//   frames/frame_####.png  still.png  <scene>.mp4
// plus contact_sheet.png and manifest.json at the pack root.
//
// Usage: web_yt_elegant.exe [--keep-frames] [--stills] [--out DIR] [scene ids...]

#include "../ui_shots_figma_notion/ui_pack.hpp"

#include <cmath>
#include <cctype>
#include <clocale>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace chrom {
using namespace chronon::uipack;
using std::string;
using std::clamp;

// ------------------------------------------------------------- palettes -- //
static const BLRgba32 kCream{244, 241, 234, 255};
static const BLRgba32 kPaper{250, 249, 246, 255};
static const BLRgba32 kWhite{252, 252, 251, 255};
static const BLRgba32 kInk{22, 22, 26, 255};
static const BLRgba32 kGrayTxt{122, 120, 114, 255};
static const BLRgba32 kDeep{16, 17, 22, 255};
static const BLRgba32 kNight{14, 15, 19, 255};
static const BLRgba32 kBlue{46, 102, 222, 255};
static const BLRgba32 kViolet{124, 96, 226, 255};
static const BLRgba32 kLavBar{214, 205, 247, 255};
static const BLRgba32 kGold{207, 158, 60, 255};
static const BLRgba32 kMarker{246, 214, 92, 255};      // highlighter yellow
static const BLRgba32 kRedC{212, 74, 66, 255};
static const BLRgba32 kGreenC{24, 148, 88, 255};
static const BLRgba32 kAmber{240, 178, 62, 255};

static const BLRgba32 kLineA{228, 225, 218, 255};       // skeleton lines on cream

// format with thousands separators
static string comma(long v) {
    string s = std::to_string(v);
    string out;
    int n = int(s.size());
    for (int i = 0; i < n; ++i) {
        out += s[size_t(i)];
        int rem = n - 1 - i;
        if (rem > 0 && rem % 3 == 0 && i != n - 1) out += ',';
    }
    return out;
}

// small uppercase eyebrow tag
static void tag(BLContext& c, double x, double y, const string& s, BLRgba32 col) {
    const BLFont f = face("semi", 44);
    const double w = textW(f, s) + 56.0;
    pill(c, x, y, w, 74, BLRgba32(255, 255, 255, 222));
    fillText(c, f, x + 28, y + 51, s, col);
}

static void lineWidth(BLContext& c, double x, double y, double w, BLRgba32 col, double h = 20.0) {
    c.setFillStyle(col); c.fillRect(BLRect(x, y, w, h));
}

// ------------------------------------------------------------ dispatch -- //
struct catalog_entry {
    int id; const char* name; const char* desc;
    double z0, z1, cx, cy, stillT;
    void (*draw)(BLContext&, double, int);
};

// forward decls used by later scenes
static BLRgba32 kInkText(double flip);
static BLRgba32 kLineDay(double flip, double alphaOnDark);
static double kWndW();

// ------------------------------------------------------------------ 01 -- //
// Browser window: classic article card, headline types in, reader arrives.
static void s01(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.03, 1.06, .5, .48}, t);
    c.setFillStyle(kCream); c.fillRect(0, 0, kW, kH);
    dotGrid(c, 76, BLRgba32(20, 20, 28, 14), 2.2);

    const double bx = 560, by = 340, bw = 2720, bh = 1500, r = 28;
    softShadow(c, bx, by, bw, bh, r, 40, 72, 44);
    card(c, bx, by, bw, bh, r, kWhite);
    // browser chrome
    c.setFillStyle(BLRgba32(237, 235, 231, 255)); c.fillRect(BLRect(bx, by, bw, 122));
    for (int i = 0; i < 3; ++i)
        c.setFillStyle(BLRgba32(186, 183, 177, 255)), c.fillCircle(BLCircle(bx + 84 + i * 84, by + 61, 22));
    card(c, bx + 360, by + 26, 1160, 70, 35, BLRgba32(247, 246, 243, 255));
    fillText(c, face("dejavu", 44), bx + 396, by + 71, "chrononledger.com/notes-on-speed", rgba(130, 128, 122));

    fillText(c, face("semi", 46), bx + 120, by + 320, "FIELD NOTE  ·  12 MIN READ", kGold);
    const BLFont fh = face("serifBold", 168);
    const string head = "The speed nobody noticed.";
    const double e = easeOutCubic(wind(t, 0.10, 0.52));
    fillText(c, fh, bx + 112, by + 560, typed(head, e), kInk);
    if (e < 1.0 && e > 0.0 && (fr % 22) < 13) {
        const double tx = bx + 112 + textW(fh, typed(head, e)) + 12;
        c.setFillStyle(kBlue); c.fillRect(BLRect(tx, by + 452, 12, 116));
    }
    fillText(c, face("reg", 52), bx + 116, by + 700, "By the Quiet Ledger desk  —  archive scan 47", kGrayTxt);
    // article skeleton
    lineWidth(c, bx + 112, by + 820, bw - 260, kLineA, 26);
    lineWidth(c, bx + 112, by + 914, bw - 620, kLineA, 26);
    lineWidth(c, bx + 112, by + 1008, bw - 420, kLineA, 26);

    pointer(c, lerp(3420.0, bx + 980, easeInOutCubic(wind(t, 0.30, 0.62))),
               lerp(2020.0, by + 1480, easeInOutCubic(wind(t, 0.30, 0.62))), "", BLRgba32(0), 0.9);
}

// ------------------------------------------------------------------ 02 -- //
// Editorial pull-quote: serif italic lines rise one by one, gold bar.
static void s02(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.06, .5, .48}, t);
    c.setFillStyle(kPaper); c.fillRect(0, 0, kW, kH);

    const BLFont fqM = face("serif", 520);
    fillText(c, fqM, 300, 1060, "\"", rgba(207, 158, 60, 90));
    fillText(c, fqM, 3260, 2140, "\"", rgba(207, 158, 60, 70));

    const BLFont fq = face("serifMedIt", 148);
    const char* rows[3] = {"The joke was that the truth", "arrived first, and the internet", "come to bury it showed up late."};
    const double xq = 760, yq = 840;
    for (int i = 0; i < 3; ++i) {
        const double e = easeOutCubic(wind(t, 0.10 + i * 0.14, 0.34 + i * 0.14));
        c.save(); c.setGlobalAlpha(float(e));
        fillText(c, fq, xq, yq + i * 250 + (1 - e) * 60, rows[i], rgba(38, 36, 33));
        c.restore();
    }

    const double eBar = easeOutCubic(wind(t, 0.04, 0.24));
    c.setFillStyle(kGold); c.fillRect(BLRect(660, yq - 190, 16 * eBar, 3 * 250 + 130));

    const double eC = easeOutCubic(wind(t, 0.58, 0.80));
    c.save(); c.setGlobalAlpha(float(eC));
    fillText(c, face("semi", 52), 768, yq + 940, "\u2014 Quiet Ledger, evening edition", kGrayTxt);
    c.restore();

    tag(c, 660, 340, "PULL QUOTE  ·  DRAFT 3", rgba(178, 170, 158));
}

// ------------------------------------------------------------------ 03 -- //
// Highlighter sweep across the key phrase of a paragraph.
static void s03(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .48, .47}, t);
    c.setFillStyle(kWhite); c.fillRect(0, 0, kW, kH);

    const double x0 = 1010;
    lineWidth(c, x0, 660, 1560, kLineA, 22);
    lineWidth(c, x0, 730, 1180, kLineA, 22);

    const BLFont fb = face("reg", 78);
    const string pre = "Reuse is the ";
    const string mid = "quiet engine";
    const string post = " of taste.";
    const double wy = 880, preW = textW(fb, pre), midW = textW(fb, mid) + 20;

    const double sweep = easeOutCubic(wind(t, 0.22, 0.54));
    c.save(); c.setGlobalAlpha(0.92f);
    c.setFillStyle(kMarker);
    c.fillRoundRect(BLRoundRect(x0 + preW - 4, wy - 66, midW * sweep + 18, 102, 18, 18));
    c.restore();

    const double inkE = clamp01(wind(t, 0.46, 0.64));
    fillText(c, fb, x0, wy, pre, rgba(168, 165, 158));
    c.save(); c.setGlobalAlpha(float(inkE));
    fillText(c, fb, x0 + preW + 10, wy, mid, kInk);
    fillText(c, fb, x0 + preW + 10 + midW, wy, post, rgba(168, 165, 158));
    c.restore();

    lineWidth(c, x0, 1010, 1420, kLineA, 22);
    lineWidth(c, x0, 1080, 1780, kLineA, 22);

    tag(c, x0, 1900, "MARKED FOR THE CLIP", rgba(178, 170, 158));
}

// ------------------------------------------------------------------ 04 -- //
// Reading progress bar fills while a key line stays pinned.
static void s04(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .5, .47}, t);
    c.setFillStyle(kCream); c.fillRect(0, 0, kW, kH);

    const double p = easeInOutCubic(wind(t, 0.05, 0.78));
    c.setFillStyle(BLRgba32(224, 220, 212, 255)); c.fillRect(BLRect(0, 0, kW, 20));
    c.setFillStyle(kViolet); c.fillRect(BLRect(0, 0, kW * p, 20));

    const double x0 = 820;
    fillText(c, face("serifBold", 150), x0, 620, "Reading the unreadable.", kInk);
    fillText(c, face("reg", 50), x0, 760, "archive digest  ·  9 minutes", kGrayTxt);
    lineWidth(c, x0, 880, 2180, kLineA, 24);
    lineWidth(c, x0, 970, 1760, kLineA, 24);

    // pinned key line
    const double ke = easeOutCubic(wind(t, 0.30, 0.50));
    c.save(); c.setGlobalAlpha(float(ke));
    c.setFillStyle(kLavBar);
    c.fillRoundRect(BLRoundRect(x0 - 30, 1064, 2130, 96, 16, 16));
    fillText(c, face("semi", 62), x0, 1130, "The dates only worked on paper.", rgba(52, 42, 106));
    c.restore();
    statusPill(c, x0 + 2280, 1112, "key line", ke, kViolet, kWhite, 0.9);

    lineWidth(c, x0, 1260, 2180, kLineA, 24);
    lineWidth(c, x0, 1350, 2050, kLineA, 24);
    lineWidth(c, x0, 1440, 2180, kLineA, 24);

    const BLFont fm = face("dejavu", 46);
    const string pct = std::to_string(int(std::round(p * 100.0))) + "%";
    card(c, 3400, 90, 300, 108, 20, kWhite, false, BLRgba32(0, 0, 0, 30));
    fillText(c, fm, 3520 - textW(fm, pct) * 0.5, 156, pct, kViolet);
}

// ------------------------------------------------------------------ 05 -- //
// Browser tabs of the sources open one by one; cursor taps the third.
static void s05(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.03, 1.05, .5, .47}, t);
    c.setFillStyle(kDeep); c.fillRect(0, 0, kW, kH);
    dotGrid(c, 84, BLRgba32(255, 255, 255, 14), 2.4);

    const double bx = 640, by = 500, bw = 2560, bh = 1280;
    softShadow(c, bx, by, bw, bh, 26, 36, 60, 60);
    card(c, bx, by, bw, bh, 26, BLRgba32(32, 33, 40, 255));
    c.setFillStyle(BLRgba32(24, 25, 31, 255)); c.fillRect(BLRect(bx, by, bw, 128));

    const char* tabs[3] = {"The Quiet Ledger", "Forensic Weekly", "Archive 47"};
    const BLRgba32 dotCol[3] = {kGold, kBlue, kGreenC};
    const double tw = 640, th = 88;
    double activeX = 0;
    for (int i = 0; i < 3; ++i) {
        const double e = easeOutCubic(wind(t, 0.08 + i * 0.12, 0.26 + i * 0.12));
        if (e <= 0.004) continue;
        const double tx = bx + 32 + i * (tw + 12);
        const double ty = by + 24 + (1 - e) * 30;
        const bool active = i == 2 && t > 0.55;
        card(c, tx, ty, tw, th, 18, active ? BLRgba32(43, 44, 53, 255) : BLRgba32(38, 39, 47, 255),
             false, active ? kBlue : BLRgba32(0));
        c.setFillStyle(dotCol[i]); c.fillCircle(BLCircle(tx + 52, ty + th * .5, 16));
        c.save(); c.setGlobalAlpha(float(e));
        fillText(c, face("med", 46), tx + 92, ty + 62, tabs[i], rgba(222, 222, 228));
        c.restore();
        if (i == 2) activeX = tx + tw * .5;
    }
    c.setFillStyle(BLRgba32(38, 39, 47, 255));
    c.fillRoundRect(BLRoundRect(bx + 32, by + 180, bw - 64, 84, 20, 20));
    fillText(c, face("dejavu", 44), bx + 64, by + 236, "archive47.openregistry/finding-aid", rgba(120, 122, 130));

    // document skeleton behind a softly dimmed page
    for (int i = 0; i < 5; ++i) {
        c.setFillStyle(BLRgba32(54, 56, 66, 255));
        c.fillRect(BLRect(bx + 120, by + 360 + double(i) * 120, double((bw - 300) * (i == 3 ? 0.5 : 0.86)), 30));
    }

    const double pe = easeInOutCubic(wind(t, 0.62, 0.86));
    pointer(c, lerp(2900.0, activeX, pe), lerp(1400.0, by + 68, pe), "Reader", kViolet, 1.0, pe > 0 ? 1.0 : 0.0);
    ripple(c, activeX, by + 68, wind(t, 0.88, 1.0), kBlue);
}

// ------------------------------------------------------------------ 06 -- //
// Social post card: text types, verification, heart pops, counter climbs.
static void s06(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .5, .48}, t);
    c.setFillStyle(kNight); c.fillRect(0, 0, kW, kH);
    dotGrid(c, 96, BLRgba32(255, 255, 255, 12), 2.4);

    const double cx = 980, cy = 520, cw = 1880, ch = 1120;
    softShadow(c, cx, cy, cw, ch, 30, 40, 70, 60);
    card(c, cx, cy, cw, ch, 30, kWhite);

    c.setFillStyle(kGold); c.fillCircle(BLCircle(cx + 130, cy + 150, 78));
    fillText(c, face("bold", 72), cx + 106, cy + 176, "A", kWhite);
    fillText(c, face("semi", 54), cx + 236, cy + 132, "Archive 47", kInk);
    c.setFillStyle(kBlue); c.fillCircle(BLCircle(cx + 452, cy + 114, 26));
    checkMark(c, cx + 452, cy + 114, 26, wind(t, 0.10, 0.20), kWhite, 7);
    fillText(c, face("reg", 44), cx + 236, cy + 190, "@archive_47  ·  3h", kGrayTxt);

    const BLFont fb = face("bold", 84);
    const double e = wind(t, 0.16, 0.52);
    fillText(c, fb, cx + 110, cy + 330, typed("Found it. Page 14", easeOutCubic(clamp01(e * 1.2))), kInk);
    fillText(c, fb, cx + 110, cy + 450, typed("was never published.", easeOutCubic(clamp01(e * 1.2 - 0.35))), kInk);

    // footer: heart with count
    const double he = easeOutCubic(wind(t, 0.58, 0.78));
    const double hx = cx + 150, hy = cy + ch - 150;
    if (he > 0.004) {
        const double hs = 1.0 + 0.5 * (1.0 - he);
        c.save(); c.setGlobalAlpha(float(he));
        c.setFillStyle(kRedC);
        BLPath tri;
        tri.lineTo(hx - 44 * hs, hy - 22 * hs);
        tri.lineTo(hx + 44 * hs, hy - 22 * hs);
        tri.lineTo(hx, hy + 46 * hs);
        tri.close();
        c.fillPath(tri);
        c.fillCircle(BLCircle(hx - 23 * hs, hy - 36 * hs, 29 * hs));
        c.fillCircle(BLCircle(hx + 23 * hs, hy - 36 * hs, 29 * hs));
        c.restore();
    }
    const BLFont fm = face("semi", 48);
    const long likes = long(std::round(lerp(9404.0, 12403.0, wind(t, 0.60, 0.92))));
    fillText(c, fm, hx + 96, hy + 16, comma(likes), rgba(196, 108, 98));
    for (int i = 0; i < 2; ++i) {
        const double rx = hx + 560 + i * 520.0;
        c.setStrokeStyle(BLRgba32(120, 120, 128, 255)); c.setStrokeWidth(8);
        c.strokeCircle(BLCircle(rx + 30, hy, 44));
        for (int k = 0; k < 3; ++k) lineWidth(c, rx + 120, hy - 12 + k * 16, 260 - k * 60, BLRgba32(228, 228, 226, 255), 12);
    }
    ripple(c, hx, hy, wind(t, 0.62, 0.80), kRedC);
}

// ------------------------------------------------------------------ 07 -- //
// Photograph reveal inside a mat frame with an elegant serif caption.
static void s07(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.04, 1.05, .5, .47}, t);
    c.setFillStyle(kPaper); c.fillRect(0, 0, kW, kH);

    const double fx = 1000, fy = 380, fw = 1840, fh = 1300;
    softShadow(c, fx, fy, fw, fh, 24, 40, 66, 50);
    card(c, fx, fy, fw, fh, 24, BLRgba32(30, 26, 34, 40), false, BLRgba32(0, 0, 0, 26));

    const double im = easeOutCubic(wind(t, 0.06, 0.46));
    c.save();
    c.setGlobalAlpha(float(im));
    c.translate(fx + fw * .5, fy + fh * .5);
    double zs = 1.14 - 0.14 * im;
    c.scale(zs, zs);
    c.translate(-(fx + fw * .5), -(fy + fh * .5));
    fillGrad(c, fx, fy, fw, fh, rgba(46, 86, 158), rgba(148, 96, 190), false);
    c.setFillStyle(BLRgba32(255, 222, 168, 255)); c.fillCircle(BLCircle(fx + fw * 0.72, fy + fh * 0.30, 220));
    c.setFillStyle(BLRgba32(20, 24, 40, 160)); c.fillRect(BLRect(fx, fy + fh * 0.62, fw, fh * 0.38));
    for (int i = 0; i < 4; ++i) {
        c.setFillStyle(BLRgba32(16, 18, 30, (uint8_t)(200 - i * 40)));
        c.fillRoundRect(BLRoundRect(fx + 140 + i * 320, fy + fh - 260 - i * 40, 260, 200 + i * 40, 16, 16));
    }
    c.restore();

    fillText(c, face("semi", 44), fx, fy + fh + 120, "FIG. 03", kGold);
    const BLFont fc = face("serifMedIt", 72);
    const double ce = easeOutCubic(wind(t, 0.50, 0.82));
    fillText(c, fc, fx, fy + fh + 210, typed("The map nobody ordered.", ce), rgba(48, 46, 42));
}

// ------------------------------------------------------------------ 08 -- //
// Claim vs record: two cards, the second slides in and gets verified.
static void s08(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .5, .47}, t);
    c.setFillStyle(kDeep); c.fillRect(0, 0, kW, kH);

    // claim card
    const double ax = 380, ay = 560, aw = 1400, ah = 980;
    softShadow(c, ax, ay, aw, ah, 26, 36, 60, 60);
    card(c, ax, ay, aw, ah, 26, kWhite);
    statusPill(c, ax + 190, ay + 110, "THE CLAIM", wind(t, 0.04, 0.18), kRedC, kWhite, 0.9);
    const BLFont fq = face("serifMedIt", 86);
    fillText(c, fq, ax + 90, ay + 340, typed("\"All of it signed", wind(t, 0.16, 0.40)), kInk);
    fillText(c, fq, ax + 90, ay + 450, typed("by the same office.\"", wind(t, 0.24, 0.48)), kInk);
    fillText(c, face("reg", 44), ax + 94, ay + 600, "quoted on the show, 04:12", kGrayTxt);
    lineWidth(c, ax + 90, ay + 700, aw - 220, kLineA, 22);

    // record card slides from the right
    const double sb = easeOutCubic(wind(t, 0.42, 0.62));
    const double bx0 = 2100 + (1 - sb) * 520, by = 560, bw = 1400, bh = 980;
    c.save(); c.setGlobalAlpha(float(sb));
    softShadow(c, bx0, by, bw, bh, 26, 36, 60, 60 * sb);
    card(c, bx0, by, bw, bh, 26, BLRgba32(243, 247, 244, 255));
    statusPill(c, bx0 + 190, by + 110, "THE RECORD", 1.0, kGreenC, kWhite, 0.9);
    const char* rows[2] = {"signature date: revoked twice", "counter-signature: page 15"};
    for (int i = 0; i < 2; ++i) {
        checkMark(c, bx0 + 140, by + 300 + i * 150, 46, wind(t, 0.62 + i * 0.10, 0.74 + i * 0.10), kGreenC, 9);
        fillText(c, face("med", 52), bx0 + 210, by + 318 + i * 150, rows[i], rgba(40, 46, 42));
    }
    lineWidth(c, bx0 + 90, by + 700, bw - 220, BLRgba32(214, 222, 216, 255), 22);
    c.restore();

    // connector + verdict
    const double ve = easeOutCubic(wind(t, 0.78, 0.92));
    if (sb > 0.9) {
        c.setStrokeStyle(BLRgba32(255, 255, 255, 90)); c.setStrokeWidth(8);
        c.strokeLine(BLPoint(ax + aw, ay + ah * .5), BLPoint(bx0, by + bh * .5));
        caretTriangle(c, (ax + aw + bx0) * .5, ay + ah * .5, 34, 1.0, BLRgba32(255, 255, 255, 90));
    }
    statusPill(c, kWndW() * .5, 1810, "CROSS-CHECKED", ve, kGreenC, kWhite, 1.1);
}

// ------------------------------------------------------------------ 09 -- //
// Search: query types in, elegant result cards drop in, one wins.
static void s09(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .5, .46}, t);
    c.setFillStyle(kWhite); c.fillRect(0, 0, kW, kH);

    const double sx = 1060, sy = 300, sw = 1720, sh = 150;
    softShadow(c, sx, sy, sw, sh, 75, 24, 40, 40);
    card(c, sx, sy, sw, sh, 75, kWhite, false, BLRgba32(0, 0, 0, 26));
    c.setStrokeStyle(kInk); c.setStrokeWidth(9);
    c.strokeCircle(BLCircle(sx + 92, sy + sh * .5 - 6, 34));
    c.strokeLine(BLPoint(sx + 116, sy + sh * .5 + 18), BLPoint(sx + 140, sy + sh * .5 + 42));
    const double e = easeOutCubic(wind(t, 0.08, 0.38));
    const string query = typed("who reset the signature dates?", e);
    fillText(c, face("reg", 60), sx + 180, sy + 94, query, kInk);
    if (e < 1.0 && (fr % 20) < 12) {
        c.setFillStyle(kBlue); c.fillRect(BLRect(sx + 180 + textW(face("reg", 60), query) + 10, sy + 42, 10, 72));
    }

    const char* titles[3] = {"The memo that reset the dates", "Archive 47 \u2014 the missing pages", "Signature audit, 1972 (scan)"};
    const char* urls[3] = {"quietledger\u00B7com/memo", "archive47.openregistry/p14", "audit-1972\u00B7com/annex"};
    for (int i = 0; i < 3; ++i) {
        const double re = easeOutCubic(wind(t, 0.42 + i * 0.10, 0.60 + i * 0.10));
        if (re <= 0.004) continue;
        const double ry = 620 + double(i) * 380 + (1 - re) * 70;
        const double rx = 1060;
        c.save(); c.setGlobalAlpha(float(re));
        if (i == 1 && t > 0.72) {
            c.setStrokeStyle(kBlue); c.setStrokeWidth(7);
            c.strokeRoundRect(BLRoundRect(rx - 26, ry - 46, 1800, 300, 24, 24));
        }
        fillText(c, face("dejavu", 42), rx, ry - 18, urls[i], rgba(104, 142, 96));
        fillText(c, face("med", 66), rx, ry + 78, titles[i], i == 1 ? kBlue : rgba(32, 32, 38, 230));
        lineWidth(c, rx, ry + 140, 1500 - i * 180, kLineA, 20);
        c.restore();
    }
    ripple(c, 1530, 1050, wind(t, 0.86, 0.98), kBlue);
}

// ------------------------------------------------------------------ 10 -- //
// Article with marginalia: sticky notes appear on the side margin.
static void s10(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .47, .47}, t);
    c.setFillStyle(kPaper); c.fillRect(0, 0, kW, kH);

    // article column
    const double x0 = 480;
    fillText(c, face("serifBold", 132), x0, 560, "Marginalia rules.", rgba(30, 30, 26));
    lineWidth(c, x0, 700, 1560, kLineA, 24);
    lineWidth(c, x0, 800, 1240, kLineA, 24);
    c.save(); c.setGlobalAlpha(0.94f);
    fillText(c, face("reg", 56), x0, 980, "Two readers argued for years in the", rgba(64, 62, 58));
    fillText(c, face("reg", 56), x0, 1054, "same margin \u2014 and both were right.", rgba(64, 62, 58));
    c.restore();
    lineWidth(c, x0, 1160, 1620, kLineA, 24);
    lineWidth(c, x0, 1260, 1380, kLineA, 24);

    // underline connecting to the notes
    const double ue = easeOutCubic(wind(t, 0.30, 0.46));
    c.setFillStyle(kViolet); c.fillRect(BLRect(x0, 1076, 1240 * ue, 8));

    // sticky notes
    const char* notes[3] = {"checked \u2014 archive 47", "!! page 14 says otherwise", "see the 1931 audit"};
    const BLRgba32 sticky[3] = {rgba(252, 232, 148), rgba(214, 205, 247), rgba(190, 226, 208)};
    for (int i = 0; i < 3; ++i) {
        const double e = easeOutCubic(wind(t, 0.36 + i * 0.15, 0.52 + i * 0.15));
        if (e <= 0.004) continue;
        const double nx = 2440, ny = 520 + double(i) * 400 + (1 - e) * 60;
        c.save();
        c.setGlobalAlpha(float(e));
        c.translate(nx, ny); c.rotate((i % 2 ? 0.045 : -0.035) * e);
        softShadow(c, 0, 0, 520, 210, 16, 22, 34, 46);
        c.setFillStyle(sticky[i]); c.fillRoundRect(BLRoundRect(0, 0, 520, 210, 14, 14));
        fillText(c, face("med", 48), 40, 120, notes[i], rgba(56, 52, 40));
        c.restore();
        c.save(); c.setGlobalAlpha(float(e * 0.7));
        c.setStrokeStyle(kViolet); c.setStrokeWidth(5);
        c.strokeLine(BLPoint(x0 + 1240 * e, 1080), BLPoint(nx - 30, ny + 100));
        c.restore();
    }
}

// ------------------------------------------------------------------ 11 -- //
// Big stat counts up over a minimal bar chart.
static void s11(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.03, 1.05, .5, .47}, t);
    c.setFillStyle(kNight); c.fillRect(0, 0, kW, kH);
    dotGrid(c, 88, BLRgba32(255, 255, 255, 12), 2.2);

    tag(c, 640, 520, "DOCUMENTS PROCESSED", kGold);

    const BLFont fb = face("anton", 460);
    const long v = long(std::round(lerp(1482.0, 9640.0, easeOutCubic(wind(t, 0.10, 0.72)))));
    fillText(c, fb, 640, 1240, comma(v), kWhite);
    const double ue = clamp01(wind(t, 0.30, 0.66));
    c.setFillStyle(kGold); c.fillRect(BLRect(640, 1320, textW(face("anton", 460), "9640") * ue * 1.18, 16));

    // bar chart
    const double heights[7] = {210, 380, 300, 500, 420, 620, 540};
    const double base = 1880;
    for (int i = 0; i < 7; ++i) {
        const double e = easeOutCubic(wind(t, 0.24 + i * 0.06, 0.48 + i * 0.06));
        const double bx = 2560 + double(i) * 150;
        c.setFillStyle(i == 6 ? kGold : BLRgba32(72, 74, 82, 255));
        c.fillRoundRect(BLRoundRect(bx, base - heights[i] * e, 96, heights[i] * e, 12, 12));
    }
    lineWidth(c, 2520, base + 6, 1180, BLRgba32(60, 62, 70, 255), 4);

    fillText(c, face("dejavu", 48), 640, 1500, "compiled from the archive, 1899\u20131945", rgba(150, 152, 160));
}

// ------------------------------------------------------------------ 12 -- //
// Chapter timeline: dots light up, active chapter gets focus + ripple.
static void s12(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .5, .48}, t);
    c.setFillStyle(kCream); c.fillRect(0, 0, kW, kH);

    const double ly = 1080, x0 = 560, x1 = 3320;
    c.setFillStyle(BLRgba32(217, 213, 204, 255)); c.fillRect(BLRect(x0, ly - 5, x1 - x0, 10));
    const double pe = easeInOutCubic(wind(t, 0.10, 0.62));
    c.setFillStyle(kViolet); c.fillRect(BLRect(x0, ly - 5, (x1 - x0) * pe, 10));

    const char* rows[5] = {"THE TIP", "THE LEDGER", "THE MISSING PAGE", "THE AUDIT", "THE AFTERMATH"};
    for (int i = 0; i < 5; ++i) {
        const double e = easeOutCubic(wind(t, 0.14 + i * 0.09, 0.32 + i * 0.09));
        if (e <= 0.004) continue;
        const double dx = x0 + double(i) * (x1 - x0) / 4.0;
        const bool act = i == 2;
        const double rad = act ? 30 + 14 * e : 22;
        c.setFillStyle(act || pe > (double(i)) / 4.0 ? kViolet : BLRgba32(217, 213, 204, 255));
        c.fillCircle(BLCircle(dx, ly, rad));
        const double sgn = i % 2 ? 1.0 : -1.0;
        c.save(); c.setGlobalAlpha(float(e));
        textC(c, face(act ? "bold" : "med", act ? 62 : 50), dx, ly + sgn * (act ? 150 : 120) + sgn * 40,
              rows[i], act ? rgba(52, 42, 106) : kGrayTxt);
        c.restore();
        if (act) { ripple(c, dx, ly, wind(t, 0.44, 0.70), kViolet); ripple(c, dx, ly, wind(t, 0.56, 0.86), kViolet); }
    }
    statusPill(c, x0 + 240, 700, "CHAPTER 03 OF 05", easeOutCubic(wind(t, 0.46, 0.64)), rgba(52, 42, 106), kWhite, 1.0);
}

// ------------------------------------------------------------------ 13 -- //
// Gloss: a word underlines and its definition pops as a tooltip card.
static void s13(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .5, .46}, t);
    c.setFillStyle(kPaper); c.fillRect(0, 0, kW, kH);
    tag(c, 940, 420, "GLOSS  ·  INLINE", rgba(178, 170, 158));

    const double x0 = 940, wy = 940;
    const BLFont fb = face("reg", 80);
    const string pre = "They kept the ";
    const string word = "archival ";
    const string post = "copies away.";
    const double preW = textW(fb, pre), wordW = textW(fb, word);
    fillText(c, fb, x0, wy, pre, rgba(70, 68, 62));
    fillText(c, fb, x0 + preW, wy, word, kViolet);
    fillText(c, fb, x0 + preW + wordW, wy, post, rgba(70, 68, 62));

    const double ue = easeOutCubic(wind(t, 0.24, 0.44));
    c.setFillStyle(kViolet); c.fillRect(BLRect(x0 + preW, wy + 28, wordW * ue, 9));

    ripple(c, x0 + preW + wordW * .5, wy - 30, wind(t, 0.30, 0.46), kViolet);

    // tooltip card
    const double te = easeOutCubic(wind(t, 0.48, 0.68));
    if (te > 0.004) {
        const double tx = x0 + preW - 60, ty0 = wy - 520, ty = ty0 + (1 - te) * 60;
        c.save(); c.setGlobalAlpha(float(te));
        softShadow(c, tx, ty, 1240, 330, 24, 30, 52, 56);
        card(c, tx, ty, 1240, 330, 24, kWhite);
        c.setFillStyle(kViolet); c.fillRect(BLRect(tx, ty, 18, 330));
        fillText(c, face("semi", 62), tx + 70, ty + 116, "archival", kViolet);
        fillText(c, face("reg", 46), tx + 70 + textW(face("semi", 62), "archival") + 30, ty + 112, "adj.", kGrayTxt);
        fillText(c, face("reg", 50), tx + 70, ty + 210, "kept for the record \u2014", rgba(56, 54, 50));
        fillText(c, face("reg", 50), tx + 70, ty + 278, "often quietly, on purpose.", rgba(56, 54, 50));
        c.restore();
    }
}

// ------------------------------------------------------------------ 14 -- //
// Designed captions: a subtitle bar with word-by-word highlight.
static void s14(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.03, 1.05, .5, .5}, t);
    fillGrad(c, 0, 0, kW, kH, rgba(24, 30, 52), rgba(52, 32, 78), true);
    // soft "subject" blobs, as if behind a darkened video frame
    c.save(); c.setGlobalAlpha(0.22f);
    c.setFillStyle(rgba(255, 224, 178)); c.fillCircle(BLCircle(1180, 640, 300));
    c.setFillStyle(rgba(120, 190, 220)); c.fillCircle(BLCircle(2740, 520, 220));
    c.restore();
    c.setFillStyle(BLRgba32(8, 9, 14, 60)); c.fillRect(0, 0, kW, kH);

    fillText(c, face("dejavu", 40), 120, 150, "captions \u2014 designed, not default", rgba(255, 255, 255, 110));

    static const char* words[7] = {"Then", "the", "dates", "stopped", "adding", "up.", ""};
    const BLFont fw = face("bold", 76);
    const double barW = 2100, barX = (kW - barW) * .5, barY = 1620, barH = 240;
    c.save(); c.setGlobalAlpha(0.78f);
    c.setFillStyle(BLRgba32(6, 7, 10, 255));
    c.fillRoundRect(BLRoundRect(barX, barY, barW, barH, 34, 34));
    c.restore();

    const double e = wind(t, 0.14, 0.86);
    const int active = int(clamp01(e / 0.8) * 5.99);
    double wx = barX + 120;
    for (int i = 0; i < 6; ++i) {
        const string w = words[i];
        const double wW = textW(fw, w + " ");
        const bool glow = i <= active;
        c.save();
        c.setGlobalAlpha(float(clamp01(e * 6.0)));
        fillText(c, fw, wx, barY + 148 - (glow ? 8 : 0), w,
                 glow ? kAmber : BLRgba32(255, 255, 255, 96));
        c.restore();
        wx += wW;
    }
    // caption edge marker
    c.setFillStyle(kAmber); c.fillRect(BLRect(barX - 18, barY + 30, 10, barH - 60));
}

// ------------------------------------------------------------------ 15 -- //
// Night reading: the page dims at the toggle and the quote glows gold.
static void s15(BLContext& c, double t, int fr) {
    (void)fr;
    cam(c, {1.02, 1.05, .5, .47}, t);
    const double flip = easeInOutCubic(wind(t, 0.34, 0.56));
    static const int bgA[3] = {248, 246, 241}, bgB[3] = {14, 15, 19};
    c.setFillStyle(BLRgba32(uint8_t(bgA[0] + int((bgB[0] - bgA[0]) * flip)),
                            uint8_t(bgA[1] + int((bgB[1] - bgA[1]) * flip)),
                            uint8_t(bgA[2] + int((bgB[2] - bgA[2]) * flip)), 255));
    c.fillRect(0, 0, kW, kH);

    const double x0 = 660;
    fillText(c, face("serifBold", 138), x0, 560, "Read it in the dark.", kInkText(flip));
    fillText(c, face("reg", 48), x0, 690, "night mode  ·  whole file, not just the mood", kGrayTxt,
             1.0 - flip * 0.4);
    lineWidth(c, x0, 800, 2300, kLineDay(flip, 0.16), 24);
    lineWidth(c, x0, 890, 1820, kLineDay(flip, 0.16), 24);

    // the key quote, glowing
    const double qe = easeOutCubic(wind(t, 0.16, 0.42));
    c.save(); c.setGlobalAlpha(0.28f + 0.5f * float(flip));
    c.setFillStyle(kGold);
    c.fillRoundRect(BLRoundRect(x0 - 26, 972, 2340, 110, 18, 18));
    c.restore();
    c.save(); c.setGlobalAlpha(float(qe));
    fillText(c, face("serifMedIt", 84), x0, 1050,
             "\"Every quiet era keeps one loud ledger.\"", kInkText(flip));
    c.restore();
    lineWidth(c, x0, 1200, 2300, kLineDay(flip, 0.16), 24);
    lineWidth(c, x0, 1290, 2100, kLineDay(flip, 0.16), 24);

    // theme toggle
    const double tx = 2960, ty = 1740;
    c.setFillStyle(flip > .5 ? BLRgba32(58, 60, 68, 255) : BLRgba32(233, 230, 224, 255));
    c.fillRoundRect(BLRoundRect(tx, ty, 300, 130, 65, 65));
    c.setFillStyle(flip > .5 ? kGold : kWhite);
    const double kx = tx + 20 + 130 * flip;
    c.fillCircle(BLCircle(kx + 45, ty + 65, 46));
    fillText(c, face("reg", 44), tx, ty + 220, "theme", flip > .5 ? BLRgba32(150, 152, 160, 255) : kGrayTxt);
    ripple(c, kx + 45, ty + 65, wind(t, 0.42, 0.60), kGold);
}

// text color softening for s15 flip
static BLRgba32 kInkText(double flip) {
    static const int a[3] = {30, 30, 26}, b[3] = {240, 239, 235};
    return BLRgba32(uint8_t(a[0] + int((b[0] - a[0]) * flip)), uint8_t(a[1] + int((b[1] - a[1]) * flip)),
                    uint8_t(a[2] + int((b[2] - a[2]) * flip)), 255);
}
static BLRgba32 kLineDay(double flip, double alphaOnDark) {
    static const int a[3] = {228, 225, 218}, b[3] = {62, 64, 74};
    return BLRgba32(uint8_t(a[0] + int((b[0] - a[0]) * flip)), uint8_t(a[1] + int((b[1] - a[1]) * flip)),
                    uint8_t(a[2] + int((b[2] - a[2]) * flip)), 255);
}

// helper used at s08 in place of window width, defined here for tidiness
static double kWndW() { return kW; }

static const catalog_entry kCatalog[15] = {
    {1,  "01_browser_article_reveal", "Browser window: classic article card types its headline as a reader arrives", 1.03, 1.06, .5, .48, 0.96, s01},
    {2,  "02_quote_pull",            "Editorial pull-quote: serif italic lines rise one by one between giant marks", 1.02, 1.06, .5, .48, 0.96, s02},
    {3,  "03_highlighter_sweep",     "Paragraph with a highlighter mark sweeping across the key phrase", 1.02, 1.05, .48, .47, 0.94, s03},
    {4,  "04_reading_progress",      "Reading progress fills the top bar while a key line stays pinned", 1.02, 1.05, .5, .47, 0.92, s04},
    {5,  "05_source_tabs",           "Browser tabs of the sources open one by one; the reader taps the last", 1.03, 1.05, .5, .47, 0.96, s05},
    {6,  "06_post_counter",          "Social post: text types in, verified tick lands, likes climb", 1.02, 1.05, .5, .48, 0.96, s06},
    {7,  "07_image_caption_reveal",  "Photograph reveal inside a mat frame with a serif caption typing under it", 1.04, 1.05, .5, .47, 0.96, s07},
    {8,  "08_claim_record",          "Claim vs record: two cards, cross-check arrow and a verified verdict", 1.02, 1.05, .5, .47, 0.96, s08},
    {9,  "09_search_results",        "Search bar types the query and elegant result cards drop in, one wins", 1.02, 1.05, .5, .46, 0.96, s09},
    {10, "10_margin_notes",          "Article page with sticky marginalia notes wired to an underlined phrase", 1.02, 1.05, .47, .47, 0.96, s10},
    {11, "11_stat_countup",          "Big stat counts up over a minimal bar chart on a midnight canvas", 1.03, 1.05, .5, .47, 0.96, s11},
    {12, "12_chapter_timeline",      "Chapter timeline dots light up; the active chapter gets a double ripple", 1.02, 1.05, .5, .48, 0.92, s12},
    {13, "13_gloss_tooltip",         "Inline gloss: word underlines and its definition pops as a tooltip card", 1.02, 1.05, .5, .46, 0.96, s13},
    {14, "14_designed_captions",     "Subtitle bar with word-by-word highlight, amber marker on the edge", 1.03, 1.05, .5, .5, 0.94, s14},
    {15, "15_night_reading",         "Night reading: the page dims via a theme toggle and the quote glows gold", 1.02, 1.05, .5, .47, 0.96, s15},
};

static inline int runScene(const catalog_entry& sc, const string& outRoot, bool stillsOnly, bool keepFrames) {
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

static inline bool writeCollateral(const string& outRoot) {
    fs::create_directories(outRoot);
    const int cellW = 640, cellH = 360, labelH = 44, pad = 24;
    const int cols = 3, rowsN = 5;
    BLImage sheet(cols * cellW + pad * 2, rowsN * (cellH + labelH) + pad * 2, BL_FORMAT_PRGB32);
    BLContext ctx(sheet);
    ctx.clearAll();
    ctx.setFillStyle(BLRgba32(18, 18, 20, 255));
    ctx.fillRect(0, 0, kW, kH);
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
    manifest["schema"] = "chronon.web-yt-elegant.v1";
    manifest["pack"] = "web_yt_elegant_v1";
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

} // namespace chrom

int main(int argc, char** argv) {
    using namespace chrom;
    if (!fonts().valid) { std::cerr << "fonts missing" << std::endl; return 2; }
    string outRoot = "C:/Users/pater/Pyt/chronons/ChrononTemplate/artifacts/web_yt_elegant_v1";
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
