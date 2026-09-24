// ChrononTemplate — catalog emitter.
//
// This tool is the producer of the canonical catalog artifact the renderer
// consumes. The data file (`catalog/motion_catalog.v1.json`) owns the motion
// vocabulary, the overlay preset-id vocabulary and the corpus selections; this
// program owns everything that is genuinely C++-owned — the template catalog
// and the composition presets — and it is the only writer of the emitted
// document, so a consumer can never read a half-owned catalog:
//
//   catalog/motion_catalog.v1.json   data      (ids, keyframes, selections)
//   chrononmotion::templates         C++       (TemplateId -> name)
//   chronontemplate::Final3DPreset   C++       (Final3DPreset -> name, glow policy)
//                 │
//                 ▼  emit_catalog
//   chronontemplate_catalog.v1.json  emitted   (consumed by RenderingGen)
//
// Validation is fail-closed: a duplicate id, a malformed keyframe or a
// selection that names an id the catalog no longer defines aborts the emit
// instead of shipping a catalog the renderer would resolve to nothing.
//
// Usage:
//   chronontemplate_emit_catalog [--catalog <in.json>] [--out <out.json>]
//
// With no arguments it reads the checked-in data file and writes the emitted
// document to stdout.

#include <nlohmann/json.hpp>

#include "chrononmotion/templates/Templates.hpp"
#include "chronontemplate/Presets.hpp"

