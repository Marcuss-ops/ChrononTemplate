#include "chronontemplate/important_phrases/highlight/HighlightPhrasePack.hpp"

#include <algorithm>
#include <stdexcept>
#include <utility>

namespace chronontemplate {
namespace {
    PhraseTrack track(const std::string& property, std::vector<PhraseKeyframe> keys,
                      const std::string& easing = "out_cubic") {
        return {property, easing, std::move(keys)};
    }

    PhraseTextAnimator animator(const std::string& unit, const std::string& order,
                                std::vector<PhraseTrack> properties,
                                const std::string& window = "full") {
        return {{unit, order, window}, std::move(properties)};
    }

    PhraseAccent marker(const char* id, const char* color, float width, float height,
                        float y_offset, float x_offset, float opacity,
                        int startFrame, int endFrame, float radius = 3.f, int enter = kPhraseEnterFrames) {
        const float posStart = -width * 0.495f;
        return {
            id, color, width, height, y_offset, radius, opacity,
            {track("scale_x", {{0, 0.01f}, {startFrame, 0.01f}, {endFrame, 1.f}, {enter, 1.f}}, "out_cubic"),
             track("position_x", {{0, posStart}, {startFrame, posStart}, {endFrame, 0.f}, {enter, 0.f}}, "out_cubic")},
            x_offset
        };
    }

    PhraseAnimationDefinition make(const char* id, const char* title, const char* phrase,
                                   std::vector<PhraseTrack> layer,
                                   std::vector<PhraseAccent> accents = {},
                                   std::vector<PhraseTextAnimator> text = {},
                                   int enter = kPhraseEnterFrames,
                                   float fontSizeOverride = 52.f) {
        return {id, title, phrase, enter, std::move(layer), std::move(text), {}, std::move(accents), fontSizeOverride};
    }

    ClassicPhraseStyle paperStyle(float fontSize = 52.f) {
        ClassicPhraseStyle style;
        style.font = "assets/fonts/Inter-Bold.ttf";
        style.font_size = fontSize;
        style.box = {1700.f, 380.f};
        style.position = {960.f, 540.f};
        style.background = {0.957f, 0.945f, 0.918f, 1.0f}; // Archival paper #F4F1EA
        style.fill = "#181A1B";                             // Dark archival ink
        style.stroke = "#000000";
        style.stroke_width = 0.f;
        style.glow = "#FFFFFF";
        style.glow_radius = 0.f;
        style.glow_intensity = 0.f;
        return style;
    }

