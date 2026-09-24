#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using Json = nlohmann::json;

struct Key {
    int frame;
    std::vector<float> value;
    Key(int at, float scalar) : frame(at), value{scalar} {}
    Key(int at, std::initializer_list<float> vector) : frame(at), value(vector) {}
};
struct Track {
    std::string property;
    std::string easing;
    std::vector<Key> keys;
};

Json makeTrack(const Track& track) {
    Json keys = Json::array();
    for (const auto& key : track.keys) {
        const Json value = key.value.size() == 1 ? Json(key.value.front()) : Json(key.value);
        keys.push_back({{"frame", key.frame}, {"value", value}});
    }
    return {{"property", track.property}, {"easing", track.easing}, {"keyframes", keys}};
}

Json tracks(const std::vector<Track>& input) {
    Json result = Json::array();
    for (const auto& track : input) result.push_back(makeTrack(track));
    return result;
}

struct Animation {
    std::string id;
    std::string title;
    std::vector<Track> image;
    std::vector<Track> camera;
};

int main(int argc, char** argv) try {
    if (argc != 2) throw std::runtime_error("usage: generate_image_25d_clean_v1 <output-directory>");
    const std::filesystem::path outDir = argv[1];
    std::filesystem::create_directories(outDir);

    const std::vector<Animation> animations = {
        {"image_25d_depth_float_in", "Depth Float In", {
            {"position_z", "out_cubic", {{0, 400}, {55, 0}, {149, 0}}},
            {"opacity", "out_cubic", {{0, 0}, {24, 1}, {149, 1}}},
            {"scale", "out_cubic", {{0, 1.06f}, {55, 1}, {149, 1}}}}, {}},
        {"image_25d_yaw_flip_in", "Yaw Flip In", {
            {"rotation_y", "out_cubic", {{0, -18}, {48, 0}, {149, 0}}},
            {"position_z", "out_cubic", {{0, 120}, {48, 0}, {149, 0}}},
            {"opacity", "out_cubic", {{0, 0}, {18, 1}, {149, 1}}}}, {}},
        {"image_25d_pitch_lift", "Pitch Lift", {
            {"rotation_x", "out_cubic", {{0, 12}, {48, 0}, {149, 0}}},
            {"position_y", "out_cubic", {{0, 60}, {48, 0}, {149, 0}}},
            {"scale", "out_cubic", {{0, 0.92f}, {48, 1}, {149, 1}}}}, {}},
        {"image_25d_pop_z_bounce", "Pop Z Bounce", {
            {"position_z", "out_cubic", {{0, -80}, {38, 0}, {149, 0}}},
            {"scale", "out_back", {{0, 0.70f}, {28, 1.04f}, {48, 1}, {149, 1}}},
            {"opacity", "out_cubic", {{0, 0}, {10, 1}, {149, 1}}}}, {}},
        {"image_25d_swipe_3d", "Swipe 3D", {
            {"position_x", "out_cubic", {{0, 320}, {42, 0}, {149, 0}}},
            {"rotation_y", "out_cubic", {{0, 14}, {42, 0}, {149, 0}}},
            {"opacity", "out_cubic", {{0, 0}, {12, 1}, {149, 1}}}}, {}},
        {"image_25d_card_swing", "Card Swing", {
            {"rotation", "in_out_cubic", {{0, {0, -10, -2}}, {36, {0, 6, -1}}, {72, {0, 0, 0}}, {149, {0, 0, 0}}}},
            {"position_z", "out_cubic", {{0, 160}, {52, 0}, {149, 0}}}}, {}},
        {"image_25d_dolly_settle", "Dolly Settle", {
            {"rotation_y", "out_cubic", {{0, -4}, {55, 0}, {149, 0}}},
            {"scale", "out_cubic", {{0, 0.94f}, {55, 1}, {149, 1}}},
            {"opacity", "out_cubic", {{0, 0}, {20, 1}, {149, 1}}}}, {
            {"camera_position_z", "in_out_cubic", {{0, -1400}, {55, -1050}, {149, -1050}}},
            {"camera_rotation_y", "in_out_cubic", {{0, -4}, {55, 0}, {149, 0}}}}},
        {"image_25d_orbit_arc", "Orbit Arc", {
            {"position_z", "out_cubic", {{0, 150}, {32, 150}, {149, 150}}},
            {"opacity", "out_cubic", {{0, 0}, {20, 1}, {149, 1}}}}, {
            {"camera_position_x", "in_out_cubic", {{0, 870}, {75, 1050}, {149, 1050}}},
            {"camera_rotation_y", "in_out_cubic", {{0, -3.2f}, {75, 3.2f}, {149, 3.2f}}}}},
        {"image_25d_counter_tilt", "Counter Tilt", {
            {"rotation_x", "out_cubic", {{0, -8}, {50, 0}, {149, 0}}},
            {"opacity", "out_cubic", {{0, 0}, {18, 1}, {149, 1}}}}, {
            {"camera_rotation_x", "out_cubic", {{0, 1.5f}, {50, 0}, {149, 0}}}}},
        {"image_25d_dolly_breath", "Dolly Breath", {
            {"scale", "in_out_sine", {{0, 1}, {55, 1.03f}, {100, 1.03f}, {149, 1}}},
            {"opacity", "out_cubic", {{0, 0}, {20, 1}, {149, 1}}}}, {
            {"camera_position_z", "in_out_cubic", {{0, -1400}, {55, -1160}, {100, -1160}, {149, -1400}}},
            {"camera_fov_deg", "in_out_cubic", {{0, 55}, {55, 52}, {100, 52}, {149, 55}}}}},
        {"image_25d_parallax_drift", "Parallax Drift", {
            {"position_z", "out_cubic", {{0, 220}, {30, 0}, {112, 0}, {149, 70}}},
            {"scale", "out_cubic", {{0, 0.94f}, {30, 1}, {112, 1}, {149, 0.96f}}},
            {"opacity", "out_cubic", {{0, 0}, {20, 1}, {124, 1}, {149, 0}}}}, {
            {"camera_position_z", "in_out_cubic", {{0, -1400}, {30, -1120}, {112, -1120}, {149, -1120}}},
            {"camera_position_x", "in_out_cubic", {{0, 960}, {48, 900}, {108, 1020}, {149, 960}}}}},
        {"image_25d_hero_pull_exit", "Hero Pull Exit", {
            {"position_z", "out_cubic", {{0, -80}, {35, 0}, {105, 0}, {149, 90}}},
            {"scale", "out_back", {{0, 0.72f}, {35, 1}, {105, 1}, {149, 0.94f}}},
            {"opacity", "out_cubic", {{0, 0}, {18, 1}, {112, 1}, {149, 0}}}}, {
            {"camera_position_z", "in_out_cubic", {{0, -1400}, {35, -1050}, {105, -1050}, {149, -1200}}}}}
    };

    for (const auto& animation : animations) {
        const std::string filename = animation.id + ".plan.json";
        const std::string video = "out/image_25d_clean_v1/videos/" + animation.id + ".mp4";
        Json root = {
            {"schema", "chronon.render-plan.v2"}, {"version", 2},
            {"job_id", "chronontemplate_" + animation.id},
            {"canvas", {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1}, {"duration_frames", 150}}},
            {"layers", Json::array({
                Json{{"id", "background"}, {"type", "color"}, {"color", {0.035, 0.055, 0.1, 1.0}},
                     {"size", {1920, 1080}}, {"start_frame", 0}, {"duration_frames", 150}, {"screen_space", true}},
                Json{{"id", "product_image"}, {"type", "image"}, {"asset", "assets/test/square_bottle_test.png"},
                     {"size", {940, 940}}, {"position", {960, 540}}, {"fit", "contain"}, {"radius", 0},
                     {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", 150},
                     {"animation", {{"tracks", tracks(animation.image)}}}}
            })},
            {"camera", {{"type", "perspective"}, {"position", {960.0, 540.0, -1400.0}},
                        {"rotation_deg", {0.0, 0.0, 0.0}}, {"fov_deg", 55.0}, {"near", 1.0}, {"far", 5000.0}, {"zoom", 1.0}}},
            {"output", {{"path", video}, {"format", "mp4"}, {"codec", "h264"}}}
        };
        if (!animation.camera.empty()) root["camera_animation"] = {{"tracks", tracks(animation.camera)}};
        std::ofstream output(outDir / filename);
        if (!output) throw std::runtime_error("cannot write " + (outDir / filename).string());
        output << root.dump(2) << '\n';
        std::cout << animation.id << " — " << animation.title << '\n';
    }
}
catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
