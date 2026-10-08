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
        std::cerr << "Usage: emit_modern_entities_v2 <out_dir>\n";
        return 1;
    }

    fs::path outDir = argv[1];
    fs::create_directories(outDir);

    const std::string fontPath = "ChrononTemplate/out/apple_spatial_entity_pack/assets/Montserrat-Bold.ttf";

    // Common subtle Apple 3D spatial animation for the main hero card
    std::vector<Track> cardTracks = {
        {"position_y", "out_cubic", {{0, -25.0f}, {48, 0.0f}, {89, 0.0f}}},
        {"position_z", "out_cubic", {{0, 140.0f}, {48, 0.0f}, {89, 0.0f}}},
        {"rotation_y", "out_cubic", {{0, -10.0f}, {48, -3.0f}, {89, -3.0f}}},
        {"rotation_x", "out_cubic", {{0, 8.0f}, {48, 2.0f}, {89, 2.0f}}},
        {"scale", "out_cubic", {{0, 0.93f}, {48, 1.0f}, {89, 1.015f}}},
        {"opacity", "out_cubic", {{0, 0.0f}, {20, 1.0f}, {89, 1.0f}}}
    };

    // Soft pill badge entrance below
    std::vector<Track> pillTracks = {
        {"position_y", "out_cubic", {{14, 20.0f}, {46, 0.0f}, {89, 0.0f}}},
        {"scale_x", "out_back", {{14, 0.6f}, {42, 1.03f}, {54, 1.0f}, {89, 1.0f}}},
        {"opacity", "out_cubic", {{14, 0.0f}, {30, 1.0f}, {89, 1.0f}}}
    };

    std::vector<Track> titleTracks = {
        {"position_y", "out_cubic", {{18, 18.0f}, {48, 0.0f}, {89, 0.0f}}},
        {"opacity", "out_cubic", {{18, 0.0f}, {34, 1.0f}, {89, 1.0f}}}
    };

    // =========================================================================
    // 1. modern_entity_01_neon_glass_hoopin
    // =========================================================================
    {
        std::string id = "modern_entity_01_neon_glass_hoopin";
        Json plan = {
            {"schema", "chronon.render-plan.v2"},
            {"version", 2},
            {"job_id", id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
            {"layers", Json::array({
                {
                    {"id", "bg_color"},
                    {"type", "color"},
                    {"color", {0.04, 0.045, 0.055, 1.0}},
                    {"start_frame", 0},
                    {"duration_frames", 90}
                },
                {
                    {"id", "hero_image"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/hero_card_hoopin.png"},
                    {"position", {960.0, 470.0}},
                    {"size", {980.0, 980.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(cardTracks)}}}
                },
                {
                    {"id", "bottom_pill_badge"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/pill_badge_apple_minimal.png"},
                    {"position", {960.0, 950.0}},
                    {"size", {700.0, 156.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(pillTracks)}}}
                },
                {
                    {"id", "name_text"},
                    {"type", "text"},
                    {"text", "Hoppin N’ Holleri"},
                    {"size", {600.0, 60.0}},
                    {"position", {960.0, 950.0}},
                    {"style", {{"font", fontPath}, {"font_size", 34.0}, {"fill", "#F2F5F8"}}},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(titleTracks)}}}
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
        std::cout << "Emitted: " << id << '\n';
    }

    // =========================================================================
    // 2. modern_entity_02_neon_card_portrait_cyan (Trump clean hero)
    // =========================================================================
    {
        std::string id = "modern_entity_02_neon_card_portrait_cyan";
        Json plan = {
            {"schema", "chronon.render-plan.v2"},
            {"version", 2},
            {"job_id", id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
            {"layers", Json::array({
                {
                    {"id", "bg_color"},
                    {"type", "color"},
                    {"color", {0.04, 0.045, 0.055, 1.0}},
                    {"start_frame", 0},
                    {"duration_frames", 90}
                },
                {
                    {"id", "hero_image"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/hero_card_trump.png"},
                    {"position", {960.0, 470.0}},
                    {"size", {930.0, 1030.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(cardTracks)}}}
                },
                {
                    {"id", "bottom_pill_badge"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/pill_badge_apple_minimal.png"},
                    {"position", {960.0, 950.0}},
                    {"size", {700.0, 156.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(pillTracks)}}}
                },
                {
                    {"id", "name_text"},
                    {"type", "text"},
                    {"text", "DONALD J. TRUMP"},
                    {"size", {600.0, 60.0}},
                    {"position", {960.0, 950.0}},
                    {"style", {{"font", fontPath}, {"font_size", 34.0}, {"fill", "#F2F5F8"}}},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(titleTracks)}}}
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
        std::cout << "Emitted: " << id << '\n';
    }

    // =========================================================================
    // 3. modern_entity_05_neon_card_gold (Steve Jobs clean hero dark)
    // =========================================================================
    {
        std::string id = "modern_entity_05_neon_card_gold";
        Json plan = {
            {"schema", "chronon.render-plan.v2"},
            {"version", 2},
            {"job_id", id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
            {"layers", Json::array({
                {
                    {"id", "bg_color"},
                    {"type", "color"},
                    {"color", {0.04, 0.045, 0.055, 1.0}},
                    {"start_frame", 0},
                    {"duration_frames", 90}
                },
                {
                    {"id", "hero_image"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/hero_card_steve.png"},
                    {"position", {960.0, 470.0}},
                    {"size", {980.0, 980.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(cardTracks)}}}
                },
                {
                    {"id", "bottom_pill_badge"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/pill_badge_apple_minimal.png"},
                    {"position", {960.0, 950.0}},
                    {"size", {700.0, 156.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(pillTracks)}}}
                },
                {
                    {"id", "name_text"},
                    {"type", "text"},
                    {"text", "STEVE JOBS"},
                    {"size", {600.0, 60.0}},
                    {"position", {960.0, 950.0}},
                    {"style", {{"font", fontPath}, {"font_size", 34.0}, {"fill", "#F2F5F8"}}},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(titleTracks)}}}
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
        std::cout << "Emitted: " << id << '\n';
    }

    // =========================================================================
    // 4. modern_entity_06_editorial_filmstrip_jobs (Exact Replica of Reference 3)
    // White background, centered rounded Steve Jobs card, bold "STEVE JOBS" below
    // =========================================================================
    {
        std::string id = "modern_entity_06_editorial_filmstrip_jobs";

        std::vector<Track> jobsWhiteCardTracks = {
            {"position_y", "out_cubic", {{0, 20.0f}, {48, 0.0f}, {89, 0.0f}}},
            {"position_z", "out_cubic", {{0, 100.0f}, {48, 0.0f}, {89, 0.0f}}},
            {"scale", "out_cubic", {{0, 0.94f}, {48, 1.0f}, {89, 1.012f}}},
            {"opacity", "out_cubic", {{0, 0.0f}, {20, 1.0f}, {89, 1.0f}}}
        };

        std::vector<Track> textJobsTracks = {
            {"position_y", "out_cubic", {{18, 25.0f}, {48, 0.0f}, {89, 0.0f}}},
            {"opacity", "out_cubic", {{18, 0.0f}, {36, 1.0f}, {89, 1.0f}}}
        };

        Json plan = {
            {"schema", "chronon.render-plan.v2"},
            {"version", 2},
            {"job_id", id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
            {"layers", Json::array({
                // Background bianco pulito
                {
                    {"id", "white_bg"},
                    {"type", "color"},
                    {"color", {0.97, 0.975, 0.98, 1.0}},
                    {"start_frame", 0},
                    {"duration_frames", 90}
                },
                // Card Steve Jobs al centro con bordi arrotondati / smussati
                {
                    {"id", "jobs_rounded_card"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/jobs_white_bg_card.png"},
                    {"position", {960.0, 460.0}},
                    {"size", {1340.0, 800.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(jobsWhiteCardTracks)}}}
                },
                // Scritta sotto STEVE JOBS in nero bold con font Montserrat-Bold
                {
                    {"id", "title_text"},
                    {"type", "text"},
                    {"text", "STEVE JOBS"},
                    {"size", {1100.0, 110.0}},
                    {"position", {960.0, 930.0}},
                    {"style", {{"font", fontPath}, {"font_size", 76.0}, {"fill", "#0A0B0E"}}},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(textJobsTracks)}}}
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
        std::cout << "Emitted: " << id << '\n';
    }

    return 0;
}
