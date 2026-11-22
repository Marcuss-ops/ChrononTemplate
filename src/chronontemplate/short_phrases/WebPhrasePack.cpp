#include "chronontemplate/short_phrases/WebPhrasePack.hpp"

#include <utility>

namespace chronontemplate::web_phrase {
namespace {

using Keys = std::initializer_list<std::pair<int, float>>;

PhraseTrack tr(std::string property, Keys keys, std::string easing = "out_cubic") {
    PhraseTrack track;
    track.property = std::move(property);
    track.easing = std::move(easing);
    for (const auto& [frame, value] : keys) track.keyframes.push_back({frame, value});
    return track;
}

PhraseTextAnimator anim(std::string unit, std::string order, std::string window,
                        std::vector<PhraseTrack> properties) {
    PhraseTextAnimator result;
    result.selector = {std::move(unit), std::move(order), std::move(window)};
    result.properties = std::move(properties);
    return result;
}

ShortPhraseDefinition make(std::string id, std::string title, std::string phrase,
                           std::vector<PhraseTrack> tracks,
                           std::vector<PhraseTextAnimator> animators) {
    ShortPhraseDefinition definition;
    definition.id = std::move(id);
    definition.title = std::move(title);
    definition.phrase = std::move(phrase);
    definition.enter = 90;
    definition.tracks = std::move(tracks);
    definition.textAnimators = std::move(animators);
    definition.exit = ShortPhraseExit::Reverse;
    definition.decor = ShortPhraseDecor::None;
    definition.font_size = 0.f;
    definition.light = false;
    definition.white_background = false;
    return definition;
}

WebPhraseRecipe recipe(std::string family, std::string subcategory, ShortPhraseDefinition definition) {
    WebPhraseRecipe row;
    row.definition = std::move(definition);
    row.family = std::move(family);
    row.subcategory = std::move(subcategory);
    row.targets = {"short_phrase", "caption"};
    return row;
}

/// Every recipe carries the same quiet layer entrance; the recipe itself is the
/// text gesture. This is what keeps the MP4 to text over the default plate.
PhraseTrack fadeIn(int settle = 20) {
    return tr("opacity", {{0, 0.f}, {settle, 1.f}, {90, 1.f}}, "out_cubic");
}

}// namespace

const std::vector<WebPhraseRecipe>& webPhraseRecipes() {
    static const std::vector<WebPhraseRecipe> rows = [] {
        std::vector<WebPhraseRecipe> out;

        // ── The 20 web gestures, distilled to text only ───────────────────────
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_aperture_scan", "Web Aperture Scan", "Aperture scan",
            {fadeIn(24), tr("scale", {{0, 1.03f}, {45, 1.f}, {90, 1.f}})},
            {anim("glyph", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {40, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, 18.f}, {40, 0.f}, {90, 0.f}}),
                tr("tracking", {{0, 12.f}, {40, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_split_flap", "Web Split Flap", "Signal becomes meaning",
            {fadeIn(18), tr("position_y", {{0, -12.f}, {30, 0.f}, {90, 0.f}})},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.f}, {40, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, 24.f}, {40, 0.f}, {90, 0.f}}),
                tr("scale_y", {{0, 0.55f}, {40, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_halftone_dissolve", "Web Halftone Dissolve", "Dots become language",
            {fadeIn(30)},
            {anim("glyph", "forward", "reveal_soft", {
                tr("opacity", {{0, 0.f}, {70, 1.f}, {90, 1.f}}, "linear"),
                tr("scale", {{0, 0.88f}, {70, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_ink_bloom", "Web Ink Bloom", "Ink finds its edge",
            {fadeIn(20), tr("scale", {{0, 0.96f}, {24, 1.02f}, {55, 1.f}, {90, 1.f}})},
            {anim("glyph", "forward", "reveal_soft", {
                tr("opacity", {{0, 0.f}, {55, 1.f}, {90, 1.f}}, "linear"),
                tr("scale", {{0, 0.82f}, {55, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_parallax_depth", "Web Parallax Depth", "Depth behind the page",
            {fadeIn(20), tr("position_x", {{0, -36.f}, {50, 0.f}, {90, 0.f}}),
             tr("scale", {{0, 1.05f}, {50, 1.f}, {90, 1.f}})},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.f}, {45, 1.f}, {90, 1.f}}, "linear"),
                tr("position_x", {{0, -18.f}, {45, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_slice_glitch", "Web Slice Glitch", "Slices realign",
            {fadeIn(14), tr("position_x", {{0, 0.f}, {8, -14.f}, {14, 10.f}, {20, -6.f},
                                           {26, 4.f}, {34, 0.f}, {90, 0.f}}, "linear")},
            {anim("glyph", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {6, 0.f}, {8, 1.f}, {12, 0.f}, {14, 1.f},
                               {90, 1.f}}, "linear"),
                tr("position_x", {{0, 6.f}, {34, 0.f}, {90, 0.f}}, "linear")})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_curtain_reveal", "Web Curtain Reveal", "The page opens",
            {fadeIn(20)},
            {anim("word", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {55, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, -34.f}, {55, 0.f}, {90, 0.f}}),
                tr("tracking", {{0, 10.f}, {55, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_kinetic_split", "Web Kinetic Split", "Split the frame",
            {fadeIn(18)},
            {anim("word", "from_center", "band", {
                tr("opacity", {{0, 0.f}, {50, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, -26.f}, {50, 0.f}, {90, 0.f}}),
                tr("scale", {{0, 0.94f}, {50, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_staggered_manifesto", "Web Staggered Manifesto", "Three beats land",
            {fadeIn(18)},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.f}, {50, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, 22.f}, {50, 0.f}, {90, 0.f}}),
                tr("tracking", {{0, 6.f}, {50, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_marquee_sweep", "Web Marquee Sweep", "The line keeps moving",
            {fadeIn(16), tr("position_x", {{0, 42.f}, {55, 0.f}, {90, 0.f}})},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.f}, {50, 1.f}, {90, 1.f}}, "linear"),
                tr("tracking", {{0, 18.f}, {50, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_card_stack", "Web Card Stack", "Cards find their stack",
            {fadeIn(18)},
            {anim("word", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {50, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, 58.f}, {50, 0.f}, {90, 0.f}}),
                tr("scale", {{0, 0.90f}, {50, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_circle_wipe", "Web Circle Wipe", "One point one field",
            {fadeIn(20), tr("scale", {{0, 1.04f}, {50, 1.f}, {90, 1.f}})},
            {anim("glyph", "from_center", "reveal_soft", {
                tr("opacity", {{0, 0.f}, {60, 1.f}, {90, 1.f}}, "linear"),
                tr("scale", {{0, 0.92f}, {60, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_grid_rhythm", "Web Grid Rhythm", "Order from the grid",
            {fadeIn(16)},
            {anim("glyph", "from_center", "reveal_soft", {
                tr("opacity", {{0, 0.f}, {60, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, -12.f}, {60, 0.f}, {90, 0.f}}),
                tr("scale", {{0, 0.94f}, {60, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_serif_emphasis", "Web Serif Emphasis", "Emphasis without noise",
            {fadeIn(20)},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.35f}, {40, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, 12.f}, {40, 0.f}, {90, 0.f}}),
                tr("fill_blue", {{0, 0.f}, {30, 0.70f}, {55, 0.f}, {90, 0.f}}, "in_out_cubic")})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_diagonal_cut", "Web Diagonal Cut", "Cut through the frame",
            {fadeIn(18), tr("position_x", {{0, -28.f}, {55, 0.f}, {90, 0.f}}),
             tr("position_y", {{0, 20.f}, {55, 0.f}, {90, 0.f}})},
            {anim("word", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {50, 1.f}, {90, 1.f}}, "linear"),
                tr("position_x", {{0, -18.f}, {50, 0.f}, {90, 0.f}}),
                tr("position_y", {{0, 10.f}, {50, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_count_to_twelve", "Web Count To Twelve", "Count every beat",
            {fadeIn(16)},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.f}, {40, 1.f}, {90, 1.f}}, "linear"),
                tr("scale", {{0, 0.78f}, {30, 1.07f}, {55, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_word_slot", "Web Word Slot", "Each word takes its slot",
            {fadeIn(16)},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.f}, {45, 1.f}, {90, 1.f}}, "linear"),
                tr("scale_y", {{0, 0.55f}, {45, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_end_card", "Web End Card", "Make it move",
            {fadeIn(24), tr("scale", {{0, 1.03f}, {50, 1.f}, {90, 1.f}})},
            {anim("glyph", "forward", "full", {
                tr("opacity", {{0, 0.f}, {40, 1.f}, {90, 1.f}}, "linear"),
                tr("tracking", {{0, 2.f}, {40, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_tilt_snap", "Web Tilt Snap", "Tilt into place",
            {fadeIn(16), tr("rotation_y", {{0, -14.f}, {30, 2.f}, {50, 0.f}, {90, 0.f}}),
             tr("position_x", {{0, -18.f}, {50, 0.f}, {90, 0.f}})},
            {anim("word", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {45, 1.f}, {90, 1.f}}, "linear"),
                tr("position_x", {{0, 8.f}, {45, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "web", make(
            "short_phrase_web_glow_pulse", "Web Glow Pulse", "A pulse of light",
            {fadeIn(20)},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.60f}, {40, 1.f}, {90, 1.f}}, "linear"),
                tr("fill_blue", {{0, 0.f}, {30, 0.50f}, {60, 0.f}, {90, 0.f}}, "in_out_cubic"),
                tr("scale", {{0, 1.02f}, {40, 1.f}, {90, 1.f}})})})));

        // ── The 10 entrance gestures ──────────────────────────────────────────
        out.push_back(recipe("web", "typewriter", make(
            "short_phrase_web_typewriter_carriage", "Typewriter Carriage", "Type the signal",
            {fadeIn(12)},
            {anim("glyph", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {55, 1.f}, {90, 1.f}}, "linear"),
                tr("position_x", {{0, 12.f}, {55, 0.f}, {90, 0.f}}),
                tr("tracking", {{0, 6.f}, {55, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "typewriter", make(
            "short_phrase_web_typewriter_staccato", "Typewriter Staccato", "Short sharp beats",
            {fadeIn(10)},
            {anim("glyph", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {12, 0.f}, {14, 1.f}, {20, 0.f}, {22, 1.f},
                               {30, 0.f}, {32, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, 5.f}, {32, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "typewriter", make(
            "short_phrase_web_typewriter_line_feed", "Typewriter Line Feed", "The line returns",
            {fadeIn(14)},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.f}, {45, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, -10.f}, {45, 0.f}, {90, 0.f}}),
                tr("position_x", {{0, -6.f}, {45, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "highlighting", make(
            "short_phrase_web_highlight_marker_fill", "Highlight Marker Fill", "Mark the words",
            {fadeIn(16)},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.50f}, {30, 1.f}, {90, 1.f}}, "linear"),
                tr("fill_blue", {{0, 0.f}, {30, 0.85f}, {60, 0.45f}, {90, 0.45f}}, "in_out_cubic"),
                tr("position_y", {{0, 6.f}, {30, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "highlighting", make(
            "short_phrase_web_highlight_word_band", "Highlight Word Band", "The band travels",
            {fadeIn(14)},
            {anim("word", "forward", "band", {
                tr("opacity", {{0, 0.75f}, {30, 1.f}, {90, 1.f}}, "linear"),
                tr("fill_blue", {{0, 0.f}, {30, 0.65f}, {60, 0.f}, {90, 0.f}}, "in_out_cubic"),
                tr("scale", {{0, 1.05f}, {40, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "highlighting", make(
            "short_phrase_web_highlight_emphasis_settle", "Highlight Emphasis Settle", "Emphasis settles",
            {fadeIn(14)},
            {anim("word", "forward", "full", {
                tr("opacity", {{0, 0.70f}, {40, 1.f}, {90, 1.f}}, "linear"),
                tr("fill_blue", {{0, 0.80f}, {40, 0.25f}, {90, 0.25f}}, "out_cubic"),
                tr("position_y", {{0, 8.f}, {40, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "geometric", make(
            "short_phrase_web_geometric_yaw_open", "Geometric Yaw Open", "Turn into view",
            {fadeIn(18), tr("rotation_y", {{0, -18.f}, {50, 0.f}, {90, 0.f}}),
             tr("position_x", {{0, -24.f}, {50, 0.f}, {90, 0.f}})},
            {anim("word", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {50, 1.f}, {90, 1.f}}, "linear"),
                tr("position_x", {{0, 10.f}, {50, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "geometric", make(
            "short_phrase_web_geometric_pow_scale", "Geometric Pow Scale", "Pow into focus",
            {fadeIn(12), tr("scale", {{0, 0.82f}, {32, 1.08f}, {55, 1.f}, {90, 1.f}})},
            {anim("glyph", "from_center", "reveal_soft", {
                tr("opacity", {{0, 0.f}, {55, 1.f}, {90, 1.f}}, "linear"),
                tr("scale", {{0, 0.86f}, {55, 1.f}, {90, 1.f}})})})));

        out.push_back(recipe("web", "geometric", make(
            "short_phrase_web_geometric_pitch_lift", "Geometric Pitch Lift", "Lift from the page",
            {fadeIn(18), tr("rotation_x", {{0, 14.f}, {55, 0.f}, {90, 0.f}}),
             tr("position_y", {{0, 24.f}, {55, 0.f}, {90, 0.f}})},
            {anim("word", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {55, 1.f}, {90, 1.f}}, "linear"),
                tr("position_y", {{0, 12.f}, {55, 0.f}, {90, 0.f}})})})));

        out.push_back(recipe("web", "geometric", make(
            "short_phrase_web_geometric_depth_push", "Geometric Depth Push", "Push through depth",
            {fadeIn(16), tr("scale", {{0, 1.12f}, {55, 1.f}, {90, 1.f}})},
            {anim("glyph", "forward", "reveal", {
                tr("opacity", {{0, 0.f}, {55, 1.f}, {90, 1.f}}, "linear"),
                tr("scale", {{0, 0.88f}, {55, 1.f}, {90, 1.f}})})})));

        return out;
    }();
    return rows;
}

}// namespace chronontemplate::web_phrase
