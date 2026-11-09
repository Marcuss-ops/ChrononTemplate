// Emits one 1920x1080 archival triptych RenderPlan with three independent
// photo layers, separated framing, and subtle per-layer motion.
#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using json = nlohmann::ordered_json;
namespace fs = std::filesystem;

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_shutter_lifetime_v1 <workspace-root>\n";
        return 2;
    }
    constexpr int width = 1920, height = 1080, frames = 150;
    const fs::path root(argv[1]);
    const fs::path out = root / "ChrononTemplate/examples/shutter_lifetime_v1/plans";
    fs::create_directories(out);

    struct Card { const char* id; int x; int y; int dx; int dy; };
    const std::vector<Card> cards{{"island", 120, 320, 5, -3},
                                  {"radio", 720, 306, -3, 4},
                                  {"corridor", 1320, 320, 4, -3}};
    json layers = json::array({{
        {"id", "paper_background"}, {"type", "color"},
        {"color", {0.47, 0.45, 0.43, 1.0}}, {"size", {width, height}},
        {"screen_space", true}, {"start_frame", 0}, {"duration_frames", frames}
    }});
    for (const auto& card : cards) {
        layers.push_back({
            {"id", std::string("photo_") + card.id}, {"type", "image"},
            {"asset", std::string("ChrononTemplate/examples/shutter_lifetime_v1/assets/card_") + card.id + ".png"},
            {"size", {480, 320}}, {"position", {card.x, card.y}},
            {"start_frame", 0}, {"duration_frames", frames},
            {"animation", {{"tracks", json::array({{
                {"property", "position"}, {"easing", "linear"},
                {"keyframes", json::array({
                    {{"frame", 0}, {"value", {card.x, card.y}}},
                    {{"frame", frames - 1}, {"value", {card.x + card.dx, card.y + card.dy}}}
                })}
            }})}}
        }});
    }
    const json plan = {
        {"schema", "chronon.render-plan.v2"}, {"version", 2},
        {"job_id", "chronons_archival_triptych_shutter_focus"},
        {"canvas", {{"width", width}, {"height", height}, {"fps_num", 30},
                    {"fps_den", 1}, {"duration_frames", frames}}},
        {"layers", std::move(layers)},
        {"output", {{"path", "chronons_archival_triptych_shutter_focus.mp4"},
                    {"format", "mp4"}, {"codec", "h264"}}}
    };
    std::ofstream file(out / "chronons_archival_triptych_shutter_focus.plan.json");
    if (!file) {
        std::cerr << "cannot write shutter-focus RenderPlan\n";
        return 1;
    }
    file << plan.dump(2) << '\n';
    std::cout << "Emitted one separated-photo triptych plan under " << out << '\n';
    return 0;
}
