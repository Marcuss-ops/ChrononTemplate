#include "chronontemplate/web/WebTextLayout.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace chronontemplate::web {
namespace {

bool continuation(unsigned char c) { return (c & 0xc0U) == 0x80U; }

bool validUtf8Boundary(std::string_view text, std::size_t offset) {
    return offset == text.size() || !continuation(static_cast<unsigned char>(text[offset]));
}

bool whitespace(unsigned char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v';
}

struct Word { std::size_t begin, end; };

std::vector<Word> words(std::string_view text) {
    std::vector<Word> result;
    for (std::size_t i = 0; i < text.size();) {
        while (i < text.size() && whitespace(static_cast<unsigned char>(text[i]))) ++i;
        if (i == text.size()) break;
        const auto begin = i;
        while (i < text.size() && !whitespace(static_cast<unsigned char>(text[i]))) ++i;
        result.push_back({begin, i});
    }
    return result;
}

} // namespace

WebTextLayout layoutWebText(std::string_view text, float x, float y, float maxWidth,
                            float lineSpacing, const std::string& fontPath, float fontSize,
                            const TextShaper& shape) {
    if (!shape || text.empty() || !std::isfinite(x) || !std::isfinite(y) ||
        !std::isfinite(maxWidth) || maxWidth <= 0.f ||
        !std::isfinite(lineSpacing) || lineSpacing <= 0.f || fontPath.empty() ||
        !std::isfinite(fontSize) || fontSize <= 0.f)
        throw std::invalid_argument("web text layout needs text, shaper, and positive finite dimensions");

    WebTextLayout result;
    result.source.assign(text);
    result.fontPath = fontPath;
    result.fontSize = fontSize;
    const auto tokens = words(text);
    if (tokens.empty()) return result;

    auto addLine = [&](std::size_t begin, std::size_t end, float lineTop) {
        const std::string lineText(text.substr(begin, end - begin));
        auto glyphs = shape(lineText);
        if (!glyphs) throw std::runtime_error("Chronon3D could not shape web text line");
        if (!std::isfinite(glyphs->width) || glyphs->width < 0.f ||
            !std::isfinite(glyphs->ascent) || !std::isfinite(glyphs->descent) ||
            !std::isfinite(glyphs->line_height) || glyphs->line_height <= 0.f)
            throw std::runtime_error("Chronon3D returned invalid glyph metrics");
        result.width = std::max(result.width, glyphs->width);
        result.height = std::max(result.height, lineTop - y + glyphs->line_height);
        result.lines.push_back({lineText, begin, end, x, lineTop,
            lineTop + glyphs->ascent, glyphs->width, glyphs->ascent,
            glyphs->descent, glyphs->line_height, std::move(*glyphs)});
    };

    std::size_t lineBegin = tokens.front().begin;
    std::size_t lineEnd = tokens.front().end;
    auto firstShape = shape(text.substr(lineBegin, lineEnd - lineBegin));
    if (!firstShape) throw std::runtime_error("Chronon3D could not shape web text word");
    if (firstShape->width > maxWidth)
        throw std::invalid_argument("a word is wider than the web text column");

    for (std::size_t i = 1; i < tokens.size(); ++i) {
        const std::size_t candidateEnd = tokens[i].end;
        const std::string_view candidate = text.substr(lineBegin, candidateEnd - lineBegin);
        auto candidateShape = shape(candidate);
        if (!candidateShape) throw std::runtime_error("Chronon3D could not shape web text candidate");
        if (candidateShape->width <= maxWidth) {
            lineEnd = candidateEnd;
            continue;
        }
        addLine(lineBegin, lineEnd, y + static_cast<float>(result.lines.size()) * lineSpacing);
        lineBegin = tokens[i].begin;
        lineEnd = tokens[i].end;
        auto wordShape = shape(text.substr(lineBegin, lineEnd - lineBegin));
        if (!wordShape) throw std::runtime_error("Chronon3D could not shape web text word");
        if (wordShape->width > maxWidth)
            throw std::invalid_argument("a word is wider than the web text column");
    }
    addLine(lineBegin, lineEnd, y + static_cast<float>(result.lines.size()) * lineSpacing);
    return result;
}

std::vector<WebTextSegment> resolveWebTextSpan(const WebTextLayout& layout,
                                                std::size_t byteStart,
                                                std::size_t byteEnd) {
    if (byteStart >= byteEnd || byteEnd > layout.source.size() ||
        !validUtf8Boundary(layout.source, byteStart) || !validUtf8Boundary(layout.source, byteEnd))
        throw std::invalid_argument("web text span requires valid UTF-8 source byte boundaries");

    std::vector<WebTextSegment> segments;
    for (std::size_t li = 0; li < layout.lines.size(); ++li) {
        const auto& line = layout.lines[li];
        const std::size_t begin = std::max(byteStart, line.sourceBegin);
        const std::size_t end = std::min(byteEnd, line.sourceEnd);
        if (begin >= end) continue;

        struct Cluster { std::size_t start; float left; float right; };
        std::vector<Cluster> clusters;
        for (const auto& glyph : line.shaped.glyphs) {
            const std::size_t local = std::min<std::size_t>(glyph.cluster, line.text.size());
            const float left = std::min(glyph.x, glyph.x + glyph.advance_x);
            const float right = std::max(glyph.x, glyph.x + glyph.advance_x);
            auto found = std::find_if(clusters.begin(), clusters.end(), [local](const Cluster& c) {
                return c.start == local;
            });
            if (found == clusters.end()) clusters.push_back({local, left, right});
            else { found->left = std::min(found->left, left); found->right = std::max(found->right, right); }
        }
        std::sort(clusters.begin(), clusters.end(), [](const Cluster& a, const Cluster& b) {
            return a.start < b.start;
        });

        float left = line.width, right = 0.f;
        bool foundAny = false;
        const auto localBegin = begin - line.sourceBegin;
        const auto localEnd = end - line.sourceBegin;
        for (std::size_t ci = 0; ci < clusters.size(); ++ci) {
            const auto clusterEnd = ci + 1 < clusters.size() ? clusters[ci + 1].start : line.text.size();
            if (clusters[ci].start < localEnd && clusterEnd > localBegin) {
                left = std::min(left, clusters[ci].left);
                right = std::max(right, clusters[ci].right);
                foundAny = true;
            }
        }
        if (foundAny && right > left) {
            segments.push_back({li, line.x + left, line.top, right - left,
                                line.ascent + line.descent, begin, end});
        }
    }
    return segments;
}

} // namespace chronontemplate::web
