#include <nlohmann/json.hpp>
#include "chronontemplate/camera_roll/ResolvedCameraSamples.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <map>
#include <cstdio>

using J = nlohmann::json;
namespace fs = std::filesystem;

constexpr int W = 1920, H = 1080, N = 240;
constexpr double CARD_LAYOUT_SHIFT_X = 110.0;

std::string quote(const std::string& s) {
    std::string o = "'";
    for (char c : s) {
        if (c == '\'') o += "'\\''";
        else o += c;
    }
    return o + "'";
}

double width(const std::string& s, double fs, const std::string& font) {
    static std::map<std::string, double> cache;
    auto k = font + "\n" + std::to_string(fs) + "\n" + s;
    if (cache.count(k)) return cache[k];
    std::string cmd = "hb-shape --font-size=" + std::to_string(fs) +
                      " --output-format=json " + quote(font) + " " + quote(s) + " 2>/dev/null";
    FILE* p = popen(cmd.c_str(), "r");
    if (!p) throw std::runtime_error("hb-shape unavailable");
    std::string out;
    char b[4096];
    while (std::fgets(b, sizeof b, p)) out += b;
    if (pclose(p) != 0) throw std::runtime_error("text shaping failed");
    auto a = J::parse(out);
    double w = 0;
    for (auto& g : a) w += g.value("ax", 0.0);
    return cache[k] = w;
}

J rgb(std::string c, double a = 1) {
    auto v = std::stoul(c.substr(1), nullptr, 16);
    return {((v >> 16) & 255) / 255.0, ((v >> 8) & 255) / 255.0, (v & 255) / 255.0, a};
}

J track(const std::string& property, const J& keys, const std::string& easing = "out_cubic") {
    return {{"property", property}, {"easing", easing}, {"keyframes", keys}};
}

J fade(int appear, int finish) {
    return J{{"tracks", J::array({track("opacity", J::array({
        J{{"frame", 0}, {"value", 0.0}},
        J{{"frame", appear}, {"value", 0.0}},
        J{{"frame", finish}, {"value", 1.0}}}))})}};
}

