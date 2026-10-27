#include "chronontemplate/charts/ChartsPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>
#include <string>
#include <vector>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {
    ChartDatum point(std::string label, double value, std::string period = {}) {
        ChartDatum d;
        d.label = std::move(label);
        d.period = std::move(period);
        d.value = value;
        return d;
    }

    void eachRecipeCreatesAValidScene() {
        section("all nine Charts recipes create valid scenes");
        const std::vector<ChartSpec> specs = [] {
            std::vector<ChartSpec> all;
            ChartSpec dual; dual.style = ChartStyle::DualComparisonBars; dual.unit = "%";
            dual.scaleMax = 100.; dual.data = {point("Tecnici", 42), point("Controllo", 18)}; all.push_back(dual);
            ChartSpec timeline; timeline.style = ChartStyle::TimelineGrowth; timeline.unit = "M€";
            timeline.data = {point("Ricavi", 18, "2022"), point("Ricavi", 30, "2023"), point("Ricavi", 42, "2024")}; all.push_back(timeline);
            ChartSpec ranked; ranked.style = ChartStyle::RankedBars; ranked.data = {point("Alfa", 40), point("Beta", 25), point("Gamma", 10)}; all.push_back(ranked);
            ChartSpec scenario; scenario.style = ChartStyle::ScenarioSplit;
            auto optimistic = point("Scenario ottimistico", 30, "Ipotesi 2027"); optimistic.qualifier = ChartQualifier::Hypothetical;
            auto prudent = point("Scenario prudente", 18, "Ipotesi 2027"); prudent.qualifier = ChartQualifier::Hypothetical;
            scenario.data = {optimistic, prudent}; scenario.unit = "M€"; all.push_back(scenario);
            ChartSpec range; range.style = ChartStyle::BoundedRangeComparison; range.unit = "M€";
            ChartDatum forecast; forecast.label = "Costo previsto"; forecast.lower = 10.; forecast.upper = 15.; forecast.qualifier = ChartQualifier::Range;
            range.data = {forecast, point("Budget iniziale", 8)}; range.scaleMax = 20.; all.push_back(range);
            ChartSpec qualified; qualified.style = ChartStyle::QualifiedGrowth; qualified.unit = "dipendenti";
            auto approx = point("Dipendenti", 200, "2022"); approx.qualifier = ChartQualifier::Approximate;
            auto more = point("Dipendenti", 350, "2024"); more.qualifier = ChartQualifier::GreaterThan;
            qualified.data = {approx, more}; all.push_back(qualified);
            ChartSpec missing; missing.style = ChartStyle::MissingDataTimeline; missing.unit = "unità";
            auto nd = point("Dato mancante", 0, "2023"); nd.value.reset(); nd.qualifier = ChartQualifier::Missing;
            missing.data = {point("Unità", 100, "2022"), nd, point("Unità", 150, "2024")}; all.push_back(missing);
            ChartSpec segmented; segmented.style = ChartStyle::SegmentedTotalBar; segmented.unit = "richieste"; segmented.total = 200.;
            segmented.data = {point("Approvate", 120), point("Respinte", 80)}; all.push_back(segmented);
            ChartSpec beforeAfter; beforeAfter.style = ChartStyle::BeforeAfterMetric; beforeAfter.unit = "clienti";
            beforeAfter.data = {point("Clienti", 40, "2023"), point("Clienti", 55, "2024")}; all.push_back(beforeAfter);
            return all;
        }();

        for (std::size_t i = 0; i < specs.size(); ++i) {
            FakeContentHost host;
            TemplateScene scene("charts_recipe_" + std::to_string(i), 30.f, host, 1920.f, 1080.f);
            const ChartComposition composition = addChart(scene, specs[i]);
            check(!composition.marks.empty(), "recipe has visual marks");
            check(composition.peakFrame == 80 && composition.endFrame == 120,
                  "recipe uses the standard four-second timing");
            check(scene.validate().empty(), "recipe scene validates");
        }
    }

    void missingDataIsNeverBridgedOrInterpolated() {
        section("missing timeline data stays explicitly absent");
        FakeContentHost host;
        TemplateScene scene("charts_gap", 30.f, host, 1920.f, 1080.f);
        ChartSpec spec;
        spec.style = ChartStyle::MissingDataTimeline;
        spec.data = {point("A", 100, "2022"), ChartDatum{.label = "dato mancante", .period = "2023",
                    .qualifier = ChartQualifier::Missing}, point("B", 150, "2024")};
        const auto out = addChart(scene, spec);
        check(out.values.size() == 3, "the missing period receives an N/D label slot");
        check(out.marks.size() == 3, "no line segment crosses the missing period");
        check(scene.validate().empty(), "the gap scene validates");
    }

    void semanticContradictionsFailClosed() {
        section("Charts rejects semantic contradictions");
        FakeContentHost host;
        TemplateScene percentScene("charts_percent", 30.f, host, 1920.f, 1080.f);
        ChartSpec percent;
        percent.unit = "%";
        percent.data = {point("A", 42), point("B", 18)};
        bool failed = false;
        try { (void)addChart(percentScene, percent); } catch (const std::invalid_argument&) { failed = true; }
        check(failed, "percentage data require an explicit declared scale");

        FakeContentHost gapHost;
        TemplateScene gapScene("charts_gap_invalid", 30.f, gapHost, 1920.f, 1080.f);
        ChartSpec gap;
        gap.style = ChartStyle::MissingDataTimeline;
        gap.data = {point("A", 1, "2022"), point("B", 2, "2023")};
        failed = false;
        try { (void)addChart(gapScene, gap); } catch (const std::invalid_argument&) { failed = true; }
        check(failed, "missing-data timelines require a real missing slot");

        FakeContentHost totalHost;
        TemplateScene totalScene("charts_bad_total", 30.f, totalHost, 1920.f, 1080.f);
        ChartSpec total;
        total.style = ChartStyle::SegmentedTotalBar;
        total.total = 100.;
        total.data = {point("A", 60), point("B", 30)};
        failed = false;
        try { (void)addChart(totalScene, total); } catch (const std::invalid_argument&) { failed = true; }
        check(failed, "segmented components must equal the declared total");
    }
}

int main() {
    eachRecipeCreatesAValidScene();
    missingDataIsNeverBridgedOrInterpolated();
    semanticContradictionsFailClosed();
    return 0;
}
