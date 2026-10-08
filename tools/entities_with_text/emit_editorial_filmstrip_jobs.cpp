#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using Json = nlohmann::ordered_json;
namespace fs = std::filesystem;

struct Keyframe {
    int frame;
    Json value;
};

struct Track {
    std::string property;
    std::string easing;
    std::vector<Keyframe> keyframes;
};

Json serializeTracks(const std::vector<Track>& tracks) {
    Json arr = Json::array();
    for (const auto& t : tracks) {
        Json kfs = Json::array();
        for (const auto& k : t.keyframes) {
            kfs.push_back({{"frame", k.frame}, {"value", k.value}});
        }
        arr.push_back({
            {"property", t.property},
            {"easing", t.easing},
            {"keyframes", kfs}
        });
    }
    return arr;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: emit_editorial_filmstrip_jobs <out_dir>\n";
        return 1;
    }

    fs::path outDir = argv[1];
    fs::create_directories(outDir);

    const std::string fontPath = "ChrononTemplate/out/apple_spatial_entity_pack/assets/Montserrat-Bold.ttf";
    const std::string id = "modern_entity_06_editorial_filmstrip_jobs";

    // Filmstrip lateral slide-in animation (like the reference, moving slightly horizontally and settling)
    std::vector<Track> filmstripTracks = {
        {"position_x", "out_cubic", {{0, 930.0f}, {48, 860.0f}, {89, 856.0f}}},
        {"position_z", "out_cubic", {{0, 80.0f}, {48, 0.0f}, {89, 0.0f}}},
        {"opacity", "out_cubic", {{0, 0.0f}, {18, 1.0f}, {89, 1.0f}}}
    };

    std::vector<Track> nextSlideTracks = {
        {"position_x", "out_cubic", {{0, 2250.0f}, {48, 2180.0f}, {89, 2176.0f}}},
        {"opacity", "out_cubic", {{0, 0.0f}, {18, 1.0f}, {89, 1.0f}}}
    };

    // Text "STEVE JOBS" below, aligned with vertical bar indicator (like "FILOSOFIA" in reference)
    std::vector<Track> textTracks = {
        {"position_x", "out_cubic", {{16, 260.0f}, {48, 290.0f}, {89, 290.0f}}},
        {"opacity", "out_cubic", {{16, 0.0f}, {34, 1.0f}, {89, 1.0f}}}
    };

    std::vector<Track> badgeTracks = {
        {"opacity", "out_cubic", {{10, 0.0f}, {30, 1.0f}, {89, 1.0f}}}
    };

    Json plan = {
        {"schema", "chronon.render-plan.v2"},
        {"version", 2},
        {"job_id", id},
        {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
        {"layers", Json::array({
            // 1. Warm cream paper background
            {
                {"id", "editorial_bg"},
                {"type", "image"},
                {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/editorial_filmstrip_cream_bg.png"},
                {"position", {960.0, 540.0}},
                {"size", {1920.0, 1080.0}},
                {"fit", "cover"},
                {"start_frame", 0},
                {"duration_frames", 90}
            },
            // 2. Editorial corner badge top-left: "CHRONON / EDITORIAL"
            {
                {"id", "corner_kicker"},
                {"type", "text"},
                {"text", "CHRONON TIPS  |  EDITORIAL"},
                {"size", {600.0, 50.0}},
                {"position", {340.0, 85.0}},
                {"style", {{"font", fontPath}, {"font_size", 22.0}, {"fill", "#A59E92"}}},
                {"start_frame", 0},
                {"duration_frames", 90},
                {"animation", {{"tracks", serializeTracks(badgeTracks)}}}
            },
            // 3. Filmstrip Next Slide on the right
            {
                {"id", "filmstrip_next"},
                {"type", "image"},
                {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/filmstrip_next_slide.png"},
                {"position", {2180.0, 450.0}},
                {"size", {1320.0, 800.0}},
                {"fit", "contain"},
                {"enable_3d", true},
                {"start_frame", 0},
                {"duration_frames", 90},
                {"animation", {{"tracks", serializeTracks(nextSlideTracks)}}}
            },
            // 4. Main Filmstrip Frame: Steve Jobs (B&W Archival Photo)
            {
                {"id", "filmstrip_jobs"},
                {"type", "image"},
                {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/filmstrip_frame_steve_jobs.png"},
                {"position", {860.0, 450.0}},
                {"size", {1320.0, 800.0}},
                {"fit", "contain"},
                {"enable_3d", true},
                {"start_frame", 0},
                {"duration_frames", 90},
                {"animation", {{"tracks", serializeTracks(filmstripTracks)}}}
            },
            // 5. Vertical accent line on the bottom-left text (like in reference)
            {
                {"id", "text_vertical_line"},
                {"type", "color"},
                {"color", {0.10, 0.11, 0.12, 1.0}},
                {"position", {208.0, 882.0}},
                {"size", {6.0, 82.0}},
                {"start_frame", 0},
                {"duration_frames", 90},
                {"animation", {{"tracks", serializeTracks(textTracks)}}}
            },
            // 6. Bold typography: "STEVE JOBS"
            {
                {"id", "title_text"},
                {"type", "text"},
                {"text", "STEVE JOBS"},
                {"size", {800.0, 95.0}},
                {"position", {630.0, 880.0}},
                {"style", {{"font", fontPath}, {"font_size", 76.0}, {"fill", "#0C0E12"}}},
                {"start_frame", 0},
                {"duration_frames", 90},
                {"animation", {{"tracks", serializeTracks(textTracks)}}}
            }
        })},
        {"camera", {
            {"type", "perspective"},
            {"position", {960.0, 540.0, -1400.0}},
            {"rotation_deg", {0.0, 0.0, 0.0}},
            {"fov_deg", 55.0},
            {"near", 1.0},
            {"far", 5000.0},
            {"zoom", 1.0}
        }},
        {"output", {
            {"path", (fs::path("ChrononTemplate/out/modern_entities_with_text/videos") / (id + ".mp4")).string()},
            {"format", "mp4"},
            {"codec", "h264"}
        }}
    };

    std::ofstream(outDir / (id + ".plan.json")) << plan.dump(2) << '\n';
    std::cout << "Emitted Filmstrip Editorial Plan: " << id << '\n';
    return 0;
}
