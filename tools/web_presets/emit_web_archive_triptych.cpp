// Emit the first ChrononTemplate web archive still as a native RenderPlan V3.
#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;
using Json = nlohmann::json;

namespace {
constexpr int kWidth = 1920;
constexpr int kHeight = 1080;
constexpr int kFrames = 1;

Json rgba(const std::string& color, double alpha = 1.0) {
    const auto rgb = std::stoul(color.substr(1), nullptr, 16);
    return {((rgb >> 16) & 255) / 255.0, ((rgb >> 8) & 255) / 255.0,
            (rgb & 255) / 255.0, alpha};
}

Json rect(const std::string& id, double x, double y, double width, double height,
          const std::string& color, double alpha = 1.0) {
    return {{"id", id}, {"type", "shape"}, {"enable_3d", true},
            {"position", {x + width * .5, kHeight - (y + height * .5), 0.0}},
            {"size", {width, height}}, {"start_frame", 0},
            {"duration_frames", kFrames},
            {"shape", {{"type", "rect"}, {"fill", rgba(color, alpha)}}}};
}

Json text(const std::string& id, const std::string& value, double x, double y,
          double width, double height, double fontSize, const std::string& font,
          const std::string& color, const std::string& align = "left") {
    return {{"id", id}, {"type", "text"}, {"enable_3d", true}, {"text", value},
            {"position", {x + width * .5, kHeight - (y + height * .5), 0.0}},
            {"size", {width, height}}, {"start_frame", 0},
            {"duration_frames", kFrames},
            {"style", {{"font", font}, {"font_size", fontSize},
                        {"fill", color}, {"fit_mode", "none"},
                        {"text_align", align}}}};
}

Json image(const std::string& id, const std::string& asset, double x, double y,
           double width, double height) {
    return {{"id", id}, {"type", "image"}, {"enable_3d", true}, {"screen_space", true},
            {"asset", asset}, {"position", {x + width * .5, y + height * .5, 0.0}},
            {"size", {width, height}}, {"fit", "cover"},
            {"start_frame", 0}, {"duration_frames", kFrames}};
}

Json makePlan() {
    Json layers = Json::array();
    layers.push_back({{"id", "archive_canvas"}, {"type", "color"},
                      {"color", rgba("#E5E2DC")}, {"size", {kWidth, kHeight}},
                      {"screen_space", true}, {"start_frame", 0},
                      {"duration_frames", kFrames}});
    layers.push_back(rect("paper_shadow", 100, 68, 1720, 960, "#D3CFC8"));
    layers.push_back(rect("archive_paper", 100, 60, 1720, 960, "#EBE9E4"));

    layers.push_back(text("archive_label", "ARCHIVE IMAGE", 178, 119, 250, 26,
                          12, "assets/fonts/Inter-Bold.ttf", "#5B5751"));
    layers.push_back(rect("archive_label_rule", 178, 148, 122, 1, "#8B857C"));
    layers.push_back(text("archive_subject", "Bednyaks, Serednyaks, and Kulaks",
                          178, 156, 470, 24, 13, "assets/fonts/Inter-Bold.ttf", "#625D56"));

    // Full phrase receives one continuous marker underline, rendered behind the text.
    layers.push_back(rect("headline_marker_underline", 426, 281, 954, 13, "#D5B54B"));
    layers.push_back(text("archive_headline", "The stories behind the frames we keep",
                          178, 226, 1450, 80, 54,
                          "assets/fonts/PlayfairDisplay-Bold.ttf", "#282722"));
    layers.push_back(rect("headline_divider", 178, 328, 1564, 1, "#C8C3BA"));

    constexpr double x1 = 248, x2 = 737, x3 = 1225;
    constexpr double cardWidth = 447, cardHeight = 326, cardTop = 392;
    layers.push_back(rect("photo_shadow_1", x1, cardTop + 12, cardWidth, cardHeight, "#D4D0C8"));
    layers.push_back(rect("photo_shadow_2", x2, cardTop + 12, cardWidth, cardHeight, "#D4D0C8"));
    layers.push_back(rect("photo_shadow_3", x3, cardTop + 12, cardWidth, cardHeight, "#D4D0C8"));
    layers.push_back(image("archive_bednyaks", "assets/web_archive_v1/bednyaks.png",
                           x1, cardTop, cardWidth, cardHeight));
    layers.push_back(image("archive_serednyaks", "assets/web_archive_v1/serednyaks.png",
                           x2, cardTop, cardWidth, cardHeight));
    layers.push_back(image("archive_kulaks", "assets/web_archive_v1/kulaks.png",
                           x3, cardTop, cardWidth, cardHeight));
    layers.push_back(text("photo_label_01", "Bednyaks", x1, 725, cardWidth, 35, 22,
                          "assets/fonts/PlayfairDisplay.ttf", "#454039", "center"));
    layers.push_back(text("photo_label_02", "Serednyaks", x2, 725, cardWidth, 35, 22,
                          "assets/fonts/PlayfairDisplay.ttf", "#454039", "center"));
    layers.push_back(text("photo_label_03", "Kulaks", x3, 725, cardWidth, 35, 22,
                          "assets/fonts/PlayfairDisplay.ttf", "#454039", "center"));
    layers.push_back(rect("archive_footer_rule", 178, 958, 1564, 1, "#C7C1B7"));
    layers.push_back(text("archive_footer_left", "CHRONON ARCHIVE  ·  FIELD NOTES",
                          178, 974, 650, 18, 10, "assets/fonts/Inter-Regular.ttf", "#777168"));
    layers.push_back(text("archive_footer_right", "COLLECTION 01  /  PHOTOGRAPHIC RECORD",
                          1120, 974, 622, 18, 10, "assets/fonts/Inter-Regular.ttf", "#777168", "right"));

    return {{"schema", "chronon.render-plan.v3"}, {"version", 3},
            {"job_id", "web_archive_triptych_native_v1"},
            {"canvas", {{"width", kWidth}, {"height", kHeight},
                        {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", kFrames}}},
            {"camera", {{"type", "perspective"}, {"position", {0, 0, -1158}},
                        {"rotation_deg", {0, 0, 0}}, {"fov_deg", 50},
                        {"near", 1}, {"far", 5000}}},
            {"layers", std::move(layers)},
            {"output", {{"path", "web_archive_triptych.mp4"}, {"format", "mp4"},
                        {"codec", "h264"}}}};
}
} // namespace

int main(int argc, char** argv) try {
    if (argc != 2) throw std::runtime_error("usage: chronontemplate_emit_web_archive_triptych <plan.json>");
    const fs::path output = fs::absolute(argv[1]);
    fs::create_directories(output.parent_path());
    std::ofstream file(output);
    file << makePlan().dump(2) << '\n';
    if (!file) throw std::runtime_error("failed to write plan: " + output.string());
    std::cout << output << '\n';
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
