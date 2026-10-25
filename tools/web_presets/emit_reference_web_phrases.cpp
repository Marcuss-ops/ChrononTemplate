// Recreate the supplied highlighted-web passages as editable Chronon render
// plans. The screenshots are references only; no screenshot is used as a plate.
#include "chronontemplate/camera_roll/ResolvedCameraSamples.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
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
constexpr int kFrames = 210;
constexpr const char* kInk = "#141414";
constexpr const char* kBody = "#777A7C";
constexpr const char* kYellow = "#F0F500";
constexpr float kRunGap = 10.f;

struct PassageLine {
    std::string before;
    std::string phrase;
    std::string after;
    float y{};
    float fontSize{};
};

struct Page {
    std::string id;
    float fontSize{38.f};
    std::vector<PassageLine> lines;
    bool doubleHighlightCameraMove{};
};

float glyphUnits(const std::string& text) {
    float units = 0.f;
    for (const unsigned char c : text) {
        if (c == ' ') units += .28f;
        else if (c == 'i' || c == 'l' || c == 'I' || c == '!' || c == '.' || c == ',' || c == ':') units += .29f;
        else if (c == 'm' || c == 'w' || c == 'M' || c == 'W') units += .78f;
        else if (c >= 'A' && c <= 'Z') units += .64f;
        else units += .52f;
    }
    return units;
}

float widthOf(const std::string& text, float size) {
    return glyphUnits(text) * size;
}

Json color(const std::string& hex, float alpha = 1.f) {
    const auto byte = [&](std::size_t offset) {
        return static_cast<float>(std::stoi(hex.substr(offset, 2), nullptr, 16)) / 255.f;
    };
    return Json::array({byte(1), byte(3), byte(5), alpha});
}

Json track(const std::string& property, const Json& keys, const std::string& easing = "out_cubic") {
    return {{"property", property}, {"easing", easing}, {"keyframes", keys}};
}

Json rect(const std::string& id, float x, float y, float w, float h,
          const std::string& fill, int entranceFrame = 0) {
    const float center = x + w * .5f;
    Json layer = {{"id", id}, {"type", "shape"}, {"enable_3d", true},
        {"size", Json::array({w, h})}, {"position", Json::array({center, kHeight - y - h * .5f, 0.f})},
        {"shape", {{"type", "rect"}, {"fill", color(fill)}}},
        {"start_frame", 0}, {"duration_frames", kFrames}};
    Json tracks = Json::array();
    tracks.push_back(track("opacity", Json::array({
        {{"frame", 0}, {"value", 0.0}},
        {{"frame", entranceFrame}, {"value", 0.0}},
        {{"frame", entranceFrame + 18}, {"value", 1.0}}})));
    tracks.push_back(track("scale_x", Json::array({
        {{"frame", 0}, {"value", .001}},
        {{"frame", entranceFrame}, {"value", .001}},
        {{"frame", entranceFrame + 26}, {"value", 1.0}}}), "in_out_cubic"));
    tracks.push_back(track("position_x", Json::array({
        {{"frame", 0}, {"value", -w * .5f}},
        {{"frame", entranceFrame}, {"value", -w * .5f}},
        {{"frame", entranceFrame + 26}, {"value", 0.0}}}), "in_out_cubic"));
    layer["animation"] = {{"tracks", std::move(tracks)}};
    return layer;
}

Json textLayer(const std::string& id, const std::string& text, float left, float y,
               float size, const std::string& fill, bool bold, int slot) {
    const float w = std::max(90.f, widthOf(text, size) * 1.32f + 48.f);
    const float h = size * 1.65f;
    Json layer = {{"id", id}, {"type", "text"}, {"text", text},
        {"size", Json::array({w, h})},
        {"position", Json::array({left + widthOf(text, size) * .5f,
                                  kHeight - y - h * .5f, 0.f})},
        {"enable_3d", true}, {"style", {{"font", bold ? "assets/fonts/Inter-Bold.ttf" : "assets/fonts/Inter-Regular.ttf"},
            {"font_size", size}, {"fill", fill}}},
        {"start_frame", 0}, {"duration_frames", kFrames}};
    const int begin = 4 + slot * 3;
    Json tracks = Json::array();
    tracks.push_back(track("opacity", Json::array({
        {{"frame", 0}, {"value", 0.0}},
        {{"frame", begin}, {"value", 0.0}},
        {{"frame", begin + 24}, {"value", 1.0}}})));
    tracks.push_back(track("position_y", Json::array({
        {{"frame", 0}, {"value", 18.0}},
        {{"frame", begin}, {"value", 18.0}},
        {{"frame", begin + 24}, {"value", 0.0}}})));
    layer["animation"] = {{"tracks", std::move(tracks)}};
    return layer;
}

