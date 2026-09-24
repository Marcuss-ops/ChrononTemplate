// ChrononTemplate — Classic important-phrase plan emitter.
//
// This tool lowers the C++-owned Classic pack (ImportantPhrasePack) to the
// Chronon3D render-plan contract, one plan per animation. It is deliberately
// thin: the look and the fifteen animations live in
// include/chronontemplate/ImportantPhrasePack.hpp and this program only
// projects them — extended keyframes (hold + synthesised exit) and the lowered
// selector window, the same canonical lowering emit_native_phrase_pack.py
// applies to catalog motions.
//
// Validation is fail-closed: a keyframe list that does not start at frame 0,
// a non-monotonic one, or an animation with neither layer tracks nor text
// animators aborts the emit instead of shipping a plan the renderer would
// reject halfway through a job.
//
// Usage:
//   chronontemplate_emit_important_phrase_plans <output-directory>

#include <nlohmann/json.hpp>

#include "chronontemplate/ClassicPhrasePack.hpp"
#include "chronontemplate/ImportantPhrasePack.hpp"
#include "chronontemplate/TypewriterPhrasePack.hpp"
#include "chronontemplate/ApplePhrasePack.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

    using json = nlohmann::ordered_json;
    using chronontemplate::ClassicPhraseAnimation;
    using chronontemplate::ClassicPhraseStyle;
    using chronontemplate::PhraseAnimationDefinition;
    using chronontemplate::PhraseKeyframe;
    using chronontemplate::PhraseSelector;
    using chronontemplate::PhraseTextAnimator;
    using chronontemplate::PhraseTrack;

    constexpr int kWidth = 1920;
    constexpr int kHeight = 1080;
    constexpr int kFps = 30;
    constexpr int kDurationFrames = 150;// 5 s showcase timeline
    /// The last nine frames are the synthesised exit.
    constexpr int kExitFrames = 9;

    [[noreturn]] void fail(const std::string& message) {
        throw std::runtime_error("emit_important_phrase_classic: " + message);
    }

    void validateTrack(const PhraseTrack& track, const std::string& where) {
        if (track.property.empty()) fail(where + " needs a non-empty property");
        if (track.keyframes.size() < 2) fail(where + " needs at least two keyframes");
        if (track.keyframes.front().frame != 0) fail(where + " must start at frame 0");
        for (std::size_t i = 0; i < track.keyframes.size(); ++i) {
            const PhraseKeyframe& key = track.keyframes[i];
            if (key.frame < 0) fail(where + " has a negative keyframe frame");
            if (i > 0 && key.frame <= track.keyframes[i - 1].frame) {
                fail(where + " keyframe frames must be strictly increasing");
            }
            if (key.frame >= kDurationFrames) {
                fail(where + " has a keyframe past the showcase timeline");
            }
        }
    }

    /// Extended keyframes: hold the resting value through the timeline, then
    /// return to the entrance state across the last frames so the phrase exits
    /// the way it came in. The final authored value is the resting one.
    json extendedKeyframes(const PhraseTrack& track, int enter) {
        const int hold = enter > (kDurationFrames - kExitFrames) ? enter : (kDurationFrames - kExitFrames);
        const int end = kDurationFrames - 1;
        const float first = track.keyframes.front().value;
        const float last = track.keyframes.back().value;

        json keys = json::array();
        for (const PhraseKeyframe& key : track.keyframes) {
            if (key.frame < hold) keys.push_back({{"frame", key.frame}, {"value", key.value}});
        }
        if (keys.empty() || keys.back()["frame"].get<int>() != hold) {
            keys.push_back({{"frame", hold}, {"value", last}});
        }
        if (end > hold) keys.push_back({{"frame", end}, {"value", first}});
        return keys;
    }

    json makeTrack(const PhraseTrack& track, int enter) {
        return json{{"property", track.property},
                    {"keyframes", extendedKeyframes(track, enter)},
                    {"easing", track.easing}};
    }

    /// A selector is a window over the units, and on the GPU lane the unit-level
    /// ramp lives in the window (`effect = property(t) * weight`):
    ///   "reveal" — `start` sweeps forward as the reveal frontier with `end`
    ///              pinned open; properties hold their hidden value and units
    ///              flip to rest as the edge passes. At start == end the
    ///              canonical terminal state leaves the run visible.
    ///   "band"   — a narrow window travels across the run; its shape weight is
    ///              a local pulse that swells each unit in turn, and the band
    ///              closes at the end so the resting window has no influence.
    ///   "full"   — a static full window; animated properties act on the whole
    ///              run at once.
    json loweredSelector(const PhraseSelector& selector, int enter, const std::string& id) {
        json start;
        json end;
        std::string shape;
        if (selector.window == "reveal" || selector.window == "reveal_soft") {
            shape = selector.window == "reveal" ? "square" : "smooth";
            start = json{{"property", "start"},
                         {"keyframes", json::array({{{"frame", 0}, {"value", 0}},
                                                    {{"frame", enter}, {"value", 100}}})},
                         {"easing", "out_cubic"}};
            end = json{{"property", "end"},
                       {"keyframes", json::array({{{"frame", 0}, {"value", 100}}})},
                       {"easing", "linear"}};
        } else if (selector.window == "band") {
            shape = "smooth";
            start = json{{"property", "start"},
                         {"keyframes", json::array({{{"frame", 0}, {"value", 0}},
                                                    {{"frame", enter}, {"value", 72}},
                                                    {{"frame", enter + 10}, {"value", 100}}})},
                         {"easing", "in_out_sine"}};
            end = json{{"property", "end"},
                       {"keyframes", json::array({{{"frame", 0}, {"value", 28}},
                                                  {{"frame", enter}, {"value", 100}},
                                                  {{"frame", enter + 10}, {"value", 100}}})},
                       {"easing", "in_out_sine"}};
        } else if (selector.window == "full") {
            shape = "square";
            start = json{{"property", "start"},
                         {"keyframes", json::array({{{"frame", 0}, {"value", 0}}})},
                         {"easing", "linear"}};
            end = json{{"property", "end"},
                       {"keyframes", json::array({{{"frame", 0}, {"value", 100}}})},
                       {"easing", "linear"}};
        } else {
            fail(id + ": unknown selector window \"" + selector.window + "\" (full | reveal | band)");
        }
        return json{{"id", id + "_selector"},
                    {"unit", selector.unit},
                    {"shape", shape},
                    {"order", selector.order},
                    {"combine", "replace"},
                    {"exclude_spaces", true},
                    {"start", std::move(start)},
                    {"end", std::move(end)}};
    }

    json lowerAnimator(const PhraseTextAnimator& animator, int enter, const std::string& id) {
        json properties = json::array();
        for (std::size_t i = 0; i < animator.properties.size(); ++i) {
            const std::string where = id + ".properties[" + std::to_string(i) + "]";
            validateTrack(animator.properties[i], where);
            properties.push_back(makeTrack(animator.properties[i], enter));
        }
        return json{{"id", id + "_text"},
                    {"selectors", json::array({loweredSelector(animator.selector, enter, id)})},
                    {"properties", properties}};
    }

    json makePlan(const PhraseAnimationDefinition& definition, const ClassicPhraseStyle& style,
                  int canvasScale = 1) {
        const int enter = definition.enter;
        if (enter <= 0 || enter >= kDurationFrames) {
            fail(definition.id + ": enter must land inside the showcase timeline");
        }
        if (definition.tracks.empty() && definition.textAnimators.empty()) {
            fail(definition.id + ": an animation with neither tracks nor text animators renders a static phrase");
        }

        json layerTracks = json::array();
        bool hasLayerOpacity = false;
        for (std::size_t i = 0; i < definition.tracks.size(); ++i) {
            const std::string where = definition.id + ".tracks[" + std::to_string(i) + "]";
            validateTrack(definition.tracks[i], where);
            hasLayerOpacity = hasLayerOpacity || definition.tracks[i].property == "opacity";
            layerTracks.push_back(makeTrack(definition.tracks[i], enter));
        }

        // Every phrase needs a real layer-level entrance/hold/exit. An animator
        // reveals the units, but without this safety net a unit-less frame
        // (spaces, punctuation the selector excludes) would pop in unstyled.
        if (!hasLayerOpacity) {
            layerTracks.push_back(json{
                    {"property", "opacity"},
                    {"keyframes", json::array({{{"frame", 0}, {"value", 0.0}},
                                               {{"frame", 8}, {"value", 1.0}},
                                               {{"frame", kDurationFrames - kExitFrames}, {"value", 1.0}},
                                               {{"frame", kDurationFrames - 1}, {"value", 0.0}}})},
                    {"easing", "linear"}});
        }

        json animators = json::array();
        for (std::size_t i = 0; i < definition.textAnimators.size(); ++i) {
            const std::string where = definition.id + ".textAnimators[" + std::to_string(i) + "]";
            if (definition.textAnimators[i].properties.empty()) {
                fail(where + " needs at least one property track");
            }
            animators.push_back(lowerAnimator(definition.textAnimators[i], enter, definition.id));
        }

        const json textStyle = json{{"font", style.font},
                                    {"font_size", style.font_size * canvasScale},
                                    {"fill", style.fill},
                                    {"stroke", json{{"color", style.stroke}, {"width", style.stroke_width}}},
                                    {"glow", json{{"radius", style.glow_radius},
                                                  {"intensity", style.glow_intensity},
                                                  {"color", style.glow}}}};
        json phrase = json{
                {"id", "phrase"},
                {"type", "text"},
                {"text", definition.phrase},
                {"size", json::array({style.box[0] * canvasScale, style.box[1] * canvasScale})},
                {"position", json::array({style.position[0] * canvasScale,
                                           style.position[1] * canvasScale})},
                {"style", textStyle},
                {"start_frame", 0},
                {"duration_frames", kDurationFrames},
                {"animation", json{{"tracks", layerTracks}}},
        };
        if (!animators.empty()) phrase["text_animators"] = animators;

        json layers = json::array();
        layers.push_back(json{{"id", "background"},
                              {"type", "color"},
                              {"color", json::array({style.background[0], style.background[1],
                                                     style.background[2], style.background[3]})},
                              {"size", json::array({kWidth * canvasScale, kHeight * canvasScale})},
                              {"start_frame", 0},
                              {"duration_frames", kDurationFrames}});
        layers.push_back(phrase);

        // The Typewriter family types with a `_` cursor layer: same face, its
        // own tracks (the sweep on position_x, the blink on opacity).
        if (!definition.cursor.tracks.empty()) {
            json cursorTracks = json::array();
            for (std::size_t i = 0; i < definition.cursor.tracks.size(); ++i) {
                const std::string where = definition.id + ".cursor[" + std::to_string(i) + "]";
                validateTrack(definition.cursor.tracks[i], where);
                cursorTracks.push_back(makeTrack(definition.cursor.tracks[i], enter));
            }
            layers.push_back(json{{"id", "cursor"},
                                  {"type", "text"},
                                  {"text", definition.cursor.text},
                                  {"size", json::array({definition.cursor.box[0], definition.cursor.box[1]})},
                                  {"position", json::array({definition.cursor.position[0],
                                                            definition.cursor.position[1]})},
                                  {"style", textStyle},
                                  {"start_frame", 0},
                                  {"duration_frames", kDurationFrames},
                                  {"animation", json{{"tracks", cursorTracks}}}});
        }

        return json{{"schema", "chronon.render-plan.v2"},
                    {"version", 2},
                    {"job_id", "chronontemplate_" + definition.id},
                    {"canvas", json{{"width", kWidth * canvasScale},
                                    {"height", kHeight * canvasScale},
                                    {"fps_num", kFps},
                                    {"fps_den", 1},
                                    {"duration_frames", kDurationFrames}}},
                    {"layers", layers},
                    {"output", json{{"path", definition.id + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}}};
    }

    void writeFile(const std::filesystem::path& path, const std::string& contents) {
        std::ofstream out(path, std::ios::binary | std::ios::trunc);
        if (!out) fail("cannot write " + path.string());
        out << contents;
    }

}// namespace

