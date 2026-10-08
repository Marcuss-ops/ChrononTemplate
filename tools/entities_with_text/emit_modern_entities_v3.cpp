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
        std::cerr << "Usage: emit_modern_entities_v3 <out_dir>\n";
        return 1;
    }

    fs::path outDir = argv[1];
    fs::create_directories(outDir);

    const std::string fontPath = "ChrononTemplate/out/apple_spatial_entity_pack/assets/Montserrat-Bold.ttf";

    // 1. Smooth 3D spatial motion for floating entity (clean, no box)
    std::vector<Track> heroTracks = {
        {"position_y", "out_cubic", {{0, -30.0f}, {48, 0.0f}, {89, 0.0f}}},
        {"position_z", "out_cubic", {{0, 140.0f}, {48, 0.0f}, {89, 0.0f}}},
        {"scale", "out_cubic", {{0, 0.92f}, {48, 1.0f}, {89, 1.015f}}},
        {"opacity", "out_cubic", {{0, 0.0f}, {20, 1.0f}, {89, 1.0f}}}
    };

    // Pill badge below (single bottom badge with name)
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
    // 1. modern_entity_01_neon_glass_hoopin -> Steve Jobs Pure Color Cutout (NO BOX)
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
                // Steve Jobs Pure Cutout, NO BOX!
                {
                    {"id", "pure_emblem_image"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/nobox_steve_cutout.png"},
                    {"position", {960.0, 480.0}},
                    {"size", {950.0, 920.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(heroTracks)}}}
                },
                // Only the pill badge below with the name!
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
        std::cout << "Emitted v3: " << id << '\n';
    }

    // =========================================================================
    // 2. modern_entity_02_neon_card_portrait_cyan -> Steve Jobs B&W Cutout (NO BOX)
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
                // Steve Jobs B&W Cutout with soft shadow, NO BOX!
                {
                    {"id", "pure_portrait_cutout"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/nobox_steve_cutout_bw.png"},
                    {"position", {960.0, 480.0}},
                    {"size", {950.0, 920.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(heroTracks)}}}
                },
                // Only the pill badge below with the name!
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
        std::cout << "Emitted v3: " << id << '\n';
    }

    // =========================================================================
    // 3. modern_entity_05_neon_card_gold -> Steve Jobs Pure Cutout (NO BOX)
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
                // Steve Jobs pure cutout, NO BOX!
                {
                    {"id", "pure_portrait_image"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/nobox_steve_cutout.png"},
                    {"position", {960.0, 480.0}},
                    {"size", {950.0, 920.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(heroTracks)}}}
                },
                // Only the box below with the name!
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
        std::cout << "Emitted v3: " << id << '\n';
    }

    // =========================================================================
    // =========================================================================
    // 4. modern_entity_06_editorial_filmstrip_jobs
    // Layout: Text on TOP ("STEVE JOBS"), Image in the CENTER (rounded photo card)
    // Animation: Text slides down & fades in first, followed by the centered card
    // =========================================================================
    {
        std::string id = "modern_entity_06_editorial_filmstrip_jobs";

        // Text at top: Enters first (frames 0 to 28)
        std::vector<Track> textJobsTracks = {
            {"position_y", "out_cubic", {{0, -25.0f}, {28, 0.0f}, {89, 0.0f}}},
            {"opacity", "out_cubic", {{0, 0.0f}, {20, 1.0f}, {89, 1.0f}}}
        };

        // Centered Steve Jobs Card: Enters right after the text (frames 14 to 52)
        std::vector<Track> jobsWhiteCardTracks = {
            {"position_y", "out_cubic", {{14, 25.0f}, {52, 0.0f}, {89, 0.0f}}},
            {"position_z", "out_cubic", {{14, 70.0f}, {52, 0.0f}, {89, 0.0f}}},
            {"scale", "out_cubic", {{14, 0.94f}, {52, 1.0f}, {89, 1.012f}}},
            {"opacity", "out_cubic", {{14, 0.0f}, {32, 1.0f}, {89, 1.0f}}}
        };

        Json plan = {
            {"schema", "chronon.render-plan.v2"},
            {"version", 2},
            {"job_id", id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
            {"layers", Json::array({
                // Clean white background
                {
                    {"id", "pure_white_bg"},
                    {"type", "color"},
                    {"color", {1.0, 1.0, 1.0, 1.0}},
                    {"start_frame", 0},
                    {"duration_frames", 90}
                },
                // Scritta IN ALTO: STEVE JOBS in bold typography (y = 105.0)
                {
                    {"id", "title_text"},
                    {"type", "text"},
                    {"text", "STEVE JOBS"},
                    {"size", {1100.0, 90.0}},
                    {"position", {960.0, 105.0}},
                    {"style", {{"font", fontPath}, {"font_size", 72.0}, {"fill", "#0A0B0E"}}},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(textJobsTracks)}}}
                },
                // Immagine Steve Jobs AL CENTRO (y = 600.0) con angoli arrotondati e ombra morbida
                {
                    {"id", "jobs_rounded_image"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/jobs_white_bg_card.png"},
                    {"position", {960.0, 600.0}},
                    {"size", {1200.0, 716.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(jobsWhiteCardTracks)}}}
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
        std::cout << "Emitted v3: " << id << '\n';
    }

    return 0;
}
