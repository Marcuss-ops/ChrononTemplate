#include "chrononmotion/chrononmotion.hpp"
#include "chrononmotion/templates/Templates.hpp"

#include "motion_check.hpp"

#include <stdexcept>
#include <string>

using namespace chrononmotion;
using namespace chrononmotion::motion;
using namespace chrononmotion::templates;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    constexpr float kFps = 30.f;

    TemplateData sampleData() {
        TemplateData data;
        data.primaryText = "Wrestling Discovery";
        data.secondaryText = "1.2M subscribers";
        data.authorText = "@wrestling";
        data.imageId = "avatar.asset";
        data.iconId = "social.icon";
        data.fps = kFps;
        data.startFrame = 10;
        data.duration = 90;
        return data;
    }

    void catalogAndValidation() {
        section("template catalog and validation");
        check(available().size() == 7, "the catalog exposes seven complete demo templates");
        check(std::string(name(TemplateId::YouTubeSubscribe)) == "youtube_subscribe",
              "template IDs have stable wire names");
        check(std::string(name(TemplateId::InstagramLike)) == "instagram_like",
              "like template has a stable wire name");
        check(std::string(name(TemplateId::BreakingNews)) == "breaking_news",
              "breaking news template has a stable wire name");
        check(std::string(name(TemplateId::EpisodeTag)) == "episode_tag",
              "episode tag template has a stable wire name");

        TemplateData invalid = sampleData();
        invalid.duration = 0;
        bool rejected = false;
        try {
            (void)build(TemplateId::QuoteCard, invalid);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        check(rejected, "invalid template timing is rejected at the template boundary");

        invalid.duration = 30;
        rejected = false;
        try {
            (void)build(TemplateId::LowerThird, invalid);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        check(rejected, "a template duration too short for all phases is rejected");
    }

    void everyTemplateBuildsAValidTimeline() {
        section("template scenes");
        const TemplateData data = sampleData();
        const int expectedEnd = data.startFrame + data.duration;

        for (const TemplateId id : available()) {
            MotionScene scene = build(id, data);
            check(scene.name() == name(id), "template scene name matches its registry identity");
            check(scene.fps() == kFps, "template preserves the requested FPS");
            check(!scene.layers().empty(), "template produces layers");
            check(scene.validate().empty(), "template produces a valid hierarchy");
            check(scene.contentEndFrame() >= expectedEnd, "template lifetime reaches its requested end");

            scene.evaluate(data.startFrame);
            const std::string first = std::to_string(scene.worldOpacity(scene.layers().front().id));
            scene.evaluate(expectedEnd);
            scene.evaluate(data.startFrame);
            const std::string second = std::to_string(scene.worldOpacity(scene.layers().front().id));
            check(first == second, "template evaluation is deterministic after another frame");

            const CompiledScene compiled = scene.compile();
            check(compiled.frame == data.startFrame, "compiled template reports its evaluated frame");
            check(compiled.transforms.size() == scene.layerCount(), "compiled template contains every layer transform");
        }
    }

    void subscribeHasWebStyleComposition() {
        section("subscribe composition");
        const TemplateData data = sampleData();
        MotionScene scene = build(TemplateId::YouTubeSubscribe, data);
        const Layer* button = scene.findLayer("SubscribeButton");
        const Layer* label = scene.findLayer("SubscribeLabel");
        const Layer* avatar = scene.findLayer("Avatar");
        check(button && label && avatar, "subscribe creates avatar, button and label layers");
        check(label->parentId == button->id, "subscribe label is parented to the button");

        scene.evaluate(data.startFrame);
        check(scene.worldOpacity(button->id) < 1.f, "subscribe starts as an entrance animation");
        scene.evaluate(data.startFrame + 20);
        const Vector3 startScale = scene.state(button->id).local.scale;
        scene.evaluate(data.startFrame + 27);
        const Vector3 settledScale = scene.state(button->id).local.scale;
        check(startScale.x != settledScale.x, "subscribe button has a scale pop after entering");
        scene.evaluate(data.startFrame + data.duration);
        check(scene.worldOpacity(button->id) == 0.f, "subscribe exits cleanly");
    }

    void likeHasBurstParticles() {
        section("like burst composition");
        const TemplateData data = sampleData();
        MotionScene scene = build(TemplateId::InstagramLike, data);
        check(scene.layerCount() >= 8, "like template contains heart, text and radial particles");
        const Layer* heart = scene.findLayer("Heart");
        check(heart != nullptr, "like template has a heart layer");

        scene.evaluate(data.startFrame + 4);
        const float startOpacity = scene.worldOpacity(heart->id);
        scene.evaluate(data.startFrame + 16);
        const float peakOpacity = scene.worldOpacity(heart->id);
        check(peakOpacity >= startOpacity, "heart reveals during the burst");
        scene.evaluate(data.startFrame + data.duration);
        check(scene.worldOpacity(heart->id) == 0.f, "heart burst exits through opacity");
    }

}// namespace

int main() {
    catalogAndValidation();
    everyTemplateBuildsAValidTimeline();
    subscribeHasWebStyleComposition();
    likeHasBurstParticles();
    return chrononmotion_test::report();
}
