// Camera-side documentary effects: loupe travel math, depth-parallax
// planes + camera push, and the before/after split sampler.
#include "chronontemplate/documentary_effects/MagnifierLoupePack.hpp"
#include "chronontemplate/documentary_effects/DepthParallaxPack.hpp"
#include "chronontemplate/documentary_effects/BeforeAfterPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <cmath>
#include <stdexcept>

using namespace chronontemplate;
using namespace chronontemplate::docfx;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    constexpr const char* kAsset = "assets/test/square_bottle_test.png";

    void loupeTravelsAndPushes() {
        section("magnifier loupe");
        LoupeSpec spec;
        spec.photoAsset = kAsset;
        spec.startFrame = 10;
        spec.durationFrames = 80;
        const auto a = loupeCenter(spec, 0);
        const auto b = loupeCenter(spec, 50);
        const auto c = loupeCenter(spec, 90);
        checkNear(a.x, 700.f, 1e-4f, "loupe starts at fromX");
        checkNear(c.x, 1220.f, 1e-4f, "loupe ends at toX");
        check(a.x < b.x && b.x < c.x, "loupe travels monotonically");
        checkNear(loupePush(spec, 10), 1.0f, 1e-6f, "push starts at 1.0");
        checkNear(loupePush(spec, 90), 1.04f, 1e-6f, "push ends at 1.04");
        FakeContentHost host;
        TemplateScene scene("loupe", 30.f, host, 1920.f, 1080.f);
        const auto layers = addMagnifierLoupe(scene, spec);
        check(layers.card != 0 && layers.ring != 0, "card and ring are authored");
        check(host.findShapeRequest("loupe_ring") != nullptr, "the ring shape exists");
        check(host.findShapeRequest("loupe_halo") != nullptr, "the halo shape exists");
        const FrameSubmission mid = scene.submit(50);
        const BoundLayer* ring = findLayer(mid, layers.ring);
        check(ring && ring->transform.visible, "the ring is visible mid-travel");
        if (ring) {
            const auto expect = loupeCenter(spec, 50);
            // World matrix carries the eased travel: x must sit between ends.
            check(ring->transform.world[12] > 700.f && ring->transform.world[12] < 1220.f,
                  "the ring world x follows the travel path");
            (void) expect;
        }
        check(scene.validate().empty(), "the loupe scene validates");
        int throws = 0;
        {
            FakeContentHost h2;
            TemplateScene s2("v", 30.f, h2, 1920.f, 1080.f);
            LoupeSpec bad = spec;
            bad.ringRadius = 5.f;
            try { (void) addMagnifierLoupe(s2, bad); } catch (const std::invalid_argument&) { ++throws; }
        }
        {
            FakeContentHost h2;
            TemplateScene s2("v", 30.f, h2, 1920.f, 1080.f);
            LoupeSpec bad = spec;
            bad.ringColor = "white";
            try { (void) addMagnifierLoupe(s2, bad); } catch (const std::invalid_argument&) { ++throws; }
        }
        check(throws == 2, "tiny ring and bad hex both throw");
        check(std::string(magnifierLoupeId()) == "docfx_magnifier_loupe_v1", "loupe id is stable");
    }

    void parallaxSeparatesPlanes() {
        section("depth parallax");
        DepthParallaxSpec spec;
        spec.photoAsset = kAsset;
        checkNear(parallaxProgress(spec, 0), 0.f, 1e-6f, "progress starts at 0");
        checkNear(parallaxProgress(spec, 75), 0.5f, 1e-6f, "progress is 0.5 halfway");
        checkNear(parallaxProgress(spec, 150), 1.f, 1e-6f, "progress ends at 1");
        FakeContentHost host;
        TemplateScene scene("parallax", 30.f, host, 1920.f, 1080.f);
        const auto layers = addDepthParallax(scene, spec);
        check(layers.background != 0 && layers.foreground != 0, "both planes are authored");
        check(host.lastImageRequest().crop.enabled, "the foreground carries its subject crop");
        const FrameSubmission mid = scene.submit(75);
        const BoundLayer* bg = findLayer(mid, layers.background);
        const BoundLayer* fg = findLayer(mid, layers.foreground);
        check(bg && fg && bg->transform.visible && fg->transform.visible,
              "both planes draw mid-scene");
        if (bg && fg)
            check(std::abs(fg->transform.world[12] - bg->transform.world[12]) > 1.f,
                  "foreground separates laterally from the background");
        check(scene.validate().empty(), "the parallax scene validates");
        bool threw = false;
        {
            FakeContentHost h2;
            TemplateScene s2("v", 30.f, h2, 1920.f, 1080.f);
            DepthParallaxSpec bad = spec;
            bad.fgOriginX = 0.8f; // 0.8 + 0.4 overflows the photo
            try { (void) addDepthParallax(s2, bad); } catch (const std::invalid_argument&) { threw = true; }
        }
        check(threw, "an overflowing subject crop throws");
        check(std::string(depthParallaxId()) == "docfx_depth_parallax_v1", "parallax id is stable");
    }

    void beforeAfterSweepsOutAndBack() {
        section("before/after wipe");
        BeforeAfterSpec spec;
        spec.beforeAsset = kAsset;
        spec.afterAsset = kAsset;
        checkNear(afterSplit(spec, 0), 0.f, 1e-6f, "split starts at 0");
        checkNear(afterSplit(spec, 35), 0.5f, 1e-6f, "split is 0.5 mid-sweep");
        checkNear(afterSplit(spec, 70), 1.f, 1e-6f, "split holds at 1");
        checkNear(afterSplit(spec, 105), 0.5f, 1e-6f, "split returns mid-way-back");
        checkNear(afterSplit(spec, 140), 0.f, 1e-6f, "split rests at 0");
        FakeContentHost host;
        TemplateScene scene("comparison", 30.f, host, 1920.f, 1080.f);
        const auto layers = addBeforeAfter(scene, spec);
        check(layers.before != 0 && layers.after != 0 && layers.divider != 0,
              "both cards and the divider are authored");
        const FrameSubmission mid = scene.submit(80);
        const BoundLayer* div = findLayer(mid, layers.divider);
        check(div && div->transform.visible, "the divider draws at full-after hold");
        check(scene.validate().empty(), "the comparison scene validates");
        bool threw = false;
        {
            FakeContentHost h2;
            TemplateScene s2("v", 30.f, h2, 1920.f, 1080.f);
            BeforeAfterSpec bad = spec;
            bad.afterAsset.clear();
            try { (void) addBeforeAfter(s2, bad); } catch (const std::invalid_argument&) { threw = true; }
        }
        check(threw, "a missing after asset throws");
        check(std::string(beforeAfterId()) == "docfx_before_after_v1", "comparison id is stable");
    }

} // namespace

int main() {
    loupeTravelsAndPushes();
    parallaxSeparatesPlanes();
    beforeAfterSweepsOutAndBack();
    return chrononmotion_test::report();
}
