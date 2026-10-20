#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

using Json = nlohmann::json;
namespace fs = std::filesystem;

namespace {
constexpr int kWidth = 1920;
constexpr int kHeight = 1080;
constexpr int kFrames = 240;

Json layerBase(const std::string& id, const std::string& type, float x, float y,
               float width, float height, bool in3d = true) {
    return {{"id", id}, {"type", type}, {"enable_3d", in3d},
            {"size", {width, height}}, {"position", {x, kHeight - y, 0.0}},
            {"start_frame", 0}, {"duration_frames", kFrames}};
}

Json rect(const std::string& id, float x, float y, float width, float height,
          const std::string& color, float alpha = 1.0f) {
    Json layer = layerBase(id, "shape", x + width * .5f, y + height * .5f,
                           width, height);
    const unsigned value = static_cast<unsigned>(std::stoul(color.substr(1), nullptr, 16));
    layer["shape"] = {{"type", "rect"},
                      {"fill", {((value >> 16) & 255) / 255.0,
                                ((value >> 8) & 255) / 255.0,
                                (value & 255) / 255.0, alpha}}};
    return layer;
}

Json text(const std::string& id, const std::string& value, float centerY,
          float fontSize, const std::string& color, bool bold, bool blurred) {
    Json layer = layerBase(id, "text", 960.0f, centerY, 1740.0f, 70.0f);
    layer["text"] = value;
    layer["style"] = {{"font", bold ? "assets/fonts/PlayfairDisplay-Bold.ttf"
                                      : "assets/fonts/PlayfairDisplay.ttf"},
                      {"font_size", fontSize}, {"fill", color}};
    if (blurred) {
        const std::string animatorId = id + "_selective_blur";
        layer["text_animators"] = Json::array({{
            {"id", animatorId},
            {"selectors", Json::array({{
                {"id", animatorId}, {"unit", "character"}, {"shape", "square"},
                {"order", "forward"}, {"combine", "replace"}, {"exclude_spaces", false},
                {"start", {{"easing", "linear"}, {"keyframes", Json::array({{{"frame", 0}, {"value", 0.0}}})}}},
                {"end", {{"easing", "linear"}, {"keyframes", Json::array({{{"frame", 0}, {"value", 100.0}}})}}}
            }})},
            {"properties", Json::array({{{"property", "blur"}, {"easing", "linear"},
                {"keyframes", Json::array({{{"frame", 0}, {"value", 5.0}},
                                            {{"frame", kFrames - 1}, {"value", 5.0}}})}}})}
        }});
    }
    return layer;
}

Json makePlan() {
    Json layers = Json::array();
    layers.push_back({{"id", "paper_background"}, {"type", "color"},
                      {"color", {0.91, 0.91, 0.90, 1.0}}, {"size", {kWidth, kHeight}},
                      {"screen_space", true}, {"start_frame", 0}, {"duration_frames", kFrames}});

    // Context above the focal paragraph. Each row is an independently blurred native text layer.
    const char* top[] = {
        "Synthetic cannabis products are sold under a variety of names,",
        "including Spice, K2, Black Mamba, Skunk, Moon Rocks, and JWH-018,",
        "with new compounds appearing faster than their effects can be studied.",
        "Many formulas are chemically distinct, even when packaging looks familiar.",
        "That makes it difficult for users, clinicians, and researchers to identify them."
    };
    const float topY[] = {190.0f, 246.0f, 302.0f, 358.0f, 414.0f};
    for (int i = 0; i < 5; ++i)
        layers.push_back(text("context_above_" + std::to_string(i), top[i],
                              topY[i], 36.0f, "#686868", false, true));

    // Three continuous marker strokes sit behind the exact three focal text lines.
    for (Json marker : {
             rect("marker_line_1", 367.0f, 445.0f, 1175.0f, 48.0f, "#F0E900", .42f),
             rect("marker_line_2", 299.0f, 497.0f, 1322.0f, 48.0f, "#F0E900", .42f),
             rect("marker_line_3", 706.0f, 549.0f, 508.0f, 48.0f, "#F0E900", .42f)}) {
        marker["position"][2] = 8.0;
        layers.push_back(std::move(marker));
    }
    layers.push_back(text("focus_line_1",
        "Synthetic cannabis, unlike pot, however, can cause a huge variety of", 469.0f,
        39.0f, "#202020", false, false));
    layers.push_back(text("focus_line_2",
        "symptoms, which can be severe: Agitation, vomiting, hallucination, paranoia,", 521.0f,
        39.0f, "#202020", false, false));
    layers.push_back(text("focus_line_3", "tremor, seizure, tachycardia,", 573.0f,
        39.0f, "#202020", false, false));

    // The continuation and nearby rows are again out of focus, like the source frame.
    const char* bottom[] = {
        "hypokalemia, chest pain, cardiac problems, stroke, kidney damage, acute",
        "psychosis, brain damage, and death.",
        "Researchers continue to study the risks and long-term effects of these substances.",
        "The chemical ingredients can change from batch to batch and from brand to brand.",
        "Public health teams track new reports to understand the scope of the problem."
    };
    const float bottomY[] = {646.0f, 702.0f, 758.0f, 814.0f, 870.0f};
    for (int i = 0; i < 5; ++i)
        layers.push_back(text("context_below_" + std::to_string(i), bottom[i],
                              bottomY[i], 36.0f, "#686868", false, true));

    return {{"schema", "chronon.render-plan.v3"}, {"version", 3},
            {"job_id", "synthetic_cannabis_native_evidence_focus_v2"},
            {"canvas", {{"width", kWidth}, {"height", kHeight}, {"fps_num", 30},
                        {"fps_den", 1}, {"duration_frames", kFrames}}},
            {"layers", std::move(layers)},
            {"camera", {{"type", "perspective"}, {"position", {0, 0, -1320}},
                         {"rotation_deg", {0, 5.4, 0}}, {"fov_deg", 50},
                         {"near", 1}, {"far", 5000}}},
            {"camera_animation", {{"tracks", Json::array({
                {{"property", "camera_position_z"}, {"easing", "in_out_cubic"},
                 {"keyframes", Json::array({{{"frame", 0}, {"value", -1320.0}},
                                             {{"frame", 239}, {"value", -1290.0}}})}},
                {{"property", "camera_rotation_y"}, {"easing", "in_out_cubic"},
                 {"keyframes", Json::array({{{"frame", 0}, {"value", 4.8}},
                                             {{"frame", 239}, {"value", 6.5}}})}}
            })}}},
            {"output", {{"path", "Synthetic_Cannabis_Evidence_Focus.mp4"},
                        {"format", "mp4"}, {"codec", "h264"}}}};
}
}

