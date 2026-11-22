// d15-d20 — budget, archive, document UI, mail, audio and geography.

#include "doc_pack.hpp"

#include <cstdio>
#include <sstream>

namespace chronon::docshots {

namespace {

const BLRgba32 kInk = rgba(24, 25, 27);
const BLRgba32 kMuted = rgba(107, 106, 100);
const BLRgba32 kGreen = rgba(47, 119, 84);
const BLRgba32 kRed = rgba(188, 51, 44);
const BLRgba32 kBlue = rgba(49, 103, 174);

// 15 — Budget table. Rows scan; bars grow in the last column. The total is a
// fixed reading, so the motion lives in the comparison, not a fake count-up.
void d15(BLContext& c, double t, int) {
    camera(c, 1.01, 1.04, 0.48, 0.50, t);
    paper(c, rgba(249, 247, 242), 34);
    browserChrome(c, "omb.example.gov/budget/fy2027/outlays", false, "BUDGET");

    tracked(c, face("semi", 11), 90, 110, "FISCAL YEAR 2027  /  OUTLAYS", rgba(109, 104, 94), 1.6);
    fillText(c, face("serifBold", 40), 90, 154, "The budget, line by line", kInk);
    fillText(c, face("reg", 14), 90, 182,
             "Discretionary and emergency authority in billions of dollars. Delta is against the request.",
             rgba(105, 101, 92));

    c.setFillStyle(rgba(255, 255, 255, 155));
    c.fillRoundRect(BLRoundRect(80, 222, 1370, 700, 9, 9));
    c.setFillStyle(rgba(255, 255, 255, 130));
    c.fillRoundRect(BLRoundRect(1480, 222, 360, 700, 9, 9));

    tracked(c, face("semi", 10), 108, 254, "AGENCY", rgba(115, 110, 100), 1.3);
    tracked(c, face("semi", 10), 668, 254, "REQUESTED", rgba(115, 110, 100), 1.3);
    tracked(c, face("semi", 10), 862, 254, "ENACTED", rgba(115, 110, 100), 1.3);
    tracked(c, face("semi", 10), 1056, 254, "DELTA", rgba(115, 110, 100), 1.3);
    tracked(c, face("semi", 10), 1210, 254, "SHARE OF CHANGE", rgba(115, 110, 100), 1.3);
    rule(c, 108, 268, 1314, rgba(45, 44, 39, 45));

    struct Row { const char* agency; const char* requested; const char* enacted;
                 const char* delta; bool up; double bar; };
    const Row rows[] = {
        {"Defense", "842.1", "861.4", "+2.3%", true, 0.74},
        {"Health & Human Services", "612.8", "604.2", "-1.4%", false, 0.61},
        {"Grid Security Initiative", "48.2", "51.6", "+7.1%", true, 0.26},
        {"Emergency Supplemental", "40.0", "40.0", "0.0%", true, 0.20},
        {"Science & Research", "92.4", "88.9", "-3.8%", false, 0.35},
    };
    const double rowH = 92;
    for (int i = 0; i < 5; ++i) {
        const double y = 286 + i * rowH;
        if (i == 1) {
            const double hi = easeInOutCubic(wind(t, 0.10, 0.44));
            c.setFillStyle(rgba(54, 111, 186, 14));
            c.fillRoundRect(BLRoundRect(96, y - 6, 1338, 78, 6, 6));
            c.setFillStyle(rgba(54, 111, 186, int(100 * hi)));
            c.fillRect(BLRect(96, y - 6, 3, 78));
        }
        fillText(c, face("med", 15), 108, y + 30, rows[i].agency, rgba(54, 54, 49));
        fillText(c, face("mono", 13), 668, y + 30, rows[i].requested, rgba(92, 91, 84));
        fillText(c, face("mono", 13), 862, y + 30, rows[i].enacted, rgba(38, 40, 37));
        fillText(c, face("mono", 12), 1056, y + 30, rows[i].delta,
                 rows[i].up ? kGreen : kRed);
        c.setFillStyle(rgba(39, 43, 40, 16));
        c.fillRoundRect(BLRoundRect(1210, y + 18, 198, 12, 6, 6));
        const double bar = easeOutCubic(wind(t, 0.18 + i * 0.05, 0.54 + i * 0.05));
        c.setFillStyle(rows[i].up ? rgba(47, 119, 84, 190) : rgba(188, 51, 44, 175));
        c.fillRoundRect(BLRoundRect(1210, y + 18, 198 * rows[i].bar * bar, 12, 6, 6));
        rule(c, 108, y + rowH - 8, 1314, rgba(45, 44, 39, 22));
    }
    const double totalY = 770;
    rule(c, 108, totalY, 1314, rgba(45, 44, 39, 65));
    fillText(c, face("semi", 16), 108, totalY + 38, "TOTAL DISCRETIONARY", kInk);
    fillText(c, face("mono", 13), 668, totalY + 38, "1,635.5", rgba(72, 71, 65));
    fillText(c, face("mono", 13), 862, totalY + 38, "1,646.1", rgba(38, 40, 37));
    fillText(c, face("mono", 13), 1056, totalY + 38, "+0.6%", kGreen);
    fillText(c, face("reg", 11), 108, totalY + 64,
             "Totals may not sum due to rounding. Emergency authority is shown separately in the source table.",
             rgba(119, 114, 104));

    tracked(c, face("semi", 10), 1504, 254, "TOTAL ENACTED", rgba(115, 110, 100), 1.4);
    fillText(c, face("serifBold", 45), 1504, 310, "1,868.4", rgba(30, 40, 48));
    fillText(c, face("reg", 13), 1504, 334, "USD billions", rgba(112, 107, 98));
    c.setFillStyle(rgba(39, 43, 40, 18));
    c.fillRoundRect(BLRoundRect(1504, 364, 296, 18, 9, 9));
    c.setFillStyle(rgba(47, 119, 84, 200));
    c.fillRoundRect(BLRoundRect(1504, 364, 296 * easeOutCubic(wind(t, 0.30, 0.72)), 18, 9, 9));
    fillText(c, face("reg", 11), 1504, 402, "4.8% above the 2025 enacted level", rgba(98, 95, 86));
    rule(c, 1504, 426, 296, rgba(45, 44, 39, 24));

    tracked(c, face("semi", 10), 1504, 458, "LARGEST DELTA", rgba(115, 110, 100), 1.3);
    fillText(c, face("serifBold", 26), 1504, 494, "Grid Security", kInk);
    fillText(c, face("mono", 14), 1504, 520, "+7.1%", kGreen);
    fillText(c, face("reg", 12), 1504, 544, "The smallest line, the largest move.", rgba(105, 101, 92));
    rule(c, 1504, 574, 296, rgba(45, 44, 39, 24));

    tracked(c, face("semi", 10), 1504, 606, "READING", rgba(115, 110, 100), 1.3);
    fillText(c, face("reg", 12), 1504, 632, "The emergency line is flat, but its", rgba(95, 92, 84));
    fillText(c, face("reg", 12), 1504, 652, "treatment changes in the footnote.", rgba(95, 92, 84));
    fillText(c, face("reg", 12), 1504, 672, "Defense absorbs most of the increase.", rgba(95, 92, 84));

    rule(c, 1504, 724, 296, rgba(45, 44, 39, 24));
    fillText(c, face("mono", 10), 1504, 752, "FY 2027  /  OMB TABLE 3", rgba(122, 117, 107));
    fillText(c, face("mono", 10), 1504, 770, "PAGE 18 OF 214", rgba(122, 117, 107));
    fillText(c, face("reg", 10), 80, 966, "SOURCE: OFFICE OF MANAGEMENT AND BUDGET, ENACTED OUTLAYS, NOVEMBER 2026",
             rgba(121, 116, 107));
    fillText(c, face("reg", 10), 1540, 966, "FIG. 2", rgba(121, 116, 107));
}

// 16 — Obituary archive. Newsprint, a procedural halftone portrait and an
// archive stamp. The portrait develops during the first half of the beat.
void d16(BLContext& c, double t, int) {
    camera(c, 1.01, 1.04, 0.50, 0.50, t);
    c.setFillStyle(rgba(231, 223, 207));
    c.fillRect(BLRect(0, 0, kW, kH));
    c.setFillStyle(rgba(244, 238, 226, 65));
    c.fillRect(BLRect(38, 28, kW - 76, kH - 56));
    c.setFillStyle(rgba(18, 18, 17));
    c.fillRect(BLRect(0, 0, kW, 12));
    rule(c, 70, 58, kW - 140, rgba(34, 32, 28, 120), 1.0);

    textC(c, face("serifBold", 40), 960, 104, "THE DAILY ARCHIVE", rgba(31, 30, 27));
    fillText(c, face("reg", 11), 70, 128, "SATURDAY, 14 MARCH 1998", rgba(89, 84, 74));
    fillText(c, face("reg", 11), 1750, 128, "SECTION B  /  PAGE 7", rgba(89, 84, 74), 0.0);
    rule(c, 70, 142, 1780, rgba(34, 32, 28, 90));

    tracked(c, face("semi", 11), 100, 190, "OBITUARIES", rgba(146, 54, 42), 2.2);
    fillText(c, face("serifBold", 54), 100, 252, "A life measured", kInk);
    fillText(c, face("serifBold", 54), 100, 310, "in documents", kInk);
    fillText(c, face("serifItalic", 24), 100, 350,
             "The archivist who taught a generation to read the footnotes.", rgba(78, 72, 62));
    fillText(c, face("mono", 12), 100, 386, "1938  \u2014  2026", rgba(112, 103, 89));

    rule(c, 100, 410, 1180, rgba(34, 32, 28, 60));
    const BLFont body = face("serif", 16);
    const BLRgba32 bodyInk = rgba(55, 50, 42);
    fillText(c, body, 100, 442,
             "She began in the basement of a county courthouse, where the", bodyInk);
    fillText(c, body, 100, 466,
             "records were stored in cardboard and the index was a hand-", bodyInk);
    fillText(c, body, 100, 490,
             "written ledger. By the time she retired, the same records were", bodyInk);
    fillText(c, body, 100, 514,
             "searchable, mirrored and cited in three national investigations.", bodyInk);
    fillText(c, body, 100, 550,
             "Her rule was simple: a document is not a fact until you know", bodyInk);
    fillText(c, body, 100, 574,
             "who kept it, who changed it and who was allowed to read it.", bodyInk);
    fillText(c, body, 100, 610,
             "She kept a card index of every request she filed. The cards", bodyInk);
    fillText(c, body, 100, 634,
             "were color-coded: green for released, red for refused, yellow", bodyInk);
    fillText(c, body, 100, 658,
             "for the ones that came back with entire pages missing.", bodyInk);
    fillText(c, body, 100, 694,
             "Her family said the archive will remain open by appointment.", bodyInk);

    // Second column.
    c.setFillStyle(rgba(34, 32, 28, 36));
    c.fillRect(BLRect(646, 410, 1, 300));
    fillText(c, face("serifBold", 19), 676, 442,
             "The last request", kInk);
    fillText(c, body, 676, 470,
             "In January, she filed for the", bodyInk);
    fillText(c, body, 676, 494,
             "operations log of a transfer", bodyInk);
    fillText(c, body, 676, 518,
             "authorization. The request was", bodyInk);
    fillText(c, body, 676, 542,
             "acknowledged, then placed on", bodyInk);
    fillText(c, body, 676, 566,
             "administrative hold. She told", bodyInk);
    fillText(c, body, 676, 590,
             "her students that the hold was", bodyInk);
    fillText(c, body, 676, 614,
             "the story, not the obstacle.", bodyInk);
    fillText(c, body, 676, 638,
             "The log was released on the", bodyInk);
    fillText(c, body, 676, 662,
             "day she died. It was three", bodyInk);
    fillText(c, body, 676, 686,
             "pages long. One line was", bodyInk);
    fillText(c, body, 676, 710,
             "redacted.", bodyInk);
    fillText(c, face("reg", 10), 676, 742, "CONTINUED ON B8", rgba(114, 104, 89));

    // Halftone portrait.
    const double reveal = easeOutCubic(wind(t, 0.10, 0.54));
    c.save();
    c.setGlobalAlpha(float(reveal));
    c.setFillStyle(rgba(48, 46, 42));
    c.fillRect(BLRect(1270, 186, 400, 470));
    c.setFillStyle(rgba(206, 195, 174));
    c.fillRect(BLRect(1282, 198, 376, 446));
    // A head-and-shoulders archival portrait, not a generic blob: hair,
    // face, neck, collar and a low-contrast halftone screen.
    c.setFillStyle(rgba(196, 183, 160));
    c.fillEllipse(BLEllipse(1470, 390, 212, 216));
    c.setFillStyle(rgba(68, 61, 51));
    c.fillEllipse(BLEllipse(1470, 566, 170, 74));
    c.setFillStyle(rgba(98, 87, 71));
    c.fillEllipse(BLEllipse(1470, 546, 148, 58));
    c.setFillStyle(rgba(166, 145, 118));
    c.fillRect(BLRect(1444, 424, 52, 92));
    c.setFillStyle(rgba(187, 165, 137));
    c.fillEllipse(BLEllipse(1470, 350, 74, 96));
    c.setFillStyle(rgba(79, 69, 55));
    c.fillEllipse(BLEllipse(1470, 306, 82, 54));
    c.fillEllipse(BLEllipse(1470, 344, 86, 42));
    c.setFillStyle(rgba(187, 165, 137));
    c.fillEllipse(BLEllipse(1470, 368, 60, 74));
    c.setFillStyle(rgba(177, 153, 127));
    c.fillEllipse(BLEllipse(1396, 360, 11, 19));
    c.fillEllipse(BLEllipse(1544, 360, 11, 19));
    c.setFillStyle(rgba(88, 76, 62));
    c.fillCircle(BLCircle(1448, 356, 3));
    c.fillCircle(BLCircle(1492, 356, 3));
    c.setFillStyle(rgba(137, 113, 89));
    c.fillEllipse(BLEllipse(1470, 386, 5, 12));
    c.setStrokeStyle(rgba(100, 82, 64));
    c.setStrokeWidth(2);
    c.strokeLine(BLPoint(1452, 414), BLPoint(1488, 414));
    // Collar and tie.
    BLPath collar;
    collar.moveTo(1400, 600);
    collar.lineTo(1470, 556);
    collar.lineTo(1540, 600);
    collar.lineTo(1540, 652);
    collar.lineTo(1400, 652);
    collar.close();
    c.setFillStyle(rgba(226, 218, 200));
    c.fillPath(collar);
    c.setFillStyle(rgba(92, 80, 64));
    c.fillTriangle(1462, 584, 1478, 584, 1470, 628);
    // halftone dots
    for (int y = 206; y < 630; y += 9) {
        for (int x = 1292; x < 1648; x += 9) {
            const double dx = x - 1470, dy = y - 390;
            const double q = 1.0 - std::min(1.0, std::sqrt(dx * dx + dy * dy) / 240.0);
            if (q > 0.18) {
                c.setFillStyle(rgba(34, 32, 28, int(18 + q * 34)));
                c.fillCircle(BLCircle(x, y, 1.55));
            }
        }
    }
    c.setFillStyle(rgba(241, 233, 218, 190));
    c.fillRect(BLRect(1270, 656, 400, 70));
    fillText(c, face("reg", 10), 1288, 678, "THE ARCHIVIST, 1998", rgba(80, 75, 65));
    fillText(c, face("reg", 9), 1288, 696, "Photograph from the family collection", rgba(114, 104, 89));
    c.restore();

    const double line = easeInOutCubic(wind(t, 0.22, 0.58));
    c.setFillStyle(rgba(34, 32, 28, 55));
    c.fillRect(BLRect(1270, 746, 400 * line, 1));

    fillText(c, face("serifItalic", 16), 100, 794,
             "\u201cA document is not a fact until you know who was allowed to read it.\u201d", rgba(69, 63, 54));
    fillText(c, face("reg", 10), 100, 816, "ATTRIBUTED, 2004 LECTURE", rgba(113, 103, 89));

    rule(c, 100, 860, 1570, rgba(34, 32, 28, 55));
    fillText(c, face("reg", 11), 100, 886,
             "Survived by two children, four grandchildren and an unprocessed FOIA request.", rgba(84, 78, 68));
    fillText(c, face("mono", 10), 1690, 886, "B7", rgba(84, 78, 68));

    const double s = easeOutCubic(wind(t, 0.52, 0.72));
    stamp(c, 1366, 770, 230, 64, "ARCHIVE", rgba(146, 54, 42), -9.0, s, 27);
    if (s > 0.01) {
        c.setFillStyle(rgba(146, 54, 42, int(18 * s)));
        c.fillRoundRect(BLRoundRect(1350, 754, 262, 96, 6, 6));
    }
}

// 17 — Annotated PDF. A highlighter sweeps the paragraph and a comment bubble
// lands in the margin. The PDF chrome is authored as a real viewer surface.
void d17(BLContext& c, double t, int) {
    camera(c, 1.01, 1.035, 0.50, 0.50, t);
    c.setFillStyle(rgba(72, 77, 83));
    c.fillRect(BLRect(0, 0, kW, kH));
    c.setFillStyle(rgba(55, 59, 64));
    c.fillRect(BLRect(0, 0, kW, 44));

    c.setFillStyle(rgba(39, 42, 46));
    c.fillRoundRect(BLRoundRect(78, 56, 1764, 968, 10, 10));
    c.setFillStyle(rgba(245, 246, 244));
    c.fillRoundRect(BLRoundRect(92, 70, 1736, 45, 7, 7));
    fillText(c, face("semi", 12), 110, 98, "briefing_memo.pdf", rgba(48, 50, 50));
    fillText(c, face("reg", 10), 282, 98, "Saved to archive  /  page 14 of 38", rgba(111, 114, 113));
    pill(c, 1548, 80, 92, 25, rgba(52, 104, 173), "SHARE", rgba(238, 244, 251), 9);
    pill(c, 1652, 80, 92, 25, rgba(88, 91, 92), "PRINT", rgba(242, 243, 242), 9);

    c.setFillStyle(rgba(224, 225, 222));
    c.fillRect(BLRect(92, 123, 1736, 1));
    c.setFillStyle(rgba(250, 250, 248));
    c.fillRect(BLRect(92, 124, 1736, 884));

    // Thumbnail rail.
    c.setFillStyle(rgba(239, 239, 236));
    c.fillRect(BLRect(92, 124, 188, 884));
    for (int i = 0; i < 4; ++i) {
        const double y = 148 + i * 180;
        c.setFillStyle(i == 1 ? rgba(52, 104, 173, 40) : rgba(255, 255, 255));
        c.fillRoundRect(BLRoundRect(114, y, 142, 154, 3, 3));
        for (int l = 0; l < 7; ++l) {
            c.setFillStyle(rgba(82, 84, 82, i == 1 ? 60 : 40));
            c.fillRect(BLRect(126, y + 18 + l * 14, 112 - (l % 3) * 18, 2));
        }
        fillText(c, face("mono", 8), 170, y + 166, std::to_string(i + 13), rgba(107, 107, 103));
    }

    // Page.
    c.setFillStyle(rgba(0, 0, 0, 35));
    c.fillRoundRect(BLRoundRect(322, 158, 1000, 790, 2, 2));
    c.setFillStyle(rgba(255, 255, 253));
    c.fillRect(BLRect(312, 148, 1000, 790));
    c.setFillStyle(rgba(199, 198, 191));
    c.fillRect(BLRect(312, 148, 1000, 1));
    c.setFillStyle(rgba(239, 238, 232));
    c.fillRect(BLRect(312, 148, 1, 790));

    tracked(c, face("semi", 9), 346, 184, "UNITED STATES DISTRICT COURT  /  SOUTHERN DISTRICT", rgba(109, 106, 98), 1.2);
    fillText(c, face("serifBold", 22), 346, 220, "MEMORANDUM IN SUPPORT", rgba(38, 38, 34));
    fillText(c, face("reg", 10), 346, 244, "Case 1:26-cr-00418  /  Filed 11/22/2026  /  Page 14", rgba(112, 108, 99));
    rule(c, 346, 260, 890, rgba(48, 46, 40, 40));

    const BLFont body = face("serif", 14);
    const BLRgba32 bodyInk = rgba(57, 55, 48);
    fillText(c, body, 346, 296,
             "The government submits this memorandum in support of its request to maintain the", bodyInk);
    fillText(c, body, 346, 320,
             "protective order as to two supporting exhibits. The exhibits are not necessary to", bodyInk);
    fillText(c, body, 346, 344,
             "the public's understanding of the ruling and would disclose an ongoing investigative", bodyInk);
    fillText(c, body, 346, 368,
             "method. The court has already found that the balance favors continued sealing.", bodyInk);

    const double hi = easeInOutCubic(wind(t, 0.14, 0.58));
    c.setFillStyle(rgba(244, 208, 67, 95));
    c.fillRect(BLRect(338, 400, 858 * hi, 70));
    fillText(c, face("serifBold", 15), 346, 422,
             "The chronology is material because the certification", rgba(41, 39, 33));
    fillText(c, face("serifBold", 15), 346, 448,
             "triggers the disclosure obligation in Section 4(b).", rgba(41, 39, 33));
    fillText(c, body, 346, 502,
             "The office has identified no written record of the approval. The operations log is", bodyInk);
    fillText(c, body, 346, 526,
             "the only contemporaneous account and is attached as Exhibit 7.", bodyInk);
    fillText(c, body, 346, 566,
             "For the foregoing reasons, the court should grant the requested relief.", bodyInk);
    fillText(c, face("reg", 10), 346, 676, "Respectfully submitted,", bodyInk);
    fillText(c, face("serif", 12), 346, 714, "/s/ M. Calder", bodyInk);
    fillText(c, face("reg", 9), 346, 736, "Office of the General Counsel", rgba(107, 103, 94));
    fillText(c, face("mono", 9), 1170, 900, "14", rgba(112, 108, 100));

    // Sticky note and comment.
    c.setFillStyle(rgba(251, 239, 172));
    c.fillRect(BLRect(1342, 298, 236, 152));
    c.setFillStyle(rgba(251, 239, 172, 210));
    c.fillTriangle(1342, 450, 1370, 450, 1342, 478);
    fillText(c, face("semi", 11), 1358, 322, "ANNOTATION  /  14", rgba(120, 99, 36));
    fillText(c, face("reg", 12), 1358, 346, "Compare with the operations", rgba(82, 70, 42));
    fillText(c, face("reg", 12), 1358, 366, "log. The date is three days", rgba(82, 70, 42));
    fillText(c, face("reg", 12), 1358, 386, "before the certification.", rgba(82, 70, 42));
    fillText(c, face("reg", 10), 1358, 420, "M. Calder  /  22 Nov", rgba(130, 104, 48));

    const double pop = easeOutCubic(wind(t, 0.42, 0.70));
    c.save();
    c.setGlobalAlpha(float(pop));
    c.setFillStyle(rgba(38, 97, 163));
    c.fillRoundRect(BLRoundRect(1360, 514 - (1 - pop) * 28, 276, 142, 9, 9));
    c.setFillStyle(rgba(38, 97, 163));
    c.fillTriangle(1360, 644, 1388, 644, 1360, 672);
    fillText(c, face("semi", 11), 1378, 544, "M. CALDER", rgba(207, 231, 250));
    fillText(c, face("reg", 12), 1378, 568, "The log is now public. This", rgba(232, 243, 252));
    fillText(c, face("reg", 12), 1378, 588, "paragraph should be cited in", rgba(232, 243, 252));
    fillText(c, face("reg", 12), 1378, 608, "the supplemental disclosure.", rgba(232, 243, 252));
    fillText(c, face("mono", 9), 1378, 636, "14:32  /  RESOLVED", rgba(174, 213, 242));
    c.restore();

    // Comment rail.
    c.setFillStyle(rgba(249, 249, 247));
    c.fillRect(BLRect(1640, 124, 188, 884));
    tracked(c, face("semi", 9), 1660, 154, "COMMENTS", rgba(117, 112, 102), 1.3);
    fillText(c, face("serifBold", 19), 1660, 184, "3 notes", kInk);
    rule(c, 1660, 198, 146, rgba(48, 46, 40, 35));
    fillText(c, face("semi", 10), 1660, 228, "M. Calder", rgba(70, 69, 63));
    fillText(c, face("reg", 10), 1660, 246, "Compare the dates.", rgba(108, 103, 94));
    fillText(c, face("semi", 10), 1660, 286, "J. Doe", rgba(70, 69, 63));
    fillText(c, face("reg", 10), 1660, 304, "Exhibit 7 is the key.", rgba(108, 103, 94));
    fillText(c, face("semi", 10), 1660, 344, "A. Shaw", rgba(70, 69, 63));
    fillText(c, face("reg", 10), 1660, 362, "Check p. 18 next.", rgba(108, 103, 94));
    pill(c, 1660, 790, 126, 28, rgba(52, 104, 173), "EXPORT NOTES", rgba(237, 244, 252), 9);

    pill(c, 1570, 948, 168, 28, rgba(51, 54, 51), "PAGE 14 OF 38", rgba(230, 233, 229), 9);
    fillText(c, face("reg", 10), 158, 1008, "110%  \u00b7  FIT WIDTH", rgba(229, 231, 228));
}

// 18 — Newsletter inbox. The newest mail slides in above the selected issue;
// the reading pane is a quiet editorial layout with one blue rule.
void d18(BLContext& c, double t, int) {
    camera(c, 1.01, 1.03, 0.50, 0.50, t);
    c.setFillStyle(rgba(228, 227, 223));
    c.fillRect(BLRect(0, 0, kW, kH));
    browserChrome(c, "mail.example.org/inbox/sunday-briefing", false, "MAIL");

    c.setFillStyle(rgba(255, 255, 255, 240));
    c.fillRoundRect(BLRoundRect(54, 86, 1812, 940, 10, 10));
    c.setFillStyle(rgba(241, 241, 237));
    c.fillRect(BLRect(54, 86, 292, 940));
    c.setFillStyle(rgba(249, 249, 246));
    c.fillRect(BLRect(346, 86, 566, 940));
    c.setFillStyle(rgba(255, 255, 255));
    c.fillRect(BLRect(912, 86, 954, 940));

    // Sidebar.
    c.setFillStyle(rgba(33, 39, 46));
    c.fillRoundRect(BLRoundRect(78, 112, 160, 40, 20, 20));
    textC(c, face("semi", 12), 158, 137, "+  COMPOSE", rgba(246, 248, 247));
    const char* folders[] = {"Inbox", "Starred", "Sent", "Drafts", "Archive"};
    const char* counts[] = {"12", "", "", "2", ""};
    for (int i = 0; i < 5; ++i) {
        const double y = 196 + i * 46;
        if (i == 0) {
            c.setFillStyle(rgba(54, 111, 186, 30));
            c.fillRoundRect(BLRoundRect(78, y - 22, 242, 40, 7, 7));
        }
        fillText(c, face(i == 0 ? "semi" : "reg", 13), 100, y + 4, folders[i],
                 i == 0 ? rgba(42, 75, 111) : rgba(84, 86, 83));
        if (counts[i][0]) textC(c, face("mono", 10), 300, y + 3, counts[i], rgba(96, 98, 94));
    }
    rule(c, 78, 448, 242, rgba(43, 45, 42, 24));
    tracked(c, face("semi", 9), 100, 478, "LABELS", rgba(127, 125, 118), 1.3);
    fillText(c, face("reg", 12), 100, 506, "Investigations", rgba(86, 87, 82));
    fillText(c, face("reg", 12), 100, 530, "Documents", rgba(86, 87, 82));
    fillText(c, face("reg", 12), 100, 554, "Reading list", rgba(86, 87, 82));
    fillText(c, face("reg", 10), 78, 980, "2.1 GB of 15 GB used", rgba(126, 125, 119));

    // Inbox header.
    tracked(c, face("semi", 10), 370, 116, "INBOX  /  ALL MAIL", rgba(113, 112, 105), 1.3);
    fillText(c, face("serifBold", 25), 370, 150, "Inbox", kInk);
    fillText(c, face("reg", 12), 370, 172, "12 unread  \u00b7  sorted by newest", rgba(106, 107, 102));
    searchIcon(c, 844, 142, 7, rgba(116, 118, 114));
    rule(c, 346, 190, 566, rgba(43, 45, 42, 22));

    struct Mail { const char* from; const char* subject; const char* preview; const char* time; };
    const Mail mail[] = {
        {"The Archive Desk", "The Sunday Briefing: what the documents show",
         "A docket, a memo and the line that changed.", "9:41"},
        {"CourtListener", "New docket entry in 1:26-cr-00418",
         "Entry 004 is now visible. Two exhibits remain sealed.", "8:12"},
        {"M. Calder", "Re: Exhibit 7 chronology",
         "The date is three days before the certification. I flagged it.", "Yesterday"},
        {"The Wayback Machine", "14 captures on your saved page",
         "A new snapshot of the briefing-room order is available.", "Yesterday"},
        {"A. Shaw", "Notes for Monday",
         "The reading list is ready. Start with the budget table.", "Fri"},
    };
    for (int i = 0; i < 5; ++i) {
        const double y = 224 + i * 104;
        if (i == 0) {
            c.setFillStyle(rgba(54, 111, 186, 25));
            c.fillRect(BLRect(346, y - 16, 566, 100));
        }
        if (i < 2) {
            c.setFillStyle(rgba(54, 111, 186));
            c.fillCircle(BLCircle(370, y + 10, 4));
        }
        fillText(c, face("semi", 11), 392, y + 13, mail[i].from, rgba(62, 64, 60));
        fillText(c, face("mono", 10), 842, y + 13, mail[i].time, rgba(128, 128, 121));
        fillText(c, face(i == 0 ? "semi" : "reg", 12), 392, y + 36, mail[i].subject,
                 i == 0 ? rgba(28, 42, 57) : rgba(69, 71, 67));
        fillText(c, face("reg", 10), 392, y + 56, mail[i].preview, rgba(124, 124, 117));
        rule(c, 370, y + 76, 518, rgba(43, 45, 42, 18));
    }

    // New mail slides in.
    const double slide = easeInOutCubic(wind(t, 0.12, 0.54));
    const double ny = 224 + (1.0 - slide) * -86;
    c.save();
    c.setGlobalAlpha(float(slide));
    c.setFillStyle(rgba(245, 249, 251));
    c.fillRect(BLRect(346, ny - 16, 566, 100));
    c.setFillStyle(rgba(54, 111, 186));
    c.fillCircle(BLCircle(370, ny + 10, 4));
    fillText(c, face("semi", 11), 392, ny + 13, "THE WIRE", rgba(44, 86, 121));
    fillText(c, face("mono", 10), 820, ny + 13, "now", rgba(70, 122, 153));
    fillText(c, face("semi", 12), 392, ny + 36,
             "Breaking: docket entries 001-004 unsealed", rgba(27, 55, 79));
    fillText(c, face("reg", 10), 392, ny + 56,
             "The clerk's office released the order at 22:41 ET.", rgba(100, 126, 142));
    c.restore();

    // Reading pane.
    tracked(c, face("semi", 9), 950, 120, "THE SUNDAY BRIEFING  /  22 NOV 2026", rgba(120, 117, 108), 1.3);
    fillText(c, face("serifBold", 33), 950, 164,
             "What the documents show", kInk);
    fillText(c, face("serifItalic", 18), 950, 190,
             "A docket, a memo and the line that changed.", rgba(97, 93, 84));
    c.setFillStyle(rgba(54, 111, 186));
    c.fillRect(BLRect(950, 208, 118, 3));
    fillText(c, face("reg", 10), 950, 230, "FROM THE ARCHIVE DESK  \u00b7  9:41 AM  \u00b7  6 MIN READ", rgba(120, 116, 106));

    c.setFillStyle(rgba(234, 237, 237));
    c.fillRoundRect(BLRoundRect(950, 252, 880, 210, 7, 7));
    c.setFillStyle(rgba(54, 78, 92));
    c.fillCircle(BLCircle(1070, 356, 92));
    c.setFillStyle(rgba(127, 158, 163, 85));
    c.fillCircle(BLCircle(1210, 330, 130));
    c.setFillStyle(rgba(29, 41, 48, 120));
    c.fillRoundRect(BLRoundRect(950, 252, 880, 210, 7, 7));
    tracked(c, face("semi", 9), 974, 280, "FIELD NOTE  /  SITE 04", rgba(211, 224, 226), 1.3);
    fillText(c, face("serifBold", 25), 974, 316, "The record is the story", rgba(243, 245, 244));
    fillText(c, face("reg", 11), 974, 338, "A visual index of the week's documents.", rgba(202, 215, 217));

    const BLFont body = face("serif", 14);
    fillText(c, body, 950, 504,
             "The docket was unsealed at 22:41 ET. Entries 001 through 004 are now public; two", rgba(51, 50, 44));
    fillText(c, body, 950, 528,
             "supporting exhibits remain behind the protective order. The clerk's office says the", rgba(51, 50, 44));
    fillText(c, body, 950, 552,
             "redactions protect an ongoing investigation, not the parties.", rgba(51, 50, 44));
    fillText(c, body, 950, 590,
             "The more useful document may be the memo. It puts the approval three days before the", rgba(51, 50, 44));
    fillText(c, body, 950, 614,
             "certification, which is the chronology the disclosure obligation turns on. The office", rgba(51, 50, 44));
    fillText(c, body, 950, 638,
             "has not produced a written record of the approval. The operations log is Exhibit 7.", rgba(51, 50, 44));

    c.setFillStyle(rgba(248, 243, 231));
    c.fillRoundRect(BLRoundRect(950, 674, 860, 104, 7, 7));
    c.setFillStyle(rgba(54, 111, 186));
    c.fillRect(BLRect(950, 674, 3, 104));
    fillText(c, face("serifItalic", 17), 974, 710,
             "\u201cThe chronology is material because the certification triggers", rgba(62, 58, 49));
    fillText(c, face("serifItalic", 17), 974, 736,
             "the disclosure obligation.\u201d", rgba(62, 58, 49));
    fillText(c, face("reg", 9), 974, 760, "MEMORANDUM  /  PAGE 3", rgba(126, 118, 102));

    fillText(c, face("semi", 11), 950, 832, "READ NEXT", rgba(119, 115, 105));
    fillText(c, face("serifBold", 17), 950, 858, "The budget table, annotated", kInk);
    fillText(c, face("reg", 11), 950, 878, "Five rows, one footnote, and the number that moves.", rgba(107, 103, 94));
    fillText(c, face("reg", 11), 950, 930, "You are receiving this because you subscribed to the archive desk.", rgba(130, 125, 114));
    fillText(c, face("semi", 10), 1580, 930, "UNSUBSCRIBE", rgba(91, 96, 91));
}

// 19 — Podcast transcript. The waveform is native bars; the played portion and
// the active transcript line share one moving playhead.
void d19(BLContext& c, double t, int) {
    camera(c, 1.01, 1.035, 0.50, 0.50, t);
    c.setFillStyle(rgba(15, 17, 19));
    c.fillRect(BLRect(0, 0, kW, kH));
    c.setFillStyle(rgba(23, 26, 30));
    c.fillRect(BLRect(0, 0, kW, 66));
    tracked(c, face("semi", 11), 54, 40, "TRANSCRIPT  /  EP. 42", rgba(184, 174, 154), 1.5);
    fillText(c, face("reg", 12), 1620, 40, "AUDIO  \u00b7  44:18", rgba(143, 140, 131));
    fillText(c, face("semi", 12), 1770, 40, "SUBSCRIBE", rgba(222, 197, 148));

    tracked(c, face("semi", 10), 54, 110, "THE ARCHIVE DESK  /  FIELD NOTES", rgba(168, 158, 139), 1.4);
    fillText(c, face("serifBold", 40), 54, 158, "The line that changed", rgba(238, 234, 226));
    fillText(c, face("reg", 14), 54, 184,
             "Episode 42: a docket, a memo and the three days between them.", rgba(155, 151, 141));

    c.setFillStyle(rgba(34, 38, 43));
    c.fillCircle(BLCircle(86, 236, 18));
    BLPath p;
    p.moveTo(82, 226); p.lineTo(82, 246); p.lineTo(96, 236); p.close();
    c.setFillStyle(rgba(224, 194, 135));
    c.fillPath(p);
    fillText(c, face("semi", 12), 118, 240, "PLAY EPISODE", rgba(221, 216, 205));
    fillText(c, face("reg", 11), 1530, 240, "44:18", rgba(156, 151, 140));
    tracked(c, face("semi", 9), 1600, 240, "SPEED  1.0X", rgba(133, 129, 119), 1.1);

    // Waveform panel.
    c.setFillStyle(rgba(22, 25, 28));
    c.fillRoundRect(BLRoundRect(54, 272, 1812, 224, 9, 9));
    const double play = easeInOutCubic(t);
    const int bars = 96;
    for (int i = 0; i < bars; ++i) {
        const double x = 86 + i * 18.2;
        const double base = 0.20 + 0.62 * std::abs(std::sin(i * 0.71 + 0.8));
        const double wob = 0.10 * std::sin(t * 9.0 + i * 0.33);
        const double h = 18 + 112 * std::min(1.0, base + wob);
        const bool played = x < 86 + play * bars * 18.2;
        c.setFillStyle(played ? rgba(224, 194, 135, 210) : rgba(91, 95, 100, 150));
        c.fillRoundRect(BLRoundRect(x, 382 - h * 0.5, 5, h, 2.5, 2.5));
    }
    c.setFillStyle(rgba(224, 194, 135));
    c.fillCircle(BLCircle(86 + play * bars * 18.2, 382, 7));
    c.setFillStyle(rgba(224, 194, 135, 35));
    c.fillCircle(BLCircle(86 + play * bars * 18.2, 382, 18));
    fillText(c, face("mono", 10), 86, 470, "00:00", rgba(129, 126, 116));
    fillText(c, face("mono", 10), 1740, 470, "44:18", rgba(129, 126, 116));

    // Transcript.
    tracked(c, face("semi", 10), 54, 540, "TRANSCRIPT  /  AUTO-GENERATED", rgba(148, 143, 132), 1.3);
    const char* speakers[] = {"HOST", "GUEST", "HOST", "GUEST", "HOST"};
    const char* lines[] = {
        "The docket is public now. What changed at 22:41?",
        "Entries 001 through 004. Two exhibits are still sealed.",
        "And the memo puts the approval before the certification.",
        "Three days before. That is the chronology the office has to explain.",
        "The operations log is the only written record. It is Exhibit 7.",
    };
    const int active = 1 + int(play * 4.0);
    for (int i = 0; i < 5; ++i) {
        const double y = 590 + i * 78;
        if (i == active) {
            c.setFillStyle(rgba(224, 194, 135, 22));
            c.fillRoundRect(BLRoundRect(54, y - 28, 1220, 62, 6, 6));
            c.setFillStyle(rgba(224, 194, 135, 190));
            c.fillRect(BLRect(54, y - 28, 3, 62));
        }
        tracked(c, face("semi", 9), 76, y, speakers[i], rgba(164, 153, 133), 1.2);
        fillText(c, face(i == active ? "med" : "reg", 14), 150, y, lines[i],
                 i == active ? rgba(236, 231, 220) : rgba(159, 157, 148));
    }

    // Key quote card.
    c.setFillStyle(rgba(30, 34, 38));
    c.fillRoundRect(BLRoundRect(1320, 536, 546, 350, 9, 9));
    tracked(c, face("semi", 9), 1346, 568, "KEY QUOTE  /  22:41", rgba(157, 148, 130), 1.3);
    fillText(c, face("serifItalic", 28), 1346, 618,
             "\u201cA document is not a fact", rgba(226, 221, 209));
    fillText(c, face("serifItalic", 28), 1346, 652,
             "until you know who was", rgba(226, 221, 209));
    fillText(c, face("serifItalic", 28), 1346, 686,
             "allowed to read it.\u201d", rgba(226, 221, 209));
    c.setFillStyle(rgba(224, 194, 135));
    c.fillRect(BLRect(1346, 714, 48, 2));
    fillText(c, face("reg", 11), 1346, 742, "THE ARCHIVIST, 2004 LECTURE", rgba(145, 138, 124));
    fillText(c, face("reg", 12), 1346, 790, "Clip 04  /  transcript synced", rgba(126, 130, 132));
    fillText(c, face("mono", 10), 1346, 818, "42:18  \u2014  43:02", rgba(126, 130, 132));

    fillText(c, face("reg", 10), 54, 1014, "THE ARCHIVE DESK  /  PRODUCED IN NEW YORK", rgba(121, 120, 112));
    fillText(c, face("mono", 10), 1700, 1014, "EP. 42  /  S02", rgba(121, 120, 112));
}

// 20 — Route map. A dark editorial map with a route drawn segment by segment.
// The right panel tracks distance and the last known signal.
void d20(BLContext& c, double t, int) {
    camera(c, 1.01, 1.035, 0.49, 0.51, t);
    c.setFillStyle(rgba(7, 18, 24));
    c.fillRect(BLRect(0, 0, kW, kH));
    browserChrome(c, "maps.example.org/route/0418/archive-flight", true, "ROUTE");

    const double mx0 = 0, my0 = 64, mw = 1460, mh = 1016;
    c.setFillStyle(rgba(9, 26, 33));
    c.fillRect(BLRect(mx0, my0, mw, mh));
    c.setStrokeStyle(rgba(87, 132, 139, 35));
    c.setStrokeWidth(1);
    for (int x = 0; x < int(mw); x += 64) c.strokeLine(BLPoint(x, my0), BLPoint(x, my0 + mh));
    for (int y = 64; y < kH; y += 64) c.strokeLine(BLPoint(mx0, y), BLPoint(mx0 + mw, y));

    // Stylised landmasses and a coastline.
    BLPath land1;
    land1.moveTo(0, 220); land1.lineTo(260, 176); land1.lineTo(410, 280);
    land1.lineTo(360, 430); land1.lineTo(150, 520); land1.lineTo(0, 470);
    land1.close();
    c.setFillStyle(rgba(25, 55, 60, 180));
    c.fillPath(land1);
    BLPath land2;
    land2.moveTo(650, 620); land2.lineTo(920, 560); land2.lineTo(1120, 680);
    land2.lineTo(1040, 890); land2.lineTo(740, 930); land2.lineTo(590, 780);
    land2.close();
    c.setFillStyle(rgba(35, 64, 64, 160));
    c.fillPath(land2);
    BLPath land3;
    land3.moveTo(1160, 180); land3.lineTo(1390, 220); land3.lineTo(1460, 360);
    land3.lineTo(1290, 420); land3.lineTo(1140, 320);
    land3.close();
    c.setFillStyle(rgba(49, 62, 53, 130));
    c.fillPath(land3);

    c.setStrokeStyle(rgba(95, 160, 164, 110));
    c.setStrokeWidth(1.5);
    c.strokePath(land1);
    c.strokePath(land2);
    c.strokePath(land3);

    // Roads and a river.
    c.setStrokeStyle(rgba(194, 184, 151, 40));
    c.setStrokeWidth(0.9);
    c.strokeLine(BLPoint(90, 600), BLPoint(520, 490));
    c.strokeLine(BLPoint(520, 490), BLPoint(840, 520));
    c.strokeLine(BLPoint(840, 520), BLPoint(1200, 380));
    c.strokeLine(BLPoint(420, 260), BLPoint(680, 380));
    c.strokeLine(BLPoint(680, 380), BLPoint(1080, 430));
    c.setStrokeStyle(rgba(67, 154, 170, 80));
    c.setStrokeWidth(2);
    BLPath river;
    river.moveTo(0, 740); river.lineTo(220, 690); river.lineTo(370, 720);
    river.lineTo(560, 640); river.lineTo(780, 660); river.lineTo(980, 580);
    river.lineTo(1180, 600); river.lineTo(1460, 540);
    c.strokePath(river);

    struct City { const char* name; double x; double y; bool route; };
    const City cities[] = {
        {"ORIGIN", 300, 760, true}, {"NODE 02", 520, 620, true},
        {"NODE 03", 760, 560, true}, {"NODE 04", 980, 430, true},
        {"SIGNAL", 1180, 360, true}, {"ARCHIVE", 1320, 690, false},
        {"RELAY", 170, 280, false},
    };
    for (const auto& city : cities) {
        const double ph = 0.5 + 0.5 * std::sin(t * 5.4 + city.x * 0.01);
        if (city.route) {
            c.setFillStyle(rgba(232, 186, 106, int(24 + 44 * ph)));
            c.fillCircle(BLCircle(city.x, city.y, 16 + 8 * ph));
            c.setFillStyle(rgba(232, 186, 106, 230));
            c.fillCircle(BLCircle(city.x, city.y, 4));
        } else {
            c.setFillStyle(rgba(116, 157, 162, 190));
            c.fillCircle(BLCircle(city.x, city.y, 3));
        }
        fillText(c, face("mono", 9), city.x + 12, city.y - 10, city.name,
                 city.route ? rgba(235, 216, 178) : rgba(133, 167, 171));
    }

    // Route.
    const BLPoint route[] = {
        {300, 760}, {430, 690}, {520, 620}, {640, 592}, {760, 560},
        {880, 482}, {980, 430}, {1080, 392}, {1180, 360},
    };
    const double rp = easeInOutCubic(wind(t, 0.10, 0.70));
    const double totalSegs = 8.0;
    const double exact = rp * totalSegs;
    const int last = std::min(8, int(exact));
    c.save();
    c.setStrokeStyle(rgba(232, 186, 106, 220));
    c.setStrokeWidth(3.2);
    for (int i = 0; i < last; ++i) c.strokeLine(route[i], route[i + 1]);
    if (rp < 1.0) {
        const int i = std::min(7, last);
        const double frac = exact - std::floor(exact);
        const BLPoint q(lerp(route[i].x, route[i + 1].x, frac),
                        lerp(route[i].y, route[i + 1].y, frac));
        c.strokeLine(route[i], q);
        c.setFillStyle(rgba(250, 229, 185));
        c.fillCircle(BLCircle(q.x, q.y, 6));
        c.setFillStyle(rgba(232, 186, 106, 35));
        c.fillCircle(BLCircle(q.x, q.y, 19));
    }
    c.restore();

    // Route distance card.
    c.setFillStyle(rgba(15, 34, 41, 225));
    c.fillRoundRect(BLRoundRect(30, 92, 326, 98, 7, 7));
    tracked(c, face("semi", 9), 48, 118, "ARCHIVE FLIGHT  /  0418", rgba(154, 181, 180), 1.2);
    fillText(c, face("serifBold", 33), 48, 158,
             std::to_string(int(7842 * rp)) + " KM", rgba(239, 228, 201));
    fillText(c, face("reg", 11), 230, 158, "of 7,842", rgba(143, 166, 166));

    // Right panel.
    c.setFillStyle(rgba(11, 25, 31));
    c.fillRect(BLRect(1460, 64, 460, 1016));
    rule(c, 1460, 64, 1, rgba(120, 161, 163, 55));
    tracked(c, face("semi", 10), 1492, 108, "ROUTE  /  SITE 04", rgba(148, 172, 170), 1.3);
    fillText(c, face("serifBold", 30), 1492, 146, "Archive flight", rgba(235, 235, 222));
    fillText(c, face("reg", 13), 1492, 170, "A reconstructed signal path.", rgba(139, 159, 158));

    tracked(c, face("semi", 9), 1492, 216, "DISTANCE", rgba(148, 172, 170), 1.3);
    fillText(c, face("mono", 13), 1492, 248, std::to_string(int(7842 * rp)) + " KM", rgba(232, 186, 106));
    rule(c, 1492, 266, 392, rgba(120, 161, 163, 40));
    tracked(c, face("semi", 9), 1492, 298, "MODE", rgba(148, 172, 170), 1.3);
    fillText(c, face("reg", 13), 1492, 322, "ARCHIVE  /  BURST", rgba(202, 211, 206));
    tracked(c, face("semi", 9), 1492, 356, "LAST SIGNAL", rgba(148, 172, 170), 1.3);
    fillText(c, face("mono", 13), 1492, 380, "22:41:08 ET", rgba(202, 211, 206));
    tracked(c, face("semi", 9), 1492, 414, "COORDINATES", rgba(148, 172, 170), 1.3);
    fillText(c, face("mono", 11), 1492, 438, "36.2048 N  /  55.2711 E", rgba(202, 211, 206));

    rule(c, 1492, 468, 392, rgba(120, 161, 163, 35));
    tracked(c, face("semi", 9), 1492, 500, "WAYPOINTS", rgba(148, 172, 170), 1.3);
    const char* names[] = {"ORIGIN", "NODE 02", "NODE 03", "NODE 04", "SIGNAL"};
    const char* times[] = {"18:02", "18:41", "19:18", "20:06", "22:41"};
    for (int i = 0; i < 5; ++i) {
        const double y = 532 + i * 54;
        c.setFillStyle(i == 4 ? rgba(232, 186, 106) : rgba(116, 157, 162, 170));
        c.fillCircle(BLCircle(1500, y - 4, 3));
        fillText(c, face(i == 4 ? "semi" : "reg", 11), 1516, y, names[i],
                 i == 4 ? rgba(235, 216, 178) : rgba(186, 199, 196));
        fillText(c, face("mono", 10), 1770, y, times[i], rgba(134, 153, 152));
        if (i < 4) rule(c, 1516, y + 18, 368, rgba(120, 161, 163, 22));
    }

    c.setFillStyle(rgba(232, 186, 106, 16));
    c.fillRoundRect(BLRoundRect(1492, 828, 392, 112, 7, 7));
    tracked(c, face("semi", 9), 1508, 854, "NOTE", rgba(210, 184, 135), 1.2);
    fillText(c, face("reg", 12), 1508, 880,
             "The last leg is reconstructed from the", rgba(201, 195, 177));
    fillText(c, face("reg", 12), 1508, 900,
             "operations log, not from the tracker.", rgba(201, 195, 177));
    fillText(c, face("mono", 9), 1508, 926, "CONFIDENCE  0.82", rgba(151, 154, 137));

    fillText(c, face("mono", 9), 1492, 1038, "MAP  /  NATIVE VECTOR PLATE", rgba(120, 145, 145));
    fillText(c, face("mono", 9), 1720, 1038, "ZOOM 06", rgba(120, 145, 145));
}

} // namespace

std::vector<Scene> scenesC() {
    return {
        {"d15_budget_table", "Data & verification",
         "Federal budget table with scanning rows and growing comparison bars",
         0.84, d15},
        {"d16_obituary_archive", "Archives & search",
         "Newsprint obituary with a halftone portrait and archive stamp",
         0.84, d16},
        {"d17_pdf_annotations", "Evidence & courts",
         "Annotated PDF viewer: highlighter sweep and a comment bubble",
         0.86, d17},
        {"d18_newsletter_inbox", "Interface & field",
         "Mail inbox with a new issue sliding in over the reading pane",
         0.86, d18},
        {"d19_podcast_transcript", "Live & broadcast",
         "Podcast transcript with a native waveform and moving playhead",
         0.84, d19},
        {"d20_map_route", "Interface & field",
         "Dark route map: drawn flight path, waypoint pulses and distance",
         0.84, d20},
    };
}

} // namespace chronon::docshots
