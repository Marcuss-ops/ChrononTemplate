#include "chronontemplate/web/ArticleEvidenceReveal.hpp"

#include "chronontemplate/core/NativePrimitives.hpp"

#include <algorithm>
#include <set>
#include <stdexcept>

namespace chronontemplate::web {
namespace {
using Json = nlohmann::json;
constexpr int W = 1920, H = 1080, FPS = 30, FRAMES = 240;

Json text(const std::string& id, const std::string& value, float x, float y,
          float w, float h, float size, const std::string& font,
          const std::string& color, int start = 0, int duration = FRAMES) {
    return {{"id", id}, {"type", "text"}, {"text", value},
            {"position", {x + w * .5f, y + h * .5f, 0.f}}, {"size", {w, h}},
            {"enable_3d", true}, {"start_frame", start}, {"duration_frames", duration},
            {"style", {{"font", font}, {"font_size", size}, {"fill", color}, {"text_align", "left"}}}};
}

Json revealTrack(int start, int end) {
    return {{"tracks", Json::array({
        {{"property", "opacity"}, {"easing", "out_cubic"}, {"keyframes", Json::array({
            {{"frame", 0}, {"value", 0.0}}, {{"frame", start}, {"value", 0.0}},
            {{"frame", end}, {"value", 1.0}}})}},
        {{"property", "position_y"}, {"easing", "out_cubic"}, {"keyframes", Json::array({
            {{"frame", 0}, {"value", 24.0}}, {{"frame", start}, {"value", 24.0}},
            {{"frame", end}, {"value", 0.0}}})}}})}};
}

Json blurContext(const std::string& id) {
    Json selector = {{"id", id + "_all"}, {"unit", "character"}, {"shape", "square"},
                     {"order", "forward"}, {"combine", "replace"}, {"exclude_spaces", false}};
    selector["start"] = {{"keyframes", Json::array({{{"frame", 0}, {"value", 0.0}}})},
                          {"easing", "linear"}};
    selector["end"] = {{"keyframes", Json::array({{{"frame", 0}, {"value", 100.0}}})},
                        {"easing", "linear"}};
    return {{"id", id + "_context_blur"}, {"selectors", Json::array({selector})},
            {"properties", Json::array({{{"property", "blur"}, {"easing", "linear"},
                {"keyframes", {{{"frame", 0}, {"value", 0.0}},
                                {{"frame", 135}, {"value", 0.0}},
                                {{"frame", 239}, {"value", 1.7}}}}}})}};
}

} // namespace

Json buildArticleEvidenceRevealPlan(const ArticleEvidenceSpec& spec,
                                    const WebTextLayout& layout) {
    if (spec.title.empty() || spec.bodyText.empty() || spec.highlightedPhrase.empty() ||
        spec.keyPoints.size() != 3 || layout.source != spec.bodyText || layout.lines.empty())
        throw std::invalid_argument("article evidence scene needs matching laid-out text and three key points");
    const auto phraseStart = spec.bodyText.find(spec.highlightedPhrase);
    if (phraseStart == std::string::npos ||
        spec.bodyText.find(spec.highlightedPhrase, phraseStart + 1) != std::string::npos)
        throw std::invalid_argument("highlighted phrase must occur exactly once in article text");
    const auto segments = resolveWebTextSpan(layout, phraseStart,
                                               phraseStart + spec.highlightedPhrase.size());
    if (segments.empty()) throw std::invalid_argument("highlight phrase has no shaped glyph geometry");
    const std::set<std::size_t> focusLines = [&] {
        std::set<std::size_t> lines;
        for (const auto& segment : segments) lines.insert(segment.lineIndex);
        return lines;
    }();

    const bool serif = spec.typography == ArticleTypography::ScientificSerif;
    const std::string expectedFont = serif ? "assets/fonts/PlayfairDisplay.ttf" : "assets/fonts/Inter-Regular.ttf";
    if (layout.fontPath != expectedFont)
        throw std::invalid_argument("text shaping font must match the selected article typography");
    const std::string font = layout.fontPath;
    const std::string bold = serif ? "assets/fonts/PlayfairDisplay-Bold.ttf" : "assets/fonts/Inter-Bold.ttf";
    Json layers = Json::array({
        {{"id", "article_paper"}, {"type", "color"}, {"color", native::Material::rgba("#F7F6F2")},
         {"size", {W, H}}, {"screen_space", true}, {"start_frame", 0}, {"duration_frames", FRAMES}},
        {{"id", "article_top_rule"}, {"type", "shape"}, {"size", {W, 5}},
         {"position", {W * .5f, 2.5f, 0.f}}, {"shape", {{"type", "rect"}, {"fill", native::Material::rgba("#26384A")}}},
         {"start_frame", 0}, {"duration_frames", FRAMES}}
    });
    layers.push_back(text("article_section", spec.section, 120.f, 74.f, 900.f, 28.f,
                          18.f, bold, "#627080"));
    layers.push_back(text("article_title", spec.title, 120.f, 122.f, 1600.f, 70.f,
                          48.f, bold, "#20252B"));
    layers.push_back(text("article_byline", spec.byline, 120.f, 214.f, 1000.f, 28.f,
                          17.f, font, "#6D747B"));
    layers.push_back({{"id", "article_divider"}, {"type", "shape"}, {"size", {1680, 2}},
                      {"position", {960, 275, 0}}, {"shape", {{"type", "rect"}, {"fill", native::Material::rgba("#D8D7D1")}}},
                      {"start_frame", 0}, {"duration_frames", FRAMES}});

    for (std::size_t i = 0; i < layout.lines.size(); ++i) {
        const auto& line = layout.lines[i];
        if (line.x < 80.f || line.x + line.width > W - 80.f || line.top < 280.f ||
            line.top + line.lineHeight > 850.f)
            throw std::invalid_argument("article text layout falls outside the page canvas");
        Json layer = text("article_body_line_" + std::to_string(i), line.text,
                          line.x, line.top, std::max(1.f, line.width + 2.f),
                          line.lineHeight, layout.fontSize, font, "#343A40");
        if (!focusLines.contains(i)) layer["text_animators"] = Json::array({blurContext("body_" + std::to_string(i))});
        layers.push_back(std::move(layer));
    }

    for (std::size_t i = 0; i < segments.size(); ++i) {
        const auto& s = segments[i];
        // Each line segment is its own native brush band. Its reveal starts at
        // 90s-equivalent frame and ends in sequence with the other line bands.
        const int begin = 90 + static_cast<int>(i) * 9;
        const int end = begin + 24;
        layers.push_back({{"id", "evidence_marker_" + std::to_string(i)}, {"type", "shape"},
            {"size", {s.width + 12.f, s.height + 5.f}},
            {"position", {s.x + (s.width + 12.f) * .5f, s.y + s.height * .5f, 1.f}},
            {"enable_3d", true}, {"shape", {{"type", "rect"}, {"fill", native::Material::rgba("#FFD11F", .64f)}}},
            {"start_frame", 0}, {"duration_frames", FRAMES},
            {"animation", revealTrack(begin, end)}});
    }

    layers.push_back(text("key_points_label", "KEY POINTS", 120.f, 878.f, 480.f, 28.f,
                          17.f, bold, "#596B7C", 180));
    for (std::size_t i = 0; i < spec.keyPoints.size(); ++i) {
        const float y = 918.f + static_cast<float>(i) * 42.f;
        layers.push_back({{"id", "key_point_bullet_" + std::to_string(i)}, {"type", "shape"},
            {"size", {12, 12}}, {"position", {128, y + 11, -1}}, {"enable_3d", true},
            {"shape", {{"type", "ellipse"}, {"fill", native::Material::rgba("#D9A827")}}}, {"start_frame", 0},
            {"duration_frames", FRAMES}, {"animation", revealTrack(180 + static_cast<int>(i) * 12,
                                                                       198 + static_cast<int>(i) * 12)}});
        layers.push_back(text("key_point_text_" + std::to_string(i), spec.keyPoints[i],
            152.f, y, 1500.f, 30.f, 21.f, font, "#343A40", 0));
        layers.back()["animation"] = revealTrack(180 + static_cast<int>(i) * 12,
                                                  198 + static_cast<int>(i) * 12);
    }

    const Json camera = native::Camera::perspective({0.f, 0.f, -1320.f}, {0.f, 0.f, 0.f}, 50.f);
    const Json cameraAnimation = native::Camera::animation(Json::array({
        native::Motion::track("camera_position_z", {{0, -1320.0}, {45, -1320.0},
            {90, -1260.0}, {180, -1260.0}, {239, -1260.0}}, "in_out_cubic")}));
    return native::TemplateComposition::renderPlan("article_evidence_reveal_v1", W, H, FPS,
        FRAMES, layers, camera, cameraAnimation,
        {{"path", spec.output}, {"format", "mp4"}, {"codec", "h264"}});
}

} // namespace chronontemplate::web
