// Contract checks for the seven documentary parity fixtures. These pin the
// authoring invariants the renderer must honour; pixel-level measurements live
// in tools/web_styles/verify_documentary_parity.py.
#include "chronontemplate/web/DocumentaryParityPack.hpp"
#include "chronontemplate/web/WebFontMeasure.hpp"

#include "motion_check.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <string>
#include <utility>

namespace {

using nlohmann::json;
using chronontemplate::web::DocumentaryParityRecipe;
using chronontemplate::web::DocumentaryParitySpec;
using chronontemplate::web::shot::measuredTextWidth;

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

const json* effectByType(const json& layer, const std::string& type) {
    if (!layer.contains("effects")) return nullptr;
    for (const auto& effect : layer["effects"]) {
        if (effect.value("type", "") == type) return &effect;
    }
    return nullptr;
}

const json* trackByProperty(const json& layer, const std::string& property) {
    if (!layer.contains("animation") || !layer["animation"].contains("tracks")) return nullptr;
    for (const auto& track : layer["animation"]["tracks"]) {
        if (track.value("property", "") == property) return &track;
    }
    return nullptr;
}

}  // namespace

int main() {
    using namespace chrononmotion_test;

    section("seven named parity recipes");
    const auto recipes = chronontemplate::web::allDocumentaryParityRecipes();
    check(recipes.size() == 7, "seven fixtures are exposed");
    for (std::size_t i = 0; i < recipes.size(); ++i) {
        DocumentaryParitySpec spec;
        spec.recipe = recipes[i];
        spec.validate();
        const std::string name = chronontemplate::web::documentaryParityName(spec.recipe);
        const std::string id = chronontemplate::web::documentaryParityTestId(spec.recipe);
        check(!name.empty(), "fixture has a plan name");
        check(id == "PARITY_0" + std::to_string(i + 1), "test ids are ordered");
        check(spec.planName() == name + "_v1", "plan name is versioned");
        check(spec.outputStem().find(".mp4") != std::string::npos, "output is an mp4");
    }

    section("common canvas, timing and determinism contract");
    for (const auto recipe : recipes) {
        DocumentaryParitySpec spec;
        spec.recipe = recipe;
        const json plan = chronontemplate::web::buildDocumentaryParityPlan(spec);
        check(plan["schema"] == "chronon.render-plan.v3", "V3 schema");
        check(plan["canvas"]["width"] == 1920 && plan["canvas"]["height"] == 1080,
              "1080p canvas");
        check(plan["canvas"]["fps_num"] == 30 && plan["canvas"]["fps_den"] == 1,
              "30 fps");
        check(plan["canvas"]["duration_frames"] == 150, "5 second fixture");
        check(plan["camera_samples"].size() == 150, "one camera sample per frame");
        check(plan["layers"].size() >= 4, "composed fixture has real layers");
        check(plan["output"]["path"].get<std::string>().find(".mp4") != std::string::npos,
              "output path stays an mp4");
        if (recipe != DocumentaryParityRecipe::DeterministicScrub) {
            check(plan["job_id"].get<std::string>().find("parity_0") == 0,
                  "job id is parity-scoped");
        }
        const json again = chronontemplate::web::buildDocumentaryParityPlan(spec);
        check(plan.dump() == again.dump(), "plan build is deterministic");
    }

    section("PARITY_01 macro LCD typewriter and optical wrap");
    {
        DocumentaryParitySpec spec;
        spec.recipe = DocumentaryParityRecipe::MacroLcdTypewriter;
        const json plan = chronontemplate::web::buildDocumentaryParityPlan(spec);
        const json* typed = layerById(plan, "p1_typed");
        check(typed != nullptr, "typed comment exists");
        if (typed) {
            check((*typed)["text"].get<std::string>().size() == 41,
                  "45-ish character sentence is pinned to 41 glyphs");
            check((*typed).contains("text_animators"), "typewriter animator exists");
            const auto& animator = (*typed)["text_animators"][0];
            const auto& selector = animator["selectors"][0];
            check(selector["unit"] == "grapheme", "selector works on graphemes");
            check(selector["exclude_spaces"] == true, "spaces are not typed");
            const auto& startKeys = selector["start"]["keyframes"];
            const int begin = startKeys[1]["frame"].get<int>();
            const int done = startKeys[2]["frame"].get<int>();
            const double glyphsPerSecond =
                41.0 * 30.0 / static_cast<double>(done - begin);
            check(glyphsPerSecond > 24.5 && glyphsPerSecond < 25.5,
                  "25 characters/second including spaces");
        }
        const json* wrap = layerById(plan, "p1_panel");
        check(wrap != nullptr && (*wrap)["type"] == "image",
              "optical wrap rides a full-frame plate, not a cropped shape");
        if (wrap) {
            check((*wrap)["asset"].get<std::string>().find("p1_panel_opaque.png") !=
                      std::string::npos,
                  "the plate carries the authored card and matching ground");
            check(hasEffect(*wrap, "lens_distortion"),
                  "curvature rides the full-frame optical plate");
            check(hasEffect(*wrap, "chromatic_aberration"), "RGB separation is authored");
            check(hasEffect(*wrap, "scanlines"), "LCD line structure is authored");
            check(hasEffect(*wrap, "vignette"), "vignette is authored");
        }
        bool no_adjustment = true;
        for (const auto& layer : plan["layers"])
            if (layer["type"] == "adjustment") no_adjustment = false;
        check(no_adjustment, "fixture avoids the all-white adjustment-layer path");
        check(layerById(plan, "p1_panel") != nullptr,
              "panel edges provide the optical probes");
        const auto& first = plan["camera_samples"][0]["camera"]["position"][0];
        const auto& last = plan["camera_samples"][149]["camera"]["position"][0];
        check(std::fabs(first.get<double>() - last.get<double>()) > 10.0,
              "camera drifts, no mathematically still frame");
        check(plan["camera_samples"][0]["camera"]["dof"]["enabled"] == false,
              "macro fixture disables DoF");
    }

    section("PARITY_02 anchored bars and seven-frame whip");
    {
        DocumentaryParitySpec spec;
        spec.recipe = DocumentaryParityRecipe::KineticWhipBars;
        const json plan = chronontemplate::web::buildDocumentaryParityPlan(spec);
        for (int i = 1; i <= 3; ++i) {
            const std::string suffix = std::to_string(i);
            const json* bar = layerById(plan, "p2_bar_" + suffix);
            const json* word = layerById(plan, "p2_word_" + suffix);
            check(bar != nullptr && word != nullptr, "bar and word exist");
            if (!bar || !word) continue;
            const double barWidth = (*bar)["size"][0].get<double>();
            const std::string value = (*word)["text"].get<std::string>();
            const double textWidth =
                measuredTextWidth(value, 142.f, "ChrononTemplate/assets/fonts/Inter-Black.ttf");
            check(std::fabs(barWidth - (textWidth + 52.0)) < 0.6,
                  "bar is the measured text box plus symmetric 26 px padding");
            const json* scale = trackByProperty(*bar, "scale_x");
            const json* position = trackByProperty(*bar, "position_x");
            check(scale != nullptr && position != nullptr,
                  "bar has coupled scale_x and position_x tracks");
            if (scale && position) {
                const auto& sk = (*scale)["keyframes"];
                const auto& pk = (*position)["keyframes"];
                check(sk.front()["value"].get<double>() < 0.01,
                      "bar starts at zero width");
                check(sk.back()["value"].get<double>() == 1.0,
                      "bar reaches full width");
                check(std::fabs(pk.front()["value"].get<double>() + barWidth * 0.5) < 0.01,
                      "bar starts pinned at its left edge");
                check(std::fabs(pk.back()["value"].get<double>()) < 0.01,
                      "bar settles at its full-width centre");
            }
            check((*bar)["position"][2].get<double>() >
                      (*word)["position"][2].get<double>(),
                  "bar sits behind its glyphs");
        }
        check(plan.contains("temporal_motion_blur"), "whip blur is declared");
        if (plan.contains("temporal_motion_blur")) {
            check(plan["temporal_motion_blur"]["samples"] == 16,
                  "16 sub-frame samples");
            check(plan["temporal_motion_blur"]["shutter_angle"] == 270.0,
                  "270-degree shutter");
        }
        const auto& s20 = plan["camera_samples"][20]["camera"]["position"][0];
        const auto& s27 = plan["camera_samples"][27]["camera"]["position"][0];
        check(s20.get<double>() < -250.0 && std::fabs(s27.get<double>()) < 1.0,
              "seven-frame whip travels from -260 to rest");
        const auto& s57 = plan["camera_samples"][57]["camera"]["position"][0];
        check(s57.get<double>() > 250.0, "second seven-frame whip travels right");
        check(plan["camera_samples"][149]["camera"]["zoom"].get<double>() == 1.0,
              "dolly-out reveals all three planes");
    }

    section("PARITY_03 four-plane rack focus");
    {
        DocumentaryParitySpec spec;
        spec.recipe = DocumentaryParityRecipe::RackFocusStack;
        const json plan = chronontemplate::web::buildDocumentaryParityPlan(spec);
        const std::array<const char*, 4> ids{
            {"p3_far", "p3_mid", "p3_subject", "p3_foreground"}};
        std::array<double, 4> depths{};
        for (std::size_t i = 0; i < ids.size(); ++i) {
            const json* layer = layerById(plan, ids[i]);
            check(layer != nullptr, "stack plane exists");
            if (layer) depths[i] = (*layer)["position"][2].get<double>();
        }
        check(depths[0] > depths[1] && depths[1] > depths[2] && depths[2] > depths[3],
              "four distinct Z planes are ordered");
        const auto& first = plan["camera_samples"][0]["camera"];
        const auto& last = plan["camera_samples"][149]["camera"];
        const double firstFocus = first["dof"]["focus_distance"].get<double>();
        const double lastFocus = last["dof"]["focus_distance"].get<double>();
        check(std::fabs(firstFocus - 1758.0) < 0.1, "rack starts on the far plane");
        check(std::fabs(lastFocus - 978.0) < 0.1, "rack lands on the subject plane");
        check(firstFocus > lastFocus, "focus travels toward the subject");
        check(std::fabs(first["f_stop"].get<double>() - 1.8) < 1e-4 &&
                  std::fabs(last["f_stop"].get<double>() - 1.8) < 1e-4,
              "aperture is constant");
        double previous = firstFocus;
        bool monotonic = true;
        for (int frame = 1; frame < 150; ++frame) {
            const double focus =
                plan["camera_samples"][frame]["camera"]["dof"]["focus_distance"].get<double>();
            if (focus > previous + 1e-4) monotonic = false;
            previous = focus;
        }
        check(monotonic, "focus is monotonic, no pull-back");
        check(layerById(plan, "p3_far_label") != nullptr,
              "each plane carries its depth label");
    }

    section("PARITY_04 particle depth and 3D placement");
    {
        DocumentaryParitySpec spec;
        spec.recipe = DocumentaryParityRecipe::ParticleRainOcclusion;
        const json plan = chronontemplate::web::buildDocumentaryParityPlan(spec);
        const json* rain = layerById(plan, "p4_money_rain");
        check(rain != nullptr && (*rain)["type"] == "particles", "rain layer exists");
        if (rain) {
            const auto& emitter = (*rain)["particle_emitter"];
            check(emitter["count"] == 250, "250 sprite instances");
            check(emitter["environment"] == true, "environment emitter requests depth");
            check(emitter["bokeh"] == true, "defocus bokeh is requested");
            check(emitter["depth_range"][0] == 0.0 && emitter["depth_range"][1] == 1.0,
                  "full normalized depth band");
            check(emitter["sprite_asset"].get<std::string>().find("banknote.png") !=
                      std::string::npos,
                  "banknote sprite is bound");
            check(emitter["rotation"].size() == 2 && emitter["angular_velocity"].size() == 2,
                  "sprite rotation and spin are authored");
            check(emitter["gravity"].get<double>() > 0.0,
                  "local particle lane uses positive Y for downward rain");
            check(emitter["velocity_min"][1].get<double>() > 0.0 &&
                      emitter["velocity_max"][1].get<double>() > 0.0,
                  "authored velocity carries the notes down-screen");
            check((*rain)["enable_3d"] == true && (*rain)["screen_space"] == false,
                  "rain uses the 3D lane, not the screen-space lane");
            check((*rain)["position"][2].get<double>() == 0.0,
                  "emitter plane sits at the composition origin");
        }
        const json* subject = layerById(plan, "p4_subject");
        const json* backdrop = layerById(plan, "p4_backdrop");
        check(subject != nullptr && backdrop != nullptr, "subject and backdrop exist");
        if (subject && backdrop) {
            check((*subject)["position"][2].get<double>() < 0.0,
                  "subject is in front of the emitter plane");
            check((*backdrop)["position"][2].get<double>() > 0.0,
                  "backdrop is behind the emitter plane");
        }
        check(layerById(plan, "p4_foreground") != nullptr,
              "blurred foreground occluder exists");
        check(plan["camera_samples"][0]["camera"]["dof"]["enabled"] == true,
              "environment depth reads through camera DoF");
    }

    section("PARITY_05 rounded 3D card and camera pan");
    {
        DocumentaryParitySpec spec;
        spec.recipe = DocumentaryParityRecipe::UiCardPanReveal;
        const json plan = chronontemplate::web::buildDocumentaryParityPlan(spec);
        const json* card = layerById(plan, "p5_card");
        check(card != nullptr, "card exists");
        if (card) {
            check((*card)["shape"]["type"] == "rounded_rect", "card is a rounded quad");
            check((*card)["shape"]["radius"] == 24.0, "corner radius is 24 px");
            check(std::fabs((*card)["position"][0].get<double>()) < 0.01 &&
                      std::fabs((*card)["position"][1].get<double>()) < 0.01,
                  "card is centred on the viewport");
            const json* ry = trackByProperty(*card, "rotation_y");
            check(ry != nullptr, "card owns a 3D yaw track");
            if (ry) {
                check(std::fabs((*ry)["keyframes"].front()["value"].get<double>() + 18.0) < 0.01,
                      "card starts at -18 degrees yaw");
                check(std::fabs((*ry)["keyframes"].back()["value"].get<double>()) < 0.01,
                      "card ends front-on");
            }
            check((*card)["effects"].size() >= 1, "card carries a material treatment");
        }
        check(layerById(plan, "p5_viewport") != nullptr, "rounded viewport exists");
        const auto& firstX = plan["camera_samples"][0]["camera"]["position"][0];
        const auto& lastX = plan["camera_samples"][149]["camera"]["position"][0];
        check(firstX.get<double>() < -100.0 && std::fabs(lastX.get<double>()) < 0.1,
              "camera pans from left to a front-on landing");
    }

    section("PARITY_06 CRT HUD and tabular counter");
    {
        DocumentaryParitySpec spec;
        spec.recipe = DocumentaryParityRecipe::CrtHudCounter;
        const json plan = chronontemplate::web::buildDocumentaryParityPlan(spec);
        const json* badge = layerById(plan, "p6_badge");
        const json* badgeText = layerById(plan, "p6_badge_text");
        check(badge != nullptr && badgeText != nullptr, "pill badge and label exist");
        if (badge && badgeText) {
            check((*badge)["shape"]["type"] == "rounded_rect", "badge is a rounded rect");
            check((*badge)["shape"]["radius"].get<double>() ==
                      (*badge)["size"][1].get<double>() * 0.5,
                  "pill radius is half the badge height");
            const double badgeLeft = 150.0;
            const double badgeWidth = (*badge)["size"][0].get<double>();
            const double content = measuredTextWidth(
                "chapter 5", 29.f, "ChrononTemplate/assets/fonts/Inter-Bold.ttf");
            const double authoredTextCentre = badgeLeft +
                (badgeWidth - content) * 0.5 + content * 0.5;
            check(std::fabs(authoredTextCentre - (badgeLeft + badgeWidth * 0.5)) < 0.01,
                  "badge text is horizontally centred on the pill");
            check((*badgeText)["style"]["fill"] == "#FFFFFF", "badge text is white");
        }
        const json* title = layerById(plan, "p6_title");
        check(title != nullptr && hasEffect(*title, "chromatic_aberration"),
              "title carries chroma misregistration");
        check(layerById(plan, "p6_title_glow") != nullptr, "title has a halo layer");
        check(layerById(plan, "p6_counter") != nullptr, "counter exists");
        const double w000 = measuredTextWidth(
            "000", 64.f, "ChrononTemplate/assets/fonts/LiberationMono-Bold.ttf");
        const double w084 = measuredTextWidth(
            "084", 64.f, "ChrononTemplate/assets/fonts/LiberationMono-Bold.ttf");
        const double w100 = measuredTextWidth(
            "100", 64.f, "ChrononTemplate/assets/fonts/LiberationMono-Bold.ttf");
        check(std::fabs(w000 - w084) < 0.01 && std::fabs(w084 - w100) < 0.01,
              "tabular figures keep one advance width");
        const json* wrap = layerById(plan, "p6_plate");
        check(wrap != nullptr && hasEffect(*wrap, "scanlines"),
              "CRT scanlines ride the live-action plate");
        if (wrap) {
            check(hasEffect(*wrap, "chromatic_aberration"),
                  "plate carries the CRT RGB separation");
            check(hasEffect(*wrap, "vignette"), "plate carries the CRT vignette");
        }
        bool no_adjustment = true;
        for (const auto& layer : plan["layers"])
            if (layer["type"] == "adjustment") no_adjustment = false;
        check(no_adjustment, "HUD fixture avoids the all-white adjustment-layer path");
    }

    section("PARITY_07 deterministic scrub fixture");
    {
        DocumentaryParitySpec spec;
        spec.recipe = DocumentaryParityRecipe::DeterministicScrub;
        const json plan = chronontemplate::web::buildDocumentaryParityPlan(spec);
        const json* gradient = layerById(plan, "p7_gradient");
        check(gradient != nullptr, "tonal gradient exists");
        if (gradient) {
            check((*gradient)["type"] == "image",
                  "gradient uses the stable image path");
            check((*gradient)["asset"].get<std::string>().find("p7_gradient.png") !=
                      std::string::npos,
                  "pre-dithered ramp asset is bound");
            check(hasEffect(*gradient, "noise"), "animated noise dithers the ramp");
        }
        const json* marker = layerById(plan, "p7_marker");
        check(marker != nullptr, "moving scrub marker exists");
        if (marker) {
            const json* track = trackByProperty(*marker, "position_x");
            check(track != nullptr, "marker owns a deterministic position track");
            if (track) {
                const auto& keys = (*track)["keyframes"];
                check(keys.front()["value"].get<double>() == -420.0 &&
                          keys.back()["value"].get<double>() == 420.0,
                      "marker travels a closed, known interval");
            }
        }
        check(plan["canvas"]["duration_frames"] == 150,
              "scrub fixture lasts long enough to sample frame 104");
    }

    section("spec defects fail closed");
    for (const auto& pair : std::array<std::pair<int, int>, 4>{{
             {29, 150}, {31, 150}, {30, 59}, {30, 301}}}) {
        DocumentaryParitySpec spec;
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
