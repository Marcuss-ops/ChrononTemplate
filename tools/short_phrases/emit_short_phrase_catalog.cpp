// ChrononTemplate — short-phrase catalog emitter.
//
// Prints `catalog/short_phrase_motion.v1.json` to stdout from the C++-owned
// ShortPhrasePack: the short-phrase archetypes, their selector windows, their tracks
// (layer + per-unit), the semantic emphasis, the exit mode and the decor
// bumper, plus the timing envelope and the RenderingGen selection table.
//
// It is deliberately thin: the recipes live in
// include/chronontemplate/short_phrases/ShortPhrasePack.hpp and this program
// only projects them into the catalog document. Validation is fail-closed, so
// a malformed pack aborts the emit instead of shipping a catalog the consumer
// would reject halfway through a job.
//
// Usage:
//   chronontemplate_emit_short_phrase_catalog > catalog/short_phrase_motion.v1.json

#include <nlohmann/json.hpp>

#include "chronontemplate/short_phrases/ShortPhrasePack.hpp"

#include <exception>
#include <iostream>
#include <set>
#include <string>
#include <vector>

namespace {

    using json = nlohmann::ordered_json;
    using chronontemplate::PhraseKeyframe;
    using chronontemplate::PhraseSelector;
    using chronontemplate::PhraseTrack;
    using chronontemplate::ShortPhraseAnimation;
    using chronontemplate::ShortPhraseDecor;
    using chronontemplate::ShortPhraseDecorDefinition;
    using chronontemplate::ShortPhraseDefinition;
    using chronontemplate::ShortPhraseExit;
    using chronontemplate::ShortPhraseTiming;

    constexpr int kWidth = 1920;
    constexpr int kHeight = 1080;
    constexpr int kFps = 30;
    constexpr int kMaxEnterFrames = 150; // Product styles may spend up to 5 s on a deliberate build.

    std::string familyId(const std::string& id) {
        if (id.rfind("short_phrase_editorial_", 0) == 0) return "editorial";
        if (id.rfind("short_phrase_product_", 0) == 0) return "product_video";
        return "classic";
    }

    std::string subcategoryId(const std::string& id) {
        if (id.find("digital_assembly") != std::string::npos ||
            id.find("chromatic_fringe_title") != std::string::npos) return "computer_character_assembly";
        if (id.find("letter_rise") != std::string::npos || id.find("weight_wave") != std::string::npos ||
            id.find("character") != std::string::npos || id.find("glyph") != std::string::npos ||
            id.find("typewriter") != std::string::npos || id.find("write_on") != std::string::npos) return "letter_by_letter_reveal";
        if (id.find("word") != std::string::npos || id.find("ticker") != std::string::npos ||
            id.find("swap") != std::string::npos || id.find("progressive") != std::string::npos ||
            id.find("line_by_line") != std::string::npos || id.find("split_flap") != std::string::npos) return "word_sequence";
        if (id.find("tracking") != std::string::npos || id.find("weight") != std::string::npos ||
            id.find("color") != std::string::npos || id.find("contrast") != std::string::npos) return "typographic_motion";
        if (id.find("glint") != std::string::npos || id.find("gradient") != std::string::npos ||
            id.find("underline") != std::string::npos || id.find("rule") != std::string::npos) return "light_and_accent";
        if (id.find("parallax") != std::string::npos || id.find("glide") != std::string::npos ||
            id.find("slide") != std::string::npos || id.find("curve") != std::string::npos) return "depth_and_space";
        if (id.find("pill") != std::string::npos || id.find("shape") != std::string::npos) return "shape_reveal";
        return "kinetic_reveal";
    }

    [[noreturn]] void fail(const std::string& message) {
        throw std::runtime_error("emit_short_phrase_catalog: " + message);
    }

    void validateTrack(const PhraseTrack& track, const std::string& where) {
        if (track.property.empty()) fail(where + " needs a non-empty property");
        if (track.keyframes.size() < 2) fail(where + " needs at least two keyframes");
        if (track.keyframes.front().frame != 0) fail(where + " must start at frame 0");
        int previous = -1;
        for (const PhraseKeyframe& key : track.keyframes) {
            if (key.frame < 0) fail(where + " has a negative keyframe frame");
            if (key.frame <= previous) fail(where + " keyframe frames must be strictly increasing");
            previous = key.frame;
        }
    }

    json trackJson(const PhraseTrack& track) {
        json keys = json::array();
        for (const PhraseKeyframe& key : track.keyframes) {
            keys.push_back({{"frame", key.frame}, {"value", key.value}});
        }
        return json{{"property", track.property}, {"easing", track.easing}, {"keyframes", keys}};
    }

    json selectorJson(const PhraseSelector& selector) {
        return json{{"unit", selector.unit}, {"order", selector.order}, {"window", selector.window}};
    }

