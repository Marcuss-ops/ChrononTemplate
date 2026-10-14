#include "chronontemplate/date_groups/DateGroupsPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <set>
#include <stdexcept>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    DateGroupsSpec twoAnimations() {
        DateGroupsSpec spec;
        spec.name = "date_groups_test";
        spec.fps = 30.f;
        spec.secondsPerDate = 3;
        spec.animations = {
            {.name = "first", .dates = {"1969", "1989"}},
            {.name = "second", .dates = {"2007", "2010"}},
        };
        return spec;
    }

    // Every layer is submitted; a date is on screen when it is visible and
    // opaque. Frames are chosen away from the fades at each window edge.
    std::set<std::string> visibleDates(TemplateScene& scene, int frame) {
        std::set<std::string> dates;
        for (const chronontemplate::BoundLayer& layer : scene.submit(frame).layers) {
            const std::string& id = layer.content.id;
            const bool readable = layer.transform.visible && layer.transform.opacity > 0.5f;
            if (readable && id.rfind("text/", 0) == 0 && id.find("@200") != std::string::npos) {
                dates.insert(id.substr(0, id.find('@')));
            }
        }
        return dates;
    }

    void durationIsTenSecondsPerTwoDatesThreeSecondsEach() {
        section("date groups duration");
        check(dateGroupsDurationFrames(twoAnimations()) == 360,
              "two animations of two 3-second dates last 12 seconds");
    }

    void eachDateHoldsItsOwnWindowInOrder() {
        section("each date shows in its window, in order");
        FakeContentHost host;
        TemplateScene scene("date_groups_test", 30.f, host, 1920.f, 1080.f);
        (void)addDateGroups(scene, twoAnimations());
        check(scene.validate().empty(), "the date-group scene validates");

        const auto first = visibleDates(scene, 30);
        check(first.count("text/1969") == 1 && first.count("text/1989") == 0,
              "the first date is shown on its own in the first 3 seconds");
        const auto second = visibleDates(scene, 120);
        check(second.count("text/1989") == 1 && second.count("text/1969") == 0,
              "the second date replaces the first after 3 seconds");
        const auto next = visibleDates(scene, 200);
        check(next.count("text/2007") == 1 && next.count("text/1989") == 0,
              "the next animation starts at 6 seconds");
        const auto last = visibleDates(scene, 300);
        check(last.count("text/2010") == 1 && last.count("text/2007") == 0,
              "the last date of the last animation is shown at 10 seconds");
    }

    void invalidSpecsFailClosed() {
        section("invalid date groups fail closed");
        FakeContentHost host;
        TemplateScene scene("date_groups_invalid", 30.f, host, 1920.f, 1080.f);

        DateGroupsSpec empty = twoAnimations();
        empty.animations.clear();
        bool threw = false;
        try { (void)addDateGroups(scene, empty); } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "an empty animation list throws");

        DateGroupsSpec noDate = twoAnimations();
        noDate.animations[0].dates.clear();
        threw = false;
        try { (void)addDateGroups(scene, noDate); } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "an animation without dates throws");
    }

} // namespace

int main() {
    durationIsTenSecondsPerTwoDatesThreeSecondsEach();
    eachDateHoldsItsOwnWindowInOrder();
    invalidSpecsFailClosed();
    return chrononmotion_test::report();
}
