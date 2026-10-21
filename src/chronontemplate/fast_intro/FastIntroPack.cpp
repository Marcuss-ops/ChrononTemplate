#include "chronontemplate/fast_intro/FastIntroPack.hpp"

#include "chrononmotion/motion/Easing.hpp"

#include <stdexcept>

namespace chronontemplate::fast_intro {

    LayerHandle& addFastIntro(TemplateScene& scene, const FastIntroSpec& spec) {
        if (spec.name.empty() || spec.kicker.empty() || spec.title.empty() ||
            spec.subtitle.empty() || spec.font.empty() || spec.accent.empty())
            throw std::invalid_argument("addFastIntro: name, copy, font and accent are required");
        if (spec.topics.size() != 3)
            throw std::invalid_argument("addFastIntro: exactly three topic chips are required");
        for (const auto& topic : spec.topics)
            if (topic.empty()) throw std::invalid_argument("addFastIntro: topic chips must not be empty");
        if (spec.durationFrames < 48 || spec.durationFrames > 180 ||
            spec.width <= 0.f || spec.height <= 0.f)
            throw std::invalid_argument("addFastIntro: invalid duration or canvas size");

        constexpr int kRailIn = 8;
        constexpr int kTitleIn = 10;
        const int end = spec.durationFrames;
        const float cx = spec.width * 0.5f;
        const float cy = spec.height * 0.5f;
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, end);
        const auto parent = root.id();

        LayerHandle& ground = scene.shape(ShapeSpec{
            .size = chrononmotion::Vector2(spec.width, spec.height),
            .fillColor = "#F5F3EE", .name = spec.name + "_ground"});
        ground.parent(parent).position(cx, cy).alive(0, end);

        LayerHandle& rail = scene.shape(ShapeSpec{
            .size = chrononmotion::Vector2(spec.width * 0.62f, 4.f),
            .fillColor = spec.accent, .name = spec.name + "_rail"});
        rail.parent(parent).position(cx, cy + 210.f).alive(kRailIn, end);
        auto& railScale = rail.layer().tracks.scale;
        railScale.add(static_cast<float>(kRailIn) / scene.fps(),
                      chrononmotion::Vector3(.001f, 1.f, 1.f),
                      chrononmotion::motion::Easing::linear());
        railScale.add(static_cast<float>(kRailIn + 16) / scene.fps(),
                      chrononmotion::Vector3(1.f, 1.f, 1.f),
                      chrononmotion::motion::Easing::easeOut());

        LayerHandle& marker = scene.shape(ShapeSpec{
            .size = chrononmotion::Vector2(18.f, 18.f),
            .fillColor = spec.accent, .name = spec.name + "_marker",
            .cornerRadius = 9.f, .geometry = ShapeGeometry::Ellipse});
        marker.parent(parent).position(cx + spec.width * 0.31f, cy + 210.f).alive(kRailIn, end);
        marker.animatePosition(kRailIn, 38,
                               chrononmotion::Vector3(-spec.width * 0.62f, 0.f, 0.f),
                               chrononmotion::motion::Easing::easeInOut());
        marker.animateOpacity(kRailIn, 10, 0.f, 1.f);

        LayerHandle& kicker = scene.text(TextSpec{.text = spec.kicker, .font = spec.font,
            .fontSize = 26.f, .color = spec.accent, .name = spec.name + "_kicker"});
        kicker.parent(parent).position(cx, cy - 210.f).alive(0, end);
        kicker.animateOpacity(0, 10, 0.f, 1.f);
        kicker.animatePosition(0, 12, chrononmotion::Vector3(0.f, 18.f, 0.f));

        LayerHandle& title = scene.text(TextSpec{.text = spec.title, .font = spec.font,
            .fontSize = 100.f, .color = "#262521", .name = spec.name + "_title"});
        title.parent(parent).position(cx, cy - 65.f).alive(0, end);
        title.animateOpacity(kTitleIn, 14, 0.f, 1.f);
        title.animatePosition(kTitleIn, 16, chrononmotion::Vector3(0.f, 32.f, 0.f));

        LayerHandle& subtitle = scene.text(TextSpec{.text = spec.subtitle, .font = spec.font,
            .fontSize = 38.f, .color = "#77746E", .name = spec.name + "_subtitle"});
        subtitle.parent(parent).position(cx, cy + 75.f).alive(16, end);
        subtitle.animateOpacity(16, 12, 0.f, 1.f);

        const float chipSpacing = spec.width * 0.22f;
        for (std::size_t i = 0; i < spec.topics.size(); ++i) {
            const int in = 32 + static_cast<int>(i) * 6;
            const float x = cx + (static_cast<float>(i) - 1.f) * chipSpacing;
            LayerHandle& chip = scene.text(TextSpec{.text = spec.topics[i], .font = spec.font,
                .fontSize = 22.f, .color = "#5D5A54",
                .name = spec.name + "_topic_" + std::to_string(i)});
            chip.parent(parent).position(x, cy + 145.f).alive(in, end);
            chip.animateOpacity(in, 10, 0.f, 1.f);
        }
        return root;
    }

} // namespace chronontemplate::fast_intro
