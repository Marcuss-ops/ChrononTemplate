#include "chronontemplate/important_phrases/highlight/PhraseHighlightPack.hpp"

#include <stdexcept>
#include <utility>

namespace chronontemplate {
namespace {

    PhraseTrack track(const char* property, std::vector<PhraseKeyframe> keys,
                      const char* easing = "out_cubic") {
        return PhraseTrack{property, easing, std::move(keys)};
    }

    PhraseAccent accent(const char* id, const char* color, float width, float height,
                        float y, float radius, float opacity,
                        std::vector<PhraseTrack> tracks) {
        return PhraseAccent{id, color, width, height, y, radius, opacity, std::move(tracks)};
    }

    PhraseAnimationDefinition make(const char* id, const char* title, const char* phrase,
                                   std::vector<PhraseAccent> accents, int enter = 78) {
        // 78 frames, not kPhraseEnterFrames: the accent sweeps hold until frame
        // 78, so a shorter entrance would clip them. See the Highlight contract
        // test, which pins that every keyframe completes inside `enter`.
        // Keep the phrase's vertical placement fixed. The GPU text path can
        // collapse animated position_y updates into a thin strip on frame boundaries.
        return PhraseAnimationDefinition{
            id, title, phrase, enter,
            {track("opacity", {{0, 0.f}, {22, 1.f}, {enter, 1.f}}, "linear")},
            {}, {}, std::move(accents), 94.f
        };
    }

