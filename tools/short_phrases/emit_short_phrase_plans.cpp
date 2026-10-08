// ChrononTemplate — short-phrase plan emitter.
//
// Lowers the C++-owned ShortPhrasePack to the Chronon3D render-plan contract,
// one plan per archetype, so the family can be rendered on the GPU lane. It is
// deliberately thin: the ShortPhrasePack recipes live in
// include/chronontemplate/short_phrases/ShortPhrasePack.hpp and this program
// only projects them — extended keyframes (hold + synthesised exit) and the
// lowered selector window, the same canonical lowering the Classic emitter and
// emit_native_phrase_pack.py apply.
//
// Validation is fail-closed: a keyframe list that does not start at frame 0, a
// non-monotonic one, or an archetype with neither layer tracks nor text
// animators aborts the emit instead of shipping a plan the renderer would
// reject halfway through a job.
//
// The semantic emphasis, the exit mode and the decor bumper are catalog
// metadata: the renderer draws the phrase run today, and the richer exit modes
// (wipe/scatter/arc) land when the render-plan contract grows a matching
// property. They are recorded in the manifest so nothing is lost.
//
// Usage:
//   chronontemplate_emit_short_phrase_plans <output-directory>

#include <nlohmann/json.hpp>

#include "chronontemplate/important_phrases/ImportantPhrasePack.hpp"
#include "chronontemplate/short_phrases/ShortPhrasePack.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <set>
#include <vector>

namespace {

    using json = nlohmann::ordered_json;
    using chronontemplate::ClassicPhraseStyle;
    using chronontemplate::PhraseKeyframe;
    using chronontemplate::PhraseSelector;
    using chronontemplate::PhraseTextAnimator;
    using chronontemplate::PhraseAccent;
    using chronontemplate::PhraseTrack;
    using chronontemplate::ShortPhraseAnimation;
    using chronontemplate::ShortPhraseDecor;
    using chronontemplate::ShortPhraseDefinition;
    using chronontemplate::ShortPhraseExit;

    constexpr int kWidth = 1920;
    constexpr int kHeight = 1080;
    constexpr int kFps = 30;
    constexpr int kDurationFrames = 210;// 7 s showcase: 3 s reveal, readable hold, exit
    /// The last fifteen frames are the synthesised exit.
    constexpr int kExitFrames = 15;

