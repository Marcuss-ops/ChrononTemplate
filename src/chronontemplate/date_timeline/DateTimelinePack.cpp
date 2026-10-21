#include "chronontemplate/date_timeline/DateTimelinePack.hpp"

#include "chrononmotion/motion/Easing.hpp"

#include <stdexcept>
#include <cstdlib>

namespace chronontemplate::date_timeline {

    namespace {
        constexpr float kRailY = 540.f;
        constexpr float kLeft = 360.f;
        constexpr float kRight = 1560.f;
        constexpr int kRevealFrames = 14;
        const char* kInk = "#262521";
        const char* kMuted = "#77746E";
        const char* kAccent = "#373631";

        void validate(const DateTimelineSpec& spec) {
            if (spec.name.empty() || spec.heading.empty() || spec.font.empty())
                throw std::invalid_argument("addDateTimeline: name, heading and font are required");
            if (spec.width < 1200.f || spec.height < 700.f)
                throw std::invalid_argument("addDateTimeline: canvas must be at least 1200x700");
            if (spec.eventStaggerFrames < 1 || spec.eventHoldFrames < kRevealFrames)
                throw std::invalid_argument("addDateTimeline: invalid event timing");
            if (spec.milestones.size() < 2 || spec.milestones.size() > 10)
                throw std::invalid_argument("addDateTimeline: expected 2..10 milestones");
            for (const auto& event : spec.milestones) {
                if (event.label.empty() || event.dates.empty())
                    throw std::invalid_argument("addDateTimeline: milestones need a label and dates");
                for (const auto& date : event.dates)
                    if (date.empty()) throw std::invalid_argument("addDateTimeline: date must not be empty");
            }
        }

        LayerHandle& text(TemplateScene& scene, MotionLayerId parent, const DateTimelineSpec& spec,
                          const std::string& name, const std::string& value, float size,
                          const std::string& color, float x, float y, int start, int end) {
            LayerHandle& layer = scene.text(TextSpec{.text = value, .font = spec.font,
                .fontSize = size, .color = color, .name = name});
            layer.parent(parent).position(x, y).alive(start, end);
            layer.animateOpacity(start, kRevealFrames, 0.f, 1.f);
            return layer;
        }
    }

    std::vector<DateMilestone> technologyDateSample() {
        return {
            {"BIRTH", {"1948", "1951"}}, {"FIRST STEP", {"1962", "1965"}},
            {"CHANGE", {"1969", "1973"}}, {"SIGNAL", {"1980", "1984"}},
            {"NETWORK", {"1989", "1991"}}, {"LAUNCH", {"1998", "2001"}},
            {"MOBILE", {"2007", "2010"}}, {"CLOUD", {"2012", "2015"}},
            {"AI", {"2017", "2022"}}, {"NOW", {"2025", "2026"}},
        };
    }

    std::vector<TimelineMotionChoice> timelineMotionChoices() {
        return {
            {TimelineMotion::StaggerFade, "stagger_fade", "Stagger Fade"},
            {TimelineMotion::MarkerPop, "marker_pop", "Marker Pop"},
            {TimelineMotion::AlternatingRise, "alternating_rise", "Alternating Rise"},
            {TimelineMotion::SideSlide, "side_slide", "Side Slide"},
            {TimelineMotion::CenterOut, "center_out", "Center Out"},
            {TimelineMotion::TravelingCursor, "traveling_cursor", "Traveling Cursor"},
            {TimelineMotion::SegmentDraw, "segment_draw", "Segment Draw"},
            {TimelineMotion::PairedWave, "paired_wave", "Paired Wave"},
            {TimelineMotion::DatesFirst, "dates_first", "Dates First"},
            {TimelineMotion::SoftCascade, "soft_cascade", "Soft Cascade"},
        };
    }

    int dateTimelineDurationFrames(const DateTimelineSpec& spec) {
        validate(spec);
        return spec.eventHoldFrames + spec.eventStaggerFrames *
            static_cast<int>(spec.milestones.size() - 1);
    }

    LayerHandle& addDateTimeline(TemplateScene& scene, const DateTimelineSpec& spec) {
        validate(spec);
        const int duration = dateTimelineDurationFrames(spec);
        const float cx = spec.width * .5f;
        const float cy = spec.height * .5f;
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, duration);
        const auto parent = root.id();

        LayerHandle& background = scene.shape(ShapeSpec{
            .size = chrononmotion::Vector2(spec.width, spec.height),
            .fillColor = "#F5F3EE", .name = spec.name + "_ground"});
        background.parent(parent).position(cx, cy).alive(0, duration);
        (void)text(scene, parent, spec, spec.name + "_heading", spec.heading,
                   34.f, kInk, cx, 150.f, 0, duration);