#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

    using json = nlohmann::ordered_json;

    constexpr std::int64_t kSchemaVersion = 1;
    constexpr const char* kSource = "ChrononTemplate";

    [[noreturn]] void fail(const std::string& message) {
        throw std::runtime_error("emit_catalog: " + message);
    }

    void requireObject(const json& value, const std::string& where) {
        if (!value.is_object()) fail(where + " must be a JSON object");
    }

    void requireArray(const json& value, const std::string& where) {
        if (!value.is_array()) fail(where + " must be a JSON array");
    }

    /// A keyframe is the one structure whose shape a consumer blindly trusts:
    /// `frame` is an integer index and `value` is a number or a string. A
    /// malformed keyframe would surface as a render-time type error, so it is
    /// rejected here instead.
    void validateKeyframe(const json& keyframe, const std::string& where) {
        requireObject(keyframe, where);
        if (!keyframe.contains("frame") || !keyframe["frame"].is_number_integer()) {
            fail(where + " needs an integer `frame`");
        }
        if (!keyframe.contains("value")) fail(where + " needs a `value`");
        const json& value = keyframe["value"];
        if (value.is_array()) {
            if (value.empty() || value.size() > 4) {
                fail(where + " has an array `value` with wrong arity (need 1..4 numbers)");
            }
            for (std::size_t i = 0; i < value.size(); ++i) {
                if (!value[i].is_number()) {
                    fail(where + " has an array `value` whose element " + std::to_string(i) + " is not a number");
                }
            }
            return;
        }
        if (!value.is_number() && !value.is_string() && !value.is_boolean()) {
            fail(where + " has a `value` that is not a number, string or boolean");
        }
    }

    void validateTrack(const json& track, const std::string& where) {
        requireObject(track, where);
        if (!track.contains("property") || !track["property"].is_string() ||
            track["property"].get<std::string>().empty()) {
            fail(where + " needs a non-empty `property`");
        }
        if (!track.contains("keyframes")) fail(where + " needs `keyframes`");
        requireArray(track["keyframes"], where + ".keyframes");
        if (track["keyframes"].size() < 2) fail(where + " needs at least two keyframes");
        for (std::size_t i = 0; i < track["keyframes"].size(); ++i) {
            validateKeyframe(track["keyframes"][i], where + ".keyframes[" + std::to_string(i) + "]");
            const auto frame = track["keyframes"][i]["frame"].get<std::int64_t>();
            if (frame < 0) fail(where + " has a negative keyframe frame");
            if (i == 0 && frame != 0) fail(where + " must start at frame 0");
            if (i > 0) {
                const auto previous = track["keyframes"][i - 1]["frame"].get<std::int64_t>();
                if (frame <= previous) fail(where + " keyframe frames must be strictly increasing");
            }
        }
    }

    /// The two properties whose resting value is 1. A `scale` or `opacity`
    /// entrance track that does not END there is not an entrance, it is a
    /// vanishing act: the compiler treats `tracks` as the entrance and
    /// synthesizes the exit from the resting value, so a track ending at 0 makes
    /// the text disappear as it enters and then reel it back in — which is how
    /// `scale_out` shipped a clip whose text collapsed to nothing at frame 24,
    /// sat clipped at the canvas edge, and popped back at frame 119.
    ///
    /// Every other track in this catalog already follows the convention (all 91
    /// of them end at 1); this gate is what keeps the next one honest. It is
    /// deliberately scoped to `motions[].tracks[]`: those are the layer-level
    /// entrances with the contract above, while `text_animators[].properties[]`
    /// are per-unit dynamics whose resting values are per-property.
    void validateRestingEntrance(const json& track, const std::string& where) {
        const std::string property = track["property"].get<std::string>();
        if (property != "scale" && property != "opacity") return;
        const json& keyframes = track["keyframes"];
        const json& last = keyframes[keyframes.size() - 1]["value"];
        if (!last.is_number() || last.get<double>() != 1.0) {
            fail(where + " (" + property + ") must end at the resting value 1; an entrance that "
                 "scales or fades the text to nothing hides it instead of revealing it");
        }
    }

    /// Validates the motion catalog and returns the set of defined motion ids.
    std::set<std::string> validateMotions(const json& motions) {
        requireArray(motions, "motions");
        if (motions.empty()) fail("motions must not be empty");
        std::set<std::string> ids;
        for (std::size_t i = 0; i < motions.size(); ++i) {
            const json& motion = motions[i];
            const std::string where = "motions[" + std::to_string(i) + "]";
            requireObject(motion, where);
            if (!motion.contains("id") || !motion["id"].is_string() ||
                motion["id"].get<std::string>().empty()) {
                fail(where + " needs a non-empty `id`");
            }
            const std::string id = motion["id"].get<std::string>();
            if (!ids.insert(id).second) fail("duplicate motion id \"" + id + "\"");
            if (!motion.contains("unit") || !motion["unit"].is_string() ||
                motion["unit"].get<std::string>().empty()) {
                fail(where + " (\"" + id + "\") needs a non-empty `unit`");
            }
            if (motion.contains("tracks")) {
                requireArray(motion["tracks"], where + ".tracks");
                for (std::size_t j = 0; j < motion["tracks"].size(); ++j) {
                    const std::string trackWhere = where + ".tracks[" + std::to_string(j) + "]";
                    validateTrack(motion["tracks"][j], trackWhere);
                    validateRestingEntrance(motion["tracks"][j], trackWhere);
                }
            }
            if (motion.contains("text_animators")) {
                requireArray(motion["text_animators"], where + ".text_animators");
                for (std::size_t j = 0; j < motion["text_animators"].size(); ++j) {
                    const std::string animatorWhere =
                        where + ".text_animators[" + std::to_string(j) + "]";
                    const json& animator = motion["text_animators"][j];
                    requireObject(animator, animatorWhere);
                    if (!animator.contains("selector")) {
                        fail(animatorWhere + " needs a `selector`");
                    }
                    if (!animator.contains("properties")) {
                        fail(animatorWhere + " needs `properties`");
                    }
                    requireArray(animator["properties"], animatorWhere + ".properties");
                    for (std::size_t k = 0; k < animator["properties"].size(); ++k) {
                        validateTrack(animator["properties"][k],
                                      animatorWhere + ".properties[" + std::to_string(k) + "]");
                    }
                }
            }
        }
        return ids;
    }

    /// Validates one preset-id list and returns it as a set.
    std::set<std::string> validatePresetIDs(const json& ids, const std::string& where) {
        requireArray(ids, where);
        if (ids.empty()) fail(where + " must not be empty");
        std::set<std::string> out;
        for (std::size_t i = 0; i < ids.size(); ++i) {
            if (!ids[i].is_string() || ids[i].get<std::string>().empty()) {
                fail(where + "[" + std::to_string(i) + "] must be a non-empty string");
            }
            const std::string id = ids[i].get<std::string>();
            if (!out.insert(id).second) fail(where + " repeats \"" + id + "\"");
        }
        return out;
    }

    /// Every id a selection names must still exist in the catalog it selects
    /// from: renaming or deleting a motion without updating its corpus is the
    /// one drift a reader cannot see by looking at either file alone.
    void validateSelections(const json& selections,
                            const std::set<std::string>& motionIDs,
                            const std::set<std::string>& imagePresetIDs) {
        requireObject(selections, "selections");
        for (const char* key : {"tyson_phrase_motions", "matrix_image_overlays", "matrix_phrase_overlays"}) {
            if (!selections.contains(key)) fail(std::string("selections needs \"") + key + "\"");
        }

        const json& phraseMotions = selections["tyson_phrase_motions"];
        requireArray(phraseMotions, "selections.tyson_phrase_motions");
        if (phraseMotions.empty()) fail("selections.tyson_phrase_motions must not be empty");
        for (std::size_t i = 0; i < phraseMotions.size(); ++i) {
            if (!phraseMotions[i].is_string()) {
                fail("selections.tyson_phrase_motions[" + std::to_string(i) + "] must be a string");
            }
            const std::string id = phraseMotions[i].get<std::string>();
            if (motionIDs.find(id) == motionIDs.end()) {
                fail("selections.tyson_phrase_motions names unknown motion \"" + id + "\"");
            }
        }

        const json& imageOverlays = selections["matrix_image_overlays"];
        requireArray(imageOverlays, "selections.matrix_image_overlays");
        if (imageOverlays.empty()) fail("selections.matrix_image_overlays must not be empty");
        for (std::size_t i = 0; i < imageOverlays.size(); ++i) {
            if (!imageOverlays[i].is_string()) {
                fail("selections.matrix_image_overlays[" + std::to_string(i) + "] must be a string");
            }
            const std::string id = imageOverlays[i].get<std::string>();
            if (imagePresetIDs.find(id) == imagePresetIDs.end()) {
                fail("selections.matrix_image_overlays names unknown image preset \"" + id + "\"");
            }
        }

        const json& phraseOverlays = selections["matrix_phrase_overlays"];
        requireArray(phraseOverlays, "selections.matrix_phrase_overlays");
        if (phraseOverlays.empty()) fail("selections.matrix_phrase_overlays must not be empty");
        std::set<std::string> overlayIDs;
        for (std::size_t i = 0; i < phraseOverlays.size(); ++i) {
            const json& row = phraseOverlays[i];
            const std::string where = "selections.matrix_phrase_overlays[" + std::to_string(i) + "]";
            requireObject(row, where);
            if (!row.contains("id") || !row["id"].is_string() || row["id"].get<std::string>().empty()) {
                fail(where + " needs a non-empty `id`");
            }
            if (!overlayIDs.insert(row["id"].get<std::string>()).second) {
                fail(where + " repeats overlay \"" + row["id"].get<std::string>() + "\"");
            }
            if (!row.contains("motion") || !row["motion"].is_string()) {
                fail(where + " needs a `motion`");
            }
            const std::string motion = row["motion"].get<std::string>();
            if (motionIDs.find(motion) == motionIDs.end()) {
                fail(where + " names unknown motion \"" + motion + "\"");
            }
        }
    }

    /// The template list is C++-owned: it is read from the same enum the packs
    /// are built from, so the emitted catalog cannot list a template the module
    /// cannot build.
    json templateCatalog() {
        json out = json::array();
        for (const auto id : chrononmotion::templates::available()) {
            out.push_back(json{{"id", chrononmotion::templates::name(id)},
                               {"name", chrononmotion::templates::name(id)}});
        }
        return out;
    }

    /// The stable wire name of a material kind. Spelled out rather than derived
    /// from the enumerator so that reordering the enum cannot renumber the
    /// artifact a consumer matches on.
    std::string materialKindName(chrononmotion::MaterialKind kind) {
        switch (kind) {
            case chrononmotion::MaterialKind::Unlit: return "unlit";
            case chrononmotion::MaterialKind::Lambert: return "lambert";
            case chrononmotion::MaterialKind::Emissive: return "emissive";
        }
        fail("composition declares an unknown material kind");
    }

    /// The preset list is C++-owned for the same reason as the template list.
    ///
    /// Material facts are emitted for consumers that need to know whether a
    /// composition is emissive; glow rendering itself is handled by Chronon3D's
    /// single simple effect and is not a per-preset quality policy.
    json final3DPresets() {
        json out = json::array();
        for (const auto preset : chronontemplate::final3DPresets()) {
            const chronontemplate::Composition composition = chronontemplate::build(preset);
            out.push_back(json{
                    {"id", chronontemplate::name(preset)},
                    {"name", chronontemplate::name(preset)},
                    {"material", {{"kind", materialKindName(composition.material.kind)},
                                  {"emissive_strength", composition.material.emissiveStrength}}}});
        }
        return out;
    }

    /// The native phrase projection is C++-owned just like the final 3D
    /// presets.  Publishing it here lets the plan emitter consume the exact
    /// font, canvas geometry and white-glow policy without re-authoring them.
    json nativePhraseStyle() {
        const auto style = chronontemplate::nativePhraseStyle();
        json out = json::object();
        out["font"] = style.font;
        out["font_size"] = style.font_size;
        out["box"] = json::array({style.box[0], style.box[1]});
        out["position"] = json::array({style.position[0], style.position[1]});
        out["background"] = json::array({style.background[0], style.background[1],
                                          style.background[2], style.background[3]});
        out["fill"] = style.fill;
        out["stroke"] = json::object({{"color", style.stroke}, {"width", style.stroke_width}});
        out["glow"] = json::object({{"radius", style.glow_radius},
                                     {"intensity", style.glow_intensity},
                                     {"color", style.glow}});
        return out;
    }

    /// The pack/preset rule, enforced at the publish boundary. A pack is a
    /// recipe and a preset is a parameter set over one, so the two published
    /// namespaces must stay disjoint and each must be unique on its own: an id
    /// in both lists is the same overlay described twice, with two timings that
    /// are free to drift. This is the only writer of the artifact, so the gate
    /// belongs here rather than in a consumer's good intentions.
    void validateIDSeparation(const json& packs, const json& presets) {
        std::map<std::string, std::string> owner;
        for (const json& row : packs) {
            const std::string id = row["id"].get<std::string>();
            if (!owner.emplace(id, "pack").second) {
                fail("pack \"" + id + "\" is listed twice");
            }
        }
        for (const json& row : presets) {
            const std::string id = row["id"].get<std::string>();
            const auto inserted = owner.emplace(id, "preset");
            if (!inserted.second) {
                fail("id \"" + id + "\" is published as both a " + inserted.first->second +
                     " and a preset; a pack is the recipe and a preset is a parameter set over one, "
                     "so the same overlay cannot be described twice");
            }
        }
    }

    std::string readFile(const std::string& path) {
        std::ifstream in(path, std::ios::binary);
        if (!in) fail("cannot read catalog data file \"" + path + "\"");
        std::ostringstream buffer;
        buffer << in.rdbuf();
        return buffer.str();
    }

    void writeFile(const std::string& path, const std::string& contents) {
        std::ofstream out(path, std::ios::binary | std::ios::trunc);
        if (!out) fail("cannot write emitted catalog \"" + path + "\"");
        out << contents;
    }

}// namespace

