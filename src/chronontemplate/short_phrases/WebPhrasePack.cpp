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
                           int enter,
                           std::vector<PhraseTrack> tracks,
                           std::vector<PhraseTextAnimator> animators,
                           std::string source_motion = {}) {
    ShortPhraseDefinition definition;
    definition.id = std::move(id);
    definition.title = std::move(title);
    definition.phrase = std::move(phrase);
    definition.enter = enter;
    definition.tracks = std::move(tracks);
    definition.textAnimators = std::move(animators);
    definition.exit = ShortPhraseExit::Reverse;
    definition.decor = ShortPhraseDecor::None;
    definition.font_size = 0.f;
    definition.light = false;
    definition.white_background = false;
    if (!source_motion.empty()) {
        definition.adaptation_note =
            "Text-only projection of the real web category motion " + source_motion +
            "; the browser/card surface itself is intentionally omitted.";
    }
    return definition;
}

ShortPhraseDefinition make(std::string id, std::string title, std::string phrase,
                           std::vector<PhraseTrack> tracks,
                           std::vector<PhraseTextAnimator> animators) {
    return make(std::move(id), std::move(title), std::move(phrase), 90,
                std::move(tracks), std::move(animators), {});
}

WebPhraseRecipe recipe(std::string family, std::string subcategory, ShortPhraseDefinition definition) {
    WebPhraseRecipe row;
    row.definition = std::move(definition);
    row.family = std::move(family);
    row.subcategory = std::move(subcategory);
    // Both phrase lanes are intentional: the same text-only entrance serves
    // short copy and long/IMPORTANT_PHRASE copy. Keep this in sync with the
    // struct default in WebPhrasePack.hpp.
    row.targets = {"short_phrase", "caption", "important_phrase"};
    return row;
}

PhraseTrack fadeIn(int settle = 20) {
    return tr("opacity", {{0, 0.f}, {settle, 1.f}, {90, 1.f}}, "out_cubic");
}

}// namespace

