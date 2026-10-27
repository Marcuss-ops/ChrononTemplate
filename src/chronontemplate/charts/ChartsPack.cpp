#include "chronontemplate/charts/ChartsPack.hpp"

#include "chrononmotion/motion/OfflineBaking.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace chronontemplate {
    namespace {
        using chrononmotion::Vector2;
        using chrononmotion::Vector3;
        using chrononmotion::motion::Easing;
        using chrononmotion::motion::Track;

        constexpr int kMaxPoints = 24;

        [[nodiscard]] float sceneY(const TemplateScene& scene, float y) {
            return scene.canvas().y - y;
        }

        [[nodiscard]] bool finite(const std::optional<double>& value) {
            return value && std::isfinite(*value);
        }

        [[nodiscard]] std::string formatValue(double value, int precision = 3) {
            std::ostringstream stream;
            stream << std::fixed << std::setprecision(std::clamp(precision, 0, 6)) << value;
            std::string raw = stream.str();
            const auto decimal = raw.find('.');
            std::string whole = raw.substr(0, decimal);
            std::string fraction = decimal == std::string::npos ? std::string{} : raw.substr(decimal + 1);
            while (!fraction.empty() && fraction.back() == '0') fraction.pop_back();
            const bool negative = !whole.empty() && whole.front() == '-';
            const std::size_t first = negative ? 1u : 0u;
            for (std::size_t pos = whole.size(); pos > first + 3; pos -= 3)
                whole.insert(pos - 3, 1, '.');
            if (!fraction.empty()) whole += ',' + fraction;
            return whole;
        }

        [[nodiscard]] std::string valueText(const ChartDatum& datum, const std::string& fallbackUnit) {
            if (datum.qualifier == ChartQualifier::Missing) return "N/D";
            if (!datum.displayValue.empty()) return datum.displayValue;
            std::string prefix;
            switch (datum.qualifier) {
                case ChartQualifier::Approximate: prefix = "≈ "; break;
                case ChartQualifier::GreaterThan: prefix = "> "; break;
                case ChartQualifier::Forecast: prefix = "PREV. "; break;
                case ChartQualifier::Hypothetical: break;
                case ChartQualifier::Range:
                    return formatValue(*datum.lower) + "–" + formatValue(*datum.upper) +
                           ((datum.unit.empty() ? fallbackUnit : datum.unit).empty()
                                ? std::string{}
                                : " " + (datum.unit.empty() ? fallbackUnit : datum.unit));
                case ChartQualifier::Exact:
                case ChartQualifier::Missing: break;
            }
            std::string result = prefix + formatValue(*datum.value);
            std::string unit = datum.unit.empty() ? fallbackUnit : datum.unit;
            if (unit == "incidenti" && datum.value && *datum.value == 1.0) unit = "incidente";
            if (!unit.empty()) result += (unit == "%" ? "" : " ") + unit;
            return result;
        }

        [[nodiscard]] float fitFont(const std::string& content, float preferred, float maxWidth) {
            const float estimatedWidth = std::max(1.f, static_cast<float>(content.size()) * preferred * 0.56f);
            return std::min(preferred, preferred * maxWidth / estimatedWidth);
        }

        [[nodiscard]] int revealFrame(const ChartSpec& spec, std::size_t index, std::size_t count) {
            if ((spec.style == ChartStyle::DualComparisonBars && !spec.sequentialComparison) || spec.style == ChartStyle::ScenarioSplit)
                return spec.inFrame + 8;
            if (spec.style == ChartStyle::DualComparisonBars && spec.sequentialComparison)
                return spec.inFrame + static_cast<int>(index) * 18;
            if (spec.style == ChartStyle::BeforeAfterMetric || spec.style == ChartStyle::QualifiedGrowth)
                return spec.inFrame + static_cast<int>(index) * std::max(10, spec.duration / 5);
            if (spec.style == ChartStyle::RankedBars)
                return spec.inFrame + static_cast<int>(index) * std::max(8, spec.duration / 12);
            const int revealWindow = std::max(1, spec.duration * 2 / 3);
            const int gap = count <= 1 ? 0 : revealWindow / static_cast<int>(count - 1);
            return spec.inFrame + static_cast<int>(index) * gap;
        }

        [[nodiscard]] Easing calmEase() { return Easing::cubicBezier(0.215f, 0.61f, 0.355f, 1.f); }

        LayerHandle& rect(TemplateScene& scene, ChartComposition& out, const ChartSpec& spec,
                          float x, float y, float w, float h, const std::string& color,
                          const std::string& suffix, int at, bool rounded = false) {
            LayerHandle& layer = scene.shape(ShapeSpec{.size = Vector2(w, h), .fillColor = color,
                                                       .name = spec.name + "_" + suffix,
                                                       .cornerRadius = rounded ? std::min(w, h) * 0.08f : 0.f});
            layer.position(x, sceneY(scene, y), 0.f).alive(spec.inFrame, out.endFrame - 1);
            layer.animateOpacity(at, std::max(1, std::min(12, out.peakFrame - at)), 0.f, 1.f, Easing::easeOut());
            out.marks.push_back(&layer);
            return layer;
        }

        LayerHandle& text(TemplateScene& scene, ChartComposition& out, const ChartSpec& spec,
                          const std::string& content, float x, float y, float size,
                          const std::string& color, const std::string& suffix, int at) {
            LayerHandle& layer = scene.text(TextSpec{.text = content, .font = spec.font, .fontSize = size,
                                                      .color = color, .name = spec.name + "_" + suffix});
            layer.position(x, sceneY(scene, y), 0.f).alive(spec.inFrame, out.endFrame - 1);
            layer.animateOpacity(at, std::max(1, std::min(12, out.peakFrame - at)), 0.f, 1.f, Easing::easeOut());
            out.labels.push_back(&layer);
            return layer;
        }

        void growX(LayerHandle& layer, const ChartSpec& spec, float fps, float canvasHeight, int at, int duration,
                   float leftEdge, float centerY, float width) {
            Track<Vector3>& scale = layer.layer().tracks.scale;
            scale.add(chrononmotion::motion::frameToTime(at, fps), Vector3(0.001f, 1.f, 1.f), calmEase());
            scale.add(chrononmotion::motion::frameToTime(at + std::max(1, duration), fps),
                      Vector3(1.f, 1.f, 1.f), calmEase());
            Track<Vector3>& position = layer.layer().tracks.position;
            position.add(chrononmotion::motion::frameToTime(at, fps),
                         Vector3(leftEdge + width * 0.0005f, canvasHeight - centerY, 0.f), calmEase());
            position.add(chrononmotion::motion::frameToTime(at + std::max(1, duration), fps),
                         Vector3(leftEdge + width * 0.5f, canvasHeight - centerY, 0.f), calmEase());
            (void)spec;
        }

        void validate(const ChartSpec& spec) {
            if (spec.data.empty() || spec.data.size() > kMaxPoints)
                throw std::invalid_argument("addChart: expected between 1 and 24 data points");
            if (spec.duration < 12 || spec.inFrame < 0)
                throw std::invalid_argument("addChart: duration must be >= 12 and inFrame non-negative");
            if (spec.scaleMin && !std::isfinite(*spec.scaleMin))
                throw std::invalid_argument("addChart: scaleMin must be finite");
            if (spec.scaleMax && (!std::isfinite(*spec.scaleMax) ||
                                  (spec.scaleMin && *spec.scaleMax <= *spec.scaleMin)))
                throw std::invalid_argument("addChart: scaleMax must exceed scaleMin");
            if ((spec.unit == "%" || std::any_of(spec.data.begin(), spec.data.end(),
                    [](const ChartDatum& d) { return d.unit == "%"; })) && !spec.scaleMax)
                throw std::invalid_argument("addChart: percentage charts require an explicit scaleMax (normally 100)");
            for (const ChartDatum& d : spec.data) {
                if (d.label.empty() && d.qualifier != ChartQualifier::Missing)
                    throw std::invalid_argument("addChart: every observation needs a label");
                if (d.qualifier == ChartQualifier::Missing) {
                    if (d.value || d.lower || d.upper)
                        throw std::invalid_argument("addChart: missing observations cannot carry values");
                } else if (d.qualifier == ChartQualifier::Range) {
                    if (!finite(d.lower) || !finite(d.upper) || *d.lower < 0.0 || *d.upper < *d.lower || d.value)
                        throw std::invalid_argument("addChart: ranges need finite non-negative lower/upper bounds only");
                } else if (!finite(d.value) || *d.value < 0.0 || d.lower || d.upper) {
                    throw std::invalid_argument("addChart: observations need one finite non-negative value");
                }
            }
            if (spec.scaleMin || spec.scaleMax) {
                const double lo = spec.scaleMin.value_or(0.0);
                const double hi = spec.scaleMax.value_or(std::numeric_limits<double>::infinity());
                for (const ChartDatum& d : spec.data) {
                    if (finite(d.value) && (*d.value < lo || *d.value > hi))
                        throw std::invalid_argument("addChart: an observation falls outside the declared scale");
                    if (finite(d.lower) && (*d.lower < lo || *d.lower > hi || *d.upper > hi))
                        throw std::invalid_argument("addChart: a range falls outside the declared scale");
                }
            }

            const auto count = spec.data.size();
            switch (spec.style) {
                case ChartStyle::DualComparisonBars:
                case ChartStyle::QualifiedGrowth:
                case ChartStyle::BeforeAfterMetric:
                case ChartStyle::BoundedRangeComparison:
                    if (count != 2) throw std::invalid_argument("addChart: this recipe requires exactly two observations");
                    break;
                case ChartStyle::ScenarioSplit:
                case ChartStyle::MissingDataTimeline:
                    if (count < 2 || count > 3) throw std::invalid_argument("addChart: this recipe requires two or three observations");
                    break;
                case ChartStyle::SegmentedTotalBar:
                    if (count < 2 || !finite(spec.total) || *spec.total <= 0.0)
                        throw std::invalid_argument("addChart: segmented totals require at least two segments and a positive total");
                    break;
                case ChartStyle::TimelineGrowth:
                case ChartStyle::RankedBars:
                    if (count < 2) throw std::invalid_argument("addChart: this recipe requires at least two observations");
                    break;
            }
            if (spec.style == ChartStyle::BoundedRangeComparison &&
                spec.data[0].qualifier != ChartQualifier::Range)
                throw std::invalid_argument("addChart: the first bounded-range observation must be a range");
            if (spec.style == ChartStyle::ScenarioSplit &&
                std::any_of(spec.data.begin(), spec.data.end(), [](const ChartDatum& d) {
                    return d.qualifier != ChartQualifier::Hypothetical;
                }))
                throw std::invalid_argument("addChart: scenario values must be marked hypothetical");
            if (spec.style == ChartStyle::QualifiedGrowth &&
                std::none_of(spec.data.begin(), spec.data.end(), [](const ChartDatum& d) {
                    return d.qualifier == ChartQualifier::Approximate || d.qualifier == ChartQualifier::GreaterThan;
                }))
                throw std::invalid_argument("addChart: qualified growth needs an approximate or open-ended value");
            if (spec.style == ChartStyle::MissingDataTimeline &&
                std::none_of(spec.data.begin(), spec.data.end(), [](const ChartDatum& d) {
                    return d.qualifier == ChartQualifier::Missing;
                }))
                throw std::invalid_argument("addChart: missing-data timeline requires an explicit missing point");
            if (spec.style == ChartStyle::SegmentedTotalBar) {
                double sum = 0.0;
                for (const auto& d : spec.data) {
                    if (!finite(d.value) || d.qualifier != ChartQualifier::Exact)
                        throw std::invalid_argument("addChart: all segments must be exact values");
                    sum += *d.value;
                }
                if (std::abs(sum - *spec.total) > std::max(1e-7, *spec.total * 1e-6))
                    throw std::invalid_argument("addChart: segment values must sum to the declared total");
            }
        }
    } // namespace

    ChartComposition addChart(TemplateScene& scene, const ChartSpec& spec) {
        validate(spec);
        const Vector2 canvas = scene.canvas();
        if (!(canvas.x > 0.f && canvas.y > 0.f) || !(scene.fps() > 0.f))
            throw std::invalid_argument("addChart: scene canvas and frame rate must be positive");

        ChartComposition out;
        out.inFrame = spec.inFrame;
        out.endFrame = spec.inFrame + spec.duration;
        out.peakFrame = spec.inFrame + spec.duration * 2 / 3;
        const int count = static_cast<int>(spec.data.size());
        const float fps = scene.fps();
        const float font = canvas.y / 24.f;
        const float big = canvas.y / 9.5f;
        const float left = canvas.x * 0.16f;
        const float right = canvas.x * 0.90f;
        const float width = right - left;
        const float top = canvas.y * 0.28f;
        const float bottom = canvas.y * 0.74f;

        LayerHandle& background = scene.shape(ShapeSpec{.size = canvas * 1.15f, .fillColor = spec.canvas,
                                                        .name = spec.name + "_background"});
        background.position(canvas.x * 0.5f, canvas.y * 0.5f, 0.f).alive(spec.inFrame, out.endFrame - 1);
        out.marks.push_back(&background);

        if (!spec.title.empty()) {
            out.title = &text(scene, out, spec, spec.title, canvas.x * 0.5f, canvas.y * 0.12f,
                              font * 1.24f, spec.ink, "title", spec.inFrame);
        }

        // A shared value-to-position policy makes scales explicit and identical
        // across observations. Missing points never enter a scale or a path.
        double dataMax = 0.0;
        for (const auto& d : spec.data) {
            if (finite(d.value)) dataMax = std::max(dataMax, *d.value);
            if (finite(d.upper)) dataMax = std::max(dataMax, *d.upper);
        }
        const double minValue = spec.scaleMin.value_or(0.0);
        const double maxValue = spec.scaleMax.value_or(dataMax > minValue ? dataMax : minValue + 1.0);
        if (!(maxValue > minValue)) throw std::invalid_argument("addChart: data need a non-degenerate explicit scale");
        const auto unit = [&](const ChartDatum& d) -> const std::string& {
            return d.unit.empty() ? spec.unit : d.unit;
        };
        const auto normalized = [&](double value) {
            return std::clamp((value - minValue) / (maxValue - minValue), 0.0, 1.0);
        };
        const auto reveal = [&](int i) { return revealFrame(spec, static_cast<std::size_t>(i), spec.data.size()); };

        switch (spec.style) {
            case ChartStyle::DualComparisonBars:
            case ChartStyle::RankedBars: {
                if (spec.style == ChartStyle::RankedBars) {
                    for (int i = 1; i < count; ++i)
                        if (*spec.data[static_cast<std::size_t>(i - 1)].value <
                            *spec.data[static_cast<std::size_t>(i)].value)
                            throw std::invalid_argument("addChart: ranked-bar data must be ordered from greatest to least");
                }
                if (spec.style == ChartStyle::DualComparisonBars && spec.comparisonCards) {
                    const float cardW = width * 0.43f;
                    const float cardH = canvas.y * 0.43f;
                    const float cy = (top + bottom) * 0.5f;
                    for (int i = 0; i < count; ++i) {
                        const auto& d = spec.data[static_cast<std::size_t>(i)];
                        const float cx = i == 0 ? canvas.x * 0.28f : canvas.x * 0.72f;
                        rect(scene, out, spec, cx, cy, cardW, cardH,
                             i == 0 ? spec.primary : spec.secondary,
                             "comparison_card_" + std::to_string(i), reveal(i), true);
                        text(scene, out, spec, d.label, cx, cy - cardH * 0.29f,
                             fitFont(d.label, font * 1.08f, cardW * 0.84f), spec.canvas,
                             "comparison_label_" + std::to_string(i), reveal(i));
                        const std::string display = valueText(d, unit(d));
                        LayerHandle& value = text(scene, out, spec, display, cx, cy + font * 0.28f,
                                                   fitFont(display, big * 1.15f, cardW * 0.86f), spec.canvas,
                                                   "comparison_value_" + std::to_string(i), reveal(i));
                        out.values.push_back(&value);
                    }
                    if (!spec.comparisonCallout.empty())
                        text(scene, out, spec, spec.comparisonCallout, canvas.x * 0.5f,
                             bottom + font * 1.22f, font * 1.25f, spec.qualified,
                             "comparison_callout", out.peakFrame);
                    break;
                }
                const float rowGap = (bottom - top) / static_cast<float>(count);
                const float barH = std::min(canvas.y * 0.13f, rowGap * 0.50f);
                for (int i = 0; i < count; ++i) {
                    const auto& d = spec.data[static_cast<std::size_t>(i)];
                    const float y = top + rowGap * (static_cast<float>(i) + 0.5f);
                    text(scene, out, spec, d.label, left - font * 0.55f, y + barH * 0.92f, font * 1.05f,
                         spec.ink, "category_" + std::to_string(i), reveal(i));
                    const float w = width * static_cast<float>(normalized(*d.value));
                    LayerHandle& bar = rect(scene, out, spec, left + w * 0.5f, y, std::max(1.f, w), barH,
                                             i == 0 ? spec.primary : spec.secondary,
                                             "bar_" + std::to_string(i), reveal(i), true);
                    growX(bar, spec, fps, canvas.y, reveal(i), std::max(1, out.peakFrame - reveal(i)),
                          left, y, std::max(1.f, w));
                    const float marker = w == 0.f ? left + canvas.y * 0.012f : left + w;
                    const std::string display = valueText(d, unit(d));
                    float valueX = marker + font * 0.75f;
                    float valueY = y + barH * 0.92f;
                    std::string valueColor = spec.ink;
                    const float estimatedHalfWidth = static_cast<float>(display.size()) * font * 1.2f * 0.28f;
                    if (valueX + estimatedHalfWidth > canvas.x * 0.95f) {
                        valueX = marker - estimatedHalfWidth - font * 0.20f;
                        valueY = y;
                        valueColor = spec.canvas;
                    }
                    LayerHandle& value = text(scene, out, spec, display, valueX,
                                               valueY, font * 1.2f, valueColor,
                                               "value_" + std::to_string(i), reveal(i));
                    out.values.push_back(&value);
                }
                if (spec.style == ChartStyle::DualComparisonBars && !spec.comparisonCallout.empty())
                    text(scene, out, spec, spec.comparisonCallout, canvas.x * 0.5f,
                         bottom + font * 1.25f, font * 1.2f, spec.qualified, "comparison_callout", out.peakFrame);
                break;
            }
            case ChartStyle::TimelineGrowth:
            case ChartStyle::MissingDataTimeline: {
                const float dx = count > 1 ? width / static_cast<float>(count - 1) : 0.f;
                const float dot = std::max(10.f, canvas.y * 0.018f);
                const int tickCount = spec.unit == "incidenti" ? 3 : 2;
                for (int tick = 0; tick <= tickCount; ++tick) {
                    const double value = minValue + (maxValue - minValue) * static_cast<double>(tick) / tickCount;
                    const float y = bottom - static_cast<float>(tick) * (bottom - top) / tickCount;
                    rect(scene, out, spec, (left + right) * 0.5f, y, width, 2.f, "#DCE2EA",
                         "grid_" + std::to_string(tick), spec.inFrame, false);
                    const std::string tickUnit = spec.unit == "incidenti" && value == 1.0 ? "incidente" : spec.unit;
                    const std::string tickLabel = formatValue(value) + (tickUnit.empty() ? "" : " " + tickUnit);
                    text(scene, out, spec, tickLabel, left - font * 1.6f, y + font * 0.15f,
                         font * 0.68f, spec.secondary, "scale_" + std::to_string(tick), spec.inFrame);
                }
                float previousX = 0.f, previousY = 0.f;
                bool hasPrevious = false;
                for (int i = 0; i < count; ++i) {
                    const auto& d = spec.data[static_cast<std::size_t>(i)];
                    const float x = left + dx * static_cast<float>(i);
                    const bool missing = d.qualifier == ChartQualifier::Missing;
                    const float y = missing ? (top + bottom) * 0.5f
                                            : bottom - static_cast<float>(normalized(*d.value)) * (bottom - top);
                    if (!missing && hasPrevious && !spec.timelineBars) {
                        const float x0 = previousX, y0 = previousY;
                        const float w = x - x0, h = std::max(5.f, canvas.y * 0.008f);
                        const float len = std::hypot(w, y - y0);
                        const float angle = std::atan2(y - y0, w);
                        // The line is an axis-aligned thin plate only when values
                        // share a level; avoid rotated geometry in this primitive.
                        if (std::abs(y - y0) < h) {
                            LayerHandle& segment = rect(scene, out, spec, (x0 + x) * 0.5f, (y0 + y) * 0.5f,
                                                         len, h, spec.primary, "segment_" + std::to_string(i),
                                                         reveal(i), true);
                            growX(segment, spec, fps, canvas.y, reveal(i), std::max(1, out.peakFrame - reveal(i)),
                                  x0, y0, len);
                        } else {
                            // A path layer is used for diagonal segments so the
                            // timeline never quantizes a real observation into a step.
                            LayerHandle& segment = scene.shape(ShapeSpec{
                                    .size = Vector2(std::max(1.f, len), h), .fillColor = spec.primary,
                                    .name = spec.name + "_segment_" + std::to_string(i)});
                            segment.position((x0 + x) * 0.5f, sceneY(scene, (y0 + y) * 0.5f), 0.f)
                                    .alive(spec.inFrame, out.endFrame - 1);
                            segment.layer().tracks.rotation.add(
                                chrononmotion::motion::frameToTime(reveal(i), fps),
                                chrononmotion::Vector3(0.f, 0.f, -angle), Easing::linear());
                            segment.animateOpacity(reveal(i), std::max(1, std::min(10, out.peakFrame - reveal(i))),
                                                   0.f, 1.f, Easing::easeOut());
                            out.marks.push_back(&segment);
                        }
                    }
                    if (!missing) {
                        if (spec.timelineBars && *d.value > 0.0) {
                            const float stemH = bottom - y;
                            rect(scene, out, spec, x, (bottom + y) * 0.5f, canvas.y * 0.055f, stemH,
                                 i == count - 1 ? spec.qualified : spec.primary,
                                 "stem_" + std::to_string(i), reveal(i), true);
                        }
                        LayerHandle& point = rect(scene, out, spec, x, y, dot * 2.f, dot * 2.f,
                                                  i == count - 1 ? spec.qualified : spec.primary,
                                                  "point_" + std::to_string(i), reveal(i), true);
                        point.animate(ScalePop{.inFrame = reveal(i), .duration = std::max(1, out.peakFrame - reveal(i)),
                                               .from = 0.1f, .to = 1.f});
                        previousX = x; previousY = y; hasPrevious = true;
                    } else {
                        hasPrevious = false; // no interpolation across an unknown period
                    }
                    text(scene, out, spec, d.period.empty() ? d.label : d.period, x, bottom + font * 1.45f,
                         font * 1.0f, spec.ink, "period_" + std::to_string(i), reveal(i));
                    const std::string display = missing ? "DATO NON DISPONIBILE" : valueText(d, unit(d));
                    LayerHandle& value = text(scene, out, spec, display, x, y - font * 1.25f, font * 1.12f,
                                               missing ? spec.qualified : spec.ink,
                                               "value_" + std::to_string(i), reveal(i));
                    out.values.push_back(&value);
                }
                break;
            }
            case ChartStyle::ScenarioSplit:
            case ChartStyle::QualifiedGrowth:
            case ChartStyle::BeforeAfterMetric: {
                if (spec.style == ChartStyle::BeforeAfterMetric) {
                    const float centerY = (top + bottom) * 0.48f;
                    const float colX[2] = {canvas.x * 0.30f, canvas.x * 0.70f};
                    for (int i = 0; i < 2; ++i) {
                        const auto& d = spec.data[static_cast<std::size_t>(i)];
                        const std::string period = d.period.empty() ? d.label : d.period;
                        text(scene, out, spec, period, colX[i], centerY - font * 2.25f, font * 1.2f,
                             spec.secondary, "period_" + std::to_string(i), reveal(i));
                        const std::string display = valueText(d, unit(d));
                        LayerHandle& v = text(scene, out, spec, display, colX[i], centerY + font * 0.1f,
                                               fitFont(display, big * 1.25f, canvas.x * 0.34f), spec.ink,
                                               "value_" + std::to_string(i), reveal(i));
                        out.values.push_back(&v);
                    }
                    text(scene, out, spec, "→", canvas.x * 0.5f, centerY, big * 0.7f,
                         spec.qualified, "before_after_arrow", out.peakFrame / 2);
                    if (spec.showDerivedChange) {
                        const double a = *spec.data[0].value, b = *spec.data[1].value;
                        if (a != 0.0 && unit(spec.data[0]) == unit(spec.data[1]) &&
                            spec.data[0].qualifier == ChartQualifier::Exact && spec.data[1].qualifier == ChartQualifier::Exact) {
                            const double change = (b - a) / std::abs(a) * 100.0;
                            const std::string label = (change >= 0.0 ? "+" : "−") + formatValue(std::abs(change), 2) + "% · DERIVATO";
                            out.derivedValue = &text(scene, out, spec, label, canvas.x * 0.5f, bottom + font * 1.35f,
                                                     font * 1.1f, spec.qualified, "derived_change", out.peakFrame);
                        }
                    }
                    break;
                }
                const float cardW = width * 0.46f;
                const float cardH = canvas.y * 0.43f;
                for (int i = 0; i < 2; ++i) {
                    const auto& d = spec.data[static_cast<std::size_t>(i)];
                    const float cx = i == 0 ? canvas.x * 0.28f : canvas.x * 0.72f;
                    const float cy = (top + bottom) * 0.5f;
                    LayerHandle& card = rect(scene, out, spec, cx, cy, cardW, cardH,
                                              i == 0 ? spec.primary : spec.secondary,
                                              "card_" + std::to_string(i), reveal(i), true);
                    (void)card;
                    if (spec.style == ChartStyle::ScenarioSplit) {
                        text(scene, out, spec, d.label, cx, cy - cardH * 0.36f,
                             fitFont(d.label, font * 0.9f, cardW * 0.84f), spec.canvas,
                             "scenario_" + std::to_string(i), reveal(i));
                        if (!d.period.empty())
                            text(scene, out, spec, d.period, cx, cy - cardH * 0.23f,
                                 fitFont(d.period, font * 0.8f, cardW * 0.84f), spec.canvas,
                                 "period_" + std::to_string(i), reveal(i));
                    } else {
                        text(scene, out, spec, d.period.empty() ? d.label : d.period, cx, cy - cardH * 0.24f,
                             fitFont(d.period.empty() ? d.label : d.period, font, cardW * 0.84f),
                             spec.canvas, "period_" + std::to_string(i), reveal(i));
                    }
                    const std::string display = valueText(d, unit(d));
                    LayerHandle& v = text(scene, out, spec, display, cx, cy + font * 0.55f,
                                           fitFont(display, big, cardW * 0.86f), spec.canvas,
                                           "value_" + std::to_string(i), reveal(i));
                    out.values.push_back(&v);
                }
                if (spec.style == ChartStyle::QualifiedGrowth) {
                    text(scene, out, spec, "→", canvas.x * 0.5f, (top + bottom) * 0.5f,
                         big * 0.72f, spec.qualified, "growth_direction", out.peakFrame);
                }
                if (spec.style == ChartStyle::BeforeAfterMetric && spec.showDerivedChange) {
                    const double a = *spec.data[0].value, b = *spec.data[1].value;
                    if (a != 0.0 && unit(spec.data[0]) == unit(spec.data[1]) &&
                        spec.data[0].qualifier == ChartQualifier::Exact &&
                        spec.data[1].qualifier == ChartQualifier::Exact) {
                        const double change = (b - a) / std::abs(a) * 100.0;
                        const std::string label = (change >= 0.0 ? "+" : "−") +
                                                  formatValue(std::abs(change), 2) + "% · DERIVATO";
                        out.derivedValue = &text(scene, out, spec, label, canvas.x * 0.5f, bottom + font * 2.f,
                                                 font, spec.qualified, "derived_change", out.peakFrame);
                    }
                }
                break;
            }
            case ChartStyle::BoundedRangeComparison: {
                const auto& range = spec.data[0];
                const auto& point = spec.data[1];
                const double scaleLo = spec.scaleMin.value_or(0.0);
                const double scaleHi = spec.scaleMax.value_or(std::max(*range.upper, *point.value));
                if (!(scaleHi > scaleLo)) throw std::invalid_argument("addChart: range scale is degenerate");
                const float axisY = (top + bottom) * 0.5f;
                const float axisH = canvas.y * 0.095f;
                const float scaleY = bottom + font * 0.3f;
                rect(scene, out, spec, (left + right) * 0.5f, scaleY, width, 3.f, "#AEB8C7",
                     "shared_scale_axis", reveal(0), false);
                for (int tick = 0; tick <= 2; ++tick) {
                    const double value = scaleLo + (scaleHi - scaleLo) * static_cast<double>(tick) / 2.0;
                    const float x = left + width * static_cast<float>(tick) * 0.5f;
                    rect(scene, out, spec, x, scaleY, 3.f, font * 0.36f, "#AEB8C7",
                         "shared_scale_tick_" + std::to_string(tick), reveal(0), false);
                    text(scene, out, spec, formatValue(value) + " " + unit(range), x,
                         scaleY + font * 0.95f, font * 0.72f, spec.secondary,
                         "shared_scale_label_" + std::to_string(tick), reveal(0));
                }
                const float rangeStart = left + width * static_cast<float>(((*range.lower - scaleLo) / (scaleHi - scaleLo)));
                const float rangeEnd = left + width * static_cast<float>(((*range.upper - scaleLo) / (scaleHi - scaleLo)));
                const float budgetX = left + width * static_cast<float>(((*point.value - scaleLo) / (scaleHi - scaleLo)));
                rect(scene, out, spec, (rangeStart + rangeEnd) * 0.5f, axisY, std::max(1.f, rangeEnd - rangeStart),
                     axisH, spec.qualified, "range_band", reveal(0), true);
                rect(scene, out, spec, budgetX, axisY, canvas.y * 0.012f, axisH * 2.1f, spec.primary,
                     "budget_marker", reveal(1), true);
                text(scene, out, spec, range.label + ": " + valueText(range, unit(range)), (rangeStart + rangeEnd) * 0.5f,
                     axisY - font * 1.8f, font, spec.ink, "range_label", reveal(0));
                text(scene, out, spec, point.label + ": " + valueText(point, unit(point)), budgetX, axisY + font * 3.5f,
                     font, spec.ink, "budget_label", reveal(1));
                break;
            }
            case ChartStyle::SegmentedTotalBar: {
                const float barY = (top + bottom) * 0.5f;
                const float h = canvas.y * 0.19f;
                float cursor = left;
                for (int i = 0; i < count; ++i) {
                    const auto& d = spec.data[static_cast<std::size_t>(i)];
                    const float w = width * static_cast<float>(*d.value / *spec.total);
                    LayerHandle& segment = rect(scene, out, spec, cursor + w * 0.5f, barY, w, h,
                                                 i == 0 ? spec.primary : spec.secondary,
                                                 "segment_" + std::to_string(i), reveal(i), true);
                    growX(segment, spec, fps, canvas.y, reveal(i), std::max(1, out.peakFrame - reveal(i)),
                          cursor, barY, w);
                    const double share = *d.value / *spec.total * 100.0;
                    const std::string segmentText = formatValue(*d.value) + " · " + d.label + " · " +
                                                    formatValue(share) + "%";
                    text(scene, out, spec, segmentText, cursor + w * 0.5f, barY, font * 0.95f,
                         spec.canvas, "segment_value_" + std::to_string(i), reveal(i));
                    cursor += w;
                }
                break;
            }
        }
        if (!spec.note.empty())
            text(scene, out, spec, spec.note, canvas.x * 0.5f, canvas.y * 0.9f,
                 fitFont(spec.note, font * 0.9f, canvas.x * 0.82f),
                 spec.secondary, "method_note", out.peakFrame);
        return out;
    }
} // namespace chronontemplate
