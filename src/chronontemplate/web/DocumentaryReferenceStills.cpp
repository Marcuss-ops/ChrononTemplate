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
    return {{"id", id}, {"type", "image"}, {"screen_space", true}, {"asset", asset},
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

J nyt_excerpt() {
    J layers = J::array();
    layers.push_back(rect("paper", 0, 0, W, H, "#F5F4F1"));
    layers.push_back(rect("paper_light", 70, 0, 1780, H, "#FBFAF8", 0.56));
    const auto serif = "assets/fonts/PlayfairDisplay.ttf";
    const auto ink = "#66635F";
    layers.push_back(text("line_1", "Federal authorities ruled that the church's activities were",
                          32, 188, 1840, 94, 61, serif, ink));
    layers.push_back(text("line_2", "illegal, and it lost its tax-exempt status.",
                          168, 286, 1590, 94, 64, serif, "#373532"));
    // A tight marker behind the final clause mirrors the yellow sentence cue.
    layers.insert(layers.end() - 1, rect("highlight_tax_status", 742, 298, 1000, 78,
                                         "#F2E900", 0.88));
    layers.push_back(text("line_3", "The organization was ordered to pay those taxes. Years of",
                          26, 390, 1800, 93, 60, serif, ink));
    layers.push_back(text("line_4", "appeals followed, and new lawsuits reached the IRS.",
                          90, 491, 1725, 92, 60, serif, ink));
    layers.push_back(text("line_5", "The fight stretched from 1973 to 1977, as the case moved",
                          35, 592, 1810, 92, 60, serif, ink));
    layers.push_back(text("line_6", "through the courts and back again.",
                          205, 693, 1500, 92, 60, serif, ink));
    layers.push_back(rect("bottom_crop", 0, 1036, W, 44, "#F5F4F1", 0.16));
    return make_plan("web_doc_reference_tax_status_v1", std::move(layers));
}

J crt_headline() {
    J layers = J::array();
    auto bg = rect("crt_black", 0, 0, W, H, "#080A0C");
    bg["effects"] = J::array({J{{"type", "noise"}, {"amount", 0.028}, {"seed", 1984}}});
    layers.push_back(std::move(bg));
    layers.push_back(rect("top_falloff", 0, 0, W, 520, "#111419", 0.45));
    // Soft, low-contrast archival strip below the title, like the footage bed in the reference.
    layers.push_back(image("archival_frame", "assets/web_archive_v1/serednyaks.png", 0, 730, W, 350));
    layers.push_back(rect("archival_dim", 0, 730, W, 350, "#070A0D", 0.58));
    const auto face = "assets/fonts/Anton-Regular.ttf";
    const std::vector<std::pair<std::string, double>> lines{
        {"GOVERNMENT TO DOUBLE", 112},
        {"ALCOHOL POISON CONTENT", 106},
        {"AND ALSO ADD BENZINE", 108}};
    const double ys[] = {45, 174, 300};
    const double xs[] = {102, 115, 188};
    const double ws[] = {1716, 1690, 1550};
    for (std::size_t i = 0; i < lines.size(); ++i) {
        layers.push_back(text("chroma_red_" + std::to_string(i), lines[i].first,
                              xs[i] - 4, ys[i], ws[i], 126, lines[i].second,
                              face, "#E2D900", "center", 0.72));
        layers.push_back(text("chroma_blue_" + std::to_string(i), lines[i].first,
                              xs[i] + 4, ys[i], ws[i], 126, lines[i].second,
                              face, "#55C4E9", "center", 0.72));
        layers.push_back(text("headline_" + std::to_string(i), lines[i].first,
                              xs[i], ys[i], ws[i], 126, lines[i].second,
                              face, "#F2F0E7", "center"));
    }
    layers.push_back(rect("thin_rule", 405, 526, 340, 3, "#AEB7B3", 0.62));
    layers.push_back(text("subhead", "SMELL WARNS DRINKERS", 270, 570, 740, 84,
                          56, "assets/fonts/Oswald-Medium.ttf", "#E8E7DE"));
    layers.push_back(rect("tracking_mark", 1000, 544, 4, 180, "#8ED8E9", 0.8));
    J diamond = rect("tracking_mark_head", 991, 534, 20, 20, "#DDECF0", 0.92, 45);
    layers.push_back(std::move(diamond));
    for (int y = 11, i = 0; y < 1080; y += 8, ++i)
        layers.push_back(rect("raster_" + std::to_string(i), 0, y, W, 1,
                              i % 2 ? "#050708" : "#C1D9DD", i % 2 ? 0.17 : 0.025));
    return make_plan("web_doc_reference_retro_headline_v1", std::move(layers));
}

J nyt_title() {
    J layers = J::array();
    layers.push_back(rect("paper", 0, 0, W, H, "#FAF9F6"));
    layers.push_back(rect("paper_warm", 0, 0, W, H, "#F2EEE6", 0.21));
    layers.push_back(rect("headline_marker_line_1", 228, 220, 1450, 91, "#EFE600", 0.94));
    layers.push_back(rect("headline_marker_line_2", 230, 313, 380, 90, "#EFE600", 0.94));
    layers.push_back(text("headline_1", "Rainmaking Is Used As Weapon", 242, 211, 1540, 110,
                          79, "assets/fonts/PlayfairDisplay-BlackItalic.ttf", "#141311"));
    layers.push_back(text("headline_2", "by U.S.", 243, 303, 490, 111,
                          79, "assets/fonts/PlayfairDisplay-BlackItalic.ttf", "#141311"));
    layers.push_back(rect("section_rule", 228, 476, 1460, 2, "#D9D7D2", 0.9));
    layers.push_back(text("share", "▣  Share full article       ↗       ♧", 236, 504,
                          760, 42, 22, "assets/fonts/Inter-Medium.ttf", "#55534F"));
    layers.push_back(text("byline", "By Seymour M. Hersh  Special to The New York Times",
                          236, 611, 1250, 44, 26, "assets/fonts/Inter-SemiBold.ttf", "#44423E"));
    layers.push_back(text("date", "July 3, 1972", 236, 660, 630, 39,
                          23, "assets/fonts/Inter-Medium.ttf", "#716E68"));
    layers.push_back(rect("lower_rule", 228, 744, 1460, 1, "#E0DED9", 0.9));
    layers.push_back(rect("subtle_crop", 0, 0, 32, H, "#FAF9F6", 0.26));
    return make_plan("web_doc_reference_rainmaking_headline_v1", std::move(layers));
}

J doc_video_highlight() {
    J layers = J::array();
    layers.push_back(image("soft_documentary_plate", "assets/images/investigative_journalist_blurred_bg.png",
                           0, 0, W, H));
    layers.push_back(rect("dark_screen_tone", 0, 0, W, H, "#14100D", 0.48));
    layers.push_back(rect("warm_center_wash", 0, 300, W, 470, "#76523C", 0.12));
    layers.push_back(text("lead_in", "Records later revealed that", 130, 362, 1300, 74,
                          49, "assets/fonts/Inter-Regular.ttf", "#ECE9E1"));
    layers.push_back(rect("highlight_pinto", 128, 444, 1637, 73, "#C4AB00", 0.73));
    layers.push_back(text("highlighted_claim", "Ford secretly crash-tested the Pinto more than forty times",
                          139, 444, 1690, 77, 48, "assets/fonts/Inter-SemiBold.ttf", "#F5E342"));
    layers.push_back(text("body_1", "before the fuel tank ruptured in every test performed at speeds",
                          128, 546, 1740, 72, 43, "assets/fonts/Inter-Regular.ttf", "#E6E3DC"));
    layers.push_back(text("body_2", "over twenty-five miles per hour.", 128, 625, 1370, 72,
                          43, "assets/fonts/Inter-Regular.ttf", "#E6E3DC"));
    layers.push_back(text("body_3", "The findings changed the way the company handled the case.",
                          128, 741, 1680, 72, 39, "assets/fonts/Inter-Regular.ttf", "#D4D0C8", "left", 0.87));
    layers.push_back(rect("bottom_shadow", 0, 864, W, 216, "#070808", 0.22));
    return make_plan("web_doc_reference_pinto_highlight_v1", std::move(layers));
}

} // namespace

std::vector<nlohmann::json> buildDocumentaryReferenceStillPlans() {
    return {nyt_excerpt(), crt_headline(), nyt_title(), doc_video_highlight()};
}

} // namespace chronontemplate::web
