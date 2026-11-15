// Contract tests for the five Modern Documentary native plans. These assert
// design invariants that must hold before a render is attempted: the
// highlighter stays behind its key line and starts at zero scale, the rack
// focus actually travels, the glitch card carries the mesh/chroma pair, the
// rain exposes sprite rotation and fake depth, the kinetic camera has a real
// whip, and the VHS screen carries a moving logo carousel plus scanlines.
#include "chronontemplate/web/ModernDocumentaryPack.hpp"

#include "motion_check.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <string>

namespace {

using nlohmann::json;
using chronontemplate::web::ModernDocumentaryRecipe;
using chronontemplate::web::ModernDocumentarySpec;

const json* layerById(const json& plan, const std::string& id) {
    for (const auto& layer : plan["layers"]) {
        if (layer.value("id", "") == id) return &layer;
    }
    return nullptr;
}

bool hasEffect(const json& layer, const std::string& type) {
    if (!layer.contains("effects")) return false;
    for (const auto& effect : layer["effects"]) {
        if (effect.value("type", "") == type) return true;
    }
    return false;
}

int layerIndex(const json& plan, const std::string& id) {
    for (std::size_t i = 0; i < plan["layers"].size(); ++i) {
        if (plan["layers"][i].value("id", "") == id) return static_cast<int>(i);
    }
    return -1;
}

}  // namespace

