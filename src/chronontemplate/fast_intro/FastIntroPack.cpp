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

    LayerHandle& addRetroStatCollage(TemplateScene& scene, const RetroStatCollageSpec& spec) {
        if (spec.name.empty() || spec.eraTitle.empty() || spec.statistic.empty() ||
            spec.font.empty() || spec.collagePath.empty())
            throw std::invalid_argument("addRetroStatCollage: name, eraTitle, statistic, font and collagePath are required");
        if (spec.durationFrames < 60 || spec.width <= 0.f || spec.height <= 0.f)
            throw std::invalid_argument("addRetroStatCollage: invalid duration or canvas size");

        const float fps = scene.fps();
        auto time = [fps](int frame) {
            return static_cast<float>(frame) / fps;
        };

        const int end = spec.durationFrames;
        const float cx = spec.width * 0.5f;
        const float cy = spec.height * 0.5f;
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, end);
        const auto parent = root.id();

        // 1. Base Ground
        LayerHandle& ground = scene.shape(ShapeSpec{
            .size = chrononmotion::Vector2(spec.width, spec.height),
            .fillColor = spec.bgOuterColor,
            .name = spec.name + "_ground"
        });
        ground.parent(parent).position(cx, cy).alive(0, end);

        // 2. Warm radial background: luminous yellow core, soft concentric
        //    orange bands and deep red edges. The reference's circles are soft
        //    and deep, so they live in the gradient stops instead of hard
        //    stroked rings, with only a very light noise texture on top.
        ShapeRadialGradient radGrad;
        radGrad.center = chrononmotion::Vector2(0.5f, 0.5f);
        radGrad.radius = 0.5f;
        radGrad.stops = {
            {0.00f, spec.bgCenterColor, 1.f},
            {0.10f, "#FFC12E", 1.f},
            {0.18f, "#F79A16", 1.f},
            {0.26f, "#EE7A10", 1.f},
            {0.34f, "#F08A14", 1.f},
            {0.42f, "#D95E0B", 1.f},
            {0.52f, "#C24A08", 1.f},
            {0.62f, "#B23A08", 1.f},
            {0.72f, "#8E2206", 1.f},
            {0.85f, "#5E0D04", 1.f},
            {1.00f, spec.bgOuterColor, 1.f}
        };

        const float glowSize = std::max(spec.width, spec.height) * 1.4f;
        LayerHandle& radialDisc = scene.shape(ShapeSpec{
            .size = chrononmotion::Vector2(glowSize, glowSize),
            .fillColor = spec.bgCenterColor,
            .name = spec.name + "_radial_glow",
            .geometry = ShapeGeometry::Ellipse,
            .radialGradient = radGrad,
            .noiseAmount = 0.06f,
            .noiseSeed = 7u,
            .noiseSize = 2.5f
        });
        radialDisc.parent(parent).position(cx, cy - 20.f).alive(0, end);

        // 3. Era Title ("1990s") - frames 0 to 46
        LayerHandle& era = scene.text(TextSpec{
            .text = spec.eraTitle,
            .font = spec.font,
            .fontSize = spec.eraFontSize,
            .color = "#F5F1EA",
            .name = spec.name + "_era",
            .shadow = TextShadowStyle{
                .color = "#1C0404",
                .opacity = 0.88f,
                .blur = 12.f,
                .offset = chrononmotion::Vector2(8.f, 14.f)
            }
        });
        era.parent(parent).position(cx, cy).alive(0, 46);
        auto& eraScale = era.layer().tracks.scale;
        eraScale.add(time(0), chrononmotion::Vector3(1.f, 1.f, 1.f), chrononmotion::motion::Easing::linear());
        eraScale.add(time(38), chrononmotion::Vector3(1.14f, 1.14f, 1.f), chrononmotion::motion::Easing::linear());
        eraScale.add(time(46), chrononmotion::Vector3(1.45f, 1.45f, 1.f), chrononmotion::motion::Easing::easeIn());
        auto& eraOpacity = era.layer().tracks.opacity;
        eraOpacity.add(time(0), 1.f, chrononmotion::motion::Easing::linear());
        eraOpacity.add(time(38), 1.f, chrononmotion::motion::Easing::linear());
        eraOpacity.add(time(46), 0.f, chrononmotion::motion::Easing::easeOut());

        // 4. Giant Statistic Number ("37.7 M") - frames 38 to 121.
        //    Crash zoom that crosses the screen as a white mass, still
        //    overflowing the borders at frame 60 (2.0s), fully legible at
        //    frame 82 (2.75s), then partially visible behind the collage
        //    through the transition until frame 121 (4.0s).
        LayerHandle& stat = scene.text(TextSpec{
            .text = spec.statistic,
            .font = spec.font,
            .fontSize = spec.statisticFontSize,
            .color = "#F5F1EA",
            .name = spec.name + "_stat",
            .shadow = TextShadowStyle{
                .color = "#1C0404",
                .opacity = 0.90f,
                .blur = 14.f,
                .offset = chrononmotion::Vector2(12.f, 16.f)
            }
        });
        stat.parent(parent).position(cx, cy).alive(38, 121);
        stat.animatePosition(38, 44, chrononmotion::Vector3(320.f, 140.f, 0.f), chrononmotion::motion::Easing::easeOut());
        auto& statScale = stat.layer().tracks.scale;
        statScale.add(time(38), chrononmotion::Vector3(spec.statisticScaleIn, spec.statisticScaleIn, 1.f), chrononmotion::motion::Easing::easeOut());
        statScale.add(time(48), chrononmotion::Vector3(4.6f, 4.6f, 1.f), chrononmotion::motion::Easing::easeOut());
        statScale.add(time(60), chrononmotion::Vector3(2.7f, 2.7f, 1.f), chrononmotion::motion::Easing::easeOut());
        statScale.add(time(72), chrononmotion::Vector3(1.6f, 1.6f, 1.f), chrononmotion::motion::Easing::easeOut());
        statScale.add(time(82), chrononmotion::Vector3(1.0f, 1.0f, 1.f), chrononmotion::motion::Easing::easeOut());
        statScale.add(time(121), chrononmotion::Vector3(0.92f, 0.92f, 1.f), chrononmotion::motion::Easing::linear());
        auto& statOpacity = stat.layer().tracks.opacity;
        statOpacity.add(time(38), 0.f, chrononmotion::motion::Easing::linear());
        statOpacity.add(time(39), 1.f, chrononmotion::motion::Easing::easeOut());
        statOpacity.add(time(82), 1.f, chrononmotion::motion::Easing::linear());
        statOpacity.add(time(90), 0.75f, chrononmotion::motion::Easing::linear());
        statOpacity.add(time(108), 0.5f, chrononmotion::motion::Easing::linear());
        statOpacity.add(time(121), 0.f, chrononmotion::motion::Easing::easeOut());

        // 5. Character Ensemble Collage - frames 88 to end. Enters from an
        //    extreme close-up and pulls back to 88% of the frame width,
        //    integrated directly with the background (no mask, no halo).
        LayerHandle& collage = scene.image(ImageSpec{
            .path = spec.collagePath,
            .name = spec.name + "_collage",
            .fit = ImageFitMode::Contain,
            .targetSize = chrononmotion::Vector2(spec.width * spec.collageTargetWidthRatio, spec.height * 0.96f)
        });
        collage.parent(parent).position(cx, cy - 15.f).alive(88, end);
        auto& collageScale = collage.layer().tracks.scale;
        collageScale.add(time(88), chrononmotion::Vector3(spec.collageScaleIn, spec.collageScaleIn, 1.f), chrononmotion::motion::Easing::easeOut());
        collageScale.add(time(99), chrononmotion::Vector3(2.4f, 2.4f, 1.f), chrononmotion::motion::Easing::easeOut());
        collageScale.add(time(120), chrononmotion::Vector3(1.42f, 1.42f, 1.f), chrononmotion::motion::Easing::easeOut());
        collageScale.add(time(150), chrononmotion::Vector3(1.04f, 1.04f, 1.f), chrononmotion::motion::Easing::easeOut());
        collageScale.add(time(162), chrononmotion::Vector3(1.f, 1.f, 1.f), chrononmotion::motion::Easing::easeOut());
        collageScale.add(time(end), chrononmotion::Vector3(1.f, 1.f, 1.f), chrononmotion::motion::Easing::linear());
        auto& collageOpacity = collage.layer().tracks.opacity;
        collageOpacity.add(time(88), 0.f, chrononmotion::motion::Easing::linear());
        collageOpacity.add(time(90), 1.f, chrononmotion::motion::Easing::easeOut());

        // 6. Optional Closing Title / Banner - frames 138 to end
        if (!spec.closingTitle.empty()) {
            LayerHandle& closing = scene.text(TextSpec{
                .text = spec.closingTitle,
                .font = spec.font,
                .fontSize = spec.closingFontSize,
                .color = "#F5F1EA",
                .name = spec.name + "_closing",
                .shadow = TextShadowStyle{
                    .color = "#1F0A06",
                    .opacity = 0.90f,
                    .blur = 6.f,
                    .offset = chrononmotion::Vector2(4.f, 8.f)
                }
            });
            closing.parent(parent).position(cx, cy + 390.f).alive(138, end);
            closing.animatePosition(138, 22, chrononmotion::Vector3(0.f, 90.f, 0.f), chrononmotion::motion::Easing::easeOut());
            closing.animateOpacity(138, 12, 0.f, 1.f);
        }

        return root;
    }

} // namespace chronontemplate::fast_intro
