// ChrononTemplate — camera motion catalog emitter.
//
// Prints `catalog/camera_motion_pack.v1.json` to stdout from the C++-owned
// CameraMotionPack: the fifteen spec rows (durations, distance fractions,
// frame-fraction travel, degrees, focus percents, easing names, backend
// requirements), the family order, the planner selection table, the
// intensity ladder and the easing map.
//
// It is deliberately thin: the recipes live in
// include/chronontemplate/camera_roll/CameraMotionPack.hpp and this program
// only projects them into the catalog document. Validation is fail-closed,
// so a malformed pack aborts the emit instead of shipping a catalog the
// consumer would reject halfway through a job.
//
// Usage:
//   chronontemplate_emit_camera_motion_catalog > catalog/camera_motion_pack.v1.json

#include <nlohmann/json.hpp>

#include "chronontemplate/camera_roll/CameraMotionPack.hpp"

#include <exception>
#include <iostream>
#include <set>
#include <string>
#include <vector>

namespace {

    using json = nlohmann::ordered_json;
    using chronontemplate::CameraContentKind;
    using chronontemplate::CameraMotionFamily;
    using chronontemplate::CameraMotionIntensity;
    using chronontemplate::CameraMotionPreset;
    using chronontemplate::CameraMotionSpec;

    [[noreturn]] void fail(const std::string& message) {
        std::cerr << "emit_camera_motion_catalog: " << message << "\n";
        std::exit(1);
    }

    std::string familyId(CameraMotionFamily family) {
        switch (family) {
            case CameraMotionFamily::EditorialTitle: return "editorial_title";
            case CameraMotionFamily::PhotoDocumentary: return "photo_documentary";
            case CameraMotionFamily::MapGeo: return "map_geo";
            case CameraMotionFamily::DashboardUI: return "dashboard_ui";
            case CameraMotionFamily::Transition: return "transition";
        }
        return "unknown";
    }

    std::string contentKindId(CameraContentKind kind) {
        using K = CameraContentKind;
        switch (kind) {
            case K::TitleOnWhite: return "title_on_white";
            case K::ImpactWord: return "impact_word";
            case K::SinglePortrait: return "single_portrait";
            case K::PortraitBuildingText: return "portrait_building_text";
            case K::ArchivePhoto: return "archive_photo";
            case K::MapCountry: return "map_country";
            case K::MapTwoCountries: return "map_two_countries";
            case K::MapRoute: return "map_route";
            case K::DashboardChart: return "dashboard_chart";
            case K::PremiumUI3D: return "premium_ui_3d";
            case K::FastCut: return "fast_cut";
            case K::ObjectPass: return "object_pass";
            case K::BlurPass: return "blur_pass";
        }
        return "unknown";
    }

    json recipeJson(const CameraMotionSpec& spec, std::set<std::string>& ids) {
        if (spec.id == nullptr || std::string(spec.id).empty()) fail("preset without id");
        if (!ids.insert(spec.id).second) fail(std::string("duplicate id ") + spec.id);
        if (spec.durationFrames < 8) fail(std::string(spec.id) + ": duration under 8 frames");
        json requirements = {
            {"dof", spec.needsDof},
            {"planes_25d", spec.needs25D},
            {"multi_plane", spec.needsMultiPlane},
            {"two_shot", spec.twoShot},
            {"occluder", spec.needsOccluder},
            {"high_energy", spec.highEnergy},
        };
        json recipe = {
            {"id", spec.id},
            {"family", familyId(spec.family)},
            {"duration_frames", spec.durationFrames},
            {"distance", {{"start", spec.distStart}, {"mid", spec.distMid},
                           {"mid_at", spec.distMidAt}, {"end", spec.distEnd}}},
            {"lateral", {{"x_start", spec.xStart}, {"x_mid", spec.xMid}, {"x_end", spec.xEnd},
                          {"y_start", spec.yStart}, {"y_mid", spec.yMid}, {"y_end", spec.yEnd},
                          {"pos_mid_at", spec.posMidAt}}},
            {"travel_window", {{"start", spec.travelStart}, {"end", spec.travelEnd}}},
            {"angles_deg", {{"yaw_start", spec.yawStart}, {"yaw_end", spec.yawEnd},
                             {"pitch_start", spec.pitchStart}, {"pitch_end", spec.pitchEnd},
                             {"roll_start", spec.rollStart}, {"roll_peak", spec.rollPeak},
                             {"roll_end", spec.rollEnd}}},
            {"focus_pct", {{"start", spec.focusStart}, {"end", spec.focusEnd}}},
            {"easing", spec.easing == nullptr ? "" : spec.easing},
            {"requirements", std::move(requirements)},
            {"cut_at", spec.cutAt},
            {"snap_in", spec.snapIn},
        };
        if (spec.easing == nullptr || std::string(spec.easing).empty()) {
            fail(std::string(spec.id) + ": unnamed easing");
        }
        // Easing names must resolve — the catalog never ships a curve the
        // resolver cannot lower.
        chronontemplate::cameraMotionEasingFor(spec.easing);
        return recipe;
    }

}// namespace

int main() {
    try {
        const std::vector<CameraMotionPreset> presets = chronontemplate::cameraMotionPresets();
        const std::vector<std::string> ids = chronontemplate::cameraMotionPresetIds();
        if (presets.size() != 15 || ids.size() != presets.size()) fail("expected fifteen camera motion presets");

        std::set<std::string> seen;
        json recipes = json::array();
        for (std::size_t index = 0; index < presets.size(); ++index) {
            const CameraMotionPreset preset = presets[index];
            const CameraMotionSpec& spec = chronontemplate::cameraMotionSpecFor(preset);
            if (spec.id == nullptr || ids[index] != spec.id) fail("roster ids and motion spec order disagree");
            recipes.push_back(recipeJson(spec, seen));
        }

        json selection = json::object();
        for (const CameraContentKind kind : chronontemplate::cameraContentKinds()) {
            json picks = json::array();
            for (const CameraMotionPreset preset : chronontemplate::cameraMotionSuggestions(kind)) {
                const std::string id = chronontemplate::cameraMotionPresetId(preset);
                if (seen.count(id) == 0) fail("selection names unknown preset " + id);
                picks.push_back(id);
            }
            if (picks.empty()) fail("content kind without suggestions");
            selection[contentKindId(kind)] = std::move(picks);
        }

        json out = json::object();
        out["schema"] = "chronontemplate.camera-motion-pack.v1";
        out["version"] = 1;
        out["catalog_id"] = "camera_motion_pack_v1";
        out["source"] = "chronontemplate::CameraMotionPack";
        out["fps"] = 30;
        out["units"] = {{"distance", "fraction of the reference framing"},
                        {"lateral", "fraction of the frame width/height"},
                        {"angles", "degrees"},
                        {"focus", "percent of the configured depth interval"}};
        out["intensity_ladder"] = {{"subtle", 0.5}, {"normal", 1.0}, {"strong", 1.5}};
        out["easing_map"] = {{"cinematic", "easeInOut"}, {"smooth", "easeInOut"},
                             {"gentle_out", "easeOut"}, {"snappy_out", "expoOut"},
                             {"whip_in", "easeIn"}, {"whip_out", "expoOut"}};
        out["families"] = {"editorial_title", "photo_documentary", "map_geo", "dashboard_ui",
                           "transition"};
        out["recipes"] = std::move(recipes);
        out["selection"] = std::move(selection);

        std::cout << out.dump(2) << "\n";
        return 0;
    } catch (const std::exception& error) {
        fail(error.what());
    }
}
