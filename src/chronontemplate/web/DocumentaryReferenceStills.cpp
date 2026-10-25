#include "chronontemplate/web/DocumentaryReferenceStills.hpp"

#include <string>
#include <utility>
#include <vector>

namespace chronontemplate::web {
namespace {
using J = nlohmann::json;
constexpr int W = 1920, H = 1080;

J rgba(const std::string& hex, double alpha = 1.0) {
    const auto rgb = std::stoul(hex.substr(1), nullptr, 16);
    return J::array({((rgb >> 16) & 255) / 255.0, ((rgb >> 8) & 255) / 255.0,
                     (rgb & 255) / 255.0, alpha});
}

J rect(std::string id, double x, double y, double w, double h,
       const std::string& color, double alpha = 1.0, double rotation = 0.0) {
    J layer = {{"id", id}, {"type", "shape"}, {"enable_3d", true},
               {"position", {x + w / 2.0, H - y - h / 2.0, 0}}, {"size", {w, h}},
               {"start_frame", 0}, {"duration_frames", 1},
               {"shape", {{"type", "rect"}, {"fill", rgba(color, alpha)}}}};
    if (rotation != 0.0) layer["rotation"] = {0, 0, rotation};
    return layer;
}

J ellipse(std::string id, double x, double y, double w, double h,
          const std::string& color, double alpha = 1.0) {
    return { {"id", id}, {"type", "shape"}, {"enable_3d", true},
             {"position", {x + w / 2.0, H - y - h / 2.0, 0}}, {"size", {w, h}},
             {"start_frame", 0}, {"duration_frames", 1},
             {"shape", {{"type", "ellipse"}, {"fill", rgba(color, alpha)}}} };
}

J text(std::string id, const std::string& value, double x, double y,
       double w, double h, double size, const std::string& font,
       const std::string& fill, const std::string& align = "left",
       double opacity = 1.0) {
    J layer = {{"id", id}, {"type", "text"}, {"enable_3d", true}, {"text", value},
            {"position", {x + w / 2.0, H - y - h / 2.0, 0}}, {"size", {w, h}},
            {"start_frame", 0}, {"duration_frames", 1},
            {"style", {{"font", font}, {"font_size", size}, {"fill", fill},
                        {"fit_mode", "none"}, {"text_align", align}}}};
    if (opacity != 1.0) layer["opacity"] = opacity;
    return layer;
}

J image(std::string id, const std::string& asset, double x, double y, double w, double h) {
    return {{"id", id}, {"type", "image"}, {"enable_3d", true}, {"screen_space", true}, {"asset", asset},
            {"position", {x + w / 2.0, y + h / 2.0}}, {"size", {w, h}}, {"fit", "cover"},
            {"start_frame", 0}, {"duration_frames", 1}};
}

J make_plan(const std::string& id, J layers) {
    return {{"schema", "chronon.render-plan.v3"}, {"version", 3},
            {"job_id", id},
            {"canvas", {{"width", W}, {"height", H}, {"fps_num", 30},
                        {"fps_den", 1}, {"duration_frames", 1}}},
            {"layers", std::move(layers)},
            {"output", {{"path", id + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}}};
}

void add_player_controls(J& layers, const std::string& timestamp, double progress) {
    // These references are screenshots of a paused YouTube player; keep its
    // seek bar and compact bottom controls in the still as part of the frame.
    layers.push_back(rect("player_bottom_fade", 0, 958, W, 122, "#050607", 0.54));
    layers.push_back(rect("player_track", 18, 1004, 1884, 3, "#B8B8B8", 0.56));
    const double played = 1884.0 * progress;
    layers.push_back(rect("player_progress", 18, 1003, played, 5, "#F00032", 1.0));
    layers.push_back(ellipse("player_scrubber", 18 + played - 6, 999, 13, 13, "#F00032"));
    layers.push_back(text("player_play", "▶", 31, 1011, 42, 50, 31,
                          "assets/fonts/DejaVuSans.ttf", "#F5F5F5"));
    layers.push_back(text("player_volume", "◖))", 77, 1014, 68, 42, 22,
                          "assets/fonts/DejaVuSans.ttf", "#E9E9E9"));
    layers.push_back(text("player_timestamp", timestamp, 155, 1017, 190, 38, 20,
                          "assets/fonts/Inter-Regular.ttf", "#E8E8E8"));
    layers.push_back(text("player_right_icons", "▣   ⚙   CC", 1673, 1014, 218, 42, 22,
                          "assets/fonts/DejaVuSans.ttf", "#E9E9E9", "center"));
}

J nyt_excerpt() {
    J layers = J::array();
    auto paper = rect("paper", 0, 0, W, H, "#E9E8E6");
    paper["effects"] = J::array({J{{"type", "noise"}, {"amount", 0.012}, {"seed", 731}}});
    layers.push_back(std::move(paper));
    const auto serif = "assets/fonts/PlayfairDisplay.ttf";
    // Match the source's very tight zoom: every line is clipped by the frame.
    // The sentence text is taken from the visible excerpt in the reference.
    layers.push_back(text("line_1", "Federal authorities ruled that the church's activities were",
                          -244, 180, 2200, 116, 78, serif, "#77736F"));
    layers.push_back(rect("link_underline", 1137, 277, 714, 4, "#8191B1", 0.76));
    layers.push_back(rect("highlight_tax_status", 348, 376, 1215, 126, "#E9E600", 0.97));
    layers.push_back(text("line_2", "and it lost its tax-exempt status.",
                          -262, 367, 1870, 126, 79, serif, "#11100F"));
    layers.push_back(text("line_3", "ordered to pay those taxes. Years of",
                          -454, 545, 2130, 112, 77, serif, "#77736F"));
    layers.push_back(text("line_4", "appeals followed and lawsuits flooded the IRS.",
                          -262, 718, 2100, 112, 77, serif, "#77736F"));
    layers.push_back(text("line_5", "From 1973-1977, something was",
                          -453, 887, 1960, 112, 77, serif, "#77736F"));
    add_player_controls(layers, "17:50 / 1:41:29", 0.177);
    return make_plan("web_doc_reference_tax_status_v1", std::move(layers));
}

J crt_headline() {
    J layers = J::array();
    auto bg = rect("crt_black", 0, 0, W, H, "#080A0C");
    bg["effects"] = J::array({J{{"type", "noise"}, {"amount", 0.004}, {"seed", 1984}}});
    layers.push_back(std::move(bg));
    layers.push_back(rect("top_falloff", 0, 0, W, 520, "#101214", 0.34));
    auto archival = image("archival_frame", "assets/archival_refs_v2/al_capone_trio_source.png",
                          232, 823, 1440, 257);
    layers.push_back(std::move(archival));
    layers.push_back(rect("archival_dim", 232, 823, 1440, 257, "#080A0C", 0.20));
    const auto face = "assets/fonts/PlayfairDisplay-Bold.ttf";
    const std::vector<std::pair<std::string, double>> lines{
        {"GOVERNMENT TO DOUBLE", 135},
        {"ALCOHOL POISON CONTENT", 135},
        {"AND ALSO ADD BENZINE", 135}};
    const double ys[] = {-22, 136, 284};
    const double centers[] = {855, 927, 1004};
    const double ws[] = {1980, 1980, 1980};
    const double horizontal_scales[] = {.66, .60, .71};
    for (std::size_t i = 0; i < lines.size(); ++i) {
        auto main = text("headline_" + std::to_string(i), lines[i].first,
                         centers[i] - ws[i] / 2.0, ys[i], ws[i], 165, lines[i].second,
                         face, "#DDE4E8", "center");
        main["scale"] = {horizontal_scales[i], 1.0, 1.0};
        layers.push_back(std::move(main));
        auto yellow = text("chroma_yellow_" + std::to_string(i), lines[i].first,
                           centers[i] - 5 - ws[i] / 2.0, ys[i] - 1, ws[i], 165, lines[i].second,
                           face, "#D5D000", "center", 0.62);
        yellow["scale"] = {horizontal_scales[i], 1.0, 1.0};
        layers.push_back(std::move(yellow));
        auto cyan = text("chroma_cyan_" + std::to_string(i), lines[i].first,
                         centers[i] + 5 - ws[i] / 2.0, ys[i] + 1, ws[i], 165, lines[i].second,
                         face, "#67B9D4", "center", 0.42);
        cyan["scale"] = {horizontal_scales[i], 1.0, 1.0};
        layers.push_back(std::move(cyan));
    }
    layers.push_back(rect("thin_rule", 420, 542, 335, 3, "#AEB7B3", 0.62));
    auto subhead = text("subhead", "SMELL WARNS DRINKERS", 96, 574, 1000, 125,
                        82, "assets/fonts/Oswald.ttf", "#DDE4E8");
    subhead["scale"] = {.83, 1.0, 1.0};
    layers.push_back(std::move(subhead));
    layers.push_back(rect("tracking_mark", 910, 535, 4, 205, "#8ED8E9", 0.8));
    J diamond = rect("tracking_mark_head", 902, 526, 20, 20, "#DDECF0", 0.92, 45);
    layers.push_back(std::move(diamond));
    add_player_controls(layers, "2:54 / 1:41:29", 0.029);
    return make_plan("web_doc_reference_retro_headline_v1", std::move(layers));
}

J nyt_title() {
    J layers = J::array();
    auto paper = rect("paper", 0, 0, W, H, "#E9E8E6");
    paper["effects"] = J::array({J{{"type", "noise"}, {"amount", 0.009}, {"seed", 912}}});
    layers.push_back(std::move(paper));
    layers.push_back(rect("headline_marker_line_1", 236, 222, 1474, 101, "#E6E300", 0.97));
    layers.push_back(rect("headline_marker_line_2", 237, 323, 333, 99, "#E6E300", 0.97));
    layers.push_back(text("headline_1", "Rainmaking Is Used As Weapon", 43, 208, 1800, 132,
                          95, "assets/fonts/PlayfairDisplay-BlackItalic.ttf", "#10100F", "center"));
    layers.push_back(text("headline_2", "by U.S.", -498, 308, 1800, 132,
                          97, "assets/fonts/PlayfairDisplay-BlackItalic.ttf", "#10100F", "center"));
    layers.push_back(rect("section_rule", 236, 477, 1484, 2, "#D1D0CD", 0.78));
    // NYT controls shown in the captured page: gift pill, share and bookmark.
    layers.push_back(rect("share_pill_outline", 258, 598, 352, 75, "#F2F1EF", 0.24));
    layers.push_back(text("share_gift", "▣  Share full article", 278, 611, 320, 48,
                          25, "assets/fonts/Inter-SemiBold.ttf", "#353432"));
    layers.push_back(ellipse("share_circle", 651, 594, 84, 84, "#F4F3F1", 0.22));
    layers.push_back(text("share_arrow", "↗", 672, 608, 48, 50, 35,
                          "assets/fonts/DejaVuSans.ttf", "#353432", "center"));
    layers.push_back(ellipse("bookmark_circle", 775, 594, 84, 84, "#F4F3F1", 0.22));
    layers.push_back(text("bookmark_icon", "▯", 794, 605, 48, 52, 35,
                          "assets/fonts/DejaVuSans.ttf", "#353432", "center"));
    layers.push_back(text("byline", "By Seymour M. Hersh  Special to The New York Times",
                          -310, 774, 1800, 48, 27, "assets/fonts/Inter-SemiBold.ttf", "#454340"));
    layers.push_back(text("date", "July 3, 1972", -570, 825, 1800, 42,
                          24, "assets/fonts/Inter-Medium.ttf", "#716E68"));
    layers.push_back(rect("lower_rule", 236, 920, 1484, 1, "#D5D4D1", 0.82));
    add_player_controls(layers, "2:54 / 1:41:29", 0.029);
    return make_plan("web_doc_reference_rainmaking_headline_v1", std::move(layers));
}

J doc_video_highlight() {
    J layers = J::array();
    layers.push_back(image("soft_documentary_plate", "assets/images/investigative_journalist_blurred_bg.png",
                           0, 0, W, H));
    auto warm_tone = rect("warm_screen_tone", 0, 0, W, H, "#80685B", 0.24);
    warm_tone["effects"] = J::array({J{{"type", "vignette"}, {"radius", 0.67},
                                       {"softness", 0.62}, {"amount", 0.62}}});
    layers.push_back(std::move(warm_tone));
    layers.push_back(text("line_1_prefix", "Records later revealed that", -600, 430, 880, 75,
                          48, "assets/fonts/Inter-Regular.ttf", "#F1EEE9", "center"));
    layers.push_back(text("line_1_suffix", "before", 1300, 430, 910, 75,
                          48, "assets/fonts/Inter-Regular.ttf", "#F1EEE9", "center"));
    layers.push_back(rect("highlight_pinto", 133, 453, 1554, 56, "#8F7313", 0.78));
    layers.push_back(text("highlighted_claim", "Ford secretly crash-tested the Pinto more than forty times",
                          -5, 442, 1800, 74, 55, "assets/fonts/Inter-Regular.ttf", "#F1D923", "center"));
    layers.push_back(text("line_2", "the fuel tank ruptured in every test performed at speeds over twenty-five miles per hour.",
                          -169, 533, 2240, 74, 47, "assets/fonts/Inter-Regular.ttf", "#EEEAE5"));
    add_player_controls(layers, "9:44 / 1:41:29", 0.096);
    return make_plan("web_doc_reference_pinto_highlight_v1", std::move(layers));
}

} // namespace

std::vector<nlohmann::json> buildDocumentaryReferenceStillPlans() {
    return {nyt_excerpt(), crt_headline(), nyt_title(), doc_video_highlight()};
}

} // namespace chronontemplate::web
