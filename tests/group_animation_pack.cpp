#include "chronontemplate/group_animation/GroupAnimationPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    bool containsRole(const std::vector<GroupRole>& roles, GroupRole role) {
        for (const GroupRole candidate : roles) {
            if (candidate == role) return true;
        }
        return false;
    }

    void specsAreBounded() {
        section("group showcase specs");
        const std::vector<GroupAnimationSpec> specs = groupAnimationShowcaseSpecs();
        check(specs.size() == 5, "the first showcase publishes five clips");
        for (const GroupAnimationSpec& spec : specs) {
            check(spec.fps == 30, "every clip is authored at 30 fps");
            check(spec.durationFrames <= spec.fps * 10, "every clip is at most ten seconds");
            const std::vector<GroupMemberTiming> timeline = groupShowcaseTimeline(spec);
            check(timeline.size() >= 2 && timeline.size() <= 8, "every group has 2..8 members");
            check(timeline.front().offsetFrames == 0, "the phrase anchor enters at group start");
            for (std::size_t index = 0; index < timeline.size(); ++index) {
                if (index > 0) {
                    check(timeline[index].offsetFrames > timeline[index - 1].offsetFrames,
                          "member offsets follow the stagger");
                }
                for (std::size_t other = 0; other < index; ++other) {
                    check(timeline[index].role != timeline[other].role,
                          "a group never repeats a role");
                }
            }
        }
        check(containsRole(groupShowcaseRoles(GroupShowcaseMode::AllRoles), GroupRole::ImportantPhrase) &&
              containsRole(groupShowcaseRoles(GroupShowcaseMode::AllRoles), GroupRole::Image) &&
              containsRole(groupShowcaseRoles(GroupShowcaseMode::AllRoles), GroupRole::Caption) &&
              containsRole(groupShowcaseRoles(GroupShowcaseMode::AllRoles), GroupRole::Date) &&
              containsRole(groupShowcaseRoles(GroupShowcaseMode::AllRoles), GroupRole::Metric),
              "the master contains every published role");
    }

    void everyModeBuildsAValidScene() {
        section("native scene composition");
        for (const GroupAnimationSpec& spec : groupAnimationShowcaseSpecs()) {
            FakeContentHost host;
            TemplateScene scene(spec.id, static_cast<float>(spec.fps), host, 1920.f, 1080.f);
            buildGroupAnimationShowcase(scene, spec);
            check(scene.validate().empty(), "the generated hierarchy is valid");
            check(scene.bindings().size() > 5, "the scene binds native text/image/shape content");
            const FrameSubmission early = scene.submit(0);
            const FrameSubmission middle = scene.submit(spec.durationFrames / 2);
            check(!early.layers.empty(), "frame zero carries the stage and first entrance");
            check(!middle.layers.empty(), "the middle frame still carries the group");
            int drawnMiddle = 0;
            for (const BoundLayer& layer : middle.layers) {
                if (layer.draws()) ++drawnMiddle;
            }
            check(drawnMiddle > 0, "the middle frame draws visible content");
        }
    }

    void invalidSpecsFailClosed() {
        section("group validation");
        GroupAnimationSpec spec = groupAnimationShowcaseSpecs().front();
        FakeContentHost host;

        const auto rejects = [&](GroupAnimationSpec candidate) {
            TemplateScene scene(candidate.id, static_cast<float>(candidate.fps), host, 1920.f, 1080.f);
            bool rejected = false;
            try {
                buildGroupAnimationShowcase(scene, candidate);
            } catch (const std::invalid_argument&) {
                rejected = true;
            }
            check(rejected, "invalid group spec is rejected");
        };

        spec.durationFrames = 301;
        rejects(spec);
        spec = groupAnimationShowcaseSpecs().front();
        spec.staggerFrames = -1;
        rejects(spec);
        spec = groupAnimationShowcaseSpecs().front();
        spec.enterFrames = 0;
        rejects(spec);
        spec = groupAnimationShowcaseSpecs().front();
        spec.phrase.clear();
        rejects(spec);
        spec = groupAnimationShowcaseSpecs().front();
        spec.imageAsset.clear();
        rejects(spec);
        spec = groupAnimationShowcaseSpecs().front();
        spec.durationFrames = 1;
        rejects(spec);
    }

    void roleIdsMatchTheProductVocabulary() {
        section("role wire ids");
        check(std::string(groupRoleId(GroupRole::Image)) == "image", "image id");
        check(std::string(groupRoleId(GroupRole::ImportantPhrase)) == "important_phrase", "phrase id");
        check(std::string(groupRoleId(GroupRole::Caption)) == "caption", "caption id");
        check(std::string(groupRoleId(GroupRole::Date)) == "date", "date id");
        check(std::string(groupRoleId(GroupRole::Metric)) == "metric", "metric id");
    }

}// namespace

int main() {
    specsAreBounded();
    everyModeBuildsAValidScene();
    invalidSpecsFailClosed();
    roleIdsMatchTheProductVocabulary();
    return chrononmotion_test::report();
}
