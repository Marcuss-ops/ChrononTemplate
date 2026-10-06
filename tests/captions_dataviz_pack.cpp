#include "chronontemplate/captions_dataviz/CaptionsDataVizPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include "chrononmotion/motion/OfflineBaking.hpp"

#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    /// The analysis settings that fit the motion core's offline DFT budget for
    /// these fixtures: the budget is window² × windows ≤ 100M operations, so a
    /// 256-point window (65k ops each) keeps even a 4-second buffer well inside
    /// it, with a hop that still resolves the burst schedule.
    AudioAnalysisSettings testSettings() {
        AudioAnalysisSettings settings;
        settings.windowSize = 256;
        settings.hopSize = 128;
        return settings;
    }

    /// A deterministic synthetic "voiceover": 220 Hz tone bursts with hard
    /// gates. The analyzer's onset is the rms crossing the silence threshold
    /// upward with a rise over `onsetThreshold`, so gated bursts are what fires
    /// it — one onset per burst, on a schedule the test can pin.
    std::vector<float> syntheticVoiceover(std::uint32_t sampleRate, float seconds) {
        const std::size_t count = static_cast<std::size_t>(static_cast<float>(sampleRate) * seconds);
        std::vector<float> samples(count, 0.f);
        const float burstPeriod = 0.8f;
        const float burstLength = 0.25f;
        for (std::size_t i = 0; i < count; ++i) {
            const float t = static_cast<float>(i) / static_cast<float>(sampleRate);
            const float phase = std::fmod(t, burstPeriod);
            if (phase < burstLength) {
                samples[i] = 0.5f * std::sin(2.f * 3.14159265f * 220.f * t);
            }
        }
        return samples;
    }

    void theBeatGridIsDeterministicAndGapped() {
        section("the beat grid is deterministic and respects the gap");
        const std::vector<float> pcm = syntheticVoiceover(48000, 4.f);
        const AudioAnalysisSettings settings = testSettings();

        const BeatGrid grid = buildBeatGrid(pcm, settings, 30.f, 0, 120);
        check(!grid.frames.empty(), "the synthetic track produces onsets");
        check(grid.frames.front() >= 0 && grid.frames.back() < 120,
              "every beat lands inside the requested window");
        for (std::size_t i = 1; i < grid.frames.size(); ++i) {
            check(grid.frames[i] - grid.frames[i - 1] > settings.minGapFrames,
                  "two beats are never closer than the declared gap");
        }

        const BeatGrid again = buildBeatGrid(pcm, settings, 30.f, 0, 120);
        check(again.frames == grid.frames, "the same samples always produce the same grid");

        bool threw = false;
        try {
            (void) buildBeatGrid({}, settings, 30.f, 0, 120);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "an empty PCM buffer is rejected");

        AudioAnalysisSettings broken = settings;
        broken.sampleRate = 0;
        threw = false;
        try {
            (void) buildBeatGrid(pcm, broken, 30.f, 0, 120);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a zero sample rate is rejected");
    }

    void captionsLineUpOnePerBeat() {
        section("captions author one band + one caption per beat");
        const std::vector<float> pcm = syntheticVoiceover(48000, 4.f);
        const BeatGrid grid = buildBeatGrid(pcm, testSettings(), 30.f, 0, 120);

        FakeContentHost host;
        TemplateScene scene("captions", 30.f, host, 1920.f, 1080.f);
        const std::vector<std::string> lines(grid.frames.size(), "ciao");
        const CaptionTrack track = addCaptionTrack(scene, grid, lines);

        check(track.captions.size() == grid.frames.size(),
              "one caption layer per beat");
        check(track.bands.size() == grid.frames.size(), "one band per beat");
        check(scene.validate().empty(), "the caption scene validates");

        // Every band is visible inside its own interval and gated off outside it
        // (the bridge binds hidden layers too; visibility is the alive signal).
        for (std::size_t i = 0; i < track.bands.size(); ++i) {
            const int start = grid.frames[i];
            const int stop = (i + 1 < grid.frames.size()) ? grid.frames[i + 1] : grid.endFrame;
            const FrameSubmission inside = scene.submit(start);
            const FrameSubmission outside = scene.submit(stop);
            const BoundLayer* inBand = findLayer(inside, track.bands[i]->id());
            const BoundLayer* outBand = findLayer(outside, track.bands[i]->id());
            check(inBand != nullptr && inBand->transform.visible,
                  "each band is alive on its first frame");
            check(outBand == nullptr || !outBand->transform.visible,
                  "each band is gated off the frame after its interval");
        }
    }

    void captionsRejectAMismatchedLineCount() {
        section("a line/beat mismatch fails closed");
        const std::vector<float> pcm = syntheticVoiceover(48000, 2.f);
        const BeatGrid grid = buildBeatGrid(pcm, testSettings(), 30.f, 0, 60);
        FakeContentHost host;
        TemplateScene scene("gate", 30.f, host, 1920.f, 1080.f);
        bool threw = false;
        try {
            (void) addCaptionTrack(scene, grid, {"solo una riga"});
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(grid.frames.size() != 1, "the fixture grid is not trivially one beat");
        check(threw, "a wrong line count is rejected");
    }

    void theChartGrowsStaggeredAndLandsOnThePeak() {
        section("the chart grows staggered and lands on the peak");
        FakeContentHost host;
        TemplateScene scene("chart", 30.f, host, 1920.f, 1080.f);

        DataVizSpec spec;
        spec.values = {0.4f, 1.f, 0.7f, 0.2f};
        spec.labels = {"nord", "centro", "sud", "isole"};
        spec.highlightIndex = 1;
        spec.title = "Vendite";
        spec.inFrame = 10;
        spec.duration = 120;
        const DataVizComposition chart = addDataVizChart(scene, spec);

        check(chart.bars.size() == 4, "one bar per value");
        check(chart.valueLabels.size() == 4, "one label per value");
        check(chart.halo != nullptr, "the highlighted bar carries a halo");
        check(chart.trendLine != nullptr, "the trend line is authored");
        check(chart.title != nullptr, "the title is authored");
        check(chart.peakFrame == 70, "the bars land halfway through the duration");
        check(scene.validate().empty(), "the chart scene validates");

        // Bar 0 has landed at its staggered key; bar 3 has not started moving yet.
        const FrameSubmission early = scene.submit(11);
        const BoundLayer* firstBar = findLayer(early, chart.bars[0]->id());
        check(firstBar != nullptr, "the first bar is bound while growing");
        const FrameSubmission landed = scene.submit(70);
        check(findLayer(landed, chart.bars[3]->id()) != nullptr,
              "the last bar is bound on the peak frame");
        check(findLayer(landed, chart.valueLabels[3]->id()) != nullptr,
              "the last label appears exactly when its bar lands");

        // Determinism: the same frame twice, identical world matrices.
        const FrameSubmission a = scene.submit(40);
        const FrameSubmission b = scene.submit(40);
        bool identical = true;
        for (std::size_t i = 0; i < a.layers.size() && identical; ++i) {
            const auto& ma = a.layers[i].transform.world.elements;
            const auto& mb = b.layers[i].transform.world.elements;
            for (std::size_t k = 0; k < ma.size(); ++k) {
                if (ma[k] != mb[k]) identical = false;
            }
        }
        check(identical, "chart evaluation is a pure function of (scene, frame)");
    }

    void theChartRejectsBadData() {
        section("bad chart data is rejected fail-closed");
        FakeContentHost host;
        TemplateScene scene("gate", 30.f, host, 1920.f, 1080.f);

        DataVizSpec empty;
        bool threw = false;
        try {
            (void) addDataVizChart(scene, empty);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "an empty value list is rejected");

        DataVizSpec zeroMax;
        zeroMax.values = {0.f, 0.f};
        threw = false;
        try {
            (void) addDataVizChart(scene, zeroMax);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "an all-zero value list is rejected");

        DataVizSpec badLabels;
        badLabels.values = {1.f, 2.f};
        badLabels.labels = {"solo uno"};
        threw = false;
        try {
            (void) addDataVizChart(scene, badLabels);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a mismatched label count is rejected");

        DataVizSpec badHighlight;
        badHighlight.values = {1.f, 2.f};
        badHighlight.highlightIndex = 5;
        threw = false;
        try {
            (void) addDataVizChart(scene, badHighlight);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "an out-of-range highlight index is rejected");
    }

    void theLineChartWalksLeftToRightAndLandsOnThePeak() {
        section("the step-line chart walks left-to-right and lands on the peak");
        FakeContentHost host;
        TemplateScene scene("line", 30.f, host, 1920.f, 1080.f);

        DataVizSpec spec;
        spec.values = {0.4f, 1.f, 0.7f, 0.2f};
        spec.labels = {"nord", "centro", "sud", "isole"};
        spec.highlightIndex = 1;
        spec.title = "Vendite";
        spec.inFrame = 10;
        spec.duration = 120;
        const DataVizLineComposition line = addDataVizLineChart(scene, spec);

        check(line.dots.size() == 4, "one dot per value");
        check(line.runs.size() == 3, "one run between consecutive values");
        check(line.valueLabels.size() == 4, "one label per value");
        check(line.title != nullptr, "the title is authored");
        check(line.peakFrame == 70, "the trace lands halfway through the duration");
        check(scene.validate().empty(), "the line scene validates");

        const FrameSubmission landed = scene.submit(70);
        check(findLayer(landed, line.dots[3]->id()) != nullptr,
              "the last dot is bound on the peak frame");
        check(findLayer(landed, line.valueLabels[3]->id()) != nullptr,
              "the last label appears exactly when its dot lands");

        const FrameSubmission a = scene.submit(40);
        const FrameSubmission b = scene.submit(40);
        bool identical = true;
        for (std::size_t i = 0; i < a.layers.size() && identical; ++i) {
            const auto& ma = a.layers[i].transform.world.elements;
            const auto& mb = b.layers[i].transform.world.elements;
            for (std::size_t k = 0; k < ma.size(); ++k) {
                if (ma[k] != mb[k]) identical = false;
            }
        }
        check(identical, "line evaluation is a pure function of (scene, frame)");

        DataVizSpec empty;
        bool threw = false;
        try {
            (void) addDataVizLineChart(scene, empty);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "an empty value list is rejected");
    }

}// namespace

int main() {

    theBeatGridIsDeterministicAndGapped();
    captionsLineUpOnePerBeat();
    captionsRejectAMismatchedLineCount();
    theChartGrowsStaggeredAndLandsOnThePeak();
    theChartRejectsBadData();
    theLineChartWalksLeftToRightAndLandsOnThePeak();
    return chrononmotion_test::report();
}
