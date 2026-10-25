// ChrononTemplate web.WebHeadlineHighlightPack — native C++ highlighter looks.
//
// All three plans (statement page, marker sweep, stepped highlight) are pure
// functions of the spec: every layer is authored as render-plan V3 data with
// the conventions proven by the web-page packs (camera-transformed layer
// positions are centers in top-left-down px, camera z is negative behind the
// layers). The highlighter blocks are estimated from the authored copy with
// the pack's deterministic width table; they are composition intent, not
// glyph-exact coverage. No Python, no Pillow, no browser: Chronon3D dev
// authoring vocabulary, the renderer rasterizes.
#include "chronontemplate/web/WebHeadlineHighlightPack.hpp"
#include "chronontemplate/core/NativePrimitives.hpp"

#include <chrononmotion/motion/Presets.hpp>

#include <algorithm>
#include <stdexcept>
#include <string>
#include <utility>

namespace chronontemplate::web {

    using native::Json;
    using native::Material;
    using native::TemplateComposition;

    namespace {

        constexpr int kW = 1920, kH = 1080, kFps = 30;
        constexpr const char* kBold = "Chronon3d/assets/fonts/Inter-Bold.ttf";
        constexpr const char* kRegular = "Chronon3d/assets/fonts/Inter-Regular.ttf";
        constexpr const char* kSerif = "Chronon3d/assets/fonts/FreeSerif.ttf";
        constexpr const char* kSerifItalic = "ChrononTemplate/assets/fonts/PlayfairDisplay-Italic.ttf";

        [[noreturn]] void fail(const std::string& message) {
            throw std::invalid_argument("WebHeadlineHighlightSpec: " + message);
        }

        /// The same deterministic width table the web-page packs use: block
        /// geometry follows authored copy, not measured glyphs.
        float estimateWidth(const std::string& text, float size) {
            double units = 0.0;
            for (unsigned char c : text) {
                if (c == ' ') units += 0.28;
                else if (c == 'i' || c == 'l' || c == 'I' || c == '!' || c == '.' || c == ',' || c == ':') units += 0.29;
                else if (c == 'm' || c == 'w' || c == 'M' || c == 'W') units += 0.78;
                else if (c >= 'A' && c <= 'Z') units += 0.64;
                else units += 0.52;
            }
            return static_cast<float>(units * size);
        }

        /// Camera-transformed shapes are authored with their center in
        /// top-left-down px, but the enable_3d wire space is bottom-left-up
        /// world units. Emission flips Y here — the single conversion point
        /// for every authored Y quantity.
        float wireY(float topDownCenterY) {
            return static_cast<float>(kH) - topDownCenterY;
        }

        Json rect(const std::string& id, float left, float top, float w, float h,
                  const std::string& hex, float alpha, const Json& tracks = Json::array()) {
            Json layer = {{ "id", id }, { "type", "shape" }, { "enable_3d", true },
                          { "size", Json::array({ w, h }) },
                          { "position", Json::array({ left + w * 0.5f, wireY(top + h * 0.5f), 0.f }) },
                          { "start_frame", 0 }, { "duration_frames", 1 },
                          { "shape", { { "type", "rect" }, { "fill", Material::rgba(hex, alpha) } } }};
            if (!tracks.empty()) layer["animation"] = { { "tracks", tracks } };
            return layer;
        }

        /// Whole-run selector: constant 0..100 window, the shape the web-page
        /// fold canary validated.
        Json fullWindowSelector(const std::string& id) {
            return { { "id", id }, { "unit", "character" }, { "shape", "square" }, { "order", "forward" },
                     { "combine", "replace" }, { "exclude_spaces", false },
                     { "start", { { "keyframes", Json::array({ { { "frame", 0 }, { "value", 0.0 } } }) }, { "easing", "linear" } } },
                     { "end", { { "keyframes", Json::array({ { { "frame", 0 }, { "value", 100.0 } } }) }, { "easing", "linear" } } } };
        }

