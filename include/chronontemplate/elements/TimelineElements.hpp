#ifndef CHRONONTEMPLATE_TIMELINE_ELEMENTS_HPP
#define CHRONONTEMPLATE_TIMELINE_ELEMENTS_HPP

// Graphics objects 01-06: data storytelling and timelines.

#include "chronontemplate/elements/ElementsCommon.hpp"

#include <string>
#include <vector>

namespace chronontemplate::elements {

    /// 01 DataTimeline: horizontal rail with date dots, links and one
    /// selected event. Every date is an independent object.
    struct DataTimelineEvent {
        std::string date{};
        std::string label{};
    };
    struct DataTimelineSpec {
        std::vector<DataTimelineEvent> events{};
        int activeEvent{0};
        float spacing{220.f};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"data_timeline"};
    };
    [[nodiscard]] LayerHandle& addDataTimeline(TemplateScene& scene,
                                               const DataTimelineSpec& spec);

    /// 02 MilestoneCard: giant year, headline and graphic accent.
    struct MilestoneCardSpec {
        std::string year{};
        std::string headline{};
        std::string accent{"#E8B84A"};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"milestone_card"};
    };
    [[nodiscard]] LayerHandle& addMilestoneCard(TemplateScene& scene,
                                                const MilestoneCardSpec& spec);

    /// 03 DateRangeBracket: bracket linking two dates with computed span.
    struct DateRangeBracketSpec {
        std::string from{};
        std::string to{};
        int fromYear{0};
        int toYear{0};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"date_range_bracket"};
    };
    [[nodiscard]] LayerHandle& addDateRangeBracket(TemplateScene& scene,
                                                   const DateRangeBracketSpec& spec);

    /// 04 MetricCounterBlock: big number with unit, label and delta flag.
    struct MetricCounterBlockSpec {
        std::string value{};
        std::string unit{};
        std::string label{};
        std::string delta{};
        bool deltaUp{true};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"metric_counter_block"};
    };
    [[nodiscard]] LayerHandle& addMetricCounterBlock(TemplateScene& scene,
                                                     const MetricCounterBlockSpec& spec);

    /// 05 ComparisonDelta: two values side by side with percent delta.
    struct ComparisonDeltaSpec {
        std::string leftValue{};
        std::string leftLabel{};
        std::string rightValue{};
        std::string rightLabel{};
        std::string delta{};
        bool deltaUp{true};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"comparison_delta"};
    };
    [[nodiscard]] LayerHandle& addComparisonDelta(TemplateScene& scene,
                                                  const ComparisonDeltaSpec& spec);

    /// 06 EventSequenceRail: vertical chain of linked events.
    struct EventSequenceRailSpec {
        std::vector<DataTimelineEvent> events{};
        float spacing{150.f};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"event_sequence_rail"};
    };
    [[nodiscard]] LayerHandle& addEventSequenceRail(TemplateScene& scene,
                                                    const EventSequenceRailSpec& spec);

}// namespace chronontemplate::elements

#endif//CHRONONTEMPLATE_TIMELINE_ELEMENTS_HPP
