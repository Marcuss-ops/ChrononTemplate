// ChrononTemplate — archival documentary timeline reveal.

#include "chronontemplate/documentary_effects/ArchivalTimelinePack.hpp"

#include "chronontemplate/backgrounds/BackgroundPack.hpp"
#include "chrononmotion/motion/Easing.hpp"

#include <random>
#include <stdexcept>

namespace chronontemplate::docfx {

    namespace {

        // Beat map (frames at 30 fps), mirroring the approved timing table.
        constexpr int kBgIn = 0;
        constexpr int kAxisIn = 15;    // 0.5 s: axis starts drawing left -> right
        constexpr int kAxisOut = 39;   // 1.3 s: axis complete
        constexpr int kPaperIn = 30;   // 1.0 s: clipping rises with fade
        constexpr int kPaperFrames = 30;
        constexpr int kYearIn = 54;    // 1.8 s
        constexpr int kYearFrames = 18;
        constexpr int kHeadlineIn = 66; // 2.2 s
        constexpr int kHeadlineFrames = 24;
        constexpr int kPushIn = 90;    // 3.0 s: slow push starts
        constexpr int kPushOut = 165;  // 5.5 s: hold to the end

        void validate(const ArchivalTimelineSpec& spec) {
            if (spec.year.empty() || spec.year.size() > 8)
                throw std::invalid_argument("archival timeline needs a 1..8 char year");
            if (spec.headline.empty() || spec.headline.size() > 64)
                throw std::invalid_argument("archival timeline needs a 1..64 char headline");
            if (spec.paperAsset.empty())
                throw std::invalid_argument("archival timeline needs a paper asset path");
            if (spec.paperWidth < 200.f || spec.paperWidth > 1600.f)
                throw std::invalid_argument("archival timeline paper width outside 200..1600");
            if (spec.lineY < 200.f || spec.lineY > 900.f)
                throw std::invalid_argument("archival timeline axis outside 200..900");
            if (spec.yearFontSize < 24.f || spec.yearFontSize > 200.f ||
                spec.headlineFontSize < 24.f || spec.headlineFontSize > 200.f)
                throw std::invalid_argument("archival timeline type size outside 24..200");
            if (spec.sceneFrames < 120 || spec.sceneFrames > 600)
                throw std::invalid_argument("archival timeline length outside 120..600 frames");
            if (spec.inFrame < 0 || spec.inFrame + 120 > spec.sceneFrames)
                throw std::invalid_argument("archival timeline inFrame leaves no room");
        }

    } // namespace

    float axisReveal(const ArchivalTimelineSpec& spec, int frame) {
        const int f = frame - spec.inFrame;
        if (f <= kAxisIn) return 0.f;
        if (f >= kAxisOut) return 1.f;
        const float t = static_cast<float>(f - kAxisIn) /
                        static_cast<float>(kAxisOut - kAxisIn);
        return t * t * (3.f - 2.f * t);
    }