void addPlainLine(Json& layers, const Page& p, std::size_t index,
                  const PassageLine& line, int slot) {
    const float size = line.fontSize > 0.f ? line.fontSize : p.fontSize;
    const std::string& text = line.before;
    const float w = widthOf(text, size);
    const float left = (kWidth - w) * .5f;
    layers.push_back(textLayer(p.id + "_line_" + std::to_string(index), text,
                               left, line.y, size, kBody, false, slot));
}

void addHighlightedLine(Json& layers, const Page& p, std::size_t index,
                        const PassageLine& line, int slot) {
    const float size = line.fontSize > 0.f ? line.fontSize : p.fontSize;
    const float beforeW = widthOf(line.before, size);
    const float phraseW = widthOf(line.phrase, size);
    const float afterW = widthOf(line.after, size);
    const float gapBefore = line.before.empty() ? 0.f : kRunGap;
    const float gapAfter = line.after.empty() ? 0.f : kRunGap;
    const float totalW = beforeW + phraseW + afterW + gapBefore + gapAfter;
    const float x = std::max(130.f, (kWidth - totalW) * .5f);
    const float baselineLeft = x;
    const float highlightLeft = x + beforeW + gapBefore;
    const float textTop = line.y;

    if (!line.before.empty())
        layers.push_back(textLayer(p.id + "_pre_" + std::to_string(index), line.before,
                                   baselineLeft, textTop, size, kBody, false, slot));
    layers.push_back(rect(p.id + "_marker_" + std::to_string(index),
                          highlightLeft - 5.f, textTop + size * .12f,
                          phraseW + 12.f, size * 1.24f, kYellow, 14 + slot * 4));
    layers.push_back(textLayer(p.id + "_phrase_" + std::to_string(index), line.phrase,
                               highlightLeft, textTop, size, kInk, true, slot + 2));
    if (!line.after.empty())
        layers.push_back(textLayer(p.id + "_post_" + std::to_string(index), line.after,
                                   highlightLeft + phraseW + gapAfter, textTop, size, kBody, false, slot + 1));
}

Json makePlan(const Page& p) {
    Json layers = Json::array();
    layers.push_back({{"id", p.id + "_paper"}, {"type", "color"}, {"screen_space", true},
        {"color", color("#F0F0EE")}, {"size", Json::array({kWidth, kHeight})},
        {"start_frame", 0}, {"duration_frames", kFrames}});
    std::size_t hi = 0;
    int slot = 0;
    for (const auto& line : p.lines) {
        if (line.phrase.empty()) addPlainLine(layers, p, hi, line, slot++);
        else addHighlightedLine(layers, p, hi, line, slot++);
        ++hi;
    }

    Json plan = {{"schema", "chronon.render-plan.v3"}, {"version", 3},
        {"job_id", p.id},
        {"canvas", {{"width", kWidth}, {"height", kHeight}, {"fps_num", 30},
                     {"fps_den", 1}, {"duration_frames", kFrames}}},
        {"camera", {{"type", "perspective"}, {"position", Json::array({0, 0, -1320})},
            {"rotation_deg", Json::array({0, 0, 0})}, {"fov_deg", 50},
            {"near", 1}, {"far", 10000}, {"zoom", 1}}},
        {"layers", std::move(layers)},
        {"output", {{"codec", "h264"}, {"format", "mp4"}, {"path", p.id + ".mp4"}}}};
    if (p.doubleHighlightCameraMove) {
        // The complete passage appears first. The camera then pushes to the
        // first marker, holds, and glides to the second marker.
        const auto centerX = [](const PassageLine& line) {
            const float beforeW = widthOf(line.before, line.fontSize);
            const float phraseW = widthOf(line.phrase, line.fontSize);
            const float totalW = beforeW + phraseW + widthOf(line.after, line.fontSize)
                + (line.before.empty() ? 0.f : kRunGap) + (line.after.empty() ? 0.f : kRunGap);
            return std::max(130.f, (kWidth - totalW) * .5f) + beforeW
                + (line.before.empty() ? 0.f : kRunGap) + phraseW * .5f - kWidth * .5f;
        };
        const auto centerY = [](const PassageLine& line) {
            return static_cast<float>(kHeight) - line.y - line.fontSize * .825f - kHeight * .5f;
        };
        const auto trackKeys = [&](float first, float second) {
            return Json::array({{{"frame", 0}, {"value", 0.0}}, {{"frame", 65}, {"value", 0.0}},
                {{"frame", 108}, {"value", first}}, {{"frame", 128}, {"value", first}},
                {{"frame", 168}, {"value", second}}, {{"frame", 209}, {"value", second}}});
        };
        const auto channel = [](const char* name, const Json& keys) {
            return Json{{"channel", name}, {"easing", "out_cubic"}, {"keyframes", keys}};
        };
        Json cameraChannels = Json::array();
        cameraChannels.push_back(channel("position_x", trackKeys(centerX(p.lines[0]), centerX(p.lines[2]))));
        cameraChannels.push_back(channel("position_y", trackKeys(centerY(p.lines[0]), centerY(p.lines[2]))));
        cameraChannels.push_back(
            channel("position_z", Json::array({{{"frame", 0}, {"value", -1320.0}},
                {{"frame", 65}, {"value", -1320.0}}, {{"frame", 108}, {"value", -760.0}},
                {{"frame", 128}, {"value", -760.0}}, {{"frame", 168}, {"value", -760.0}},
                {{"frame", 209}, {"value", -760.0}}})));
        // camera_animation is retired by the render-plan contract: lower the
        // authored move to resolved per-frame camera_samples through the
        // shared CM3D baker instead of shipping track intent.
        chronontemplate::camera_roll::attachResolvedCameraSamples(
            plan, plan.at("camera"), cameraChannels, 30.f,
            static_cast<std::size_t>(kFrames));
    }
    return plan;
}