int main(int argc, char** argv) try {
    const std::string mode = argc >= 3 ? argv[2] : "";
    if (argc < 2 || argc > 4 || (argc == 3 && mode != "--static-only" && mode != "--static-canaries") ||
        (argc == 4 && mode != "--editorial-static" && mode != "--editorial-word-reveal" &&
         mode != "--editorial-layer-rise")) {
        std::cerr << "usage: chronontemplate_emit_important_phrase_plans <output-directory> [--static-only|--static-canaries|--editorial-static|--editorial-word-reveal|--editorial-layer-rise <font-path>]\n";
        return 2;
    }
    const std::filesystem::path outDir = argv[1];
    const bool staticOnly = mode == "--static-only" || mode == "--static-canaries" ||
                            mode == "--editorial-static" || mode == "--editorial-word-reveal" ||
                            mode == "--editorial-layer-rise";
    std::filesystem::create_directories(outDir);

    const ClassicPhraseStyle style = chronontemplate::classicPhraseStyle();
    const ClassicPhraseStyle appleStyle = chronontemplate::applePhraseStyle();
    json manifest = json{{"schema", "chronontemplate.important-phrase-classic.v1"},
                        {"pipeline", "ChrononTemplate C++ pack -> chronon.render-plan.v2 -> Chronon3D GPU"},
                        {"style", json{{"font", style.font},
                                       {"font_size", style.font_size},
                                       {"fill", style.fill},
                                       {"background", "black"},
                                       {"glow", json{{"radius", style.glow_radius},
                                                     {"intensity", style.glow_intensity},
                                                     {"color", style.glow}}}}},
                        {"apple_style", json{{"stroke", json{{"color", appleStyle.stroke},
                                                                  {"width", appleStyle.stroke_width}}},
                                              {"glow", json{{"radius", appleStyle.glow_radius},
                                                             {"intensity", appleStyle.glow_intensity},
                                                             {"color", appleStyle.glow}}}}},
                        {"canvas", json{{"width", kWidth}, {"height", kHeight},
                                        {"fps", kFps}, {"duration_frames", kDurationFrames}}},
                        {"animations", json::array()}};

    const auto emitFamily = [&](const auto& animations, const std::string& family) {
        for (const auto animation : animations) {
            const PhraseAnimationDefinition definition = chronontemplate::definition(animation);
            const std::string expected = chronontemplate::name(animation);
            if (definition.id != expected) {
                fail("definition id \"" + definition.id + "\" is published as \"" + expected + "\"");
            }
            const ClassicPhraseStyle familyStyle = family == "apple" ? chronontemplate::applePhraseStyle()
                                                                      : chronontemplate::classicPhraseStyle();
            const json plan = makePlan(definition, familyStyle);
            const std::string planName = definition.id + ".plan.json";
            writeFile(outDir / planName, plan.dump(2) + "\n");
            manifest["animations"].push_back(json{{"id", definition.id},
                                                  {"family", family},
                                                  {"title", definition.title},
                                                  {"phrase", definition.phrase},
                                                  {"enter", definition.enter},
                                                  {"cursor", !definition.cursor.tracks.empty()},
                                                  {"unit", definition.textAnimators.empty()
                                                                  ? "layer"
                                                                  : definition.textAnimators.front().selector.unit},
                                                  {"plan", planName}});
            std::cout << "emitted " << planName << "\n";
        }
    };
    if (!staticOnly) {
        emitFamily(chronontemplate::classicPhraseAnimations(), "classic");
        emitFamily(chronontemplate::typewriterPhraseAnimations(), "typewriter");
        emitFamily(chronontemplate::applePhraseAnimations(), "apple");
    }
    if (mode == "--editorial-static" || mode == "--editorial-word-reveal" ||
        mode == "--editorial-layer-rise") {
        auto editorialStyle = chronontemplate::classicPhraseStyle();
        editorialStyle.font = argv[3];
        editorialStyle.font_size = 84.f;
        editorialStyle.box = {1640.f, 260.f};
        editorialStyle.fill = "#F8F8F8";
        editorialStyle.stroke_width = 0.f;
        editorialStyle.glow = "#FFFFFF";
        editorialStyle.glow_radius = 3.f;
        editorialStyle.glow_intensity = 0.045f;
        const bool wordReveal = mode == "--editorial-word-reveal";
        const bool layerRise = mode == "--editorial-layer-rise";
        const PhraseAnimationDefinition still{
            wordReveal ? "editorial_words_appear_reveal" :
                (layerRise ? "editorial_words_appear_layer_rise" : "editorial_words_appear"),
            wordReveal ? "Editorial Word Reveal" :
                (layerRise ? "Editorial Layer Rise" : "Editorial Static"),
            "Words appear at the right time", (wordReveal || layerRise) ? 36 : 1,
            layerRise
                ? std::vector<PhraseTrack>{
                    PhraseTrack{"position_y", "out_cubic", {{0, 28.f}, {36, 0.f}}},
                    PhraseTrack{"scale", "out_cubic", {{0, 0.985f}, {36, 1.f}}},
                    PhraseTrack{"opacity", "out_cubic", {{0, 0.f}, {36, 1.f}}}}
                : std::vector<PhraseTrack>{PhraseTrack{"opacity", "linear", {{0, 1.f}, {1, 1.f}}}},
            wordReveal ? std::vector<PhraseTextAnimator>{PhraseTextAnimator{
                PhraseSelector{"word", "forward", "reveal_soft"},
                {PhraseTrack{"position_y", "out_cubic", {{0, 18.f}, {36, 0.f}}},
                 PhraseTrack{"opacity", "linear", {{0, 0.f}, {36, 0.f}}}}}}
                : std::vector<PhraseTextAnimator>{}, {}};
        const json plan = makePlan(still, editorialStyle);
        const std::string file = still.id + ".plan.json";
        writeFile(outDir / file, plan.dump(2) + "\n");
        manifest["static_styles"].push_back(json{{"id", still.id}, {"title", still.title},
            {"phrase", still.phrase}, {"font", editorialStyle.font}, {"font_size", editorialStyle.font_size},
            {"fill", editorialStyle.fill}, {"stroke_width", 0}, {"glow_radius", editorialStyle.glow_radius},
            {"glow_intensity", editorialStyle.glow_intensity}, {"animated", wordReveal || layerRise},
            {"animation_model", wordReveal ? "word-selector" : (layerRise ? "layer-transform" : "static")},
            {"plan", file}});
    } else if (mode == "--static-canaries") {
        auto canaryStyle = chronontemplate::applePhraseStyle();
        canaryStyle.stroke_width = 0.f;
        canaryStyle.glow_radius = 0.f;
        canaryStyle.glow_intensity = 0.f;
        const auto emitCanary = [&](const std::string& id, float layerScale,
                                    float fontSizeScale, int canvasScale) {
            const PhraseAnimationDefinition still{
                id, "MTSDF edge canary", "watching", 1,
                {PhraseTrack{"opacity", "linear", {{0, 1.f}, {1, 1.f}}},
                 PhraseTrack{"scale", "linear", {{0, layerScale}, {1, layerScale}}}}, {}, {}};
            auto variantStyle = canaryStyle;
            variantStyle.font_size *= fontSizeScale;
            const json plan = makePlan(still, variantStyle, canvasScale);
            const std::string file = id + ".plan.json";
            writeFile(outDir / file, plan.dump(2) + "\n");
            manifest["static_styles"].push_back(json{{"id", id}, {"phrase", still.phrase},
                {"font", variantStyle.font}, {"font_size", variantStyle.font_size * canvasScale},
                {"stroke_width", 0}, {"glow_radius", 0}, {"glow_intensity", 0},
                {"canvas_scale", canvasScale}, {"layer_scale", layerScale}, {"plan", file}});
        };
        emitCanary("mtsdf_A_base", 1.f, 1.f, 1);
        emitCanary("mtsdf_B_layer_scale_1_5x", 1.5f, 1.f, 1);
        emitCanary("mtsdf_C_font_size_1_5x", 1.f, 1.5f, 1);
        emitCanary("mtsdf_D_2x_supersample", 1.f, 1.f, 2);
    } else {
        const PhraseAnimationDefinition still = chronontemplate::appleClassicStill();
        const json plan = makePlan(still, chronontemplate::applePhraseStyle());
        writeFile(outDir / (still.id + ".plan.json"), plan.dump(2) + "\n");
        manifest["static_styles"].push_back(json{{"id", still.id}, {"title", still.title},
                                                  {"phrase", still.phrase},
                                                  {"plan", still.id + ".plan.json"}});
    }
    writeFile(outDir / "manifest.json", manifest.dump(2) + "\n");
    std::cout << "emitted " << manifest["animations"].size() << " classic important-phrase plans in "
              << outDir.string() << "\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << "\n";
    return 1;
}