    ArchivalTimelineLayers addArchivalTimelineReveal(
        TemplateScene& scene, const ArchivalTimelineSpec& spec) {
        validate(spec);
        const int endFrame = spec.inFrame + spec.sceneFrames;
        const float fps = scene.fps();
        ArchivalTimelineLayers out{};

        // Near-black plate plus hand-rolled drifting dust.
        // ArchiveDust is not used: its radial-gradient dots are not writable
        // by this emission path, while plain ellipses lower cleanly.
        {
            BackgroundSpec bg;
            bg.look = BackgroundLook::SolidTint;
            bg.ground = "#050505";
            bg.inFrame = spec.inFrame + kBgIn;
            bg.duration = spec.sceneFrames;
            bg.name = "archival_ground";
            BackgroundComposition comp = addBackground(scene, bg);
            out.background = comp.ground ? comp.ground->id() : MotionLayerId{0};

            std::mt19937 rng(1971u);
            std::uniform_real_distribution<float> unit(0.f, 1.f);
            for (int i = 0; i < 36; ++i) {
                const float x = unit(rng) * 1920.f;
                const float y = unit(rng) * 1080.f;
                const float size = 1.2f + unit(rng) * 2.5f;
                const float opacity = (i % 5 == 0) ? 0.55f : 0.26f;
                const int lifeIn = spec.inFrame + (i * 13) % 44;
                const int lifeOut = endFrame - 8;
                LayerHandle& dot = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(size, size),
                    .fillColor = "#8A8A8A",
                    .name = "archival_dust_" + std::to_string(i),
                    .geometry = ShapeGeometry::Ellipse});
                dot.position(x, y);
                dot.alive(spec.inFrame, endFrame);
                dot.animateOpacity(lifeIn, 8, 0.f, opacity,
                                   chrononmotion::motion::Easing::easeOut());
                dot.animateOpacity(lifeOut, 8, opacity, 0.f,
                                   chrononmotion::motion::Easing::easeIn());
                dot.animatePosition(lifeIn, lifeOut - lifeIn,
                                    chrononmotion::Vector3(
                                        (unit(rng) - 0.5f) * 42.f,
                                        -(7.f + unit(rng) * 28.f), 0.f),
                                    chrononmotion::motion::Easing::linear());
            }
        }

        // Paper clipping: desaturated plate, torn alpha edge, analog grain.
        // Its bottom edge rests on the axis; it rises ~40 px while revealing.
        const float paperH = spec.paperWidth * 1080.f / 1920.f;
        const float paperY = spec.lineY - paperH / 2.f;
        {
            // Torn alpha is baked in the asset pixels (the RoughenEdges
            // effect is not writable by the render-plan emitter).
            ImageFrameStyle frame;
            frame.saturation = 0.f;
            frame.contrast = 0.95f;
            frame.grain = 0.15f;
            frame.grainSeed = 1971u;
            LayerHandle& paper = scene.image(ImageSpec{
                .path = spec.paperAsset,
                .name = "archival_paper",
                .frame = frame,
                .fit = ImageFitMode::Cover,
                .targetSize = chrononmotion::Vector2(spec.paperWidth, paperH)});
            paper.position(960.f, paperY);
            paper.alive(spec.inFrame + kPaperIn, endFrame);
            paper.animatePosition(spec.inFrame + kPaperIn, kPaperFrames,
                                  chrononmotion::Vector3(0.f, 40.f, 0.f),
                                  chrononmotion::motion::Easing::easeOut());
            paper.animateOpacity(spec.inFrame + kPaperIn, kPaperFrames, 0.f, 1.f,
                                 chrononmotion::motion::Easing::easeOut());
            out.paper = paper.id();
        }

        // Timeline axis: full-width hairline drawing left -> right.
        // RenderPlan has no anchor field, so the anchored draw-on is
        // expressed as a position track mirroring the scale easing (the
        // CaptionsDataViz bar-growth idiom): pos.x(t) = 960*s(t) glues the
        // left end at x = 0 exactly as a left pivot would.
        {
            LayerHandle& axis = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(1920.f, 3.f),
                .fillColor = "#F5F0E6",
                .name = "archival_axis"});
            const auto t0 = static_cast<float>(spec.inFrame + kAxisIn) / fps;
            const auto t1 = static_cast<float>(spec.inFrame + kAxisOut) / fps;
            axis.position(0.f, spec.lineY);
            axis.alive(spec.inFrame + kAxisIn, endFrame);
            auto& scale = axis.layer().tracks.scale;
            scale.add(t0, chrononmotion::Vector3(0.001f, 1.f, 1.f),
                      chrononmotion::motion::Easing::linear());
            scale.add(t1, chrononmotion::Vector3(1.f, 1.f, 1.f),
                      chrononmotion::motion::Easing::easeInOut());
            auto& pos = axis.layer().tracks.position;
            pos.add(t0, chrononmotion::Vector3(0.f, spec.lineY, 0.f),
                    chrononmotion::motion::Easing::linear());
            pos.add(t1, chrononmotion::Vector3(960.f, spec.lineY, 0.f),
                    chrononmotion::motion::Easing::easeInOut());
            out.line = axis.id();
        }

        // Year: condensed white, small rise with fade.
        {
            LayerHandle& year = scene.text(TextSpec{
                .text = spec.year,
                .font = "ChrononTemplate/assets/fonts/Oswald-Medium.ttf",
                .fontSize = spec.yearFontSize,
                .color = "#FFFFFF",
                .name = "archival_year"});
            year.position(960.f, spec.lineY + 85.f);
            year.alive(spec.inFrame + kYearIn, endFrame);
            year.animatePosition(spec.inFrame + kYearIn, kYearFrames,
                                 chrononmotion::Vector3(0.f, 18.f, 0.f),
                                 chrononmotion::motion::Easing::easeOut());
            year.animateOpacity(spec.inFrame + kYearIn, kYearFrames, 0.f, 1.f,
                                chrononmotion::motion::Easing::easeOut());
            out.year = year.id();
        }

        // Headline: condensed bold dim gold over a dark-red offset copy.
        // TextShadowStyle is not writable by the render-plan emitter, so the
        // shadow is a real second text layer riding the same beats.
        {
            LayerHandle& shadow = scene.text(TextSpec{
                .text = spec.headline,
                .font = "ChrononTemplate/assets/fonts/Anton-Regular.ttf",
                .fontSize = spec.headlineFontSize,
                .color = "#4A1F16",
                .name = "archival_headline_shadow"});
            shadow.position(963.f, spec.lineY + 170.f);
            shadow.alive(spec.inFrame + kHeadlineIn, endFrame);
            shadow.animatePosition(spec.inFrame + kHeadlineIn, kHeadlineFrames,
                                   chrononmotion::Vector3(0.f, 30.f, 0.f),
                                   chrononmotion::motion::Easing::easeOut());
            shadow.animateOpacity(spec.inFrame + kHeadlineIn, kHeadlineFrames,
                                  0.f, 0.9f,
                                  chrononmotion::motion::Easing::easeOut());
            out.headlineShadow = shadow.id();
            LayerHandle& headline = scene.text(TextSpec{
                .text = spec.headline,
                .font = "ChrononTemplate/assets/fonts/Anton-Regular.ttf",
                .fontSize = spec.headlineFontSize,
                .color = spec.headlineColor,
                .name = "archival_headline"});
            headline.position(960.f, spec.lineY + 166.f);
            headline.alive(spec.inFrame + kHeadlineIn, endFrame);
            headline.animatePosition(spec.inFrame + kHeadlineIn, kHeadlineFrames,
                                     chrononmotion::Vector3(0.f, 30.f, 0.f),
                                     chrononmotion::motion::Easing::easeOut());
            headline.animateOpacity(spec.inFrame + kHeadlineIn, kHeadlineFrames,
                                    0.f, 1.f,
                                    chrononmotion::motion::Easing::easeOut());
            out.headline = headline.id();
        }

        // One slow push over the locked layout: the paper base never leaves
        // the axis because nothing but the rig moves.
        scene.camera().setFov(45.f);
        scene.camera().push(12.f).between(spec.inFrame + kPushIn,
                                          spec.inFrame + kPushOut);
        return out;
    }

    const char* archivalTimelineId() noexcept {
        return "docfx_archival_timeline_v1";
    }

} // namespace chronontemplate::docfx
