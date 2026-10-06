// ChrononTemplate — the editorial Didone title pack implementation.
//
// Milestone: editorial_didone_titles_v1
// Pure geometry, SpanBoundsResolver, deterministic styling and motion authoring.

#include "chronontemplate/important_phrases/didone/DidoneTitlesPack.hpp"
#include "chrononmotion/motion/Easing.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace chronontemplate {
namespace {

    constexpr float kCanvasWidth{1920.f};
    constexpr float kCanvasHeight{1080.f};

    [[nodiscard]] int clamp_positive(int value, int fallback) {
        return value > 0 ? value : fallback;
    }

    [[nodiscard]] std::string to_lower_ascii(std::string_view text) {
        std::string out;
        out.reserve(text.size());
        for (const char c : text)
            out.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
        return out;
    }

    constexpr std::size_t kNotFound = std::numeric_limits<std::size_t>::max();

    [[nodiscard]] std::size_t find_accent_offset(const std::string& haystack,
                                                 const std::string& needle) {
        if (needle.empty()) return kNotFound;
        const std::string lower_hay = to_lower_ascii(haystack);
        const std::string lower_needle = to_lower_ascii(needle);
        const auto position = lower_hay.find(lower_needle);
        if (position == std::string::npos) return kNotFound;
        std::size_t offset = position;
        while (offset < haystack.size() &&
               (static_cast<unsigned char>(haystack[offset]) & 0xc0U) == 0x80U) {
            ++offset;
        }
        return offset;
    }

    [[nodiscard]] std::string join_lines(const std::vector<std::string>& lines) {
        std::string joined;
        for (std::size_t i = 0; i < lines.size(); ++i) {
            if (i > 0) joined += '\n';
            joined += lines[i];
        }
        return joined;
    }

