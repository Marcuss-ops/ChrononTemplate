#include "chronontemplate/TemplateScene.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>
#include <string>

using namespace chronontemplate;
using chrononmotion::motion::ContentRef;
using chrononmotion::motion::MeasurementState;
using chrononmotion::motion::MotionScene;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chronontemplate_test::sameMatrix;
using chronontemplate_test::UnmeasuredHost;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    /// The template from the design: content by Chronon, space/time by the motion
    /// core, bindings by this module.
    void contentCallsBindOneRowEach() {

        section("content calls and bindings");
        FakeContentHost host;
        TemplateScene scene("youtube_subscribe", 30.f, host);

        LayerHandle& title = scene.text(TextSpec{.text = "Wrestling Discovery", .font = "Inter-Bold.ttf", .fontSize = 96.f});
        LayerHandle& count = scene.text(TextSpec{.text = "1.2M subscribers", .fontSize = 48.f});
        LayerHandle& avatar = scene.image(ImageSpec{.path = "avatar.png"});

        title.position(960.f, 540.f, 0.f)
                .animate(ScalePop{.inFrame = 0, .duration = 15, .from = 0.6f, .to = 1.f})
                .animate(FadeIn{.inFrame = 0, .duration = 10});
        count.position(960.f, 850.f)
                .animate(SlideIn{.direction = chrononmotion::motion::presets::Direction::Up,
                                 .inFrame = 10, .duration = 12, .distance = 120.f})
                .animate(FadeOut{.startFrame = 80, .duration = 10});
        avatar.position(750.f, 540.f, 20.f)
                .animate(SpinXYZ{.inFrame = 10, .duration = 25, .turns = 0.75f});

        check(scene.bindings().size() == 3, "every content call adds exactly one binding row");
        check(scene.motion().layerCount() == 3, "every content call creates exactly one motion layer");
        check(avatar.contentId() == "image/avatar.png", "the binding carries Chronon's id unchanged");
        check(title.contentId() == "text/Wrestling Discovery@96", "a text binding carries Chronon's measured id");
        check(scene.validate().empty(), "the generated hierarchy is valid");

        const FrameSubmission frame = scene.submit(0);
        check(frame.layerCount() == 3, "the submission carries every layer");
        check(frame.sceneName == "youtube_subscribe", "the submission keeps the composition name");
        check(frame.camera != nullptr, "the bridge samples the camera rig");

        for (const BoundLayer& layer : frame.layers) {
            check(layer.draws(), "a content layer draws something");
            check(layer.content.metrics.measured(), "the ref carries Chronon's measurement");
            check(layer.measurement == MeasurementState::Current, "the carried measurement is the current one");
        }
        check(findLayer(frame, avatar.id())->content.isImage(), "the image layer keeps its content kind");
        check(findLayer(frame, count.id())->content.isText(), "the text layer keeps its content kind");
    }

    void aControllerLayerNeedsNoBinding() {

        section("controller layer");
        FakeContentHost host;
        TemplateScene scene("grouped", 30.f, host);

        LayerHandle& controller = scene.group("Null_Subscribe");
        LayerHandle& label = scene.text(TextSpec{.text = "Subscribe", .fontSize = 48.f});
        label.parent(controller.id()).position(960.f, 540.f);
        controller.animate(ScalePop{.inFrame = 0, .duration = 10, .from = 0.5f, .to = 1.f});

        check(scene.bindings().size() == 1, "only the content layer is bound");
        check(!scene.bindings().bound(controller.id()), "the controller layer has no binding row");

        const FrameSubmission atStart = scene.submit(0);
        const FrameSubmission atEnd = scene.submit(10);
        const BoundLayer* null = findLayer(atStart, controller.id());
        const BoundLayer* text = findLayer(atStart, label.id());

        check(null != nullptr && !null->draws(), "the controller layer draws nothing");
        check(text != nullptr && text->draws(), "the label draws its content");
        check(!sameMatrix(findLayer(atStart, label.id())->transform.world,
                          findLayer(atEnd, label.id())->transform.world),
              "the child matrix follows the controller layer");
    }

    void determinismAndCameraMove() {

        section("determinism and camera");
        FakeContentHost host;
        TemplateScene scene("orbit", 30.f, host);

        LayerHandle& title = scene.text(TextSpec{.text = "CHRONON", .fontSize = 120.f});
        title.position(960.f, 540.f).animate(FadeIn{.inFrame = 0, .duration = 12});
        scene.camera().orbit(-0.35f, 0.05f).between(0, 90);

        const FrameSubmission first = scene.submit(12);
        (void)scene.submit(80);
        const FrameSubmission again = scene.submit(12);
        const FrameSubmission later = scene.submit(80);

        check(sameMatrix(findLayer(first, title.id())->transform.world,
                         findLayer(again, title.id())->transform.world),
              "the same frame always resolves to the same matrix");
        check(findLayer(first, title.id())->transform.opacity == findLayer(again, title.id())->transform.opacity,
              "the same frame always resolves to the same opacity");

        check(first.camera != nullptr && later.camera != nullptr, "every frame carries a camera pose");
        check(first.camera->hasTarget, "the camera keeps looking at its target");
        const bool moved = first.camera->position.x != later.camera->position.x ||
                           first.camera->position.y != later.camera->position.y ||
                           first.camera->position.z != later.camera->position.z;
        check(moved, "the orbit moves the eye over the authored window");
    }

    void aRemeasuredAssetCannotSlipThrough() {

        section("staleness");
        FakeContentHost host;
        TemplateScene scene("stale", 30.f, host);

        LayerHandle& title = scene.text(TextSpec{.text = "SUBSCRIBE", .fontSize = 96.f});
        const ContentId content = title.contentId();

        check(findLayer(scene.submit(0), title.id())->measurement == MeasurementState::Current,
              "a fresh measurement is reported as current");

        host.remeasure(content);
        bool rejected = false;
        try {
            (void)scene.submit(0);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        check(rejected, "a re-measured asset stops the frame instead of mis-anchoring it");

        scene.bridge().enforceMeasurements(false);
        check(findLayer(scene.submit(0), title.id())->measurement == MeasurementState::Stale,
              "the stale measurement is still reported when enforcement is off");
    }

    void defectsAreRefused() {

        section("refused defects");
        FakeContentHost host;
        TemplateScene scene("defects", 30.f, host);
        (void)scene.text(TextSpec{.text = "A", .fontSize = 48.f});

        // A content layer added straight to the motion scene has no binding row.
        MotionScene& motion = scene.motion();
        motion.addContent(900, "Raw", ContentRef::text("raw.asset", chrononmotion::Vector2(120.f, 60.f)));

        bool rejected = false;
        try {
            (void)scene.submit(0);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        check(rejected, "a content layer with no binding refuses to submit");

        UnmeasuredHost bare;
        TemplateScene unmeasured("bare", 30.f, bare);
        bool refused = false;
        try {
            (void)unmeasured.text(TextSpec{.text = "A", .fontSize = 48.f});
        } catch (const std::invalid_argument&) {
            refused = true;
        }
        check(refused, "content handed over without a measurement is refused");
    }

}// namespace

int main() {

    contentCallsBindOneRowEach();
    aControllerLayerNeedsNoBinding();
    determinismAndCameraMove();
    aRemeasuredAssetCannotSlipThrough();
    defectsAreRefused();
    return chrononmotion_test::report();
}
