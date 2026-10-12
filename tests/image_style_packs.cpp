#include "chronontemplate/single_images/PixelGridPack.hpp"
#include "chronontemplate/single_images/EdgeStrokePack.hpp"
#include "chronontemplate/single_images/GlowPack.hpp"
#include "chronontemplate/single_images/RGBSplitPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <array>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    constexpr const char* kAsset = "assets/test/square_bottle_test.png";

    template <typename AddFn>
    void submitsAndExits(const std::string& sceneName, AddFn add) {
        FakeContentHost host;
        TemplateScene scene(sceneName, 30.f, host, 1920.f, 1080.f);
        LayerHandle& image = add(scene, host);
        image.position(960.f, 540.f);
        const FrameSubmission start = scene.submit(0);
        const FrameSubmission settled = scene.submit(48);
        const FrameSubmission exit = scene.submit(149);
        const BoundLayer* a = findLayer(start, image.id());
        const BoundLayer* c = findLayer(settled, image.id());
        const BoundLayer* d = findLayer(exit, image.id());
        check(a && c && d, "each style recipe submits its image");
        check(a && a->draws() && a->content.isImage(), "the bound content remains an image");
        if (c && d) {
            check(c->transform.opacity > 0.f, "the styled image is visible after its entrance");
            check(d->transform.opacity < c->transform.opacity,
                  "the styled image fades out before the end of the timeline");
        }
        check(scene.validate().empty(), "each styled scene validates");
    }

    void theFivePixelGridRecipesSubmit() {
        section("five pixel-grid recipes");
        constexpr std::array<ImagePixelGrid, 5> animations{
                ImagePixelGrid::GridReveal, ImagePixelGrid::PixelStepIn,
                ImagePixelGrid::GridZoomOut, ImagePixelGrid::GridSlideTiles,
                ImagePixelGrid::GridBreathe};
        constexpr std::array<const char*, 5> tags{
                "reveal", "step", "zoomout", "tiles", "breathe"};
        for (std::size_t i = 0; i < animations.size(); ++i) {
            FakeContentHost host;
            TemplateScene scene(std::string("image_grid_") + tags[i], 30.f, host,
                                1920.f, 1080.f);
            LayerHandle& image = addImagePixelGrid(scene, animations[i], kAsset,
                                                    "grid", ImageFrameStyle{.cornerRadius = 64.f});
            image.position(960.f, 540.f);
            for (const char* bar : {"h0", "h1", "v0", "v1"}) {
                const auto* shape = host.findShapeRequest(std::string("grid_grid_") + bar);
                check(shape != nullptr, "each grid recipe emits its lattice bars");
                if (shape) {
                    check(shape->fillColor == "#8A8F98",
                          "the lattice stays neutral grey over the dimmed plate");
                }
            }
            const FrameSubmission settled = scene.submit(48);
            const FrameSubmission exit = scene.submit(149);
            const BoundLayer* c = findLayer(settled, image.id());
            const BoundLayer* d = findLayer(exit, image.id());
            check(c && d, "each grid recipe submits its image");
            if (c && d) {
                check(c->transform.opacity > 0.f, "the grid image is visible after its entrance");
                check(d->transform.opacity < c->transform.opacity,
                      "the grid image fades out before the end of the timeline");
            }
            check(scene.validate().empty(), "each grid scene validates");
        }
    }

    void theFiveOrangeEdgeStrokesSubmit() {
        section("five orange edge strokes");
        constexpr std::array<ImageEdgeStroke, 5> animations{
                ImageEdgeStroke::StrokeLeft, ImageEdgeStroke::StrokeRight,
                ImageEdgeStroke::StrokeDuo, ImageEdgeStroke::StrokeTopBottom,
                ImageEdgeStroke::StrokeSweep};
        constexpr std::array<const char*, 5> tags{
                "left", "right", "duo", "topbottom", "sweep"};
        for (std::size_t i = 0; i < animations.size(); ++i) {
            submitsAndExits(std::string("image_stroke_") + tags[i],
                [&](TemplateScene& scene, FakeContentHost& host) -> LayerHandle& {
                    LayerHandle& image = addImageEdgeStroke(scene, animations[i], kAsset,
                                                             "stroke", ImageFrameStyle{.cornerRadius = 64.f});
                    if (i == 2) {
                        check(host.findShapeRequest("stroke_stroke_duo_left") != nullptr &&
                                      host.findShapeRequest("stroke_stroke_duo_right") != nullptr,
                              "the duo recipe paints both orange sides");
                    } else if (i == 3) {
                        const auto* top = host.findShapeRequest("stroke_stroke_top");
                        const auto* bottom = host.findShapeRequest("stroke_stroke_bottom");
                        check(top && bottom, "the top/bottom recipe paints both orange sides");
                        if (top && bottom) {
                            check(top->size.x > top->size.y && bottom->size.x > bottom->size.y,
                                  "horizontal sides use wide orange bars");
                        }
                    } else {
                        const char* barName = i == 0 ? "stroke_stroke_left"
                                : i == 1             ? "stroke_stroke_right"
                                                     : "stroke_stroke_sweep";
                        const auto* bar = host.findShapeRequest(barName);
                        check(bar != nullptr, "each single-side recipe emits its orange bar");
                        if (bar) {
                            check(bar->fillColor == "#FF7A1A",
                                  "the side stroke keeps the signature orange");
                            check(bar->size.x < bar->size.y,
                                  "vertical sides use a tall orange bar");
                        }
                    }
                    return image;
                });
        }
    }

    void theFiveGlowPlatesSubmit() {
        section("five glow plates");
        constexpr std::array<ImageGlow, 5> animations{
                ImageGlow::WarmGlow, ImageGlow::CoolGlow, ImageGlow::GoldGlow,
                ImageGlow::RoseGlow, ImageGlow::PulseGlow};
        constexpr std::array<const char*, 5> colors{
                "#FF8A3D", "#38BDF8", "#E8B84A", "#F472B6", "#A78BFA"};
        for (std::size_t i = 0; i < animations.size(); ++i) {
            submitsAndExits(std::string("image_glow_") + std::to_string(i),
                [&](TemplateScene& scene, FakeContentHost& host) -> LayerHandle& {
                    LayerHandle& image = addImageGlow(scene, animations[i], kAsset,
                                                       "glow", ImageFrameStyle{.cornerRadius = 64.f});
                    const auto* plate = host.findShapeRequest("glow_glow");
                    check(plate != nullptr, "each glow recipe emits its halo plate");
                    if (plate) {
                        check(plate->fillColor == colors[i],
                              "each glow recipe keeps its signature halo color");
                    }
                    return image;
                });
        }
    }

    void theFiveRGBSplitsSubmit() {
        section("five RGB splits");
        constexpr std::array<ImageRGBSplit, 5> animations{
                ImageRGBSplit::SplitStatic, ImageRGBSplit::SplitConverge,
                ImageRGBSplit::SplitPulse, ImageRGBSplit::SplitGlitch,
                ImageRGBSplit::SplitExit};
        for (std::size_t i = 0; i < animations.size(); ++i) {
            submitsAndExits(std::string("image_rgb_") + std::to_string(i),
                [&](TemplateScene& scene, FakeContentHost& host) -> LayerHandle& {
                    LayerHandle& image = addImageRGBSplit(scene, animations[i], kAsset,
                                                           "rgb", ImageFrameStyle{.cornerRadius = 64.f});
                    const auto* red = host.findShapeRequest("rgb_rgb_red");
                    const auto* cyan = host.findShapeRequest("rgb_rgb_cyan");
                    check(red && cyan, "each split recipe emits both channel ghosts");
                    if (red && cyan) {
                        check(red->fillColor == "#FF3B30", "the left ghost stays channel red");
                        check(cyan->fillColor == "#22D3EE", "the right ghost stays channel cyan");
                    }
                    return image;
                });
        }
    }

}// namespace

int main() {
    theFivePixelGridRecipesSubmit();
    theFiveOrangeEdgeStrokesSubmit();
    theFiveGlowPlatesSubmit();
    theFiveRGBSplitsSubmit();
    return chrononmotion_test::report();
}