    void author_camera_plan(TemplateScene& scene, const DidoneCameraPlan& plan) {
        auto& camera = scene.cameraRig();
        const float fps = scene.fps();
        const float t0 = static_cast<float>(plan.in_frame) / fps;
        const float t_settle = static_cast<float>(plan.in_frame + plan.duration - plan.settle_frames) / fps;
        const float t1 = static_cast<float>(plan.in_frame + plan.duration) / fps;

        const float mid_z = plan.start_z + (plan.end_z - plan.start_z) * 0.85f;
        camera.positionTrack().add(t0, chrononmotion::Vector3(0.f, 0.f, plan.start_z),
                                   chrononmotion::motion::Easing::easeInOut());
        camera.positionTrack().add(t_settle, chrononmotion::Vector3(0.f, 0.f, mid_z),
                                   chrononmotion::motion::Easing::easeOut());
        camera.positionTrack().add(t1, chrononmotion::Vector3(0.f, 0.f, plan.end_z),
                                   chrononmotion::motion::Easing::linear());

        if (std::fabs(plan.start_yaw_deg - plan.end_yaw_deg) > 0.0001f) {
            const float rad_start = plan.start_yaw_deg * 3.14159265f / 180.f;
            const float rad_end = plan.end_yaw_deg * 3.14159265f / 180.f;
            chrononmotion::Quaternion q0, q1;
            q0.setFromAxisAngle(chrononmotion::Vector3(0.f, 1.f, 0.f), rad_start);
            q1.setFromAxisAngle(chrononmotion::Vector3(0.f, 1.f, 0.f), rad_end);
            camera.orientationTrack().add(t0, q0, chrononmotion::motion::Easing::easeOut());
            camera.orientationTrack().add(t1, q1, chrononmotion::motion::Easing::linear());
        }
    }

} // namespace

    DidoneStyleTokens didoneStyleTokens() {
        return DidoneStyleTokens{};
    }

    DidoneBackgroundSpec didoneBackgroundSpec() {
        return DidoneBackgroundSpec{};
    }

    float didoneRunWidthEm(std::string_view text, float font_size) {
        if (font_size <= 0.f)
            throw std::invalid_argument("didoneRunWidthEm: font_size must be positive");
        std::size_t code_points = 0;
        for (const char c : text) {
            if ((static_cast<unsigned char>(c) & 0xc0U) != 0x80U)
                ++code_points;
        }
        constexpr float kAdvanceEm = 0.52f;
        const float width = static_cast<float>(code_points) * kAdvanceEm * font_size;
        return std::max(width, font_size * 0.8f);
    }

    DidoneRect didoneHighlightBarBounds(std::string_view text, float font_size,
                                        const chrononmotion::Vector2& canvas_center,
                                        float padding_x, float padding_y) {
        const float width = didoneRunWidthEm(text, font_size) + 2.f * padding_x;
        const float height = font_size * 0.95f + 2.f * padding_y;
        return DidoneRect{
            canvas_center.x - width * 0.5f,
            canvas_center.y - height * 0.5f,
            width,
            height,
        };
    }

    SpanBoundsResolver::SpanBoundsResolver(const TextBlockLayout& layout, float default_font_size)
        : m_layout(layout), m_default_size(default_font_size > 0.f ? default_font_size : 120.f) {
        const float stride = m_default_size * m_layout.line_height;
        const std::size_t num_lines = m_layout.lines.size();
        const float total_height = static_cast<float>(num_lines) * stride;
        const float start_y = m_layout.origin.y - total_height * 0.5f;

        for (std::size_t line_idx = 0; line_idx < num_lines; ++line_idx) {
            const auto& line = m_layout.lines[line_idx];
            float total_line_w = 0.f;
            std::vector<float> span_widths;
            span_widths.reserve(line.spans.size());

            for (const auto& span : line.spans) {
                const float sz = span.style.size > 0.f ? span.style.size : m_default_size;
                const float w = didoneRunWidthEm(span.text, sz);
                span_widths.push_back(w);
                total_line_w += w;
            }

            const float line_x = m_layout.alignment_center
                ? (m_layout.origin.x - total_line_w * 0.5f)
                : m_layout.origin.x;
            const float line_y = start_y + static_cast<float>(line_idx) * stride;

            ResolvedSpanBounds line_bounds;
            line_bounds.text = line.plain_text();
            line_bounds.bounds = DidoneRect{line_x, line_y, total_line_w, m_default_size};
            line_bounds.line_index = static_cast<int>(line_idx);
            line_bounds.span_index = -1;
            line_bounds.baseline_y = line_y + m_default_size * 0.8f;
            m_resolved_lines.push_back(line_bounds);

            float cur_span_x = line_x;
            for (std::size_t span_idx = 0; span_idx < line.spans.size(); ++span_idx) {
                const auto& span = line.spans[span_idx];
                const float w = span_widths[span_idx];
                const float sz = span.style.size > 0.f ? span.style.size : m_default_size;

                ResolvedSpanBounds sb;
                sb.text = span.text;
                sb.bounds = DidoneRect{cur_span_x, line_y, w, sz};
                sb.line_index = static_cast<int>(line_idx);
                sb.span_index = static_cast<int>(span_idx);
                sb.baseline_y = line_y + sz * 0.8f;
                m_resolved_spans.push_back(sb);

                cur_span_x += w;
            }
        }
    }

    std::optional<ResolvedSpanBounds> SpanBoundsResolver::resolve_span_bounds(std::string_view target_text) const {
        if (target_text.empty()) return std::nullopt;
        const std::string lower_target = to_lower_ascii(target_text);
        for (const auto& sb : m_resolved_spans) {
            if (to_lower_ascii(sb.text) == lower_target ||
                to_lower_ascii(sb.text).find(lower_target) != std::string::npos) {
                return sb;
            }
        }
        return std::nullopt;
    }

    std::optional<ResolvedSpanBounds> SpanBoundsResolver::resolve_line_bounds(int line_index) const {
        if (line_index >= 0 && line_index < static_cast<int>(m_resolved_lines.size())) {
            return m_resolved_lines[line_index];
        }
        return std::nullopt;
    }

    DidoneRect SpanBoundsResolver::resolve_highlight_bar(std::string_view target_span, float pad_x, float pad_y) const {
        const auto sb = resolve_span_bounds(target_span);
        if (!sb) {
            return didoneHighlightBarBounds(target_span, m_default_size, m_layout.origin, pad_x, pad_y);
        }
        return DidoneRect{
            sb->bounds.x - pad_x,
            sb->bounds.y - pad_y,
            sb->bounds.width + 2.f * pad_x,
            sb->bounds.height + 2.f * pad_y,
        };
    }

    chrononmotion::Vector2 SpanBoundsResolver::resolve_checkmark_anchor(int line_index, float margin_right) const {
        const auto lb = resolve_line_bounds(line_index);
        if (lb) {
            return chrononmotion::Vector2{lb->bounds.right() + margin_right, lb->bounds.center().y};
        }
        const float stride = m_default_size * m_layout.line_height;
        return chrononmotion::Vector2{m_layout.origin.x + 300.f + margin_right,
                                      m_layout.origin.y + static_cast<float>(line_index) * stride};
    }

    DidoneRect SpanBoundsResolver::resolve_mask_reveal_bounds(int line_index, float overflow_margin) const {
        const auto lb = resolve_line_bounds(line_index);
        if (lb) {
            return DidoneRect{
                lb->bounds.x - overflow_margin,
                lb->bounds.y - overflow_margin,
                lb->bounds.width + 2.f * overflow_margin,
                lb->bounds.height + 2.f * overflow_margin,
            };
        }
        return DidoneRect{};
    }

    DidoneChecklistTiming didoneChecklistTiming() {
        return DidoneChecklistTiming{};
    }

    std::array<int, 2> didoneCheckTrimWindow(const DidoneChecklistItem& item,
                                             const DidoneChecklistTiming& timing) {
        const int text_settle = item.in_frame + clamp_positive(timing.enter, 1);
        const int start = text_settle + clamp_positive(timing.check_delay, 0);
        return {start, start + clamp_positive(timing.check_draw, 1)};
    }

    DidoneCheckmarkPath didoneCheckmarkPath() {
        return DidoneCheckmarkPath{};
    }

    const char* didoneTitlePresetId(DidoneTitlePreset preset) noexcept {
        switch (preset) {
            case DidoneTitlePreset::RedBarReveal:     return "didone_title_red_bar_reveal";
            case DidoneTitlePreset::ChecklistStagger: return "didone_checklist_stagger";
            case DidoneTitlePreset::InlineEmphasis:   return "didone_inline_emphasis";
            case DidoneTitlePreset::HeroStatement:    return "didone_hero_statement";
            case DidoneTitlePreset::WordFocusRack:    return "didone_word_focus_rack";
            case DidoneTitlePreset::LineMaskRise:     return "didone_line_mask_rise";
            case DidoneTitlePreset::RedKeywordSwap:   return "didone_red_keyword_swap";
            case DidoneTitlePreset::CameraSlowPush:   return "didone_camera_slow_push";
            case DidoneTitlePreset::CameraPullReveal: return "didone_camera_pull_reveal";
            case DidoneTitlePreset::QuoteDepthFocus:  return "didone_quote_depth_focus";
        }
        return "didone_title_unknown";
    }

    std::vector<std::string> didoneTitlePresetIds() {
        std::vector<std::string> ids;
        ids.reserve(10);
        for (const DidoneTitlePreset preset : didoneTitlePresets()) {
            ids.emplace_back(didoneTitlePresetId(preset));
        }
        return ids;
    }

    std::vector<DidoneTitlePreset> didoneTitlePresets() {
        return {
            DidoneTitlePreset::RedBarReveal,
            DidoneTitlePreset::ChecklistStagger,
            DidoneTitlePreset::InlineEmphasis,
            DidoneTitlePreset::HeroStatement,
            DidoneTitlePreset::WordFocusRack,
            DidoneTitlePreset::LineMaskRise,
            DidoneTitlePreset::RedKeywordSwap,
            DidoneTitlePreset::CameraSlowPush,
            DidoneTitlePreset::CameraPullReveal,
            DidoneTitlePreset::QuoteDepthFocus,
        };
    }

    DidoneCameraPlan didoneCameraPlanFor(int preset_index, int duration_frames) {
        const int duration = clamp_positive(duration_frames, 90);
        DidoneCameraPlan plan;
        plan.duration = duration;
        switch (preset_index) {
            case 0: // RedBarReveal: tiny push
                plan.start_z = 1100.f;
                plan.end_z = 1030.f;
                plan.start_yaw_deg = 0.f;
                plan.end_yaw_deg = 0.f;
                break;
            case 1: // ChecklistStagger: near-static lens
                plan.start_z = 1150.f;
                plan.end_z = 1130.f;
                plan.start_yaw_deg = 0.f;
                plan.end_yaw_deg = 0.f;
                break;
            case 2: // InlineEmphasis: gentle settle from a slight angle
                plan.start_z = 1200.f;
                plan.end_z = 1120.f;
                plan.start_yaw_deg = -0.8f;
                plan.end_yaw_deg = 0.f;
                break;
            case 3: // HeroStatement: 1250 -> 1100 with documentary yaw
            default:
                plan.start_z = 1250.f;
                plan.end_z = 1100.f;
                plan.start_yaw_deg = -1.5f;
                plan.end_yaw_deg = 0.f;
                break;
        }
        return plan;
    }

    DidoneRect applyDidoneTitlePreset(TemplateScene& scene, DidoneTitlePreset preset,
                                      const DidoneTitleSpec& spec,
                                      const DidoneStyleTokens& tokens) {
        if (spec.duration <= 0)
            throw std::invalid_argument("didone: duration must be positive");
        if (spec.lines.empty() && spec.check_items.empty() && !spec.custom_layout)
            throw std::invalid_argument("didone: the block needs at least one line or item");

        DidoneRect bar_rect{};

        switch (preset) {
            case DidoneTitlePreset::RedBarReveal: {
                if (spec.lines.size() < 2)
                    throw std::invalid_argument("didone_title_red_bar_reveal: needs a small line and a statement line");

                LayerHandle& background = scene.group("didone-bg");
                background.alive(spec.in_frame, spec.in_frame + spec.duration);

                const std::string& small = spec.lines.front();
                const std::string& statement = spec.lines.back();

                bar_rect = didoneHighlightBarBounds(statement, tokens.hero_size,
                                                    chrononmotion::Vector2(kCanvasWidth * 0.5f, kCanvasHeight * 0.56f));

                LayerHandle& small_layer = scene.text({
                    .text = small,
                    .font = tokens.font.file,
                    .fontSize = tokens.small_size,
                    .color = tokens.white,
                    .name = "didone-small",
                });
                small_layer.position(kCanvasWidth * 0.5f, kCanvasHeight * 0.42f);
                small_layer.animatePosition(spec.in_frame, 10, chrononmotion::Vector3(0.f, 18.f, 0.f));
                small_layer.animateOpacity(spec.in_frame, 10, 0.f, 1.f);

                LayerHandle& statement_layer = scene.text({
                    .text = statement,
                    .font = tokens.font.file,
                    .fontSize = tokens.hero_size,
                    .color = tokens.white,
                    .name = "didone-statement",
                });
                statement_layer.position(kCanvasWidth * 0.5f, kCanvasHeight * 0.56f);
                statement_layer.animatePosition(spec.in_frame + 6, 14, chrononmotion::Vector3(0.f, 35.f, 0.f));
                statement_layer.animateOpacity(spec.in_frame + 6, 14, 0.f, 1.f);

                const DidoneCameraPlan cam = didoneCameraPlanFor(0, spec.duration - spec.in_frame);
                author_camera_plan(scene, cam);
                break;
            }

            case DidoneTitlePreset::ChecklistStagger: {
                if (spec.check_items.size() < 2)
                    throw std::invalid_argument("didone_checklist_stagger: needs at least two items");

                LayerHandle& background = scene.group("didone-bg");
                background.alive(spec.in_frame, spec.in_frame + spec.duration);

                const DidoneChecklistTiming timing = didoneChecklistTiming();
                const float slot_height = kCanvasHeight / static_cast<float>(spec.check_items.size() + 1);

                int index = 0;
                for (const DidoneChecklistItem& item : spec.check_items) {
                    const std::string name = "didone-check-text-" + std::to_string(index);
                    LayerHandle& text = scene.text({
                        .text = item.text,
                        .font = tokens.font.file,
                        .fontSize = tokens.normal_size,
                        .color = tokens.white,
                        .name = name,
                    });
                    const float y = slot_height * static_cast<float>(index + 1);
                    text.position(kCanvasWidth * 0.36f, y);
                    text.animatePosition(item.in_frame, timing.enter, chrononmotion::Vector3(0.f, 25.f, 0.f));
                    text.animateOpacity(item.in_frame, timing.enter, 0.f, 1.f);
                    ++index;
                }

                const DidoneCameraPlan cam = didoneCameraPlanFor(1, spec.duration - spec.in_frame);
                author_camera_plan(scene, cam);
                break;
            }

            case DidoneTitlePreset::InlineEmphasis:
            case DidoneTitlePreset::LineMaskRise:
            case DidoneTitlePreset::RedKeywordSwap:
            case DidoneTitlePreset::QuoteDepthFocus: {
                LayerHandle& background = scene.group("didone-bg");
                background.alive(spec.in_frame, spec.in_frame + spec.duration);

                if (spec.lines.empty() && !spec.custom_layout)
                    throw std::invalid_argument("didone: the block needs lines");

                if (!spec.accent_text.empty()) {
                    bool found = false;
                    for (const auto& line : spec.lines) {
                        if (find_accent_offset(line, spec.accent_text) != kNotFound) {
                            found = true;
                            break;
                        }
                    }
                    if (!found)
                        throw std::invalid_argument("didone: accent_text does not occur in the block");
                }

                LayerHandle& block = scene.text({
                    .text = join_lines(spec.lines),
                    .font = tokens.font.file,
                    .fontSize = tokens.normal_size,
                    .color = tokens.white,
                    .name = "didone-emphasis",
                });
                block.position(kCanvasWidth * 0.5f, kCanvasHeight * 0.5f);
                block.animatePosition(spec.in_frame, 15, chrononmotion::Vector3(0.f, 20.f, 0.f));
                block.animateOpacity(spec.in_frame, 15, 0.f, 1.f);

                const DidoneCameraPlan cam = didoneCameraPlanFor(2, spec.duration - spec.in_frame);
                author_camera_plan(scene, cam);
                break;
            }

            case DidoneTitlePreset::HeroStatement:
            case DidoneTitlePreset::WordFocusRack:
            case DidoneTitlePreset::CameraSlowPush:
            case DidoneTitlePreset::CameraPullReveal: {
                LayerHandle& background = scene.group("didone-bg");
                background.alive(spec.in_frame, spec.in_frame + spec.duration);

                if (spec.lines.empty() && !spec.custom_layout)
                    throw std::invalid_argument("didone: the block needs lines");

                LayerHandle& block = scene.text({
                    .text = join_lines(spec.lines),
                    .font = tokens.font.file,
                    .fontSize = tokens.hero_size,
                    .color = tokens.white,
                    .name = "didone-hero",
                });
                block.position(kCanvasWidth * 0.5f, kCanvasHeight * 0.5f);
                block.animatePosition(spec.in_frame, 14, chrononmotion::Vector3(0.f, 20.f, 0.f));
                block.animateOpacity(spec.in_frame, 14, 0.f, 1.f);

                const DidoneCameraPlan cam = didoneCameraPlanFor(3, spec.duration - spec.in_frame);
                author_camera_plan(scene, cam);
                break;
            }
        }

        return bar_rect;
    }

} // namespace chronontemplate