    ClassicPhraseStyle darkStyle(float fontSize = 56.f) {
        ClassicPhraseStyle style;
        style.font = "assets/fonts/Inter-Bold.ttf";
        style.font_size = fontSize;
        style.box = {1700.f, 380.f};
        style.position = {960.f, 540.f};
        style.background = {0.059f, 0.067f, 0.075f, 1.0f}; // Dark cinematic #0F1113
        style.fill = "#F8FAFC";                             // Crisp white
        style.stroke = "#000000";
        style.stroke_width = 0.f;
        style.glow = "#FFFFFF";
        style.glow_radius = 0.f;
        style.glow_intensity = 0.f;
        return style;
    }
}

ClassicPhraseStyle highlightPhraseStyle() {
    return paperStyle();
}

ClassicPhraseStyle highlightPhraseStyle(HighlightPhraseAnimation a) {
    using H = HighlightPhraseAnimation;
    switch (a) {
        // Family B: Kinetic Typography (Dark background)
        case H::Doc06RedKeywordPunch:
        case H::Doc07WordImpactReveal:
        case H::Doc09CinematicUnderlineDraw:
        case H::Doc10SelectiveContrastFocus:
        case H::Doc15DocumentarySourceFocus:
            return darkStyle(56.f);

        // Family A & C: Paper / Archival background
        case H::Doc03DocumentaryQuoteMarker: {
            auto s = paperStyle(60.f);
            s.font = "assets/fonts/PlayfairDisplay-BoldItalic.ttf";
            return s;
        }
        case H::Doc08MixedFontEmphasis: {
            auto s = darkStyle(56.f);
            s.font = "assets/fonts/PlayfairDisplay-BoldItalic.ttf";
            return s;
        }
        case H::Doc12QuoteLineByLineReveal:
            return paperStyle(42.f);
        default:
            return paperStyle(52.f);
    }
}

const char* name(HighlightPhraseAnimation a) {
    using H = HighlightPhraseAnimation;
    switch (a) {
        case H::Doc01YellowMarkerSweep: return "doc_01_yellow_marker_sweep";
        case H::Doc02MultiLineStaggerHighlight: return "doc_02_multiline_stagger_highlight";
        case H::Doc03DocumentaryQuoteMarker: return "doc_03_documentary_quote_marker";
        case H::Doc04ArchivalSourceHighlight: return "doc_04_archival_source_highlight";
        case H::Doc05SelectivePhraseTracking: return "doc_05_selective_phrase_tracking";
        case H::Doc06RedKeywordPunch: return "doc_06_red_keyword_punch";
        case H::Doc07WordImpactReveal: return "doc_07_word_impact_reveal";
        case H::Doc08MixedFontEmphasis: return "doc_08_mixed_font_emphasis";
        case H::Doc09CinematicUnderlineDraw: return "doc_09_cinematic_underline_draw";
        case H::Doc10SelectiveContrastFocus: return "doc_10_selective_contrast_focus";
        case H::Doc11HeadlineCinematicZoom: return "doc_11_headline_cinematic_zoom";
        case H::Doc12QuoteLineByLineReveal: return "doc_12_quote_line_by_line_reveal";
        case H::Doc13AnalogScannerHighlight: return "doc_13_analog_scanner_highlight";
        case H::Doc14DualHighlightSequence: return "doc_14_dual_highlight_sequence";
        case H::Doc15DocumentarySourceFocus: return "doc_15_documentary_source_focus";
    }
    throw std::invalid_argument("chronontemplate::name: unknown Highlight phrase animation");
}

std::vector<HighlightPhraseAnimation> highlightPhraseAnimations() {
    return {
        HighlightPhraseAnimation::Doc01YellowMarkerSweep,
        HighlightPhraseAnimation::Doc02MultiLineStaggerHighlight,
        HighlightPhraseAnimation::Doc03DocumentaryQuoteMarker,
        HighlightPhraseAnimation::Doc04ArchivalSourceHighlight,
        HighlightPhraseAnimation::Doc05SelectivePhraseTracking,
        HighlightPhraseAnimation::Doc06RedKeywordPunch,
        HighlightPhraseAnimation::Doc07WordImpactReveal,
        HighlightPhraseAnimation::Doc08MixedFontEmphasis,
        HighlightPhraseAnimation::Doc09CinematicUnderlineDraw,
        HighlightPhraseAnimation::Doc10SelectiveContrastFocus,
        HighlightPhraseAnimation::Doc11HeadlineCinematicZoom,
        HighlightPhraseAnimation::Doc12QuoteLineByLineReveal,
        HighlightPhraseAnimation::Doc13AnalogScannerHighlight,
        HighlightPhraseAnimation::Doc14DualHighlightSequence,
        HighlightPhraseAnimation::Doc15DocumentarySourceFocus
    };
}

PhraseAnimationDefinition definition(HighlightPhraseAnimation a) {
    using H = HighlightPhraseAnimation;
    constexpr int n = 60;
    const auto layerWithOpacity = [](std::vector<PhraseTrack> tracks = {}) {
        const bool hasOpacity = std::any_of(tracks.begin(), tracks.end(),
            [](const PhraseTrack& item) { return item.property == "opacity"; });
        if (!hasOpacity) tracks.push_back(track("opacity", {{0, 1.f}, {n, 1.f}}));
        return tracks;
    };

    switch (a) {
        // ── Family A: Yellow Highlight — Documentary & Investigative ─────────
        // 01 — Yellow Marker Sweep: Single-line intense yellow marker sweep behind text
        case H::Doc01YellowMarkerSweep: {
            return make(name(a), "01 — Yellow Marker Sweep",
                "The hidden truth finally emerged.",
                layerWithOpacity(),
                {marker("marker_yellow", "#FFE600", 912.f, 72.f, 0.f, -2.f, 0.88f, 10, 32, 3.f, n)},
                {}, n, 56.f);
        }

        // 02 — Multi-Line Stagger Highlight: Two-line sequential highlight
        case H::Doc02MultiLineStaggerHighlight: {
            return make(name(a), "02 — Multi-Line Stagger Highlight",
                "Germany lost 144,000 jobs\nlast year alone.",
                layerWithOpacity(),
                {marker("m1", "#FFE600", 659.f, 68.f, -40.f, -0.5f, 0.88f, 8, 24, 3.f, n),
                 marker("m2", "#FFE600", 371.f, 68.f, 40.f, -1.5f, 0.88f, 28, 44, 3.f, n)},
                {}, n, 50.f);
        }

        // 03 — Documentary Quote Marker: Serif italic quote with yellow marker covering "my decision.”"
        case H::Doc03DocumentaryQuoteMarker: {
            return make(name(a), "03 — Documentary Quote Marker",
                "“It was my decision.”",
                layerWithOpacity(),
                {marker("quote_marker", "#FFE600", 370.f, 74.f, 0.f, 102.f, 0.86f, 12, 34, 3.f, n)},
                {}, n, 60.f);
        }

        // 04 — Archival Source Highlight: Eyebrow + Quote with camera push 1.0 -> 1.045
        case H::Doc04ArchivalSourceHighlight: {
            return make(name(a), "04 — Archival Source Highlight",
                "ARCHIVE SOURCE\nThe missing documents were discovered.",
                layerWithOpacity({track("scale", {{0, 1.0f}, {n, 1.045f}}, "out_cubic")}),
                {marker("source_marker", "#FFE600", 1020.f, 66.f, 36.f, -2.f, 0.88f, 12, 36, 3.f, n)},
                {}, n, 48.f);
        }

        // 05 — Selective Phrase Tracking: Camera pan + marker locked on "never published."
        case H::Doc05SelectivePhraseTracking: {
            return make(name(a), "05 — Selective Phrase Tracking",
                "The report was never published.",
                layerWithOpacity({track("position_x", {{0, -25.f}, {n, 25.f}}, "in_out_sine")}),
                {marker("locked_marker", "#FFE600", 440.f, 70.f, 0.f, 229.f, 0.86f, 10, 32, 3.f, n)},
                {}, n, 54.f);
        }

        // ── Family B: Kinetic Typography — Modern Documentary ────────────────
        // 06 — Red Keyword Punch: White phrase on dark, red punch on "FINAL WARNING"
        case H::Doc06RedKeywordPunch: {
            PhraseAccent punchBar = {
                "red_punch_bar", "#DC2626", 518.f, 72.f, 0.f, 3.f, 0.88f,
                {track("scale", {{0, 0.94f}, {18, 0.94f}, {30, 1.04f}, {42, 1.0f}, {n, 1.0f}}, "out_cubic"),
                 track("opacity", {{0, 0.f}, {18, 0.f}, {24, 0.88f}, {n, 0.88f}}, "linear")},
                72.f
            };
            return make(name(a), "06 — Red Keyword Punch",
                "THE FINAL WARNING",
                layerWithOpacity(),
                {punchBar}, {}, n, 64.f);
        }

        // 07 — Word Impact Reveal: Words enter sequentially, "FAR." enters larger with glow
        case H::Doc07WordImpactReveal: {
            return make(name(a), "07 — Word Impact Reveal",
                "IT WENT TOO FAR.",
                layerWithOpacity(),
                {},
                {animator("word", "forward",
                          {track("opacity", {{0, 0.f}, {36, 1.f}}),
                           track("scale", {{0, 0.82f}, {36, 1.f}})}, "reveal")},
                n, 64.f);
        }

        // 08 — Mixed Font Emphasis: Elegant italic emphasis with warm gold marker on "together."
        case H::Doc08MixedFontEmphasis: {
            PhraseAccent goldMarker = marker("gold_marker", "#D97706", 229.f, 70.f, 0.f, 140.5f, 0.70f, 14, 36, 4.f, n);
            return make(name(a), "08 — Mixed Font Emphasis",
                "It all came together.",
                layerWithOpacity({track("position_y", {{0, 14.f}, {28, 0.f}, {n, 0.f}})}),
                {goldMarker}, {}, n, 58.f);
        }

        // 09 — Cinematic Underline Draw: Surgical thin underline precisely under "the truth."
        case H::Doc09CinematicUnderlineDraw: {
            PhraseAccent underline = {
                "surgical_underline", "#E2E8F0", 264.f, 3.f, 42.f, 1.5f, 0.92f,
                {track("scale_x", {{0, 0.01f}, {12, 0.01f}, {38, 1.f}, {n, 1.f}}, "out_cubic"),
                 track("position_x", {{0, -131.f}, {12, -131.f}, {38, 0.f}, {n, 0.f}}, "out_cubic")},
                199.f
            };
            return make(name(a), "09 — Cinematic Underline Draw",
                "Nobody knew the truth.",
                layerWithOpacity(),
                {underline}, {}, n, 58.f);
        }

        // 10 — Selective Contrast Focus: Secondary words dim, "evidence" holds high contrast
        case H::Doc10SelectiveContrastFocus: {
            PhraseAccent focusPill = marker("contrast_focus", "#38BDF8", 246.f, 70.f, 0.f, -224.f, 0.65f, 12, 32, 4.f, n);
            return make(name(a), "10 — Selective Contrast Focus",
                "The evidence changed everything.",
                layerWithOpacity(),
                {focusPill}, {}, n, 54.f);
        }

        // ── Family C: Camera + Highlight — Documentary Footage & Sources ─────
        // 11 — Headline Cinematic Zoom: Camera zoom 1.0 -> 1.08, yellow marker triggers on settle
        case H::Doc11HeadlineCinematicZoom: {
            return make(name(a), "11 — Headline Cinematic Zoom",
                "SPECIAL REPORT\nTHE OVERLOOKED LEDGER",
                layerWithOpacity({track("scale", {{0, 1.0f}, {40, 1.08f}, {n, 1.08f}}, "out_cubic")}),
                {marker("headline_marker", "#FFE600", 691.f, 70.f, 38.f, -0.5f, 0.88f, 32, 54, 3.f, n)},
                {}, n, 48.f);
        }

        // 12 — Quote Line-by-Line Reveal: 3-line progressive reveal with voiceover cadence
        case H::Doc12QuoteLineByLineReveal: {
            return make(name(a), "12 — Quote Line-by-Line Reveal",
                "First, the records vanished.\nThen, the witnesses changed their testimony.\nFinally, the truth came out.",
                layerWithOpacity(),
                {marker("l1", "#FFE600", 534.f, 54.f, -60.f, -1.f, 0.86f, 6, 20, 3.f, n),
                 marker("l2", "#FFE600", 893.f, 54.f, 0.f, -1.5f, 0.86f, 22, 40, 3.f, n),
                 marker("l3", "#FFE600", 522.f, 54.f, 60.f, -1.f, 0.86f, 42, 58, 3.f, n)},
                {}, n, 40.f);
        }

        // 13 — Analog Scanner Highlight: Scanline feel with highlighter on confidential memo
        case H::Doc13AnalogScannerHighlight: {
            PhraseAccent confidentialBox = {
                "confidential_box", "#DC2626", 420.f, 32.f, -48.f, 2.f, 0.85f,
                {track("opacity", {{0, 0.f}, {8, 0.85f}, {n, 0.85f}}, "linear")},
                0.f
            };
            PhraseAccent scanMarker = marker("scan_marker", "#FFE600", 898.f, 66.f, 34.f, -1.f, 0.86f, 16, 44, 3.f, n);
            return make(name(a), "13 — Analog Scanner Highlight",
                "CONFIDENTIAL MEMORANDUM\nSUBJECT: FINANCIAL DISCREPANCIES",
                layerWithOpacity({track("scale", {{0, 1.0f}, {n, 1.03f}}, "in_out_sine")}),
                {confidentialBox, scanMarker}, {}, n, 46.f);
        }

        // 14 — Dual Highlight Sequence: Two distinct regions highlighted with a narrative pause
        case H::Doc14DualHighlightSequence: {
            PhraseAccent r1 = marker("dual_region_1", "#FFE600", 338.f, 66.f, -34.f, -210.f, 0.88f, 10, 26, 3.f, n);
            PhraseAccent r2 = marker("dual_region_2", "#FFE600", 435.f, 66.f, 34.f, 32.5f, 0.88f, 38, 54, 3.f, n);
            return make(name(a), "14 — Dual Highlight Sequence",
                "The first claim was contradicted\nby the second report.",
                layerWithOpacity(),
                {r1, r2}, {}, n, 48.f);
        }

        // 15 — Documentary Source Focus: Forensic cyan marker on source citation with long hold
        case H::Doc15DocumentarySourceFocus: {
            PhraseAccent sourceMarker = marker("source_cyan", "#06B6D4", 1006.f, 68.f, 34.f, -2.f, 0.82f, 10, 32, 3.f, n);
            return make(name(a), "15 — Documentary Source Focus",
                "SOURCE: INTERNAL LOGS\nAccess was granted without authorization.",
                layerWithOpacity({track("position_y", {{0, 10.f}, {24, 0.f}, {n, 0.f}})}),
                {sourceMarker}, {}, n, 48.f);
        }
    }
    throw std::invalid_argument("chronontemplate::definition: unknown Highlight phrase animation");
}

}// namespace chronontemplate
