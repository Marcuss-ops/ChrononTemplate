#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>
#include <cmath>

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
    std::string outPlanPath = "out/cinematic_documentary_cpp.plan.json";
    std::string outMp4Path = "out/cinematic_documentary_cpp.mp4";
    bool doRender = true;
    bool doUpload = true;
    std::string driveFolderId = "1UEUnH1G35Zyhdq7iH2VN0GkyrPiHgMUN";

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--no-render") {
            doRender = false;
        } else if (arg == "--no-upload") {
            doUpload = false;
        } else if (arg == "--folder" && i + 1 < argc) {
            driveFolderId = argv[++i];
        } else if (arg == "-o" && i + 1 < argc) {
            outPlanPath = argv[++i];
        }
    }

    const int width = 1920;
    const int height = 1080;
    const int fps = 30;
    const int durationFrames = 390; // 13.0s

    // Archival broadcast plates & imagery
    const std::string bgDark = "assets/backgrounds/cinematic_dark_slate.png";
    const std::string chapterPlate = "assets/images/plate_chapter.png";
    const std::string synergyPlate = "assets/images/plate_synergy.png";
    const std::string turingCompound = "assets/images/turing_compound_plate.png";
    const std::string adaCompound = "assets/images/ada_compound_plate.png";
    const std::string timelineMilestonePlate = "assets/images/plate_timeline_milestone.png";
    const std::string mapPlate = "assets/maps/london_tactical_basemap.png";
    const std::string mapReticle = "assets/maps/doc_reticle_gold.png";
    const std::string mapBeacon = "assets/maps/gold_beacon_target.png";
    const std::string mapInfoPlate = "assets/images/plate_map_info.png";

    // =========================================================================
    // 3D Cinematic Camera with Steadicam Banking & Dynamic Camera Roll
    // - Frame 0->60: Dolly push into Turing (+1.6 deg roll relaxing to 0)
    // - Frame 130->180: Pan right & bank roll (-1.4 deg) as Ada Lovelace enters
    // - Frame 250->390: Flyover sweep directly into London tactical map plate
    // =========================================================================
    std::vector<Track> cameraTracks = {
        // Lateral camera pan (tracking subjects)
        makeTrack("camera_position_x", "in_out_cubic", {
            {0, 0.0},
            {120, 0.0},
            {175, 40.0},
            {250, 40.0},
            {290, 0.0},
            {389, 0.0}
        }),
        // Vertical camera tracking
        makeTrack("camera_position_y", "in_out_cubic", {
            {0, 0.0},
            {120, 10.0},
            {250, 10.0},
            {290, -15.0},
            {389, -30.0}
        }),
        // Camera dolly push (Z axis: -1050 to -820)
        makeTrack("camera_position_z", "in_out_cubic", {
            {0, -1050.0},
            {120, -990.0},
            {180, -960.0},
            {250, -940.0},
            {290, -900.0},
            {389, -820.0}
        }),
        // Dynamic Camera Roll (Z rotation) - Cinema / Steadicam organic banking!
        makeTrack("camera_rotation_z", "in_out_cubic", {
            {0, 1.6},
            {60, 0.0},
            {145, -1.4},
            {215, 0.3},
            {260, -0.8},
            {389, 0.0}
        }),
        // Camera Yaw (Y rotation)
        makeTrack("camera_rotation_y", "in_out_cubic", {
            {0, -2.5},
            {60, 0.0},
            {180, 1.8},
            {250, 0.0},
            {389, 0.0}
        }),
        // Dynamic FOV / Focal Length
        makeTrack("camera_fov_deg", "in_out_cubic", {
            {0, 46.0},
            {120, 44.5},
            {250, 44.0},
            {389, 42.0}
        })
    };

    Json layers = Json::array();

    // =========================================================================
    // 0. Archival Background: Deep Dark Slate Plate with Subtle Vignette
    // =========================================================================
    layers.push_back({
        {"id", "bg_slate"},
        {"type", "image"},
        {"asset", bgDark},
        {"size", {width, height}},
        {"position", {0, 0}},
        {"fit", "cover"},
        {"screen_space", true},
        {"start_frame", 0},
        {"duration_frames", durationFrames}
    });

    // Subtle warm film tint overlay (15% opacity)
    layers.push_back({
        {"id", "bg_grade"},
        {"type", "color"},
        {"color", {0.04, 0.035, 0.025, 0.15}},
        {"size", {width, height}},
        {"position", {0, 0}},
        {"screen_space", true},
        {"start_frame", 0},
        {"duration_frames", durationFrames}
    });

    // Elegant documentary chapter title plate (Top Center)
    std::vector<Track> chapterTracks = {
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {25, 0.95}, {230, 0.95}, {255, 0.0}})
    };
    layers.push_back({
        {"id", "chapter_title_plate"},
        {"type", "image"},
        {"asset", chapterPlate},
        {"size", {900, 60}},
        {"position", {0, -475}},
        {"fit", "contain"},
        {"screen_space", true},
        {"start_frame", 0},
        {"duration_frames", 260},
        {"animation", {{"tracks", serializeTracks(chapterTracks)}}}
    });

    // =========================================================================
    // 1. Alan Turing: Archival Photographic Compound Plate (3D Layer)
    // Moves and rolls organically with the 3D camera.
    // Portrait center is at Y = -160, so its bottom edge rests at Y = +175.
    // =========================================================================
    const int turingStart = 0;
    const int turingDur = 260;

    std::vector<Keyframe> turingPosX = {{0, 0.0}, {34, 0.0}, {145, 0.0}, {180, -450.0}, {235, -450.0}, {259, -450.0}};
    std::vector<Keyframe> turingPosY = {{0, -160.0}, {34, -160.0}, {145, -160.0}, {180, -160.0}, {235, -160.0}, {259, -160.0}};
    std::vector<Keyframe> turingPosZ = {{0, -260.0}, {34, 0.0}, {145, 0.0}, {180, 0.0}, {235, 0.0}, {259, 140.0}};

    std::vector<Keyframe> turingRotX = {{0, 0.0}, {34, 0.0}, {145, 0.0}, {180, 0.0}, {235, 0.0}, {259, 0.0}};
    std::vector<Keyframe> turingRotY = {{0, -18.0}, {34, 0.0}, {145, 0.0}, {180, -2.0}, {235, -2.0}, {259, -2.0}};
    std::vector<Keyframe> turingRotZ = {{0, 0.0}, {34, 0.0}, {145, 0.0}, {180, 0.0}, {235, 0.0}, {259, 0.0}};

    std::vector<Keyframe> turingScale = {{0, 0.88}, {34, 1.0}, {145, 1.0}, {180, 0.88}, {235, 0.88}, {259, 0.78}};
    std::vector<Keyframe> turingOpacity = {{0, 0.0}, {34, 1.0}, {145, 1.0}, {180, 1.0}, {235, 1.0}, {259, 0.0}};

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

    // Turing Soft Archival Shadow in 3D Space
    layers.push_back({
        {"id", "turing_shadow"},
        {"type", "color"},
        {"color", {0.0, 0.0, 0.0, 0.60}},
        {"size", {446, 676}},
        {"position", {6, -154, 0}},
        {"radius", 8},
        {"enable_3d", true},
        {"start_frame", turingStart},
        {"duration_frames", turingDur},
        {"animation", {{"tracks", serializeTracks(turing3dTracks)}}}
    });

    // Turing Archival Compound Print (Photo + Gold hairline + Name + Role)
    layers.push_back({
        {"id", "turing_compound_plate"},
        {"type", "image"},
        {"asset", turingCompound},
        {"size", {440, 670}},
        {"position", {0, -160, 0}},
        {"fit", "contain"},
        {"radius", 6},
        {"enable_3d", true},
        {"start_frame", turingStart},
        {"duration_frames", turingDur},
        {"animation", {{"tracks", serializeTracks(turing3dTracks)}}}
    });

    // =========================================================================
    // 2. Connected Historical Timeline Directly Below
    // Emerges cleanly under Turing at frame 65.
    // Turing's bottom is at Y = +175.
    // Connector pin drops from Y = +185 to +250.
    // Horizontal axis line at Y = +250.
    // Milestone card ("1940 | ENIGMA CIPHER CRACKED") at Y = +330.
    // Zero overlaps, perfect editorial breathing room!
    // =========================================================================
    const int timelineStart = 65;
    const int timelineDur = 195; // 65 -> 260

    // Timeline horizontal axis (thin 2px archival rule)
    layers.push_back({
        {"id", "timeline_axis_line"},
        {"type", "color"},
        {"color", {0.77, 0.66, 0.50, 0.55}},
        {"size", {1400, 2}},
        {"position", {0, 250}},
        {"screen_space", true},
        {"start_frame", timelineStart},
        {"duration_frames", timelineDur},
        {"animation", {
            {"tracks", serializeTracks({
                makeTrack("scale_x", "out_cubic", {{0, 0.05}, {26, 1.0}, {194, 1.0}}),
                makeTrack("opacity", "out_cubic", {{0, 0.0}, {16, 1.0}, {175, 1.0}, {194, 0.0}})
            })}
        }}
    });

    // Vertical gold connector pin dropping from Turing to the axis
    layers.push_back({
        {"id", "timeline_drop_pin"},
        {"type", "color"},
        {"color", {0.85, 0.74, 0.55, 0.85}},
        {"size", {2, 50}},
        {"position", {0, 225}},
        {"screen_space", true},
        {"start_frame", timelineStart},
        {"duration_frames", timelineDur},
        {"animation", {
            {"tracks", serializeTracks({
                makeTrack("scale_y", "out_cubic", {{0, 0.01}, {20, 1.0}, {194, 1.0}}),
                makeTrack("opacity", "out_cubic", {{0, 0.0}, {15, 0.85}, {175, 0.85}, {194, 0.0}})
            })}
        }}
    });

    // Milestone Historical Card Plate ("1940 | ENIGMA CIPHER CRACKED...")
    std::vector<Track> milestoneTracks = {
        makeTrack("position_y", "out_cubic", {{0, 15.0}, {22, 0.0}, {175, 0.0}, {194, 0.0}}),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {20, 1.0}, {175, 1.0}, {194, 0.0}})
    };
    layers.push_back({
        {"id", "timeline_milestone_plate"},
        {"type", "image"},
        {"asset", timelineMilestonePlate},
        {"size", {800, 120}},
        {"position", {0, 330}},
        {"fit", "contain"},
        {"screen_space", true},
        {"start_frame", timelineStart},
        {"duration_frames", timelineDur},
        {"animation", {{"tracks", serializeTracks(milestoneTracks)}}}
    });

    // =========================================================================
    // 3. Ada Lovelace (Second Archival Subject - Duo Partnership)
    // Base position is {0, -160, 0} matching Turing;
    // Animation track translates her from +530 to +450 with mirrored 3D depth and yaw.
    // =========================================================================
    const int adaStart = 150;
    const int adaDur = 110; // 150 -> 260

    std::vector<Keyframe> adaPosX = {{0, 530.0}, {32, 450.0}, {80, 450.0}, {109, 450.0}};
    std::vector<Keyframe> adaPosY = {{0, -160.0}, {32, -160.0}, {80, -160.0}, {109, -160.0}};
    std::vector<Keyframe> adaPosZ = {{0, -260.0}, {32, 0.0}, {80, 0.0}, {109, 140.0}};

    std::vector<Keyframe> adaRotX = {{0, 0.0}, {32, 0.0}, {80, 0.0}, {109, 0.0}};
    std::vector<Keyframe> adaRotY = {{0, 18.0}, {32, 2.0}, {80, 2.0}, {109, 2.0}};
    std::vector<Keyframe> adaRotZ = {{0, 0.0}, {32, 0.0}, {80, 0.0}, {109, 0.0}};

    std::vector<Keyframe> adaScale = {{0, 0.88}, {32, 0.88}, {80, 0.88}, {109, 0.78}};
    std::vector<Keyframe> adaOpacity = {{0, 0.0}, {32, 1.0}, {80, 1.0}, {109, 0.0}};

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

    // Ada Soft Archival Shadow in 3D Space
    layers.push_back({
        {"id", "ada_shadow"},
        {"type", "color"},
        {"color", {0.0, 0.0, 0.0, 0.60}},
        {"size", {446, 676}},
        {"position", {6, -154, 0}},
        {"radius", 8},
        {"enable_3d", true},
        {"start_frame", adaStart},
        {"duration_frames", adaDur},
        {"animation", {{"tracks", serializeTracks(ada3dTracks)}}}
    });

    // Ada Archival Compound Print (Portrait + Gold hairline + Name + Role)
    layers.push_back({
        {"id", "ada_compound_plate"},
        {"type", "image"},
        {"asset", adaCompound},
        {"size", {440, 670}},
        {"position", {0, -160, 0}},
        {"fit", "contain"},
        {"radius", 6},
        {"enable_3d", true},
        {"start_frame", adaStart},
        {"duration_frames", adaDur},
        {"animation", {{"tracks", serializeTracks(ada3dTracks)}}}
    });

    // Archival Synergy Banner ("FOUNDATIONAL COLLABORATION...")
    std::vector<Track> synergyTracks = {
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {18, 0.90}, {60, 0.90}, {74, 0.0}})
    };
    layers.push_back({
        {"id", "synergy_plate"},
        {"type", "image"},
        {"asset", synergyPlate},
        {"size", {900, 60}},
        {"position", {0, -425}},
        {"fit", "contain"},
        {"screen_space", true},
        {"start_frame", 175},
        {"duration_frames", 75},
        {"animation", {{"tracks", serializeTracks(synergyTracks)}}}
    });

    // =========================================================================
    // 4. Archival Tactical Map: London & Admiralty Command
    // Authentic dark London cartography plate.
    // Gold rotating reticle over central London / Westminster, glowing beacon dot,
    // and lower-left editorial dispatch metadata plate.
    // Westminster / London center: X = -10, Y = +65 (in canvas centered coordinates)
    // =========================================================================
    const int mapStart = 250;
    const int mapDur = 140; // 250 -> 390

    // Full Screen Authentic London Tactical Basemap Plate
    std::vector<Track> mapPlateTracks = {
        makeTrack("position_x", "out_cubic", {{0, 0.0}, {30, 0.0}, {139, 0.0}}),
        makeTrack("position_y", "out_cubic", {{0, 20.0}, {30, 0.0}, {139, -30.0}}),
        makeTrack("scale", "out_cubic", {{0, 1.02}, {30, 1.10}, {139, 1.25}}),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {26, 1.0}, {139, 1.0}})
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
        {"animation", {{"tracks", serializeTracks(mapPlateTracks)}}}
    });

    // Map Archival Warm Tint & Contrast Boost
    layers.push_back({
        {"id", "map_warm_grade"},
        {"type", "color"},
        {"color", {0.05, 0.04, 0.03, 0.25}},
        {"size", {width, height}},
        {"position", {0, 0}},
        {"screen_space", true},
        {"start_frame", mapStart},
        {"duration_frames", mapDur},
        {"animation", {
            {"tracks", serializeTracks({
                makeTrack("opacity", "out_cubic", {{0, 0.0}, {26, 0.25}, {139, 0.25}})
            })}
        }}
    });

    // Delicate Military Tactical Gold Reticle centered over Westminster/London
    // Position on canvas: Westminster is at (-10, +65)
    std::vector<Track> reticleTracks = {
        makeTrack("rotation_z", "out_cubic", {{0, -45.0}, {35, 0.0}, {129, 35.0}}),
        makeTrack("scale", "out_cubic", {{0, 1.5}, {28, 1.0}, {129, 1.06}}),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {18, 0.95}, {129, 0.95}})
    };
    layers.push_back({
        {"id", "map_reticle"},
        {"type", "image"},
        {"asset", mapReticle},
        {"size", {140, 140}},
        {"position", {-10, 65}},
        {"fit", "contain"},
        {"start_frame", mapStart + 10},
        {"duration_frames", mapDur - 10},
        {"animation", {{"tracks", serializeTracks(reticleTracks)}}}
    });

    // Pulsating Golden Target Beacon Dot (Centered at reticle: -10, 65)
    std::vector<Track> beaconTracks = {
        makeTrack("scale", "out_cubic", {
            {0, 0.0}, {15, 1.4}, {30, 1.0}, {45, 1.3}, {60, 1.0}, {124, 1.2}
        }),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {15, 1.0}, {124, 1.0}})
    };
    layers.push_back({
        {"id", "map_beacon_dot"},
        {"type", "image"},
        {"asset", mapBeacon},
        {"size", {48, 48}},
        {"position", {-10, 65}},
        {"fit", "contain"},
        {"start_frame", mapStart + 15},
        {"duration_frames", mapDur - 15},
        {"animation", {{"tracks", serializeTracks(beaconTracks)}}}
    });

    // Lower-Left Editorial Metadata Plate (London, Admiralty, Coordinates)
    // Centered at X = -560, Y = +390 (cleanly in the lower left corner)
    std::vector<Track> mapInfoTracks = {
        makeTrack("position_x", "out_cubic", {{0, -40.0}, {26, 0.0}, {119, 0.0}}),
        makeTrack("opacity", "out_cubic", {{0, 0.0}, {20, 1.0}, {119, 1.0}})
    };
    layers.push_back({
        {"id", "map_info_plate"},
        {"type", "image"},
        {"asset", mapInfoPlate},
        {"size", {700, 140}},
        {"position", {-560, 390}},
        {"fit", "contain"},
        {"screen_space", true},
        {"start_frame", mapStart + 20},
        {"duration_frames", mapDur - 20},
        {"animation", {{"tracks", serializeTracks(mapInfoTracks)}}}
    });

    // Assemble final render-plan.v3
    Json plan = {
        {"schema", "chronon.render-plan.v3"},
        {"version", 3},
        {"job_id", "cinematic_documentary_cpp"},
        {"canvas", {
            {"width", width},
            {"height", height},
            {"fps_num", fps},
            {"fps_den", 1},
            {"duration_frames", durationFrames}
        }},
        {"camera", {
            {"type", "perspective"},
            {"position", {0.0, 0.0, -1050.0}},
            {"rotation_deg", {0.0, -2.5, 1.6}},
            {"fov_deg", 46.0},
            {"near", 1.0},
            {"far", 10000.0},
            {"zoom", 1.0}
        }},
        {"camera_animation", {
            {"tracks", serializeTracks(cameraTracks)}
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

    std::cout << "[C++ Cinema] Plan written to: " << outPlanPath
              << " (" << layers.size() << " layers, " << durationFrames << " frames)\n";

    if (doRender) {
        std::cout << "[C++ Cinema] Rendering via Chronon3D CLI...\n";
        std::string renderCmd = "./Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli render "
                                "--plan " + outPlanPath + " "
                                "-o " + outMp4Path + " "
                                "--assets-root /home/pierone/src/go-master/projects/Pyt/VeloxEditing/Chronon3d";
        int ret = std::system(renderCmd.c_str());
        if (ret != 0) {
            std::cerr << "[C++ Cinema] Render failed (exit code " << ret << ")\n";
            return 1;
        }
        std::cout << "[C++ Cinema] Render complete! MP4 saved to: " << outMp4Path << "\n";

        if (doUpload) {
            std::cout << "[C++ Cinema] Uploading to Google Drive (" << driveFolderId << ")...\n";
            std::string uploadCmd = "./RenderingGen/bin/drive-upload "
                                    "-credentials /home/pierone/.config/velox/credentials.json "
                                    "-token /home/pierone/.config/velox/token.json "
                                    "-folder " + driveFolderId + " "
                                    "-file " + outMp4Path + " "
                                    "-name cinematic_documentary_cpp.mp4";
            int upRet = std::system(uploadCmd.c_str());
            if (upRet != 0) {
                std::cerr << "[C++ Cinema] Drive upload failed (exit code " << upRet << ")\n";
                return 1;
            }
            std::cout << "[C++ Cinema] Successfully uploaded to Drive!\n";
        }
    }

    return 0;
}