        /// Baked linear blur animator: defocused copy keeps its blur the whole
        /// clip (the decoder requires sampled linear keyframes).
        Json blurAnimator(const std::string& id, float blur, int durationFrames) {
            return { { "id", id }, { "selectors", Json::array({ fullWindowSelector(id) }) },
                     { "properties", Json::array({ {
                         { "property", "blur" }, { "easing", "linear" },
                         { "keyframes", Json::array({
                             { { "frame", 0 }, { "value", blur } },
                             { { "frame", durationFrames - 1 }, { "value", blur } } }) } } }) } };
        }

        Json easedTrack(const std::string& property, float from, float to, int start, int span,
                        const std::string& easing) {
            return { { "property", property }, { "easing", easing },
                     { "keyframes", Json::array({
                         { { "frame", 0 }, { "value", from } },
                         { { "frame", std::max(1, start) }, { "value", from } },
                         { { "frame", start + span }, { "value", to } } }) } };
        }

        /// One text layer. `blur > 0` adds the full-window blur animator and
        /// `slot >= 0` staggers a fade/rise entrance.
        Json textLayer(const std::string& id, const std::string& text, float left, float top,
                       float size, const char* font, const std::string& fill, int durationFrames,
                       float blur = 0.f, int entranceSlot = -1) {
            const float w = std::max(60.f, estimateWidth(text, size) * 1.32f + 48.f);
            const float h = size * 1.65f;
            Json layer = { { "id", id }, { "type", "text" }, { "text", text },
                           { "size", Json::array({ w, h }) },
                           { "position", Json::array({ left + w * 0.5f + 8.f, wireY(top + h * 0.5f), 0.f }) },
                           { "enable_3d", true },
                           { "style", { { "font", font }, { "font_size", size }, { "fill", fill } } },
                           { "start_frame", 0 }, { "duration_frames", durationFrames } };
            if (blur > 0.f) {
                layer["text_animators"] = Json::array({ blurAnimator(id + "_blur", blur, durationFrames) });
            }
            if (entranceSlot >= 0) {
                const int start = 3 + entranceSlot * 4;
                layer["animation"] = { { "tracks", Json::array({
                    easedTrack("opacity", 0.f, 1.f, start, 26, "out_cubic"),
                    easedTrack("position_y", -26.f, 0.f, start, 26, "out_cubic") }) } };
            }
            return layer;
        }

        /// Frame-sorted: entrance + sweep keys appended out of order stay legal.
        template <typename Push>
        Json sortedKeys(Push push) {
            Json keys = Json::array();
            push(keys);
            std::sort(keys.begin(), keys.end(), [](const Json& a, const Json& b) {
                return a["frame"].get<int>() < b["frame"].get<int>();
            });
            return keys;
        }

        /// The left-to-right highlighter wipe: scale_x grows while the center
        /// slides from the left edge, the coupling the web-page marker used.
        Json highlightSweepTracks(float width, int begin, int span) {
            auto sweep = [&](Json& keys) {
                keys.push_back({ { "frame", begin - 8 }, { "value", 0.0 } });
                keys.push_back({ { "frame", begin }, { "value", 0.0 } });
                keys.push_back({ { "frame", begin + span }, { "value", 1.0 } });
            };
            auto slide = [&](Json& keys) {
                keys.push_back({ { "frame", begin }, { "value", -width * 0.5 } });
                keys.push_back({ { "frame", begin + span }, { "value", 0.0 } });
            };
            return Json::array({
                { { "property", "opacity" }, { "easing", "in_out_cubic" },
                  { "keyframes", sortedKeys([&](Json& keys) { sweep(keys); }) } },
                { { "property", "scale_x" }, { "easing", "in_out_cubic" },
                  { "keyframes", sortedKeys([&](Json& keys) { sweep(keys); }) } },
                { { "property", "position_x" }, { "easing", "in_out_cubic" },
                  { "keyframes", sortedKeys([&](Json& keys) { slide(keys); }) } } });
        }

