#include "chronontemplate/captions_dataviz/CaptionsDataVizPack.hpp"

#include "chrononmotion/motion/OfflineBaking.hpp"
#include "chrononmotion/motion/Presets.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <iterator>
#include <stdexcept>

namespace chronontemplate {

    namespace {

        using Vector2 = chrononmotion::Vector2;
        using Vector3 = chrononmotion::Vector3;
        namespace pm = chrononmotion::motion::presets;
        using chrononmotion::motion::Easing;
        using chrononmotion::motion::Track;

        /// Frames -> seconds, the one conversion the motion core presets use.
        [[nodiscard]] inline float frameTime(const int frame, const float fps) {
            return chrononmotion::motion::frameToTime(frame, fps);
        }

        // ── The audio half ──────────────────────────────────────────────────

        [[nodiscard]] int frameOf(float seconds, float fps, int firstFrame) {
            return firstFrame + static_cast<int>(std::lround(seconds * fps));
        }

    }// namespace

    BeatGrid buildBeatGrid(const std::span<const float> interleavedPcm,
                           const AudioAnalysisSettings& settings, const float fps,
                           const int firstFrame, const int lastFrame) {
        if (interleavedPcm.empty()) {
            throw std::invalid_argument("buildBeatGrid: the PCM buffer is empty");
        }
        if (settings.sampleRate == 0) {
            throw std::invalid_argument("buildBeatGrid: the sample rate must be positive");
        }
        if (settings.windowSize == 0 || settings.hopSize == 0) {
            throw std::invalid_argument("buildBeatGrid: the analysis window must be non-degenerate");
        }
        if (lastFrame <= firstFrame) {
            throw std::invalid_argument("buildBeatGrid: expected firstFrame < lastFrame");
        }

        chrononmotion::motion::AudioAnalysisSpec analysis;
        analysis.sampleRate = settings.sampleRate;
        analysis.channels = settings.channels;
        analysis.windowSize = settings.windowSize;
        analysis.hopSize = settings.hopSize;
        analysis.onsetThreshold = settings.onsetThreshold;

        const std::vector<chrononmotion::motion::AudioFeatureSample> features =
                chrononmotion::motion::analyzePcmAudio(interleavedPcm, analysis);

        const int gap = std::max(0, settings.minGapFrames);
        BeatGrid grid;
        grid.fps = fps;
        grid.firstFrame = firstFrame;
        grid.endFrame = lastFrame;

        for (const chrononmotion::motion::AudioFeatureSample& feature : features) {
            if (feature.onset <= 0.f) continue;
            const int frame = frameOf(feature.seconds, fps, firstFrame);
            if (frame < firstFrame || frame >= lastFrame) continue;
            if (!grid.frames.empty() && frame - grid.frames.back() <= gap) continue;
            grid.frames.push_back(frame);
        }
        return grid;
    }

    // ── Captions ────────────────────────────────────────────────────────────

    CaptionTrack addCaptionTrack(TemplateScene& scene, const BeatGrid& beats,
                                 const std::vector<std::string>& lines, const CaptionTrackSpec& spec) {
        if (lines.size() != beats.frames.size()) {
            throw std::invalid_argument(
                    "addCaptionTrack: one line per beat is required (" +
                    std::to_string(lines.size()) + " lines for " +
                    std::to_string(beats.frames.size()) + " beats)");
        }
        for (const std::string& line : lines) {
            if (line.empty()) {
                throw std::invalid_argument("addCaptionTrack: caption lines must not be empty");
            }
        }
        if (!(spec.bandHeightFraction > 0.f) || spec.bandHeightFraction >= 0.5f) {
            throw std::invalid_argument("addCaptionTrack: the band fraction must be in (0, 0.5)");
        }
        if (beats.frames.empty()) {
            return {};
        }

        const Vector2 canvas = scene.canvas();
        const float bandH = canvas.y * spec.bandHeightFraction;
        const float bandY = canvas.y * 0.86f;
        const float slide = bandH * 0.5f;

        CaptionTrack out;
        out.firstFrame = beats.firstFrame;
        out.endFrame = beats.endFrame;

        for (std::size_t i = 0; i < beats.frames.size(); ++i) {
            const int start = beats.frames[i];
            const int stop = (i + 1 < beats.frames.size()) ? beats.frames[i + 1] : beats.endFrame;
            if (stop <= start) {
                throw std::invalid_argument("addCaptionTrack: the beat grid is not strictly increasing");
            }

            // The band is the strip the caption lives on; it hard-cuts in and out
            // on the beat, which is what makes the cut itself read as the beat.
            LayerHandle& band = scene.shape(ShapeSpec{.size = Vector2(canvas.x, bandH),
                                                      .fillColor = spec.bandColor,
                                                      .name = spec.name + "_band_" +
                                                               std::to_string(i)});
            band.position(canvas.x * 0.5f, bandY, 0.f)
                .alive(start, stop - 1);

            LayerHandle& caption = scene.text(TextSpec{.text = lines[i],
                                                       .font = spec.font,
                                                       .fontSize = spec.fontSize,
                                                       .color = spec.color,
                                                       .name = spec.name + "_" +
                                                               std::to_string(i)});
            caption.position(canvas.x * 0.5f, bandY, 0.f)
                   .alive(start, stop - 1);
            if (stop - start >= 4) {
                // Slide up into the band and fade in; fade out over the last
                // third. A shorter interval keeps the caption static instead of
                // interleaving two fades into one window.
                caption.animatePosition(start, std::max(1, (stop - start) / 3),
                                        Vector3(0.f, slide, 0.f), Easing::easeOut());
                caption.animateOpacity(start, std::max(1, (stop - start) / 4), 0.f, 1.f,
                                       Easing::easeOut());
                caption.animateOpacity(stop - std::max(1, (stop - start) / 3),
                                       std::max(1, (stop - start) / 3),
                                       1.f, 0.f, Easing::easeIn());
            }

            out.bands.push_back(&band);
            out.captions.push_back(&caption);
        }
        return out;
    }