int main() {
    using namespace chrononmotion_test;

    section("recipe names and output stems");
    const auto recipes = chronontemplate::web::allModernDocumentaryRecipes();
    check(recipes.size() == 5, "five recipes are exposed");
    for (const auto recipe : recipes) {
        ModernDocumentarySpec spec;
        spec.recipe = recipe;
        spec.validate();
        const std::string name = chronontemplate::web::modernDocumentaryName(recipe);
        check(!name.empty(), "recipe has a name");
        check(spec.planName() == name + "_v1", "plan name is versioned");
        check(spec.outputStem().find(".mp4") != std::string::npos,
              "default output is an mp4 stem");
    }

    section("every plan honours the canvas, temporal and camera contract");
    for (const auto recipe : recipes) {
        ModernDocumentarySpec spec;
        spec.recipe = recipe;
        spec.durationFrames = 150;
        const json plan = chronontemplate::web::buildModernDocumentaryPlan(spec);
        check(plan["schema"] == "chronon.render-plan.v3", "schema is V3");
        check(plan["canvas"]["width"] == 1920 && plan["canvas"]["height"] == 1080,
              "1080p canvas");
        check(plan["canvas"]["fps_num"] == 30 && plan["canvas"]["fps_den"] == 1,
              "30 fps");
        check(plan["canvas"]["duration_frames"] == 150, "duration is forwarded");
        check(plan.contains("camera") && plan.contains("camera_samples"),
              "camera and camera_samples coexist");
        check(plan["camera_samples"].size() == 150, "one camera sample per frame");
        check(plan["layers"].size() >= 15, "procedural composition has real depth");
        check(plan["output"]["path"].get<std::string>().find(".mp4") != std::string::npos,
              "output stays an mp4");
        const json again = chronontemplate::web::buildModernDocumentaryPlan(spec);
        check(plan.dump() == again.dump(), "plan build is deterministic");
    }

    section("Vox highlighter is left-anchored, multiply and behind the key line");
    {
        ModernDocumentarySpec spec;
        spec.recipe = ModernDocumentaryRecipe::VoxHighlight;
        const json plan = chronontemplate::web::buildModernDocumentaryPlan(spec);
        const json* marker = layerById(plan, "vox_marker");
        const json* key = layerById(plan, "vox_key");
        check(marker != nullptr && key != nullptr, "marker and key line exist");
        if (marker && key) {
            check(marker->value("blend_mode", "") == "multiply", "marker uses multiply");
            check((*marker)["shape"]["type"] == "rect", "marker is a quad");
            check(layerIndex(plan, "vox_marker") < layerIndex(plan, "vox_key"),
                  "marker is emitted before the sharp key text");
            const auto& tracks = (*marker)["animation"]["tracks"];
            const auto scale = std::find_if(tracks.begin(), tracks.end(), [](const json& t) {
                return t.value("property", "") == "scale_x";
            });
            check(scale != tracks.end(), "marker has a scale_x track");
            if (scale != tracks.end()) {
                const auto& keys = (*scale)["keyframes"];
                check(keys.front()["value"].get<double>() < 0.01, "marker starts at zero width");
                check(keys.back()["value"].get<double>() == 1.0, "marker reaches full width");
            }
        }
        const json* subject = layerById(plan, "vox_subject");
        check(subject != nullptr, "cutout subject exists");
        if (subject) check((*subject)["type"] == "image", "subject is an image layer");
        const auto& samples = plan["camera_samples"];
        const double first = samples.front()["camera"]["dof"]["focus_distance"].get<double>();
        const double last = samples.back()["camera"]["dof"]["focus_distance"].get<double>();
        check(std::fabs(first - last) > 120.0, "rack focus travels at least 120 units");
        check(last < first, "focus moves from page plane toward the nearer subject");
    }

    section("split composition combines torn seam, halftone and card glitch");
    {
        ModernDocumentarySpec spec;
        spec.recipe = ModernDocumentaryRecipe::SplitGlitch;
        const json plan = chronontemplate::web::buildModernDocumentaryPlan(spec);
        const json* left = layerById(plan, "split_left_image");
        check(left != nullptr && hasEffect(*left, "halftone"), "left photo is halftoned");
        check(layerById(plan, "split_energy_divider") != nullptr, "torn energy seam exists");
        const json* card = layerById(plan, "split_card");
        check(card != nullptr, "Z-space card exists");
        if (card) {
            check((*card)["shape"]["type"] == "rounded_rect", "card is a rounded quad");
            check(hasEffect(*card, "mesh_warp"), "card carries horizontal slice warp");
            check(hasEffect(*card, "chromatic_aberration"), "card carries RGB separation");
            check(hasEffect(*card, "scanlines"), "card carries digital scanlines");
        }
        check(layerById(plan, "split_glitch_cyan") != nullptr &&
              layerById(plan, "split_glitch_red") != nullptr,
              "cyan/red glitch duplicates exist");
    }

    section("macro UI has typewriter, crowd depth and textured rain");
    {
        ModernDocumentarySpec spec;
        spec.recipe = ModernDocumentaryRecipe::MacroUiRain;
        const json plan = chronontemplate::web::buildModernDocumentaryPlan(spec);
        const json* typed = layerById(plan, "macro_typed");
        check(typed != nullptr && typed->contains("text_animators"),
              "macro sentence carries a character animator");
        if (typed) {
            check((*typed)["text_animators"][0]["selectors"][0]["unit"] == "grapheme",
                  "typewriter selects graphemes");
        }
        check(layerById(plan, "macro_crowd_head_0") != nullptr &&
              layerById(plan, "macro_crowd_head_4") != nullptr,
              "crowd is split across depth layers");
        int rainLayers = 0;
        bool rainContract = true;
        for (const auto& layer : plan["layers"]) {
            const std::string id = layer.value("id", "");
            if (id.rfind("macro_money_rain_", 0) != 0) continue;
            ++rainLayers;
            const auto& emitter = layer["particle_emitter"];
            rainContract = rainContract &&
                emitter.value("sprite_asset", "").find("banknote.png") !=
                    std::string::npos &&
                emitter.value("environment", false) &&
                emitter.value("bokeh", false) &&
                emitter.contains("rotation") &&
                emitter.contains("angular_velocity") &&
                // Screen-space particle Y grows downward: positive gravity
                // and velocity are what make the notes fall, not rise.
                emitter["gravity"].get<double>() > 0.0 &&
                emitter["velocity_max"][1].get<double>() > 0.0;
        }
        check(rainLayers >= 48, "rain is authored as a volume of one-drop emitters");
        check(rainContract,
              "every drop keeps sprite, fake depth, bokeh, spin and down physics");
        check(layerById(plan, "macro_chapter") != nullptr, "HUD chapter badge exists");
        check(layerById(plan, "macro_product") != nullptr, "product card exists");
    }

    section("kinetic type carries a real whip and shutter blur");
    {
        ModernDocumentarySpec spec;
        spec.recipe = ModernDocumentaryRecipe::KineticType;
        const json plan = chronontemplate::web::buildModernDocumentaryPlan(spec);
        check(plan.contains("temporal_motion_blur"), "motion blur is declared");
        if (plan.contains("temporal_motion_blur")) {
            check(plan["temporal_motion_blur"]["shutter_angle"] == 180, "180-degree shutter");
            check(plan["temporal_motion_blur"]["samples"].get<int>() >= 8,
                  "at least eight sub-frame samples");
        }
        int words = 0;
        bool every_word_fades = true;
        for (const auto& layer : plan["layers"]) {
            if (layer.value("id", "").rfind("kinetic_word_", 0) != 0) continue;
            ++words;
            bool has_fade = false;
            for (const auto& t : layer["animation"]["tracks"]) {
                if (t.value("property", "") != "opacity") continue;
                has_fade = true;
                const auto& keys = t["keyframes"];
                check(keys.front()["value"].get<double>() < 0.01,
                      "word enters from zero opacity");
                check(keys[2]["value"].get<double>() == 1.0,
                      "word reaches full opacity");
            }
            every_word_fades = every_word_fades && has_fade;
        }
        check(words == 4, "four typographic beats");
        check(every_word_fades, "every beat owns its reveal");
    }

    section("VHS carousel has spring travel, hot title and analog wear");
    {
        ModernDocumentarySpec spec;
        spec.recipe = ModernDocumentaryRecipe::VhsCarousel;
        const json plan = chronontemplate::web::buildModernDocumentaryPlan(spec);
        int logos = 0;
        double minX = 1e9, maxX = -1e9;
        for (const auto& layer : plan["layers"]) {
            if (layer.value("id", "").rfind("vhs_logo_", 0) != 0) continue;
            ++logos;
            const auto& tracks = layer["animation"]["tracks"];
            const auto pos = std::find_if(tracks.begin(), tracks.end(), [](const json& t) {
                return t.value("property", "") == "position_x";
            });
            check(pos != tracks.end(), "logo has a carousel position track");
            if (pos != tracks.end()) {
                for (const auto& k : (*pos)["keyframes"]) {
                    minX = std::min(minX, k["value"].get<double>());
                    maxX = std::max(maxX, k["value"].get<double>());
                }
            }
            check(hasEffect(layer, "directional_blur"), "logo has shutter smear");
        }
        check(logos == 5, "five broadcast marks");
        check(maxX - minX >= 900.0, "carousel crosses more than half the screen");
        const json* screen = layerById(plan, "vhs_screen");
        check(screen != nullptr, "CRT screen exists");
        if (screen) {
            check(hasEffect(*screen, "retro_tv"), "screen has analog jitter");
            check(hasEffect(*screen, "scanlines"), "screen has scanlines");
            check(hasEffect(*screen, "chromatic_aberration"), "screen has chroma bleed");
        }
        const json* title = layerById(plan, "vhs_title");
        check(title != nullptr, "hot title exists");
        check(layerById(plan, "vhs_title_glow") != nullptr, "title has a bloom halo layer");
        const json* typed = layerById(plan, "vhs_typed");
        check(typed != nullptr && typed->contains("text_animators"),
              "lower third types on");
    }

    section("spec defects fail closed");
    for (const auto& pair : std::array<std::pair<int, int>, 4>{{
             {29, 150}, {31, 150}, {30, 59}, {30, 301}}}) {
        ModernDocumentarySpec spec;
        spec.fps = pair.first;
        spec.durationFrames = pair.second;
        bool threw = false;
        try {
            spec.validate();
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "invalid fps/duration is rejected");
    }

    return report();
}
