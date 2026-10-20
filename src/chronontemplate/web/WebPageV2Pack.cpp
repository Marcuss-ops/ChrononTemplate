// ChrononTemplate web.WebPageV2Pack — second-generation native web pages.
//
// See the header for the V1 defect list this pack fixes. The single most
// important invariant: text_animator `rotation` is read by the renderer in
// RADIANS (V1 authored 82.0 degrees and every video export died in
// TextRunNode with a ~248k px producer surface). kFoldMaxRad is the ceiling.
#include "chronontemplate/web/WebPageV2Pack.hpp"

#include "chronontemplate/core/NativePrimitives.hpp"

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
        constexpr const char* kSerif = "assets/fonts/FreeSerif.ttf";
        constexpr int kFoldStagger = 2, kFoldFrames = 9;
        // RADIANS ceiling for the per-glyph fold (1.45 rad ~= 83 deg of look).
        // Anything above ~3.0 rad is a units bug: see V1-001 in the header.
        constexpr double kFoldMaxRad = 1.45;
        constexpr float kFoldLift = 30.f;

        [[noreturn]] void fail(const std::string& message) {
            throw std::invalid_argument("WebPageV2Spec: " + message);
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

        Json easedTrack(const std::string& property, float from, float to, int start, int span,
                        const std::string& easing) {
            return {{"property", property}, {"easing", easing},
                    {"keyframes", Json::array({
                        {{"frame", 0}, {"value", from}},
                        {{"frame", std::max(1, start)}, {"value", from}},
                        {{"frame", start + span}, {"value", to}}})}};
        }

        Json rect(const std::string& id, float left, float top, float w, float h,
                  const std::string& hex, float alpha, const Json& tracks = Json::array()) {
            Json layer = {{"id", id}, {"type", "shape"}, {"enable_3d", true},
                          {"size", Json::array({w, h})},
                          {"position", Json::array({left + w * 0.5f, top + h * 0.5f, 0.f})},
                          {"start_frame", 0}, {"duration_frames", 1},
                          {"shape", {{"type", "rect"}, {"fill", Material::rgba(hex, alpha)}}}};
            if (!tracks.empty()) layer["animation"] = {{"tracks", tracks}};
            return layer;
        }

        Json fullWindowSelector(const std::string& id) {
            return {{"id", id}, {"unit", "character"}, {"shape", "square"}, {"order", "forward"},
                    {"combine", "replace"}, {"exclude_spaces", false},
                    {"start", {{"keyframes", Json::array({{{"frame", 0}, {"value", 0.0}}})}, {"easing", "linear"}}},
                    {"end", {{"keyframes", Json::array({{{"frame", 0}, {"value", 100.0}}})}, {"easing", "linear"}}}};
        }

        Json blurAnimator(const std::string& id, float blur, int durationFrames) {
            return {{"id", id}, {"selectors", Json::array({fullWindowSelector(id)})},
                    {"properties", Json::array({{
                        {"property", "blur"}, {"easing", "linear"},
                        {"keyframes", Json::array({
                            {{"frame", 0}, {"value", blur}},
                            {{"frame", durationFrames - 1}, {"value", blur}}})}}})}};
        }

        /// Per-glyph 3D fold in RADIANS: each character rotates in around X
        /// from kFoldMaxRad with a kFoldLift px lift, staggered per glyph.
        Json foldAnimators(const std::string& id, const std::string& text, int offset, int durationFrames) {
            const int n = static_cast<int>(text.size());
            Json animators = Json::array();
            for (int i = 0; i < n; ++i) {
                const int begin = offset + i * kFoldStagger;
                const double lo = 100.0 * i / n, hi = 100.0 * (i + 1) / n;
                Json selector = fullWindowSelector("v2_glyph_fold_" + std::to_string(i));
                if (begin > 0) {
                    selector["start"]["keyframes"].push_back({{"frame", begin}, {"value", lo}});
                    selector["end"]["keyframes"].push_back({{"frame", begin}, {"value", hi}});
                }
                Json rot = Json::array(), pos = Json::array(), opacity = Json::array();
                auto sample = [&](int frame) {
                    const double p = static_cast<double>(std::clamp(frame - begin, 0, kFoldFrames)) / kFoldFrames;
                    const double eased = 1.0 - std::pow(1.0 - p, 3.0);
                    rot.push_back({{"frame", frame}, {"value", Json::array({kFoldMaxRad * (1.0 - eased), 0.0, 0.0})}});
                    pos.push_back({{"frame", frame}, {"value", kFoldLift * (1.0 - eased)}});
                    opacity.push_back({{"frame", frame}, {"value", eased}});
                };
                if (begin > 0) sample(0);
                for (int f = 0; f <= kFoldFrames; ++f) sample(begin + f);
                for (Json* track : {&rot, &pos, &opacity}) {
                    if (begin + kFoldFrames < durationFrames - 1) {
                        track->push_back({{"frame", durationFrames - 1}, {"value", track->back()["value"]}});
                    }
                }
                animators.push_back({{"id", id + "_fold_" + std::to_string(i)},
                                     {"selectors", Json::array({std::move(selector)})},
                                     {"properties", Json::array({
                                         {{"property", "rotation"}, {"easing", "linear"}, {"keyframes", std::move(rot)}},
                                         {{"property", "position_y"}, {"easing", "linear"}, {"keyframes", std::move(pos)}},
                                         {{"property", "opacity"}, {"easing", "linear"}, {"keyframes", std::move(opacity)}}})}});
            }
            return animators;
        }

        Json textLayer(const std::string& id, const std::string& text, float left, float top,
                       float size, const char* font, const std::string& fill, int durationFrames,
                       float blur = 0.f, int entranceSlot = -1, bool fold = false, int foldOffset = 0) {
            const float w = std::max(60.f, estimateWidth(text, size) * 1.32f + 48.f);
            const float h = size * 1.65f;
            Json layer = {{"id", id}, {"type", "text"}, {"text", text},
                          {"size", Json::array({w, h})},
                          {"position", Json::array({left + w * 0.5f + 8.f, top + h * 0.5f, 0.f})},
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
                        easedTrack("opacity", 0.f, 1.f, start, 30, "out_cubic"),
                        easedTrack("position_y", 22.f, 0.f, start, 30, "out_cubic")})}};
            }
            return layer;
        }

        template <typename Push>
        Json sortedKeys(Push push) {
            Json keys = Json::array();
            push(keys);
            std::sort(keys.begin(), keys.end(), [](const Json& a, const Json& b) {
                return a["frame"].get<int>() < b["frame"].get<int>();
            });
            return keys;
        }

        Json markerSweepTracks(float width, int begin = 112, int span = 48) {
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

    const char* name(WebPageV2Theme theme) {
        return theme == WebPageV2Theme::Light ? "light" : "dark";
    }

    const char* name(WebPageV2Recipe recipe) {
        switch (recipe) {
            case WebPageV2Recipe::Complete: return "complete";
            case WebPageV2Recipe::Highlight3D: return "highlight3d";
            case WebPageV2Recipe::LongPhraseBlurred: return "longphraseblurred";
        }
        return "unknown";
    }

    WebPageV2Palette paletteFor(WebPageV2Theme theme) {
        if (theme == WebPageV2Theme::Light) {
            return {.paper = "#FAF9F6", .nav = "#FFFFFF", .ink = "#191D23", .muted = "#6E747C",
                    .accent = "#C8392B", .link = "#1A56DB", .rule = "#E7E4DC", .panel = "#F2F0EA",
                    .panelLine = "#D9D7D0", .highlight = "#FFE45C", .body = "#3E434B"};
        }
        return {.paper = "#0E1116", .nav = "#151A21", .ink = "#F4F1E9", .muted = "#9AA3AE",
                .accent = "#E8604C", .link = "#6FB7FF", .rule = "#222931", .panel = "#161C24",
                .panelLine = "#272F3A", .highlight = "#E8604C", .body = "#C2C8D1"};
    }

    void WebPageV2Spec::validate() const {
        const bool longBlurred = recipe == WebPageV2Recipe::LongPhraseBlurred;
        if (siteName.empty()) fail("siteName is required");
        if (siteName.size() > 24) fail("siteName is too long (<= 24 chars)");
        if (navLinks.size() > 5) fail("at most five nav links");
        for (const std::string& link : navLinks) {
            if (link.empty() || link.size() > 16) fail("nav links must be 1..16 chars");
        }
        if (!longBlurred) {
            if (headlineLineOne.empty()) fail("headlineLineOne is required");
            if (headlineLineOne.size() > 44) fail("headlineLineOne is too long (<= 44 chars)");
            if (headlineLineTwo.size() > 44) fail("headlineLineTwo is too long (<= 44 chars)");
            if (kicker.empty()) fail("kicker is required");
            if (bodyLines.empty()) fail("bodyLines is required for the article body");
            if (bodyLines.size() > 12) fail("at most twelve body lines");
            if (pickTitles.size() > 3) fail("at most three sidebar picks");
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
        if (!leadLine.empty() && leadLine.size() > 72) fail("leadLine is too long (<= 72 chars)");
        for (const std::string* text : {&byline, &dateline, &meta, &actionLabel,
                                        &searchHint, &importantPhrase, &leadLine}) {
            if (text->find('\n') != std::string::npos) fail("fields must not contain newlines");
        }
        if (durationFrames < 120 || durationFrames > 600) fail("durationFrames must be in [120, 600]");
    }

    std::string WebPageV2Spec::planName() const {
        return "web_page_v2_" + std::string(name(recipe)) + "_" + name(theme) + "_v1";
    }

    std::string WebPageV2Spec::outputStem() const {
        return outputName.empty() ? planName() + ".mp4"
                                  : (outputName.size() > 4 &&
                                     outputName.compare(outputName.size() - 4, 4, ".mp4") == 0
                                         ? outputName
                                         : outputName + ".mp4");
    }

    Json buildWebPageV2Plan(const WebPageV2Spec& spec) {
        spec.validate();
        const WebPageV2Palette pal = paletteFor(spec.theme);
        const int duration = spec.durationFrames;
        const std::string contrast = spec.theme == WebPageV2Theme::Light ? "#FAF9F6" : "#0E1116";
        const bool folded = spec.recipe == WebPageV2Recipe::Highlight3D;

        Json layers = Json::array({{
            {"id", "web_page_paper"}, {"type", "color"}, {"color", Material::rgba(pal.paper)},
            {"size", Json::array({kW, kH})}, {"screen_space", true},
            {"start_frame", 0}, {"duration_frames", duration}}});

        if (spec.recipe != WebPageV2Recipe::LongPhraseBlurred) {
            // ── nav chrome ────────────────────────────────────────────────
            layers.push_back(rect("nav_bar", 0.f, 0.f, static_cast<float>(kW), 76.f, pal.nav, 1.f));
            layers.push_back(rect("nav_rule", 0.f, 74.f, static_cast<float>(kW), 2.f, pal.rule, 1.f));
            layers.push_back(textLayer("nav_logo", spec.siteName, 90.f, 20.f, 25.f, kBold, pal.ink, duration,
                                       0.f, 0));
            float linkX = 660.f;
            int slot = 2;
            for (std::size_t i = 0; i < spec.navLinks.size(); ++i, ++slot) {
                layers.push_back(textLayer("nav_link_" + std::to_string(i), spec.navLinks[i],
                                           linkX, 26.f, 19.f, kRegular, pal.muted, duration, 2.6f, slot));
                linkX += estimateWidth(spec.navLinks[i], 19.f) + 46.f;
            }
            layers.push_back(rect("nav_search_pill", 1396.f, 20.f, 194.f, 38.f, pal.panel, 1.f,
                                  Json::array({easedTrack("opacity", 0.f, 1.f, 22, 28, "out_cubic")})));
            layers.push_back(textLayer("nav_search_text", spec.searchHint, 1418.f, 27.f, 16.f,
                                       kRegular, pal.muted, duration, 2.6f));
            layers.push_back(rect("nav_action_pill", 1618.f, 18.f, 212.f, 42.f, pal.accent, 1.f,
                                  Json::array({easedTrack("opacity", 0.f, 1.f, 26, 28, "out_cubic")})));
            layers.push_back(textLayer("nav_action_text", spec.actionLabel, 1648.f, 27.f, 18.f,
                                       kBold, contrast, duration));

            // ── masthead: kicker bar + label, hero headline, byline row ───
            layers.push_back(rect("kicker_bar", kMargin, 140.f, 44.f, 6.f, pal.accent, 1.f,
                                  Json::array({easedTrack("scale_x", 0.f, 1.f, 8, 24, "out_cubic")})));
            layers.push_back(textLayer("masthead_kicker", spec.kicker, kMargin + 58.f, 128.f, 21.f,
                                       kBold, pal.accent, duration, 0.f, 2));
            layers.push_back(textLayer("masthead_meta", spec.meta,
                                       kContentRight - estimateWidth(spec.meta, 16.f) - 16.f, 132.f,
                                       16.f, kRegular, pal.muted, duration, 2.4f, 3));

            if (folded) {
                layers.push_back(textLayer("headline_line_1", spec.headlineLineOne, kMargin, 200.f,
                                           72.f, kBold, pal.ink, duration, 0.f, -1, true, 0));
                if (!spec.headlineLineTwo.empty()) {
                    layers.push_back(textLayer("headline_line_2", spec.headlineLineTwo, kMargin, 296.f,
                                               72.f, kBold, pal.ink, duration, 0.f, -1, true, 40));
                    layers.push_back(rect("headline_marker", kMargin - 14.f, 292.f, 600.f, 118.f,
                                          pal.highlight, 0.45f, markerSweepTracks(600.f)));
                }
            } else {
                layers.push_back(textLayer("headline_line_1", spec.headlineLineOne, kMargin, 200.f,
                                           72.f, kBold, pal.ink, duration, 0.f, 4));
                if (!spec.headlineLineTwo.empty()) {
                    layers.push_back(textLayer("headline_line_2", spec.headlineLineTwo, kMargin, 296.f,
                                               72.f, kBold, pal.ink, duration, 0.f, 5));
                }
                layers.push_back(rect("headline_rule", kMargin, 402.f, 120.f, 5.f, pal.accent, 1.f,
                                      Json::array({easedTrack("scale_x", 0.f, 1.f, 34, 30, "out_cubic")})));
            }
            // byline + dateline + share pills on one row
            layers.push_back(textLayer("masthead_byline", spec.byline, kMargin, 428.f, 20.f,
                                       kBold, pal.ink, duration, 0.f, 7));
            const float bylineW = estimateWidth(spec.byline, 20.f);
            layers.push_back(textLayer("masthead_dateline", spec.dateline, kMargin + bylineW + 28.f, 430.f,
                                       19.f, kRegular, pal.muted, duration, 2.2f, 8));
            const std::vector<std::string> shares{"Share", "Save"};
            float shareX = kMargin;
            for (std::size_t i = 0; i < shares.size(); ++i) {
                const float pillW = estimateWidth(shares[i], 16.f) + 44.f;
                layers.push_back(rect("share_pill_" + std::to_string(i), shareX, 474.f, pillW, 34.f,
                                      pal.panel, 1.f,
                                      Json::array({easedTrack("opacity", 0.f, 1.f, 44 + static_cast<int>(i) * 4, 26, "out_cubic")})));
                layers.push_back(textLayer("share_text_" + std::to_string(i), shares[i], shareX + 22.f,
                                           481.f, 16.f, kRegular, pal.muted, duration, 2.2f));
                shareX += pillW + 14.f;
            }
            layers.push_back(rect("masthead_rule", kMargin, 534.f, kContentRight - kMargin - 330.f, 2.f,
                                  pal.rule, 1.f,
                                  Json::array({easedTrack("opacity", 0.f, 1.f, 46, 30, "out_cubic")})));

            // ── body: lead voice + two-column copy ────────────────────────
            int bodySlot = 9;
            float bodyY = 566.f;
            if (!spec.leadLine.empty()) {
                layers.push_back(textLayer("body_lead", spec.leadLine, kMargin, bodyY, 27.f,
                                           kSerif, pal.ink, duration, 0.f, bodySlot++));
                bodyY += 52.f;
            }
            const std::size_t split = spec.bodyLines.size() / 2 + 1;
            for (std::size_t i = 0; i < spec.bodyLines.size(); ++i) {
                const float y = bodyY + static_cast<float>(static_cast<int>(i) % 6) * 38.f;
                const float x = static_cast<int>(i) < static_cast<int>(split) ? kMargin : kMargin + 700.f;
                layers.push_back(textLayer("body_line_" + std::to_string(i), spec.bodyLines[i],
                                           x, y, 23.f, kSerif, pal.body, duration, 3.0f, bodySlot++));
            }

            // ── sidebar: numbered picks ───────────────────────────────────
            layers.push_back(rect("sidebar_panel", 1490.f, 212.f, 280.f, 540.f, pal.panel, 1.f));
            layers.push_back(rect("sidebar_panel_light", 1490.f, 212.f, 280.f, 2.f, pal.panelLine, 1.f));
            layers.push_back(textLayer("sidebar_title", "EDITOR'S PICKS", 1516.f, 240.f, 18.f,
                                       kBold, pal.muted, duration, 2.6f, 9));
            float pickY = 302.f;
            for (std::size_t i = 0; i < spec.pickTitles.size() && i < 3; ++i) {
                const std::string base = "sidebar_pick_" + std::to_string(i);
                layers.push_back(textLayer(base + "_num", "0" + std::to_string(i + 1), 1516.f, pickY,
                                           30.f, kBold, pal.accent, duration, 0.f, 10 + static_cast<int>(i)));
                layers.push_back(textLayer(base + "_line", spec.pickTitles[i], 1572.f, pickY + 6.f, 16.f,
                                           kRegular, pal.body, duration, 3.2f, 10 + static_cast<int>(i)));
                pickY += 108.f;
                if (i + 1 < spec.pickTitles.size()) {
                    layers.push_back(rect(base + "_rule", 1516.f, pickY - 26.f, 234.f, 1.f,
                                          pal.panelLine, 0.9f));
                }
            }

            // ── footer ────────────────────────────────────────────────────
            layers.push_back(rect("footer_rule", kMargin, 1006.f, kContentRight - kMargin, 1.f,
                                  pal.rule, 1.f));
            layers.push_back(textLayer("footer_left", spec.siteName + "  ·  all rights reserved",
                                       kMargin, 1024.f, 15.f, kRegular, pal.muted, duration, 2.6f));
            layers.push_back(textLayer("footer_right", "Top stories  ·  Newsletters",
                                       kContentRight - estimateWidth("Top stories  ·  Newsletters", 15.f) - 16.f,
                                       1024.f, 15.f, kRegular, pal.muted, duration, 2.6f));
        } else {
            auto contextLine = [&](const std::string& id, const std::string& text, float y) {
                const float w = estimateWidth(text, 30.f);
                layers.push_back(textLayer(id, text, 960.f - w * 0.5f, y, 30.f, kRegular,
                                           pal.muted, duration, 6.0f));
            };
            if (!spec.contextPhrases.empty()) contextLine("long_context_top_0", spec.contextPhrases[0], 232.f);
            if (spec.contextPhrases.size() > 1)
                contextLine("long_context_top_1", spec.contextPhrases[1], 292.f);

            layers.push_back(textLayer("important_center_phrase", spec.importantPhrase,
                                       960.f - estimateWidth(spec.importantPhrase, 76.f) * 0.5f, 476.f,
                                       76.f, kBold, pal.ink, duration, 0.f, -1, true, 0));
            const float phraseW = estimateWidth(spec.importantPhrase, 76.f);
            layers.push_back(rect("important_underline", 960.f - phraseW * 0.5f, 626.f,
                                  phraseW + 32.f, 6.f, pal.accent, 0.85f,
                                  markerSweepTracks(phraseW + 32.f)));

            for (std::size_t i = 2; i < spec.contextPhrases.size() && i < 6; ++i) {
                const float y = 766.f + static_cast<float>(i - 2) * 60.f;
                contextLine("long_context_bottom_" + std::to_string(i - 2), spec.contextPhrases[i], y);
            }
        }

        // ── camera: 3% push-in plus a slow half-degree drift ──────────────
        const Json camera = native::Camera::perspective({0.f, 0.f, -1320.f}, {0.f, 0.f, 0.f}, 50.f);
        Json cameraTracks = Json::array({
                Motion::track("camera_position_z",
                              {{0, -1320.0}, {duration * 2 / 3, -1260.0}, {duration - 1, -1254.0}},
                              "in_out_cubic"),
                Motion::track("camera_rotation_y", {{0, 0.5}, {duration - 1, -0.5}}, "in_out_cubic")});

        return TemplateComposition::renderPlan(
                spec.planName(), kW, kH, kFps, duration, layers, camera,
                native::Camera::animation(cameraTracks),
                {{"path", spec.outputStem()}, {"format", "mp4"}, {"codec", "h264"}});
    }

}// namespace chronontemplate::web
