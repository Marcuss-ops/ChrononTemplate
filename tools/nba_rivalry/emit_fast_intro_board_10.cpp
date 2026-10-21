// Ten-player corkboard Fast Intro. Photo cards and camera motion stay editable
// native layers in a Chronon render plan; no full-frame plate is precomposited.
#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using Json = nlohmann::json;

namespace {
constexpr int kWidth = 1920;
constexpr int kHeight = 1080;
constexpr int kFps = 30;
constexpr int kFrames = 900;
constexpr float kCardWidth = 360.f;
constexpr float kCardHeight = 482.f;
constexpr float kNoteWidth = 130.f;
constexpr float kNoteHeight = 98.f;

struct Player {
    std::string id;
    std::string name;
    float x;
    float y;
    float tilt;
};

Json key(int frame, double value) {
    return {{"frame", frame}, {"value", value}};
}

Json track(const std::string& property, const Json& keyframes,
           const std::string& easing = "in_out_cubic") {
    return {{"property", property}, {"easing", easing}, {"keyframes", keyframes}};
}

Json rect(const std::string& id, float x, float y, float z, float w, float h,
          const Json& fill, float tilt) {
    return {{"id", id}, {"type", "shape"}, {"enable_3d", true},
        // Shape primitives are authored in canvas-origin coordinates; photo
        // images and the camera use the centered scene coordinates above.
        {"size", {w, h}}, {"position", {x + kWidth * .5f, y + kHeight * .5f, z}},
        {"shape", {{"type", "rect"}, {"fill", fill}}},
        {"start_frame", 0}, {"duration_frames", kFrames},
        {"animation", {{"tracks", Json::array({
            track("rotation_z", Json::array({key(0, tilt), key(kFrames - 1, tilt)}), "linear")})}}}};
}

Json makePlan() {
    const std::vector<Player> players{
        {"paul_pierce", "Paul Pierce", -840.f, 280.f, -5.5f},
        {"lebron_james", "LeBron James", -420.f, 340.f, 4.0f},
        {"kevin_garnett", "Kevin Garnett", 0.f, 260.f, -2.5f},
        {"dwyane_wade", "Dwyane Wade", 420.f, 320.f, 5.0f},
        {"ray_allen", "Ray Allen", 840.f, 290.f, -4.0f},
        {"chris_bosh", "Chris Bosh", -840.f, -290.f, 3.5f},
        {"rajon_rondo", "Rajon Rondo", -420.f, -330.f, -5.0f},
        {"udonis_haslem", "Udonis Haslem", 0.f, -250.f, 2.0f},
        {"kendrick_perkins", "Kendrick Perkins", 420.f, -345.f, -3.0f},
        {"shane_battier", "Shane Battier", 840.f, -285.f, 4.5f},
    };
    const std::vector<float> cameraYaw{0.f, -1.2f, 1.2f, -0.8f, 1.4f,
                                       -1.0f, 1.1f, -1.3f, 0.8f, 0.f};

    Json layers = Json::array();
    layers.push_back({{"id", "corkboard_background"}, {"type", "image"},
        {"asset", "assets/nba_rivalry/web/corkboard_bg.png"},
        {"position", {0, 0}}, {"size", {kWidth, kHeight}}, {"fit", "cover"},
        {"screen_space", true}, {"start_frame", 0}, {"duration_frames", kFrames}});

    Json cameraX = Json::array({key(0, 0), key(44, 0)});
    Json cameraY = Json::array({key(0, 0), key(44, 0)});
    Json cameraZ = Json::array({key(0, -1450), key(44, -1450)});
    Json cameraYawTrack = Json::array({key(0, 0), key(44, 0)});
    for (std::size_t i = 0; i < players.size(); ++i) {
        const auto& player = players[i];
        const int number = static_cast<int>(i) + 1;
        const float noteX = player.x - 108.f;
        const float noteY = player.y - 135.f;
        const std::string base = "assets/nba_rivalry/cards/" + player.id + ".png";

        layers.push_back(rect(player.id + "_shadow", player.x + 10.f, player.y - 12.f,
            0.f, kCardWidth + 14.f, kCardHeight + 16.f, {0.055f, 0.039f, 0.027f, 0.72f}, player.tilt));
        layers.push_back({{"id", player.id + "_photo_card"}, {"type", "image"},
            {"asset", base}, {"position", {player.x, player.y, 4.f}},
            {"size", {kCardWidth, kCardHeight}}, {"fit", "contain"}, {"enable_3d", true},
            {"start_frame", 0}, {"duration_frames", kFrames},
            {"animation", {{"tracks", Json::array({
                track("rotation_z", Json::array({key(0, player.tilt), key(kFrames - 1, player.tilt)}), "linear")})}}}});

        layers.push_back({{"id", player.id + "_numbered_note"}, {"type", "image"},
            {"asset", "assets/nba_rivalry/numbered_notes/number_" + std::to_string(number) + ".png"},
            {"position", {noteX, noteY, -8.f}}, {"size", {kNoteWidth, kNoteHeight}},
            {"fit", "contain"}, {"enable_3d", true}, {"start_frame", 0},
            {"duration_frames", kFrames}, {"animation", {{"tracks", Json::array({
                track("rotation_z", Json::array({key(0, player.tilt), key(kFrames - 1, player.tilt)}), "linear")})}}}});

        const int moveStart = 45 + static_cast<int>(i) * 87;
        const int arrive = moveStart + 42;
        cameraX.push_back(key(arrive, player.x));
        cameraY.push_back(key(arrive, player.y));
        cameraZ.push_back(key(arrive, -660));
        cameraYawTrack.push_back(key(arrive, cameraYaw[i]));
        if (i + 1 < players.size()) {
            const int nextMove = arrive + 45;
            cameraX.push_back(key(nextMove, player.x));
            cameraY.push_back(key(nextMove, player.y));
            cameraZ.push_back(key(nextMove, -660));
            cameraYawTrack.push_back(key(nextMove, cameraYaw[i]));
        }
    }

    return {{"schema", "chronon.render-plan.v3"}, {"version", 3},
        {"job_id", "nba_fast_intro_board_10"},
        {"canvas", {{"width", kWidth}, {"height", kHeight}, {"fps_num", kFps},
                     {"fps_den", 1}, {"duration_frames", kFrames}}},
        {"camera", {{"type", "perspective"}, {"position", {0, 0, -1450}},
            {"rotation_deg", {0, 0, 0}}, {"fov_deg", 53.14}, {"near", 1},
            {"far", 10000}, {"zoom", 1}}},
        {"camera_animation", {{"tracks", Json::array({
            track("camera_position_x", cameraX), track("camera_position_y", cameraY),
            track("camera_position_z", cameraZ), track("camera_rotation_y", cameraYawTrack)})}}},
        {"layers", std::move(layers)},
        {"output", {{"path", "nba_fast_intro_board_10.mp4"}, {"format", "mp4"}, {"codec", "h264"}}}};
}
}

int main(int argc, char** argv) try {
    const fs::path out = argc > 1 ? fs::path(argv[1])
        : fs::path("ChrononTemplate/out/nba_rivalry/nba_fast_intro_board_10.plan.json");
    fs::create_directories(out.parent_path());
    std::ofstream file(out, std::ios::binary | std::ios::trunc);
    if (!file || !(file << makePlan().dump(2) << '\n'))
        throw std::runtime_error("could not write " + out.string());
    std::cout << "Wrote " << out << " (10 photos, 30 s, 30 fps)\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << "emit_fast_intro_board_10: " << error.what() << '\n';
    return 1;
}
