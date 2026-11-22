// d01-d07 — evidence, archives, retrieval and live verification.

#include "doc_pack.hpp"

namespace chronon::docshots {

namespace {

const BLRgba32 kInk = rgba(18, 21, 26);
const BLRgba32 kPaper = rgba(246, 242, 234);
const BLRgba32 kCream = rgba(244, 239, 229);
const BLRgba32 kRed = rgba(190, 49, 42);
const BLRgba32 kBlue = rgba(54, 111, 186);
const BLRgba32 kTeal = rgba(76, 183, 190);
const BLRgba32 kMuted = rgba(112, 112, 108);

// 01 — PACER docket. A court record is scanned; one entry receives a filed
// stamp and an evidence highlight.
void d01(BLContext& c, double t, int) {
    camera(c, 1.015, 1.045, 0.49, 0.50, t);
    c.setFillStyle(rgba(7, 16, 27));
    c.fillRect(BLRect(0, 0, kW, kH));
    c.setFillStyle(rgba(10, 24, 40));
    c.fillRoundRect(BLRoundRect(-120, 90, 620, 1050, 32, 32));
    browserChrome(c, "courtlistener.com/docket/1:26-cr-00418", true, "DOCKET");

    c.setFillStyle(rgba(20, 35, 52));
    c.fillRect(BLRect(420, 64, 1, kH - 64));
    tracked(c, face("semi", 12), 48, 132, "UNITED STATES DISTRICT COURT", rgba(116, 151, 177), 1.5);
    fillText(c, face("serifBold", 34), 48, 194, "UNITED STATES", rgba(233, 239, 244));
    fillText(c, face("serifBold", 34), 48, 236, "v. DOE", rgba(233, 239, 244));
    rule(c, 48, 266, 330, rgba(124, 154, 177, 70));
    tracked(c, face("reg", 12), 48, 306, "CASE NUMBER", rgba(112, 146, 170), 1.5);
    fillText(c, face("mono", 18), 48, 336, "1:26-cr-00418", rgba(198, 215, 227));

    tracked(c, face("reg", 12), 48, 394, "COURT", rgba(112, 146, 170), 1.5);
    fillText(c, face("reg", 17), 48, 423, "Southern District of New York", rgba(198, 215, 227));
    tracked(c, face("reg", 12), 48, 480, "PRESIDING", rgba(112, 146, 170), 1.5);
    fillText(c, face("reg", 17), 48, 509, "Hon. M. Calder", rgba(198, 215, 227));
    tracked(c, face("reg", 12), 48, 566, "STATUS", rgba(112, 146, 170), 1.5);
    pill(c, 48, 580, 104, 28, rgba(190, 49, 42), "SEALED", rgba(255, 236, 232), 12);
    pill(c, 162, 580, 92, 28, rgba(39, 74, 96), "ACTIVE", rgba(193, 226, 235), 12);

    tracked(c, face("reg", 11), 48, 670, "PARTIES", rgba(112, 146, 170), 1.5);
    fillText(c, face("reg", 15), 48, 699, "USA", rgba(198, 215, 227));
    fillText(c, face("reg", 15), 48, 724, "JOHN DOE", rgba(198, 215, 227));
    rule(c, 48, 760, 330, rgba(124, 154, 177, 50));
    fillText(c, face("reg", 13), 48, 792, "Last updated 22 Nov 2026, 22:41 ET",
             rgba(118, 150, 172));

    tracked(c, face("semi", 12), 480, 132, "DOCKET ENTRIES", rgba(118, 171, 191), 1.8);
    fillText(c, face("serifBold", 40), 480, 184, "Case activity", rgba(232, 240, 245));
    fillText(c, face("reg", 15), 480, 214,
             "Seven entries. Two visible. One temporarily sealed.", rgba(131, 160, 179));

    c.setFillStyle(rgba(22, 45, 63));
    c.fillRoundRect(BLRoundRect(470, 246, 1400, 42, 7, 7));
    tracked(c, face("semi", 11), 490, 272, "DATE", rgba(141, 190, 204), 1.4);
    tracked(c, face("semi", 11), 640, 272, "DOC", rgba(141, 190, 204), 1.4);
    tracked(c, face("semi", 11), 760, 272, "DESCRIPTION", rgba(141, 190, 204), 1.4);
    tracked(c, face("semi", 11), 1590, 272, "STATUS", rgba(141, 190, 204), 1.4);

    struct Row { const char* date; const char* doc; const char* desc; const char* status; };
    const Row rows[] = {
        {"NOV 18", "001", "MOTION to seal the docket and supporting exhibits", "FILED"},
        {"NOV 19", "002", "ORDER granting temporary sealing of entry 001", "GRANTED"},
        {"NOV 22", "003", "NOTICE of unsealing as to the limited redacted appendix", "SEALED"},
        {"NOV 22", "004", "MEMORANDUM in support of continued protective order", "FILED"},
    };
    const double baseY = 312;
    for (int i = 0; i < 4; ++i) {
        const double y = baseY + i * 136;
        rule(c, 480, y + 112, 1380, rgba(123, 169, 190, 42));
        fillText(c, face("mono", 14), 490, y + 38, rows[i].date, rgba(145, 186, 201));
        fillText(c, face("mono", 14), 640, y + 38, rows[i].doc, rgba(145, 186, 201));
        fillText(c, face("reg", 17), 760, y + 38, rows[i].desc, rgba(218, 230, 237));
        const bool red = std::string(rows[i].status) == "SEALED";
        pill(c, 1588, y + 13, 100, 28, red ? rgba(84, 32, 34) : rgba(31, 69, 60),
             rows[i].status, red ? rgba(247, 181, 172) : rgba(156, 224, 198), 11);
    }

    const double s = easeInOutCubic(wind(t, 0.10, 0.42));
    c.setFillStyle(rgba(61, 168, 186, 28));
    c.fillRoundRect(BLRoundRect(470, 626, 1400 * s, 136, 8, 8));
    c.setFillStyle(rgba(81, 208, 220, 130));
    c.fillRect(BLRect(470, 626, 1400 * s, 2));
    const double scanY = 246 + fmod(t * 760.0, 700.0);
    c.setFillStyle(rgba(101, 220, 232, 22));
    c.fillRect(BLRect(470, scanY, 1400, 3));
    c.setFillStyle(rgba(101, 220, 232, 120));
    c.fillCircle(BLCircle(1866, scanY + 1, 3));

    const double a = easeOutCubic(wind(t, 0.38, 0.62));
    stamp(c, 1510, 100, 236, 66, "FILED", rgba(224, 85, 77), -6.5, a, 27);

    c.setFillStyle(rgba(148, 193, 210, 25));
    c.fillCircle(BLCircle(1770, 196, 56));
    c.setFillStyle(rgba(148, 193, 210, 42));
    c.fillCircle(BLCircle(1770, 196, 58));
    textC(c, face("mono", 15), 1770, 201, "04", rgba(205, 232, 241));
    textC(c, face("reg", 11), 1770, 226, "ENTRIES", rgba(130, 177, 195));
}

// 02 — SEC EDGAR. The risk-factor paragraph gets a red editorial underline;
// the filing tab and an exhibit marker land late.
void d02(BLContext& c, double t, int) {
    camera(c, 1.01, 1.04, 0.50, 0.51, t);
    paper(c, kCream, 62);
    browserChrome(c, "sec.gov/Archives/edgar/data/0002041876/000204187626000041/", false, "EDGAR");
    rule(c, 0, 64, kW, rgba(40, 39, 34, 45), 0.6);

    tracked(c, face("semi", 12), 120, 112, "UNITED STATES SECURITIES AND EXCHANGE COMMISSION",
            rgba(100, 96, 88), 1.7);
    fillText(c, face("serifBold", 34), 120, 154, "FORM 10-K", kInk);
    fillText(c, face("reg", 15), 120, 181, "ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d)",
             rgba(89, 86, 79));
    rule(c, 120, 200, 1540, rgba(50, 47, 40, 65));

    fillText(c, face("semi", 17), 120, 238, "NORTHSTAR GRID SYSTEMS, INC.", kInk);
    fillText(c, face("reg", 13), 120, 260, "Commission File Number 001-40318", rgba(104, 100, 91));
    fillText(c, face("reg", 13), 1440, 238, "FISCAL YEAR ENDED", rgba(104, 100, 91));
    fillText(c, face("mono", 14), 1440, 260, "DECEMBER 31, 2026", rgba(59, 56, 49));

    c.setFillStyle(rgba(37, 35, 30));
    c.fillRect(BLRect(120, 288, 1540, 2));
    tracked(c, face("semi", 12), 120, 322, "PART II  /  ITEM 1A", rgba(116, 111, 101), 1.5);
    fillText(c, face("serifBold", 32), 120, 360, "Risk Factors", kInk);

    const BLFont body = face("serif", 19);
    const BLRgba32 bodyInk = rgba(44, 42, 37);
    const BLRgba32 bodyMuted = rgba(91, 88, 81);
    const double x = 120;
    fillText(c, body, x, 406,
             "Our results of operations depend on the continued availability of critical grid components,",
             bodyInk);
    fillText(c, body, x, 433,
             "including high-voltage transformers and control systems. We have identified a material", bodyInk);
    fillText(c, body, x, 460,
             "weakness in internal controls over financial reporting related to inventory valuation.", bodyInk);
    fillText(c, body, x, 487,
             "While we are implementing remediation measures, there can be no assurance that these", bodyMuted);
    fillText(c, body, x, 514,
             "measures will be sufficient to prevent a material misstatement in future periods.", bodyMuted);

    const double phraseX = x;
    const std::string phrase = "material weakness in internal controls over financial reporting";
    const double phraseW = textW(body, phrase);
    const double rs = easeInOutCubic(wind(t, 0.10, 0.46));
    c.setFillStyle(rgba(190, 49, 42, 48));
    c.fillRect(BLRect(phraseX, 441, phraseW * rs, 24));
    c.setFillStyle(rgba(190, 49, 42, 220));
    c.fillRect(BLRect(phraseX, 464, phraseW * rs, 3));

    // A hand-like editorial bracket in the outer margin.
    const double bs = easeInOutCubic(wind(t, 0.24, 0.48));
    c.save();
    c.setStrokeStyle(rgba(190, 49, 42, 190));
    c.setStrokeWidth(2);
    c.strokeLine(BLPoint(92, 441), BLPoint(78, 441));
    c.strokeLine(BLPoint(78, 441), BLPoint(78, 464 + 24 * bs));
    c.strokeLine(BLPoint(78, 464 + 24 * bs), BLPoint(92, 464 + 24 * bs));
    c.restore();

    // Filing sidebar: a thin exhibit label and a miniature delta table.
    c.setFillStyle(rgba(255, 255, 255, 125));
    c.fillRoundRect(BLRoundRect(1438, 300, 310, 218, 8, 8));
    tracked(c, face("semi", 11), 1458, 328, "EXHIBIT 99.1", rgba(122, 116, 104), 1.4);
    fillText(c, face("serifBold", 23), 1458, 361, "Selected financial data", kInk);
    fillText(c, face("reg", 12), 1458, 383, "USD millions, except per-share data", rgba(113, 108, 98));
    rule(c, 1458, 402, 270, rgba(55, 51, 44, 40));
    fillText(c, face("reg", 13), 1458, 426, "Revenue", rgba(71, 68, 60));
    fillText(c, face("mono", 13), 1640, 426, "4,218", rgba(44, 42, 37));
    fillText(c, face("reg", 13), 1458, 451, "Operating income", rgba(71, 68, 60));
    fillText(c, face("mono", 13), 1640, 451, "612", rgba(44, 42, 37));
    fillText(c, face("reg", 13), 1458, 476, "Risk factor delta", rgba(71, 68, 60));
    fillText(c, face("mono", 13), 1640, 476, "+18%", rgba(190, 49, 42));
    rule(c, 1458, 492, 270, rgba(55, 51, 44, 34));

    const double e = easeOutCubic(wind(t, 0.44, 0.68));
    c.setFillStyle(rgba(190, 49, 42, 235));
    c.fillRoundRect(BLRoundRect(1438, 540, 150, 34, 6, 6));
    tracked(c, face("semi", 11), 1452, 562, "REVISED FILING", rgba(255, 239, 235), 1.1);
    c.setFillStyle(rgba(28, 28, 25, 20));
    c.fillRect(BLRect(120, 590, 1540, 1));
    fillText(c, face("reg", 13), 120, 620,
             "This excerpt is a native reconstruction of a public filing layout; it is not a source document.",
             rgba(119, 113, 102));
    fillText(c, face("mono", 12), 1510, 620, "PAGE 14 / 186", rgba(121, 115, 104));

    stamp(c, 1450, 680, 226, 66, "MATERIAL", rgba(190, 49, 42), -5.0, e, 22);
    if (e > 0.01) {
        c.setFillStyle(rgba(190, 49, 42, int(24 * e)));
        c.fillRoundRect(BLRoundRect(1434, 676, 258, 74, 7, 7));
    }
}

// 03 — Wikipedia revision history. A revision diff card rises over the page;
// the added/removed lines are drawn by the animation, not baked in.
void d03(BLContext& c, double t, int) {
    camera(c, 1.01, 1.04, 0.47, 0.51, t);
    paper(c, rgba(250, 248, 243), 42);
    browserChrome(c, "en.wikipedia.org/wiki/2026_federal_budget", false, "ARTICLE");

    c.setFillStyle(rgba(245, 246, 243));
    c.fillRoundRect(BLRoundRect(62, 100, 386, 386, 8, 8));
    c.setFillStyle(rgba(36, 38, 36));
    c.fillCircle(BLCircle(250, 214, 72));
    c.setFillStyle(rgba(245, 246, 243));
    c.fillCircle(BLCircle(250, 214, 36));
    textC(c, face("serifBold", 40), 250, 226, "W", rgba(36, 38, 36));
    fillText(c, face("serifBold", 32), 110, 340, "WIKIPEDIA", rgba(36, 38, 36));
    fillText(c, face("reg", 14), 110, 365, "The free encyclopedia", rgba(94, 94, 89));

    tracked(c, face("semi", 11), 494, 122, "ARTICLE  /  UNITED STATES BUDGET", rgba(106, 106, 100), 1.4);
    fillText(c, face("serifBold", 42), 494, 172, "2026 United States federal budget", kInk);
    rule(c, 494, 192, 850, rgba(54, 55, 51, 38));
    fillText(c, face("reg", 17), 494, 226,
             "The 2026 federal budget was signed into law on September 30, 2025, funding", rgba(62, 64, 60));
    fillText(c, face("reg", 17), 494, 253,
             "government operations through September 30, 2026. The enacted plan increased", rgba(62, 64, 60));
    fillText(c, face("reg", 17), 494, 280,
             "discretionary outlays by 4.8 percent while reducing mandatory program growth.", rgba(62, 64, 60));
    fillText(c, face("reg", 17), 494, 326,
             "The budget passed after a nine-week continuing resolution and a narrow Senate vote.", rgba(62, 64, 60));
    fillText(c, face("reg", 17), 494, 353,
             "A last-minute amendment changed the treatment of emergency supplemental funds.", rgba(62, 64, 60));

    rule(c, 494, 690, 870, rgba(54, 55, 51, 28));
    fillText(c, face("serifBold", 22), 494, 726, "Contents", kInk);
    fillText(c, face("reg", 15), 494, 754, "1  Background", rgba(62, 64, 60));
    fillText(c, face("reg", 15), 494, 778, "2  Congressional action", rgba(62, 64, 60));
    fillText(c, face("reg", 15), 494, 802, "3  Provisions", rgba(62, 64, 60));

    // Right rail: revision history.
    c.setFillStyle(rgba(255, 255, 255, 110));
    c.fillRoundRect(BLRoundRect(1408, 104, 448, 840, 8, 8));
    tracked(c, face("semi", 11), 1432, 134, "REVISION HISTORY", rgba(101, 101, 96), 1.4);
    fillText(c, face("serifBold", 24), 1432, 170, "2026 federal budget", kInk);
    rule(c, 1432, 190, 400, rgba(54, 55, 51, 34));

    struct Rev { const char* time; const char* user; const char* note; };
    const Rev revs[] = {
        {"22:41, 18 Nov 2026", "ArchiveDesk", "Restored cited figure"},
        {"19:04, 18 Nov 2026", "M. Calder", "Copy edit"},
        {"11:26, 18 Nov 2026", "K. Ibarra", "Added Senate vote"},
        {"08:02, 18 Nov 2026", "J. Doe", "Removed unsourced claim"},
    };
    for (int i = 0; i < 4; ++i) {
        const double y = 228 + i * 94;
        c.setFillStyle(i == 0 ? rgba(54, 111, 186, 18) : rgba(0, 0, 0, 0));
        c.fillRoundRect(BLRoundRect(1420, y - 24, 416, 74, 6, 6));
        fillText(c, face("mono", 11), 1432, y, revs[i].time, rgba(94, 94, 89));
        fillText(c, face("semi", 14), 1432, y + 22, revs[i].user, rgba(48, 49, 46));
        fillText(c, face("reg", 12), 1432, y + 41, revs[i].note, rgba(110, 110, 104));
    }
    rule(c, 1432, 610, 400, rgba(54, 55, 51, 28));
    fillText(c, face("reg", 13), 1432, 644, "Current revision", rgba(94, 94, 89));
    pill(c, 1432, 660, 92, 28, rgba(48, 111, 74), "CURRENT", rgba(235, 252, 241), 11);

    // Diff card.
    const double slide = easeInOutCubic(wind(t, 0.10, 0.44));
    const double cardX = 92;
    const double cardY = 776 - 56 * (1.0 - slide);
    c.save();
    c.setGlobalAlpha(float(0.96 * slide));
    roundedCard(c, cardX, cardY, 1190, 236, 9, rgba(255, 255, 255));
    c.restore();
    c.save();
    c.setGlobalAlpha(float(slide));
    tracked(c, face("semi", 11), 114, cardY + 28, "DIFF  /  REVISION 2481", rgba(106, 106, 100), 1.3);
    fillText(c, face("serifBold", 23), 114, cardY + 62,
             "Treatment of emergency supplemental funds", kInk);
    c.setFillStyle(rgba(225, 243, 226));
    c.fillRoundRect(BLRoundRect(114, cardY + 78, 1144, 48, 5, 5));
    if (slide > 0.40) {
        c.setFillStyle(rgba(250, 228, 227));
        c.fillRoundRect(BLRoundRect(114, cardY + 130, 1144, 48, 5, 5));
    }
    fillText(c, face("mono", 13), 128, cardY + 108,
             "+", rgba(45, 125, 72));
    fillText(c, face("reg", 15), 150, cardY + 108,
             "the emergency supplemental funds are excluded from the discretionary cap",
             rgba(40, 67, 48));
    fillText(c, face("mono", 13), 128, cardY + 160,
             "-", rgba(173, 61, 57));
    fillText(c, face("reg", 15), 150, cardY + 160,
             "the emergency supplemental funds are included in the discretionary cap",
             rgba(99, 48, 46));
    c.setFillStyle(rgba(54, 111, 186, 255));
    c.fillRect(BLRect(128, cardY + 188, 46, 3));
    fillText(c, face("reg", 12), 186, cardY + 192,
             "2 changes  \u00b7  1 editor  \u00b7  no edit summary", rgba(116, 116, 109));
    c.restore();

    const double a = easeOutCubic(wind(t, 0.46, 0.68));
    c.setFillStyle(rgba(54, 111, 186, int(16 * a)));
    c.fillRoundRect(BLRoundRect(80, 104, 1310, 764, 8, 8));
    if (a > 0.1) {
        c.setFillStyle(rgba(54, 111, 186, int(70 * a)));
        c.fillRect(BLRect(80, 104, 1310, 2));
    }
}

// 04 — Wayback Machine calendar. A year of captures is scrubbed; the selected
// snapshot gets a ring and the capture count updates.
void d04(BLContext& c, double t, int) {
    camera(c, 1.01, 1.04, 0.50, 0.48, t);
    paper(c, rgba(247, 243, 234), 46);
    c.setFillStyle(rgba(28, 49, 74));
    c.fillRect(BLRect(0, 0, kW, 64));
    c.setFillStyle(rgba(255, 255, 255));
    tracked(c, face("semi", 13), 30, 37, "WEB ARCHIVE", rgba(230, 237, 241), 1.4);
    c.setFillStyle(rgba(255, 255, 255, 18));
    c.fillRoundRect(BLRoundRect(410, 16, 1100, 34, 17, 17));
    c.setFillStyle(rgba(111, 202, 139));
    c.fillCircle(BLCircle(430, 33, 5));
    fillText(c, face("reg", 15), 448, 39, "web.archive.org/web/20141118000000/*/briefing-room", rgba(225, 233, 238));
    tracked(c, face("med", 11), 1710, 37, "SAVE PAGE", rgba(230, 237, 241), 1.2);

    tracked(c, face("semi", 12), 120, 112, "THE WAYBACK MACHINE", rgba(100, 96, 87), 1.5);
    fillText(c, face("serifBold", 38), 120, 154, "Browse the archive", kInk);
    fillText(c, face("reg", 15), 120, 180,
             "A public record is only as reliable as the version someone kept.", rgba(104, 100, 92));

    c.setFillStyle(rgba(255, 255, 255, 135));
    c.fillRoundRect(BLRoundRect(120, 206, 870, 60, 8, 8));
    fillText(c, face("mono", 16), 140, 242, "https://briefing-room.example.gov/orders/2026", rgba(54, 55, 53));
    c.setFillStyle(rgba(28, 49, 74));
    c.fillRoundRect(BLRoundRect(902, 214, 76, 44, 6, 6));
    tracked(c, face("semi", 11), 914, 241, "GO", rgba(235, 241, 244), 1.6);

    const char* years[] = {"2012", "2013", "2014", "2015", "2016"};
    for (int i = 0; i < 5; ++i) {
        const double x = 120 + i * 154;
        const bool sel = i == 2;
        c.setFillStyle(sel ? rgba(28, 49, 74) : rgba(255, 255, 255, 80));
        c.fillRoundRect(BLRoundRect(x, 294, 126, 36, 18, 18));
        textC(c, face(sel ? "semi" : "reg", 14), x + 63, 317, years[i],
              sel ? rgba(242, 246, 248) : rgba(78, 80, 76));
    }
    rule(c, 120, 348, 870, rgba(47, 50, 47, 25));

    const char* days[] = {"S", "M", "T", "W", "T", "F", "S"};
    for (int i = 0; i < 7; ++i) {
        textC(c, face("semi", 11), 186 + i * 112, 386, days[i], rgba(120, 116, 107));
    }
    // 35 cells, deterministic October/November-style calendar.
    for (int r = 0; r < 5; ++r) {
        for (int col = 0; col < 7; ++col) {
            const int idx = r * 7 + col;
            const double x = 136 + col * 112;
            const double y = 406 + r * 94;
            const bool selected = idx == 17;
            const bool hot = (idx % 6 == 1 || idx == 16 || idx == 17 || idx == 18);
            const BLRgba32 fill = hot ? rgba(61, 122, 155, 110 + (idx % 4) * 24)
                                      : rgba(218, 220, 213, 120);
            c.setFillStyle(fill);
            c.fillRoundRect(BLRoundRect(x, y, 96, 76, 7, 7));
            fillText(c, face("mono", 13), x + 10, y + 24, std::to_string(idx + 1),
                     hot ? rgba(238, 245, 247) : rgba(103, 104, 99));
            if (hot && idx != 17) {
                c.setFillStyle(rgba(238, 245, 247, 150));
                c.fillCircle(BLCircle(x + 76, y + 50, 3));
            }
            if (selected) {
                c.setFillStyle(rgba(196, 105, 49));
                c.fillCircle(BLCircle(x + 76, y + 50, 4));
            }
        }
    }

    const double scan = 136 + fmod(t * 840.0, 790.0);
    c.setFillStyle(rgba(231, 142, 67, 25));
    c.fillRect(BLRect(scan, 396, 4, 482));
    c.setFillStyle(rgba(231, 142, 67, 170));
    c.fillRect(BLRect(scan, 396, 2, 482));

    const double ring = easeOutCubic(wind(t, 0.28, 0.58));
    if (ring > 0.01) {
        c.save();
        c.setStrokeStyle(rgba(222, 128, 55, 220));
        c.setStrokeWidth(4.0);
        c.strokeRoundRect(BLRoundRect(136 + 3 * 112 - 5, 406 + 2 * 94 - 5,
                                      106, 86, 9, 9));
        c.restore();
    }

    // Capture inspector.
    c.setFillStyle(rgba(255, 255, 255, 145));
    c.fillRoundRect(BLRoundRect(1070, 294, 704, 528, 9, 9));
    tracked(c, face("semi", 11), 1096, 326, "SNAPSHOT INSPECTOR", rgba(106, 101, 92), 1.4);
    fillText(c, face("serifBold", 27), 1096, 364, "18 November 2014", kInk);
    fillText(c, face("reg", 14), 1096, 388, "briefing-room.example.gov/orders/2026", rgba(105, 101, 93));
    rule(c, 1096, 408, 650, rgba(47, 50, 47, 26));

    c.setFillStyle(rgba(28, 49, 74, 8));
    c.fillRoundRect(BLRoundRect(1096, 430, 650, 128, 6, 6));
    tracked(c, face("semi", 11), 1114, 458, "CAPTURED URL", rgba(116, 111, 101), 1.3);
    fillText(c, face("mono", 12), 1114, 486, "http://briefing-room.example.gov/orders/2026", rgba(57, 59, 56));
    fillText(c, face("mono", 12), 1114, 512, "HTTP 200  \u00b7  text/html  \u00b7  41 KB", rgba(116, 111, 101));

    const double count = 14.0 * easeOutCubic(wind(t, 0.34, 0.70));
    fillText(c, face("serifBold", 58), 1096, 630, std::to_string(int(std::lround(count))), rgba(28, 49, 74));
    fillText(c, face("reg", 14), 1164, 620, "captures", rgba(105, 101, 93));
    fillText(c, face("reg", 13), 1164, 639, "on this URL", rgba(137, 131, 120));
    rule(c, 1096, 658, 650, rgba(47, 50, 47, 26));

    const char* labels[] = {"Latest capture", "First capture", "Calendar view"};
    const char* values[] = {"22 Nov 2026", "04 Mar 2009", "2014"};
    for (int i = 0; i < 3; ++i) {
        fillText(c, face("reg", 13), 1096, 692 + i * 32, labels[i], rgba(109, 105, 96));
        fillText(c, face("mono", 12), 1430, 692 + i * 32, values[i], rgba(48, 51, 48));
    }
    pill(c, 1096, 796 - 26, 192, 36, rgba(28, 49, 74), "OPEN SNAPSHOT", rgba(236, 242, 245), 11);
    fillText(c, face("reg", 11), 1320, 800,
             "archive.org is a non-profit library", rgba(130, 125, 115));
}

// 05 — Search results. Query terms are underlined; the sealed result gets an
// expanding evidence frame and a red status chip.
void d05(BLContext& c, double t, int) {
    camera(c, 1.01, 1.04, 0.49, 0.50, t);
    paper(c, rgba(252, 251, 248), 30);
    browserChrome(c, "search.example.org/results?q=warrant+courtlistener", false, "SEARCH");
    tracked(c, face("black", 15), 150, 112, "THE ARCHIVE", rgba(36, 43, 53), 2.0);
    c.setFillStyle(rgba(36, 43, 53));
    c.fillCircle(BLCircle(282, 107, 4));

    c.setFillStyle(rgba(255, 255, 255));
    c.fillRoundRect(BLRoundRect(150, 132, 1390, 60, 30, 30));
    outline(c, 150, 132, 1390, 60, rgba(50, 50, 48, 45), 1.2, 30);
    searchIcon(c, 184, 162, 10, rgba(86, 88, 86));
    fillText(c, face("reg", 19), 216, 169, "\"warrant\" site:courtlistener.com", rgba(39, 42, 43));
    const double qs = easeInOutCubic(wind(t, 0.10, 0.36));
    const double qx = 216 + textW(face("reg", 19), "\"warrant\"") + 10;
    c.setFillStyle(rgba(54, 111, 186, 90));
    c.fillRect(BLRect(qx, 176, 88 * qs, 3));
    c.setFillStyle(rgba(54, 111, 186));
    c.fillRoundRect(BLRoundRect(1490, 142, 40, 40, 20, 20));
    textC(c, face("semi", 14), 1510, 168, "GO", rgba(255, 255, 255));

    const char* tabs[] = {"All", "News", "Images", "Documents"};
    for (int i = 0; i < 4; ++i) {
        const double x = 154 + i * 116;
        if (i == 0) {
            c.setFillStyle(rgba(54, 111, 186));
            c.fillRect(BLRect(x, 218, 34, 3));
        }
        fillText(c, face(i == 0 ? "semi" : "reg", 15), x, 213, tabs[i],
                 i == 0 ? rgba(34, 57, 85) : rgba(102, 105, 102));
    }
    fillText(c, face("reg", 13), 154, 250, "About 1,240,000 results (0.41 seconds)", rgba(114, 116, 112));

    struct Result { const char* title; const char* url; const char* line1; const char* line2; const char* tag; };
    const Result results[] = {
        {"Docket 1:26-cr-00418 — United States v. Doe", "courtlistener.com/docket/1:26-cr-00418",
         "Full docket sheet, entries 001-007, and the sealed appendix.", "Last updated 22 Nov 2026.", ""},
        {"Order granting temporary sealing — Memorandum", "courtlistener.com/recap/gov.uscourts/nysd.418",
         "The court finds that continued sealing is necessary to protect", "an ongoing investigation. Filed 19 Nov 2026.", "SEALED"},
        {"Search warrant application — redacted appendix", "courtlistener.com/recap/gov.uscourts/nysd.421",
         "Redacted application and supporting affidavit. The exhibit list", "references a second, unrelated matter.", ""},
    };
    for (int i = 0; i < 3; ++i) {
        const double y = 290 + i * 174;
        const double a = easeOutCubic(wind(t, 0.16 + i * 0.08, 0.34 + i * 0.08));
        if (a <= 0.01) continue;
        c.save();
        c.setGlobalAlpha(float(a));
        if (i == 1) {
            const double frame = easeInOutCubic(wind(t, 0.38, 0.58));
            c.setFillStyle(rgba(54, 111, 186, 10));
            c.fillRoundRect(BLRoundRect(132, y - 18, 1338, 152, 9, 9));
            outline(c, 132, y - 18, 1338, 152, rgba(54, 111, 186, int(80 * frame)), 1.4, 9);
        }
        fillText(c, face("serifBold", 22), 154, y + 10, results[i].title, rgba(43, 72, 112));
        fillText(c, face("reg", 12), 154, y + 32, results[i].url, rgba(67, 128, 87));
        fillText(c, face("reg", 14), 154, y + 59, results[i].line1, rgba(78, 81, 78));
        fillText(c, face("reg", 14), 154, y + 80, results[i].line2, rgba(78, 81, 78));
        if (std::string(results[i].tag) == "SEALED") {
            pill(c, 1424, y + 22, 82, 26, rgba(190, 49, 42), "SEALED", rgba(255, 239, 235), 10);
        }
        c.restore();
    }

    // Knowledge panel.
    const double kp = easeOutCubic(wind(t, 0.46, 0.66));
    c.save();
    c.setGlobalAlpha(float(kp));
    c.setFillStyle(rgba(255, 255, 255, 155));
    c.fillRoundRect(BLRoundRect(1530, 286, 292, 554, 10, 10));
    tracked(c, face("semi", 10), 1550, 314, "KNOWLEDGE PANEL", rgba(115, 112, 105), 1.3);
    fillText(c, face("serifBold", 27), 1550, 350, "1:26-cr-00418", kInk);
    fillText(c, face("reg", 13), 1550, 373, "Southern District of New York", rgba(109, 106, 99));
    rule(c, 1550, 390, 250, rgba(49, 50, 47, 28));
    fillText(c, face("semi", 13), 1550, 418, "Parties", rgba(60, 61, 57));
    fillText(c, face("reg", 13), 1550, 440, "United States of America", rgba(84, 86, 81));
    fillText(c, face("reg", 13), 1550, 460, "John Doe", rgba(84, 86, 81));
    fillText(c, face("semi", 13), 1550, 492, "Judge", rgba(60, 61, 57));
    fillText(c, face("reg", 13), 1550, 514, "Hon. M. Calder", rgba(84, 86, 81));
    fillText(c, face("semi", 13), 1550, 546, "Status", rgba(60, 61, 57));
    pill(c, 1550, 558, 88, 26, rgba(190, 49, 42), "SEALED", rgba(255, 239, 235), 10);
    rule(c, 1550, 606, 250, rgba(49, 50, 47, 28));
    fillText(c, face("reg", 12), 1550, 634, "Sources: PACER, CourtListener", rgba(117, 113, 105));
    c.setFillStyle(rgba(54, 111, 186, 70));
    c.fillCircle(BLCircle(1550, 672, 4));
    fillText(c, face("reg", 11), 1564, 676, "Cached 14 minutes ago", rgba(117, 113, 105));
    c.restore();

    c.setFillStyle(rgba(54, 111, 186, 12));
    c.fillRect(BLRect(0, 1030, kW, 50));
    tracked(c, face("reg", 11), 154, 1060, "SEARCH INDEX  /  PUBLIC RECORDS ONLY  /  NO PAYWALL", rgba(110, 112, 108), 1.3);
    fillText(c, face("mono", 11), 1620, 1060, "1-3 / 3", rgba(110, 112, 108));
}

// 06 — Fact-check. The verdict meter fills; the FALSE stamp lands over the
// rating card while the claim underline sweeps.
void d06(BLContext& c, double t, int) {
    camera(c, 1.01, 1.04, 0.50, 0.49, t);
    paper(c, rgba(246, 241, 231), 52);
    browserChrome(c, "factcheck.example.org/2026/11/22/federal-budget-claim/", false, "FACT CHECK");

    tracked(c, face("black", 12), 120, 112, "FACT CHECK  /  VERIFICATION", rgba(99, 94, 83), 2.0);
    fillText(c, face("serifBold", 54), 120, 174, "Did the budget cut", kInk);
    fillText(c, face("serifBold", 54), 120, 232, "emergency relief by $40B?", kInk);
    fillText(c, face("reg", 14), 120, 264, "A viral post misreads the supplemental funding table.", rgba(106, 101, 91));

    c.setFillStyle(rgba(255, 255, 255, 120));
    c.fillRoundRect(BLRoundRect(120, 302, 1190, 170, 8, 8));
    tracked(c, face("semi", 11), 144, 330, "THE CLAIM", rgba(118, 112, 100), 1.4);
    fillText(c, face("serifItalic", 27), 144, 374,
             "\u201cThe 2026 budget cuts emergency relief by $40 billion.\u201d", rgba(52, 50, 44));
    fillText(c, face("reg", 13), 144, 404, "Source: social post, 21 Nov 2026  \u00b7  18.4K shares",
             rgba(121, 115, 103));

    const double us = easeInOutCubic(wind(t, 0.16, 0.46));
    c.setFillStyle(rgba(190, 49, 42, 30));
    c.fillRect(BLRect(146, 390, 602 * us, 20));
    c.setFillStyle(rgba(190, 49, 42, 210));
    c.fillRect(BLRect(146, 411, 602 * us, 3));

    tracked(c, face("semi", 11), 120, 522, "OUR RATING", rgba(118, 112, 100), 1.4);
    fillText(c, face("serifBold", 30), 120, 558, "False", rgba(190, 49, 42));
    fillText(c, face("reg", 14), 120, 582,
             "The supplemental appropriation is excluded from the cap, not cut.", rgba(91, 87, 78));

    const double fill = easeInOutCubic(wind(t, 0.28, 0.62));
    const char* meter[] = {"FALSE", "MOSTLY FALSE", "MIXED", "MOSTLY TRUE", "TRUE"};
    for (int i = 0; i < 5; ++i) {
        const double x = 120 + i * 230;
        const bool active = i == 0;
        const double local = active ? fill : 0.0;
        c.setFillStyle(rgba(214, 210, 199, 160));
        c.fillRoundRect(BLRoundRect(x, 620, 208, 76, 5, 5));
        if (local > 0.01) {
            c.setFillStyle(rgba(190, 49, 42, 220));
            c.fillRoundRect(BLRoundRect(x, 620, 208 * local, 76, 5, 5));
        }
        if (active) {
            textC(c, face("semi", 11), x + 104, 654, meter[i],
                  local > 0.6 ? rgba(255, 238, 234) : rgba(94, 89, 80));
        } else {
            textC(c, face("semi", 11), x + 104, 654, meter[i], rgba(94, 89, 80));
        }
    }

    c.setFillStyle(rgba(255, 255, 255, 120));
    c.fillRoundRect(BLRoundRect(120, 734, 1190, 206, 8, 8));
    tracked(c, face("semi", 11), 144, 762, "WHAT WE FOUND", rgba(118, 112, 100), 1.4);
    fillText(c, face("serifBold", 22), 144, 796,
             "The $40B figure is the supplemental emergency fund, not a cut.", kInk);
    fillText(c, face("reg", 15), 144, 826,
             "The enacted table shows $40B in emergency supplemental authority outside the", rgba(80, 78, 70));
    fillText(c, face("reg", 15), 144, 850,
             "discretionary cap. The baseline for ordinary relief actually rises by 2.1%.", rgba(80, 78, 70));
    rule(c, 144, 876, 1120, rgba(50, 48, 42, 30));
    fillText(c, face("semi", 12), 144, 902, "SOURCES", rgba(118, 112, 100));
    fillText(c, face("reg", 12), 144, 922, "OMB FY2026 enacted table  \u00b7  Congressional Budget Office cost estimate",
             rgba(100, 96, 87));

    const double s = easeOutCubic(wind(t, 0.48, 0.72));
    stamp(c, 1372, 596, 330, 112, "FALSE", rgba(190, 49, 42), -7.0, s, 47);
    if (s > 0.01) {
        c.setFillStyle(rgba(190, 49, 42, int(20 * s)));
        c.fillRoundRect(BLRoundRect(1356, 580, 362, 144, 8, 8));
    }
    rule(c, 120, 974, 1190, rgba(50, 48, 42, 30));
    tracked(c, face("reg", 11), 120, 1004, "REVIEWED 22 NOV 2026  /  BY THE VERIFICATION DESK", rgba(121, 115, 103), 1.3);
    fillText(c, face("mono", 11), 1210, 1004, "READ 04 MIN", rgba(121, 115, 103));
}

// 07 — Live blog. A new update card slides up from below; the live dot pulses
// and the right rail's latest timestamp changes.
void d07(BLContext& c, double t, int) {
    camera(c, 1.01, 1.035, 0.50, 0.50, t);
    c.setFillStyle(rgba(12, 16, 22));
    c.fillRect(BLRect(0, 0, kW, kH));
    c.setFillStyle(rgba(20, 27, 37));
    c.fillRoundRect(BLRoundRect(-100, 86, 460, 1080, 30, 30));
    browserChrome(c, "thewire.example.org/live/federal-budget-ruling", true, "LIVE");

    const double pulse = 0.55 + 0.45 * std::sin(t * 6.2);
    c.setFillStyle(rgba(190, 49, 42));
    c.fillCircle(BLCircle(122, 112, 6.0 + pulse * 2.0));
    c.setFillStyle(rgba(190, 49, 42, 45));
    c.fillCircle(BLCircle(122, 112, 13.0 + pulse * 4.0));
    tracked(c, face("semi", 11), 140, 117, "LIVE  /  BUDGET RULING", rgba(232, 190, 184), 1.4);
    fillText(c, face("serifBold", 36), 120, 162, "The ruling, minute by minute", rgba(238, 241, 244));
    fillText(c, face("reg", 14), 120, 188,
             "Reporters in Washington and New York track the emergency docket.", rgba(138, 151, 163));
    rule(c, 120, 206, 1090, rgba(255, 255, 255, 35));

    struct Update { const char* time; const char* title; const char* body; };
    const Update updates[] = {
        {"22:31", "Court clears the final procedural hurdle",
         "The clerk's office confirms the mandate will issue before midnight."},
        {"22:36", "White House counsel responds",
         "A statement says the administration is reviewing the opinion."},
        {"22:40", "The sealed appendix is now public",
         "Two pages remain redacted; the exhibit list is visible."},
    };
    for (int i = 0; i < 3; ++i) {
        const double y = 236 + i * 150;
        c.setFillStyle(rgba(255, 255, 255, 9));
        c.fillRoundRect(BLRoundRect(120, y, 1080, 118, 7, 7));
        fillText(c, face("mono", 13), 140, y + 30, updates[i].time, rgba(113, 197, 207));
        fillText(c, face("semi", 18), 206, y + 30, updates[i].title, rgba(232, 236, 239));
        fillText(c, face("reg", 14), 206, y + 55, updates[i].body, rgba(148, 160, 171));
        c.setFillStyle(rgba(101, 207, 216, 55));
        c.fillRect(BLRect(140, y + 72, 39, 2));
        fillText(c, face("reg", 10), 140, y + 94, "THE WIRE", rgba(105, 120, 133));
    }

    // New card owned by the animation.
    const double slide = easeInOutCubic(wind(t, 0.12, 0.54));
    const double cy = 760 + (1.0 - slide) * 260;
    c.save();
    c.setGlobalAlpha(float(0.98 * slide));
    roundedCard(c, 120, cy, 1080, 208, 8, rgba(248, 244, 236));
    c.restore();
    c.save();
    c.setGlobalAlpha(float(slide));
    c.setFillStyle(rgba(101, 207, 216));
    c.fillRect(BLRect(120, cy, 1080, 4));
    pill(c, 142, cy + 24, 68, 26, rgba(190, 49, 42), "NEW", rgba(255, 242, 238), 10);
    fillText(c, face("mono", 13), 224, cy + 43, "22:41", rgba(93, 91, 83));
    fillText(c, face("serifBold", 25), 142, cy + 82,
             "Judge orders the docket unsealed", rgba(29, 31, 29));
    fillText(c, face("reg", 14), 142, cy + 108,
             "The order makes entries 001-004 public. Two supporting exhibits remain sealed.", rgba(81, 82, 76));
    fillText(c, face("reg", 12), 142, cy + 136,
             "The clerk's office has not said whether it will appeal the redactions.", rgba(117, 114, 104));
    c.setFillStyle(rgba(101, 207, 216, 55));
    c.fillRect(BLRect(142, cy + 158, 44, 2));
    fillText(c, face("reg", 10), 142, cy + 180, "BREAKING  /  STAFF", rgba(105, 103, 94));
    c.restore();

    // Right rail.
    c.setFillStyle(rgba(255, 255, 255, 12));
    c.fillRoundRect(BLRoundRect(1240, 236, 540, 590, 9, 9));
    tracked(c, face("semi", 11), 1264, 268, "THE LATEST", rgba(126, 145, 159), 1.4);
    fillText(c, face("serifBold", 26), 1264, 306, "What changed", rgba(232, 236, 240));
    const char* rail[] = {"Mandate expected", "Appendix public", "Two pages sealed", "Appeal window"};
    for (int i = 0; i < 4; ++i) {
        fillText(c, face("mono", 11), 1264, 350 + i * 50, "0" + std::to_string(i + 1), rgba(100, 186, 196));
        fillText(c, face("reg", 14), 1310, 350 + i * 50, rail[i], rgba(203, 212, 220));
        rule(c, 1264, 368 + i * 50, 490, rgba(255, 255, 255, 20));
    }
    rule(c, 1264, 584, 490, rgba(255, 255, 255, 30));
    tracked(c, face("semi", 10), 1264, 616, "LAST UPDATE", rgba(126, 145, 159), 1.4);
    fillText(c, face("mono", 16), 1264, 644, "22:41 ET", rgba(232, 236, 240));
    fillText(c, face("reg", 12), 1264, 668, "2 min ago", rgba(126, 145, 159));
    const double cta = easeOutCubic(wind(t, 0.64, 0.80));
    pill(c, 1264, 700, 210, 38, rgba(101, 207, 216), "FOLLOW LIVE", rgba(12, 16, 22), 11, cta);
    fillText(c, face("reg", 12), 1264, 776,
             "Reporting: A. Shaw, M. Calder, J. Doe", rgba(126, 145, 159));
}

} // namespace

std::vector<Scene> scenesA() {
    return {
        {"d01_court_docket_filed", "Evidence & courts",
         "PACER-style docket page: sealed entry, row scan and FILED stamp",
         0.82, d01},
        {"d02_sec_edgar_redline", "Evidence & courts",
         "SEC 10-K page with a material-weakness redline and exhibit tab",
         0.84, d02},
        {"d03_wikipedia_revision_diff", "Archives & search",
         "Wikipedia page with revision history and a rising diff card",
         0.84, d03},
        {"d04_wayback_calendar", "Archives & search",
         "Wayback Machine calendar scrub with selected snapshot ring",
         0.82, d04},
        {"d05_search_results_warrant", "Archives & search",
         "Public-records search results, sealed hit and knowledge panel",
         0.84, d05},
        {"d06_factcheck_verdict", "Data & verification",
         "Fact-check claim, verdict meter and FALSE stamp",
         0.84, d06},
        {"d07_live_blog_update", "Live & broadcast",
         "Dark live blog with a new breaking update card sliding in",
         0.86, d07},
    };
}

} // namespace chronon::docshots
