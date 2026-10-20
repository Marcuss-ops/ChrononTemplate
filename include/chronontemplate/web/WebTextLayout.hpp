#pragma once

#include <chronon3d/text/font_engine.hpp>

#include <cstddef>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace chronontemplate::web {

/// All line measurements come from Chronon3D's HarfBuzz shaping result.
/// A callback keeps the template library renderer-link-free; production code
/// should bind it to FontEngine::shape_text (see chrononTextShaper).
using TextShaper = std::function<std::optional<chronon3d::GlyphRun>(std::string_view)>;

struct WebTextLine {
    std::string text;
    std::size_t sourceBegin{0};
    std::size_t sourceEnd{0};
    float x{0.f};
    float top{0.f};
    float baseline{0.f};
    float width{0.f};
    float ascent{0.f};
    float descent{0.f};
    float lineHeight{0.f};
    chronon3d::GlyphRun shaped{};
};

struct WebTextLayout {
    std::string source;
    std::string fontPath;
    float fontSize{0.f};
    std::vector<WebTextLine> lines;
    float width{0.f};
    float height{0.f};
};

/// A single physical-line segment of a semantic span, in pixel coordinates.
struct WebTextSegment {
    std::size_t lineIndex{0};
    float x{0.f};
    float y{0.f};
    float width{0.f};
    float height{0.f};
    std::size_t sourceBegin{0};
    std::size_t sourceEnd{0};
};

/// Wraps at whitespace using exact shaped candidate widths. The input's byte
/// offsets are retained so spans remain stable across UTF-8 text and wrapping.
[[nodiscard]] WebTextLayout layoutWebText(std::string_view text, float x, float y,
                                           float maxWidth, float lineSpacing,
                                           const std::string& fontPath, float fontSize,
                                           const TextShaper& shape);

/// Maps a source byte interval to one segment per intersected visual line.
/// Glyph clusters, rather than estimated character widths, determine x bounds.
[[nodiscard]] std::vector<WebTextSegment> resolveWebTextSpan(
    const WebTextLayout& layout, std::size_t byteStart, std::size_t byteEnd);

/// Convenience adapter for production callers that link Chronon3D.
[[nodiscard]] inline TextShaper chrononTextShaper(
    const chronon3d::FontEngine& engine, chronon3d::FontSpec font, float size,
    chronon3d::TextShaping shaping = {}) {
    return [&engine, font = std::move(font), size, shaping = std::move(shaping)](std::string_view text) {
        return engine.shape_text(text, font, size, shaping);
    };
}

} // namespace chronontemplate::web
