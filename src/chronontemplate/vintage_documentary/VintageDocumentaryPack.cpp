#include "chronontemplate/vintage_documentary/VintageDocumentaryPack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <cmath>
#include <random>
#include <stdexcept>

namespace chronontemplate::vintage_documentary {

    namespace {

        void requireHex(const std::string& color, const char* what) {
            if (!chronon3d::render_plan::parse_hex_color(color))
                throw std::invalid_argument(std::string("vintage documentary: ") + what +
                                            " must be #RRGGBB");
        }

        void requireFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("vintage documentary: ") + what +
                                            " must be finite");
        }

        void validatePhoto(const VintagePhotoTreatment& photo) {
            requireFinite(photo.saturation, "photo.saturation");
            requireFinite(photo.contrast, "photo.contrast");
            requireFinite(photo.grain, "photo.grain");
            requireFinite(photo.vignette, "photo.vignette");
            requireFinite(photo.cornerRadius, "photo.cornerRadius");
            requireFinite(photo.tornEdgeAmount, "photo.tornEdgeAmount");
            requireFinite(photo.tornEdgeScale, "photo.tornEdgeScale");
            requireFinite(photo.scanlineIntensity, "photo.scanlineIntensity");
            requireFinite(photo.scanlineSpacing, "photo.scanlineSpacing");
            requireFinite(photo.tintOpacity, "photo.tintOpacity");
            requireFinite(photo.edgeGlowOpacity, "photo.edgeGlowOpacity");
            if (photo.saturation < 0.f || photo.saturation > 4.f ||
                photo.contrast < 0.f || photo.contrast > 16.f ||
                photo.grain < 0.f || photo.grain > 1.f ||
                photo.vignette < 0.f || photo.vignette > 1.f ||
                photo.cornerRadius < 0.f || photo.cornerRadius > 512.f ||
                photo.tornEdgeAmount < 0.f || photo.tornEdgeAmount > 64.f ||
                photo.tornEdgeScale < 0.f || photo.tornEdgeScale > 1024.f ||
                (photo.tornEdgeAmount > 0.f && photo.tornEdgeScale <= 0.f) ||
                photo.scanlineIntensity < 0.f || photo.scanlineIntensity > 0.25f ||
                photo.scanlineSpacing < 0.002f || photo.scanlineSpacing > 1.f ||
                photo.tintOpacity < 0.f || photo.tintOpacity > 1.f ||
                photo.edgeGlowOpacity < 0.f || photo.edgeGlowOpacity > 1.f)
                throw std::invalid_argument("vintage documentary: photo treatment is outside supported ranges");
            requireHex(photo.tintColor, "photo.tintColor");
            requireHex(photo.edgeGlowColor, "photo.edgeGlowColor");
        }

        void validateBackground(const AtmosphericBackground& bg) {
            requireFinite(bg.lightCenterX, "background.lightCenterX");
            requireFinite(bg.lightCenterY, "background.lightCenterY");
            requireFinite(bg.lightRadius, "background.lightRadius");
            requireFinite(bg.lightOpacity, "background.lightOpacity");
            requireFinite(bg.dustOpacity, "background.dustOpacity");
            requireFinite(bg.vignetteStrength, "background.vignetteStrength");
            requireFinite(bg.grain, "background.grain");
            if (bg.lightCenterX < 0.f || bg.lightCenterX > 1.f ||
                bg.lightCenterY < 0.f || bg.lightCenterY > 1.f ||
                bg.lightRadius <= 0.f || bg.lightRadius > 2.f ||
                bg.lightOpacity < 0.f || bg.lightOpacity > 1.f ||
                bg.dustCount > 256 || bg.dustOpacity < 0.f || bg.dustOpacity > 1.f ||
                bg.vignetteStrength < 0.f || bg.vignetteStrength > 1.f ||
                bg.grain < 0.f || bg.grain > 1.f)
                throw std::invalid_argument("vintage documentary: background is outside supported ranges");
            requireHex(bg.baseColor, "background.baseColor");
            requireHex(bg.lightColor, "background.lightColor");
        }

        void validateTitle(const VintageTitle& title) {
            requireFinite(title.fontSize, "title.fontSize");
            requireFinite(title.glowWideRadius, "title.glowWideRadius");
            requireFinite(title.glowWideIntensity, "title.glowWideIntensity");
            requireFinite(title.glowSmallRadius, "title.glowSmallRadius");
            requireFinite(title.glowSmallIntensity, "title.glowSmallIntensity");
            requireFinite(title.dividerWidth, "title.dividerWidth");
            requireFinite(title.dividerOpacity, "title.dividerOpacity");
            if (title.text.empty() || title.fontSize <= 0.f || title.fontSize > 512.f ||
                title.glowWideRadius < 0.f || title.glowWideRadius > 256.f ||
                title.glowWideIntensity < 0.f || title.glowWideIntensity > 4.f ||
                title.glowSmallRadius < 0.f || title.glowSmallRadius > 256.f ||
                title.glowSmallIntensity < 0.f || title.glowSmallIntensity > 4.f ||
                title.dividerWidth <= 0.f || title.dividerWidth > 1920.f ||
                title.dividerOpacity < 0.f || title.dividerOpacity > 1.f)
                throw std::invalid_argument("vintage documentary: title is outside supported ranges");
            requireHex(title.color, "title.color");
            requireHex(title.glowWideColor, "title.glowWideColor");
        }

        void validateBrush(const BrushReveal& brush, int sceneIn, int sceneEnd) {
            if (!brush.enabled) return;
            requireFinite(brush.bristleAmplitudePx, "brush.bristleAmplitudePx");
            requireFinite(brush.edgeSoftnessPx, "brush.edgeSoftnessPx");
            requireFinite(brush.slant, "brush.slant");
            requireFinite(brush.pushFrom, "brush.pushFrom");
            requireFinite(brush.pushTo, "brush.pushTo");
            requireFinite(brush.leadIntensity, "brush.leadIntensity");
            if (brush.startFrame < sceneIn || brush.durationFrames < 1 ||
                brush.durationFrames > 300 ||
                brush.startFrame + brush.durationFrames > sceneEnd ||
                brush.bristleAmplitudePx <= 0.f || brush.bristleAmplitudePx > 128.f ||
                brush.edgeSoftnessPx <= 0.f || brush.edgeSoftnessPx > 64.f ||
                brush.slant < -1.f || brush.slant > 1.f ||
                brush.pushFrom < 1.f || brush.pushFrom > 1.5f ||
                brush.pushTo < 1.f || brush.pushTo > 1.5f ||
                brush.pushFrom < brush.pushTo ||
                brush.pushDurationFrames < 1 || brush.pushDurationFrames > 300 ||
                brush.startFrame + brush.pushDurationFrames > sceneEnd ||
                brush.leadIntensity < 0.f || brush.leadIntensity > 1.f)
                throw std::invalid_argument("vintage documentary: brush reveal is outside supported ranges");
            requireHex(brush.leadColor, "brush.leadColor");
        }

        void validateGlitch(const DigitalSliceGlitch& glitch, int sceneEnd) {
            requireFinite(glitch.sliceDisplace, "glitch.sliceDisplace");
            requireFinite(glitch.rgbSplitPx, "glitch.rgbSplitPx");
            if (glitch.startFrame < 0 || glitch.durationFrames < 1 ||
                glitch.durationFrames > 30 ||
                glitch.startFrame + glitch.durationFrames > sceneEnd ||
                glitch.sliceDisplace < 0.f || glitch.sliceDisplace > 1.f ||
                glitch.rgbSplitPx < 0.f || glitch.rgbSplitPx > 128.f ||
                (glitch.mosaicBlockSize != 0 &&
                 (glitch.mosaicBlockSize < 2 || glitch.mosaicBlockSize > 64)))
                throw std::invalid_argument("vintage documentary: glitch is outside supported ranges");
        }

        // Deterministic [0,1) from an integer index (splitmix64): stable dust
        // placement without shipping an RNG sequence in the recipe.
        float hash01(std::uint64_t index, std::uint64_t seed) {
            std::uint64_t z = index + 0x9E3779B97F4A7C15ULL + seed * 0xBF58476D1CE4E5B9ULL;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
            z = z ^ (z >> 31);
            return static_cast<float>(z >> 11) * (1.f / 9007199254740992.f);
        }

    } // namespace

    VintageDocumentaryLayers addVintageDocumentaryScene(
            TemplateScene& scene, const VintageDocumentaryScene& spec) {
        validatePhoto(spec.photo);
        validateBackground(spec.background);
        validateTitle(spec.title);
        if (spec.photoAsset.empty() || spec.name.empty())
            throw std::invalid_argument("vintage documentary: photo asset and scene name are required");
        requireFinite(spec.photoWidth, "photoWidth");
        requireFinite(spec.photoHeight, "photoHeight");
        requireFinite(spec.photoCenterX, "photoCenterX");
        requireFinite(spec.photoCenterY, "photoCenterY");
        requireFinite(spec.titleCenterY, "titleCenterY");
        if (spec.inFrame < 0 || spec.durationFrames < 1 || spec.durationFrames > 900 ||
            spec.photoWidth <= 0.f || spec.photoHeight <= 0.f)
            throw std::invalid_argument("vintage documentary: scene window or photo size is invalid");
        const float canvasW = scene.canvas().x;
        const float canvasH = scene.canvas().y;
        if (spec.photoCenterX < 0.f || spec.photoCenterX > canvasW ||
            spec.photoCenterY < 0.f || spec.photoCenterY > canvasH ||
            spec.titleCenterY < 0.f || spec.titleCenterY > canvasH)
            throw std::invalid_argument("vintage documentary: photo/title centers must sit on canvas");
        const int endFrame = spec.inFrame + spec.durationFrames;
        validateBrush(spec.brush, spec.inFrame, endFrame);
        validateGlitch(spec.glitch, endFrame);
        const std::string& photoAsset = spec.brush.enabled && !spec.brush.photoAsset.empty()
            ? spec.brush.photoAsset : spec.photoAsset;

        VintageDocumentaryLayers out{};

        // ── 1. Atmospheric background (static textures, no camera move) ──
        {
            const auto& bg = spec.background;
            LayerHandle& ground = scene.shape(ShapeSpec{
                    .size = scene.canvas(), .fillColor = bg.baseColor,
                    .name = spec.name + "_bg_ground"});
            ground.position(canvasW * 0.5f, canvasH * 0.5f);
            ground.alive(spec.inFrame, endFrame);
            ground.animateOpacity(spec.inFrame, 24, 0.f, 1.f);
            out.background = ground.id();

            ShapeRadialGradient light;
            light.center = chrononmotion::Vector2(0.5f, 0.5f);
            light.radius = 0.5f;
            light.stops = {{0.f, bg.lightColor, bg.lightOpacity},
                           {1.f, bg.lightColor, 0.f}};
            LayerHandle& glow = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(bg.lightRadius * canvasW,
                                                   bg.lightRadius * canvasH),
                    .fillColor = bg.lightColor, .name = spec.name + "_bg_light",
                    .geometry = ShapeGeometry::Ellipse, .radialGradient = light});
            glow.position(bg.lightCenterX * canvasW, bg.lightCenterY * canvasH);
            glow.alive(spec.inFrame, endFrame);
            glow.animateOpacity(spec.inFrame, 30, 0.f, 1.f);

            // Sparse deterministic film dust over the whole scene.
            for (std::uint32_t i = 0; i < bg.dustCount; ++i) {
                const float dx = hash01(i * 3, bg.dustSeed);
                const float dy = hash01(i * 3 + 1, bg.dustSeed);
                const float drift = (hash01(i * 3 + 2, bg.dustSeed) - 0.5f) * 60.f;
                const float size = 2.f + hash01(i * 7 + 1, bg.dustSeed + 5) * 3.f;
                LayerHandle& dot = scene.shape(ShapeSpec{
                        .size = chrononmotion::Vector2(size, size),
                        .fillColor = "#FFFFFF",
                        .name = spec.name + "_dust_" + std::to_string(i),
                        .geometry = ShapeGeometry::Ellipse});
                dot.position(dx * canvasW, dy * canvasH);
                dot.alive(spec.inFrame, endFrame);
                const int lifeIn = spec.inFrame + static_cast<int>(dx * 30.f);
                dot.animateOpacity(lifeIn, 12, 0.f, bg.dustOpacity);
                dot.animateOpacity(endFrame - 12, 12, bg.dustOpacity, 0.f);
                dot.animatePosition(lifeIn, endFrame - lifeIn - 12,
                                    chrononmotion::Vector3(drift, -drift * 0.6f, 0.f));
            }

            // Vignette: oversized ellipse, transparent heart, dark rim.
            ShapeRadialGradient vig;
            vig.center = chrononmotion::Vector2(0.5f, 0.5f);
            vig.radius = 0.5f;
            vig.stops = {{0.f, "#000000", 0.f},
                         {0.62f, "#000000", 0.f},
                         {1.f, "#000000", bg.vignetteStrength}};
            LayerHandle& shade = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(canvasW * 1.6f, canvasH * 1.6f),
                    .fillColor = "#000000", .name = spec.name + "_bg_vignette",
                    .geometry = ShapeGeometry::Ellipse, .radialGradient = vig,
                    .noiseAmount = bg.grain, .noiseSeed = bg.grainSeed});
            shade.position(canvasW * 0.5f, canvasH * 0.5f);
            shade.alive(spec.inFrame, endFrame);
            shade.animateOpacity(spec.inFrame, 24, 0.f, 1.f);
        }

        // ── 2. Vintage photo: halo, graded torn card, pink wash ──
        const auto& photo = spec.photo;
        ImageFrameStyle frame{
                .cornerRadius = photo.cornerRadius,
                .saturation = photo.saturation, .contrast = photo.contrast,
                .grain = photo.grain, .vignette = photo.vignette,
                .grainSeed = photo.grainSeed,
                .tornEdgeAmount = photo.tornEdgeAmount,
                .tornEdgeScale = photo.tornEdgeScale,
                .tornEdgeSeed = photo.tornEdgeSeed,
                .scanlineIntensity = photo.scanlineIntensity,
                .scanlineSpacing = photo.scanlineSpacing};
        {
            ShapeRadialGradient halo;
            halo.center = chrononmotion::Vector2(0.5f, 0.5f);
            halo.radius = 0.5f;
            halo.stops = {{0.f, photo.edgeGlowColor, photo.edgeGlowOpacity},
                          {1.f, photo.edgeGlowColor, 0.f}};
            LayerHandle& haloLayer = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(spec.photoWidth * 1.25f,
                                                   spec.photoHeight * 1.3f),
                    .fillColor = photo.edgeGlowColor,
                    .name = spec.name + "_photo_halo",
                    .geometry = ShapeGeometry::Ellipse, .radialGradient = halo});
            haloLayer.position(spec.photoCenterX, spec.photoCenterY);
            haloLayer.alive(spec.inFrame, endFrame);
            haloLayer.animateOpacity(spec.inFrame, 20, 0.f, 1.f);
            haloLayer.animateOpacity(endFrame - 18, 18, 1.f, 0.f);
        }
        LayerHandle& card = scene.image(ImageSpec{
                .path = photoAsset, .name = spec.name + "_photo",
                .frame = frame, .fit = ImageFitMode::Cover,
                .targetSize = chrononmotion::Vector2(spec.photoWidth, spec.photoHeight)});
        card.position(spec.photoCenterX, spec.photoCenterY);
        card.alive(spec.inFrame, endFrame);
        card.animate(FadeIn{.inFrame = spec.inFrame, .duration = 20});
        if (spec.brush.enabled) {
            // Modern push-in while the bristles paint: motion-side half of
            // the reveal; the pixel wipe rides the sampler math below.
            card.animate(ScalePop{.inFrame = spec.brush.startFrame,
                                  .duration = spec.brush.pushDurationFrames,
                                  .from = spec.brush.pushFrom,
                                  .to = spec.brush.pushTo});
        } else {
            card.animate(ScalePop{.inFrame = spec.inFrame, .duration = 44,
                                  .from = 0.94f, .to = 1.f});
        }
        card.animate(FadeOut{.startFrame = endFrame - 18, .duration = 18});
        out.photo = card.id();
        {
            LayerHandle& wash = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(spec.photoWidth, spec.photoHeight),
                    .fillColor = photo.tintColor,
                    .name = spec.name + "_photo_tint",
                    .cornerRadius = photo.cornerRadius});
            wash.parent(card.id());
            wash.position(0.f, 0.f);
            wash.opacity(photo.tintOpacity);
            wash.alive(spec.inFrame, endFrame);
            wash.animateOpacity(spec.inFrame, 20, 0.f, photo.tintOpacity);
            wash.animateOpacity(endFrame - 18, 18, photo.tintOpacity, 0.f);
        }

        // ── 3. Divider + double-glow yellow title ──
        const auto& title = spec.title;
        {
            const float ruleY = spec.titleCenterY - title.fontSize * 0.9f;
            LayerHandle& haloRule = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(title.dividerWidth, 9.f),
                    .fillColor = "#FFFFFF",
                    .name = spec.name + "_divider_halo"});
            haloRule.position(spec.photoCenterX, ruleY);
            haloRule.opacity(0.22f * title.dividerOpacity);
            haloRule.alive(spec.inFrame, endFrame);
            haloRule.animateOpacity(spec.inFrame + 12, 20, 0.f, 0.22f * title.dividerOpacity);
            haloRule.animateOpacity(endFrame - 18, 18, 0.22f * title.dividerOpacity, 0.f);
            LayerHandle& rule = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(title.dividerWidth, 3.f),
                    .fillColor = "#FFFFFF", .name = spec.name + "_divider"});
            rule.position(spec.photoCenterX, ruleY);
            rule.opacity(title.dividerOpacity);
            rule.alive(spec.inFrame, endFrame);
            rule.animateOpacity(spec.inFrame + 12, 20, 0.f, title.dividerOpacity);
            rule.animateOpacity(endFrame - 18, 18, title.dividerOpacity, 0.f);

            TextSpec wide{.text = title.text, .font = title.font,
                          .fontSize = title.fontSize, .color = title.color,
                          .name = spec.name + "_title_halo"};
            wide.glow = TextGlowStyle{.color = title.glowWideColor,
                                      .radius = title.glowWideRadius,
                                      .intensity = title.glowWideIntensity};
            LayerHandle& haloTitle = scene.text(wide);
            haloTitle.position(spec.photoCenterX, spec.titleCenterY);
            haloTitle.alive(spec.inFrame, endFrame);
            haloTitle.animateOpacity(spec.inFrame + 12, 20, 0.f, 1.f);
            haloTitle.animateOpacity(endFrame - 18, 18, 1.f, 0.f);

            TextSpec hot{.text = title.text, .font = title.font,
                         .fontSize = title.fontSize, .color = title.color,
                         .name = spec.name + "_title"};
            hot.glow = TextGlowStyle{.color = title.color,
                                     .radius = title.glowSmallRadius,
                                     .intensity = title.glowSmallIntensity};
            LayerHandle& hotTitle = scene.text(hot);
            hotTitle.position(spec.photoCenterX, spec.titleCenterY);
            hotTitle.alive(spec.inFrame, endFrame);
            hotTitle.animateOpacity(spec.inFrame + 16, 20, 0.f, 1.f);
            hotTitle.animateOpacity(endFrame - 18, 18, 1.f, 0.f);
        }

        // ── 4. Closing slice glitch over a dipped clean card ──
        {
            const auto& glitch = spec.glitch;
            const int gEnd = glitch.startFrame + glitch.durationFrames;
            ImageFrameStyle glitchFrame = frame;
            glitchFrame.grainSeed = glitch.seed;
            glitchFrame.sliceDisplace = glitch.sliceDisplace;
            glitchFrame.channelSplit = glitch.rgbSplitPx;
            glitchFrame.mosaicBlockSize = glitch.mosaicBlockSize;
            LayerHandle& broken = scene.image(ImageSpec{
                    .path = photoAsset, .name = spec.name + "_photo_glitch",
                    .frame = glitchFrame, .fit = ImageFitMode::Cover,
                    .targetSize = chrononmotion::Vector2(spec.photoWidth, spec.photoHeight)});
            broken.position(spec.photoCenterX, spec.photoCenterY);
            broken.alive(glitch.startFrame, gEnd);
            broken.animateOpacity(glitch.startFrame, 2, 0.f, 1.f);
            broken.animateOpacity(gEnd - 2, 2, 1.f, 0.f);
            out.glitch = broken.id();
            card.animateOpacity(glitch.startFrame, 2, 1.f, 0.12f);
            card.animateOpacity(gEnd - 2, 2, 0.12f, 1.f);
        }
        return out;
    }

    float brushRevealProgress(const BrushReveal& brush, int frame) {
        if (!brush.enabled) return 1.f;
        if (frame <= brush.startFrame) return 0.f;
        if (frame >= brush.startFrame + brush.durationFrames) return 1.f;
        const float p = static_cast<float>(frame - brush.startFrame) /
            static_cast<float>(brush.durationFrames);
        return p * p * (3.f - 2.f * p);
    }

    float brushEdgeX(const BrushReveal& brush, int frame, float photoWidth) {
        // Progress is already eased; the edge is linear in it (mirrors the
        // reference Python renderer exactly).
        const float p = brushRevealProgress(brush, frame);
        if (brush.direction == BrushDirection::LeftToRight)
            return -40.f + p * (photoWidth + 80.f);
        return photoWidth + 40.f - p * (photoWidth + 80.f);
    }

    float brushPushScale(const BrushReveal& brush, int frame) {
        if (!brush.enabled) return 1.f;
        if (frame <= brush.startFrame) return brush.pushFrom;
        if (frame >= brush.startFrame + brush.pushDurationFrames) return brush.pushTo;
        const float p = static_cast<float>(frame - brush.startFrame) /
            static_cast<float>(brush.pushDurationFrames);
        const float eased = 1.f - (1.f - p) * (1.f - p);
        return brush.pushFrom - (brush.pushFrom - brush.pushTo) * eased;
    }

    const char* vintageDocumentaryId() noexcept {
        return "vintage_documentary_v1";
    }

} // namespace chronontemplate::vintage_documentary
