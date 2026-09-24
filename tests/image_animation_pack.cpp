#include "chronontemplate/ImageAnimationPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <array>
#include <cmath>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chronontemplate_test::sameMatrix;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void theTwelveClean25dAnimationsSubmitWithTheirAuthoredCameraBehavior() {
        section("twelve clean 2.5D image animations");
        constexpr const char* asset = "assets/test/square_bottle_test.png";
        constexpr std::array<ImageAnimation, 12> animations{
                ImageAnimation::DepthFloatIn, ImageAnimation::YawFlipIn,
                ImageAnimation::PitchLift, ImageAnimation::PopZBounce,
                ImageAnimation::Swipe3D, ImageAnimation::CardSwing,
                ImageAnimation::DollySettle, ImageAnimation::OrbitArc,
                ImageAnimation::CounterTilt, ImageAnimation::DollyBreath,
                ImageAnimation::ParallaxDrift, ImageAnimation::HeroPullExit};
        constexpr std::array<bool, 12> movesCamera{
                false, false, false, false, false, false,
                true, true, true, true, true, true};

        for (std::size_t i = 0; i < animations.size(); ++i) {
            FakeContentHost host;
            TemplateScene scene("image_25d_" + std::to_string(i), 30.f, host,
                                1920.f, 1080.f);
            LayerHandle& image = addImageAnimation(scene, animations[i], asset,
                                                    "product", ImageFrameStyle{.cornerRadius = 64.f},
                                                    ImageCameraMove::None);
            image.position(960.f, 540.f);

            const FrameSubmission start = scene.submit(0);
            const FrameSubmission middle = scene.submit(55);
            const FrameSubmission late = scene.submit(120);
            const BoundLayer* a = findLayer(start, image.id());
            const BoundLayer* b = findLayer(middle, image.id());
            const BoundLayer* c = findLayer(late, image.id());
            check(a && b && c, "each 2.5D recipe submits its bound image at start, middle and late frames");
            check(a && a->draws() && a->content.isImage(), "each 2.5D recipe keeps image content bound");
            check(start.camera && middle.camera && late.camera,
                  "each 2.5D recipe submits a ChrononMotion3D camera pose");
            if (start.camera && middle.camera) {
                const bool cameraChanged =
                        std::abs(start.camera->position.x - middle.camera->position.x) > 0.01f ||
                        std::abs(start.camera->position.y - middle.camera->position.y) > 0.01f ||
                        std::abs(start.camera->position.z - middle.camera->position.z) > 0.01f;
                check(cameraChanged == movesCamera[i],
                      "only the six camera-authored 2.5D recipes move the camera");
            }
            if (a && b && c) {
                check(!sameMatrix(a->transform.world, b->transform.world) || movesCamera[i],
                      "the image transform changes during the authored entrance");
                check(std::isfinite(a->transform.opacity) && std::isfinite(b->transform.opacity) &&
                              std::isfinite(c->transform.opacity),
                      "2.5D opacity stays finite throughout the five-second timeline");
                check(a->transform.opacity >= 0.f && a->transform.opacity <= 1.f &&
                              b->transform.opacity >= 0.f && b->transform.opacity <= 1.f &&
                              c->transform.opacity >= 0.f && c->transform.opacity <= 1.f,
                      "2.5D opacity remains in the supported range");
            }
            check(scene.validate().empty(), "each 2.5D scene validates");
        }
    }

    void theFiveSquareCornerImageEntrancesSubmit() {
        section("five square-corner image entrances");
        constexpr const char* asset = "assets/test/square_bottle_test.png";
        constexpr std::array<ImageAnimation, 5> animations{
                ImageAnimation::Fade, ImageAnimation::Rise, ImageAnimation::ScalePop,
                ImageAnimation::Slide, ImageAnimation::Spin};
        constexpr std::array<const char*, 5> names{
                "fade", "rise", "scale_pop", "slide", "spin"};
        constexpr std::array<ImageCameraMove, 5> cameraMoves{
                ImageCameraMove::Dolly, ImageCameraMove::Orbit,
                ImageCameraMove::DollyOrbit, ImageCameraMove::Orbit,
                ImageCameraMove::Dolly};

        for (std::size_t i = 0; i < animations.size(); ++i) {
            FakeContentHost host;
            TemplateScene scene(std::string("image_") + names[i], 30.f, host,
                                1920.f, 1080.f);
            LayerHandle& image = addImageAnimation(scene, animations[i], asset, names[i],
                                                    ImageFrameStyle{.cornerRadius = 64.f},
                                                    cameraMoves[i]);
            image.position(960.f, 540.f);

            const FrameSubmission start = scene.submit(0);
            const FrameSubmission motion = scene.submit(12);
            const FrameSubmission settled = scene.submit(48);
            const FrameSubmission ongoing = scene.submit(90);
            const FrameSubmission exit = scene.submit(149);
            const BoundLayer* a = findLayer(start, image.id());
            const BoundLayer* b = findLayer(motion, image.id());
            const BoundLayer* c = findLayer(settled, image.id());
            const BoundLayer* e = findLayer(ongoing, image.id());
            const BoundLayer* d = findLayer(exit, image.id());

            check(a && b && c && d && e, "every animation submits its image at all sampled frames");
            check(start.camera && motion.camera && ongoing.camera && exit.camera,
                  "every 2.5D image scene submits the ChrononMotion3D camera pose");
            const bool cameraPoseChanged =
                    std::abs(start.camera->position.x - ongoing.camera->position.x) > 0.01f ||
                    std::abs(start.camera->position.y - ongoing.camera->position.y) > 0.01f ||
                    std::abs(start.camera->position.z - ongoing.camera->position.z) > 0.01f;
            check(cameraPoseChanged,
                  "dolly and orbit presets change the sampled ChrononMotion3D camera pose");
            check(!sameMatrix(findLayer(start, image.id())->clipFromLocal,
                              findLayer(ongoing, image.id())->clipFromLocal),
                  "the shared camera movement changes the image projection during the clip");
            check(a->draws() && a->content.isImage(), "the bound content remains an image");
            check(a->content.id == std::string("image/") + asset,
                  "Chronon receives the generated square-corner image asset unchanged");
            check(host.lastImageRequest().cornerRadius == 64.f,
                  "the C++ image request carries the modern rounded-corner radius");
            check(host.lastImageRequest().borderWidth == 0.f &&
                          host.lastImageRequest().borderColor.empty(),
                  "the C++ image request disables the outline stroke");
            check(a->transform.opacity <= b->transform.opacity,
                  "the entrance opacity progresses without going negative");
            check(scene.validate().empty(), "the image animation scene validates");
            if (animations[i] != ImageAnimation::Fade) {
                check(!sameMatrix(c->transform.world, e->transform.world),
                      "the selected image motion remains visibly active through the clip");
            } else {
                check(b->transform.opacity != e->transform.opacity,
                      "the fade remains in progress beyond its opening frames");
            }
            check(c->transform.opacity > 0.f, "the image is visible after its entrance");
            check(d->transform.opacity < c->transform.opacity,
                  "the image fades out before the end of the five-second timeline");
        }
    }

}// namespace

int main() {
    theFiveSquareCornerImageEntrancesSubmit();
    theTwelveClean25dAnimationsSubmitWithTheirAuthoredCameraBehavior();
    return chrononmotion_test::report();
}
