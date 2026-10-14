#include "chronontemplate/vintage_documentary/VintageDocumentaryTitle01Pack.hpp"

#include "chronontemplate/core/PlanLowering.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>

using namespace chronontemplate;
using namespace chronontemplate::vintage_documentary;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    VintageDocumentaryTitle01Scene canonicalScene() {
        VintageDocumentaryTitle01Scene spec;
        spec.name = "title01_test";
        spec.small.text = "The";
        spec.small.font = "catalog/Anton.ttf";
        spec.small.fontSize = 92.f;
        spec.small.posX = 300.f;
        spec.small.posY = 380.f;
        spec.small.enterFrame = 6;
        spec.main.text = "DOCUMENTARY";
        spec.main.font = "catalog/Anton.ttf";
        spec.main.fontSize = 280.f;
        spec.main.posX = 960.f;
        spec.main.posY = 545.f;
        spec.main.enterFrame = 6;
        spec.script.text = "editing-style";
        spec.script.font = "fonts/PlayfairDisplay-Italic.ttf";
        spec.script.fontSize = 104.f;
        spec.script.posX = 1330.f;
        spec.script.posY = 740.f;
        spec.script.enterFrame = 36;
        spec.exitStartFrame = 132;
        return spec;
    }

    void deterministicTwinsMatchTheRenderPlanGenerator() {
        section("title01 deterministic twins");
        // Golden samples computed from the reference Python lowering.
        checkNear(weaveOffsetX(0), 0.594999f, 1e-4f, "weave X at frame 0");
        checkNear(weaveOffsetY(0), 0.627803f, 1e-4f, "weave Y at frame 0");
        checkNear(weaveOffsetX(37), 0.401620f, 1e-4f, "weave X at frame 37");
        checkNear(weaveOffsetY(37), 0.205565f, 1e-4f, "weave Y at frame 37");
        checkNear(weaveOffsetX(149), -0.427209f, 1e-4f, "weave X at frame 149");
        // LCG stream: hold 0 -> 0.943745816, hold 1 -> 0.500527604.
        TitleFlicker flicker{};
        checkNear(flickerLift(flicker, 0, 0), 0.006f + 0.943745816f * 0.018f, 1e-6f,
                  "flicker hold 0 matches the generator");
        checkNear(flickerLift(flicker, 1, 3), 0.006f + 0.500527604f * 0.018f, 1e-6f,
                  "flicker hold 1 matches the generator");
        checkNear(flickerLift(flicker, 44, 132), 0.07f, 1e-6f,
                  "exit flash peak rides the flash window");
        checkNear(titleHash01(0, 1234), titleHash01(0, 1234), 0.f,
                  "dust hash is a pure function of its inputs");
        check(titleHash01(1, 1234) != titleHash01(2, 1234),
              "dust hash varies across dots");
    }

    void theSceneAuthorsEveryLayerWithItsRequests() {
        section("title01 scene");
        FakeContentHost host;
        TemplateScene scene("title01_test", 30.f, host, 1920.f, 1080.f);
        const auto layers = addVintageDocumentaryTitle01Scene(scene, canonicalScene());
        check(layers.background != 0 && layers.smallLine != 0 &&
              layers.mainTitle != 0 && layers.scriptLine != 0 &&
              layers.dust != 0 && layers.flickerVeil != 0,
              "background, three lines, dust and flicker handles are all live");

        const auto* ground = host.findShapeRequest("title01_test_bg_ground");
        check(ground != nullptr && ground->fillColor == "#090909",
              "the near-black ground is authored");
        check(ground != nullptr && ground->animatedNoise &&
              ground->noiseSeed == 42,
              "the ground carries the animated grain contract (seed 42)");
        check(host.findShapeRequest("title01_test_bg_vignette") != nullptr,
              "the vignette plate is authored");
        check(host.findShapeRequest("title01_test_dust_0") != nullptr,
              "deterministic film dust is authored");
        check(host.findShapeRequest("title01_test_flicker") != nullptr,
              "the exposure-flicker veil is authored");

        // Timing: titles fade in on their entrance frames and out
        // together at the exit window (opacity tracks, exact samples).
        const FrameSubmission before = scene.submit(0);
        const FrameSubmission titles = scene.submit(60);
        const FrameSubmission late = scene.submit(149);
        const BoundLayer* mainEarly = findLayer(before, layers.mainTitle);
        const BoundLayer* mainMid = findLayer(titles, layers.mainTitle);
        const BoundLayer* scriptEarly = findLayer(before, layers.scriptLine);
        const BoundLayer* scriptMid = findLayer(titles, layers.scriptLine);
        const BoundLayer* mainLate = findLayer(late, layers.mainTitle);
        check(mainEarly && mainEarly->transform.opacity == 0.f,
              "the main title is silent at frame 0");
        check(mainMid && mainMid->transform.opacity == 1.f,
              "the main title is fully in mid-card");
        check(scriptEarly && scriptEarly->transform.opacity == 0.f,
              "the script subtitle waits for its entrance");
        check(scriptMid && scriptMid->transform.opacity == 1.f,
              "the script subtitle draws mid-card");
        check(mainLate && mainLate->transform.opacity < 0.05f,
              "the main title is almost gone at the tail");
        check(scene.validate().empty(), "the title01 scene validates");
    }

    void invalidSpecsThrow() {
        section("title01 validation");
        FakeContentHost host;
        bool threw = false;
        try {
            auto bad = canonicalScene();
            bad.main.fontSize = 0.f;
            TemplateScene scene("title01_bad", 30.f, host, 1920.f, 1080.f);
            (void)addVintageDocumentaryTitle01Scene(scene, bad);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a zero main font size throws");
        threw = false;
        try {
            auto bad = canonicalScene();
            bad.grain.amount = 2.f;
            TemplateScene scene("title01_bad", 30.f, host, 1920.f, 1080.f);
            (void)addVintageDocumentaryTitle01Scene(scene, bad);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "grain outside [0,1] throws");
        threw = false;
        try {
            auto bad = canonicalScene();
            bad.small.text.clear();
            TemplateScene scene("title01_bad", 30.f, host, 1920.f, 1080.f);
            (void)addVintageDocumentaryTitle01Scene(scene, bad);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "an empty small line throws");
    }

} // namespace

int main() {
    deterministicTwinsMatchTheRenderPlanGenerator();
    theSceneAuthorsEveryLayerWithItsRequests();
    invalidSpecsThrow();
    return chrononmotion_test::report();
}
