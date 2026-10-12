#include "chronontemplate/elements/TimelineElements.hpp"

namespace chronontemplate::elements {

    LayerHandle& addDataTimeline(TemplateScene& scene, const DataTimelineSpec& spec) {
        require(!spec.events.empty(), "addDataTimeline: at least one event is required");
        require(spec.spacing > 0.f, "addDataTimeline: spacing must be positive");
        require(spec.activeEvent >= 0 &&
                        spec.activeEvent < static_cast<int>(spec.events.size()),
                "addDataTimeline: activeEvent is outside the event list");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        const float total = spec.spacing * static_cast<float>(spec.events.size() - 1);
        LayerHandle& rail = addBar(scene, root.id(), spec.name + "_rail",
                                   total > 0.f ? total : 8.f, 4.f, 0.f, 0.f, pal.line, 2.f);
        applyElementMotion(rail, spec.motion, scene.fps());
        for (std::size_t i = 0; i < spec.events.size(); ++i) {
            const auto& event = spec.events[i];
            require(!event.date.empty(), "addDataTimeline: every event needs a date");
            const float x = -total * 0.5f + spec.spacing * static_cast<float>(i);
            const bool active = static_cast<int>(i) == spec.activeEvent;
            LayerHandle& dot = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(active ? 26.f : 16.f, active ? 26.f : 16.f),
                    .fillColor = active ? pal.accent : pal.muted,
                    .name = spec.name + "_dot_" + std::to_string(i),
                    .cornerRadius = active ? 13.f : 8.f,
                    .geometry = ShapeGeometry::Ellipse});
            dot.parent(root.id());
            dot.position(x, 0.f);
            dot.alive(0, 150);
            applyElementMotion(dot, spec.motion, scene.fps(), static_cast<int>(i));
            LayerHandle& date = addText(scene, root.id(), spec.name + "_date_" + std::to_string(i),
                                        event.date, active ? 40.f : 30.f,
                                        active ? pal.ink : pal.muted, x, -64.f);
            applyElementMotion(date, spec.motion, scene.fps(), static_cast<int>(i));
            if (!event.label.empty()) {
                LayerHandle& label = addText(scene, root.id(),
                                             spec.name + "_label_" + std::to_string(i),
                                             event.label, 28.f, pal.muted, x, 64.f);
                applyElementMotion(label, spec.motion, scene.fps(), static_cast<int>(i));
            }
        }
        return root;
    }

    LayerHandle& addMilestoneCard(TemplateScene& scene, const MilestoneCardSpec& spec) {
        require(!spec.year.empty(), "addMilestoneCard: a year is required");
        require(!spec.headline.empty(), "addMilestoneCard: a headline is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& accent = addBar(scene, root.id(), spec.name + "_accent",
                                     120.f, 10.f, -260.f, -120.f, spec.accent, 5.f);
        applyElementMotion(accent, spec.motion, scene.fps());
        LayerHandle& year = addText(scene, root.id(), spec.name + "_year",
                                    spec.year, 170.f, pal.ink, 0.f, -40.f);
        applyElementMotion(year, spec.motion, scene.fps(), 1);
        LayerHandle& headline = addText(scene, root.id(), spec.name + "_headline",
                                        spec.headline, 44.f, pal.muted, 0.f, 110.f);
        applyElementMotion(headline, spec.motion, scene.fps(), 2);
        return root;
    }

    LayerHandle& addDateRangeBracket(TemplateScene& scene, const DateRangeBracketSpec& spec) {
        require(!spec.from.empty() && !spec.to.empty(),
                "addDateRangeBracket: both dates are required");
        require(spec.toYear >= spec.fromYear,
                "addDateRangeBracket: the end year must not precede the start year");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& rail = addBar(scene, root.id(), spec.name + "_rail",
                                   560.f, 4.f, 0.f, 0.f, pal.line, 2.f);
        applyElementMotion(rail, spec.motion, scene.fps());
        LayerHandle& tickL = addBar(scene, root.id(), spec.name + "_tick_from",
                                    4.f, 44.f, -280.f, 0.f, pal.accent, 2.f);
        applyElementMotion(tickL, spec.motion, scene.fps(), 1);
        LayerHandle& tickR = addBar(scene, root.id(), spec.name + "_tick_to",
                                    4.f, 44.f, 280.f, 0.f, pal.accent, 2.f);
        applyElementMotion(tickR, spec.motion, scene.fps(), 1);
        LayerHandle& from = addText(scene, root.id(), spec.name + "_from",
                                    spec.from, 40.f, pal.ink, -280.f, -70.f);
        applyElementMotion(from, spec.motion, scene.fps(), 2);
        LayerHandle& to = addText(scene, root.id(), spec.name + "_to",
                                  spec.to, 40.f, pal.ink, 280.f, -70.f);
        applyElementMotion(to, spec.motion, scene.fps(), 2);
        const int span = spec.toYear - spec.fromYear;
        LayerHandle& spanLabel = addText(scene, root.id(), spec.name + "_span",
                                         std::to_string(span) + " YEARS", 32.f,
                                         pal.accent, 0.f, 60.f);
        applyElementMotion(spanLabel, spec.motion, scene.fps(), 3);
        return root;
    }

    LayerHandle& addMetricCounterBlock(TemplateScene& scene, const MetricCounterBlockSpec& spec) {
        require(!spec.value.empty(), "addMetricCounterBlock: a value is required");
        require(!spec.unit.empty(), "addMetricCounterBlock: a unit is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& value = addText(scene, root.id(), spec.name + "_value",
                                     spec.value, 150.f, pal.ink, 0.f, -50.f);
        applyElementMotion(value, spec.motion, scene.fps());
        LayerHandle& unit = addText(scene, root.id(), spec.name + "_unit",
                                    spec.unit, 56.f, pal.accent, 0.f, 60.f);
        applyElementMotion(unit, spec.motion, scene.fps(), 1);
        if (!spec.label.empty()) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_label",
                                         spec.label, 32.f, pal.muted, 0.f, 130.f);
            applyElementMotion(label, spec.motion, scene.fps(), 2);
        }
        if (!spec.delta.empty()) {
            const std::string arrow = spec.deltaUp ? "▲ " : "▼ ";
            const std::string color = spec.deltaUp ? "#3FB950" : "#E03B2F";
            LayerHandle& delta = addText(scene, root.id(), spec.name + "_delta",
                                         arrow + spec.delta, 36.f, color, 0.f, 190.f);
            applyElementMotion(delta, spec.motion, scene.fps(), 3);
        }
        return root;
    }

    LayerHandle& addComparisonDelta(TemplateScene& scene, const ComparisonDeltaSpec& spec) {
        require(!spec.leftValue.empty() && !spec.rightValue.empty(),
                "addComparisonDelta: both values are required");
        require(!spec.delta.empty(), "addComparisonDelta: a delta is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& left = addText(scene, root.id(), spec.name + "_left_value",
                                    spec.leftValue, 110.f, pal.ink, -260.f, -40.f);
        applyElementMotion(left, spec.motion, scene.fps());
        LayerHandle& right = addText(scene, root.id(), spec.name + "_right_value",
                                     spec.rightValue, 110.f, pal.ink, 260.f, -40.f);
        applyElementMotion(right, spec.motion, scene.fps(), 1);
        if (!spec.leftLabel.empty()) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_left_label",
                                         spec.leftLabel, 30.f, pal.muted, -260.f, 70.f);
            applyElementMotion(label, spec.motion, scene.fps(), 2);
        }
        if (!spec.rightLabel.empty()) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_right_label",
                                         spec.rightLabel, 30.f, pal.muted, 260.f, 70.f);
            applyElementMotion(label, spec.motion, scene.fps(), 2);
        }
        const std::string arrow = spec.deltaUp ? "▲ " : "▼ ";
        const std::string color = spec.deltaUp ? "#3FB950" : "#E03B2F";
        LayerHandle& divider = addBar(scene, root.id(), spec.name + "_divider",
                                      4.f, 170.f, 0.f, 0.f, pal.line, 2.f);
        applyElementMotion(divider, spec.motion, scene.fps(), 1);
        LayerHandle& delta = addText(scene, root.id(), spec.name + "_delta",
                                     arrow + spec.delta, 44.f, color, 0.f, 130.f);
        applyElementMotion(delta, spec.motion, scene.fps(), 3);
        return root;
    }

    LayerHandle& addEventSequenceRail(TemplateScene& scene, const EventSequenceRailSpec& spec) {
        require(!spec.events.empty(), "addEventSequenceRail: at least one event is required");
        require(spec.spacing > 0.f, "addEventSequenceRail: spacing must be positive");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        const float total = spec.spacing * static_cast<float>(spec.events.size() - 1);
        LayerHandle& rail = addBar(scene, root.id(), spec.name + "_rail",
                                   4.f, total > 0.f ? total : 8.f, 0.f, 0.f, pal.line, 2.f);
        applyElementMotion(rail, spec.motion, scene.fps());
        for (std::size_t i = 0; i < spec.events.size(); ++i) {
            const auto& event = spec.events[i];
            require(!event.date.empty(), "addEventSequenceRail: every event needs a date");
            const float y = -total * 0.5f + spec.spacing * static_cast<float>(i);
            LayerHandle& dot = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(18.f, 18.f),
                    .fillColor = pal.accent,
                    .name = spec.name + "_dot_" + std::to_string(i),
                    .cornerRadius = 9.f,
                    .geometry = ShapeGeometry::Ellipse});
            dot.parent(root.id());
            dot.position(-190.f, y);
            dot.alive(0, 150);
            applyElementMotion(dot, spec.motion, scene.fps(), static_cast<int>(i));
            LayerHandle& date = addText(scene, root.id(), spec.name + "_date_" + std::to_string(i),
                                        event.date, 34.f, pal.ink, -60.f, y - 8.f);
            applyElementMotion(date, spec.motion, scene.fps(), static_cast<int>(i));
            if (!event.label.empty()) {
                LayerHandle& label = addText(scene, root.id(),
                                             spec.name + "_label_" + std::to_string(i),
                                             event.label, 28.f, pal.muted, -60.f, y + 36.f);
                applyElementMotion(label, spec.motion, scene.fps(), static_cast<int>(i));
            }
        }
        return root;
    }

}// namespace chronontemplate::elements