    PhraseAccent sweep(const char* id, const char* color, float width, float height,
                       float y, float opacity = 1.f, int start = 32, int finish = 62) {
        const int hold = finish >= 78 ? finish + 1 : 78;
        return accent(id, color, width, height, y, height * .5f, opacity,
                      {track("scale_x", {{0, .01f}, {start, .01f}, {finish, 1.f}, {hold, 1.f}}, "linear"),
                       track("position_x", {{0, -width * .5f}, {start, -width * .5f},
                                             {finish, 0.f}, {hold, 0.f}}, "linear")});
    }

}// namespace

const char* name(PhraseHighlightAnimation animation) {
    switch (animation) {
        case PhraseHighlightAnimation::RedUnderlineSweep: return "phrase_red_underline_sweep";
        case PhraseHighlightAnimation::WarmMarkerSweep: return "phrase_warm_marker_sweep";
        case PhraseHighlightAnimation::CenterOutUnderline: return "phrase_center_out_underline";
        case PhraseHighlightAnimation::DoubleRule: return "phrase_double_rule";
        case PhraseHighlightAnimation::DelayedAccent: return "phrase_delayed_accent";
        case PhraseHighlightAnimation::SoftPulse: return "phrase_soft_pulse";
        case PhraseHighlightAnimation::ShortKeywordRule: return "phrase_short_keyword_rule";
        case PhraseHighlightAnimation::StaggeredLines: return "phrase_staggered_lines";
        case PhraseHighlightAnimation::IvoryUnderline: return "phrase_ivory_underline";
        case PhraseHighlightAnimation::RedMarkerPulse: return "phrase_red_marker_pulse";
        case PhraseHighlightAnimation::OffsetDoubleRule: return "phrase_offset_double_rule";
        case PhraseHighlightAnimation::GoldDrawOn: return "phrase_gold_draw_on";
        case PhraseHighlightAnimation::CenterDash: return "phrase_center_dash";
        case PhraseHighlightAnimation::TripleEditorialRule: return "phrase_triple_editorial_rule";
        case PhraseHighlightAnimation::SplitMarker: return "phrase_split_marker";
        case PhraseHighlightAnimation::SlowReveal: return "phrase_slow_reveal";
        case PhraseHighlightAnimation::YellowHighlighterSweep: return "phrase_yellow_highlighter_sweep";
    }
    throw std::invalid_argument("unknown phrase highlight animation");
}

std::vector<PhraseHighlightAnimation> phraseHighlightAnimations() {
    return {PhraseHighlightAnimation::RedUnderlineSweep,
            PhraseHighlightAnimation::WarmMarkerSweep,
            PhraseHighlightAnimation::CenterOutUnderline,
            PhraseHighlightAnimation::DoubleRule,
            PhraseHighlightAnimation::DelayedAccent,
            PhraseHighlightAnimation::SoftPulse,
            PhraseHighlightAnimation::ShortKeywordRule,
            PhraseHighlightAnimation::StaggeredLines,
            PhraseHighlightAnimation::IvoryUnderline,
            PhraseHighlightAnimation::RedMarkerPulse,
            PhraseHighlightAnimation::OffsetDoubleRule,
            PhraseHighlightAnimation::GoldDrawOn,
            PhraseHighlightAnimation::CenterDash,
            PhraseHighlightAnimation::TripleEditorialRule,
            PhraseHighlightAnimation::SplitMarker,
            PhraseHighlightAnimation::SlowReveal,
            PhraseHighlightAnimation::YellowHighlighterSweep};
}

PhraseAnimationDefinition definition(PhraseHighlightAnimation animation) {
    constexpr float y = 104.f;
    constexpr float width = 1480.f;
    switch (animation) {
        case PhraseHighlightAnimation::RedUnderlineSweep:
            return make(name(animation), "Red underline sweep",
                        "OGNI SCELTA LASCIA UN SEGNO",
                        {sweep("underline", "#FF1018", width, 7.f, y)});
        case PhraseHighlightAnimation::WarmMarkerSweep:
            return make(name(animation), "Warm marker sweep",
                        "IL CAMBIAMENTO INIZIA DA QUI",
                        {sweep("marker", "#E9B66B", 1420.f, 24.f, y + 5.f, .62f, 38, 68)});
        case PhraseHighlightAnimation::CenterOutUnderline:
            return make(name(animation), "Center-out underline",
                        "NON È MAI TROPPO TARDI",
                        {accent("center_rule", "#F7F5F1", 1260.f, 6.f, y, 3.f, .9f,
                                {track("scale_x", {{0, .01f}, {42, 1.f}, {78, 1.f}}, "out_cubic")})});
        case PhraseHighlightAnimation::DoubleRule:
            return make(name(animation), "Double rule",
                        "UNA NUOVA PROSPETTIVA CAMBIA TUTTO",
                        {sweep("upper_rule", "#FF1018", 1500.f, 5.f, y - 5.f, .95f, 30, 58),
                         sweep("lower_rule", "#F7F5F1", 1320.f, 3.f, y + 9.f, .72f, 43, 72)});
        case PhraseHighlightAnimation::DelayedAccent:
            return make(name(animation), "Delayed accent",
                        "LE IDEE MIGLIORI HANNO BISOGNO DI TEMPO",
                        {sweep("late_rule", "#D94A45", 1540.f, 9.f, y, .9f, 54, 77)}, 88);
        case PhraseHighlightAnimation::SoftPulse:
            return make(name(animation), "Soft marker pulse",
                        "QUELLO CHE CONTA RESTA CON NOI",
                        {accent("soft_marker", "#C98255", 1480.f, 28.f, y + 6.f, 0.f, .44f,
                                {track("scale_x", {{0, .94f}, {34, 1.f}, {78, 1.f}}, "out_cubic"),
                                 track("opacity", {{0, 0.f}, {38, .44f}, {50, .28f},
                                                    {64, .44f}, {78, .44f}}, "in_out_sine")})});
        case PhraseHighlightAnimation::ShortKeywordRule:
            return make(name(animation), "Short keyword rule",
                        "IL VALORE NASCE DALLE PERSONE",
                        {sweep("keyword_rule", "#FF1018", 540.f, 8.f, y, 1.f, 36, 60)});
        case PhraseHighlightAnimation::StaggeredLines:
            return make(name(animation), "Staggered double accent",
                        "OGNI PASSO APRE UNA STRADA NUOVA",
                        {sweep("first_accent", "#E9B66B", 1120.f, 18.f, y - 3.f, .68f, 32, 57),
                         sweep("second_accent", "#FF1018", 760.f, 5.f, y + 13.f, 1.f, 48, 72)});
        case PhraseHighlightAnimation::IvoryUnderline:
            return make(name(animation), "Ivory underline",
                        "LE STORIE CI FANNO VEDERE OLTRE",
                        {sweep("ivory_rule", "#F7F5F1", 1380.f, 5.f, y, .9f, 34, 64)});
        case PhraseHighlightAnimation::RedMarkerPulse:
            return make(name(animation), "Red marker pulse",
                        "IL CORAGGIO CAMBIA IL PERCORSO",
                        {accent("red_marker", "#A92B2D", 1460.f, 22.f, y + 5.f, 0.f, .65f,
                                {track("scale_x", {{0, .82f}, {36, 1.f}, {54, .96f}, {78, 1.f}}, "out_cubic"),
                                 track("opacity", {{0, 0.f}, {30, .65f}, {44, .38f},
                                                    {58, .65f}, {78, .65f}}, "in_out_sine")})});
        case PhraseHighlightAnimation::OffsetDoubleRule:
            return make(name(animation), "Offset double rule",
                        "UNA SCOPERTA APRE NUOVE DOMANDE",
                        {sweep("long_rule", "#FF1018", 1420.f, 5.f, y - 3.f, 1.f, 30, 56),
                         sweep("short_rule", "#E9B66B", 840.f, 4.f, y + 11.f, .9f, 47, 73)});
        case PhraseHighlightAnimation::GoldDrawOn:
            return make(name(animation), "Gold draw-on",
                        "IL FUTURO PRENDE FORMA INSIEME",
                        {sweep("gold_draw", "#D5A65D", 1480.f, 8.f, y, .92f, 48, 76)}, 88);
        case PhraseHighlightAnimation::CenterDash:
            return make(name(animation), "Center dash",
                        "PICCOLI GESTI GRANDE IMPATTO",
                        {accent("center_dash", "#FF1018", 470.f, 7.f, y, 3.5f, 1.f,
                                {track("scale_x", {{0, .01f}, {30, 1.f}, {78, 1.f}}, "out_cubic")})});
        case PhraseHighlightAnimation::TripleEditorialRule:
            return make(name(animation), "Triple editorial rule",
                        "LA MEMORIA ATTRAVERSA LE GENERAZIONI",
                        {sweep("rule_top", "#E9B66B", 1240.f, 3.f, y - 7.f, .72f, 28, 54),
                         sweep("rule_main", "#FF1018", 1500.f, 7.f, y + 1.f, 1.f, 38, 64),
                         sweep("rule_bottom", "#F7F5F1", 980.f, 3.f, y + 12.f, .62f, 52, 78)}, 80);
        // 80, not 78: sweep() holds one frame past a finish of 78, so this
        // recipe's last keyframe is 79 and the entrance must cover it.
        case PhraseHighlightAnimation::SplitMarker:
            return make(name(animation), "Split marker",
                        "DA UNA CRISI NASCE UNA POSSIBILITÀ",
                        {sweep("left_marker", "#C98255", 660.f, 18.f, y + 4.f, .65f, 28, 52),
                         accent("right_marker", "#C98255", 660.f, 18.f, y + 4.f, 0.f, .65f,
                                {track("scale_x", {{0, .01f}, {43, 1.f}, {78, 1.f}}, "out_cubic"),
                                 track("position_x", {{0, 330.f}, {43, 0.f}, {78, 0.f}})})});
        case PhraseHighlightAnimation::SlowReveal:
            return make(name(animation), "Slow documentary underline",
                        "OGNI DETTAGLIO RACCONTA QUALCOSA",
                        {sweep("slow_rule", "#FF1018", 1500.f, 5.f, y, .88f, 46, 78)}, 88);
        case PhraseHighlightAnimation::YellowHighlighterSweep:
            return make(name(animation), "Yellow highlighter sweep",
                        "LA GERMANIA HA PERSO 144MILA POSTI DI LAVORO",
                        {sweep("yellow_highlighter", "#F2E500", 1480.f, 48.f,
                               y + 4.f, .94f, 22, 58)});
    }
    throw std::invalid_argument("unknown phrase highlight animation");
}

}// namespace chronontemplate
