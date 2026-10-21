#ifndef CHRONONTEMPLATE_DATE_TIMELINE_PACK_HPP
#define CHRONONTEMPLATE_DATE_TIMELINE_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <string>
#include <vector>

namespace chronontemplate::date_timeline {

    enum class TimelineMotion {
        StaggerFade, MarkerPop, AlternatingRise, SideSlide, CenterOut,
        TravelingCursor, SegmentDraw, PairedWave, DatesFirst, SoftCascade
    };

    struct TimelineMotionChoice {
        TimelineMotion motion{};
        std::string id{};
        std::string label{};
    };

    struct DateMilestone {
        std::string label{};
        std::vector<std::string> dates{};
    };

    struct DateTimelineSpec {
        std::string name{"date_timeline_v1"};
        std::string heading{"A CHRONOLOGY"};
        std::vector<DateMilestone> milestones{};
        TimelineMotion motion{TimelineMotion::StaggerFade};
        int eventStaggerFrames{12};
        int eventHoldFrames{80};
        float width{1920.f};
        float height{1080.f};
        std::string font{"ChrononTemplate/assets/fonts/Inter-Regular.ttf"};
    };

    [[nodiscard]] std::vector<DateMilestone> technologyDateSample();
    [[nodiscard]] std::vector<TimelineMotionChoice> timelineMotionChoices();
    [[nodiscard]] int dateTimelineDurationFrames(const DateTimelineSpec& spec);
    /// Compose only the dates timeline: no opening title sequence or Fast Intro.
    [[nodiscard]] LayerHandle& addDateTimeline(TemplateScene& scene,
                                               const DateTimelineSpec& spec);

} // namespace chronontemplate::date_timeline

#endif // CHRONONTEMPLATE_DATE_TIMELINE_PACK_HPP