        const float left = spec.width * (kLeft / 1920.f);
        const float right = spec.width * (kRight / 1920.f);
        const float span = right - left;
        LayerHandle& rail = scene.shape(ShapeSpec{
            .size = chrononmotion::Vector2(span, 2.f), .fillColor = "#B8B4AC",
            .name = spec.name + "_rail"});
        rail.parent(parent).position(cx, cy).alive(0, duration);
        auto& scaleTrack = rail.layer().tracks.scale;
        scaleTrack.add(0.f, chrononmotion::Vector3(.001f, 1.f, 1.f),
                       chrononmotion::motion::Easing::linear());
        scaleTrack.add(26.f / scene.fps(), chrononmotion::Vector3(1.f, 1.f, 1.f),
                       chrononmotion::motion::Easing::easeOut());

        for (std::size_t i = 0; i < spec.milestones.size(); ++i) {
            const auto& event = spec.milestones[i];
            const float x = left + span * static_cast<float>(i) /
                static_cast<float>(spec.milestones.size() - 1);
            int rank = static_cast<int>(i);
            if (spec.motion == TimelineMotion::CenterOut)
                rank = std::abs(static_cast<int>(i) - static_cast<int>(spec.milestones.size() - 1) / 2);
            else if (spec.motion == TimelineMotion::PairedWave)
                rank = static_cast<int>(i / 2) * 2 + static_cast<int>(i % 2) * 5;
            const int start = rank * spec.eventStaggerFrames;
            const bool upper = i % 2 == 0;
            const float labelY = upper ? 375.f : 705.f;
            const float dateY = labelY + 45.f;
            const float stemEnd = upper ? 470.f : 610.f;
            const float stemHeight = upper ? kRailY - stemEnd : stemEnd - kRailY;
            const int end = duration;

            LayerHandle& stem = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(1.f, stemHeight), .fillColor = "#D1CEC7",
                .name = spec.name + "_stem_" + std::to_string(i)});
            stem.parent(parent).position(x, (kRailY + stemEnd) * .5f).alive(start, end);
            stem.animateOpacity(start, kRevealFrames, 0.f, 1.f);
            if (spec.motion == TimelineMotion::SegmentDraw)
                stem.animatePosition(start, kRevealFrames, chrononmotion::Vector3(0.f, upper ? 10.f : -10.f, 0.f));

            LayerHandle& tick = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(10.f, 10.f), .fillColor = kAccent,
                .name = spec.name + "_tick_" + std::to_string(i), .cornerRadius = 5.f,
                .geometry = ShapeGeometry::Ellipse});
            tick.parent(parent).position(x, kRailY).alive(start, end);
            tick.animateOpacity(start, kRevealFrames, 0.f, 1.f);
            if (spec.motion == TimelineMotion::MarkerPop)
                tick.animate(ScalePop{.inFrame = start, .duration = kRevealFrames, .from = .3f});

            std::string dates;
            for (const auto& date : event.dates) {
                if (!dates.empty()) dates += "  ·  ";
                dates += date;
            }
            const int labelStart = start + (spec.motion == TimelineMotion::DatesFirst ? 7 : 0);
            LayerHandle& label = text(scene, parent, spec, spec.name + "_label_" + std::to_string(i),
                       event.label, 18.f, kMuted, x, labelY, labelStart, end);
            LayerHandle& datesLayer = text(scene, parent, spec, spec.name + "_dates_" + std::to_string(i),
                       dates, 18.f, kInk, x, dateY, start, end);
            if (spec.motion == TimelineMotion::AlternatingRise) {
                const auto offset = upper ? 12.f : -12.f;
                label.animatePosition(start, kRevealFrames, chrononmotion::Vector3(0.f, offset, 0.f));
                datesLayer.animatePosition(start, kRevealFrames, chrononmotion::Vector3(0.f, offset, 0.f));
            } else if (spec.motion == TimelineMotion::SideSlide) {
                const auto offset = i < spec.milestones.size() / 2 ? -18.f : 18.f;
                label.animatePosition(start, kRevealFrames, chrononmotion::Vector3(offset, 0.f, 0.f));
                datesLayer.animatePosition(start, kRevealFrames, chrononmotion::Vector3(offset, 0.f, 0.f));
            } else if (spec.motion == TimelineMotion::SoftCascade) {
                const auto offset = upper ? 7.f : -7.f;
                label.animatePosition(start, kRevealFrames + 8, chrononmotion::Vector3(0.f, offset, 0.f));
                datesLayer.animatePosition(start, kRevealFrames + 8, chrononmotion::Vector3(0.f, offset, 0.f));
            }
        }
        if (spec.motion == TimelineMotion::TravelingCursor) {
            LayerHandle& cursor = scene.shape(ShapeSpec{.size = chrononmotion::Vector2(8.f, 8.f),
                .fillColor = kInk, .name = spec.name + "_cursor", .cornerRadius = 4.f,
                .geometry = ShapeGeometry::Ellipse});
            cursor.parent(parent).position(left, kRailY).alive(0, duration);
            cursor.layer().tracks.position.add(0.f, chrononmotion::Vector3(left, kRailY, 0.f));
            cursor.layer().tracks.position.add(static_cast<float>(duration) / scene.fps(),
                chrononmotion::Vector3(right, kRailY, 0.f), chrononmotion::motion::Easing::easeInOut());
        }
        return root;
    }

} // namespace chronontemplate::date_timeline