int main(int argc, char** argv) {
    std::string catalogPath = CHRONONTEMPLATE_CATALOG_FILE;
    std::string outPath;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--catalog" && i + 1 < argc) {
            catalogPath = argv[++i];
        } else if (arg == "--out" && i + 1 < argc) {
            outPath = argv[++i];
        } else if (arg == "-h" || arg == "--help") {
            std::cout << "usage: chronontemplate_emit_catalog [--catalog <in.json>] [--out <out.json>]\n";
            return 0;
        } else {
            std::cerr << "emit_catalog: unknown argument \"" << arg << "\"\n";
            return 2;
        }
    }

    try {
        const json data = json::parse(readFile(catalogPath));
        requireObject(data, "catalog");
        if (!data.contains("schema_version") || data["schema_version"] != kSchemaVersion) {
            fail("unsupported schema_version (expected " + std::to_string(kSchemaVersion) + ")");
        }
        if (!data.contains("source") || data["source"] != kSource) {
            fail(std::string("source must be \"") + kSource + "\"");
        }
        if (!data.contains("motions")) fail("catalog needs `motions`");
        if (!data.contains("overlay_presets")) fail("catalog needs `overlay_presets`");
        if (!data.contains("selections")) fail("catalog needs `selections`");

        const std::set<std::string> motionIDs = validateMotions(data["motions"]);

        const json& presets = data["overlay_presets"];
        requireObject(presets, "overlay_presets");
        if (!presets.contains("text")) fail("overlay_presets needs `text`");
        if (!presets.contains("image")) fail("overlay_presets needs `image`");
        const std::set<std::string> textPresetIDs = validatePresetIDs(presets["text"], "overlay_presets.text");
        const std::set<std::string> imagePresetIDs = validatePresetIDs(presets["image"], "overlay_presets.image");

        validateSelections(data["selections"], motionIDs, imagePresetIDs);

        const json packRows = templateCatalog();
        const json presetRows = final3DPresets();
        validateIDSeparation(packRows, presetRows);

        json emitted = json::object();
        emitted["schema_version"] = kSchemaVersion;
        emitted["source"] = kSource;
        emitted["templates"] = packRows;
        emitted["final3d_presets"] = presetRows;
        emitted["native_phrase_style"] = nativePhraseStyle();
        emitted["motions"] = data["motions"];
        emitted["overlay_presets"] = data["overlay_presets"];
        emitted["selections"] = data["selections"];

        std::string rendered = emitted.dump(2);
        rendered.push_back('\n');
        if (outPath.empty()) {
            std::cout << rendered;
        } else {
            writeFile(outPath, rendered);
            std::cerr << "emit_catalog: " << motionIDs.size() << " motions, "
                      << textPresetIDs.size() << " text presets, "
                      << imagePresetIDs.size() << " image presets -> " << outPath << "\n";
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 1;
    }
}