    [[noreturn]] void fail(const std::string& message) {
        throw std::runtime_error("emit_short_phrase_plans: " + message);
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
            if (key.frame >= kDurationFrames) fail(where + " has a keyframe past the showcase timeline");
        }
    }

    /// Extended keyframes: hold the resting value through the timeline, then
    /// return to the entrance state across the last frames so the phrase exits
    /// the way it came in. The final authored value is the resting one.
    json extendedKeyframes(const PhraseTrack& track, int enter) {
        const bool sequence = track.keyframes.back().frame >= 120;
        const int hold = sequence ? (kDurationFrames - kExitFrames)
                                  : (enter > (kDurationFrames - kExitFrames) ? enter : (kDurationFrames - kExitFrames));
        const int end = kDurationFrames - 1;
        const float first = track.keyframes.front().value;
        float last = first;
        for (const PhraseKeyframe& key : track.keyframes) {
            if (key.frame <= hold) last = key.value;
        }

        json keys = json::array();
        for (const PhraseKeyframe& key : track.keyframes) {
            if (key.frame < hold) keys.push_back({{"frame", key.frame}, {"value", key.value}});
        }
        if (keys.empty() || keys.back()["frame"].get<int>() != hold) {
            keys.push_back({{"frame", hold}, {"value", last}});
        }
        float exit = first;
        if (sequence) {
            if (track.property == "position_x") exit = last + 140.f;
            else if (track.property == "position_y") exit = last - 140.f;
            else if (track.property == "scale") exit = last * 0.78f;
            else if (track.property == "tracking") exit = 0.f;
            else if (track.property == "blur") exit = 14.f;
        }
        if (end > hold) keys.push_back({{"frame", end}, {"value", exit}});
        return keys;
    }

    /// Chronon3D evaluates text-animator property tracks with linear
    /// interpolation only (render_plan_decoder_text.cpp rejects any easing but
    /// "linear" on them: "text animator property tracks require sampled linear
    /// keyframes"), so the authored easing has to be baked into the keyframes
    /// here. These polynomials are exactly the GLM functions
    /// chronon3d::easing::apply delegates to (glm/gtx/easing.inl), so the baked
    /// ramp matches the easing a layer track would have applied.
    float applyEasing(const std::string& easing, float t) {
        if (t <= 0.f) return 0.f;
        if (t >= 1.f) return 1.f;
        constexpr float kPi = 3.14159265358979323846f;
        if (easing == "kcb_entry") {
            constexpr float x1=.2f, y1=.8f, x2=.2f, y2=1.f;
            float lo=0.f, hi=1.f, u=.5f;
            for (int i=0;i<28;++i) {
                u=(lo+hi)*.5f;
                const float v=3.f*(1.f-u)*(1.f-u)*u*x1+3.f*(1.f-u)*u*u*x2+u*u*u;
                if (v<t) lo=u; else hi=u;
            }
            u=(lo+hi)*.5f;
            return 3.f*(1.f-u)*(1.f-u)*u*y1+3.f*(1.f-u)*u*u*y2+u*u*u;
        }
        if (easing == "per_word_land") {
            constexpr float split=.78f, residual=.07f;
            constexpr float slope=((1.f-residual)/split)*.5f;
            if (t<split) {
                const float x=t/split, inv=1.f-x;
                return (1.f-residual)*(.5f*(1.f-inv*inv*inv)+.5f*x);
            }
            const float u=(t-split)/(1.f-split);
            const float b=slope*(1.f-split);
            const float c=3.f*residual-2.f*b;
            const float d=b-2.f*residual;
            return 1.f-residual+b*u+c*u*u+d*u*u*u;
        }
        if (easing == "linear") return t;
        if (easing == "smoothstep") return t * t * (3.f - 2.f * t);
        if (easing == "in_quad") return t * t;
        if (easing == "out_quad") return -(t * (t - 2.f));
        if (easing == "in_cubic") return t * t * t;
        if (easing == "out_cubic") { const float f = t - 1.f; return f * f * f + 1.f; }
        if (easing == "in_out_cubic") {
            if (t < 0.5f) return 4.f * t * t * t;
            const float f = 2.f * t - 2.f;
            return 0.5f * f * f * f + 1.f;
        }
        if (easing == "in_sine") return std::sin((t - 1.f) * (kPi / 2.f)) + 1.f;
        if (easing == "out_sine") return std::sin(t * (kPi / 2.f));
        if (easing == "in_out_sine") return 0.5f * (1.f - std::cos(t * kPi));
        if (easing == "out_back") {
            constexpr float o = 1.70158f;
            const float n = t - 1.f;
            return n * n * ((o + 1.f) * n + o) + 1.f;
        }
        fail("unsupported text-animator easing \"" + easing +
             "\": bake it or add the GLM polynomial to applyEasing");
    }

    /// Sample a track into one linear keyframe per frame so a text-animator
    /// property track carries the sampled linear timing the decoder requires
    /// while keeping the shape of the authored easing.
    json bakedTrack(const PhraseTrack& track, int enter, const std::string& where) {
        const json source = extendedKeyframes(track, enter);
        std::vector<std::pair<int, float>> keys;
        keys.reserve(source.size());
        for (const auto& key : source) {
            keys.emplace_back(key.at("frame").get<int>(), key.at("value").get<float>());
        }
        if (keys.empty() || keys.front().first != 0) fail(where + " baked keyframes must start at frame 0");

        json baked = json::array();
        std::size_t segment = 0;
        for (int frame = 0; frame < kDurationFrames; ++frame) {
            while (segment + 1 < keys.size() && frame > keys[segment + 1].first) ++segment;
            float value = keys.back().second;
            if (segment + 1 < keys.size()) {
                const int start = keys[segment].first;
                const int end = keys[segment + 1].first;
                if (frame <= start) {
                    value = keys[segment].second;
                } else if (end <= start) {
                    value = keys[segment + 1].second;
                } else {
                    const float t = static_cast<float>(frame - start) /
                                    static_cast<float>(end - start);
                    const float eased = applyEasing(track.easing, t);
                    value = keys[segment].second +
                            (keys[segment + 1].second - keys[segment].second) * eased;
                }
            }
            baked.push_back({{"frame", frame}, {"value", value}});
        }
        return baked;
    }

    /// The renderer's text-animator path demands 3-component rotation values
    /// (render_plan_compiler_animation_text.cpp: scalar rotation is only
    /// accepted on layer tracks, not inside text_animators), so any animator
    /// rotation track is projected onto its Z component here.
    json vectorizeRotation(const PhraseTrack& track, const json& keys) {
        if (track.property != "rotation") return keys;
        json rotated = json::array();
        for (const auto& key : keys) {
            const float z = key.at("value").get<float>();
            rotated.push_back({{"frame", key.at("frame")},
                               {"value", json::array({0.f, 0.f, z})}});
        }
        return rotated;
    }

    /// The per-key component contract rejects axis tracks whose keyframe sets
    /// or easing differ; resample every position_* axis of one accent onto the
    /// union of its keyframes (linear cross-sampling) and force a shared
    /// easing. Position axes move in lockstep anyway, so the resample keeps the
    /// authored path piecewise-identical at every authored key.
    void alignAccentAxes(PhraseAccent& accent, const std::string& id) {
        std::vector<PhraseTrack*> positionAxes;
        for (auto& track : accent.tracks) {
            if (track.property.rfind("position_", 0) == 0) positionAxes.push_back(&track);
        }
        if (positionAxes.size() < 2) return;
        std::set<int> union_frames;
        for (const auto* track : positionAxes) {
            for (const auto& key : track->keyframes) union_frames.insert(key.frame);
        }
        for (auto* track : positionAxes) {
            std::vector<PhraseKeyframe> resampled;
            for (const int frame : union_frames) {
                const auto& keys = track->keyframes;
                if (frame <= keys.front().frame) {
                    resampled.push_back({frame, keys.front().value});
                    continue;
                }
                if (frame >= keys.back().frame) {
                    resampled.push_back({frame, keys.back().value});
                    continue;
                }
                for (std::size_t i = 0; i + 1 < keys.size(); ++i) {
                    if (keys[i].frame <= frame && frame <= keys[i + 1].frame) {
                        const float t = static_cast<float>(frame - keys[i].frame) /
                                        static_cast<float>(keys[i + 1].frame - keys[i].frame);
                        resampled.push_back({frame, keys[i].value + (keys[i + 1].value - keys[i].value) * t});
                        break;
                    }
                }
            }
            track->keyframes = std::move(resampled);
            track->easing = positionAxes.front()->easing;
        }
        (void)id;
    }

    json makeTrack(const PhraseTrack& track, int enter) {
        json result{{"property", track.property},
                    {"keyframes", extendedKeyframes(track, enter)},
                    {"easing", track.easing}};
        if (track.easing == "kcb_entry") {
            result["easing"] = "bezier";
            result["bezier_curve"] = json::array({0.2f, 0.8f, 0.2f, 1.f});
        }
        return result;
    }

    /// A selector is a window over the units; on the GPU lane the unit-level
    /// ramp lives in the window (`effect = property(t) * weight`).
    json loweredSelector(const PhraseSelector& selector, int enter, const std::string& id) {
        // Selector tracks carry baked linear timing only: render_plan_decoder_text
        // rejects a `property` key and any non-linear easing on the start/end
        // window ramp, so the shaping has to live in the animator's property
        // tracks instead of on the selector window itself.
        json start;
        json end;
        std::string shape;
        if (selector.window == "reveal" || selector.window == "reveal_soft") {
            shape = selector.window == "reveal" ? "square" : "smooth";
            start = json{{"keyframes", json::array({{{"frame", 0}, {"value", 0}},
                                                    {{"frame", enter}, {"value", 100}}})},
                         {"easing", "linear"}};
            end = json{{"keyframes", json::array({{{"frame", 0}, {"value", 100}}})},
                       {"easing", "linear"}};
        } else if (selector.window == "band") {
            shape = "smooth";
            start = json{{"keyframes", json::array({{{"frame", 0}, {"value", 0}},
                                                    {{"frame", enter}, {"value", 72}},
                                                    {{"frame", enter + 10}, {"value", 100}}})},
                         {"easing", "linear"}};
            end = json{{"keyframes", json::array({{{"frame", 0}, {"value", 28}},
                                                  {{"frame", enter}, {"value", 100}},
                                                  {{"frame", enter + 10}, {"value", 100}}})},
                       {"easing", "linear"}};
        } else if (selector.window.rfind("pick:", 0) == 0) {
            // pick:<index>:<count> selects exactly one unit of a run of <count>.
            const std::size_t split = selector.window.find(':', 5);
            const float index = std::stof(selector.window.substr(5, split - 5));
            const float count = std::stof(selector.window.substr(split + 1));
            shape = "square";
            start = json{{"keyframes", json::array({{{"frame", 0}, {"value", 100.f * index / count}}})},
                         {"easing", "linear"}};
            end = json{{"keyframes", json::array({{{"frame", 0}, {"value", 100.f * (index + 1.f) / count}}})},
                       {"easing", "linear"}};
        } else if (selector.window == "full") {
            shape = "square";
            start = json{{"keyframes", json::array({{{"frame", 0}, {"value", 0}}})},
                         {"easing", "linear"}};
            end = json{{"keyframes", json::array({{{"frame", 0}, {"value", 100}}})},
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

    /// Color shorthand is projected to animated RGBA accepted by the renderer.
    bool isColorMix(const std::string& property) {
        return property == "fill_blue" || property == "fill_gray" || property == "fill_orange";
    }

    json colorTrack(const PhraseTrack& track, int enter, bool light, bool whiteBackground, const std::string& where) {
        const std::array<float, 4> rest = (light || whiteBackground)
            ? std::array<float, 4>{0.03f, 0.03f, 0.03f, 1.f}
            : std::array<float, 4>{1.f, 1.f, 1.f, 1.f};
        const std::array<float, 4> target = track.property == "fill_blue"
            ? std::array<float, 4>{0.30f, 0.55f, 1.f, 1.f}
            : track.property == "fill_orange"
                ? std::array<float, 4>{1.f, 0.38f, 0.12f, 1.f}
                : (light ? std::array<float, 4>{0.62f, 0.62f, 0.62f, 1.f}
                         : std::array<float, 4>{0.40f, 0.40f, 0.40f, 1.f});
        json keys = json::array();
        for (const auto& key : bakedTrack(track, enter, where)) {
            const float mix = std::clamp(key.at("value").get<float>(), 0.f, 1.f);
            json value = json::array();
            for (int c = 0; c < 4; ++c) value.push_back(rest[c] + (target[c] - rest[c]) * mix);
            keys.push_back({{"frame", key.at("frame")}, {"value", value}});
        }
        return json{{"property", "fill_color"}, {"keyframes", keys}, {"easing", "linear"}};
    }

    json lowerAnimator(const PhraseTextAnimator& animator, int enter, const std::string& id,
                       bool light = false, bool whiteBackground = false) {
        json properties = json::array();
        for (std::size_t i = 0; i < animator.properties.size(); ++i) {
            const std::string where = id + ".properties[" + std::to_string(i) + "]";
            validateTrack(animator.properties[i], where);
            // Text-animator property tracks are sampled-linear in the contract,
            // so bake the authored easing into per-frame keyframes.
            if (isColorMix(animator.properties[i].property)) {
                properties.push_back(colorTrack(animator.properties[i], enter, light, whiteBackground, where));
                continue;
            }
            properties.push_back(json{{"property", animator.properties[i].property},
                                      {"keyframes", vectorizeRotation(animator.properties[i],
                                          bakedTrack(animator.properties[i], enter, where))},
                                      {"easing", "linear"}});
        }
        return json{{"id", id + "_text"},
                    {"selectors", json::array({loweredSelector(animator.selector, enter, id)})},
                    {"properties", properties}};
    }

    json makePlan(const ShortPhraseDefinition& definition, const ClassicPhraseStyle& style) {
        const int enter = definition.enter;
        const bool editorial = definition.id.rfind("short_phrase_editorial_", 0) == 0;
        const bool product = definition.id.rfind("short_phrase_product_", 0) == 0;
        const bool modern = editorial || product;
        if (enter <= 0 || enter >= kDurationFrames) {
            fail(definition.id + ": enter must land inside the showcase timeline");
        }
        if (definition.tracks.empty() && definition.textAnimators.empty() &&
            definition.textOverlays.empty()) {
            fail(definition.id + ": an animation with neither tracks nor text animators renders a static phrase");
        }

        const auto setBezier = [](json& tracks, const std::string& property,
                                  const std::array<float, 4>& curve) {
            for (auto& item : tracks) {
                if (item.value("property", std::string{}) != property) continue;
                item["easing"] = "bezier";
                item["bezier_curve"] = curve;
            }
        };
        json layerTracks = json::array();
        bool hasLayerOpacity = false;
        for (std::size_t i = 0; i < definition.tracks.size(); ++i) {
            const std::string where = definition.id + ".tracks[" + std::to_string(i) + "]";
            validateTrack(definition.tracks[i], where);
            hasLayerOpacity = hasLayerOpacity || definition.tracks[i].property == "opacity";
            layerTracks.push_back(makeTrack(definition.tracks[i], enter));
        }
        if (definition.id == "short_phrase_product_text_match_cut")
            setBezier(layerTracks, "scale", {0.85f, 0.f, 0.15f, 1.f});

        // Every phrase needs a real layer-level entrance/hold/exit. An animator
        // reveals the units, but without this safety net a unit-less frame
        // (spaces, punctuation the selector excludes) would pop in unstyled.
        if (!hasLayerOpacity) {
            layerTracks.push_back(json{
                    {"property", "opacity"},
                    {"keyframes", json::array({{{"frame", 0}, {"value", 0.0}},
                                               {{"frame", enter}, {"value", 1.0}},
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
            animators.push_back(lowerAnimator(definition.textAnimators[i], enter, definition.id + "_anim" + std::to_string(i),
                                              definition.light, definition.white_background));
        }
        // Semantic emphasis uses the family's accent and settles to the resting fill.
        const int words = static_cast<int>(chronontemplate::shortPhraseWordCount(definition.phrase));
        for (const std::size_t word : definition.emphasis) {
            if (static_cast<int>(word) >= words) fail(definition.id + ": emphasis index out of range");
            PhraseTextAnimator emphasis{
                    PhraseSelector{"word", "forward", "pick:" + std::to_string(word) + ":" + std::to_string(words)},
                    {PhraseTrack{definition.white_background ? "fill_orange" : "fill_blue", "linear",
                                 definition.id == "short_phrase_product_dual_tone_reveal"
                                     ? std::vector<PhraseKeyframe>{{0, 0.f}, {enter + 8, 0.f},
                                                                   {enter + 16, 1.f}, {120, 1.f}}
                                     : std::vector<PhraseKeyframe>{{0, 1.f}, {enter + 6, 1.f},
                                                                   {enter + 18, 0.f}}}}};
            animators.push_back(lowerAnimator(emphasis, enter,
                                              definition.id + "_emph" + std::to_string(word),
                                              definition.light, definition.white_background));
        }

        const float phraseFontSize = definition.font_size > 0.f ? definition.font_size : style.font_size;
        const bool sentence = definition.id.find("two_line") != std::string::npos ||
                              definition.id.find("build_focus") != std::string::npos ||
                              definition.id.find("chain_curve") != std::string::npos ||
                              definition.id.find("progressive") != std::string::npos ||
                              definition.id.find("write_on") != std::string::npos ||
                              definition.id.find("cascade_sentence") != std::string::npos;
        const std::string fontPath = definition.id == "short_phrase_editorial_claude_terminal_focus"
                                   ? "assets/fonts/UbuntuMono-R.ttf"
                                   : modern ? "assets/fonts/Bricolage-Grotesque.ttf"
                                   : sentence ? "assets/fonts/DMSans-Bold.ttf"
                                              : "assets/fonts/Inter-Bold.ttf";
        json textStyle{{"font", fontPath},
                       {"font_size", phraseFontSize},
                       {"fill", definition.fill_color.empty() ? style.fill : definition.fill_color},
                       {"stroke", json{{"color", "#000000"}, {"width", 0}}},
                       {"glow", json{{"radius", 0}, {"intensity", 0}, {"color", "#000000"}}}};
        if (definition.light || definition.white_background) textStyle["fill"] = "#080808";
        if (definition.id == "short_phrase_editorial_claude_terminal_focus") {
            textStyle["font"] = "assets/fonts/UbuntuMono-R.ttf";
        }
        json phrase = json{
                {"id", "phrase"},
                {"type", "text"},
                {"text", definition.phrase},
                {"size", json::array({style.box[0], style.box[1]})},
                {"position", json::array({style.position[0], style.position[1]})},
                {"style", textStyle},
                {"start_frame", 0},
                {"duration_frames", kDurationFrames},
                {"animation", json{{"tracks", layerTracks}}},
        };
        if (!animators.empty()) phrase["text_animators"] = animators;
        if (definition.id == "short_phrase_product_blur_out_up") {
            phrase["masks"] = json::array({json{{"type", "rect"}, {"mode", "intersect"},
                {"position", json::array({0, 0})}, {"size", json::array({1760, 260})}}});
        }
        if (definition.id == "short_phrase_product_depth_parallax") {
            phrase.erase("text_animators");
            phrase["animation"]["tracks"] = json::array({json{{"property", "opacity"}, {"easing", "linear"},
                {"keyframes", json::array({{{"frame", 0}, {"value", 0.0}},
                                           {{"frame", kDurationFrames-1}, {"value", 0.0}}})}}});
        }
        json layers = json::array();
        layers.push_back(json{{"id", "background"},
                              {"type", "image"},
                              {"asset", definition.light ? "assets/images/short_phrase_light.png"
                                                         : "assets/images/short_phrase_dark.png"},
                              {"size", json::array({kWidth, kHeight})},
                              {"fit", "cover"},
                              {"position", json::array({0, 0})},
                              {"start_frame", 0},
                              {"duration_frames", kDurationFrames}});
        if (modern) {
            const auto bg = definition.white_background ? json::array({1.0, 1.0, 1.0, 1.0})
                : definition.light ? json::array({0.96, 0.95, 0.93, 1.0})
                : definition.id == "short_phrase_product_text_match_cut"
                    ? json::array({0.0, 0.0, 0.035, 1.0})
                    : json::array({0.025, 0.032, 0.045, 1.0});
            layers[0] = json{{"id", "background"}, {"type", "color"},
                             {"color", bg},
                             {"start_frame", 0}, {"duration_frames", kDurationFrames}};
        }
        for (const auto& accent : definition.accents) {
            if (accent.color.size() != 7 || accent.color.front() != '#') fail("invalid accent color");
            const auto channel = [&](std::size_t offset) {
                return std::stoi(accent.color.substr(offset, 2), nullptr, 16) / 255.f;
            };
            json tracks = json::array();
            // The per-key component contract (render_plan_compiler_animation.cpp
            // add_component_vector_track) rejects axis tracks whose keyframe
            // sets or track easing differ, so authored position_x/position_y
            // pairs must land on the same frames with the same easing.
            PhraseAccent accentAligned = accent;
            alignAccentAxes(accentAligned, definition.id);
            for (const auto& accentTrack : accentAligned.tracks) {
                validateTrack(accentTrack, definition.id + "." + accent.id);
                auto lowered = makeTrack(accentTrack, enter);
                // Native solid-rect promotion needs a non-singular transform
                // and nonzero source alpha, even when the accent is hidden.
                // 0.001 is subpixel/sub-code-value at these rule dimensions.
                if (accentTrack.property == "opacity" || accentTrack.property == "scale_x" ||
                    accentTrack.property == "scale_y") {
                    for (auto& key : lowered["keyframes"]) {
                        key["value"] = std::max(0.001f, key["value"].get<float>());
                    }
                }
                tracks.push_back(std::move(lowered));
            }
            layers.push_back(json{{"id", accent.id}, {"type", "shape"},
                                  {"shape", {{"type", "rect"},
                                             {"fill", json::array({channel(1), channel(3), channel(5), 1.f})}}},
                                  {"size", json::array({accent.width, accent.height})},
                                  {"position", json::array({style.position[0], style.position[1] + accent.y_offset})},
                                  {"opacity", accent.opacity}, {"start_frame", 0},
                                  {"duration_frames", kDurationFrames}, {"animation", {{"tracks", tracks}}}});
        }
        if (definition.drawMainPhrase) layers.push_back(phrase);
        for (const auto& overlay : definition.textOverlays) {
            json copy = phrase;
            copy["id"] = overlay.id;
            copy["text"] = overlay.text.empty() ? definition.phrase : overlay.text;
            copy["position"][0] = style.position[0] + overlay.offset_x;
            copy["position"][1] = style.position[1] + overlay.offset_y;
            copy["opacity"] = overlay.opacity;
            copy["style"]["fill"] = overlay.fill;
            json overlayTracks = json::array();
            for (const auto& t : overlay.tracks) {
                validateTrack(t, definition.id + "." + overlay.id);
                overlayTracks.push_back(makeTrack(t, enter));
            }
            if (!overlayTracks.empty()) copy["animation"]["tracks"] = std::move(overlayTracks);
            if (definition.id == "short_phrase_product_text_match_cut")
                setBezier(copy["animation"]["tracks"], "scale", {0.85f, 0.f, 0.15f, 1.f});
            if (!overlay.textAnimators.empty()) {
                json overlayAnimators = json::array();
                for (std::size_t i = 0; i < overlay.textAnimators.size(); ++i)
                    overlayAnimators.push_back(lowerAnimator(overlay.textAnimators[i], enter,
                        definition.id + "_" + overlay.id + "_anim" + std::to_string(i),
                        definition.light, definition.white_background));
                copy["text_animators"] = std::move(overlayAnimators);
            } else {
                copy.erase("text_animators");
            }
            layers.push_back(std::move(copy));
        }

        if (definition.id == "short_phrase_product_depth_parallax") {
            json upper = phrase;
            upper["id"] = "parallax_upper";
            upper["text"] = "Clarity";
            upper["position"][1] = style.position[1] - 72;
            upper["animation"]["tracks"] = json::array({
                json{{"property", "position_x"}, {"easing", "out_cubic"},
                     {"keyframes", json::array({{{"frame", 0}, {"value", -42}}, {{"frame", enter}, {"value", 0}}, {{"frame", kDurationFrames-kExitFrames}, {"value", 0}}, {{"frame", kDurationFrames-1}, {"value", 0}}})}},
                json{{"property", "opacity"}, {"easing", "linear"},
                     {"keyframes", json::array({{{"frame", 0}, {"value", 0}}, {{"frame", enter}, {"value", 1}}, {{"frame", kDurationFrames-kExitFrames}, {"value", 1}}, {{"frame", kDurationFrames-1}, {"value", 0}}})}}});
            json lower = upper;
            lower["id"] = "parallax_lower";
            lower["text"] = "with purpose";
            lower["position"][1] = style.position[1] + 72;
            lower["animation"]["tracks"][0]["keyframes"] = json::array({{{"frame", 0}, {"value", 42}}, {{"frame", enter + 4}, {"value", 0}}, {{"frame", kDurationFrames-kExitFrames}, {"value", 0}}, {{"frame", kDurationFrames-1}, {"value", 0}}});
            lower["animation"]["tracks"][1]["keyframes"] = json::array({{{"frame", 0}, {"value", 0}}, {{"frame", enter + 4}, {"value", 1}}, {{"frame", kDurationFrames-kExitFrames}, {"value", 1}}, {{"frame", kDurationFrames-1}, {"value", 0}}});
            layers.push_back(upper);
            layers.push_back(lower);
        }

        json result{{"schema", modern ? "chronon.render-plan.v3" : "chronon.render-plan.v2"},
                    {"version", modern ? 3 : 2},
                    {"job_id", "chronontemplate_" + definition.id},
                    {"canvas", json{{"width", kWidth},
                                    {"height", kHeight},
                                    {"fps_num", kFps},
                                    {"fps_den", 1},
                                    {"duration_frames", kDurationFrames}}},
                    {"layers", layers},
                    {"output", json{{"path", definition.id + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}}};
        if (definition.id == "short_phrase_product_fold_text") {
            for (auto& layer : result["layers"]) {
                if (layer.value("type", std::string{}) == "text") layer["enable_3d"] = true;
            }
            result["camera"] = json{{"type", "perspective"}, {"position", json::array({0,0,-1700})},
                                    {"rotation_deg", json::array({0,0,0})}, {"fov_deg", 45},
                                    {"near", 0.1}, {"far", 10000}};
        }
        if (definition.id == "short_phrase_product_perspective_marquee") {
            for (auto& layer : result["layers"]) {
                if (layer.value("type", std::string{}) == "text") layer["enable_3d"] = true;
            }
            result["camera"] = json{{"type", "perspective"}, {"position", json::array({0,0,-1700})},
                                    {"rotation_deg", json::array({0,0,0})}, {"fov_deg", 45},
                                    {"near", 0.1}, {"far", 10000}};
            result["camera_animation"] = json{{"tracks", json::array({
                json{{"property", "camera_position_x"}, {"easing", "in_out_cubic"},
                     {"keyframes", json::array({{{"frame",0},{"value",-320}},{{"frame",99},{"value",320}},{{"frame",209},{"value",320}}})}}
            })}};
        }
        return result;
    }

    void writeFile(const std::filesystem::path& path, const std::string& contents) {
        std::ofstream out(path, std::ios::binary | std::ios::trunc);
        if (!out) fail("cannot write " + path.string());
        out << contents;
    }

    const char* exitId(ShortPhraseExit exit) noexcept {
        switch (exit) {
            case ShortPhraseExit::Reverse: return "reverse";
            case ShortPhraseExit::Forward: return "forward";
            case ShortPhraseExit::Wipe: return "wipe";
            case ShortPhraseExit::Scatter: return "scatter";
            case ShortPhraseExit::ArcDissolve: return "arc_dissolve";
        }
        return "unknown";
    }

    const char* decorName(ShortPhraseDecor decor) noexcept {
        switch (decor) {
            case ShortPhraseDecor::None: return "none";
            case ShortPhraseDecor::StarBumper: return "star_bumper";
        }
        return "unknown";
    }

}// namespace

int main(int argc, char** argv) try {
    if (argc < 2 || argc > 3 || (argc == 3 && std::string(argv[2]) != "--editorial-only" &&
                                std::string(argv[2]) != "--product-only" &&
                                std::string(argv[2]) != "--react-text-only" &&
                                std::string(argv[2]) != "--claude-only")) {
        std::cerr << "usage: chronontemplate_emit_short_phrase_plans <output-directory> [--editorial-only|--product-only|--react-text-only|--claude-only]\n";
        return 2;
    }
    const std::filesystem::path outDir = argv[1];
    std::filesystem::create_directories(outDir);

    const ClassicPhraseStyle style = chronontemplate::classicPhraseStyle();
    json manifest = json{{"schema", "chronontemplate.short-phrase.v1"},
                         {"pipeline", "ChrononTemplate C++ pack -> chronon.render-plan.v2 -> Chronon3D GPU"},
                         {"style", json{{"font", style.font},
                                        {"font_size", style.font_size},
                                        {"fill", style.fill},
                                        {"background", "black"}}},
                         {"canvas", json{{"width", kWidth}, {"height", kHeight},
                                         {"fps", kFps}, {"duration_frames", kDurationFrames}}},
                         {"animations", json::array()}};
    if (argc == 3 && std::string(argv[2]) == "--claude-only") {
        manifest["pipeline"] = "ChrononTemplate C++ pack -> chronon.render-plan.v3 -> Chronon3D GPU";
        manifest["style"]["fill"] = "#080808";
        manifest["style"]["background"] = "#FFFFFF";
    }

    for (const ShortPhraseAnimation animation : chronontemplate::shortPhraseAnimations()) {
        const ShortPhraseDefinition definition = chronontemplate::definition(animation);
        if (argc == 3 && std::string(argv[2]) == "--editorial-only" &&
            definition.id.rfind("short_phrase_editorial_", 0) != 0) continue;
        if (argc == 3 && std::string(argv[2]) == "--product-only" &&
            definition.id.rfind("short_phrase_product_", 0) != 0) continue;
        if (argc == 3 && std::string(argv[2]) == "--react-text-only" &&
            definition.id != "short_phrase_product_masked_heading" &&
            definition.id != "short_phrase_product_split_flap_text" &&
            definition.id != "short_phrase_product_warp_text" &&
            definition.id != "short_phrase_product_fold_text" &&
            definition.id != "short_phrase_product_decrypted_text" &&
            definition.id != "short_phrase_product_scroll_reveal" &&
            definition.id != "short_phrase_product_scrambled_text") continue;
        if (argc == 3 && std::string(argv[2]) == "--claude-only" &&
            definition.id != "short_phrase_editorial_claude_prompt_response" &&
            definition.id != "short_phrase_editorial_claude_diff_patch" &&
            definition.id != "short_phrase_editorial_claude_terminal_focus") continue;
        const std::string expected = chronontemplate::name(animation);
        if (definition.id != expected) {
            fail("definition id \"" + definition.id + "\" is published as \"" + expected + "\"");
        }
        const json plan = makePlan(definition, style);
        const std::string planName = definition.id + ".plan.json";
        writeFile(outDir / planName, plan.dump(2) + "\n");

        json emphasis = json::array();
        for (const std::size_t word : definition.emphasis) emphasis.push_back(word);
        manifest["animations"].push_back(json{
                {"id", definition.id},
                {"title", definition.title},
                {"phrase", definition.phrase},
                {"enter", definition.enter},
                {"word_count", chronontemplate::shortPhraseWordCount(definition.phrase)},
                {"unit", definition.textAnimators.empty() ? "layer"
                                                          : definition.textAnimators.front().selector.unit},
                {"exit", exitId(definition.exit)},
                {"decor", decorName(definition.decor)},
                {"adaptation_note", definition.adaptation_note},
                {"white_background", definition.white_background},
                {"emphasis", emphasis},
                {"plan", planName},
                {"render", definition.id + ".mp4"}});
        std::cout << "emitted " << planName << "\n";
    }
    writeFile(outDir / "manifest.json", manifest.dump(2) + "\n");
    std::cout << "emitted " << manifest["animations"].size() << " short-phrase plans in "
              << outDir.string() << "\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << "\n";
    return 1;
}
