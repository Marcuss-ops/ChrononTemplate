#include "chronontemplate/elements/TimelineElements.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <string>

using namespace chronontemplate;
using namespace chronontemplate::elements;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void submitsThrough(const char* what, TemplateScene& scene, LayerHandle& root) {
        const FrameSubmission start = scene.submit(0);
        const FrameSubmission settled = scene.submit(48);
        const FrameSubmission late = scene.submit(149);
        check(findLayer(start, root.id()) && findLayer(settled, root.id()) &&
                      findLayer(late, root.id()),
              what);
        check(scene.validate().empty(), "each timeline scene validates");
    }

    void theRegistryHoldsThirtyUniqueIds() {
        section("registry holds thirty unique ids");
        const std::vector<std::string> ids = allElementIds();
        check(ids.size() == 30, "the registry lists exactly thirty objects");
        for (std::size_t i = 0; i < ids.size(); ++i) {
            check(!ids[i].empty(), "every registry id is non-empty");
            for (std::size_t j = i + 1; j < ids.size(); ++j) {
                check(ids[i] != ids[j], "registry ids are unique");
            }
        }
        check(std::string(elementId(ElementKind::DataTimeline)) == "timeline.data_timeline",
              "the data timeline keeps its stable id");
        check(std::string(elementId(ElementKind::FlowDiagramNode)) == "diagram.flow_diagram_node",
              "the last object keeps its stable id");
    }

    void dataTimelineComposes() {
        section("01 data timeline");
        FakeContentHost host;
        TemplateScene scene("el_timeline", 30.f, host, 1920.f, 1080.f);
        DataTimelineSpec spec;
        spec.events = {{"2007", "iPhone"}, {"2010", "iPad"}, {"2017", "X"}};
        spec.activeEvent = 1;
        LayerHandle& root = addDataTimeline(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the timeline root submits across the clip", scene, root);
        const FrameSubmission settled = scene.submit(48);
        check(settled.layers.size() == 11,
              "three labeled events compose root, rail, dots, dates and labels");
        const auto* active = host.findShapeRequest("data_timeline_dot_1");
        const auto* idle = host.findShapeRequest("data_timeline_dot_0");
        check(active && active->fillColor == "#E8B84A",
              "the active event dot carries the accent");
        check(idle && idle->fillColor == "#8A8F98",
              "idle event dots stay muted");
        bool threw = false;
        try {
            DataTimelineSpec bad;
            bad.events = {{"2007", "iPhone"}};
            bad.activeEvent = 5;
            addDataTimeline(scene, bad);
        } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "an out-of-range active event fails closed");
    }

    void milestoneCardComposes() {
        section("02 milestone card");
        FakeContentHost host;
        TemplateScene scene("el_milestone", 30.f, host, 1920.f, 1080.f);
        MilestoneCardSpec spec;
        spec.year = "2007";
        spec.headline = "THE FIRST iPHONE";
        LayerHandle& root = addMilestoneCard(scene, spec);
        root.position(960.f, 480.f);
        submitsThrough("the milestone root submits across the clip", scene, root);
        const FrameSubmission settled = scene.submit(48);
        check(settled.layers.size() == 4, "year, headline and accent compose four layers");
        const auto* accent = host.findShapeRequest("milestone_card_accent");
        check(accent && accent->fillColor == "#E8B84A",
              "the milestone accent keeps its default gold");
    }

    void dateRangeBracketComposes() {
        section("03 date range bracket");
        FakeContentHost host;
        TemplateScene scene("el_bracket", 30.f, host, 1920.f, 1080.f);
        DateRangeBracketSpec spec;
        spec.from = "1998";
        spec.to = "2010";
        spec.fromYear = 1998;
        spec.toYear = 2010;
        LayerHandle& root = addDateRangeBracket(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the bracket root submits across the clip", scene, root);
        const FrameSubmission settled = scene.submit(48);
        check(settled.layers.size() == 7, "rail, ticks, dates and span compose seven layers");
        bool threw = false;
        try {
            DateRangeBracketSpec bad;
            bad.from = "2010";
            bad.to = "1998";
            bad.fromYear = 2010;
            bad.toYear = 1998;
            addDateRangeBracket(scene, bad);
        } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "an inverted range fails closed");
    }

    void metricCounterBlockComposes() {
        section("04 metric counter block");
        FakeContentHost host;
        TemplateScene scene("el_metric", 30.f, host, 1920.f, 1080.f);
        MetricCounterBlockSpec spec;
        spec.value = "45";
        spec.unit = "$ BILLION";
        spec.label = "REVENUE";
        spec.delta = "12%";
        spec.deltaUp = true;
        LayerHandle& root = addMetricCounterBlock(scene, spec);
        root.position(960.f, 480.f);
        submitsThrough("the metric root submits across the clip", scene, root);
        const FrameSubmission settled = scene.submit(48);
        check(settled.layers.size() == 5, "value, unit, label and delta compose five layers");
    }

    void comparisonDeltaComposes() {
        section("05 comparison delta");
        FakeContentHost host;
        TemplateScene scene("el_delta", 30.f, host, 1920.f, 1080.f);
        ComparisonDeltaSpec spec;
        spec.leftValue = "2.1";
        spec.leftLabel = "BEFORE";
        spec.rightValue = "4.8";
        spec.rightLabel = "AFTER";
        spec.delta = "128%";
        spec.deltaUp = true;
        LayerHandle& root = addComparisonDelta(scene, spec);
        root.position(960.f, 480.f);
        submitsThrough("the delta root submits across the clip", scene, root);
        const auto* divider = host.findShapeRequest("comparison_delta_divider");
        check(divider != nullptr, "the comparison keeps its divider");
    }

    void eventSequenceRailComposes() {
        section("06 event sequence rail");
        FakeContentHost host;
        TemplateScene scene("el_rail", 30.f, host, 1920.f, 1080.f);
        EventSequenceRailSpec spec;
        spec.events = {{"2001", "CAUSE"}, {"2005", "EFFECT"}, {"2008", "AFTERMATH"}};
        LayerHandle& root = addEventSequenceRail(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the rail root submits across the clip", scene, root);
        const FrameSubmission settled = scene.submit(48);
        check(settled.layers.size() == 11, "three chained events compose eleven layers");
    }

}// namespace

int main() {
    theRegistryHoldsThirtyUniqueIds();
    dataTimelineComposes();
    milestoneCardComposes();
    dateRangeBracketComposes();
    metricCounterBlockComposes();
    comparisonDeltaComposes();
    eventSequenceRailComposes();
    return chrononmotion_test::report();
}
