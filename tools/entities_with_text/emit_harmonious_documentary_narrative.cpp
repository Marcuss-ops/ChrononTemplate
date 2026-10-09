#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>
#include <chrono>

using Json = nlohmann::ordered_json;
namespace fs = std::filesystem;

struct Keyframe {
    int frame;
    double value;
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

Track makeTrack(const std::string& prop, const std::string& easing, const std::vector<Keyframe>& keyframes) {
    return Track{prop, easing, keyframes};
}

int main(int argc, char** argv) {
    std::string outPlanPath = "out/documentary_narrative_cpp.plan.json";
    std::string outMp4Path = "out/documentary_narrative_cpp.mp4";
    bool doRender = false;
    bool doUpload = false;
    std::string driveFolderId = "1UEUnH1G35Zyhdq7iH2VN0GkyrPiHgMUN";

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--render") {
            doRender = true;
        } else if (arg == "--upload" && i + 1 < argc) {
            doUpload = true;
            driveFolderId = argv[++i];
        } else if (arg == "-o" && i + 1 < argc) {
            outPlanPath = argv[++i];
        }
    }

    const int width = 1920;
    const int height = 1080;
    const int fps = 30;
    const int durationFrames = 390; // 13.0s

    const std::string bgVideo = "assets/backgrounds/documentary_bg.mp4";
    const std::string fontBold = "assets/fonts/Inter-Bold.ttf";
    const std::string fontRegular = "assets/fonts/Inter-Regular.ttf";
    const std::string turingImg = "assets/images/alan_turing.png";
    const std::string adaImg = "assets/images/ada_lovelace.jpg";
    const std::string mapPlate = "assets/maps/t4_plate2.png";
    const std::string mapReticle = "assets/maps/doc_reticle.png";

    Json layers = Json::array();

    // =========================================================================
    // 0. Real Documentary Background Video + Cinematic Grade
    // =========================================================================
    layers.push_back({
        {"id", "bg_video"},
        {"type", "video"},
        {"source", bgVideo},
        {"size", {width, height}},
        {"position", {0, 0}},
        {"fit", "cover"},
        {"screen_space", true},
        {"start_frame", 0},
        {"duration_frames", durationFrames},
        {"loop", true}
    });

    layers.push_back({
        {"id", "bg_tint"},
        {"type", "color"},
        {"color", {0.012, 0.018, 0.028, 0.75}},
        {"size", {width, height}},
        {"position", {0, 0}},
        {"screen_space", true},
        {"start_frame", 0},
        {"duration_frames", durationFrames}
    });

    // Top Header Badge
    std::vector<Track> headerTracks = {
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {20, 1.0}, {240, 1.0}, {259, 0.0}})
    };
    layers.push_back({
        {"id", "header_pill_bg"},
        {"type", "color"},
        {"color", {0.06, 0.09, 0.14, 0.88}},
        {"size", {640, 42}},
        {"position", {0, -470}},
        {"radius", 21},
        {"start_frame", 0},
        {"duration_frames", 260},
        {"animation", {{"tracks", serializeTracks(headerTracks)}}}
    });

    layers.push_back({
        {"id", "header_text"},
        {"type", "text"},
        {"text", "HISTORICAL CHRONOLOGY  •  BRITISH INTELLIGENCE"},
        {"size", {620, 36}},
        {"position", {960, 70}},
        {"style", {
            {"font", fontBold},
            {"font_size", 17},
            {"fill", "#00F0FF"},
            {"fit_mode", "shrink_only"}
        }},
        {"start_frame", 0},
        {"duration_frames", 260},
        {"animation", {{"tracks", serializeTracks(headerTracks)}}}
    });

    // =========================================================================
    // 1. Alan Turing (Full 3D Entrance + Duo Handoff)
    // Synchronized multi-axis keyframes: [0, 32, 150, 185, 240, 259]
    // =========================================================================
    const int turingStart = 0;
    const int turingDur = 260;

    std::vector<Keyframe> turingPosX = {{0, 0.0}, {32, 0.0}, {150, 0.0}, {185, -430.0}, {240, -430.0}, {259, -430.0}};
    std::vector<Keyframe> turingPosY = {{0, 0.0}, {32, 0.0}, {150, 0.0}, {185, 0.0}, {240, 0.0}, {259, 0.0}};
    std::vector<Keyframe> turingPosZ = {{0, -280.0}, {32, 0.0}, {150, 0.0}, {185, 0.0}, {240, 0.0}, {259, 120.0}};

    std::vector<Keyframe> turingRotX = {{0, 0.0}, {32, 0.0}, {150, 0.0}, {185, 0.0}, {240, 0.0}, {259, 0.0}};
    std::vector<Keyframe> turingRotY = {{0, -24.0}, {32, 0.0}, {150, 0.0}, {185, -1.5}, {240, -1.5}, {259, -1.5}};
    std::vector<Keyframe> turingRotZ = {{0, 0.0}, {32, 0.0}, {150, 0.0}, {185, 0.0}, {240, 0.0}, {259, 0.0}};

    std::vector<Keyframe> turingScale = {{0, 0.88}, {32, 1.0}, {150, 1.0}, {185, 0.88}, {240, 0.88}, {259, 0.78}};
    std::vector<Keyframe> turingOpacity = {{0, 0.0}, {32, 1.0}, {150, 1.0}, {185, 1.0}, {240, 1.0}, {259, 0.0}};

    std::vector<Track> turing3dTracks = {
        makeTrack("position_x", "out_cubic", turingPosX),
        makeTrack("position_y", "out_cubic", turingPosY),
        makeTrack("position_z", "out_cubic", turingPosZ),
        makeTrack("rotation_x", "out_cubic", turingRotX),
        makeTrack("rotation_y", "out_cubic", turingRotY),
        makeTrack("rotation_z", "out_cubic", turingRotZ),
        makeTrack("scale", "out_cubic", turingScale),
        makeTrack("opacity", "out_cubic", turingOpacity)
    };

    // Turing Plinth
    layers.push_back({
        {"id", "turing_card_bg"},
        {"type", "color"},
        {"color", {0.05, 0.07, 0.11, 0.95}},
        {"size", {480, 520}},
        {"position", {0, -80}},
        {"radius", 24},
        {"enable_3d", true},
        {"start_frame", turingStart},
        {"duration_frames", turingDur},
        {"animation", {{"tracks", serializeTracks(turing3dTracks)}}}
    });

    // Turing Portrait
    layers.push_back({
        {"id", "turing_portrait"},
        {"type", "image"},
        {"asset", turingImg},
        {"size", {440, 410}},
        {"position", {0, -120}},
        {"fit", "cover"},
        {"radius", 18},
        {"enable_3d", true},
        {"start_frame", turingStart},
        {"duration_frames", turingDur},
        {"animation", {{"tracks", serializeTracks(turing3dTracks)}}}
    });

    // Turing Pill Badge
    layers.push_back({
        {"id", "turing_pill_bg"},
        {"type", "color"},
        {"color", {0.08, 0.12, 0.18, 0.95}},
        {"size", {420, 50}},
        {"position", {0, 130}},
        {"radius", 25},
        {"enable_3d", true},
        {"start_frame", turingStart},
        {"duration_frames", turingDur},
        {"animation", {{"tracks", serializeTracks(turing3dTracks)}}}
    });

    // Turing Name Text
    std::vector<Track> turingTextTracks = {
        makeTrack("position_x", "out_cubic", turingPosX),
        makeTrack("scale", "out_cubic", turingScale),
        makeTrack("opacity", "out_cubic", turingOpacity)
    };
    layers.push_back({
        {"id", "turing_name_text"},
        {"type", "text"},
        {"text", "ALAN TURING  •  CRYPTANALYST"},
        {"size", {400, 40}},
        {"position", {960, 670}},
        {"style", {
            {"font", fontBold},
            {"font_size", 20},
            {"fill", "#FFFFFF"},
            {"fit_mode", "shrink_only"}
        }},
        {"start_frame", turingStart},
        {"duration_frames", turingDur},
        {"animation", {{"tracks", serializeTracks(turingTextTracks)}}}
    });

    // =========================================================================
    // 2. Connected Timeline Sotto (Data 1940 - Collegata al 100% all'immagine)
    // Starts at Frame 75 directly underneath Alan Turing
    // =========================================================================
    const int timelineStart = 75;
    const int timelineDur = 185;

    std::vector<Track> timelineBarTracks = {
        makeTrack("scale_x", "out_cubic", {{0, 0.05}, {28, 1.0}, {184, 1.0}}),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {18, 1.0}, {165, 1.0}, {184, 0.0}})
    };
    layers.push_back({
        {"id", "timeline_bar_bg"},
        {"type", "color"},
        {"color", {0.06, 0.09, 0.14, 0.92}},
        {"size", {960, 76}},
        {"position", {0, 270}},
        {"radius", 20},
        {"start_frame", timelineStart},
        {"duration_frames", timelineDur},
        {"animation", {{"tracks", serializeTracks(timelineBarTracks)}}}
    });

    layers.push_back({
        {"id", "timeline_rail_line"},
        {"type", "color"},
        {"color", {0.0, 0.94, 1.0, 0.85}},
        {"size", {900, 3}},
        {"position", {0, 246}},
        {"start_frame", timelineStart},
        {"duration_frames", timelineDur},
        {"animation", {{"tracks", serializeTracks(timelineBarTracks)}}}
    });

    // Year Callout Pill ("1940")
    std::vector<Track> yearPillTracks = {
        makeTrack("scale", "out_cubic", {{0, 0.5}, {22, 1.08}, {32, 1.0}, {184, 1.0}}),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {16, 1.0}, {165, 1.0}, {184, 0.0}})
    };
    layers.push_back({
        {"id", "timeline_year_pill"},
        {"type", "color"},
        {"color", {0.0, 0.94, 1.0, 1.0}},
        {"size", {130, 36}},
        {"position", {-350, 275}},
        {"radius", 18},
        {"start_frame", timelineStart},
        {"duration_frames", timelineDur},
        {"animation", {{"tracks", serializeTracks(yearPillTracks)}}}
    });

    layers.push_back({
        {"id", "timeline_year_text"},
        {"type", "text"},
        {"text", "1940"},
        {"size", {120, 32}},
        {"position", {610, 815}},
        {"style", {
            {"font", fontBold},
            {"font_size", 22},
            {"fill", "#0A0D14"},
            {"fit_mode", "shrink_only"}
        }},
        {"start_frame", timelineStart},
        {"duration_frames", timelineDur},
        {"animation", {{"tracks", serializeTracks(yearPillTracks)}}}
    });

    std::vector<Track> timelineDescTracks = {
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {24, 1.0}, {165, 1.0}, {184, 0.0}})
    };
    layers.push_back({
        {"id", "timeline_desc_text"},
        {"type", "text"},
        {"text", "ENIGMA CIPHER CRACKED  •  BOMBE MACHINE DEPLOYED"},
        {"size", {700, 36}},
        {"position", {1080, 815}},
        {"style", {
            {"font", fontBold},
            {"font_size", 20},
            {"fill", "#FFFFFF"},
            {"fit_mode", "shrink_only"}
        }},
        {"start_frame", timelineStart},
        {"duration_frames", timelineDur},
        {"animation", {{"tracks", serializeTracks(timelineDescTracks)}}}
    });

    // =========================================================================
    // 3. Ada Lovelace (Second Image in Same Group - Duo Pairing)
    // Synchronized multi-axis keyframes: [0, 32, 85, 104]
    // =========================================================================
    const int adaStart = 155;
    const int adaDur = 105;

    std::vector<Keyframe> adaPosX = {{0, 430.0 + 80.0}, {32, 430.0}, {85, 430.0}, {104, 430.0}};
    std::vector<Keyframe> adaPosY = {{0, 0.0}, {32, 0.0}, {85, 0.0}, {104, 0.0}};
    std::vector<Keyframe> adaPosZ = {{0, -280.0}, {32, 0.0}, {85, 0.0}, {104, 120.0}};

    std::vector<Keyframe> adaRotX = {{0, 0.0}, {32, 0.0}, {85, 0.0}, {104, 0.0}};
    std::vector<Keyframe> adaRotY = {{0, 24.0}, {32, 0.0}, {85, 1.5}, {104, 1.5}};
    std::vector<Keyframe> adaRotZ = {{0, 0.0}, {32, 0.0}, {85, 0.0}, {104, 0.0}};

    std::vector<Keyframe> adaScale = {{0, 0.88}, {32, 0.88}, {85, 0.88}, {104, 0.78}};
    std::vector<Keyframe> adaOpacity = {{0, 0.0}, {32, 1.0}, {85, 1.0}, {104, 0.0}};

    std::vector<Track> ada3dTracks = {
        makeTrack("position_x", "out_cubic", adaPosX),
        makeTrack("position_y", "out_cubic", adaPosY),
        makeTrack("position_z", "out_cubic", adaPosZ),
        makeTrack("rotation_x", "out_cubic", adaRotX),
        makeTrack("rotation_y", "out_cubic", adaRotY),
        makeTrack("rotation_z", "out_cubic", adaRotZ),
        makeTrack("scale", "out_cubic", adaScale),
        makeTrack("opacity", "out_cubic", adaOpacity)
    };

    layers.push_back({
        {"id", "ada_card_bg"},
        {"type", "color"},
        {"color", {0.05, 0.07, 0.11, 0.95}},
        {"size", {480, 520}},
        {"position", {0, -80}},
        {"radius", 24},
        {"enable_3d", true},
        {"start_frame", adaStart},
        {"duration_frames", adaDur},
        {"animation", {{"tracks", serializeTracks(ada3dTracks)}}}
    });

    layers.push_back({
        {"id", "ada_portrait"},
        {"type", "image"},
        {"asset", adaImg},
        {"size", {440, 410}},
        {"position", {0, -120}},
        {"fit", "cover"},
        {"radius", 18},
        {"enable_3d", true},
        {"start_frame", adaStart},
        {"duration_frames", adaDur},
        {"animation", {{"tracks", serializeTracks(ada3dTracks)}}}
    });

    layers.push_back({
        {"id", "ada_pill_bg"},
        {"type", "color"},
        {"color", {0.08, 0.12, 0.18, 0.95}},
        {"size", {420, 50}},
        {"position", {0, 130}},
        {"radius", 25},
        {"enable_3d", true},
        {"start_frame", adaStart},
        {"duration_frames", adaDur},
        {"animation", {{"tracks", serializeTracks(ada3dTracks)}}}
    });

    std::vector<Track> adaTextTracks = {
        makeTrack("position_x", "out_cubic", {{0, 80.0}, {32, 0.0}, {85, 0.0}, {104, 0.0}}),
        makeTrack("scale", "out_cubic", adaScale),
        makeTrack("opacity", "out_cubic", adaOpacity)
    };
    layers.push_back({
        {"id", "ada_name_text"},
        {"type", "text"},
        {"text", "ADA LOVELACE  •  ALGORITHM PIONEER"},
        {"size", {400, 40}},
        {"position", {1390, 670}},
        {"style", {
            {"font", fontBold},
            {"font_size", 20},
            {"fill", "#FFFFFF"},
            {"fit_mode", "shrink_only"}
        }},
        {"start_frame", adaStart},
        {"duration_frames", adaDur},
        {"animation", {{"tracks", serializeTracks(adaTextTracks)}}}
    });

    // Duo Synergic Header
    std::vector<Track> duoHeaderTracks = {
        makeTrack("scale", "out_cubic", {{0, 0.7}, {24, 1.0}, {60, 1.0}, {79, 1.0}}),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {18, 1.0}, {60, 1.0}, {79, 0.0}})
    };
    layers.push_back({
        {"id", "duo_link_badge"},
        {"type", "color"},
        {"color", {0.07, 0.11, 0.16, 0.92}},
        {"size", {380, 36}},
        {"position", {0, -320}},
        {"radius", 18},
        {"start_frame", 180},
        {"duration_frames", 80},
        {"animation", {{"tracks", serializeTracks(duoHeaderTracks)}}}
    });

    layers.push_back({
        {"id", "duo_link_text"},
        {"type", "text"},
        {"text", "THEORETICAL FOUNDATION DUO"},
        {"size", {360, 30}},
        {"position", {960, 220}},
        {"style", {
            {"font", fontBold},
            {"font_size", 16},
            {"fill", "#50FA7B"},
            {"fit_mode", "shrink_only"}
        }},
        {"start_frame", 180},
        {"duration_frames", 80},
        {"animation", {{"tracks", serializeTracks(duoHeaderTracks)}}}
    });

    // =========================================================================
    // 4. MAP ANIMATION: LONDON, UK (Cinematic Flyover / Tactical Zoom on London)
    // Synchronized multi-axis keyframes: [0, 30, 134]
    // =========================================================================
    const int mapStart = 255;
    const int mapDur = 135;

    std::vector<Track> mapTracks = {
        makeTrack("position_x", "out_cubic", {{0, 0.0}, {30, 0.0}, {134, 0.0}}),
        makeTrack("position_y", "out_cubic", {{0, 30.0}, {30, 0.0}, {134, -40.0}}),
        makeTrack("scale", "out_cubic", {{0, 1.02}, {30, 1.15}, {134, 1.32}}),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {24, 1.0}, {134, 1.0}})
    };

    layers.push_back({
        {"id", "map_plate"},
        {"type", "image"},
        {"asset", mapPlate},
        {"size", {1920, 1080}},
        {"position", {0, 0}},
        {"fit", "cover"},
        {"start_frame", mapStart},
        {"duration_frames", mapDur},
        {"animation", {{"tracks", serializeTracks(mapTracks)}}}
    });

    std::vector<Track> vignetteTracks = {
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {24, 0.45}, {134, 0.45}})
    };
    layers.push_back({
        {"id", "map_vignette"},
        {"type", "color"},
        {"color", {0.02, 0.03, 0.05, 0.45}},
        {"size", {width, height}},
        {"position", {0, 0}},
        {"screen_space", true},
        {"start_frame", mapStart},
        {"duration_frames", mapDur},
        {"animation", {{"tracks", serializeTracks(vignetteTracks)}}}
    });

    // Radar Beacon Dot
    std::vector<Track> radarDotTracks = {
        makeTrack("scale", "out_cubic", {
            {0, 0.0}, {15, 1.6}, {30, 1.0}, {45, 1.6}, {60, 1.0},
            {75, 1.6}, {90, 1.0}, {119, 1.4}
        }),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {15, 1.0}, {119, 1.0}})
    };
    layers.push_back({
        {"id", "radar_dot"},
        {"type", "color"},
        {"color", {0.0, 0.94, 1.0, 1.0}},
        {"size", {18, 18}},
        {"position", {60, -30}},
        {"radius", 9},
        {"start_frame", mapStart + 15},
        {"duration_frames", mapDur - 15},
        {"animation", {{"tracks", serializeTracks(radarDotTracks)}}}
    });

    // Tactical Reticle
    std::vector<Track> reticleTracks = {
        makeTrack("rotation_z", "out_cubic", {{0, -90.0}, {40, 0.0}, {124, 45.0}}),
        makeTrack("scale", "out_cubic", {{0, 1.8}, {30, 1.0}, {124, 1.05}}),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {20, 1.0}, {124, 1.0}})
    };
    layers.push_back({
        {"id", "map_reticle"},
        {"type", "image"},
        {"asset", mapReticle},
        {"size", {120, 120}},
        {"position", {60, -30}},
        {"fit", "contain"},
        {"start_frame", mapStart + 10},
        {"duration_frames", mapDur - 10},
        {"animation", {{"tracks", serializeTracks(reticleTracks)}}}
    });

    // Callout Information Card
    std::vector<Track> calloutTracks = {
        makeTrack("position_x", "out_cubic", {{0, -60.0}, {28, 0.0}, {114, 0.0}}),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {20, 1.0}, {114, 1.0}})
    };
    layers.push_back({
        {"id", "london_card_bg"},
        {"type", "color"},
        {"color", {0.05, 0.08, 0.13, 0.95}},
        {"size", {620, 170}},
        {"position", {-580, 360}},
        {"radius", 22},
        {"start_frame", mapStart + 20},
        {"duration_frames", mapDur - 20},
        {"animation", {{"tracks", serializeTracks(calloutTracks)}}}
    });

    std::vector<Track> calloutTextTracks = {
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {20, 1.0}, {114, 1.0}})
    };
    layers.push_back({
        {"id", "london_eyebrow"},
        {"type", "text"},
        {"text", "TACTICAL GEOGRAPHIC LOCATION"},
        {"size", {560, 30}},
        {"position", {380, 835}},
        {"style", {
            {"font", fontBold},
            {"font_size", 17},
            {"fill", "#00F0FF"},
            {"fit_mode", "shrink_only"}
        }},
        {"start_frame", mapStart + 20},
        {"duration_frames", mapDur - 20},
        {"animation", {{"tracks", serializeTracks(calloutTextTracks)}}}
    });

    layers.push_back({
        {"id", "london_title"},
        {"type", "text"},
        {"text", "LONDON, UK"},
        {"size", {560, 52}},
        {"position", {380, 880}},
        {"style", {
            {"font", fontBold},
            {"font_size", 42},
            {"fill", "#FFFFFF"},
            {"fit_mode", "shrink_only"}
        }},
        {"start_frame", mapStart + 20},
        {"duration_frames", mapDur - 20},
        {"animation", {{"tracks", serializeTracks(calloutTextTracks)}}}
    });

    layers.push_back({
        {"id", "london_sub"},
        {"type", "text"},
        {"text", "51.5074° N  •  0.1278° W  (ADMIRALTY & WAR CABINET)"},
        {"size", {560, 32}},
        {"position", {380, 935}},
        {"style", {
            {"font", fontRegular},
            {"font_size", 18},
            {"fill", "#A0B8D0"},
            {"fit_mode", "shrink_only"}
        }},
        {"start_frame", mapStart + 20},
        {"duration_frames", mapDur - 20},
        {"animation", {{"tracks", serializeTracks(calloutTextTracks)}}}
    });

    // Assemble final chronon.render-plan.v3
    Json plan = {
        {"schema", "chronon.render-plan.v3"},
        {"version", 3},
        {"job_id", "documentary_narrative_cpp"},
        {"canvas", {
            {"width", width},
            {"height", height},
            {"fps_num", fps},
            {"fps_den", 1},
            {"duration_frames", durationFrames}
        }},
        {"output", {
            {"path", outMp4Path},
            {"format", "mp4"},
            {"codec", "h264"}
        }},
        {"layers", layers}
    };

    fs::create_directories(fs::path(outPlanPath).parent_path());
    std::ofstream ofs(outPlanPath);
    ofs << plan.dump(2);
    ofs.close();

    std::cout << "[C++ Native] Plan successfully emitted to: " << outPlanPath
              << " (" << layers.size() << " layers, " << durationFrames << " frames)\n";

    if (doRender) {
        std::cout << "[C++ Native] Invoking Chronon3D CLI renderer...\n";
        std::string renderCmd = "./Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli render "
                                "--plan " + outPlanPath + " "
                                "-o " + outMp4Path + " "
                                "--assets-root /home/pierone/src/go-master/projects/Pyt/VeloxEditing/Chronon3d";
        int ret = std::system(renderCmd.c_str());
        if (ret != 0) {
            std::cerr << "[C++ Native] Error during Chronon3D render (exit code " << ret << ")\n";
            return 1;
        }
        std::cout << "[C++ Native] Render complete! MP4 saved to: " << outMp4Path << "\n";

        if (doUpload) {
            std::cout << "[C++ Native] Uploading to Google Drive (" << driveFolderId << ")...\n";
            std::string uploadCmd = "./RenderingGen/bin/drive-upload "
                                    "-credentials /home/pierone/.config/velox/credentials.json "
                                    "-token /home/pierone/.config/velox/token.json "
                                    "-folder " + driveFolderId + " "
                                    "-file " + outMp4Path + " "
                                    "-name documentary_narrative_cpp.mp4";
            int upRet = std::system(uploadCmd.c_str());
            if (upRet != 0) {
                std::cerr << "[C++ Native] Error during Drive upload (exit code " << upRet << ")\n";
                return 1;
            }
            std::cout << "[C++ Native] Successfully uploaded to Drive!\n";
        }
    }

    return 0;
}
