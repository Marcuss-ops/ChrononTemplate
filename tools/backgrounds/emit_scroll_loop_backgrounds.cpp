// ChrononTemplate — horizontal seamless-loop background emitter.
// For every tile name given, writes a plan with two copies of the 1920x1080 tile scrolling left by exactly one
// tile width over the loop duration (linear), so the last frame equals the first -> perfect loop.
// Usage: chronontemplate_emit_scroll_loop_backgrounds <out-dir> <seconds> <tile-name>...
//   strip asset expected at assets/images/chbgw_<tile-name>.png (3840x1080 = tile twice)
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    using json = nlohmann::ordered_json;
    if (argc < 4) { std::cerr << "usage: emit_scroll_loop_backgrounds <out-dir> <seconds> <tile>...\n"; return 2; }
    const std::filesystem::path out = argv[1];
    const int fps = 30, W = 1920, H = 1080, frames = static_cast<int>(std::stod(argv[2]) * fps);
    std::filesystem::create_directories(out);
    for (int i = 3; i < argc; ++i) {
        const std::string name = argv[i];
        // One 2-tile-wide strip (assets/images/chbgw_<name>.png, the tile repeated twice) scrolls left by one tile.
        json track = {{"property", "position_x"},
                      {"keyframes", json::array({{{"frame", 0}, {"value", 0}}, {{"frame", frames}, {"value", -W}}})},
                      {"easing", "linear"}};
        json layers = json::array({{{"id", "strip"}, {"type", "image"}, {"asset", "assets/images/chbgw_" + name + ".png"},
                                    {"size", {2 * W, H}}, {"position", {0, 0}}, {"start_frame", 0},
                                    {"duration_frames", frames}, {"animation", {{"tracks", json::array({track})}}}}});
        json plan = {{"schema", "chronon.render-plan.v2"}, {"version", 2}, {"job_id", "loop_" + name},
                     {"canvas", {{"width", W}, {"height", H}, {"fps_num", fps}, {"fps_den", 1}, {"duration_frames", frames}}},
                     {"layers", layers}, {"output", {{"path", "loop_" + name + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}}};
        std::ofstream(out / ("loop_" + name + ".plan.json")) << plan.dump(1);
        std::cout << "emitted loop_" << name << "\n";
    }
}