void writePage(const fs::path& out, const Page& p) {
    const fs::path path = out / (p.id + ".plan.json");
    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    if (!file || !(file << makePlan(p).dump(2) << '\n'))
        throw std::runtime_error("could not write " + path.string());
    std::cout << "Wrote " << path << '\n';
}
}

int main(int argc, char** argv) try {
    const fs::path out = argc > 1 ? argv[1] : "ChrononTemplate/out/web_long_short_v2/recreated_phrases/plans";
    fs::create_directories(out);

    Page kaycee{"web_phrase_kaycee_question", 58.f, {}};
    kaycee.lines.push_back({"", "Is it possible that Kaycee did not exist", "", 458.f, 58.f});
    writePage(out, kaycee);

    Page mmsZoom{"web_phrase_mms_testimonies_zoom", 38.f, {}};
    mmsZoom.lines = {
        {"The Grenons ", "sold tens of thousands of bottles of MMS", " nationwide,", 320.f, 38.f},
        {"including to consumers throughout South Florida.", "", "", 394.f, 38.f},
        {"And here are the ", "Weekly Testimonies", " from people who used MMS.", 468.f, 38.f},
        {"MMS recently completely healed an abscess of the gum that I had had", "", "", 542.f, 38.f},
        {"for over 5 years with only three days of treatment and two days of MMS", "", "", 616.f, 38.f},
        {"mouthwash.", "", "", 690.f, 38.f}};
    writePage(out, mmsZoom);

    Page mmsDouble{"web_phrase_mms_double_highlight_camera", 38.f, mmsZoom.lines, true};
    writePage(out, mmsDouble);

    Page mmsFull{"web_phrase_mms_testimonies_fullpage", 29.f, {}};
    mmsFull.lines = {
        {"The Grenons ", "sold tens of thousands of bottles of MMS", " nationwide,", 330.f, 29.f},
        {"including to consumers throughout South Florida.", "", "", 391.f, 29.f},
        {"And here are the ", "Weekly Testimonies", " from people who used MMS.", 452.f, 29.f},
        {"MMS recently completely healed an abscess of the gum that I had had", "", "", 513.f, 29.f},
        {"for over 5 years with only three days of treatment and two days of MMS", "", "", 574.f, 29.f},
        {"mouthwash.", "", "", 635.f, 29.f}};
    writePage(out, mmsFull);

    Page price{"web_phrase_price_450", 54.f, {}};
    price.lines = {
        {"producers paid ", "$450", " to be ordained", 404.f, 54.f},
        {"and training seminar at a Houston hotel.", "", "", 500.f, 54.f}};
    writePage(out, price);
    return 0;
} catch (const std::exception& e) {
    std::cerr << "emit_reference_web_phrases: " << e.what() << '\n';
    return 1;
}
