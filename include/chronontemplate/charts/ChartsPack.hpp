#ifndef CHRONONTEMPLATE_CHARTS_CHARTS_PACK_HPP
#define CHRONONTEMPLATE_CHARTS_CHARTS_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <optional>
#include <string>
#include <vector>

namespace chronontemplate {

    /// The visual recipe requested by a validated upstream chart decision.
    enum class ChartStyle {
        DualComparisonBars,
        TimelineGrowth,
        RankedBars,
        ScenarioSplit,
        BoundedRangeComparison,
        QualifiedGrowth,
        MissingDataTimeline,
        SegmentedTotalBar,
        BeforeAfterMetric
    };

    /// Qualifiers stay attached to each observation through layout and labels.
    enum class ChartQualifier { Exact, Approximate, GreaterThan, Forecast, Hypothetical, Range, Missing };

    struct ChartDatum {
        std::string label{};
        std::string period{};
        std::string unit{};               ///< Optional per-observation override.
        std::optional<double> value{};
        std::optional<double> lower{};    ///< Used by Range.
        std::optional<double> upper{};    ///< Used by Range.
        ChartQualifier qualifier{ChartQualifier::Exact};
        std::string displayValue{};       ///< Optional source-faithful spelling (e.g. "≈ 200").
        std::string source{};
    };

    struct ChartSpec {
        ChartStyle style{ChartStyle::DualComparisonBars};
        std::string title{};
        std::string note{};              ///< Optional source-faithful method note shown below the chart.
        std::string unit{};
        std::vector<ChartDatum> data{};
        std::optional<double> scaleMin{};
        std::optional<double> scaleMax{};
        std::optional<double> total{};    ///< Required for SegmentedTotalBar.
        bool showDerivedChange{true};
        bool comparisonCards{false};
        bool timelineBars{false};
        bool sequentialComparison{false};
        std::string comparisonCallout{};
        int inFrame{0};
        int duration{120};
        std::string ink{"#18212B"};
        std::string primary{"#3659D9"};
        std::string secondary{"#59687D"};
        std::string qualified{"#E18B42"};
        std::string canvas{"#F7F8FA"};
        std::string font{"assets/fonts/Inter-SemiBold.ttf"};
        std::string name{"charts"};
    };

    struct ChartComposition {
        std::vector<LayerHandle*> marks{};
        std::vector<LayerHandle*> labels{};
        std::vector<LayerHandle*> values{};
        LayerHandle* title{nullptr};
        LayerHandle* derivedValue{nullptr};
        int inFrame{0};
        int peakFrame{0};
        int endFrame{0};
    };

    /// Compose one of the nine Charts recipes from semantically qualified data.
    /// BrainRust owns eligibility and normalization decisions; this API validates
    /// the shape-specific contract and never infers missing or exact values.
    [[nodiscard]] ChartComposition addChart(TemplateScene& scene, const ChartSpec& spec);

} // namespace chronontemplate

#endif
