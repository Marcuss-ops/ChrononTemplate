// ChrononTemplate — the caption/data-viz pack (BACKLOG item 5).
//
// Two halves, one boundary: the *audio* half turns PCM into a deterministic
// beat grid through the motion core's certified analyzer (no decoder lives
// here; the caller supplies normalized interleaved samples), and the *visual*
// half authors captions timed to that grid and a bar chart that grows on plain
// keyframes. Everything is composition and timing: Chronon shapes and measures
// every layer, ChrononMotion keys it, this module only decides what happens
// when.

#ifndef CHRONONTEMPLATE_CAPTIONS_DATAVIZ_CAPTIONS_DATAVIZ_PACK_HPP
#define CHRONONTEMPLATE_CAPTIONS_DATAVIZ_CAPTIONS_DATAVIZ_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include "chrononmotion/math/Vector2.hpp"

#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace chronontemplate {

    // ── The audio half ──────────────────────────────────────────────────────

    /// How the PCM is analyzed. The defaults match the motion core's own
    /// `AudioAnalysisSpec` except for the frame-space gate.
    struct AudioAnalysisSettings {
        std::uint32_t sampleRate{48000};
        std::uint32_t channels{1};
        std::size_t windowSize{1024};
        std::size_t hopSize{512};
        float onsetThreshold{1.5f};
        /// Two onsets closer than this many frames collapse into one beat, so a
        /// fluttering detector cannot key more captions than can be read.
        int minGapFrames{6};
    };

    /// The beats the analyzer found, in scene frames, plus the window they live
    /// in. `frames` is strictly increasing with at least `minGapFrames` between
    /// neighbours — the grid a caption track hangs on.
    struct BeatGrid {
        std::vector<int> frames{};
        int firstFrame{0};
        int endFrame{0};
        float fps{30.f};
    };

    /// Analyze interleaved, normalized PCM (no file I/O, no decoder) and reduce
    /// it to onset frames inside `[firstFrame, lastFrame)`. Deterministic: the
    /// same samples always produce the same grid. Throws
    /// `std::invalid_argument` on an empty buffer, a zero sample rate, or a
    /// degenerate window.
    [[nodiscard]] BeatGrid buildBeatGrid(std::span<const float> interleavedPcm,
                                         const AudioAnalysisSettings& settings,
                                         float fps, int firstFrame, int lastFrame);

    // ── Captions ────────────────────────────────────────────────────────────

    struct CaptionTrackSpec {
        std::string font{};
        float fontSize{54.f};
        std::string color{"#FFFFFF"};
        std::string bandColor{"#0B0E14"};
        float bandHeightFraction{0.16f}; ///< band height as a fraction of the canvas
        std::string name{"captions"};
    };

    /// What the pack authored: one band + one text layer per caption, in beat
    /// order. Caption i is alive on `[beats[i], beats[i + 1])`, the last one
    /// until `grid.endFrame`; it slides up into the band and fades out at its
    /// own end. No layer outlives its interval.
    struct CaptionTrack {
        std::vector<LayerHandle*> bands{};
        std::vector<LayerHandle*> captions{};
        int firstFrame{0};
        int endFrame{0};
    };

    /// Author one caption per beat. `lines` must carry exactly one entry per
    /// beat (trim the text list to the grid before calling). Throws
    /// `std::invalid_argument` on a size mismatch, an empty line, or a band
    /// fraction outside (0, 0.5).
    [[nodiscard]] CaptionTrack addCaptionTrack(TemplateScene& scene, const BeatGrid& beats,
                                               const std::vector<std::string>& lines,
                                               const CaptionTrackSpec& spec = {});

    // ── The data-viz half ───────────────────────────────────────────────────

    struct DataVizSpec {
        std::vector<float> values{};          ///< one bar per value; scaled to their max
        std::vector<std::string> labels{};    ///< per-bar text; empty entries render the value
        int highlightIndex{-1};               ///< one bar gets a pulsing halo
        std::string title{};
        std::string barColor{"#1B2330"};
        std::string accentColor{"#00E5FF"};
        std::string labelColor{"#FFFFFF"};
        std::string labelFont{};
        std::string titleFont{};
        float chartHeightFraction{0.45f};     ///< chart height as a fraction of the canvas
        float marginX{0.08f};                 ///< side margin as a fraction of the canvas
        bool showTrendLine{true};             ///< a rule that draws itself to the average
        bool pingPeak{true};                  ///< a two-pulse ping on the highlighted bar
        std::string name{"dataviz"};
        int inFrame{0};
        int duration{150};                    ///< bars finish growing halfway through
    };

    /// What the pack authored. `peakFrame` is when the bars have all landed —
    /// the natural cut point for a camera move or a title.
    struct DataVizComposition {
        std::vector<LayerHandle*> bars{};
        std::vector<LayerHandle*> valueLabels{};
        LayerHandle* halo{nullptr};
        LayerHandle* trendLine{nullptr};
        LayerHandle* title{nullptr};
        int inFrame{0};
        int endFrame{0};
        int peakFrame{0};
    };

    /// Author the chart into `scene`. Bars grow bottom-up on their own anchored
    /// scale track (staggered, all landed by the midpoint), each value label
    /// fades in exactly when its bar lands, the highlighted bar carries a slow
    /// opacity pulse, and the trend line draws itself left-to-right. Deterministic:
    /// no RNG anywhere. Throws `std::invalid_argument` on empty/too many values
    /// (1..24), a non-positive max, an out-of-range highlight index, a label
    /// count mismatch, or degenerate fractions.
    [[nodiscard]] DataVizComposition addDataVizChart(TemplateScene& scene, const DataVizSpec& spec);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_CAPTIONS_DATAVIZ_CAPTIONS_DATAVIZ_PACK_HPP
