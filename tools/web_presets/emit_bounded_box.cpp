// Emit the screen-space RenderPlan example for ChrononTemplate's bounded box.
#include "chronontemplate/elements/WebElements.hpp"

#include <filesystem>
#include <array>
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>
#include <stdexcept>

using chronontemplate::elements::BoundedBoxSpec;
using nlohmann::json;

namespace {
constexpr int kWidth = 1920;
constexpr int kHeight = 1080;
constexpr int kFps = 30;

json track(const char* property, std::initializer_list<std::pair<int, float>> keys) {
    json keyframes = json::array();
    for (const auto& [frame, value] : keys)
        keyframes.push_back({{"frame", frame}, {"value", value}});
    return {{"property", property}, {"easing", "out_cubic"}, {"keyframes", keyframes}};
}

json rectangle(const std::string& id, const BoundedBoxSpec& spec,
               int width, int height, const std::array<float, 4>& fill,
               bool animate) {
    json layer = {
        {"id", id}, {"type", "shape"}, {"size", {width, height}},
        {"position", {kWidth / 2, kHeight / 2}}, {"start_frame", 0},
        {"duration_frames", spec.durationFrames},
        {"shape", {{"type", "rect"}, {"fill", fill}}}
    };
    if (animate) {
        layer["animation"] = {{"tracks", {
            track("opacity", {{0, 0.f}, {90, 1.f}, {spec.durationFrames - 1, 1.f}}),
            track("scale_x", {{0, 0.02f}, {90, 1.f}, {spec.durationFrames - 1, 1.f}})
        }}};
    }
    return layer;
}
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_emit_bounded_box <output.plan.json>\n";
        return 2;
    }

    try {
        BoundedBoxSpec spec;
        spec.text = "Il tuo testo qui";
        spec.font = "tests/fixtures/Inter-Bold.ttf";
        spec.width = 920.f;
        spec.height = 300.f;
        spec.fontSize = 62.f;
        spec.durationFrames = 300;

        const auto output = std::filesystem::absolute(argv[1]);
        std::filesystem::create_directories(output.parent_path());
        const json plan = {
            {"schema", "chronon.render-plan.v3"}, {"version", 3},
            {"job_id", "web_bounded_box"},
            {"canvas", {{"width", kWidth}, {"height", kHeight},
                         {"fps_num", kFps}, {"fps_den", 1},
                         {"duration_frames", spec.durationFrames}}},
            {"layers", json::array({
                rectangle("background", spec, kWidth, kHeight,
                          {23.f / 255.f, 25.f / 255.f, 31.f / 255.f, 1.f}, false),
                rectangle("bounded_box", spec, static_cast<int>(spec.width),
                          static_cast<int>(spec.height), {1.f, 1.f, 1.f, 1.f}, true),
                {{"id", "bounded_box_text"}, {"type", "text"}, {"text", spec.text},
                 {"size", {static_cast<int>(spec.width), 160}},
                 {"position", {kWidth / 2, kHeight / 2}}, {"start_frame", 0},
                 {"duration_frames", spec.durationFrames},
                 {"style", {{"font", spec.font}, {"font_size", spec.fontSize},
                             {"fill", spec.textColor}}},
                 {"animation", {{"tracks", {
                     track("opacity", {{0, 0.f}, {12, 0.f}, {90, 1.f},
                                        {spec.durationFrames - 1, 1.f}}),
                     track("scale", {{0, 0.96f}, {90, 1.f},
                                      {spec.durationFrames - 1, 1.f}})
                 }}}}}
            })},
            {"output", {{"path", "web_bounded_box_1080p.mp4"},
                         {"format", "mp4"}, {"codec", "h264"}}}
        };

        std::ofstream file(output, std::ios::binary | std::ios::trunc);
        if (!file || !(file << plan.dump(2)))
            throw std::runtime_error("failed to write plan: " + output.string());
        std::cout << "Wrote " << output << " with web.bounded_box; 10 seconds at 30 fps\n";
    } catch (const std::exception& error) {
        std::cerr << "emit_bounded_box: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
