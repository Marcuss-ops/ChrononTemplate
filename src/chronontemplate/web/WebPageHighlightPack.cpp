// ChrononTemplate web.WebPageHighlightPack — native C++ web-page composition.
//
// All six plans (three recipes · two themes) are pure functions of the spec:
// every layer is authored as render-plan V3 data with the conventions proven
// by the blackboard and camera-bullet canaries (camera-transformed layer
// positions are centers in top-left-down px, camera z is negative behind the
// layers). Text that is not the point of the shot carries a full-window blur
// animator; the important center phrase never does. No Python, no Pillow, no
// browser: Chronon3D dev authoring vocabulary, the renderer rasterizes.
#include "chronontemplate/web/WebPageHighlightPack.hpp"
#include "chronontemplate/web/WebTextLayout.hpp"

#include "chronontemplate/core/NativePrimitives.hpp"

#include <chrononmotion/motion/Presets.hpp>

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace chronontemplate::web {

    using native::Json;
    using native::Material;
    using native::Motion;
    using native::TemplateComposition;

    namespace {

        constexpr int kW = 1920, kH = 1080, kFps = 30;
        constexpr float kMargin = 150.f;
        constexpr float kContentRight = kW - kMargin;   // 1770
        constexpr const char* kBold = "assets/fonts/Inter-Bold.ttf";
        constexpr const char* kRegular = "assets/fonts/Inter-Regular.ttf";
        constexpr const char* kSerif = "assets/fonts/PlayfairDisplay.ttf";
        // Keep one selected character active at a time. The Vulkan MTSDF
        // lane evaluates one animator per text run and applies its selector
        // per glyph; overlapping independent per-glyph animator stacks force
        // the entire run through the software rasterizer.
        constexpr int kFoldFrames = 5;

        [[noreturn]] void fail(const std::string& message) {
            throw std::invalid_argument("WebPageHighlightSpec: " + message);
        }

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

        /// Sparse layer-track with a named easing — the proven layer-track shape
        /// the bullet-focus canary validated against the renderer.
        Json easedTrack(const std::string& property, float from, float to, int start, int span,
                        const std::string& easing) {
            return {{"property", property}, {"easing", easing},
                    {"keyframes", Json::array({
                        {{"frame", 0}, {"value", from}},
                        {{"frame", std::max(1, start)}, {"value", from}},
                        {{"frame", start + span}, {"value", to}}})}};
        }

        /// Camera-transformed shapes are authored with their center in
        /// top-left-down px, but the enable_3d wire space is bottom-left-up
        /// world units (the reference phrase emitter lowers with the same
        /// `kHeight - y` conversion). Emission flips Y here — the single
        /// conversion point for every authored Y quantity.
        float wireY(float topDownCenterY) {
            return static_cast<float>(kH) - topDownCenterY;
        }

        Json rect(const std::string& id, float left, float top, float w, float h,
                  const std::string& hex, float alpha, const Json& tracks = Json::array()) {
            Json layer = {{"id", id}, {"type", "shape"}, {"enable_3d", true},
                          {"size", Json::array({w, h})},
                          {"position", Json::array({left + w * 0.5f, wireY(top + h * 0.5f), 0.f})},
                          {"start_frame", 0}, {"duration_frames", 1},
                          {"shape", {{"type", "rect"}, {"fill", Material::rgba(hex, alpha)}}}};
            if (!tracks.empty()) layer["animation"] = {{"tracks", tracks}};
            return layer;
        }

        /// Whole-run selector: constant 0..100 window, the shape the fold
        /// canary validated.
        Json fullWindowSelector(const std::string& id) {
            return {{"id", id}, {"unit", "character"}, {"shape", "square"}, {"order", "forward"},
                    {"combine", "replace"}, {"exclude_spaces", false},
                    {"start", {{"keyframes", Json::array({{{"frame", 0}, {"value", 0.0}}})}, {"easing", "linear"}}},
                    {"end", {{"keyframes", Json::array({{{"frame", 0}, {"value", 100.0}}})}, {"easing", "linear"}}}};
        }

        /// Baked linear blur animator: defocused context text keeps its blur the
        /// whole clip (the decoder requires sampled linear keyframes).
        Json blurAnimator(const std::string& id, float blur, int durationFrames) {
            return {{"id", id}, {"selectors", Json::array({fullWindowSelector(id)})},
                    {"properties", Json::array({{
                        {"property", "blur"}, {"easing", "linear"},
                        {"keyframes", Json::array({
                            {{"frame", 0}, {"value", blur}},
                            {{"frame", durationFrames - 1}, {"value", blur}}})}}})}};
        }

        /// GPU-native per-glyph fold. One character selector walks the shaped
        /// run while a single animator supplies the shared fold envelope.
        Json foldAnimators(const std::string& id, const std::string& text, int offset, int durationFrames) {
            const int n = static_cast<int>(text.size());
            const int foldFrames = std::max(1, std::min(kFoldFrames,
                (durationFrames - offset) / std::max(n, 1)));
            const int stagger = foldFrames;
            Json selector = fullWindowSelector("glyph_fold");
            Json selectorStart = Json::array();
            Json selectorEnd = Json::array();
            Json rot = Json::array(), pos = Json::array(), opacity = Json::array();
            for (int i = 0; i < n; ++i) {
                const int begin = offset + i * stagger;
                const double lo = 100.0 * i / n, hi = 100.0 * (i + 1) / n;
                for (int f = 0; f < foldFrames; ++f) {
                    selectorStart.push_back({{"frame", begin + f}, {"value", lo}});
                    selectorEnd.push_back({{"frame", begin + f}, {"value", hi}});
                }
                auto sample = [&](int frame) {
                    const double p = static_cast<double>(frame - begin) / foldFrames;
                    const double eased = 1.0 - std::pow(1.0 - p, 3.0);
                    rot.push_back({{"frame", frame}, {"value", Json::array({35.0 * (1.0 - eased), 0.0, 0.0})}});
                    pos.push_back({{"frame", frame}, {"value", -36.0 * (1.0 - eased)}});
                    opacity.push_back({{"frame", frame}, {"value", eased}});
                };
                for (int f = 0; f < foldFrames; ++f) sample(begin + f);
                if (i + 1 == n) sample(begin + foldFrames);
            }
            selectorStart.push_back({{"frame", offset + n * stagger}, {"value", 100.0}});
            selectorEnd.push_back({{"frame", offset + n * stagger}, {"value", 100.0}});
            selector["start"] = {{"easing", "linear"}, {"keyframes", std::move(selectorStart)}};
            selector["end"] = {{"easing", "linear"}, {"keyframes", std::move(selectorEnd)}};
            for (Json* track : {&rot, &pos, &opacity}) {
                std::sort(track->begin(), track->end(), [](const Json& a, const Json& b) {
                    return a["frame"].get<int>() < b["frame"].get<int>();
                });
                Json unique = Json::array();
                for (const auto& key : *track) {
                    if (!unique.empty() && unique.back()["frame"] == key["frame"])
                        unique.back() = key;
                    else
                        unique.push_back(key);
                }
                *track = std::move(unique);
            }
            Json animators = Json::array({{{"id", id + "_fold"},
                {"selectors", Json::array({std::move(selector)})},
                {"properties", Json::array({
                    {{"property", "rotation"}, {"easing", "linear"}, {"keyframes", std::move(rot)}},
                    {{"property", "position_y"}, {"easing", "linear"}, {"keyframes", std::move(pos)}},
                    {{"property", "opacity"}, {"easing", "linear"}, {"keyframes", std::move(opacity)}}})}}});
            return animators;
        }

        /// One text layer. `blur > 0` adds the full-window blur animator
        /// (context text), `fold` authors the per-glyph 3D reveal (important
        /// text), and `slot >= 0` staggers a fade/rise entrance.
        Json textLayer(const std::string& id, const std::string& text, float left, float top,
                       float size, const char* font, const std::string& fill, int durationFrames,
                       float blur = 0.f, int entranceSlot = -1, bool fold = false, int foldOffset = 0) {
            const float w = std::max(60.f, estimateWidth(text, size) * 1.32f + 48.f);
            const float h = size * 1.65f;
            Json layer = {{"id", id}, {"type", "text"}, {"text", text},
                          {"size", Json::array({w, h})},
                          {"position", Json::array({left + w * 0.5f + 8.f, wireY(top + h * 0.5f), 0.f})},
                          {"enable_3d", true},
                          {"style", {{"font", font}, {"font_size", size}, {"fill", fill}}},
                          {"start_frame", 0}, {"duration_frames", durationFrames}};
            Json animators = Json::array();
            if (blur > 0.f) animators.push_back(blurAnimator(id + "_blur", blur, durationFrames));
            if (fold) {
                Json glyphAnimators = foldAnimators(id, text, foldOffset, durationFrames);
                animators.insert(animators.end(), glyphAnimators.begin(), glyphAnimators.end());
            }
            if (!animators.empty()) layer["text_animators"] = std::move(animators);
            if (entranceSlot >= 0) {
                const int start = 3 + entranceSlot * 4;
                layer["animation"] = {{"tracks", Json::array({
                        easedTrack("opacity", 0.f, 1.f, start, 26, "out_cubic"),
                        easedTrack("position_y", -26.f, 0.f, start, 26, "out_cubic")})}};
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

        /// The left-to-right accent wipe used by the marker and the underline:
        /// scale_x grows while the center slides from the left edge (the exact
        /// coupling the bullet-focus heading markers used).
        Json markerSweepTracks(float width) {
            const int begin = 116, span = 46;
            auto sweep = [&](Json& keys) {
                keys.push_back({{"frame", begin - 8}, {"value", 0.0}});
                keys.push_back({{"frame", begin}, {"value", 0.0}});
                keys.push_back({{"frame", begin + span}, {"value", 1.0}});
            };
            auto slide = [&](Json& keys) {
                keys.push_back({{"frame", begin}, {"value", -width * 0.5}});
                keys.push_back({{"frame", begin + span}, {"value", 0.0}});
            };
            return Json::array({
                {{"property", "opacity"}, {"easing", "in_out_cubic"},
                 {"keyframes", sortedKeys([&](Json& keys) { sweep(keys); })}},
                {{"property", "scale_x"}, {"easing", "in_out_cubic"},
                 {"keyframes", sortedKeys([&](Json& keys) { sweep(keys); })}},
                {{"property", "position_x"}, {"easing", "in_out_cubic"},
                 {"keyframes", sortedKeys([&](Json& keys) { slide(keys); })}}});
        }

    }// namespace

    const char* name(WebPageTheme theme) {
        return theme == WebPageTheme::Light ? "light" : "dark";
    }

    const char* name(WebPageRecipe recipe) {
        switch (recipe) {
            case WebPageRecipe::Complete: return "complete";
            case WebPageRecipe::Highlight3D: return "highlight3d";
            case WebPageRecipe::LongPhraseBlurred: return "longphraseblurred";
        }
        return "unknown";
    }

    WebPagePalette paletteFor(WebPageTheme theme) {
        if (theme == WebPageTheme::Light) {
            return {.paper = "#F7F6F2", .nav = "#FFFFFF", .ink = "#1E2126", .muted = "#767A80",
                    .accent = "#2E3D4E", .link = "#1A56DB", .rule = "#E5E3DD", .panel = "#F1EFE9",
                    .panelLine = "#DBD9D3", .highlight = "#FFE45C", .body = "#43484F"};
        }
        return {.paper = "#0F1217", .nav = "#161B22", .ink = "#F2F0E8", .muted = "#98A1AC",
                .accent = "#62C8D6", .link = "#6FB7FF", .rule = "#232A32", .panel = "#171D25",
                .panelLine = "#262E38", .highlight = "#62C8D6", .body = "#BEC5CE"};
    }

    void WebPageHighlightSpec::validate() const {
        const bool longBlurred = recipe == WebPageRecipe::LongPhraseBlurred;
        if (siteName.empty()) fail("siteName is required");
        if (siteName.size() > 24) fail("siteName is too long (<= 24 chars)");
        if (navLinks.size() > 5) fail("at most five nav links");
        for (const std::string& link : navLinks) {
            if (link.empty() || link.size() > 16) fail("nav links must be 1..16 chars");
        }
        if (!longBlurred) {
            if (headlineLineOne.empty()) fail("headlineLineOne is required");
            if (headlineLineOne.size() > 48) fail("headlineLineOne is too long (<= 48 chars)");
            if (headlineLineTwo.size() > 48) fail("headlineLineTwo is too long (<= 48 chars)");
            if (kicker.empty()) fail("kicker is required");
            if (bodyLines.empty()) fail("bodyLines is required for the article body");
            if (bodyLines.size() > 80) fail("at most eighty body lines");
        } else {
            if (importantPhrase.empty()) fail("importantPhrase is required");
            if (importantPhrase.size() > 44) fail("importantPhrase is too long (<= 44 chars)");
            if (contextPhrases.size() < 2) fail("at least two contextPhrases are required");
            if (contextPhrases.size() > 6) fail("at most six contextPhrases");
        }
        for (const std::vector<std::string>* fields : {&bodyLines, &pickTitles, &contextPhrases}) {
            for (const std::string& line : *fields) {
                if (line.empty() || line.size() > 72) fail("rendered lines must be 1..72 chars");
            }
        }
        for (const std::string* text : {&byline, &dateline, &meta, &actionLabel,
                                        &searchHint, &importantPhrase}) {
            if (text->find('\n') != std::string::npos) fail("fields must not contain newlines");
        }
        if (durationFrames < 120 || durationFrames > 600) fail("durationFrames must be in [120, 600]");
    }

    std::string WebPageHighlightSpec::planName() const {
        return "web_page_" + std::string(name(recipe)) + "_" + name(theme) + "_v1";
    }

    std::string WebPageHighlightSpec::outputStem() const {
        return outputName.empty() ? planName() + ".mp4"
                                  : (outputName.size() > 4 &&
                                     outputName.compare(outputName.size() - 4, 4, ".mp4") == 0
                                         ? outputName
                                         : outputName + ".mp4");
    }

    Json buildWebPageHighlightPlan(const WebPageHighlightSpec& spec) {
        spec.validate();
        const WebPagePalette pal = paletteFor(spec.theme);
        const int duration = spec.durationFrames;
        const std::string contrast = spec.theme == WebPageTheme::Light ? "#F7F6F2" : "#0F1217";

        // The page paper is the full-bleed canvas; a screen-space color layer
        // stays exactly where it is while the camera push-in rides above it.
        Json layers = Json::array({{
            {"id", "web_page_paper"}, {"type", "color"}, {"color", Material::rgba(pal.paper)},
            {"size", Json::array({kW, kH})}, {"screen_space", true},
            {"start_frame", 0}, {"duration_frames", duration}}});

        if (spec.recipe != WebPageRecipe::LongPhraseBlurred) {
            // ── nav chrome ────────────────────────────────────────────────────
            layers.push_back(rect("nav_bar", 0.f, 0.f, static_cast<float>(kW), 72.f, pal.nav, 1.f));
            layers.push_back(rect("nav_rule", 0.f, 70.f, static_cast<float>(kW), 2.f, pal.rule, 1.f));
            layers.push_back(textLayer("nav_logo", spec.siteName, 90.f, 18.f, 24.f, kBold, pal.ink, duration,
                                       0.f, 0));
            float linkX = 640.f;
            int slot = 2;
            for (std::size_t i = 0; i < spec.navLinks.size(); ++i, ++slot) {
                layers.push_back(textLayer("nav_link_" + std::to_string(i), spec.navLinks[i],
                                           linkX, 22.f, 19.f, kRegular, pal.muted, duration, 3.4f, slot));
                linkX += estimateWidth(spec.navLinks[i], 19.f) + 44.f;
            }
            layers.push_back(rect("nav_search_pill", 1400.f, 18.f, 190.f, 38.f, pal.panel, 1.f,
                                  Json::array({easedTrack("opacity", 0.f, 1.f, 20, 26, "out_cubic")})));
            layers.push_back(textLayer("nav_search_text", spec.searchHint, 1420.f, 24.f, 16.f,
                                       kRegular, pal.muted, duration, 3.4f));
            layers.push_back(rect("nav_action_pill", 1620.f, 16.f, 210.f, 40.f, pal.accent, 1.f,
                                  Json::array({easedTrack("opacity", 0.f, 1.f, 24, 26, "out_cubic")})));
            layers.push_back(textLayer("nav_action_text", spec.actionLabel, 1650.f, 24.f, 18.f,
                                       kBold, contrast, duration));

            // ── masthead ──────────────────────────────────────────────────────
            layers.push_back(textLayer("masthead_kicker", spec.kicker, kMargin, 138.f, 22.f,
                                       kBold, pal.accent, duration, 0.f, 2));
            layers.push_back(textLayer("masthead_meta", spec.meta,
                                       kContentRight - estimateWidth(spec.meta, 16.f) - 16.f, 142.f,
                                       16.f, kRegular, pal.muted, duration, 3.f, 3));

            auto headline = [&](const std::string& id, const std::string& text, float y, int offset) {
                layers.push_back(textLayer(id, text, kMargin, y, 64.f, kBold, pal.ink, duration,
                                           0.f, -1, true, offset));
            };
            headline("headline_line_1", spec.headlineLineOne, 212.f, 0);
            if (!spec.headlineLineTwo.empty()) {
                headline("headline_line_2", spec.headlineLineTwo, 300.f, 44);
                if (spec.recipe == WebPageRecipe::Highlight3D) {
                    layers.push_back(rect("headline_marker", kMargin - 14.f, 296.f, 566.f, 108.f,
                                          pal.highlight, 0.5f, markerSweepTracks(566.f)));
                }
            }
            layers.push_back(textLayer("masthead_byline", spec.byline, kMargin, 418.f, 20.f,
                                       kBold, pal.ink, duration, 2.4f, 6));
            layers.push_back(rect("masthead_rule", kMargin, 466.f, kContentRight - kMargin, 2.f,
                                  pal.rule, 1.f,
                                  Json::array({easedTrack("opacity", 0.f, 1.f, 40, 30, "out_cubic")})));

            // ── two-column body: defocused context copy ───────────────────────
            int bodySlot = 7;
            const int split = static_cast<int>(spec.bodyLines.size() / 2 + 1);
            for (std::size_t i = 0; i < spec.bodyLines.size(); ++i) {
                const float y = 500.f + static_cast<float>(static_cast<int>(i) % 7) * 40.f;
                const float x = static_cast<int>(i) < split ? kMargin : kMargin + 690.f;
                layers.push_back(textLayer("body_line_" + std::to_string(i), spec.bodyLines[i],
                                           x, y, 23.f, kSerif, pal.body, duration, 3.2f, bodySlot++));
            }

            // ── sidebar: defocused recommendation card ────────────────────────
            layers.push_back(rect("sidebar_panel", 1490.f, 212.f, 280.f, 520.f, pal.panel, 1.f));
            layers.push_back(rect("sidebar_panel_light", 1490.f, 212.f, 280.f, 2.f, pal.panelLine, 1.f));
            layers.push_back(textLayer("sidebar_title", "EDITOR'S PICKS", 1516.f, 240.f, 18.f,
                                       kBold, pal.muted, duration, 3.f, 9));
            float pickY = 300.f;
            for (std::size_t i = 0; i < spec.pickTitles.size() && i < 3; ++i) {
                const std::string base = "sidebar_pick_" + std::to_string(i);
                layers.push_back(rect(base + "_thumb", 1516.f, pickY, 78.f, 56.f, pal.accent, 0.32f));
                layers.push_back(textLayer(base + "_line", spec.pickTitles[i], 1612.f, pickY + 4.f, 15.f,
                                           kRegular, pal.body, duration, 3.6f, 10 + static_cast<int>(i)));
                pickY += 96.f;
                if (i + 1 < spec.pickTitles.size()) {
                    layers.push_back(rect(base + "_rule", 1516.f, pickY - 22.f, 234.f, 1.f,
                                          pal.panelLine, 0.9f));
                }
            }

            // ── footer ────────────────────────────────────────────────────────
            layers.push_back(rect("footer_rule", kMargin, 1006.f, kContentRight - kMargin, 1.f,
                                  pal.rule, 1.f));
            layers.push_back(textLayer("footer_left", spec.siteName + "  ·  all rights reserved",
                                       kMargin, 1024.f, 15.f, kRegular, pal.muted, duration, 3.f));
        } else {
            // ── quiet plate: blurred long phrases, sharp center phrase ───────
            auto contextLine = [&](const std::string& id, const std::string& text, float y) {
                const float w = estimateWidth(text, 30.f);
                layers.push_back(textLayer(id, text, 960.f - w * 0.5f, y, 30.f, kRegular,
                                           pal.muted, duration, 6.5f));
            };
            if (!spec.contextPhrases.empty()) contextLine("long_context_top_0", spec.contextPhrases[0], 236.f);
            if (spec.contextPhrases.size() > 1)
                contextLine("long_context_top_1", spec.contextPhrases[1], 296.f);

            layers.push_back(textLayer("important_center_phrase", spec.importantPhrase,
                                       960.f - estimateWidth(spec.importantPhrase, 72.f) * 0.5f, 480.f,
                                       72.f, kBold, pal.ink, duration, 0.f, -1, true, 0));
            const float phraseW = estimateWidth(spec.importantPhrase, 72.f);
            layers.push_back(rect("important_underline", 960.f - phraseW * 0.5f, 622.f,
                                  phraseW + 32.f, 6.f, pal.accent, 0.85f,
                                  markerSweepTracks(phraseW + 32.f)));

            for (std::size_t i = 2; i < spec.contextPhrases.size() && i < 6; ++i) {
                const float y = 762.f + static_cast<float>(i - 2) * 60.f;
                contextLine("long_context_bottom_" + std::to_string(i - 2), spec.contextPhrases[i], y);
            }
        }

        // ── restrained camera: 2.6% push-in plus a slow half-degree drift ────
        constexpr float kDegToRad = 0.01745329251994329577f;
        chrononmotion::motion::CameraRig cameraRig(1, 50.f, float(kW) / float(kH), 1.f, 10000.f);
        cameraRig.setPosition({0.f, 0.f, 1320.f});
        chrononmotion::Quaternion initialYaw;
        initialYaw.setFromAxisAngle(chrononmotion::Vector3(0.f, 1.f, 0.f), -0.5f * kDegToRad);
        cameraRig.setOrientation(initialYaw);
        chrononmotion::motion::presets::cameraPush(cameraRig, 0, duration * 2 / 3, 56.f, float(kFps));
        chrononmotion::motion::presets::cameraPush(cameraRig, duration * 2 / 3,
            duration - 1 - duration * 2 / 3, 6.f, float(kFps));
        chrononmotion::motion::presets::cameraOrbit(cameraRig, 0, duration - 1,
            1.f * kDegToRad, 0.f, float(kFps));
        const Json cameraSamples = native::Camera::samples(cameraRig, float(kFps), duration);
        const Json camera = cameraSamples.front().at("camera");

        return TemplateComposition::renderPlan(
                spec.planName(), kW, kH, kFps, duration, layers, camera,
                cameraSamples,
                {{"path", spec.outputStem()}, {"format", "mp4"}, {"codec", "h264"}});
    }

    Json buildWebPageHighlightPlan(const WebPageHighlightSpec& spec,
                                   const WebTextLayout& bodyLayout) {
        if (bodyLayout.lines.empty() || bodyLayout.fontPath.empty() || bodyLayout.fontSize <= 0.f)
            throw std::invalid_argument("exact web page layout must contain shaped body lines and font metadata");
        WebPageHighlightSpec measured = spec;
        measured.bodyLines.clear();
        measured.bodyLines.reserve(bodyLayout.lines.size());
        for (const auto& line : bodyLayout.lines) measured.bodyLines.push_back(line.text);
        Json plan = buildWebPageHighlightPlan(measured);
        for (std::size_t i = 0; i < bodyLayout.lines.size(); ++i) {
            Json& layer = plan["layers"][static_cast<std::size_t>(
                std::find_if(plan["layers"].begin(), plan["layers"].end(), [&](const Json& candidate) {
                    return candidate.value("id", std::string{}) == "body_line_" + std::to_string(i);
                }) - plan["layers"].begin())];
            const auto& line = bodyLayout.lines[i];
            if (line.width <= 0.f || line.lineHeight <= 0.f)
                throw std::invalid_argument("exact web page line has invalid shaped dimensions");
            layer["size"] = Json::array({line.width + 2.f, line.lineHeight});
            layer["position"] = Json::array({line.x + (line.width + 2.f) * .5f,
                                               wireY(line.top + line.lineHeight * .5f), 0.f});
            layer["style"]["font"] = bodyLayout.fontPath;
            layer["style"]["font_size"] = bodyLayout.fontSize;
        }
        return plan;
    }

}// namespace chronontemplate::web