J rect(std::string id, double x, double y, double w, double h, std::string c,
       double alpha = 1, double z = 0) {
    return {{"id", id}, {"type", "shape"},
            {"position", {x + w * .5 + CARD_LAYOUT_SHIFT_X, H - (y + h * .5), z}},
            {"size", {w, h}}, {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", N},
            {"shape", {{"type", "rect"}, {"fill", rgb(c, alpha)}}}};
}

J text(std::string id, std::string s, double xleft, double y, double fs, std::string font,
       std::string fill, double z = 8, int appear = -1, int finish = -1) {
    double w = width(s, fs, font);
    J l = {{"id", id}, {"type", "text"}, {"text", s},
           {"position", {xleft + w * .5 + CARD_LAYOUT_SHIFT_X, H - y, z}},
           {"size", {1900, fs * 1.8}}, {"enable_3d", true},
           {"start_frame", 0}, {"duration_frames", N},
           {"style", {{"font", font}, {"font_size", fs}, {"fill", fill}, {"fit_mode", "none"}}}};
    if (appear >= 0) l["animation"] = fade(appear, finish);
    return l;
}

J makePlan() {
    J a = J::array();

    // A single screen-space plate carries both the photograph and its dark
    // grade. Two stacked screen-space plates (photo + dim rect) made the
    // background alternate between them during the 3D yaw; a baked plate is
    // one composited layer and cannot flicker. Regenerate the plate from the
    // original photo with:
    //   ffmpeg -i dirk_nowitzki_2011.jpg -vf "scale=1920:1080:force_original_aspect_ratio=increase,
    //     crop=1920:1080,lutrgb=r='clip(round(val*0.36+4.48),0,255)':
    //     g='clip(round(val*0.36+10.24),0,255)':b='clip(round(val*0.36+17.92),0,255)'"
    //     dirk_nowitzki_2011_dim.jpg
    J photo = {{"id", "dirk_photo_background"}, {"type", "image"},
               {"asset", "assets/nba_rivalry/web/dirk_nowitzki_2011_dim.jpg"},
               {"position", {0, 0}}, {"size", {W, H}}, {"fit", "cover"},
               {"screen_space", true}, {"start_frame", 0}, {"duration_frames", N}};
    a.push_back(photo);

    J card = rect("article_card", 10, 185, 1900, 840, "#191A1C", 1, 0);
    card["animation"] = {{"tracks", J::array({
        track("scale_x", J::array({J{{"frame", 0}, {"value", .01}},
                                   J{{"frame", 39}, {"value", 1.0}}})),
        track("scale_y", J::array({J{{"frame", 0}, {"value", .02}},
                                   J{{"frame", 39}, {"value", 1.0}}}))})}};
    a.push_back(card);

    J hair = rect("card_hairline", 10, 185, 1900, 2, "#FFFFFF", .14, 2);
    hair["animation"] = fade(37, 43);
    a.push_back(hair);

    J band = rect("photo_credit_band", 10, 189, 1900, 88, "#141517", .97, 3);
    band["animation"] = fade(37, 43);
    a.push_back(band);

    a.push_back(text("photo_caption", "Mark Cuban yells during the game against the San Antonio Spurs in Game Six of the 2006 NBA Finals.",
                     145, 211, 22, "assets/fonts/Inter-Medium.ttf", "#C7C8CA", 8, 42, 52));
    a.push_back(text("source_caption", "Dallas won 113–111.  Mandatory Credit: Kevin Jairaj / USA TODAY Sports",
                     145, 256, 20, "assets/fonts/Inter-Regular.ttf", "#888A8D", 8, 45, 55));
    a.push_back(text("section_nba", "NBA", 145, 408, 29, "assets/fonts/Inter-Bold.ttf",
                     "#BFC1C4", 8, 57, 67));
    a.push_back(text("headline_line_1", "Report: Mark Cuban Hired Former FBI Agent to Investigate",
                     145, 500, 60, "assets/fonts/Oswald-Bold.ttf", "#F4F4F2", 8, 72, 84));
    a.push_back(text("headline_line_2", "NBA After 2006 Finals",
                     145, 582, 60, "assets/fonts/Oswald-Bold.ttf", "#F4F4F2", 8, 88, 100));
    a.push_back(text("author", "Grant Hughes", 145, 688, 29, "assets/fonts/Inter-Medium.ttf",
                     "#A0A1A3", 8, 111, 120));
    a.push_back(text("date", "May 19, 2014", 145, 738, 27, "assets/fonts/Inter-Regular.ttf",
                     "#898B8E", 8, 123, 132));
    a.push_back(text("share_x", "𝕏", 145, 816, 43, "assets/fonts/Inter-Regular.ttf",
                     "#E8E9EA", 8, 139, 148));
    a.push_back(text("share_f", "f", 258, 816, 43, "assets/fonts/Inter-Bold.ttf",
                     "#E8E9EA", 8, 144, 153));
    a.push_back(text("share_link", "↗", 365, 816, 43, "assets/fonts/Inter-Regular.ttf",
                     "#E8E9EA", 8, 149, 158));

    // Article deck under the share row: the card carried a headline but no
    // copy, so the lower third of the panel stayed empty.
    a.push_back(text("body_line_1", "The report said Cuban hired a former FBI agent to review the 2006 Finals.",
                     145, 884, 21, "assets/fonts/Inter-Regular.ttf", "#A9ABAE", 8, 162, 172));
    a.push_back(text("body_line_2", "League officials examined how the series was officiated and how the league responded.",
                     145, 916, 21, "assets/fonts/Inter-Regular.ttf", "#A9ABAE", 8, 174, 184));
    a.push_back(text("body_line_3", "The inquiry renewed debate about one of the most disputed Finals in NBA history.",
                     145, 948, 21, "assets/fonts/Inter-Regular.ttf", "#A9ABAE", 8, 186, 196));

    const J camera = {{"type", "perspective"}, {"position", {0, 0, -1320}},
                      {"rotation_deg", {0, 2.5, 0}}, {"fov_deg", 50}, {"near", 1}, {"far", 5000}};
    const J cameraChannels = J::array({
        {{"channel", "position_z"}, {"easing", "in_out_cubic"}, {"keyframes", J::array({
            J{{"frame", 0}, {"value", -1320.0}},
            J{{"frame", 145}, {"value", -1320.0}},
            J{{"frame", 239}, {"value", -1320.0}}})}},
        {{"channel", "rotation_y"}, {"easing", "in_out_cubic"}, {"keyframes", J::array({
            J{{"frame", 0}, {"value", 2.5}},
            J{{"frame", 145}, {"value", 2.5}},
            J{{"frame", 239}, {"value", 8.0}}})}}});

    J plan = {{"schema", "chronon.render-plan.v3"}, {"version", 3},
              {"job_id", "dark_nba_article_card_animated_v3"},
              {"canvas", {{"width", W}, {"height", H}, {"fps_num", 30}, {"fps_den", 1},
                          {"duration_frames", N}}},
              {"layers", a}, {"camera", camera},
              {"output", {{"path", "Dark_NBA_Article_Card.mp4"}, {"format", "mp4"}, {"codec", "h264"}}}};
    chronontemplate::camera_roll::attachResolvedCameraSamples(plan, camera, cameraChannels, 30.f, N);
    return plan;
}

int main(int argc, char** argv) {
    try {
        if (argc != 2) return 2;
        J p = makePlan();
        fs::path out = fs::absolute(argv[1]);
        fs::create_directories(out.parent_path());
        std::ofstream f(out);
        f << p.dump(2) << '\n';
        if (!f) throw std::runtime_error("failed to write plan");
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