    /// The selector the text engine is configured with: the recipe's first text
    /// animator, or a neutral whole-run window for a layer-only entrance.
    json recipeSelector(const ShortPhraseDefinition& def) {
        if (def.textAnimators.empty()) {
            return json{{"unit", "layer"}, {"order", "forward"}, {"window", "full"}};
        }
        return selectorJson(def.textAnimators.front().selector);
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

    const char* decorId(ShortPhraseDecor decor) noexcept {
        switch (decor) {
            case ShortPhraseDecor::None: return "none";
            case ShortPhraseDecor::StarBumper: return "star_bumper";
        }
        return "unknown";
    }

    json recipeJson(ShortPhraseAnimation animation, std::set<std::string>& ids) {
        const ShortPhraseDefinition def = chronontemplate::definition(animation);
        if (def.id != chronontemplate::name(animation)) fail(def.id + ": id disagrees with name()");
        if (def.id.rfind("short_phrase_", 0) != 0) fail(def.id + ": wire id needs the short_phrase_ prefix");
        if (!ids.insert(def.id).second) fail("duplicate recipe id " + def.id);
        if (def.title.empty()) fail(def.id + ": needs a human title");
        if (def.phrase.empty()) fail(def.id + ": needs a showcase phrase");
        if (def.enter <= 0 || def.enter > kMaxEnterFrames) fail(def.id + ": enter is outside the short-phrase range");

        const std::size_t words = chronontemplate::shortPhraseWordCount(def.phrase);
        if (words == 0) fail(def.id + ": the showcase phrase has no words");
        for (const std::size_t word : def.emphasis) {
            if (word >= words) fail(def.id + ": emphasis names a word the phrase does not have");
        }

        json tracks = json::array();
        for (std::size_t i = 0; i < def.tracks.size(); ++i) {
            validateTrack(def.tracks[i], def.id + ".tracks[" + std::to_string(i) + "]");
            tracks.push_back(trackJson(def.tracks[i]));
        }

        bool closesOpacity = false;
        bool hasRevealWindow = false;
        json animators = json::array();
        for (std::size_t i = 0; i < def.textAnimators.size(); ++i) {
            const auto& animator = def.textAnimators[i];
            const std::string where = def.id + ".textAnimators[" + std::to_string(i) + "]";
            const std::string unit = animator.selector.unit;
            const std::string window = animator.selector.window;
            if (unit != "glyph" && unit != "word" && unit != "line") fail(where + ": unit must be glyph, word, or line");
            const bool indexedWindow = window.rfind("pick:", 0) == 0;
            if (window != "full" && window != "reveal" && window != "reveal_soft" && window != "band" && !indexedWindow) {
                fail(where + ": window must be full | reveal | reveal_soft | band");
            }
            if (window == "reveal" || window == "reveal_soft") hasRevealWindow = true;

            json properties = json::array();
            for (std::size_t j = 0; j < animator.properties.size(); ++j) {
                const PhraseTrack& track = animator.properties[j];
                validateTrack(track, where + ".properties[" + std::to_string(j) + "]");
                if (track.property == "opacity" && track.keyframes.back().value < 1.f) closesOpacity = true;
                properties.push_back(trackJson(track));
            }
            if (properties.empty()) fail(where + ": needs at least one property");
            animators.push_back({{"selector", selectorJson(animator.selector)}, {"properties", properties}});
        }
        for (const PhraseTrack& track : def.tracks) {
            if (track.property == "opacity" && track.keyframes.back().value < 1.f) closesOpacity = true;
        }
        // A reveal window arrives visible by construction; anything else must end open.
        // Product videos can deliberately hand the final beat to a native
        // text overlay (for example a line replacement), or close the layer
        // on the exit. The reveal-window invariant applies to entrance
        // recipes only; applying it to the product composition falsely
        // rejected those valid handoffs.
        const bool productVideo = def.id.rfind("short_phrase_product_", 0) == 0;
        if (closesOpacity && !hasRevealWindow && !productVideo) {
            fail(def.id + ": opacity closes without a reveal window");
        }

        const ShortPhraseTiming timing = chronontemplate::shortPhraseTiming(static_cast<int>(words));
        const int total = timing.inFrames + timing.holdFrames + timing.outFrames;
        if (timing.minFrames <= 0 || timing.minFrames > timing.maxFrames) {
            fail(def.id + ": the frame bracket is not ordered");
        }
        if (total < timing.minFrames || total > timing.maxFrames) {
            fail(def.id + ": in + hold + out sits outside its bracket");
        }

        json accents = json::array();
        for (const auto& accent : def.accents) {
            json accentTracks = json::array();
            for (const auto& t : accent.tracks) {
                validateTrack(t, def.id + "." + accent.id);
                accentTracks.push_back(trackJson(t));
            }
            accents.push_back({{"id", accent.id}, {"color", accent.color},
                               {"width", accent.width}, {"height", accent.height},
                               {"y_offset", accent.y_offset}, {"radius", accent.radius},
                               {"opacity", accent.opacity}, {"tracks", accentTracks}});
        }
        json emphasis = json::array();
        for (const std::size_t word : def.emphasis) emphasis.push_back(word);
        const bool hasUnsupportedTextAnimatorRotation = std::any_of(
                def.textAnimators.begin(), def.textAnimators.end(), [](const auto& animator) {
                    return std::any_of(animator.properties.begin(), animator.properties.end(),
                                       [](const PhraseTrack& track) {
                                           return track.property == "rotation";
                                       });
                });
        json targets = nullptr;
        if (!hasUnsupportedTextAnimatorRotation) {
            targets = json::array({"short_phrase"});
            if (!def.textAnimators.empty()) targets.push_back("caption");
        }
        json overlays = json::array();
        for (const auto& overlay : def.textOverlays) {
            json overlayTracks = json::array();
            for (const auto& track : overlay.tracks) {
                validateTrack(track, def.id + "." + overlay.id);
                overlayTracks.push_back(trackJson(track));
            }
            overlays.push_back({{"id", overlay.id}, {"text", overlay.text},
                                {"fill", overlay.fill}, {"offset_x", overlay.offset_x},
                                {"offset_y", overlay.offset_y}, {"opacity", overlay.opacity},
                                {"tracks", overlayTracks}});
        }

        return json{
                {"id", def.id},
                {"family", familyId(def.id)},
                {"subcategory", subcategoryId(def.id)},
                {"targets", targets},
                {"title", def.title},
                {"phrase", def.phrase},
                {"enter", def.enter},
                {"word_count", words},
                {"selector", recipeSelector(def)},
                {"tracks", tracks},
                {"text_animators", animators},
                {"text_overlays", overlays},
                {"accents", accents},
                {"font_size", def.font_size},
                {"light", def.light},
                {"white_background", def.white_background},
                {"emphasis", emphasis},
                {"exit", exitId(def.exit)},
                {"decor", def.decor == ShortPhraseDecor::None ? json(nullptr) : json(decorId(def.decor))},
                {"adaptation_note", def.adaptation_note},
                {"timing", {{"min_frames", timing.minFrames},
                            {"max_frames", timing.maxFrames},
                            {"in_frames", timing.inFrames},
                            {"hold_frames", timing.holdFrames},
                            {"out_frames", timing.outFrames}}}};
    }

    json decorJson(ShortPhraseDecor decor) {
        const ShortPhraseDecorDefinition def = chronontemplate::shortPhraseDecor(decor);
        if (def.id.empty()) fail("decor needs an id");
        if (def.shape.empty()) fail(def.id + ": needs a shape");
        if (def.tracks.empty()) fail(def.id + ": needs motion");
        json tracks = json::array();
        for (std::size_t i = 0; i < def.tracks.size(); ++i) {
            validateTrack(def.tracks[i], def.id + ".tracks[" + std::to_string(i) + "]");
            tracks.push_back(trackJson(def.tracks[i]));
        }
        return json{{"id", def.id}, {"shape", def.shape}, {"tracks", tracks}};
    }

    json selectionJson() {
        json selection = json::object();
        for (int words = 1; words <= 5; ++words) {
            const std::vector<ShortPhraseAnimation> picks = chronontemplate::shortPhraseSuggestions(words);
            if (picks.empty()) fail("word count " + std::to_string(words) + " has no suggested recipe");
            json ids = json::array();
            for (const ShortPhraseAnimation pick : picks) ids.push_back(chronontemplate::name(pick));
            selection[std::to_string(words)] = ids;
        }
        return selection;
    }

}// namespace

int main() {
    try {
        const std::vector<ShortPhraseAnimation> animations = chronontemplate::shortPhraseAnimations();
        if (animations.size() != 50) fail("expected twelve original, thirteen editorial, and twenty-five product-motion short-phrase archetypes");

        std::set<std::string> ids;
        json recipes = json::array();
        for (const ShortPhraseAnimation animation : animations) {
            recipes.push_back(recipeJson(animation, ids));
        }

        if (!chronontemplate::shortPhraseSuggestions(0).empty() ||
            !chronontemplate::shortPhraseSuggestions(6).empty()) {
            fail("the short-phrase family must cover exactly 1..5 words");
        }

        json out = json::object();
        out["schema"] = "chronontemplate.short-phrase-motion.v1";
        out["version"] = 1;
        out["catalog_id"] = "short_phrase_motion_v1";
        out["source"] = "chronontemplate::ShortPhrasePack";
        out["canvas"] = {{"width", kWidth}, {"height", kHeight}, {"fps", kFps}};
        out["word_range"] = json::array({1, 5});
        out["exit_modes"] = json::array({"reverse", "forward", "wipe", "scatter", "arc_dissolve"});
        out["decor"] = json::array({decorJson(ShortPhraseDecor::StarBumper)});
        out["recipes"] = recipes;
        out["selection"] = selectionJson();

        std::cout << out.dump(2) << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 1;
    }
}
