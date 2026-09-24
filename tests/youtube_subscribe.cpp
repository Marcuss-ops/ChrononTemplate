// Through the module's one include, so the aggregator is compiled by a test and
// cannot rot: it is the header the README tells a template author to use.
#include "chronontemplate/chronontemplate.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include "chronontemplate/UiPrimitives.hpp"

#include <array>
#include <stdexcept>
#include <string>

using namespace chronontemplate;
using chronontemplate::templates::buildYouTubeSubscribe;
using chronontemplate::templates::YouTubeSubscribePack;
using chronontemplate::templates::YouTubeSubscribeSpec;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chronontemplate_test::sameMatrix;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    constexpr float kFps = 30.f;
    constexpr int kEntranceFrames = 18;

    YouTubeSubscribeSpec cardSpec() {

        YouTubeSubscribeSpec spec;
        spec.fps = kFps;
        return spec;
    }

    float controllerScale(TemplateScene& scene, const YouTubeSubscribePack& pack) {

        return scene.motion().state(pack.controller->id()).local.scale.x;
    }

    float buttonScale(TemplateScene& scene, const YouTubeSubscribePack& pack) {

        return scene.motion().state(pack.button->id()).local.scale.x;
    }

    void composition() {

        section("subscribe card composition");
        FakeContentHost host;
        TemplateScene scene("youtube_subscribe", kFps, host);
        const YouTubeSubscribePack pack = buildYouTubeSubscribe(scene, cardSpec());

        check(scene.bindings().size() == 6, "the card binds its six content layers");
        check(scene.motion().layerCount() == 7, "the card is one controller plus six content layers");
        check(scene.validate().empty(), "the card hierarchy is valid");
        check(pack.clickFrame == 45, "the click lands in the middle of the composition by default");
        check(pack.endFrame == 90, "the pack reports the composition end");

        const std::array<const char*, 7> names{
                "Null_Subscribe", "Avatar", "ChannelName", "SubscriberCount", "SubscribeButton", "SubscribeLabel", "Bell"};
        for (const char* name : names) {
            check(scene.motion().findLayer(name) != nullptr, "the card contains the layer the design names");
        }

        const auto* label = scene.motion().findLayer("SubscribeLabel");
        const auto* button = scene.motion().findLayer("SubscribeButton");
        check(label != nullptr && button != nullptr && label->parentId == button->id,
              "the subscribe label lives inside the button");
        check(!scene.bindings().bound(pack.controller->id()), "the controller layer owns no content");

        const std::array<LayerHandle*, 5> children{
                pack.avatar, pack.channelName, pack.subscriberCount, pack.button, pack.bell};
        for (LayerHandle* layer : children) {
            const auto* built = scene.motion().findLayer(layer->id());
            check(built != nullptr && built->parentId == pack.controller->id(),
                  "every content layer hangs off the controller");
        }
        check(label->parentId == button->id, "the label is the button's child, not the controller's");

        const FrameSubmission frame = scene.submit(30);
        check(frame.layerCount() == 7, "the submission carries the whole card");
        std::size_t drawing = 0;
        for (const BoundLayer& layer : frame.layers) {
            if (!layer.draws()) continue;
            ++drawing;
            check(layer.measurement == chrononmotion::motion::MeasurementState::Current,
                  "every carried measurement is the current one");
        }
        check(drawing == 6, "six of the seven layers draw content");
    }

    void entranceAndExit() {

        section("card entrance and exit");
        FakeContentHost host;
        TemplateScene scene("youtube_subscribe", kFps, host);
        const YouTubeSubscribePack pack = buildYouTubeSubscribe(scene, cardSpec());

        (void)scene.submit(pack.startFrame);
        check(scene.motion().worldOpacity(pack.controller->id()) < 1.f,
              "the card starts as an entrance, not as a finished frame");
        check(controllerScale(scene, pack) < 1.f, "the card scales up from below its resting size");

        (void)scene.submit(pack.startFrame + kEntranceFrames);
        checkNear(controllerScale(scene, pack), 1.f, 0.001f, "the card settles at its resting size");

        (void)scene.submit(pack.startFrame + 30);
        checkNear(scene.motion().worldOpacity(pack.controller->id()), 1.f, 0.001f, "the card is fully visible");
        checkNear(scene.motion().worldOpacity(pack.label->id()), 1.f, 0.001f,
                  "the label inherits the controller's opacity");

        (void)scene.submit(pack.endFrame);
        check(scene.motion().worldOpacity(pack.controller->id()) == 0.f, "the card exits through the controller");
        check(scene.motion().worldOpacity(pack.label->id()) == 0.f, "the exit reaches the children too");
    }

    void clickPulse() {

        section("click pulse");
        FakeContentHost host;
        TemplateScene scene("youtube_subscribe", kFps, host);
        const YouTubeSubscribePack pack = buildYouTubeSubscribe(scene, cardSpec());

        (void)scene.submit(pack.clickFrame - 1);
        const float held = buttonScale(scene, pack);
        (void)scene.submit(pack.clickFrame);
        const float punched = buttonScale(scene, pack);
        (void)scene.submit(pack.clickFrame + 10);
        const float settled = buttonScale(scene, pack);

        checkNear(held, 1.f, 0.001f, "the button holds its resting size up to the click");
        check(punched > held, "the click pokes the button above its resting size");
        checkNear(punched, 1.12f, 0.001f, "the poke is the authored amount, not a ramp");
        checkNear(settled, 1.f, 0.001f, "the button settles back after the click");
    }

    void determinism() {

        section("card determinism");
        FakeContentHost host;
        TemplateScene scene("youtube_subscribe", kFps, host);
        const YouTubeSubscribePack pack = buildYouTubeSubscribe(scene, cardSpec());

        const FrameSubmission first = scene.submit(40);
        (void)scene.submit(80);
        const FrameSubmission again = scene.submit(40);

        check(sameMatrix(findLayer(first, pack.avatar->id())->transform.world,
                         findLayer(again, pack.avatar->id())->transform.world),
              "the same frame always resolves the card to the same matrix");
        check(findLayer(first, pack.channelName->id())->transform.opacity ==
                      findLayer(again, pack.channelName->id())->transform.opacity,
              "the same frame always resolves the card to the same opacity");
    }

    void primitiveContracts() {

        section("web primitive contracts");
        ui::RoundedRect card{.width = 320.f, .height = 120.f, .radius = 24.f};
        card.validate();
        ui::Shadow shadow{.blur = 20.f, .offsetY = 8.f, .opacity = 0.3f};
        shadow.validate();
        ui::Button button{.shape = card, .shadow = shadow, .label = "SUBSCRIBE"};
        button.validate();
        ui::AvatarCircle avatar{.diameter = 96.f, .assetPath = "avatar.png"};
        avatar.validate();
        ui::Border border{.width = 2.f, .color = "#FF3045"};
        border.validate();
        ui::IconSlot icon{.width = 32.f, .height = 32.f, .assetPath = "bell.png"};
        icon.validate();
        ui::Row row{.gap = {.value = 12.f}, .padding = {.top = 8.f, .right = 8.f, .bottom = 8.f, .left = 8.f}};
        row.validate();
        ui::Column column{.gap = {.value = 12.f}};
        column.validate();
        ui::Stack stack{.padding = {.top = 4.f, .right = 4.f, .bottom = 4.f, .left = 4.f}};
        stack.validate();
        ui::Badge badge{.label = "NEW", .fill = "#FF3045"};
        badge.validate();
        ui::Separator separator{.length = 120.f, .thickness = 2.f, .color = "#D0D5DD"};
        separator.validate();

        const style::Tokens light = style::WebLight();
        const style::Tokens dark = style::WebDark();
        const style::Tokens youtube = style::YouTubeBrand();
        const style::Tokens instagram = style::InstagramBrand();
        const style::Tokens breaking = style::BreakingNewsBrand();
        light.validate();
        dark.validate();
        youtube.validate();
        instagram.validate();
        breaking.validate();
        check(youtube.accent == "#FF0000", "YouTube tokens expose the brand accent");
        check(instagram.accent == "#E1306C", "Instagram tokens expose the brand accent");

        bool rejected = false;
        try {
            ui::RoundedRect invalid{.width = 20.f, .height = 20.f, .radius = 11.f};
            invalid.validate();
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        check(rejected, "rounded rectangles reject a radius larger than half the bounds");
    }

    void refusedSpecs() {

        section("refused specs");
        FakeContentHost host;

        bool tooShort = false;
        try {
            TemplateScene scene("short", kFps, host);
            (void)buildYouTubeSubscribe(scene, YouTubeSubscribeSpec{.fps = kFps, .duration = 30});
        } catch (const std::invalid_argument&) {
            tooShort = true;
        }
        check(tooShort, "a composition too short for entrance, click and exit is refused");

        bool clickTooLate = false;
        try {
            TemplateScene scene("late", kFps, host);
            (void)buildYouTubeSubscribe(scene, YouTubeSubscribeSpec{.fps = kFps, .duration = 90, .clickFrame = 85});
        } catch (const std::invalid_argument&) {
            clickTooLate = true;
        }
        check(clickTooLate, "a click with no room for the pulse and the exit is refused");

        bool missingText = false;
        try {
            TemplateScene scene("empty", kFps, host);
            (void)buildYouTubeSubscribe(scene, YouTubeSubscribeSpec{.channelName = "", .fps = kFps});
        } catch (const std::invalid_argument&) {
            missingText = true;
        }
        check(missingText, "a card with no channel name is refused");

        bool wrongTimeBase = false;
        try {
            TemplateScene scene("timebase", kFps, host);
            (void)buildYouTubeSubscribe(scene, YouTubeSubscribeSpec{.fps = 24.f});
        } catch (const std::invalid_argument&) {
            wrongTimeBase = true;
        }
        check(wrongTimeBase, "a spec on a different time base than the scene is refused");
    }

}// namespace

int main() {

    composition();
    entranceAndExit();
    clickPulse();
    determinism();
    primitiveContracts();
    refusedSpecs();
    return chrononmotion_test::report();
}
