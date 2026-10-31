#include "chronontemplate/fast_intro/FastIntroPack.hpp"

#include "chrononmotion/motion/Easing.hpp"

#include <algorithm>
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

    // ── v2 helpers ───────────────────────────────────────────────────────

    namespace {
        constexpr float kMinScale = 0.02f;
        constexpr float kMaxScale = 3.5f;
        float clampScale(float v) {
            if (v < kMinScale) return kMinScale;
            if (v > kMaxScale) return kMaxScale;
            return v;
        }
    }

    std::vector<FastIntroV2Choice> fastIntroV2Choices() {
        return {
            {FastIntroRecipe::OpeningPlate, "opening_plate_v1", "Dark cinematic opening plate", 120},
            {FastIntroRecipe::PunchStat, "punch_stat_v1", "Retro punch-stat with collage", 150},
            {FastIntroRecipe::WhipMatch, "whip_match_v1", "Parametric whip match-cut", 180},
            {FastIntroRecipe::ChapterCard, "chapter_card_v1", "Parametric chapter card", 150},
        };
    }

    int fastIntroV2DurationFrames(const FastIntroV2Spec& spec) {
        return spec.durationFrames;
    }

    LayerHandle& addFastIntroV2(TemplateScene& scene, const FastIntroV2Spec& spec) {
        if (spec.name.empty() || spec.font.empty())
            throw std::invalid_argument("addFastIntroV2: name and font are required");
        if (spec.durationFrames < 90 || spec.durationFrames > 400 ||
            spec.width <= 0.f || spec.height <= 0.f)
            throw std::invalid_argument("addFastIntroV2: invalid duration or canvas size");
        if (spec.topics.size() > 4)
            throw std::invalid_argument("addFastIntroV2: at most four topic chips");
        for (const auto& t : spec.topics)
            if (t.empty()) throw std::invalid_argument("addFastIntroV2: topic chips must not be empty");

        const int end = spec.durationFrames;
        const float cx = spec.width * 0.5f;
        const float cy = spec.height * 0.5f;
        const bool portrait = spec.height > spec.width;
        const float unit = portrait ? spec.width / 1080.f : spec.width / 1920.f;
        auto time = [fps = scene.fps()](int frame) {
            return static_cast<float>(frame) / fps;
        };

        // Every v2 recipe rides a slow push: no static plates.
        scene.camera().push(spec.cameraPush).between(0, end);

        if (spec.recipe == FastIntroRecipe::OpeningPlate) {
            if (spec.title.empty())
                throw std::invalid_argument("addFastIntroV2: opening plate needs a title");
            LayerHandle& root = scene.group(spec.name);
            root.alive(0, end);
            const auto parent = root.id();

            LayerHandle& ground = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, spec.height),
                .fillColor = spec.ground, .name = spec.name + "_ground"});
            ground.parent(parent).position(cx, cy).alive(0, end);

            // Soft accent aura behind the title (cheap: one radial disc).
            ShapeRadialGradient aura;
            aura.center = chrononmotion::Vector2(0.5f, 0.45f);
            aura.radius = 0.55f;
            aura.stops = {{0.0f, spec.accent, 0.28f}, {1.0f, spec.ground, 0.0f}};
            LayerHandle& glow = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width * 1.1f, spec.height * 1.1f),
                .fillColor = spec.accent, .name = spec.name + "_aura",
                .geometry = ShapeGeometry::Ellipse,
                .radialGradient = aura});
            glow.parent(parent).position(cx, cy).alive(0, end);
            glow.animateOpacity(0, 20, 0.f, 1.f);

            LayerHandle& kicker = scene.text(TextSpec{.text = spec.kicker, .font = spec.font,
                .fontSize = portrait ? 26.f : 30.f, .color = spec.accent,
                .name = spec.name + "_kicker"});
            kicker.parent(parent).position(cx, cy - 230.f * unit).alive(0, end);
            kicker.animateOpacity(0, 8, 0.f, 1.f);  // hook: visible by frame 8
            kicker.animatePosition(0, 10, chrononmotion::Vector3(0.f, 14.f, 0.f));

            LayerHandle& title = scene.text(TextSpec{.text = spec.title, .font = spec.font,
                .fontSize = portrait ? 76.f : 104.f, .color = "#F5F2EA",
                .name = spec.name + "_title",
                .shadow = TextShadowStyle{.color = "#000000", .opacity = 0.6f,
                    .blur = 10.f, .offset = chrononmotion::Vector2(0.f, 6.f)}});
            title.parent(parent).position(cx, cy - 70.f * unit).alive(0, end);
            title.animateOpacity(0, 10, 0.f, 1.f);
            auto& ts = title.layer().tracks.scale;
            ts.add(time(0), chrononmotion::Vector3(0.92f, 0.92f, 1.f),
                   chrononmotion::motion::Easing::easeOut());
            ts.add(time(12), chrononmotion::Vector3(1.f, 1.f, 1.f),
                   chrononmotion::motion::Easing::easeOut());

            if (!spec.chapterLabel.empty()) {
                LayerHandle& band = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(spec.width, 64.f * unit),
                    .fillColor = spec.accent, .name = spec.name + "_chapter_band"});
                band.parent(parent).position(cx, cy - 310.f * unit).alive(0, end);
                auto& bs = band.layer().tracks.scale;
                bs.add(time(0), chrononmotion::Vector3(kMinScale, 1.f, 1.f),
                       chrononmotion::motion::Easing::linear());
                bs.add(time(16), chrononmotion::Vector3(1.f, 1.f, 1.f),
                       chrononmotion::motion::Easing::easeOut());
                LayerHandle& label = scene.text(TextSpec{.text = spec.chapterLabel,
                    .font = spec.font, .fontSize = 30.f, .color = "#FFFFFF",
                    .name = spec.name + "_chapter_label"});
                label.parent(parent).position(cx, cy - 310.f * unit).alive(4, end);
                label.animateOpacity(4, 10, 0.f, 1.f);
            }

            if (!spec.subtitle.empty()) {
                LayerHandle& sub = scene.text(TextSpec{.text = spec.subtitle, .font = spec.font,
                    .fontSize = portrait ? 28.f : 34.f, .color = "#B9B4A8",
                    .name = spec.name + "_subtitle"});
                sub.parent(parent).position(cx, cy + 80.f * unit).alive(10, end);
                sub.animateOpacity(10, 12, 0.f, 1.f);
            }

            LayerHandle& rail = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width * 0.62f, 4.f),
                .fillColor = spec.accent, .name = spec.name + "_rail"});
            rail.parent(parent).position(cx, cy + 220.f * unit).alive(6, end);
            auto& rs = rail.layer().tracks.scale;
            rs.add(time(6), chrononmotion::Vector3(kMinScale, 1.f, 1.f),
                   chrononmotion::motion::Easing::linear());
            rs.add(time(20), chrononmotion::Vector3(1.f, 1.f, 1.f),
                   chrononmotion::motion::Easing::easeOut());

            LayerHandle& marker = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(16.f, 16.f),
                .fillColor = spec.accent, .name = spec.name + "_marker",
                .cornerRadius = 8.f, .geometry = ShapeGeometry::Ellipse});
            marker.parent(parent).position(cx + spec.width * 0.31f, cy + 220.f * unit).alive(6, end);
            marker.animatePosition(6, 38, chrononmotion::Vector3(-spec.width * 0.62f, 0.f, 0.f),
                                   chrononmotion::motion::Easing::easeInOut());
            marker.animateOpacity(6, 8, 0.f, 1.f);

            const float spacing = portrait ? spec.width * 0.30f : spec.width * 0.20f;
            for (std::size_t i = 0; i < spec.topics.size(); ++i) {
                const int in = 28 + static_cast<int>(i) * 6;
                const float x = cx + (static_cast<float>(i) -
                    (static_cast<float>(spec.topics.size()) - 1.f) * 0.5f) * spacing;
                const float pillW = static_cast<float>(spec.topics[i].size()) * 13.f + 52.f;
                LayerHandle& pill = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(pillW, 44.f),
                    .fillColor = "#1A1A1F", .name = spec.name + "_pill_" + std::to_string(i),
                    .cornerRadius = 22.f, .strokeColor = spec.accent, .strokeWidth = 1.5f});
                pill.parent(parent).position(x, cy + 150.f * unit).alive(in, end);
                pill.animateOpacity(in, 10, 0.f, 0.95f);
                LayerHandle& chip = scene.text(TextSpec{.text = spec.topics[i], .font = spec.font,
                    .fontSize = 22.f, .color = "#E8E2D4",
                    .name = spec.name + "_topic_" + std::to_string(i)});
                chip.parent(parent).position(x, cy + 150.f * unit).alive(in, end);
                chip.animateOpacity(in, 10, 0.f, 1.f);
                chip.animatePosition(in, 10, chrononmotion::Vector3(0.f, 18.f, 0.f));
            }
            return root;
        }

        if (spec.recipe == FastIntroRecipe::PunchStat) {
            if (spec.eraTitle.empty() || spec.statistic.empty() || spec.collagePath.empty())
                throw std::invalid_argument("addFastIntroV2: punch_stat needs eraTitle, statistic and collagePath");
            LayerHandle& root = scene.group(spec.name);
            root.alive(0, end);
            const auto parent = root.id();

            LayerHandle& ground = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, spec.height),
                .fillColor = spec.bgOuterColor, .name = spec.name + "_ground"});
            ground.parent(parent).position(cx, cy).alive(0, end);

            ShapeRadialGradient radGrad;
            radGrad.center = chrononmotion::Vector2(0.5f, 0.5f);
            radGrad.radius = 0.5f;
            radGrad.stops = {
                {0.00f, spec.bgCenterColor, 1.f}, {0.10f, "#FFC12E", 1.f},
                {0.18f, "#F79A16", 1.f}, {0.26f, "#EE7A10", 1.f},
                {0.34f, "#F08A14", 1.f}, {0.42f, "#D95E0B", 1.f},
                {0.52f, "#C24A08", 1.f}, {0.62f, "#B23A08", 1.f},
                {0.72f, "#8E2206", 1.f}, {0.85f, "#5E0D04", 1.f},
                {1.00f, spec.bgOuterColor, 1.f}};
            const float glowSize = std::max(spec.width, spec.height) * 1.2f;
            LayerHandle& disc = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(glowSize, glowSize),
                .fillColor = spec.bgCenterColor, .name = spec.name + "_radial_glow",
                .geometry = ShapeGeometry::Ellipse, .radialGradient = radGrad,
                .noiseAmount = 0.05f, .noiseSeed = 7u, .noiseSize = 2.5f});
            disc.parent(parent).position(cx, cy - 20.f).alive(0, end);

            // Geometric ring tunnel (the Python look, native and cheap):
            // 5 stroked ellipses expanding 1.0 -> 1.12 over the whole clip.
            for (int r = 0; r < 5; ++r) {
                const float frac = 0.30f + static_cast<float>(r) * 0.20f;
                LayerHandle& ring = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(glowSize * frac, glowSize * frac),
                    .fillColor = "#EE941F", .name = spec.name + "_ring_" + std::to_string(r),
                    .fillEnabled = false, .geometry = ShapeGeometry::Ellipse,
                    .strokeColor = "#EE941F", .strokeWidth = 10.f - static_cast<float>(r) * 1.2f});
                ring.parent(parent).position(cx, cy - 20.f).alive(0, end);
                ring.animateOpacity(0, 20, 0.f, 0.20f - static_cast<float>(r) * 0.02f);
                auto& rsc = ring.layer().tracks.scale;
                rsc.add(time(0), chrononmotion::Vector3(1.f, 1.f, 1.f),
                        chrononmotion::motion::Easing::linear());
                rsc.add(time(end), chrononmotion::Vector3(1.12f, 1.12f, 1.f),
                        chrononmotion::motion::Easing::linear());
            }

            const int eraEnd = std::min(46, end - 1);
            LayerHandle& era = scene.text(TextSpec{.text = spec.eraTitle, .font = spec.font,
                .fontSize = 320.f, .color = "#F5F1EA", .name = spec.name + "_era",
                .shadow = TextShadowStyle{.color = "#1C0404", .opacity = 0.88f,
                    .blur = 12.f, .offset = chrononmotion::Vector2(8.f, 14.f)}});
            era.parent(parent).position(cx, cy).alive(0, eraEnd);
            auto& es = era.layer().tracks.scale;
            es.add(time(0), chrononmotion::Vector3(1.f, 1.f, 1.f),
                   chrononmotion::motion::Easing::linear());
            es.add(time(std::min(38, eraEnd)), chrononmotion::Vector3(1.14f, 1.14f, 1.f),
                   chrononmotion::motion::Easing::linear());
            if (eraEnd > 38)
                es.add(time(eraEnd), chrononmotion::Vector3(1.32f, 1.32f, 1.f),
                       chrononmotion::motion::Easing::easeIn());
            auto& eo = era.layer().tracks.opacity;
            eo.add(time(0), 1.f, chrononmotion::motion::Easing::linear());
            eo.add(time(std::min(38, eraEnd)), 1.f, chrononmotion::motion::Easing::linear());
            eo.add(time(eraEnd), 0.f, chrononmotion::motion::Easing::easeOut());

            const int statIn = 38;
            const int statOut = std::min(121, end - 1);
            if (statOut > statIn) {
                LayerHandle& stat = scene.text(TextSpec{.text = spec.statistic, .font = spec.font,
                    .fontSize = 340.f, .color = "#F5F1EA", .name = spec.name + "_stat",
                    .shadow = TextShadowStyle{.color = "#1C0404", .opacity = 0.90f,
                        .blur = 14.f, .offset = chrononmotion::Vector2(12.f, 16.f)}});
                stat.parent(parent).position(cx, cy).alive(statIn, statOut);
                stat.animatePosition(statIn, std::min(44, statOut - statIn),
                    chrononmotion::Vector3(320.f, 140.f, 0.f),
                    chrononmotion::motion::Easing::easeOut());
                auto& ss = stat.layer().tracks.scale;
                ss.add(time(statIn), chrononmotion::Vector3(clampScale(3.4f), clampScale(3.4f), 1.f),
                       chrononmotion::motion::Easing::easeOut());
                if (statOut >= 82) {
                    ss.add(time(48), chrononmotion::Vector3(2.75f, 2.75f, 1.f),
                           chrononmotion::motion::Easing::easeOut());
                    ss.add(time(60), chrononmotion::Vector3(2.2f, 2.2f, 1.f),
                           chrononmotion::motion::Easing::easeOut());
                    ss.add(time(72), chrononmotion::Vector3(1.5f, 1.5f, 1.f),
                           chrononmotion::motion::Easing::easeOut());
                    ss.add(time(82), chrononmotion::Vector3(1.f, 1.f, 1.f),
                           chrononmotion::motion::Easing::easeOut());
                }
                ss.add(time(statOut), chrononmotion::Vector3(0.94f, 0.94f, 1.f),
                       chrononmotion::motion::Easing::linear());
                auto& so = stat.layer().tracks.opacity;
                so.add(time(statIn), 0.f, chrononmotion::motion::Easing::linear());
                so.add(time(statIn + 1), 1.f, chrononmotion::motion::Easing::easeOut());
                so.add(time(statOut), 0.f, chrononmotion::motion::Easing::easeOut());
            }

            const int colIn = 88;
            if (end > colIn) {
                LayerHandle& collage = scene.image(ImageSpec{
                    .path = spec.collagePath, .name = spec.name + "_collage",
                    .fit = ImageFitMode::Contain,
                    .targetSize = chrononmotion::Vector2(
                        spec.width * 0.88f, spec.height * 0.96f)});
                collage.parent(parent).position(cx, cy - 15.f).alive(colIn, end);
                auto& cs = collage.layer().tracks.scale;
                cs.add(time(colIn), chrononmotion::Vector3(clampScale(3.2f), clampScale(3.2f), 1.f),
                       chrononmotion::motion::Easing::easeOut());
                cs.add(time(std::min(99, end)), chrononmotion::Vector3(2.4f, 2.4f, 1.f),
                       chrononmotion::motion::Easing::easeOut());
                if (end > 120)
                    cs.add(time(120), chrononmotion::Vector3(1.42f, 1.42f, 1.f),
                           chrononmotion::motion::Easing::easeOut());
                if (end > 150)
                    cs.add(time(150), chrononmotion::Vector3(1.04f, 1.04f, 1.f),
                           chrononmotion::motion::Easing::easeOut());
                else if (end > 120)
                    cs.add(time(end - 1), chrononmotion::Vector3(1.04f, 1.04f, 1.f),
                           chrononmotion::motion::Easing::easeOut());
                cs.add(time(end), chrononmotion::Vector3(1.f, 1.f, 1.f),
                       chrononmotion::motion::Easing::linear());
                auto& co = collage.layer().tracks.opacity;
                co.add(time(colIn), 0.f, chrononmotion::motion::Easing::linear());
                co.add(time(std::min(colIn + 2, end)), 1.f, chrononmotion::motion::Easing::easeOut());
            }

            if (!spec.closingTitle.empty() && end > 138) {
                LayerHandle& closing = scene.text(TextSpec{.text = spec.closingTitle,
                    .font = spec.font, .fontSize = 80.f, .color = "#F5F1EA",
                    .name = spec.name + "_closing"});
                closing.parent(parent).position(cx, cy + 390.f).alive(138, end);
                closing.animatePosition(138, std::min(22, end - 138),
                    chrononmotion::Vector3(0.f, 90.f, 0.f),
                    chrononmotion::motion::Easing::easeOut());
                closing.animateOpacity(138, std::min(12, end - 138), 0.f, 1.f);
            }
            return root;
        }

        if (spec.recipe == FastIntroRecipe::WhipMatch) {
            if (spec.plates.size() < 4 || spec.plates.size() > 16)
                throw std::invalid_argument("addFastIntroV2: whip_match needs 4-16 plates");
            if (spec.whipQuickFrames < 5 || spec.whipQuickFrames > 12 ||
                spec.whipHoldFrames < 10 || spec.whipHoldFrames > 30)
                throw std::invalid_argument("addFastIntroV2: invalid whip timing");
            LayerHandle& root = scene.group(spec.name);
            root.alive(0, end);
            const auto parent = root.id();
            LayerHandle& ground = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, spec.height),
                .fillColor = "#000000", .name = spec.name + "_ground"});
            ground.parent(parent).position(cx, cy).alive(0, end);

            // Full-bleed Cover plates: no pillarbox in v2 (fixes black bars).
            int cursor = 0;
            for (std::size_t i = 0; i < spec.plates.size(); ++i) {
                const bool hold = (i % 3 == 1);
                int len = hold ? spec.whipHoldFrames : spec.whipQuickFrames;
                if (i == spec.plates.size() - 1) len = std::max(len, end - cursor);
                const int s = cursor;
                const int e = std::min(s + len, end);
                if (s >= end) break;
                const float dir = (i % 2 == 0) ? 1.f : -1.f;
                LayerHandle& shot = scene.image(ImageSpec{
                    .path = spec.plates[i], .name = spec.name + "_shot_" + std::to_string(i),
                    .fit = ImageFitMode::Cover,
                    .targetSize = chrononmotion::Vector2(spec.width, spec.height)});
                shot.parent(parent).position(cx, cy).alive(s, e);
                // Whip in from the side, drift slightly, whip out.
                shot.animatePosition(s, std::min(6, std::max(1, e - s)),
                    chrononmotion::Vector3(dir * 1200.f, 0.f, 0.f),
                    chrononmotion::motion::Easing::easeOut());
                shot.animateOpacity(s, std::min(3, std::max(1, e - s)), 0.f, 1.f);
                cursor += len;
                if (cursor >= end) break;
            }
            // Vignette: one radial disc, no baked PNG.
            ShapeRadialGradient vig;
            vig.center = chrononmotion::Vector2(0.5f, 0.5f);
            vig.radius = 0.75f;
            vig.stops = {{0.0f, "#000000", 0.0f}, {0.7f, "#000000", 0.0f},
                         {1.0f, "#000000", 0.55f}};
            LayerHandle& vignette = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width * 1.2f, spec.height * 1.2f),
                .fillColor = "#000000", .name = spec.name + "_vignette",
                .geometry = ShapeGeometry::Ellipse, .radialGradient = vig});
            vignette.parent(parent).position(cx, cy).alive(0, end);
            return root;
        }

        // ChapterCard (parametric disaster-chapter successor).
        if (spec.title.empty())
            throw std::invalid_argument("addFastIntroV2: chapter card needs a title");
        {
            LayerHandle& root = scene.group(spec.name);
            root.alive(0, end);
            const auto parent = root.id();
            LayerHandle& ground = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, spec.height),
                .fillColor = "#060608", .name = spec.name + "_ground"});
            ground.parent(parent).position(cx, cy).alive(0, end);

            LayerHandle& band = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, 110.f),
                .fillColor = "#C40A1F", .name = spec.name + "_band"});
            band.parent(parent).position(cx, cy - 20.f).alive(0, end);
            auto& bs = band.layer().tracks.scale;
            bs.add(time(0), chrononmotion::Vector3(kMinScale, 1.f, 1.f),
                   chrononmotion::motion::Easing::linear());
            bs.add(time(18), chrononmotion::Vector3(1.f, 1.f, 1.f),
                   chrononmotion::motion::Easing::easeOut());

            const std::string label =
                spec.chapterLabel.empty() ? std::string("CHAPTER 1") : spec.chapterLabel;
            LayerHandle& chapter = scene.text(TextSpec{.text = label, .font = spec.font,
                .fontSize = 44.f, .color = "#FF8A94", .name = spec.name + "_chapter"});
            chapter.parent(parent).position(cx, cy - 220.f).alive(4, end);
            chapter.animateOpacity(4, 10, 0.f, 1.f);

            // Single glow declaration on the title (was 3 duplicated layers).
            LayerHandle& title = scene.text(TextSpec{.text = spec.title, .font = spec.font,
                .fontSize = portrait ? 52.f : 64.f, .color = "#FFF8F5",
                .name = spec.name + "_title",
                .glow = TextGlowStyle{.color = "#FF2638", .radius = 18.f, .intensity = 0.5f}});
            title.parent(parent).position(cx, cy - 20.f).alive(8, end);
            title.animateOpacity(8, 12, 0.f, 1.f);
            auto& tls = title.layer().tracks.scale;
            tls.add(time(8), chrononmotion::Vector3(0.94f, 0.94f, 1.f),
                    chrononmotion::motion::Easing::linear());
            tls.add(time(26), chrononmotion::Vector3(1.f, 1.f, 1.f),
                    chrononmotion::motion::Easing::easeOut());

            if (!spec.subtitle.empty()) {
                LayerHandle& sub = scene.text(TextSpec{.text = spec.subtitle, .font = spec.font,
                    .fontSize = 30.f, .color = "#C9C2B4", .name = spec.name + "_subtitle"});
                sub.parent(parent).position(cx, cy + 180.f).alive(16, end);
                sub.animateOpacity(16, 12, 0.f, 1.f);
            }

            for (int p = 0; p < 12; ++p) {
                const float px = cx - spec.width * 0.45f +
                    static_cast<float>((p * 173) % 100) / 100.f * spec.width * 0.9f;
                const float py = cy + static_cast<float>((p * 97) % 100) / 100.f * 300.f - 150.f;
                LayerHandle& dot = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(4.f + static_cast<float>(p % 3) * 3.f,
                                                 4.f + static_cast<float>(p % 3) * 3.f),
                    .fillColor = "#E8B98A", .name = spec.name + "_dust_" + std::to_string(p),
                    .geometry = ShapeGeometry::Ellipse});
                dot.parent(parent).position(px, py).alive(0, end);
                dot.animatePosition(0, end, chrononmotion::Vector3(30.f, -60.f, 0.f),
                    chrononmotion::motion::Easing::linear());
                dot.animateOpacity(0, 20, 0.f, 0.5f);
            }
            return root;
        }
    }

} // namespace chronontemplate::fast_intro