const std::vector<WebPhraseRecipe>& webPhraseRecipes() {
    static const std::vector<WebPhraseRecipe> rows = [] {
        std::vector<WebPhraseRecipe> out;

        // ── 20 real web-category motions, projected onto the phrase layer ────────
        // Source of truth: category "web" (14) + "web_rect_v1" (6) in
        // catalog/chronontemplate_catalog.v1.json. Only the layer tracks are
        // copied: the phrase review stays text-only, without browser/card decor.
        // web_browser_depth_dolly: real category tracks, retimed to the 60-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_aperture_scan", "Browser Depth Dolly", "Depth opens the page",
            60, {tr("position_z", {{0, 520.000000f}, {60, 0.000000f}}, "in_out_cubic"),
                tr("scale", {{0, 1.180000f}, {60, 1.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {22, 1.000000f}, {60, 1.000000f}}, "out_cubic")}, {}, "web_browser_depth_dolly")));
        // web_browser_depth_in: real category tracks, retimed to the 46-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_split_flap", "Browser Depth In", "The page comes forward",
            46, {tr("position_z", {{0, 360.000000f}, {46, 0.000000f}}, "out_cubic"),
                tr("rotation_x", {{0, 16.000000f}, {46, 0.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {18, 1.000000f}, {46, 1.000000f}}, "out_cubic")}, {}, "web_browser_depth_in")));
        // web_browser_focus_pulse: real category tracks, retimed to the 42-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_halftone_dissolve", "Browser Focus Pulse", "Focus finds the page",
            42, {tr("scale", {{0, 0.920000f}, {20, 1.035000f}, {42, 1.000000f}}, "in_out_sine"),
                tr("opacity", {{0, 0.000000f}, {14, 1.000000f}, {42, 1.000000f}}, "out_cubic")}, {}, "web_browser_focus_pulse")));
        // web_browser_parallax: real category tracks, retimed to the 52-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_ink_bloom", "Browser Parallax", "Layers move apart",
            52, {tr("position_x", {{0, -180.000000f}, {52, 0.000000f}}, "out_cubic"),
                tr("position_y", {{0, 72.000000f}, {52, 0.000000f}}, "out_cubic"),
                tr("rotation_y", {{0, 9.000000f}, {52, 0.000000f}}, "out_cubic"),
                tr("position_z", {{0, 180.000000f}, {52, 0.000000f}}, "out_cubic")}, {}, "web_browser_parallax")));
        // web_browser_scroll_focus: real category tracks, retimed to the 56-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_parallax_depth", "Browser Scroll Focus", "Scroll into focus",
            56, {tr("position_y", {{0, 260.000000f}, {38, -12.000000f}, {56, 0.000000f}}, "out_cubic"),
                tr("scale", {{0, 0.940000f}, {56, 1.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {18, 1.000000f}, {56, 1.000000f}}, "out_cubic")}, {}, "web_browser_scroll_focus")));
        // web_browser_stack_fan: real category tracks, retimed to the 54-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_slice_glitch", "Browser Stack Fan", "Cards find their stack",
            54, {tr("rotation_z", {{0, -12.000000f}, {36, 4.000000f}, {54, 0.000000f}}, "out_cubic"),
                tr("rotation_y", {{0, -24.000000f}, {36, -4.000000f}, {54, 0.000000f}}, "out_cubic"),
                tr("position_z", {{0, 240.000000f}, {36, 20.000000f}, {54, 0.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {36, 1.000000f}, {54, 1.000000f}}, "out_cubic")}, {}, "web_browser_stack_fan")));
        // web_browser_tilt_in: real category tracks, retimed to the 48-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_curtain_reveal", "Browser Tilt In", "Tilt into the page",
            48, {tr("rotation_y", {{0, -15.000000f}, {48, 0.000000f}}, "out_cubic"),
                tr("rotation_x", {{0, 5.000000f}, {48, 0.000000f}}, "out_cubic"),
                tr("position_z", {{0, -120.000000f}, {48, 0.000000f}}, "out_cubic")}, {}, "web_browser_tilt_in")));
        // web_browser_zoom_in: real category tracks, retimed to the 48-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_kinetic_split", "Browser Zoom In", "Zoom into the story",
            48, {tr("scale", {{0, 1.280000f}, {48, 1.000000f}}, "out_cubic"),
                tr("position_z", {{0, 160.000000f}, {48, 0.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {18, 1.000000f}, {48, 1.000000f}}, "out_cubic")}, {}, "web_browser_zoom_in")));
        // web_card_flip_y: real category tracks, retimed to the 42-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_staggered_manifesto", "Card Flip Y", "The card turns",
            42, {tr("rotation_y", {{0, -72.000000f}, {42, 0.000000f}}, "out_cubic"),
                tr("position_z", {{0, 220.000000f}, {42, 0.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {20, 1.000000f}, {42, 1.000000f}}, "out_cubic")}, {}, "web_card_flip_y")));
        // web_card_scale_pop: real category tracks, retimed to the 32-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_marquee_sweep", "Card Scale Pop", "Cards pop into place",
            32, {tr("scale", {{0, 0.720000f}, {22, 1.060000f}, {32, 1.000000f}}, "out_back"),
                tr("opacity", {{0, 0.000000f}, {12, 1.000000f}, {32, 1.000000f}}, "out_cubic")}, {}, "web_card_scale_pop")));
        // web_card_slide_left: real category tracks, retimed to the 40-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_card_stack", "Card Slide Left", "Slide across the page",
            40, {tr("position_x", {{0, 240.000000f}, {40, 0.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {16, 1.000000f}, {40, 1.000000f}}, "out_cubic")}, {}, "web_card_slide_left")));
        // web_card_slide_up: real category tracks, retimed to the 36-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_circle_wipe", "Card Slide Up", "Rise into the page",
            36, {tr("position_y", {{0, 180.000000f}, {36, 0.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {18, 1.000000f}, {36, 1.000000f}}, "out_cubic")}, {}, "web_card_slide_up")));
        // web_cursor_focus: real category tracks, retimed to the 40-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_grid_rhythm", "Web Cursor Focus", "Cursor finds focus",
            40, {tr("position_z", {{0, 180.000000f}, {40, 0.000000f}}, "out_cubic"),
                tr("scale", {{0, 1.040000f}, {40, 1.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {18, 1.000000f}, {40, 1.000000f}}, "out_cubic")}, {}, "web_cursor_focus")));
        // web_section_spotlight: real category tracks, retimed to the 46-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_serif_emphasis", "Web Section Spotlight", "Spotlight the section",
            46, {tr("position_z", {{0, 240.000000f}, {46, 0.000000f}}, "out_cubic"),
                tr("rotation_x", {{0, 10.000000f}, {46, 0.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {20, 1.000000f}, {46, 1.000000f}}, "out_cubic")}, {}, "web_section_spotlight")));
        // web_rect_depth_push: real category tracks, retimed to the 44-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_diagonal_cut", "Web Rect Depth Push", "Push through the page",
            44, {tr("position_z", {{0, -150.000000f}, {44, 0.000000f}}, "out_cubic"),
                tr("scale", {{0, 0.960000f}, {44, 1.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {20, 1.000000f}, {44, 1.000000f}}, "out_cubic")}, {}, "web_rect_depth_push")));
        // web_rect_focus_expand: real category tracks, retimed to the 44-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_count_to_twelve", "Web Rect Focus Expand", "Expand the focus",
            44, {tr("scale", {{0, 0.940000f}, {44, 1.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {18, 1.000000f}, {44, 1.000000f}}, "out_cubic")}, {}, "web_rect_focus_expand")));
        // web_rect_section_zoom: real category tracks, retimed to the 46-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_word_slot", "Web Rect Section Zoom", "Zoom the section",
            46, {tr("scale", {{0, 1.060000f}, {46, 1.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {14, 1.000000f}, {46, 1.000000f}}, "out_cubic")}, {}, "web_rect_section_zoom")));
        // web_rect_split_panel: real category tracks, retimed to the 44-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_end_card", "Web Rect Split Panel", "Split the page",
            44, {tr("position_x", {{0, -24.000000f}, {44, 0.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {18, 1.000000f}, {44, 1.000000f}}, "out_cubic")}, {}, "web_rect_split_panel")));
        // web_rect_tilt_settle: real category tracks, retimed to the 42-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_tilt_snap", "Web Rect Tilt Settle", "Tilt and settle",
            42, {tr("rotation_x", {{0, 6.000000f}, {42, 0.000000f}}, "out_cubic"),
                tr("rotation_y", {{0, -4.000000f}, {42, 0.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {18, 1.000000f}, {42, 1.000000f}}, "out_cubic")}, {}, "web_rect_tilt_settle")));
        // web_rect_yaw_open: real category tracks, retimed to the 44-frame entrance.
        out.push_back(recipe("web", "web", make(
            "short_phrase_web_glow_pulse", "Web Rect Yaw Open", "Yaw into view",
            44, {tr("rotation_y", {{0, -15.000000f}, {44, 0.000000f}}, "out_cubic"),
                tr("opacity", {{0, 0.000000f}, {18, 1.000000f}, {44, 1.000000f}}, "out_cubic")}, {}, "web_rect_yaw_open")));

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