        /// Restrained push-in: every recipe rides the same slow camera grammar
        /// the web-page family proved against the renderer.
        Json cameraSamplesFor(int duration) {
            constexpr float kDegToRad = 0.01745329251994329577f;
            chrononmotion::motion::CameraRig cameraRig(1, 50.f, float(kW) / float(kH), 1.f, 10000.f);
            cameraRig.setPosition({ 0.f, 0.f, 1320.f });
            chrononmotion::Quaternion initialYaw;
            initialYaw.setFromAxisAngle(chrononmotion::Vector3(0.f, 1.f, 0.f), -0.5f * kDegToRad);
            cameraRig.setOrientation(initialYaw);
            chrononmotion::motion::presets::cameraPush(cameraRig, 0, duration * 2 / 3, 56.f, float(kFps));
            chrononmotion::motion::presets::cameraPush(cameraRig, duration * 2 / 3,
                duration - 1 - duration * 2 / 3, 6.f, float(kFps));
            chrononmotion::motion::presets::cameraOrbit(cameraRig, 0, duration - 1,
                1.f * kDegToRad, 0.f, float(kFps));
            return native::Camera::samples(cameraRig, float(kFps), duration);
        }

    }// namespace

    const char* name(HeadlineHighlightRecipe recipe) {
        switch (recipe) {
            case HeadlineHighlightRecipe::StatementPage: return "statement";
            case HeadlineHighlightRecipe::MarkerSweep: return "marker_sweep";
            case HeadlineHighlightRecipe::SteppedHighlight: return "stepped_highlight";
        }
        return "unknown";
    }

    std::string WebHeadlineHighlightSpec::planName() const {
        return "web_headline_" + std::string(name(recipe)) + "_v1";
    }

    std::string WebHeadlineHighlightSpec::outputStem() const {
        return outputName.empty() ? planName() + ".mp4"
                                  : (outputName.size() > 4 &&
                                     outputName.compare(outputName.size() - 4, 4, ".mp4") == 0
                                         ? outputName
                                         : outputName + ".mp4");
    }

    void WebHeadlineHighlightSpec::validate() const {
        if (durationFrames < 60 || durationFrames > 600)
            fail("durationFrames must be in [60, 600]");
        for (const std::string* text : { &kicker, &highlightText, &dateline, &phrase,
                                         &siteName, &paperColor, &inkColor, &highlightColor }) {
            if (text->find('\n') != std::string::npos) fail("fields must not contain newlines");
        }
        if (recipe == HeadlineHighlightRecipe::MarkerSweep) {
            if (phrase.empty()) fail("phrase is required for the marker sweep");
            if (phrase.size() > 48) fail("phrase is too long (<= 48 chars)");
            return;
        }
        if (headlineLines.empty() || headlineLines.size() > 4)
            fail("one to four headline lines are required");
        for (const std::string& line : headlineLines) {
            if (line.empty() || line.size() > 64) fail("headline lines must be 1..64 chars");
        }
        if (highlightText.empty()) fail("highlightText is required");
        if (highlightText.size() > 64) fail("highlightText is too long (<= 64 chars)");
        if (recipe == HeadlineHighlightRecipe::StatementPage) {
            if (kicker.empty()) fail("kicker is required for the statement page");
            if (siteName.empty()) fail("siteName is required for the statement page");
            if (navLinks.size() > 4) fail("at most four nav links");
            for (const std::string& link : navLinks) {
                if (link.empty() || link.size() > 18) fail("nav links must be 1..18 chars");
            }
            if (bodyLines.size() > 6) fail("at most six body lines");
            for (const std::string& line : bodyLines) {
                if (line.empty() || line.size() > 80) fail("body lines must be 1..80 chars");
            }
        }
        if (recipe == HeadlineHighlightRecipe::SteppedHighlight && kicker.empty())
            fail("kicker is required for the stepped highlight");
    }

