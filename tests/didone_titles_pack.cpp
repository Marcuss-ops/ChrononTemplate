// ChrononTemplate — acceptance tests for editorial Didone titles (milestone: editorial_didone_titles_v1).

#include "chronontemplate/DidoneTitlesPack.hpp"
#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <fstream>
#include <set>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    void testExactFontAssetUsed() {
        section("TestExactFontAssetUsed");
        const DidoneStyleTokens tokens = didoneStyleTokens();
        check(tokens.font.id == "editorial_didone_book_italic", "font asset id is editorial_didone_book_italic");
        check(tokens.font.file == "Chronon3d/assets/fonts/Bodoni72-BookItalic.ttf",
              "font asset file points to Bodoni72-BookItalic.ttf");
        check(tokens.font.style == "Book Italic", "font style is Book Italic");
        check(tokens.font.weight == 400, "font weight is the native Book cut (400)");
        check(tokens.font.sha256 == "6dc5810efd4e5b5ec21b42bce000bb532fa07e26abfb0b63f4cdae74a52d3bf5",
              "font asset checksum matches pinned SHA-256");

        // Verify the file actually exists on disk in the project
        bool exists = false;
        const std::vector<std::string> prefixes = {"", "../", "../../", "/home/pierone/src/go-master/projects/Pyt/VeloxEditing/"};
        for (const auto& prefix : prefixes) {
            std::ifstream f(prefix + tokens.font.file, std::ios::binary);
            if (f.is_open()) {
                exists = true;
                break;
            }
        }
        check(exists, "font file exists in workspace");
    }

    void testSpanColorDoesNotChangeLayout() {
        section("TestSpanColorDoesNotChangeLayout");
        const DidoneStyleTokens tokens = didoneStyleTokens();

        // Layout A: All white "Non accettare"
        TextBlockLayout layoutA;
        TextBlockLine lineA;
        lineA.spans.push_back(TextSpan{.text = "Non accettare", .style = {.color = tokens.white}});
        layoutA.lines.push_back(lineA);

        // Layout B: Multi-span "Non " (white) + "accettare" (red)
        TextBlockLayout layoutB;
        TextBlockLine lineB;
        lineB.spans.push_back(TextSpan{.text = "Non ", .style = {.color = tokens.white}});
        lineB.spans.push_back(TextSpan{.text = "accettare", .style = {.color = tokens.red}});
        layoutB.lines.push_back(lineB);

        SpanBoundsResolver resA(layoutA, tokens.normal_size);
        SpanBoundsResolver resB(layoutB, tokens.normal_size);

        const auto lineBoundsA = resA.resolve_line_bounds(0);
        const auto lineBoundsB = resB.resolve_line_bounds(0);
        check(lineBoundsA.has_value() && lineBoundsB.has_value(), "line bounds resolved");
        checkNear(lineBoundsA->bounds.width, lineBoundsB->bounds.width, 0.01f,
                  "multi-span recoloring preserves identical total line width");
        checkNear(lineBoundsA->bounds.x, lineBoundsB->bounds.x, 0.01f,
                  "multi-span recoloring preserves line x origin");
        checkNear(lineBoundsA->bounds.y, lineBoundsB->bounds.y, 0.01f,
                  "multi-span recoloring preserves line y origin");
    }

    void testSpanBoundsMatchGlyphBounds() {
        section("TestSpanBoundsMatchGlyphBounds");
        const DidoneStyleTokens tokens = didoneStyleTokens();

        TextBlockLayout layout;
        TextBlockLine line0;
        line0.spans.push_back(TextSpan{.text = "è il valore più grande", .style = {.color = tokens.white}});
        TextBlockLine line1;
        line1.spans.push_back(TextSpan{.text = "di ", .style = {.color = tokens.white}});
        line1.spans.push_back(TextSpan{.text = "ogni business", .style = {.color = tokens.red}});
        layout.lines.push_back(line0);
        layout.lines.push_back(line1);

        SpanBoundsResolver resolver(layout, tokens.hero_size);

        const auto spanTarget = resolver.resolve_span_bounds("ogni business");
        check(spanTarget.has_value(), "can resolve span 'ogni business'");
        if (spanTarget) {
            check(spanTarget->bounds.width > 0.f, "resolved span has positive width");
            check(spanTarget->bounds.height > 0.f, "resolved span has positive height");
            check(spanTarget->line_index == 1, "resolved span belongs to line 1");
        }

        const auto line0Bounds = resolver.resolve_line_bounds(0);
        const auto line1Bounds = resolver.resolve_line_bounds(1);
        check(line0Bounds.has_value() && line1Bounds.has_value(), "line bounds resolve");
        check(line1Bounds->bounds.y > line0Bounds->bounds.y, "line 1 sits below line 0");
    }

    void testTightLeadingStable() {
        section("TestTightLeadingStable");
        const DidoneStyleTokens tokens = didoneStyleTokens();
        check(tokens.tight_leading >= 1.20f && tokens.tight_leading <= 1.40f,
              "open leading multiplier is in the readable editorial range 1.20 - 1.40");
        check(tokens.tracking >= -0.035f && tokens.tracking <= -0.01f,
              "tracking is slightly negative (-0.01em to -0.035em)");

        // Two lines at 100px: open leading prevents the hairline strokes from touching.
        const float stride = 100.f * tokens.tight_leading;
        checkNear(stride, 125.f, 0.01f, "line stride with 1.25 leading is 125px for 100px font");
    }

    void testHighlightBarTracksSpanBounds() {
        section("TestHighlightBarTracksSpanBounds");
        const DidoneStyleTokens tokens = didoneStyleTokens();

        TextBlockLayout layout;
        TextBlockLine line0;
        line0.spans.push_back(TextSpan{.text = "Non poteva accettare"});
        TextBlockLine line1;
        line1.spans.push_back(TextSpan{.text = "CIÒ CHE ERA"});
        layout.lines.push_back(line0);
        layout.lines.push_back(line1);

        SpanBoundsResolver resolver(layout, tokens.hero_size);
        const auto targetSpan = resolver.resolve_span_bounds("CIÒ CHE ERA");
        check(targetSpan.has_value(), "resolved target span 'CIÒ CHE ERA'");

        const DidoneRect bar = resolver.resolve_highlight_bar("CIÒ CHE ERA", 22.f, 6.f);
        check(!bar.empty(), "highlight bar is non-empty");
        checkNear(bar.width, targetSpan->bounds.width + 44.f, 0.01f,
                  "highlight bar width includes paddingX (22px each side)");
        checkNear(bar.height, targetSpan->bounds.height + 12.f, 0.01f,
                  "highlight bar height includes paddingY (6px each side)");
        checkNear(bar.x, targetSpan->bounds.x - 22.f, 0.01f,
                  "highlight bar starts 22px left of span");
    }

    void testCheckmarkTrimStartsZeroEndsOne() {
        section("TestCheckmarkTrimStartsZeroEndsOne");
        const DidoneChecklistTiming timing = didoneChecklistTiming();
        check(timing.stagger > 0, "checklist stagger is positive");
        check(timing.enter > 0, "checklist enter duration is positive");
        check(timing.check_delay >= 0, "check delay is non-negative");
        check(timing.check_draw > 0, "check draw duration is positive");

        DidoneChecklistItem item{.text = "Ferrovie", .in_frame = 14};
        const auto window = didoneCheckTrimWindow(item, timing);
        check(window[0] >= item.in_frame + timing.enter,
              "check draw starts after text settle (text settle = in_frame + enter)");
        check(window[1] > window[0], "check draw ends after it starts");
        check(window[1] - window[0] == timing.check_draw, "check draw window equals check_draw duration");

        const auto checkPath = didoneCheckmarkPath();
        check(!checkPath.svg_path.empty(), "check vector path is declared");
        check(checkPath.stroke_color == "#FF1018", "check color matches editorial.red");
        check(checkPath.stroke_width > 0.f, "check stroke width is positive");
    }

    void testMaskRevealDoesNotMoveFinalLayout() {
        section("TestMaskRevealDoesNotMoveFinalLayout");
        const DidoneStyleTokens tokens = didoneStyleTokens();

        TextBlockLayout layout;
        TextBlockLine line;
        line.spans.push_back(TextSpan{.text = "CIÒ CHE ERA"});
        layout.lines.push_back(line);

        SpanBoundsResolver resolver(layout, tokens.hero_size);
        const auto maskRect = resolver.resolve_mask_reveal_bounds(0, 10.f);
        const auto lineBounds = resolver.resolve_line_bounds(0);

        check(lineBounds.has_value(), "line bounds resolved");
        check(maskRect.x < lineBounds->bounds.x, "mask extends left of text");
        check(maskRect.right() > lineBounds->bounds.right(), "mask extends right of text");
        check(maskRect.y < lineBounds->bounds.y, "mask extends above text");
        check(maskRect.bottom() > lineBounds->bounds.bottom(), "mask extends below text");
    }

    void testPresetVocabularyMatches10Presets() {
        section("TestPresetVocabularyMatches10Presets");
        const auto presets = didoneTitlePresets();
        check(presets.size() == 10, "exactly 10 presets in the Didone editorial family");

        const auto ids = didoneTitlePresetIds();
        check(ids.size() == 10, "10 preset ids returned");

        std::set<std::string> unique_ids;
        for (const auto& id : ids) {
            check(id.rfind("didone_", 0) == 0, "preset id starts with 'didone_' prefix");
            check(unique_ids.insert(id).second, "preset ids are unique");
        }
        check(unique_ids.contains("didone_title_red_bar_reveal"), "contains didone_title_red_bar_reveal");
        check(unique_ids.contains("didone_checklist_stagger"), "contains didone_checklist_stagger");
        check(unique_ids.contains("didone_inline_emphasis"), "contains didone_inline_emphasis");
        check(unique_ids.contains("didone_hero_statement"), "contains didone_hero_statement");
    }

    void testDocumentaryCharcoalBackgroundTokens() {
        section("TestDocumentaryCharcoalBackgroundTokens");
        const DidoneBackgroundSpec bg = didoneBackgroundSpec();
        check(bg.base_color == "#080808", "charcoal background base is #080808");
        check(bg.center_lift >= 0.05f && bg.center_lift <= 0.12f, "center lift is 5-10%");
        check(bg.warm_tint > 0.f && bg.warm_tint <= 0.08f, "subtle warm tint");
        check(bg.vignette_amount >= 0.2f && bg.vignette_amount <= 0.5f, "moderate vignette");
        check(bg.grain_amount > 0.f && bg.grain_amount <= 0.1f, "subtle grain");
    }

    void testTemplateSceneApplication() {
        section("TestTemplateSceneApplication");
        FakeContentHost host;
        TemplateScene scene("didone_test", 30.f, host, 1920.f, 1080.f);

        // Template A
        DidoneTitleSpec specA{
            .lines = {"Non poteva accettare", "CIÒ CHE ERA"},
            .duration = 120,
        };
        const DidoneRect bar = applyDidoneTitlePreset(scene, DidoneTitlePreset::RedBarReveal, specA);
        check(!bar.empty(), "RedBarReveal returns a non-empty highlight bar rect");

        // Template B
        DidoneTitleSpec specB{
            .check_items = {
                {.text = "Ferrovie", .in_frame = 0},
                {.text = "Oleodotti", .in_frame = 14},
                {.text = "Raffinerie", .in_frame = 28},
            },
            .duration = 120,
        };
        applyDidoneTitlePreset(scene, DidoneTitlePreset::ChecklistStagger, specB);

        // Template C
        DidoneTitleSpec specC{
            .lines = {"Non accettare", "la propria", "condizione."},
            .accent_text = "accettare",
            .duration = 120,
        };
        applyDidoneTitlePreset(scene, DidoneTitlePreset::InlineEmphasis, specC);

        // Template D
        DidoneTitleSpec specD{
            .lines = {"è il valore più grande", "di ogni business"},
            .accent_text = "ogni business",
            .duration = 120,
        };
        applyDidoneTitlePreset(scene, DidoneTitlePreset::HeroStatement, specD);

        // Validation error on empty spec
        DidoneTitleSpec invalidSpec{.duration = 120};
        bool threw = false;
        try {
            applyDidoneTitlePreset(scene, DidoneTitlePreset::HeroStatement, invalidSpec);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "applyDidoneTitlePreset throws on empty spec");
    }

    void testFinalPoseValidation() {
        section("TestFinalPoseValidation");
        FakeContentHost host;

        // 1. Scene 1: RedBarReveal
        {
            TemplateScene scene("scene1_test", 30.f, host, 1920.f, 1080.f);
            DidoneTitleSpec spec{
                .lines = {"Non poteva accettare", "CIÒ CHE ERA"},
                .duration = 120,
            };
            const DidoneRect bar = applyDidoneTitlePreset(scene, DidoneTitlePreset::RedBarReveal, spec);
            check(!bar.empty(), "RedBarReveal bar bounds non-empty");

            const FrameSubmission sub = scene.submit(spec.duration);
            check(!sub.layers.empty(), "scene 1 has layers at end frame");
            for (const auto& bl : sub.layers) {
                check(bl.transform.visible, "scene 1 layer is visible at end frame");
                checkNear(bl.transform.opacity, 1.0f, 0.001f, "scene 1 layer opacity is 1.0 at end frame");
                const auto* motionLayer = scene.motion().findLayer(bl.transform.id);
                if (motionLayer != nullptr) {
                    checkNear(bl.transform.world[12], motionLayer->transform.position.x, 0.01f,
                              "scene 1 layer x animation offset is 0 at end frame");
                    checkNear(bl.transform.world[13], motionLayer->transform.position.y, 0.01f,
                              "scene 1 layer y animation offset is 0 at end frame");
                }
            }
        }

        // 2. Scene 2: ChecklistStagger
        {
            TemplateScene scene("scene2_test", 30.f, host, 1920.f, 1080.f);
            DidoneTitleSpec spec{
                .check_items = {
                    {.text = "Ferrovie", .in_frame = 0},
                    {.text = "Oleodotti", .in_frame = 14},
                    {.text = "Raffinerie", .in_frame = 28},
                },
                .duration = 120,
            };
            applyDidoneTitlePreset(scene, DidoneTitlePreset::ChecklistStagger, spec);
            const FrameSubmission sub = scene.submit(spec.duration);
            check(sub.layers.size() >= 3, "scene 2 has 3 checklist layers at end frame");
            for (const auto& bl : sub.layers) {
                check(bl.transform.visible, "scene 2 layer visible at end frame");
                checkNear(bl.transform.opacity, 1.0f, 0.001f, "scene 2 layer opacity is 1.0 at end frame");
                const auto* motionLayer = scene.motion().findLayer(bl.transform.id);
                if (motionLayer != nullptr) {
                    checkNear(bl.transform.world[12], motionLayer->transform.position.x, 0.01f,
                              "scene 2 layer x animation offset is 0 at end frame");
                    checkNear(bl.transform.world[13], motionLayer->transform.position.y, 0.01f,
                              "scene 2 layer y animation offset is 0 at end frame");
                }
            }
        }

        // 3. Scene 3: InlineEmphasis
        {
            TemplateScene scene("scene3_test", 30.f, host, 1920.f, 1080.f);
            DidoneTitleSpec spec{
                .lines = {"Non accettare", "la propria", "condizione."},
                .accent_text = "accettare",
                .duration = 120,
            };
            applyDidoneTitlePreset(scene, DidoneTitlePreset::InlineEmphasis, spec);
            const FrameSubmission sub = scene.submit(spec.duration);
            check(!sub.layers.empty(), "scene 3 has text layer at end frame");
            for (const auto& bl : sub.layers) {
                check(bl.transform.visible, "scene 3 layer visible at end frame");
                checkNear(bl.transform.opacity, 1.0f, 0.001f, "scene 3 layer opacity is 1.0 at end frame");
                const auto* motionLayer = scene.motion().findLayer(bl.transform.id);
                if (motionLayer != nullptr) {
                    checkNear(bl.transform.world[12], motionLayer->transform.position.x, 0.01f,
                              "scene 3 layer x offset is 0 at end frame");
                    checkNear(bl.transform.world[13], motionLayer->transform.position.y, 0.01f,
                              "scene 3 layer y offset is 0 at end frame");
                }
            }
        }

        // 4. Scene 4: HeroStatement
        {
            TemplateScene scene("scene4_test", 30.f, host, 1920.f, 1080.f);
            DidoneTitleSpec spec{
                .lines = {"è il valore più grande", "di ogni business"},
                .accent_text = "ogni business",
                .duration = 120,
            };
            applyDidoneTitlePreset(scene, DidoneTitlePreset::HeroStatement, spec);
            const FrameSubmission sub = scene.submit(spec.duration);
            check(!sub.layers.empty(), "scene 4 has text layer at end frame");
            for (const auto& bl : sub.layers) {
                check(bl.transform.visible, "scene 4 layer visible at end frame");
                checkNear(bl.transform.opacity, 1.0f, 0.001f, "scene 4 layer opacity is 1.0 at end frame");
                const auto* motionLayer = scene.motion().findLayer(bl.transform.id);
                if (motionLayer != nullptr) {
                    checkNear(bl.transform.world[12], motionLayer->transform.position.x, 0.01f,
                              "scene 4 layer x offset is 0 at end frame");
                    checkNear(bl.transform.world[13], motionLayer->transform.position.y, 0.01f,
                              "scene 4 layer y offset is 0 at end frame");
                }
            }
        }
    }

} // namespace

int main() {
    testExactFontAssetUsed();
    testSpanColorDoesNotChangeLayout();
    testSpanBoundsMatchGlyphBounds();
    testTightLeadingStable();
    testHighlightBarTracksSpanBounds();
    testCheckmarkTrimStartsZeroEndsOne();
    testMaskRevealDoesNotMoveFinalLayout();
    testPresetVocabularyMatches10Presets();
    testDocumentaryCharcoalBackgroundTokens();
    testTemplateSceneApplication();
    testFinalPoseValidation();

    return chrononmotion_test::report();
}
