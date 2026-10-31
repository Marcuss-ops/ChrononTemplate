// The native web-shot contract: 28 rebuild plans plus six reusable recipes,
// all pure RenderPlan V3 documents in the current web contract.
//
// This test pins the parts that used to drift: full-bleed paper is a
// screen-space color layer, text boxes are measured and carry no fit_mode /
// text_align overrides, the camera is the shared static page camera (no
// obsolete centre-origin samples or baked crop tracks), and every plan is a
// deterministic function of its spec.
#include "chronontemplate/web/WebShotsRebuildPack.hpp"
#include "chronontemplate/web/WebShotsNextPack.hpp"

#include "motion_check.hpp"

#include <nlohmann/json.hpp>

#include <cmath>
#include <set>
#include <string>
#include <vector>

using json = nlohmann::json;
using namespace chronontemplate::web;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    // 1:1 wire->px mapping: 540/tan(25deg) = 1158.06 (calibration renders
    // confirm rects land on authored pixels; -1320 scaled 0.877 to center).

    void checksPlanEnvelope(const json& plan, const std::string& jobId, int duration) {
        check(plan.at("schema") == "chronon.render-plan.v3" && plan.at("version") == 3,
              "the plan is render-plan V3");
        check(plan.at("job_id") == jobId, "the job id follows the recipe identity");
        const auto& canvas = plan.at("canvas");
        check(canvas.at("width") == 1920 && canvas.at("height") == 1080,
              "the canvas is 1920x1080");
        check(canvas.at("fps_num") == 30 && canvas.at("fps_den") == 1,
              "the canvas is 30 fps");
        check(canvas.at("duration_frames") == duration,
              "the canvas carries the authored duration");
        check(plan.at("output").at("format") == "mp4" &&
                  plan.at("output").at("codec") == "h264",
              "the output is H.264 mp4");
        check(plan.contains("camera"), "the plan declares a camera");
        check(!plan.contains("camera_samples"),
              "the plan does not carry obsolete camera samples");
        const auto& camera = plan.at("camera");
        check(camera.at("type") == "perspective", "the camera is perspective");
        chrononmotion_test::checkNear(camera.at("position")[2].get<float>(),
                                     -1158.06f, 0.01f,
                                     "the camera gives 1:1 wire to pixel mapping");
    }

    void checksLayerContract(const json& plan) {
        std::set<std::string> ids;
        bool hasText = false;
        for (const auto& layer : plan.at("layers")) {
            check(ids.insert(layer.at("id").get<std::string>()).second,
                  "layer ids are unique inside the plan");
            const std::string type = layer.at("type").get<std::string>();
            if (type == "color") {
                check(layer.value("screen_space", false),
                      "a full-bleed color plate is screen-space");
                check(layer.at("size")[0] == 1920 && layer.at("size")[1] == 1080,
                      "the screen-space plate covers the canvas");
            }
            if (type == "text") {
                hasText = true;
                check(layer.contains("style"), "a text layer carries a style block");
                const auto& style = layer.at("style");
                check(!style.contains("fit_mode") && !style.contains("text_align"),
                      "text uses the renderer's measured-box contract, not fit/align overrides");
                check(layer.at("size")[0].get<float>() >= 60.f,
                      "the text box is measured from the copy");
                check(std::isfinite(layer.at("position")[0].get<float>()) &&
                          std::isfinite(layer.at("position")[1].get<float>()),
                      "the text position is finite");
            }
        }
        check(hasText, "every web shot authors at least one text layer");
    }

    void checksRebuild() {
        section("web shots rebuild 28");
        const std::vector<WebShotId> ids = allWebShotIds();
        check(ids.size() == 28, "all 28 reference shots are registered");

        std::set<std::string> names;
        for (const WebShotId id : ids) {
            WebShotSpec spec;
            spec.id = id;
            spec.durationFrames = 90;
            spec.fps = 30;
            const json plan = buildWebShotPlan(spec);
            checksPlanEnvelope(plan, spec.planName(), 90);
            checksLayerContract(plan);
            check(names.insert(webShotName(id)).second,
                  "every shot has a unique stable name");
            check(plan.at("output").at("path") == spec.outputStem(),
                  "the output stem follows the stable shot name");
            check(buildWebShotPlan(spec).dump() == plan.dump(),
                  "the emitted plan is deterministic");
        }
    }

    void checksNext() {
        section("web shots next recipes");
        const std::vector<WebNextRecipe> recipes = allWebNextRecipes();
        check(recipes.size() == 6, "all six reusable recipes are registered");

        std::set<std::string> names;
        for (const WebNextRecipe recipe : recipes) {
            WebNextSpec spec;
            spec.recipe = recipe;
            spec.headline = "Senate passes the chip export bill";
            spec.highlight = "chip export bill";
            spec.subline = "Breaking — 10:42 ET";
            spec.body = "Markets rally as export rules take hold.";
            const json plan = buildWebNextPlan(spec);
            checksPlanEnvelope(plan, spec.planName(), 90);
            checksLayerContract(plan);
            check(names.insert(webNextName(recipe)).second,
                  "every recipe has a unique stable name");
            check(buildWebNextPlan(spec).dump() == plan.dump(),
                  "the emitted recipe is deterministic");
        }
    }

    void failsClosed() {
        section("web shots fail-closed");
        const auto throws = [](auto&& build, const char* what) {
            try {
                (void) build();
            } catch (const std::invalid_argument&) {
                check(true, what);
                return;
            }
            check(false, what);
        };

        throws([] {
            WebShotSpec spec;
            spec.durationFrames = 10;
            return buildWebShotPlan(spec);
        }, "a sub-second rebuild fails closed");

        throws([] {
            WebShotSpec spec;
            spec.fps = 24;
            return buildWebShotPlan(spec);
        }, "a non-30 fps rebuild fails closed");

        throws([] {
            WebNextSpec spec;
            spec.highlight = "not in the headline";
            return buildWebNextPlan(spec);
        }, "a recipe whose highlight is absent fails closed");
    }

}// namespace

int main() {
    checksRebuild();
    checksNext();
    failsClosed();
    return chrononmotion_test::report();
}