    Json buildWebHeadlineHighlightPlan(const WebHeadlineHighlightSpec& spec) {
        spec.validate();
        const int duration = spec.durationFrames;
        Json layers = Json::array();

        if (spec.recipe == HeadlineHighlightRecipe::MarkerSweep) {
            // ── lined paper, italic serif phrase, yellow marker band ─────────
            const std::string paper = spec.paperColor.empty() ? "#F7F3E9" : spec.paperColor;
            const std::string ink = spec.inkColor.empty() ? "#1F1B16" : spec.inkColor;
            const std::string marker = spec.highlightColor.empty() ? "#FFD23F" : spec.highlightColor;

            layers.push_back({ { "id", "sweep_paper" }, { "type", "color" },
                               { "color", Material::rgba(paper) },
                               { "size", Json::array({ kW, kH }) }, { "screen_space", true },
                               { "start_frame", 0 }, { "duration_frames", duration } });
            for (int line = 0; line < 14; ++line) {
                const float y = 120.f + static_cast<float>(line) * 68.f;
                layers.push_back(rect("paper_rule_" + std::to_string(line), 0.f, y,
                                      static_cast<float>(kW), 1.5f, ink, 0.10f));
            }

            const float phraseSize = 148.f;
            const float phraseW = estimateWidth(spec.phrase, phraseSize);
            const float phraseLeft = 960.f - phraseW * 0.5f;

            // The marker band: a wide bar plus a lower lip approximating the
            // hand-drawn slanted ends of the reference swipe.
            const int begin = std::max(12, duration / 5);
            const int span = std::max(12, duration / 4);
            const float bandW = phraseW * 1.12f;
            const float bandLeft = phraseLeft - phraseW * 0.06f;
            layers.push_back(rect("marker_band", bandLeft, 430.f, bandW, 176.f, marker, 0.92f,
                                  highlightSweepTracks(bandW, begin, span)));
            layers.push_back(rect("marker_band_lip", bandLeft + 26.f, 588.f, bandW * 0.82f, 30.f,
                                  marker, 0.85f, highlightSweepTracks(bandW, begin + 6, span)));

            layers.push_back(textLayer("sweep_phrase", spec.phrase, phraseLeft, 438.f,
                                       phraseSize, kSerifItalic, ink, duration, 0.f, 0));

            if (!spec.kicker.empty()) {
                layers.push_back(textLayer("sweep_kicker", spec.kicker, 150.f, 118.f, 22.f,
                                           kBold, ink, duration, 2.4f, 1));
            }
            if (!spec.dateline.empty()) {
                layers.push_back(textLayer("sweep_dateline", spec.dateline, 150.f, 940.f, 22.f,
                                           kRegular, ink, duration, 2.8f, 2));
            }
        } else {
            // ── shared page ground for the two headline recipes ──────────────
            const bool statement = spec.recipe == HeadlineHighlightRecipe::StatementPage;
            const std::string paper = spec.paperColor.empty()
                    ? (statement ? "#F4F2EE" : "#F2F1EC") : spec.paperColor;
            const std::string ink = spec.inkColor.empty() ? "#20242B" : spec.inkColor;
            const std::string marker = spec.highlightColor.empty()
                    ? (statement ? "#E8734A" : "#F2C230") : spec.highlightColor;

            layers.push_back({ { "id", "page_paper" }, { "type", "color" },
                               { "color", Material::rgba(paper) },
                               { "size", Json::array({ kW, kH }) }, { "screen_space", true },
                               { "start_frame", 0 }, { "duration_frames", duration } });

            float top = 150.f;
            if (statement) {
                // nav chrome + centered kicker, the statement page's grammar
                layers.push_back(rect("nav_bar", 0.f, 0.f, static_cast<float>(kW), 78.f, paper, 1.f));
                layers.push_back(rect("nav_rule", 0.f, 76.f, static_cast<float>(kW), 2.f, ink, 0.18f));
                layers.push_back(textLayer("nav_logo", spec.siteName, 96.f, 22.f, 24.f,
                                           kBold, ink, duration, 0.f, 0));
                float linkX = 1120.f;
                for (std::size_t i = 0; i < spec.navLinks.size(); ++i) {
                    layers.push_back(textLayer("nav_link_" + std::to_string(i), spec.navLinks[i],
                                               linkX, 26.f, 19.f, kRegular, ink, duration,
                                               3.2f, 1 + static_cast<int>(i)));
                    linkX += estimateWidth(spec.navLinks[i], 19.f) + 52.f;
                }
                const float kickerW = estimateWidth(spec.kicker, 24.f);
                layers.push_back(textLayer("page_kicker", spec.kicker, 960.f - kickerW * 0.5f,
                                           148.f, 24.f, kBold, ink, duration, 2.f, 5));
                top = 236.f;
            }

            // The headline stack; the highlighter covers the highlighted span
            // line by line, estimated from the authored copy.
            const float headlineSize = statement ? 88.f : 84.f;
            const float lineStep = headlineSize * 1.32f;
            float highlightLeft = 0.f, highlightRight = 0.f;
            int highlightLine = -1;
            for (std::size_t i = 0; i < spec.headlineLines.size(); ++i) {
                const std::string& line = spec.headlineLines[i];
                const float lineLeft = 150.f;
                layers.push_back(textLayer("headline_line_" + std::to_string(i), line,
                                           lineLeft, top + static_cast<float>(i) * lineStep,
                                           headlineSize, statement ? kBold : kSerif, ink,
                                           duration, 0.f, -1));
                const std::size_t found = line.find(spec.highlightText);
                if (found != std::string::npos) {
                    highlightLine = static_cast<int>(i);
                    highlightLeft = lineLeft + estimateWidth(line.substr(0, found), headlineSize);
                    highlightRight = lineLeft + estimateWidth(
                            line.substr(0, found + spec.highlightText.size()), headlineSize);
                }
            }

            if (highlightLine >= 0) {
                const int begin = std::max(12, duration / 5);
                const int span = std::max(12, duration / 4);
                const float blockTop = top + static_cast<float>(highlightLine) * lineStep +
                                       headlineSize * 0.18f;
                const float blockH = headlineSize * 1.02f;
                if (spec.recipe == HeadlineHighlightRecipe::SteppedHighlight) {
                    // Two stacked blocks with a stepped right edge, the shape
                    // of the AI-talent-war reference.
                    const float blockW = highlightRight - highlightLeft + 28.f;
                    layers.push_back(rect("highlight_block_top", highlightLeft - 14.f, blockTop,
                                          blockW, blockH * 0.55f, marker, 0.95f,
                                          highlightSweepTracks(blockW, begin, span)));
                    layers.push_back(rect("highlight_block_step", highlightLeft - 14.f,
                                          blockTop + blockH * 0.52f, blockW * 0.86f,
                                          blockH * 0.55f, marker, 0.95f,
                                          highlightSweepTracks(blockW, begin + 5, span)));
                } else {
                    const float blockW = highlightRight - highlightLeft + 28.f;
                    layers.push_back(rect("highlight_block", highlightLeft - 14.f, blockTop,
                                          blockW, blockH, marker, 0.88f,
                                          highlightSweepTracks(blockW, begin, span)));
                }
            }

            if (statement) {
                float bodyTop = top + static_cast<float>(spec.headlineLines.size()) * lineStep + 48.f;
                if (!spec.dateline.empty()) {
                    const float dateW = estimateWidth(spec.dateline, 26.f);
                    layers.push_back(textLayer("page_dateline", spec.dateline,
                                               960.f - dateW * 0.5f, bodyTop, 26.f,
                                               kRegular, ink, duration, 2.6f, 6));
                    bodyTop += 64.f;
                }
                for (std::size_t i = 0; i < spec.bodyLines.size(); ++i) {
                    layers.push_back(textLayer("body_line_" + std::to_string(i), spec.bodyLines[i],
                                               150.f, bodyTop + static_cast<float>(i) * 46.f,
                                               28.f, kSerif, ink, duration, 3.2f,
                                               7 + static_cast<int>(i)));
                }
            } else if (!spec.kicker.empty()) {
                // red-bullet kicker above the headline
                layers.push_back(rect("kicker_bullet", 150.f, top - 58.f, 14.f, 14.f, "#C0392B", 1.f));
                layers.push_back(textLayer("page_kicker", spec.kicker, 182.f, top - 68.f, 22.f,
                                           kBold, ink, duration, 2.f, 1));
                if (!spec.dateline.empty()) {
                    layers.push_back(textLayer("page_dateline", spec.dateline, 150.f,
                                               top + static_cast<float>(spec.headlineLines.size()) *
                                                         lineStep + 36.f,
                                               22.f, kRegular, ink, duration, 2.6f, 2));
                }
            }
        }

        const Json cameraSamples = cameraSamplesFor(duration);
        const Json camera = cameraSamples.front().at("camera");

        return TemplateComposition::renderPlan(
                spec.planName(), kW, kH, kFps, duration, layers, camera,
                cameraSamples,
                { { "path", spec.outputStem() }, { "format", "mp4" }, { "codec", "h264" } });
    }

}// namespace chronontemplate::web
