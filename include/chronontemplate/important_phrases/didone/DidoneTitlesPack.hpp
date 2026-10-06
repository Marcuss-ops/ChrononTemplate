// ChrononTemplate — the editorial Didone title pack (editorial_didone_titles_v1).
//
// Milestone: editorial_didone_titles_v1
// Ten reference-matched title templates in the high-contrast Didone italic
// documentary language: Bodoni 72 Book Italic on a charcoal ground, one red
// accent per scene (editorial.red = #FF1018), open multi-line leading,
// SpanBoundsResolver for anchored geometry (highlight bar, checkmarks, masks),
// and camera-only motion after the entrance.
//
// The pack owns recipes and geometry authoring: it never renders pixels,
// never shapes glyphs, and never touches font files directly. The content
// side resolves the font asset through its own registry.
//
// Boundary: preset ids (`didone_*`) are editorial vocabulary and live here,
// NOT in the renderer.

#ifndef CHRONONTEMPLATE_DIDONE_TITLES_PACK_HPP
#define CHRONONTEMPLATE_DIDONE_TITLES_PACK_HPP

#include "chrononmotion/math/Vector2.hpp"
#include "chrononmotion/math/Vector3.hpp"
#include "chronontemplate/core/TemplateScene.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace chronontemplate {

    // ── Style tokens & FontAsset ─────────────────────────────────────────────

    /// Deterministic font asset description. The pipeline must load this exact
    /// file (checksum-pinned) through the content side's font registry — never
    /// "the font installed on the machine".
    struct DidoneFontAsset {
        std::string id{"editorial_didone_book_italic"};
        std::string file{"Chronon3d/assets/fonts/Bodoni72-BookItalic.ttf"};
        int face_index{0};
        std::string style{"Book Italic"};
        int weight{400};
        std::string sha256{"6dc5810efd4e5b5ec21b42bce000bb532fa07e26abfb0b63f4cdae74a52d3bf5"};
    };

    /// The Didone scene look: charcoal base, warm off-white text, one red token.
    struct DidoneStyleTokens {
        std::string white{"#F7F5F1"};
        std::string red{"#FF1018"};             ///< editorial.red: single token for text, bar, check
        std::string background{"#080808"};      ///< bg_documentary_charcoal base
        std::string background_deep_red{"#0A0203"};
        float hero_size{170.f};                 ///< Hero statement size @1920x1080 (140-220px)
        float normal_size{120.f};               ///< Normal emphasis line (90-150px)
        float small_size{72.f};                 ///< Small heading above the statement (55-90px)
        float tight_leading{1.25f};             ///< Open editorial leading for thin high-contrast strokes
        float tracking{-0.012f};                ///< Restrained negative tracking in em (-0.01em to -0.035em)
        DidoneFontAsset font{};
    };

    [[nodiscard]] DidoneStyleTokens didoneStyleTokens();

    /// Documentary charcoal background recipe tokens (bg_documentary_charcoal).
    struct DidoneBackgroundSpec {
        std::string base_color{"#080808"};
        float center_lift{0.08f};      ///< +5-10% center lightness
        float warm_tint{0.03f};        ///< subtle warm brown/red field
        float vignette_amount{0.35f};  ///< moderate radial vignette
        float grain_amount{0.04f};     ///< fine film grain
    };

    [[nodiscard]] DidoneBackgroundSpec didoneBackgroundSpec();

    // ── TextBlockLayout & TextSpan primitives ─────────────────────────────────

    struct TextSpanStyle {
        std::string font{};
        float size{0.f};
        std::string color{};
        float tracking{0.f};
        float baseline_shift{0.f};
        float opacity{1.f};
    };

    struct TextSpan {
        std::string text{};
        TextSpanStyle style{};
        std::string semantic_id{};
    };

    struct TextBlockLine {
        std::vector<TextSpan> spans{};

        [[nodiscard]] std::string plain_text() const {
            std::string out;
            for (const auto& span : spans) out += span.text;
            return out;
        }
    };

    /// TextBlockLayout — a unified multi-line layout with per-span styling.
    /// Preserves baseline, kerning, and tight leading across styled words.
    struct TextBlockLayout {
        std::vector<TextBlockLine> lines{};
        float line_height{1.25f};
        bool alignment_center{true};
        chrononmotion::Vector2 origin{960.f, 540.f};

        [[nodiscard]] std::string total_text() const {
            std::string out;
            for (std::size_t i = 0; i < lines.size(); ++i) {
                if (i > 0) out += '\n';
                out += lines[i].plain_text();
            }
            return out;
        }
    };

    // ── Pure geometry & SpanBoundsResolver ────────────────────────────────────

    struct DidoneRect {
        float x{0.f};
        float y{0.f};
        float width{0.f};
        float height{0.f};

        [[nodiscard]] bool empty() const noexcept { return width <= 0.f || height <= 0.f; }
        [[nodiscard]] float right() const noexcept { return x + width; }
        [[nodiscard]] float bottom() const noexcept { return y + height; }
        [[nodiscard]] chrononmotion::Vector2 center() const noexcept {
            return chrononmotion::Vector2{x + width * 0.5f, y + height * 0.5f};
        }
    };

    struct ResolvedSpanBounds {
        std::string text{};
        DidoneRect bounds{};
        int line_index{0};
        int span_index{0};
        float baseline_y{0.f};
    };

    /// Conservative run width calculation: 0.52em per code point for Didone italic.
    [[nodiscard]] float didoneRunWidthEm(std::string_view text, float font_size);

    /// Compute the red HighlightBar bounds for a target run centered at `canvas_center`.
    [[nodiscard]] DidoneRect didoneHighlightBarBounds(
            std::string_view text, float font_size,
            const chrononmotion::Vector2& canvas_center,
            float padding_x = 20.f, float padding_y = 6.f);

    /// SpanBoundsResolver — resolves geometrical anchors and boundaries
    /// for decorations (highlight bar, checkmarks, masks, depth focus).
    class SpanBoundsResolver {
    public:
        SpanBoundsResolver(const TextBlockLayout& layout, float default_font_size);

        [[nodiscard]] std::optional<ResolvedSpanBounds> resolve_span_bounds(std::string_view target_text) const;
        [[nodiscard]] std::optional<ResolvedSpanBounds> resolve_line_bounds(int line_index) const;
        [[nodiscard]] DidoneRect resolve_highlight_bar(std::string_view target_span, float pad_x = 20.f, float pad_y = 6.f) const;
        [[nodiscard]] chrononmotion::Vector2 resolve_checkmark_anchor(int line_index, float margin_right = 40.f) const;
        [[nodiscard]] DidoneRect resolve_mask_reveal_bounds(int line_index, float overflow_margin = 12.f) const;

    private:
        TextBlockLayout m_layout;
        float m_default_size{120.f};
        std::vector<ResolvedSpanBounds> m_resolved_spans;
        std::vector<ResolvedSpanBounds> m_resolved_lines;
    };

    // ── Checklist & Path Trim ────────────────────────────────────────────────

    struct DidoneChecklistItem {
        std::string text{};
        int in_frame{0};
    };

    struct DidoneChecklistTiming {
        int stagger{14};
        int enter{16};
        int check_delay{4};
        int check_draw{10};
    };

    [[nodiscard]] DidoneChecklistTiming didoneChecklistTiming();

    /// Returns the window [start_frame, end_frame] of an item's check stroke trim (0 -> 1).
    [[nodiscard]] std::array<int, 2> didoneCheckTrimWindow(
            const DidoneChecklistItem& item, const DidoneChecklistTiming& timing);

    /// Vector path definition for the stroked checkmark (not a font glyph).
    struct DidoneCheckmarkPath {
        std::string svg_path{"M 0,14 L 9,23 L 26,4"};
        float stroke_width{4.5f};
        std::string stroke_color{"#FF1018"};
    };

    [[nodiscard]] DidoneCheckmarkPath didoneCheckmarkPath();

    // ── Documentary camera plan ──────────────────────────────────────────────

    struct DidoneCameraPlan {
        float start_z{1250.f};
        float end_z{1100.f};
        float start_yaw_deg{-1.5f};
        float end_yaw_deg{0.f};
        int in_frame{0};
        int duration{90};
        int settle_frames{12};
    };

    [[nodiscard]] DidoneCameraPlan didoneCameraPlanFor(int preset_index, int duration_frames);

    // ── Presets Vocabulary (10 presets) ──────────────────────────────────────

    enum class DidoneTitlePreset : std::uint8_t {
        RedBarReveal,       ///< didone_title_red_bar_reveal (Template A)
        ChecklistStagger,   ///< didone_checklist_stagger (Template B)
        InlineEmphasis,     ///< didone_inline_emphasis (Template C)
        HeroStatement,      ///< didone_hero_statement (Template D)
        WordFocusRack,      ///< didone_word_focus_rack
        LineMaskRise,       ///< didone_line_mask_rise
        RedKeywordSwap,     ///< didone_red_keyword_swap
        CameraSlowPush,     ///< didone_camera_slow_push
        CameraPullReveal,   ///< didone_camera_pull_reveal
        QuoteDepthFocus,    ///< didone_quote_depth_focus
    };

    [[nodiscard]] const char* didoneTitlePresetId(DidoneTitlePreset preset) noexcept;
    [[nodiscard]] std::vector<std::string> didoneTitlePresetIds();
    [[nodiscard]] std::vector<DidoneTitlePreset> didoneTitlePresets();

    struct DidoneTitleSpec {
        std::string small_line{};
        std::vector<std::string> lines{};
        std::string accent_text{};
        std::vector<DidoneChecklistItem> check_items{};
        int in_frame{0};
        int duration{120};
        int entrance_end{30};
        std::optional<TextBlockLayout> custom_layout{};
    };

    /// Author `preset` onto `scene`. Returns the resolved highlight bar rect if any.
    [[nodiscard]] DidoneRect applyDidoneTitlePreset(
            TemplateScene& scene, DidoneTitlePreset preset,
            const DidoneTitleSpec& spec,
            const DidoneStyleTokens& tokens = didoneStyleTokens());

} // namespace chronontemplate

#endif // CHRONONTEMPLATE_DIDONE_TITLES_PACK_HPP
