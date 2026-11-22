// d08-d14 — data, field evidence, documents and interface surfaces.

#include "doc_pack.hpp"

namespace chronon::docshots {

namespace {

const BLRgba32 kInk = rgba(22, 24, 27);
const BLRgba32 kMuted = rgba(108, 108, 103);
const BLRgba32 kOrange = rgba(205, 104, 47);
const BLRgba32 kBlue = rgba(54, 111, 186);
const BLRgba32 kRed = rgba(190, 49, 42);

// 08 — Data desk. The line chart is drawn with native strokes; the endpoint
// and annotation land under a second, slower beat.
void d08(BLContext& c, double t, int) {
    camera(c, 1.01, 1.04, 0.48, 0.50, t);
    paper(c, rgba(252, 250, 246), 34);
    browserChrome(c, "data.example.org/series/federal-outlays", false, "DATA");

    tracked(c, face("semi", 11), 120, 110, "CASE FILE  /  SERIES 04", rgba(111, 107, 98), 1.7);
    fillText(c, face("serifBold", 42), 120, 154, "The line moved before", kInk);
    fillText(c, face("serifBold", 42), 120, 198, "the language did", kInk);
    fillText(c, face("reg", 14), 120, 226,
             "Emergency outlays, indexed to the 2019 baseline. The vertical mark is the ruling.",
             rgba(108, 104, 95));

    c.setFillStyle(rgba(255, 255, 255, 155));
    c.fillRoundRect(BLRoundRect(120, 254, 1340, 596, 10, 10));
    c.setFillStyle(rgba(255, 255, 255, 130));
    c.fillRoundRect(BLRoundRect(1490, 254, 310, 596, 10, 10));

    const double gx0 = 176;
    const double gy0 = 306;
    const double gw = 1216;
    const double gh = 468;
    for (int i = 0; i <= 4; ++i) {
        const double y = gy0 + gh * i / 4.0;
        rule(c, gx0, y, gw, rgba(40, 46, 43, 20));
        fillText(c, face("mono", 11), 140, y + 4, std::to_string(80 - i * 20), rgba(118, 116, 108));
    }
    const char* months[] = {"JAN", "MAR", "MAY", "JUL", "SEP", "NOV"};
    for (int i = 0; i < 6; ++i) {
        const double x = gx0 + i * (gw / 5.0);
        c.setFillStyle(rgba(40, 46, 43, 18));
        c.fillRect(BLRect(x, gy0, 1, gh));
        textC(c, face("mono", 10), x, gy0 + gh + 24, months[i], rgba(118, 116, 108));
    }
    rule(c, gx0, gy0 + gh, gw, rgba(40, 46, 43, 75));
    tracked(c, face("semi", 10), gx0, 282, "INDEXED OUTLAYS  /  USD BILLIONS", rgba(113, 109, 100), 1.3);
    fillText(c, face("reg", 11), 1354, 282, "SOURCE: OMB, 2026", rgba(132, 127, 117));

    const int values[] = {31, 34, 33, 40, 43, 46, 51, 57, 56, 63, 70, 78};
    std::vector<BLPoint> pts;
    for (int i = 0; i < 12; ++i) {
        const double x = gx0 + i * (gw / 11.0);
        const double y = gy0 + gh - (values[i] - 20) * (gh / 70.0);
        pts.push_back(BLPoint(x, y));
    }

    // Area fill is static and very light; the line is revealed by the beat.
    BLPath area;
    area.moveTo(pts.front().x, gy0 + gh);
    for (const auto& p : pts) area.lineTo(p.x, p.y);
    area.lineTo(pts.back().x, gy0 + gh);
    area.close();
    c.setFillStyle(rgba(205, 104, 47, 16));
    c.fillPath(area);

    const double draw = easeInOutCubic(wind(t, 0.10, 0.64));
    c.save();
    c.setStrokeStyle(rgba(205, 104, 47, 230));
    c.setStrokeWidth(3.4);
    const int last = std::max(1, int(draw * 11.0));
    for (int i = 0; i < last; ++i) {
        c.strokeLine(pts[i], pts[i + 1]);
    }
    if (draw < 1.0) {
        const double seg = draw * 11.0 - std::floor(draw * 11.0);
        const int i = std::min(10, int(draw * 11.0));
        const BLPoint q(lerp(pts[i].x, pts[i + 1].x, seg),
                        lerp(pts[i].y, pts[i + 1].y, seg));
        c.strokeLine(pts[i], q);
        c.setFillStyle(rgba(205, 104, 47, 255));
        c.fillCircle(BLCircle(q.x, q.y, 5));
    }
    c.restore();

    const double pulse = 0.55 + 0.45 * std::sin(t * 7.2);
    c.setFillStyle(rgba(205, 104, 47, 40));
    c.fillCircle(BLCircle(pts.back().x, pts.back().y, 16 + pulse * 7));
    c.setFillStyle(rgba(255, 250, 244));
    c.fillCircle(BLCircle(pts.back().x, pts.back().y, 7 + pulse * 2));

    // Annotation block.
    const double a = easeOutCubic(wind(t, 0.48, 0.72));
    c.save();
    c.setGlobalAlpha(float(a));
    c.setStrokeStyle(rgba(205, 104, 47, 170));
    c.setStrokeWidth(1.2);
    c.strokeLine(BLPoint(pts.back().x - 8, pts.back().y), BLPoint(1456, 340));
    c.setFillStyle(rgba(255, 252, 247, 230));
    c.fillRoundRect(BLRoundRect(1514, 318, 254, 112, 7, 7));
    tracked(c, face("semi", 10), 1530, 342, "POST-RULING", rgba(130, 120, 105), 1.4);
    fillText(c, face("serifBold", 34), 1530, 376, "+312%", rgba(205, 104, 47));
    fillText(c, face("reg", 12), 1530, 398, "against the 2019 baseline", rgba(112, 107, 98));
    fillText(c, face("reg", 11), 1530, 416, "n = 1,842 filings", rgba(139, 132, 120));
    c.restore();

    fillText(c, face("serifBold", 22), 1520, 492, "The inflection", kInk);
    fillText(c, face("reg", 13), 1520, 518,
             "The visible spike begins four days before the", rgba(94, 91, 83));
    fillText(c, face("reg", 13), 1520, 538,
             "public docket entry, not after it.", rgba(94, 91, 83));
    rule(c, 1520, 558, 248, rgba(39, 45, 42, 28));
    fillText(c, face("semi", 11), 1520, 584, "KEY", rgba(118, 111, 101));
    fillText(c, face("mono", 11), 1520, 606, "2019 BASELINE  = 100", rgba(75, 75, 69));
    fillText(c, face("mono", 11), 1520, 626, "JAN 2026  \u2192  NOV 2026", rgba(75, 75, 69));
    fillText(c, face("reg", 11), 1520, 672, "FIG. 04  /  NATIVE DATA DESK", rgba(132, 126, 116));

    rule(c, 120, 884, 1680, rgba(39, 45, 42, 28));
    fillText(c, face("reg", 11), 120, 910, "METHOD: rolling 30-day mean, seasonally adjusted", rgba(121, 116, 107));
    fillText(c, face("reg", 11), 1430, 910, "LAST UPDATED 22 NOV 2026, 22:41 ET", rgba(121, 116, 107));
}

// 09 — Before/after field plate. Two procedural map textures share one frame;
// the divider, crosshair and change tag are the moving evidence.
void d09(BLContext& c, double t, int) {
    camera(c, 1.01, 1.035, 0.50, 0.51, t);
    c.setFillStyle(rgba(5, 15, 19));
    c.fillRect(BLRect(0, 0, kW, kH));
    browserChrome(c, "field.example.org/site/04/change-detection", true, "FIELD");
    tracked(c, face("semi", 11), 34, 92, "SITE 04  /  DELTA ANALYSIS", rgba(154, 191, 182), 1.6);
    fillText(c, face("serifBold", 30), 34, 128, "The same ground, two records", rgba(232, 239, 231));
    fillText(c, face("mono", 11), 1690, 96, "36.2048 N  /  55.2711 E", rgba(142, 177, 171));

    auto panel = [&](double x0, double x1, bool warm) {
        const BLRgba32 base = warm ? rgba(41, 29, 23) : rgba(11, 38, 42);
        c.setFillStyle(base);
        c.fillRect(BLRect(x0, 152, x1 - x0, 742));
        c.setStrokeStyle(rgba(178, 210, 193, warm ? 28 : 36));
        c.setStrokeWidth(1);
        for (int x = int(x0); x <= int(x1); x += 54)
            c.strokeLine(BLPoint(x, 152), BLPoint(x, 894));
        for (int y = 174; y <= 894; y += 54)
            c.strokeLine(BLPoint(x0, y), BLPoint(x1, y));

        const BLRgba32 land = warm ? rgba(117, 63, 39, 120) : rgba(42, 101, 101, 145);
        const BLRgba32 land2 = warm ? rgba(168, 83, 44, 75) : rgba(58, 120, 111, 95);
        BLPath p1;
        p1.moveTo(x0 + 30, 250);
        p1.lineTo(x0 + 230, 198);
        p1.lineTo(x0 + 380, 298);
        p1.lineTo(x0 + 330, 464);
        p1.lineTo(x0 + 120, 502);
        p1.lineTo(x0 + 12, 400);
        p1.close();
        c.setFillStyle(land);
        c.fillPath(p1);
        BLPath p2;
        p2.moveTo(x0 + 350, 560);
        p2.lineTo(x0 + 610, 490);
        p2.lineTo(x0 + 790, 610);
        p2.lineTo(x0 + 700, 790);
        p2.lineTo(x0 + 460, 832);
        p2.lineTo(x0 + 300, 706);
        p2.close();
        c.setFillStyle(land2);
        c.fillPath(p2);
        BLPath p3;
        p3.moveTo(x0 + 160, 640);
        p3.lineTo(x0 + 290, 596);
        p3.lineTo(x0 + 336, 668);
        p3.lineTo(x0 + 250, 730);
        p3.close();
        c.setFillStyle(warm ? rgba(224, 129, 65, 95) : rgba(74, 165, 148, 95));
        c.fillPath(p3);

        // A river / linear feature and a road network.
        c.setStrokeStyle(warm ? rgba(230, 158, 91, 80) : rgba(86, 196, 187, 85));
        c.setStrokeWidth(1.4);
        BLPath river;
        river.moveTo(x0 + 40, 700);
        river.cubicTo(x0 + 220, 606, x0 + 300, 780, x0 + 470, 680);
        river.cubicTo(x0 + 590, 612, x0 + 650, 700, x0 + 930, 560);
        c.strokePath(river);
        c.setStrokeStyle(rgba(224, 211, 180, warm ? 70 : 48));
        c.setStrokeWidth(0.8);
        c.strokeLine(BLPoint(x0 + 70, 520), BLPoint(x0 + 360, 560));
        c.strokeLine(BLPoint(x0 + 360, 560), BLPoint(x0 + 640, 480));
        c.strokeLine(BLPoint(x0 + 220, 390), BLPoint(x0 + 530, 620));

        // Hotspots: mostly optical/thermal anomalies on the after plate.
        const int count = warm ? 5 : 2;
        for (int i = 0; i < count; ++i) {
            const double hx = x0 + 150 + (i * 143) % 570;
            const double hy = 286 + (i * 173) % 450;
            c.setFillStyle(warm ? rgba(236, 131, 64, 25) : rgba(117, 224, 204, 18));
            c.fillCircle(BLCircle(hx, hy, 44 + i * 4));
            c.setFillStyle(warm ? rgba(245, 162, 79, 90) : rgba(130, 236, 216, 65));
            c.fillCircle(BLCircle(hx, hy, 8 + (i % 2) * 3));
            c.setStrokeStyle(warm ? rgba(247, 181, 101, 100) : rgba(140, 238, 218, 70));
            c.setStrokeWidth(1);
            c.strokeCircle(BLCircle(hx, hy, 27 + i * 3));
        }
    };
    panel(0, 960, false);
    panel(960, 1920, true);

    // Divider and crosshair.
    const double dx = lerp(1020, 900, easeInOutCubic(wind(t, 0.0, 0.70)));
    c.setFillStyle(rgba(7, 17, 21, 240));
    c.fillRect(BLRect(dx - 8, 152, 16, 742));
    c.setFillStyle(rgba(234, 231, 210, 190));
    c.fillRect(BLRect(dx - 1, 152, 2, 742));
    c.setFillStyle(rgba(234, 231, 210, 200));
    c.fillCircle(BLCircle(dx, 520, 5));

    const double cross = easeInOutCubic(wind(t, 0.22, 0.66));
    const double cx = lerp(690, 1130, cross);
    const double cy = lerp(560, 438, cross);
    c.setStrokeStyle(rgba(238, 235, 213, 90));
    c.setStrokeWidth(1);
    c.strokeLine(BLPoint(cx - 26, cy), BLPoint(cx + 26, cy));
    c.strokeLine(BLPoint(cx, cy - 26), BLPoint(cx, cy + 26));
    c.setFillStyle(rgba(238, 235, 213, 180));
    c.fillCircle(BLCircle(cx, cy, 2.5));

    const char* leftTag = "BEFORE  /  14 MAR 2019";
    const char* rightTag = "AFTER  /  22 NOV 2026";
    c.setFillStyle(rgba(9, 22, 25, 215));
    c.fillRoundRect(BLRoundRect(28, 826, 316, 42, 5, 5));
    c.fillRoundRect(BLRoundRect(1576, 826, 316, 42, 5, 5));
    tracked(c, face("mono", 11), 42, 852, leftTag, rgba(197, 220, 211), 1.1);
    tracked(c, face("mono", 11), 1590, 852, rightTag, rgba(238, 195, 161), 1.1);

    c.setFillStyle(rgba(7, 17, 21, 210));
    c.fillRoundRect(BLRoundRect(28, 892, 1864, 64, 6, 6));
    tracked(c, face("semi", 10), 44, 916, "SAR  /  OPTICAL  /  CHANGE INDEX", rgba(148, 183, 176), 1.4);
    fillText(c, face("reg", 12), 44, 940, "Difference field is illustrative; coordinates are reconstructed for the plate.",
             rgba(139, 157, 152));
    fillText(c, face("mono", 11), 1590, 926, "5,842 KM\u00b2", rgba(209, 228, 218));
    fillText(c, face("mono", 11), 1700, 946, "PASS 041", rgba(139, 172, 166));

    const double a = easeOutCubic(wind(t, 0.46, 0.68));
    pill(c, 746, 176, 428, 40, rgba(190, 49, 42), "CHANGE DETECTED  /  5 HOTSPOTS",
         rgba(255, 238, 233), 11, a);
    if (a > 0.1) {
        c.setFillStyle(rgba(190, 49, 42, 40));
        c.fillRoundRect(BLRoundRect(736, 166, 448, 60, 7, 7));
    }
}

// 10 — Leaked memo. The redaction bar is the animation: it leaves the page and
// exposes the sentence underneath. Everything else is a fixed paper plate.
void d10(BLContext& c, double t, int) {
    camera(c, 1.01, 1.04, 0.50, 0.50, t);
    c.setFillStyle(rgba(20, 16, 12));
    c.fillRect(BLRect(0, 0, kW, kH));
    c.setFillStyle(rgba(36, 28, 20));
    c.fillRoundRect(BLRoundRect(120, 40, 1680, 1010, 18, 18));
    c.setFillStyle(rgba(0, 0, 0, 80));
    c.fillRoundRect(BLRoundRect(232, 78, 1480, 950, 4, 4));
    c.setFillStyle(rgba(242, 234, 216));
    c.fillRect(BLRect(220, 62, 1480, 950));

    c.setFillStyle(rgba(220, 204, 177));
    c.fillRect(BLRect(220, 62, 12, 950));
    c.setFillStyle(rgba(60, 51, 39, 28));
    for (int i = 0; i < 7; ++i) c.fillRect(BLRect(220 + i * 26, 62, 1, 950));

    tracked(c, face("semi", 11), 264, 104, "EYES ONLY  /  INTERNAL REVIEW", rgba(122, 104, 82), 1.8);
    fillText(c, face("serifBold", 44), 264, 156, "MEMORANDUM", rgba(42, 36, 29));
    rule(c, 264, 174, 1370, rgba(71, 58, 43, 90));
    fillText(c, face("mono", 12), 264, 204, "TO:      OFFICE OF THE GENERAL COUNSEL", rgba(71, 62, 50));
    fillText(c, face("mono", 12), 264, 228, "FROM:    [REDACTED]", rgba(71, 62, 50));
    fillText(c, face("mono", 12), 264, 252, "DATE:    18 NOV 2026", rgba(71, 62, 50));
    fillText(c, face("mono", 12), 264, 276, "RE:      TRANSFER AUTHORIZATION  /  APPENDIX C", rgba(71, 62, 50));
    rule(c, 264, 296, 1370, rgba(71, 58, 43, 70));

    const BLFont f = face("serif", 19);
    const BLRgba32 ink = rgba(57, 49, 40);
    fillText(c, f, 264, 340,
             "The review confirms that the transfer described in Appendix C was approved before the", ink);
    fillText(c, f, 264, 368,
             " emergency supplemental certification was issued. The chronology is material because", ink);
    fillText(c, f, 264, 396,
             " the certification triggers the disclosure obligation described in Section 4(b).", ink);
    fillText(c, f, 264, 450,
             "The office should treat the following paragraph as the operative finding:", ink);

    // The exposed sentence; the black bar is drawn later and retracts.
    fillText(c, face("serifBold", 22), 264, 504,
             "the transfer was approved by the deputy director on 12 November,", rgba(41, 35, 28));
    fillText(c, face("serifBold", 22), 264, 534,
             "three days before the certification date.", rgba(41, 35, 28));

    fillText(c, f, 264, 592,
             "The office has identified no written record of the approval. A verbal authorization was", ink);
    fillText(c, f, 264, 620,
             "relayed by the duty officer and logged in the operations channel at 22:41 ET. The log", ink);
    fillText(c, f, 264, 648,
             "has been preserved and is attached as Exhibit 7.", ink);

    c.setFillStyle(rgba(71, 58, 43, 40));
    c.fillRect(BLRect(264, 690, 1360, 1));
    fillText(c, face("semi", 13), 264, 718, "RECOMMENDATION", rgba(79, 65, 50));
    fillText(c, f, 264, 746,
             "Counsel should prepare a supplemental disclosure and preserve the operations log.", ink);
    fillText(c, f, 264, 774,
             "No further distribution without written authorization from the general counsel.", ink);
    fillText(c, face("reg", 11), 264, 966, "PAGE 3 OF 7  /  THIS COPY IS UNCONTROLLED", rgba(112, 96, 78));

    // Redaction bars: all except one are static; one retracts.
    const double retract = easeInOutCubic(wind(t, 0.28, 0.66));
    c.setFillStyle(rgba(14, 13, 12, 245));
    c.fillRect(BLRect(264, 204, 370, 16));
    c.fillRect(BLRect(264, 228, 310, 16));
    c.fillRect(BLRect(264, 252, 434, 16));
    c.fillRect(BLRect(264, 276, 210, 16));
    c.setFillStyle(rgba(14, 13, 12, 235));
    c.fillRect(BLRect(264, 490, 910 * (1.0 - retract), 54));
    c.setFillStyle(rgba(14, 13, 12, 245));
    c.fillRect(BLRect(264, 610, 510, 16));
    c.fillRect(BLRect(264, 638, 640, 16));

    const double scan = 264 + fmod(t * 900.0, 1220.0);
    c.setFillStyle(rgba(183, 76, 55, 20));
    c.fillRect(BLRect(scan, 180, 3, 700));
    c.setFillStyle(rgba(183, 76, 55, 100));
    c.fillRect(BLRect(scan, 180, 1, 700));

    const double s = easeOutCubic(wind(t, 0.50, 0.72));
    stamp(c, 1360, 810, 254, 78, "LEAKED", rgba(174, 52, 43), -8.0, s, 34);
    if (s > 0.01) {
        c.setFillStyle(rgba(174, 52, 43, int(24 * s)));
        c.fillRoundRect(BLRoundRect(1344, 794, 286, 110, 8, 8));
    }

    // Paperclip and a faint coffee ring keep the plate tactile.
    c.save();
    c.setStrokeStyle(rgba(126, 126, 120, 200));
    c.setStrokeWidth(3);
    c.strokeRoundRect(BLRoundRect(1500, 84, 34, 88, 16, 16));
    c.strokeLine(BLPoint(1517, 92), BLPoint(1517, 158));
    c.restore();
    c.setStrokeStyle(rgba(137, 97, 64, 45));
    c.setStrokeWidth(2);
    c.strokeCircle(BLCircle(1220, 760, 80));
    c.strokeCircle(BLCircle(1220, 760, 74));
}

// 11 — Phone lockscreen. Notifications cascade; the newest one expands to
// reveal the docket detail. The phone is authored, not a screenshot.
void d11(BLContext& c, double t, int) {
    camera(c, 1.01, 1.035, 0.50, 0.50, t);
    c.setFillStyle(rgba(4, 5, 8));
    c.fillRect(BLRect(0, 0, kW, kH));
    for (int i = 0; i < 3; ++i) {
        c.setFillStyle(rgba(32, 49, 74, 35 - i * 8));
        c.fillCircle(BLCircle(420 + i * 520, 130 + i * 110, 280));
    }
    c.setFillStyle(rgba(112, 75, 111, 30));
    c.fillCircle(BLCircle(1480, 920, 330));
    tracked(c, face("semi", 10), 80, 1004, "LOCKSCREEN  /  22 NOV 2026", rgba(124, 133, 148), 1.8);

    // Device shell and screen.
    c.setFillStyle(rgba(8, 9, 12));
    c.fillRoundRect(BLRoundRect(660, 30, 600, 1020, 62, 62));
    c.setStrokeStyle(rgba(105, 111, 122, 190));
    c.setStrokeWidth(2);
    c.strokeRoundRect(BLRoundRect(660, 30, 600, 1020, 62, 62));
    c.setFillStyle(rgba(24, 28, 38));
    c.fillRoundRect(BLRoundRect(680, 50, 560, 980, 48, 48));
    c.setFillStyle(rgba(32, 48, 70));
    c.fillRoundRect(BLRoundRect(680, 50, 560, 980, 48, 48));
    c.setFillStyle(rgba(70, 48, 76, 90));
    c.fillCircle(BLCircle(760, 800, 350));
    c.setFillStyle(rgba(35, 84, 102, 80));
    c.fillCircle(BLCircle(1220, 580, 360));
    c.setFillStyle(rgba(8, 10, 14, 50));
    c.fillRect(BLRect(680, 50, 560, 980));

    c.setFillStyle(rgba(2, 3, 5));
    c.fillRoundRect(BLRoundRect(880, 62, 160, 28, 14, 14));
    c.setFillStyle(rgba(236, 239, 242));
    fillText(c, face("semi", 12), 720, 84, "9:41", rgba(242, 244, 247));
    tracked(c, face("semi", 9), 1090, 82, "5G", rgba(215, 225, 235), 0.8);
    for (int i = 0; i < 4; ++i) {
        c.setFillStyle(rgba(232, 237, 241, 190));
        c.fillRect(BLRect(1144 + i * 5, 82 - i * 3, 3, 6 + i * 3));
    }
    c.setStrokeStyle(rgba(232, 237, 241, 190));
    c.setStrokeWidth(1.5);
    c.strokeRoundRect(BLRoundRect(1178, 72, 24, 12, 3, 3));
    c.setFillStyle(rgba(232, 237, 241, 190));
    c.fillRect(BLRect(1181, 75, 16, 6));

    c.setFillStyle(rgba(238, 242, 247));
    textC(c, face("light", 108), 960, 202, "9:41", rgba(240, 243, 247));
    textC(c, face("med", 18), 960, 234, "Sunday, 22 November", rgba(222, 228, 235));
    c.setStrokeStyle(rgba(231, 237, 242, 190));
    c.setStrokeWidth(3);
    c.strokeRoundRect(BLRoundRect(1002, 260, 36, 28, 8, 8));
    c.strokeCircle(BLCircle(1020, 262, 12));

    const double expand = easeInOutCubic(wind(t, 0.38, 0.70));
    const double enter = easeOutCubic(wind(t, 0.08, 0.34));
    const double cw = 504;
    const double cx = 708;

    auto notification = [&](double y, double h, double alpha, const char* app,
                            const char* time, const char* title, const char* body,
                            BLRgba32 accent, const char* glyph) {
        if (alpha <= 0.01) return;
        c.save();
        c.setGlobalAlpha(float(alpha));
        c.setFillStyle(rgba(24, 27, 35, 225));
        c.fillRoundRect(BLRoundRect(cx, y, cw, h, 20, 20));
        c.setStrokeStyle(rgba(255, 255, 255, 22));
        c.setStrokeWidth(1);
        c.strokeRoundRect(BLRoundRect(cx, y, cw, h, 20, 20));
        c.setFillStyle(accent);
        c.fillRoundRect(BLRoundRect(cx + 20, y + 18, 38, 38, 10, 10));
        textC(c, face("black", 15), cx + 39, y + 44, glyph, rgba(255, 255, 255));
        tracked(c, face("semi", 10), cx + 72, y + 32, app, rgba(198, 205, 215), 1.3);
        fillText(c, face("reg", 11), cx + cw - 58, y + 32, time, rgba(151, 162, 175));
        fillText(c, face("semi", 15), cx + 72, y + 56, title, rgba(243, 246, 249));
        fillText(c, face("reg", 13), cx + 72, y + 80, body, rgba(181, 190, 201));
        c.restore();
    };

    const double topH = 124 + 72 * expand;
    const double topY = 320 + (1.0 - enter) * 42;
    const double card2Y = topY + topH + 16 + (1.0 - enter) * 24;
    notification(card2Y, 104, enter, "ARCHIVE ALERT", "22:39",
                 "Snapshot saved", "The 2014 page is still reachable.",
                 rgba(77, 117, 163), "A");
    const double card3Y = card2Y + 120 + (1.0 - enter) * 36;
    notification(card3Y, 104, enter * 0.95, "COURT FILINGS", "22:40",
                 "New entry on the docket", "Entry 004 is now visible.",
                 rgba(138, 88, 151), "C");
    notification(topY, topH, enter, "THE WIRE", "now",
                 "The docket was unsealed",
                 expand > 0.3 ? "Two exhibits remain sealed." : "Tap to read the update.",
                 rgba(190, 49, 42), "W");
    if (expand > 0.05) {
        c.save();
        c.setGlobalAlpha(float(expand));
        c.setFillStyle(rgba(228, 234, 241, 190));
        c.fillRect(BLRect(cx + 72, topY + 96, cw - 96, 1));
        fillText(c, face("reg", 12), cx + 72, topY + 122,
                 "The clerk's office released entries 001-004 at 22:41 ET.", rgba(198, 207, 218));
        fillText(c, face("semi", 11), cx + 72, topY + 148,
                 "OPEN LIVE BLOG  \u2192", rgba(116, 189, 203));
        c.restore();
    }

    c.setFillStyle(rgba(235, 240, 246, 200));
    c.fillCircle(BLCircle(960, 886, 3));
    c.setFillStyle(rgba(235, 240, 246, 130));
    c.fillRoundRect(BLRoundRect(922, 934, 76, 5, 2, 2));
    c.setFillStyle(rgba(235, 240, 246, 120));
    c.fillCircle(BLCircle(852, 984, 22));
    c.fillCircle(BLCircle(912, 984, 22));
    c.fillCircle(BLCircle(972, 984, 22));
    c.setFillStyle(rgba(235, 240, 246, 42));
    c.fillRoundRect(BLRoundRect(838, 972, 28, 24, 6, 6));
    c.setFillStyle(rgba(235, 240, 246, 42));
    c.fillRoundRect(BLRoundRect(900, 972, 24, 24, 12, 12));
    c.setFillStyle(rgba(235, 240, 246, 42));
    c.fillRoundRect(BLRoundRect(958, 972, 28, 24, 6, 6));
}

// 12 — YouTube-style watch page. The video plate stays quiet; the transcript
// selection and progress are the moving evidence.
void d12(BLContext& c, double t, int) {
    camera(c, 1.01, 1.035, 0.50, 0.49, t);
    c.setFillStyle(rgba(12, 13, 15));
    c.fillRect(BLRect(0, 0, kW, kH));
    browserChrome(c, "video.example.org/watch?v=ruling-22-11", true, "WATCH");

    // Video frame.
    c.setFillStyle(rgba(24, 25, 28));
    c.fillRoundRect(BLRoundRect(54, 100, 1130, 636, 12, 12));
    c.save();
    c.setFillStyle(rgba(74, 91, 106, 90));
    c.fillCircle(BLCircle(330, 380, 280));
    c.setFillStyle(rgba(126, 80, 70, 65));
    c.fillCircle(BLCircle(820, 320, 310));
    c.setFillStyle(rgba(36, 51, 60, 120));
    c.fillRoundRect(BLRoundRect(54, 100, 1130, 636, 12, 12));
    c.setFillStyle(rgba(8, 9, 11, 90));
    for (int i = 0; i < 7; ++i)
        c.fillRoundRect(BLRoundRect(100 + i * 150, 160 + (i % 3) * 86, 96, 400, 30, 30));
    c.restore();

    tracked(c, face("semi", 10), 86, 158, "THE WIRE  /  FIELD REPORT", rgba(191, 199, 207), 1.5);
    fillText(c, face("serifBold", 48), 86, 214, "The docket, unsealed", rgba(242, 244, 246));
    fillText(c, face("reg", 16), 86, 244,
             "A reading of the order with the reporting team.", rgba(189, 198, 207));

    c.setFillStyle(rgba(245, 247, 248, 235));
    c.fillCircle(BLCircle(620, 470, 44));
    BLPath play;
    play.moveTo(610, 450);
    play.lineTo(610, 490);
    play.lineTo(641, 470);
    play.close();
    c.setFillStyle(rgba(18, 20, 22));
    c.fillPath(play);

    c.setFillStyle(rgba(8, 9, 11, 205));
    c.fillRoundRect(BLRoundRect(86, 666, 1066, 42, 21, 21));
    c.setFillStyle(rgba(255, 255, 255, 30));
    c.fillRoundRect(BLRoundRect(110, 684, 1018, 5, 2, 2));
    c.setFillStyle(rgba(226, 56, 56));
    c.fillRoundRect(BLRoundRect(110, 684, 340 + 600 * easeInOutCubic(t), 5, 2, 2));
    c.setFillStyle(rgba(235, 239, 243));
    c.fillCircle(BLCircle(450 + 600 * easeInOutCubic(t), 686, 7));
    fillText(c, face("mono", 10), 112, 706, "01:18", rgba(198, 205, 212));
    fillText(c, face("mono", 10), 1060, 706, "04:28", rgba(198, 205, 212));

    c.setFillStyle(rgba(22, 24, 27));
    c.fillRect(BLRect(54, 778, 1130, 1));
    fillText(c, face("semi", 17), 54, 812, "The docket was unsealed at 22:41", rgba(231, 235, 239));
    fillText(c, face("reg", 13), 54, 836, "312K views  \u00b7  1 hour ago", rgba(143, 153, 164));
    c.setFillStyle(rgba(190, 49, 42));
    c.fillRoundRect(BLRoundRect(54, 858, 74, 28, 14, 14));
    tracked(c, face("semi", 10), 70, 876, "LIVE", rgba(255, 240, 235), 1.0);
    fillText(c, face("reg", 12), 144, 878, "Clip 04  /  transcript tracked", rgba(137, 147, 158));

    // Transcript panel.
    c.setFillStyle(rgba(24, 26, 29));
    c.fillRoundRect(BLRoundRect(1210, 100, 656, 860, 12, 12));
    tracked(c, face("semi", 10), 1234, 132, "TRANSCRIPT", rgba(152, 162, 174), 1.5);
    fillText(c, face("semi", 16), 1234, 160, "Auto-generated  /  EN", rgba(224, 229, 235));
    c.setFillStyle(rgba(60, 64, 70));
    c.fillRoundRect(BLRoundRect(1234, 178, 1, 740, 1, 1));
    const char* rows[] = {
        "The clerk's office has released the",
        "order in full. Entries 001 through",
        "004 are now public. Two exhibits",
        "remain sealed. The court says the",
        "redactions protect an ongoing",
        "investigation, not the parties.",
    };
    const int active = 2;
    const double slide = easeInOutCubic(wind(t, 0.12, 0.62));
    const double activeY = 232 + (active * 94.0) + 14 * std::sin(t * 5.0);
    c.setFillStyle(rgba(227, 54, 54, 20));
    c.fillRoundRect(BLRoundRect(1218, activeY - 20, 612, 80, 7, 7));
    c.setFillStyle(rgba(227, 54, 54, 180));
    c.fillRect(BLRect(1218, activeY - 20, 3, 80));
    for (int i = 0; i < 6; ++i) {
        const double y = 232 + i * 94;
        fillText(c, face("mono", 10), 1234, y, i < 3 ? "0:42" : "1:18", rgba(121, 132, 145));
        fillText(c, face(i == active ? "med" : "reg", 14), 1288, y, rows[i],
                 i == active ? rgba(241, 244, 247) : rgba(183, 191, 200));
        if (i == active) {
            c.setFillStyle(rgba(190, 49, 42));
            c.fillRect(BLRect(1288, y + 10, 164 * slide, 2));
        }
    }
    c.setFillStyle(rgba(255, 255, 255, 14));
    c.fillRoundRect(BLRoundRect(1234, 860, 600, 54, 7, 7));
    fillText(c, face("reg", 11), 1252, 884, "Transcripts are generated automatically.", rgba(134, 145, 157));
    fillText(c, face("semi", 11), 1252, 904, "REPORT AN ERROR", rgba(199, 208, 218));
    fillText(c, face("mono", 11), 1700, 904, "EN", rgba(199, 208, 218));

    c.setFillStyle(rgba(227, 54, 54, 40));
    c.fillCircle(BLCircle(960, 632, 34));
}

// 13 — Forum thread. The locked thread has one new reply; the vote count
// climbs as the reply enters. No platform logo or screenshot is used.
void d13(BLContext& c, double t, int) {
    camera(c, 1.01, 1.035, 0.50, 0.49, t);
    c.setFillStyle(rgba(18, 18, 19));
    c.fillRect(BLRect(0, 0, kW, kH));
    browserChrome(c, "forum.example.org/r/archive/comments/26fh4", true, "THREAD");
    c.setFillStyle(rgba(24, 24, 25));
    c.fillRect(BLRect(0, 64, kW, 58));

    c.setFillStyle(rgba(205, 84, 36));
    c.fillCircle(BLCircle(92, 94, 10));
    tracked(c, face("semi", 11), 112, 99, "FORUM  /  r/archive", rgba(214, 218, 221), 1.4);
    fillText(c, face("reg", 12), 1590, 99, "Search the archive", rgba(133, 139, 144));
    searchIcon(c, 1570, 94, 5, rgba(133, 139, 144), 1.4);

    c.setFillStyle(rgba(26, 26, 27));
    c.fillRoundRect(BLRoundRect(180, 150, 1230, 870, 10, 10));
    c.setFillStyle(rgba(255, 255, 255, 10));
    c.fillRoundRect(BLRoundRect(206, 176, 1178, 818, 8, 8));

    arrowUp(c, 260, 236, 34, rgba(205, 84, 36));
    const double count = 1200 + 3600 * easeOutCubic(wind(t, 0.16, 0.70));
    textC(c, face("semi", 18), 260, 286, std::to_string(int(count)), rgba(224, 227, 230));
    fillText(c, face("reg", 10), 246, 306, "upvotes", rgba(126, 132, 138));

    c.setFillStyle(rgba(255, 255, 255, 18));
    c.fillCircle(BLCircle(330, 224, 15));
    fillText(c, face("semi", 11), 330, 228, "OP", rgba(205, 84, 36));
    tracked(c, face("reg", 10), 354, 228, "u/archive_watch  \u00b7  3h", rgba(128, 134, 140), 0.7, 1.0);
    pill(c, 1450, 202, 111, 30, rgba(65, 65, 67), "LOCKED", rgba(213, 217, 221), 10);

    fillText(c, face("serifBold", 31), 330, 278,
             "The docket was unsealed, but the exhibits are still sealed", rgba(237, 239, 241));
    fillText(c, face("reg", 14), 330, 310,
             "The clerk's PDF is up. Entries 001-004 are visible. Two exhibits remain behind the", rgba(184, 190, 196));
    fillText(c, face("reg", 14), 330, 332,
             "protective order. I pulled the snapshot from 22:41, before the page changed again.", rgba(184, 190, 196));
    c.setFillStyle(rgba(83, 146, 160, 30));
    c.fillRoundRect(BLRoundRect(330, 354, 1010, 82, 6, 6));
    fillText(c, face("mono", 11), 350, 380, "courtlistener.com/docket/1:26-cr-00418", rgba(108, 187, 199));
    fillText(c, face("reg", 12), 350, 402, "Last captured 22:41:08 ET  \u00b7  text/html  \u00b7  41 KB", rgba(150, 159, 168));
    fillText(c, face("reg", 11), 350, 422, "No paywall. No login.", rgba(150, 159, 168));

    rule(c, 330, 470, 1010, rgba(255, 255, 255, 20));
    fillText(c, face("semi", 14), 330, 500, "34 comments  \u00b7  sorted by new", rgba(160, 166, 172));

    struct Comment { const char* user; const char* time; const char* text; };
    const Comment comments[] = {
        {"u/marginalia", "2h", "The Exhibit 7 log is the interesting part. It is not a court record."},
        {"u/redaction_desk", "1h", "Entry 004 is dated before the certification. That is the whole ballgame."},
    };
    for (int i = 0; i < 2; ++i) {
        const double y = 548 + i * 104;
        c.setFillStyle(rgba(255, 255, 255, 7));
        c.fillRoundRect(BLRoundRect(330, y, 1010, 84, 6, 6));
        c.setFillStyle(rgba(105, 123, 140));
        c.fillCircle(BLCircle(354, y + 24, 10));
        fillText(c, face("semi", 11), 372, y + 27, comments[i].user, rgba(143, 151, 158));
        fillText(c, face("reg", 10), 490, y + 27, comments[i].time, rgba(113, 120, 127));
        fillText(c, face("reg", 13), 354, y + 54, comments[i].text, rgba(202, 207, 212));
    }

    const double slide = easeInOutCubic(wind(t, 0.30, 0.70));
    const double ny = 774 + (1.0 - slide) * 90;
    c.save();
    c.setGlobalAlpha(float(slide));
    c.setFillStyle(rgba(205, 84, 36, 20));
    c.fillRoundRect(BLRoundRect(330, ny, 1010, 132, 6, 6));
    c.setFillStyle(rgba(205, 84, 36, 180));
    c.fillRect(BLRect(330, ny, 3, 132));
    c.setFillStyle(rgba(255, 255, 255, 14));
    c.fillCircle(BLCircle(354, ny + 24, 10));
    fillText(c, face("semi", 11), 372, ny + 27, "u/chronon_reader", rgba(238, 168, 128));
    fillText(c, face("reg", 10), 500, ny + 27, "now", rgba(149, 128, 116));
    fillText(c, face("reg", 13), 354, ny + 54,
             "The snapshot diff is now in the Wayback calendar. 14 captures, one changed paragraph.", rgba(214, 214, 211));
    fillText(c, face("reg", 11), 354, ny + 78,
             "The changed line is the supplemental-funds treatment.", rgba(165, 165, 161));
    pill(c, 354, ny + 94, 110, 24, rgba(205, 84, 36), "NEW REPLY", rgba(255, 244, 236), 9);
    c.restore();

    // Sidebar.
    c.setFillStyle(rgba(26, 26, 27));
    c.fillRoundRect(BLRoundRect(1440, 150, 320, 360, 10, 10));
    tracked(c, face("semi", 10), 1464, 180, "ABOUT THIS THREAD", rgba(132, 138, 144), 1.4);
    fillText(c, face("serifBold", 23), 1464, 214, "Archive watch", rgba(232, 235, 238));
    fillText(c, face("reg", 12), 1464, 240, "Public records, versioned.", rgba(149, 155, 161));
    rule(c, 1464, 258, 272, rgba(255, 255, 255, 22));
    fillText(c, face("reg", 12), 1464, 284, "Created  /  14 Oct 2026", rgba(149, 155, 161));
    fillText(c, face("reg", 12), 1464, 306, "Members  /  18.4K", rgba(149, 155, 161));
    fillText(c, face("reg", 12), 1464, 328, "Online   /  241", rgba(149, 155, 161));
    pill(c, 1464, 350, 136, 30, rgba(255, 255, 255, 20), "JOIN THREAD", rgba(225, 229, 232), 9);
    fillText(c, face("reg", 10), 1464, 414, "Moderated by u/chronon", rgba(116, 123, 129));
    fillText(c, face("reg", 10), 1464, 432, "No screenshots. Link the record.", rgba(116, 123, 129));
}

// 14 — Press release. A wire page with a moving distribution ticker; the
// headline and dateline are deliberately quiet so the ticker carries motion.
void d14(BLContext& c, double t, int) {
    camera(c, 1.01, 1.035, 0.50, 0.50, t);
    paper(c, rgba(252, 251, 249), 30);
    browserChrome(c, "newswire.example.org/release/2026/11/22/transfer/", false, "RELEASE");

    tracked(c, face("black", 14), 120, 110, "NEWSWIRE", rgba(20, 32, 49), 2.2);
    c.setFillStyle(rgba(190, 49, 42));
    c.fillCircle(BLCircle(242, 105, 4));
    tracked(c, face("reg", 10), 260, 109, "PUBLIC INTEREST  /  NO EMBARGO", rgba(116, 111, 102), 1.3);
    rule(c, 120, 126, 1680, rgba(29, 36, 42, 70));

    c.setFillStyle(rgba(190, 49, 42));
    c.fillRoundRect(BLRoundRect(120, 154, 184, 30, 4, 4));
    tracked(c, face("semi", 10), 134, 174, "FOR IMMEDIATE RELEASE", rgba(255, 241, 236), 1.2);
    const double underline = easeInOutCubic(wind(t, 0.10, 0.40));
    c.setFillStyle(rgba(190, 49, 42, 200));
    c.fillRect(BLRect(120, 184, 1680 * underline, 2));

    fillText(c, face("serifBold", 48), 120, 248,
             "Transfer authorization was approved before", kInk);
    fillText(c, face("serifBold", 48), 120, 300,
             "the emergency certification, memo shows", kInk);
    fillText(c, face("reg", 14), 120, 330,
             "WASHINGTON, D.C., Nov. 22, 2026 \u2014 The Office of the General Counsel today released", rgba(85, 82, 74));
    fillText(c, face("reg", 14), 120, 352,
             "a redacted memorandum describing the timing of a contested transfer authorization.", rgba(85, 82, 74));

    c.setFillStyle(rgba(255, 255, 255, 130));
    c.fillRoundRect(BLRoundRect(120, 390, 1130, 300, 8, 8));
    fillText(c, face("serifItalic", 28), 150, 440,
             "\u201cThe chronology is material because the", rgba(47, 45, 39));
    fillText(c, face("serifItalic", 28), 150, 474,
             "certification triggers the disclosure", rgba(47, 45, 39));
    fillText(c, face("serifItalic", 28), 150, 508,
             "obligation described in Section 4(b).\u201d", rgba(47, 45, 39));
    fillText(c, face("reg", 11), 150, 548, "EXCERPT  /  MEMORANDUM, PAGE 3", rgba(120, 113, 101));
    c.setFillStyle(rgba(190, 49, 42));
    c.fillRect(BLRect(150, 562, 62, 2));
    fillText(c, face("reg", 13), 150, 596,
             "The office said it would prepare a supplemental disclosure and preserve the operations log.", rgba(88, 84, 76));
    fillText(c, face("reg", 13), 150, 618,
             "No further distribution was authorized without written approval from the general counsel.", rgba(88, 84, 76));

    c.setFillStyle(rgba(255, 255, 255, 130));
    c.fillRoundRect(BLRoundRect(1280, 390, 520, 300, 8, 8));
    tracked(c, face("semi", 10), 1304, 420, "DISTRIBUTION", rgba(117, 111, 101), 1.4);
    const double dist = easeOutCubic(wind(t, 0.30, 0.72));
    fillText(c, face("serifBold", 58), 1304, 480,
             std::to_string(int(4218 * dist)), rgba(29, 37, 48));
    fillText(c, face("reg", 13), 1304, 504, "outlets reached", rgba(107, 103, 94));
    rule(c, 1304, 526, 464, rgba(44, 45, 41, 28));
    fillText(c, face("reg", 12), 1304, 552, "Region  /  North America", rgba(95, 91, 83));
    fillText(c, face("reg", 12), 1304, 574, "Language  /  English", rgba(95, 91, 83));
    fillText(c, face("reg", 12), 1304, 596, "Embargo  /  None", rgba(95, 91, 83));
    pill(c, 1304, 626, 142, 28, rgba(29, 37, 48), "VERIFIED WIRE", rgba(236, 241, 245), 9);

    rule(c, 120, 718, 1680, rgba(44, 45, 41, 24));
    tracked(c, face("semi", 10), 120, 746, "ABOUT THE RELEASE", rgba(117, 111, 101), 1.3);
    fillText(c, face("reg", 12), 120, 770,
             "This is a native reconstruction of a wire layout. It is not a source document and does not", rgba(98, 94, 85));
    fillText(c, face("reg", 12), 120, 790,
             "represent an official statement. Contact: press desk, extension 418.", rgba(98, 94, 85));

    // Ticker.
    c.setFillStyle(rgba(16, 26, 37));
    c.fillRect(BLRect(0, 1004, kW, 76));
    c.setFillStyle(rgba(190, 49, 42));
    c.fillRect(BLRect(0, 1004, 206, 76));
    tracked(c, face("semi", 11), 22, 1032, "NEWSWIRE", rgba(255, 241, 236), 1.7);
    tracked(c, face("mono", 10), 22, 1056, "MARKET  /  LIVE", rgba(255, 192, 184), 1.1);
    const std::string ticker =
        "  NGS  +4.2%   |   TRANSFER MEMO RELEASED   |   COURT DOCKET 1:26-CR-00418   |   "
        "SUPPLEMENTAL DISCLOSURE EXPECTED   |   ARCHIVE SNAPSHOT 22:41 ET  ";
    const double x = 224 - fmod(t * 2100.0, 1600.0);
    fillText(c, face("mono", 13), x, 1046, ticker, rgba(215, 225, 232));
    fillText(c, face("mono", 13), x + 1600, 1046, ticker, rgba(215, 225, 232));
    fillText(c, face("mono", 10), 1776, 1030, "22:41 ET", rgba(143, 161, 173));

    const double s = easeOutCubic(wind(t, 0.48, 0.68));
    stamp(c, 1510, 150, 214, 60, "WIRE", rgba(190, 49, 42), -7.0, s, 25);
}

} // namespace

std::vector<Scene> scenesB() {
    return {
        {"d08_data_chart_annotation", "Data & verification",
         "Data desk with a native line chart, endpoint pulse and annotation",
         0.86, d08},
        {"d09_satellite_before_after", "Data & verification",
         "Split before/after field plate with moving scan divider and hotspots",
         0.84, d09},
        {"d10_leaked_memo_redaction", "Evidence & courts",
         "Leaked memo: the redaction bar retracts to expose the finding",
         0.86, d10},
        {"d11_phone_alerts", "Interface & field",
         "Lock-screen alert stack: the newest notification expands",
         0.86, d11},
        {"d12_youtube_transcript", "Live & broadcast",
         "Watch page with a live transcript rail and moving selection",
         0.84, d12},
        {"d13_forum_thread", "Interface & field",
         "Locked forum thread with climbing votes and a new reply",
         0.86, d13},
        {"d14_press_release_wire", "Live & broadcast",
         "Newswire release with distribution count and scrolling ticker",
         0.84, d14},
    };
}

} // namespace chronon::docshots