int main(int argc, char** argv) try {
    if (argc != 2 && argc != 3) {
        std::cerr << "usage: emit_synthetic_cannabis_native <output-plan.json> [--preview]\n";
        return 2;
    }
    Json plan = makePlan();
    const bool preview = argc == 3 && std::string(argv[2]) == "--preview";
    if (argc == 3 && !preview) throw std::runtime_error("unknown option: " + std::string(argv[2]));
    if (preview) {
        plan["job_id"] = "synthetic_cannabis_native_evidence_focus_preview";
        plan["canvas"]["duration_frames"] = 1;
        plan.erase("camera_animation");
        for (auto& layer : plan["layers"]) {
            layer["duration_frames"] = 1;
            if (!layer.contains("text_animators")) continue;
            for (auto& animator : layer["text_animators"])
                for (auto& property : animator["properties"]) {
                    auto first = property["keyframes"][0];
                    first["frame"] = 0;
                    property["keyframes"] = Json::array({first});
                }
        }
        plan["output"]["path"] = "Synthetic_Cannabis_Evidence_Focus.preview.mp4";
    }
    const fs::path output = fs::absolute(argv[1]);
    fs::create_directories(output.parent_path());
    std::ofstream file(output);
    file << plan.dump(2) << '\n';
    if (!file) throw std::runtime_error("failed to write plan: " + output.string());
    std::cout << output << '\n';
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
