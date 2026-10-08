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
        std::cerr << "Usage: emit_modern_entities_with_text <out_dir>\n";
        return 1;
    }

    fs::path outDir = argv[1];
    fs::create_directories(outDir);

    const std::string fontPath = "ChrononTemplate/out/apple_spatial_entity_pack/assets/Montserrat-Bold.ttf";

    // -------------------------------------------------------------
    // RECIPE 1: Neon Glass Card + Cyan Pill Badge (Hoppin N' Holleri)
    // -------------------------------------------------------------
    {
        std::string id = "modern_entity_01_neon_glass_hoopin";
        std::vector<Track> cardTracks = {
            {"position_y", "out_cubic", {{0, -40.0f}, {45, 0.0f}, {89, 0.0f}}},
            {"position_z", "out_cubic", {{0, 160.0f}, {45, 0.0f}, {89, 0.0f}}},
            {"rotation_y", "out_cubic", {{0, -26.0f}, {45, -14.0f}, {89, -14.0f}}},
            {"rotation_x", "out_cubic", {{0, 20.0f}, {45, 12.0f}, {89, 12.0f}}},
            {"rotation_z", "out_cubic", {{0, -6.0f}, {45, -3.0f}, {89, -3.0f}}},
            {"scale", "out_cubic", {{0, 0.88f}, {45, 1.0f}, {89, 1.015f}}},
            {"opacity", "out_cubic", {{0, 0.0f}, {18, 1.0f}, {89, 1.0f}}}
        };

        std::vector<Track> pillTracks = {
            {"scale_x", "out_back", {{12, 0.1f}, {38, 1.05f}, {50, 1.0f}, {89, 1.0f}}},
            {"opacity", "out_cubic", {{12, 0.0f}, {26, 1.0f}, {89, 1.0f}}}
        };

        std::vector<Track> titleTracks = {
            {"opacity", "out_cubic", {{18, 0.0f}, {34, 1.0f}, {89, 1.0f}}},
            {"scale", "out_back", {{18, 0.85f}, {42, 1.02f}, {52, 1.0f}, {89, 1.0f}}}
        };

        Json plan = {
            {"schema", "chronon.render-plan.v2"},
            {"version", 2},
            {"job_id", id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
            {"layers", Json::array({
                {
                    {"id", "bg_color"},
                    {"type", "color"},
                    {"color", {0.035, 0.04, 0.045, 1.0}},
                    {"start_frame", 0},
                    {"duration_frames", 90}
                },
                {
                    {"id", "neon_card"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/card_hoopin_cyan_glow.png"},
                    {"position", {960.0, 480.0}},
                    {"size", {720.0, 780.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(cardTracks)}}}
                },
                {
                    {"id", "neon_pill_badge"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/pill_badge_cyan.png"},
                    {"position", {960.0, 895.0}},
                    {"size", {720.0, 180.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(pillTracks)}}}
                },
                {
                    {"id", "title_text"},
                    {"type", "text"},
                    {"text", "Hoppin N’ Holleri"},
                    {"size", {600.0, 60.0}},
                    {"position", {960.0, 895.0}},
                    {"style", {{"font", fontPath}, {"font_size", 42.0}, {"fill", "#FFFFFF"}}},
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

    // -------------------------------------------------------------
    // RECIPE 2: Neon Glass Card with Portrait + Cyan Pill
    // -------------------------------------------------------------
    {
        std::string id = "modern_entity_02_neon_card_portrait_cyan";
        std::vector<Track> cardTracks = {
            {"position_y", "out_cubic", {{0, -40.0f}, {45, 0.0f}, {89, 0.0f}}},
            {"position_z", "out_cubic", {{0, 180.0f}, {45, 0.0f}, {89, 0.0f}}},
            {"rotation_y", "out_cubic", {{0, 24.0f}, {45, 14.0f}, {89, 14.0f}}},
            {"rotation_x", "out_cubic", {{0, 18.0f}, {45, 10.0f}, {89, 10.0f}}},
            {"scale", "out_cubic", {{0, 0.90f}, {45, 1.0f}, {89, 1.015f}}},
            {"opacity", "out_cubic", {{0, 0.0f}, {18, 1.0f}, {89, 1.0f}}}
        };

        std::vector<Track> pillTracks = {
            {"scale_x", "out_back", {{12, 0.1f}, {38, 1.05f}, {50, 1.0f}, {89, 1.0f}}},
            {"opacity", "out_cubic", {{12, 0.0f}, {26, 1.0f}, {89, 1.0f}}}
        };

        std::vector<Track> titleTracks = {
            {"opacity", "out_cubic", {{18, 0.0f}, {34, 1.0f}, {89, 1.0f}}},
            {"scale", "out_back", {{18, 0.85f}, {42, 1.02f}, {52, 1.0f}, {89, 1.0f}}}
        };

        Json plan = {
            {"schema", "chronon.render-plan.v2"},
            {"version", 2},
            {"job_id", id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
            {"layers", Json::array({
                {
                    {"id", "bg_color"},
                    {"type", "color"},
                    {"color", {0.03, 0.035, 0.045, 1.0}},
                    {"start_frame", 0},
                    {"duration_frames", 90}
                },
                {
                    {"id", "neon_card"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/card_trump_cyan_glow.png"},
                    {"position", {960.0, 480.0}},
                    {"size", {720.0, 780.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(cardTracks)}}}
                },
                {
                    {"id", "neon_pill_badge"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/pill_badge_cyan_electric.png"},
                    {"position", {960.0, 895.0}},
                    {"size", {720.0, 180.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(pillTracks)}}}
                },
                {
                    {"id", "title_text"},
                    {"type", "text"},
                    {"text", "DONALD J. TRUMP"},
                    {"size", {600.0, 60.0}},
                    {"position", {960.0, 895.0}},
                    {"style", {{"font", fontPath}, {"font_size", 40.0}, {"fill", "#FFFFFF"}}},
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

    // -------------------------------------------------------------
    // RECIPE 3: Curved CRT Screen Studio Light (Sixers #23)
    // -------------------------------------------------------------
    {
        std::string id = "modern_entity_03_curved_crt_sixers_studio";
        std::vector<Track> screenTracks = {
            {"scale", "out_cubic", {{0, 0.90f}, {45, 1.0f}, {89, 1.018f}}},
            {"position_z", "out_cubic", {{0, 140.0f}, {45, 0.0f}, {89, 0.0f}}},
            {"position_y", "out_cubic", {{0, 30.0f}, {45, 0.0f}, {89, 0.0f}}},
            {"opacity", "out_cubic", {{0, 0.0f}, {18, 1.0f}, {89, 1.0f}}}
        };

        std::vector<Track> textTracks = {
            {"position_y", "out_cubic", {{16, 24.0f}, {48, 0.0f}, {89, 0.0f}}},
            {"opacity", "out_cubic", {{16, 0.0f}, {34, 1.0f}, {89, 1.0f}}}
        };

        Json plan = {
            {"schema", "chronon.render-plan.v2"},
            {"version", 2},
            {"job_id", id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
            {"layers", Json::array({
                {
                    {"id", "bg_image"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/studio_light_bg.png"},
                    {"position", {960.0, 540.0}},
                    {"size", {1920.0, 1080.0}},
                    {"fit", "cover"},
                    {"start_frame", 0},
                    {"duration_frames", 90}
                },
                {
                    {"id", "curved_crt_screen"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/curved_screen_sixers.png"},
                    {"position", {960.0, 485.0}},
                    {"size", {1560.0, 950.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(screenTracks)}}}
                },
                {
                    {"id", "title_text"},
                    {"type", "text"},
                    {"text", "WORLD B. FREE"},
                    {"size", {1000.0, 70.0}},
                    {"position", {960.0, 975.0}},
                    {"style", {{"font", fontPath}, {"font_size", 42.0}, {"fill", "#12151D"}}},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(textTracks)}}}
                },
                {
                    {"id", "subtitle_text"},
                    {"type", "text"},
                    {"text", "PHILADELPHIA 76ERS • #23"},
                    {"size", {1000.0, 45.0}},
                    {"position", {960.0, 1025.0}},
                    {"style", {{"font", fontPath}, {"font_size", 22.0}, {"fill", "#5A606E"}}},
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
        std::cout << "Emitted: " << id << '\n';
    }

    // -------------------------------------------------------------
    // RECIPE 4: Curved CRT Screen Dark Studio (Steve Jobs)
    // -------------------------------------------------------------
    {
        std::string id = "modern_entity_04_curved_crt_portrait_dark";
        std::vector<Track> screenTracks = {
            {"scale", "out_cubic", {{0, 0.91f}, {48, 1.0f}, {89, 1.02f}}},
            {"position_z", "out_cubic", {{0, 150.0f}, {48, 0.0f}, {89, 0.0f}}},
            {"opacity", "out_cubic", {{0, 0.0f}, {18, 1.0f}, {89, 1.0f}}}
        };

        std::vector<Track> textTracks = {
            {"position_y", "out_cubic", {{18, 24.0f}, {50, 0.0f}, {89, 0.0f}}},
            {"opacity", "out_cubic", {{18, 0.0f}, {36, 1.0f}, {89, 1.0f}}}
        };

        Json plan = {
            {"schema", "chronon.render-plan.v2"},
            {"version", 2},
            {"job_id", id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
            {"layers", Json::array({
                {
                    {"id", "bg_image"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/studio_dark_bg.png"},
                    {"position", {960.0, 540.0}},
                    {"size", {1920.0, 1080.0}},
                    {"fit", "cover"},
                    {"start_frame", 0},
                    {"duration_frames", 90}
                },
                {
                    {"id", "curved_crt_screen"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/curved_screen_steve.png"},
                    {"position", {960.0, 485.0}},
                    {"size", {1560.0, 950.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(screenTracks)}}}
                },
                {
                    {"id", "title_text"},
                    {"type", "text"},
                    {"text", "STEVE JOBS"},
                    {"size", {1000.0, 70.0}},
                    {"position", {960.0, 975.0}},
                    {"style", {{"font", fontPath}, {"font_size", 42.0}, {"fill", "#F2F4F8"}}},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(textTracks)}}}
                },
                {
                    {"id", "subtitle_text"},
                    {"type", "text"},
                    {"text", "CHIEF EXECUTIVE OFFICER • APPLE"},
                    {"size", {1000.0, 45.0}},
                    {"position", {960.0, 1025.0}},
                    {"style", {{"font", fontPath}, {"font_size", 22.0}, {"fill", "#FFC832"}}},
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
        std::cout << "Emitted: " << id << '\n';
    }

    // -------------------------------------------------------------
    // RECIPE 5: Warm Gold Neon Glass Card + Gold Pill Badge
    // -------------------------------------------------------------
    {
        std::string id = "modern_entity_05_neon_card_gold";
        std::vector<Track> cardTracks = {
            {"position_y", "out_cubic", {{0, -40.0f}, {45, 0.0f}, {89, 0.0f}}},
            {"position_z", "out_cubic", {{0, 160.0f}, {45, 0.0f}, {89, 0.0f}}},
            {"rotation_y", "out_cubic", {{0, -22.0f}, {45, -12.0f}, {89, -12.0f}}},
            {"rotation_x", "out_cubic", {{0, 18.0f}, {45, 10.0f}, {89, 10.0f}}},
            {"scale", "out_cubic", {{0, 0.90f}, {45, 1.0f}, {89, 1.015f}}},
            {"opacity", "out_cubic", {{0, 0.0f}, {18, 1.0f}, {89, 1.0f}}}
        };

        std::vector<Track> pillTracks = {
            {"scale_x", "out_back", {{12, 0.1f}, {38, 1.05f}, {50, 1.0f}, {89, 1.0f}}},
            {"opacity", "out_cubic", {{12, 0.0f}, {26, 1.0f}, {89, 1.0f}}}
        };

        std::vector<Track> titleTracks = {
            {"opacity", "out_cubic", {{18, 0.0f}, {34, 1.0f}, {89, 1.0f}}},
            {"scale", "out_back", {{18, 0.85f}, {42, 1.02f}, {52, 1.0f}, {89, 1.0f}}}
        };

        Json plan = {
            {"schema", "chronon.render-plan.v2"},
            {"version", 2},
            {"job_id", id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 90}}},
            {"layers", Json::array({
                {
                    {"id", "bg_color"},
                    {"type", "color"},
                    {"color", {0.035, 0.03, 0.025, 1.0}},
                    {"start_frame", 0},
                    {"duration_frames", 90}
                },
                {
                    {"id", "neon_card"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/card_steve_gold_glow.png"},
                    {"position", {960.0, 480.0}},
                    {"size", {720.0, 780.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(cardTracks)}}}
                },
                {
                    {"id", "neon_pill_badge"},
                    {"type", "image"},
                    {"asset", "ChrononTemplate/out/modern_entities_with_text/assets/pill_badge_gold.png"},
                    {"position", {960.0, 895.0}},
                    {"size", {720.0, 180.0}},
                    {"fit", "contain"},
                    {"enable_3d", true},
                    {"start_frame", 0},
                    {"duration_frames", 90},
                    {"animation", {{"tracks", serializeTracks(pillTracks)}}}
                },
                {
                    {"id", "title_text"},
                    {"type", "text"},
                    {"text", "STEVE JOBS"},
                    {"size", {600.0, 60.0}},
                    {"position", {960.0, 895.0}},
                    {"style", {{"font", fontPath}, {"font_size", 42.0}, {"fill", "#FFFFFF"}}},
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

    return 0;
}
