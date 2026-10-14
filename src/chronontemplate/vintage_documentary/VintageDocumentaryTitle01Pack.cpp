#include "chronontemplate/vintage_documentary/VintageDocumentaryTitle01Pack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <cmath>
#include <stdexcept>

namespace chronontemplate::vintage_documentary {

    namespace {

        void requireHex(const std::string& color, const char* what) {
            if (!chronon3d::render_plan::parse_hex_color(color))
                throw std::invalid_argument(std::string("title01: ") + what +
                                            " must be #RRGGBB");
        }

        void requireFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("title01: ") + what +
                                            " must be finite");
        }

        void validateGrain(const TitleGrain& grain, const char* what) {
            requireFinite(grain.amount, what);
            if (grain.amount < 0.f || grain.amount > 1.f)
                throw std::invalid_argument(std::string("title01: ") + what +
                                            " amount must be in [0,1]");
        }

        void validateLine(const TitleLine& line, const char* what) {
            const std::string prefix = std::string("title01: ") + what;
            if (line.text.empty())
                throw std::invalid_argument(prefix + " text is required");
            if (line.font.empty())
                throw std::invalid_argument(prefix + " font is required");
            requireFinite(line.fontSize, "fontSize");
            requireFinite(line.posX, "posX");
            requireFinite(line.posY, "posY");
            requireFinite(line.haloOpacity, "haloOpacity");
            requireFinite(line.haloBlur, "haloBlur");
            requireFinite(line.chromaSplit, "chromaSplit");
            requireFinite(line.distressAmount, "distressAmount");
            if (line.fontSize <= 0.f || line.fontSize > 512.f ||
                line.haloOpacity < 0.f || line.haloOpacity > 1.f ||
                line.haloBlur < 0.f || line.haloBlur > 256.f ||
                line.chromaSplit < 0.f || line.chromaSplit > 128.f ||
                line.distressAmount < 0.f || line.distressAmount > 1.f ||
                line.enterFrame < 0)
                throw std::invalid_argument(prefix + " is outside supported ranges");
            requireHex(line.color, "line color");
        }

        float at(int frame, float fps) {
            return static_cast<float>(frame) / fps;
        }

    } // namespace

    float titleHash01(std::uint64_t index, std::uint64_t seed) noexcept {
        std::uint64_t z = index + 0x9E3779B97F4A7C15ULL + seed * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        z = z ^ (z >> 31);
        return static_cast<float>(z >> 11) * (1.f / 9007199254740992.f);
    }

    float weaveOffsetX(int frame, float amplitude) noexcept {
        const double t = static_cast<double>(frame);
        constexpr double pi = 3.14159265358979323846;
        const double dx = std::sin(2.0 * pi * t / 37.0) +
            0.6 * std::sin(2.0 * pi * t / 13.0 + 1.7);
        return static_cast<float>(dx * static_cast<double>(amplitude));
    }

    float weaveOffsetY(int frame, float amplitude) noexcept {
        const double t = static_cast<double>(frame);
        constexpr double pi = 3.14159265358979323846;
        const double dy = 0.9 * std::sin(2.0 * pi * t / 29.0 + 0.6) +
            0.5 * std::sin(2.0 * pi * t / 11.0 + 2.9);
        return static_cast<float>(dy * static_cast<double>(amplitude));
    }

    float flickerLift(const TitleFlicker& flicker, int holdIndex, int frame) noexcept {
        const int holdStart = holdIndex * 3;
        if (holdStart >= flicker.flashFrame && holdStart < flicker.flashFrame + 6)
            return holdStart < flicker.flashFrame + 3 ? flicker.flashLift : 0.02f;
        // Same LCG stream as the RenderPlan generator (x0 = 1234567).
        std::uint64_t x = 1234567;
        for (int i = 0; i <= holdIndex; ++i)
            x = (1103515245ULL * x + 12345ULL) % 2147483648ULL;
        const float r = static_cast<float>(x) / 2147483648.f;
        (void)frame;
        return flicker.baseLift + r * flicker.variance;
    }

    VintageDocumentaryTitle01Layers addVintageDocumentaryTitle01Scene(
            TemplateScene& scene, const VintageDocumentaryTitle01Scene& spec) {
        if (spec.name.empty())
            throw std::invalid_argument("title01: scene name is required");
        validateLine(spec.small, "small line");
        validateLine(spec.main, "main line");
        validateLine(spec.script, "script line");
        validateGrain(spec.grain, "grain");
        validateGrain(spec.flickerGrain, "flickerGrain");
        requireFinite(spec.vignette.radius, "vignette.radius");
        requireFinite(spec.vignette.softness, "vignette.softness");
        requireFinite(spec.vignette.amount, "vignette.amount");
        requireFinite(spec.dust.opacity, "dust.opacity");
        requireFinite(spec.flicker.baseLift, "flicker.baseLift");
        requireFinite(spec.flicker.variance, "flicker.variance");
        requireFinite(spec.flicker.flashLift, "flicker.flashLift");
        requireFinite(spec.weave.amplitude, "weave.amplitude");
        requireFinite(spec.zoomFrom, "zoomFrom");
        requireFinite(spec.zoomTo, "zoomTo");
        if (spec.inFrame < 0 || spec.durationFrames < 1 || spec.durationFrames > 900 ||
            spec.vignette.radius < 0.f || spec.vignette.radius > 1.f ||
            spec.vignette.softness < 0.f || spec.vignette.softness > 1.f ||
            spec.vignette.amount < 0.f || spec.vignette.amount > 1.f ||
            spec.dust.count > 256 || spec.dust.opacity < 0.f || spec.dust.opacity > 1.f ||
            spec.flicker.baseLift < 0.f || spec.flicker.baseLift > 1.f ||
            spec.flicker.variance < 0.f || spec.flicker.variance > 1.f ||
            spec.flicker.flashLift < 0.f || spec.flicker.flashLift > 1.f ||
            spec.flicker.flashFrame < spec.inFrame ||
            spec.weave.amplitude < 0.f || spec.weave.amplitude > 8.f ||
            spec.zoomFrom <= 0.f || spec.zoomFrom > 4.f ||
            spec.zoomTo <= 0.f || spec.zoomTo > 4.f ||
            spec.exitStartFrame < spec.inFrame ||
            spec.exitStartFrame > spec.inFrame + spec.durationFrames ||
            spec.small.enterFrame > spec.inFrame + spec.durationFrames ||
            spec.main.enterFrame > spec.inFrame + spec.durationFrames ||
            spec.script.enterFrame > spec.inFrame + spec.durationFrames)
            throw std::invalid_argument("title01: scene is outside supported ranges");
        requireHex(spec.backgroundColor, "backgroundColor");
        const float canvasW = scene.canvas().x;
        const float canvasH = scene.canvas().y;
        const float fps = scene.fps();
        const int endFrame = spec.inFrame + spec.durationFrames;
        const int exitDuration = endFrame - spec.exitStartFrame;

        VintageDocumentaryTitle01Layers out{};
        using chrononmotion::motion::Easing;

        // ── 1. Near-black ground (grain seed rides the content request;
        // temporal animation is a render-side contract of TitleGrain) ──
        {
            ShapeSpec groundSpec{.size = scene.canvas(),
                                 .fillColor = spec.backgroundColor,
                                 .name = spec.name + "_bg_ground"};
            groundSpec.noiseAmount = spec.grain.amount;
            groundSpec.noiseSeed = spec.grain.seed;
            groundSpec.animatedNoise = spec.grain.animated;
            LayerHandle& ground = scene.shape(groundSpec);
            ground.position(canvasW * 0.5f, canvasH * 0.5f);
            ground.alive(spec.inFrame, endFrame);
            // Constant-valued track: forces per-frame evaluation so the
            // animated grain contract (seed, frame) is honoured by the
            // renderer instead of serving one frozen frame.
            ground.layer().tracks.opacity.add(at(spec.inFrame, fps), 1.f, Easing::linear());
            ground.layer().tracks.opacity.add(at(endFrame, fps), 1.f, Easing::linear());
            out.background = ground.id();

            ShapeRadialGradient vig;
            vig.center = chrononmotion::Vector2(0.5f, 0.5f);
            vig.radius = 0.5f;
            vig.stops = {{0.f, "#000000", 0.f},
                         {0.62f, "#000000", 0.f},
                         {1.f, "#000000", spec.vignette.amount}};
            ShapeSpec vigSpec{.size = chrononmotion::Vector2(canvasW * 1.6f, canvasH * 1.6f),
                              .fillColor = "#000000",
                              .name = spec.name + "_bg_vignette",
                              .geometry = ShapeGeometry::Ellipse,
                              .radialGradient = vig};
            vigSpec.noiseAmount = spec.flickerGrain.amount;
            vigSpec.noiseSeed = spec.flickerGrain.seed;
            vigSpec.animatedNoise = spec.flickerGrain.animated;
            LayerHandle& shade = scene.shape(vigSpec);
            shade.position(canvasW * 0.5f, canvasH * 0.5f);
            shade.alive(spec.inFrame, endFrame);
            shade.animateOpacity(spec.inFrame, 24, 0.f, 1.f);
        }

        // ── 2-4. The three typographic lines ──
        const TitleLine* lines[3] = {&spec.small, &spec.main, &spec.script};
        MotionLayerId* handles[3] = {&out.smallLine, &out.mainTitle, &out.scriptLine};
        const char* suffixes[3] = {"_small", "_main", "_script"};
        for (int li = 0; li < 3; ++li) {
            const TitleLine& line = *lines[li];
            TextSpec textSpec{.text = line.text, .font = line.font,
                              .fontSize = line.fontSize, .color = line.color,
                              .name = spec.name + suffixes[li]};
            // Halation via halo shadow (GPU-safe: no expanding effect stack).
            textSpec.shadow = TextShadowStyle{.color = "#FFFFFF",
                                              .opacity = line.haloOpacity,
                                              .blur = line.haloBlur,
                                              .offset = chrononmotion::Vector2(0.f, 0.f)};
            LayerHandle& text = scene.text(textSpec);
            text.position(line.posX, line.posY);
            text.alive(spec.inFrame, endFrame);
            text.animateOpacity(line.enterFrame, 15, 0.f, 1.f);
            text.animateOpacity(spec.exitStartFrame, exitDuration, 1.f, 0.f);
            // Whole-frame weave: identical absolute keys on every line.
            for (int f = spec.inFrame; f < endFrame; f += 4) {
                text.layer().tracks.position.add(
                    at(f, fps),
                    chrononmotion::Vector3(line.posX + weaveOffsetX(f, spec.weave.amplitude),
                                           line.posY + weaveOffsetY(f, spec.weave.amplitude),
                                           0.f),
                    Easing::linear());
            }
            // Slow composition push-in.
            text.layer().tracks.scale.add(at(spec.inFrame, fps),
                                          chrononmotion::Vector3(spec.zoomFrom, spec.zoomFrom, 1.f),
                                          Easing::linear());
            text.layer().tracks.scale.add(at(endFrame, fps),
                                          chrononmotion::Vector3(spec.zoomTo, spec.zoomTo, 1.f),
                                          Easing::linear());
            *handles[li] = text.id();
        }

        // ── 5. Deterministic dust drift ──
        {
            bool anchored = false;
            for (std::uint32_t i = 0; i < spec.dust.count; ++i) {
                const float dx = titleHash01(i * 3, spec.dust.seed);
                const float dy = titleHash01(i * 3 + 1, spec.dust.seed);
                const float drift = (titleHash01(i * 3 + 2, spec.dust.seed) - 0.5f) * 60.f;
                const float size = 2.f + titleHash01(i * 7 + 1, spec.dust.seed + 5) * 3.f;
                LayerHandle& dot = scene.shape(ShapeSpec{
                        .size = chrononmotion::Vector2(size, size),
                        .fillColor = "#FFFFFF",
                        .name = spec.name + "_dust_" + std::to_string(i),
                        .geometry = ShapeGeometry::Ellipse});
                dot.position(dx * canvasW, dy * canvasH);
                dot.alive(spec.inFrame, endFrame);
                const int lifeIn = spec.inFrame + static_cast<int>(dx * 30.f);
                dot.animateOpacity(lifeIn, 12, 0.f, spec.dust.opacity);
                dot.animateOpacity(endFrame - 12, 12, spec.dust.opacity, 0.f);
                dot.animatePosition(lifeIn, endFrame - lifeIn - 12,
                                    chrononmotion::Vector3(drift, -drift * 0.6f, 0.f));
                if (!anchored) {
                    out.dust = dot.id();
                    anchored = true;
                }
            }
        }

        // ── 6. Exposure-flicker veil (dense holds, exit flash) ──
        {
            LayerHandle& veil = scene.shape(ShapeSpec{
                    .size = scene.canvas(), .fillColor = "#FFFFFF",
                    .name = spec.name + "_flicker"});
            veil.position(canvasW * 0.5f, canvasH * 0.5f);
            veil.alive(spec.inFrame, endFrame);
            veil.opacity(0.f);
            int hold = 0;
            for (int f = spec.inFrame; f < endFrame; f += 3, ++hold) {
                veil.layer().tracks.opacity.add(at(f, fps),
                                                flickerLift(spec.flicker, hold, f),
                                                Easing::linear());
            }
            veil.layer().tracks.opacity.add(at(endFrame, fps), 0.f, Easing::linear());
            out.flickerVeil = veil.id();
        }
        return out;
    }

    const char* vintageDocumentaryTitle01Id() noexcept {
        return "vintage_documentary_title_01";
    }

} // namespace chronontemplate::vintage_documentary