    // ── The data-viz half ───────────────────────────────────────────────────

    DataVizComposition addDataVizChart(TemplateScene& scene, const DataVizSpec& spec) {
        if (spec.values.empty() || spec.values.size() > 24) {
            throw std::invalid_argument("addDataVizChart: expected between 1 and 24 values");
        }
        if (!(spec.chartHeightFraction > 0.f) || spec.chartHeightFraction > 1.f ||
            !(spec.marginX >= 0.f) || spec.marginX >= 0.5f) {
            throw std::invalid_argument("addDataVizChart: degenerate chart fractions");
        }
        if (!spec.labels.empty() && spec.labels.size() != spec.values.size()) {
            throw std::invalid_argument("addDataVizChart: the label count must match the value count");
        }
        if (spec.highlightIndex >= static_cast<int>(spec.values.size())) {
            throw std::invalid_argument("addDataVizChart: the highlight index is out of range");
        }
        const float max = *std::max_element(spec.values.begin(), spec.values.end());
        if (!(max > 0.f) || !std::isfinite(max)) {
            throw std::invalid_argument("addDataVizChart: values must be finite with a positive max");
        }

        const Vector2 canvas = scene.canvas();
        const float fps = scene.fps();
        const int inFrame = spec.inFrame;
        const int peak = inFrame + std::max(1, spec.duration / 2);
        const int endFrame = inFrame + spec.duration;
        const float chartH = canvas.y * spec.chartHeightFraction;
        const float floorY = canvas.y * 0.82f;
        const float left = canvas.x * spec.marginX;
        const float width = canvas.x * (1.f - 2.f * spec.marginX);
        const std::size_t n = spec.values.size();
        const float barW = width / static_cast<float>(n) * 0.6f;
        const float step = width / static_cast<float>(n);
        const int grow = std::max(6, (peak - inFrame) / 2);

        DataVizComposition out;
        out.inFrame = inFrame;
        out.endFrame = endFrame;
        out.peakFrame = peak;

        const float fontSize = std::max(18.f, canvas.y * 0.024f);
        float highlightX = 0.f;
        const auto valueText = [&](std::size_t i) {
            if (i < spec.labels.size() && !spec.labels[i].empty()) return spec.labels[i];
            char buffer[32];
            std::snprintf(buffer, sizeof(buffer), "%.4g", static_cast<double>(spec.values[i]));
            return std::string(buffer);
        };

        for (std::size_t i = 0; i < n; ++i) {
            const float value = spec.values[i] / max;               // normalized 0..1
            const float height = std::max(chartH * 0.02f, chartH * value);
            const float cx = left + step * (static_cast<float>(i) + 0.5f);
            if (static_cast<int>(i) == spec.highlightIndex) highlightX = cx;
            const int start = inFrame + static_cast<int>(i) * 3;    // staggered growth

            LayerHandle& bar = scene.shape(ShapeSpec{.size = Vector2(barW, height),
                                                     .fillColor = (static_cast<int>(i) == spec.highlightIndex)
                                                                          ? spec.accentColor
                                                                          : spec.barColor,
                                                     .name = spec.name + "_bar_" + std::to_string(i)});
            // Anchor at the base: scale grows the bar up off the floor, never
            // around its middle.
            bar.position(cx, floorY - height * 0.5f, 0.f)
               .anchor(barW * 0.5f, height * 0.5f)
               .alive(inFrame, endFrame);
            Track<Vector3>& scale = bar.layer().tracks.scale;
            scale.add(frameTime(start, fps), Vector3(0.02f, 0.02f, 1.f), Easing::overshoot());
            scale.add(frameTime(start + grow, fps), Vector3(1.f, 1.f, 1.f), Easing::overshoot());

            LayerHandle& label = scene.text(TextSpec{.text = valueText(i),
                                                     .font = spec.labelFont,
                                                     .fontSize = fontSize,
                                                     .color = spec.labelColor,
                                                     .name = spec.name + "_label_" + std::to_string(i)});
            label.position(cx, floorY - height - fontSize * 0.7f, 0.f)
                 .alive(start + grow, endFrame);
            label.animateOpacity(start + grow, std::max(1, grow / 2), 0.f, 1.f, Easing::easeOut());

            out.bars.push_back(&bar);
            out.valueLabels.push_back(&label);
        }

        // The highlighted bar carries a slow, readable opacity pulse train after
        // the peak — the chart keeps breathing without a second animation pass.
        if (spec.highlightIndex >= 0) {
            LayerHandle& halo = scene.shape(ShapeSpec{
                    .size = Vector2(barW * 1.6f, std::max(chartH * 0.06f, canvas.y * 0.02f)),
                    .fillColor = spec.accentColor,
                    .name = spec.name + "_halo"});
            halo.position(highlightX, floorY + fontSize * 0.6f, 0.f)
                .opacity(0.8f)
                .alive(peak, endFrame);
            pm::pulseOpacity(halo.layer(), peak, endFrame - peak, 3, fps, 0.35f);
            out.halo = &halo;
        }

        if (spec.showTrendLine && n > 1) {
            float sum = 0.f;
            for (const float v : spec.values) sum += v;
            const float avgY = floorY - chartH * (sum / static_cast<float>(n)) / max;
            LayerHandle& rule = scene.shape(ShapeSpec{.size = Vector2(width, std::max(2.f, canvas.y * 0.0035f)),
                                                      .fillColor = spec.accentColor,
                                                      .name = spec.name + "_trend"});
            // Scale X from nothing to full width about the left edge: the rule
            // draws itself, exactly like the motion core's lineDraw vocabulary.
            rule.position(left + width * 0.5f, avgY, 0.f)
                .anchor(width * 0.5f, 0.f)
                .alive(peak - grow, endFrame);
            Track<Vector3>& scale = rule.layer().tracks.scale;
            scale.add(frameTime(peak - grow, fps), Vector3(0.02f, 1.f, 1.f), Easing::easeInOut());
            scale.add(frameTime(peak, fps), Vector3(1.f, 1.f, 1.f), Easing::easeInOut());
            out.trendLine = &rule;
        }

        if (!spec.title.empty()) {
            LayerHandle& title = scene.text(TextSpec{.text = spec.title,
                                                     .font = spec.titleFont,
                                                     .fontSize = fontSize * 1.6f,
                                                     .color = spec.labelColor,
                                                     .name = spec.name + "_title"});
            title.position(canvas.x * 0.5f, canvas.y * 0.10f, 0.f)
                 .alive(inFrame, endFrame);
            title.animate(FadeIn{.inFrame = inFrame, .duration = 12});
            pm::slideIn(title.layer(), pm::Direction::Left, inFrame, 18, canvas.x * 0.06f, fps);
            out.title = &title;
        }

        if (spec.pingPeak) {
            LayerHandle& ping = scene.shape(ShapeSpec{
                    .size = Vector2(barW * 2.2f, barW * 2.2f),
                    .fillColor = spec.accentColor,
                    .name = spec.name + "_peak_ping",
                    .cornerRadius = barW * 1.1f});
            const std::size_t peakIndex = std::distance(
                    spec.values.begin(), std::max_element(spec.values.begin(), spec.values.end()));
            const float peakX = left + step * (static_cast<float>(peakIndex) + 0.5f);
            const float peakH = std::max(chartH * 0.02f, chartH * (spec.values[peakIndex] / max));
            ping.position(peakX, floorY - peakH - fontSize * 0.7f, 0.f)
                .opacity(0.f)
                .alive(peak, endFrame);
            pm::radarPing(ping.layer(), peak, endFrame - peak, 2, 0.2f, 1.f, fps);
            out.halo = out.halo ? out.halo : &ping;
        }
        return out;
    }

}// namespace chronontemplate
