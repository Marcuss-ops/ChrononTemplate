#include "chronontemplate/single_images/ArchivalCardPack.hpp"

#include "chronontemplate/effects/EffectsPack.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace chronontemplate {

    namespace {

        using chrononmotion::Vector2;
        using chrononmotion::Vector3;

        constexpr float kMatPadX = 48.f;
        constexpr float kMatPadY = 60.f;
        constexpr float kCaptionGap = 46.f;
        constexpr const char* kTornFrameAsset =
                "ChrononTemplate/assets/archival_refs_v2/torn_paper_frame.png";

        // Deterministic [0,1) from an index (splitmix64), so the torn edges and
        // paper stains are byte-identical across machines and resumed renders.
        float hash01(std::uint64_t index, std::uint64_t seed) {
            std::uint64_t z = index + 0x9E3779B97F4A7C15ULL + seed * 0xBF58476D1CE4E5B9ULL;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
            z = z ^ (z >> 31);
            return static_cast<float>(z >> 11) * (1.f / 9007199254740992.f);
        }

        void requireFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("archive card: ") + what + " must be finite");
        }

        void positionScreenLayer(LayerHandle& layer, float screenX, float screenY) {
            layer.position(screenX, screenY);
        }

        void validateSpec(ArchivalCardLook look, const ArchivalCardSpec& spec,
                          float canvasW, float canvasH, int endFrame) {
            if (spec.name.empty())
                throw std::invalid_argument("archive card: scene name is required");
            if (spec.primaryAsset.empty())
                throw std::invalid_argument("archive card: primary asset is required");
            if (look == ArchivalCardLook::DoublePortraitArchive && spec.secondaryAsset.empty())
                throw std::invalid_argument("archive card: double portrait requires a secondary asset");
            requireFinite(spec.primaryWidth, "primaryWidth");
            requireFinite(spec.primaryHeight, "primaryHeight");
            requireFinite(spec.secondaryWidth, "secondaryWidth");
            requireFinite(spec.secondaryHeight, "secondaryHeight");
            requireFinite(spec.centerX, "centerX");
            requireFinite(spec.centerY, "centerY");
            if (spec.primaryWidth <= 0.f || spec.primaryHeight <= 0.f ||
                spec.secondaryWidth <= 0.f || spec.secondaryHeight <= 0.f ||
                spec.primaryWidth > canvasW || spec.primaryHeight > canvasH ||
                spec.secondaryWidth > canvasW || spec.secondaryHeight > canvasH)
                throw std::invalid_argument("archive card: card sizes must be positive and fit the canvas");
            if (spec.inFrame < 0 || spec.durationFrames < 2 || spec.durationFrames > 900)
                throw std::invalid_argument("archive card: frame window is outside supported ranges");
            if (endFrame <= spec.inFrame)
                throw std::invalid_argument("archive card: empty frame window");
        }

        LayerHandle& tornPaper(TemplateScene& scene, const std::string& name,
                               float width, float height, const std::string& fill,
                               float jitter, std::uint32_t seed, float dx, float dy,
                               float centerX, float centerY, int inFrame, int endFrame) {
            ShapeSpec spec{};
            spec.size = Vector2(width, height);
            spec.fillColor = fill;
            spec.name = name;
            spec.geometry = ShapeGeometry::Rectangle;
            (void)jitter;
            (void)dx;
            (void)dy;
            spec.noiseAmount = 0.012f;
            spec.noiseSeed = seed;
            LayerHandle& handle = scene.shape(spec);
            positionScreenLayer(handle, centerX, centerY);
            handle.alive(inFrame, endFrame);
            return handle;
        }

        void animatePhoto(LayerHandle& photo, int inFrame, int endFrame, float baseScale) {
            photo.alive(inFrame, endFrame);
            photo.scale(baseScale);
            photo.opacity(1.f);
            // A restrained dissolve only. Keep the archival image registered
            // exactly in place throughout the shot.
            constexpr int kEntranceFrames = 18;
            photo.animateOpacity(inFrame, kEntranceFrames, 0.f, 1.f);
        }

        void fadeEntrance(LayerHandle& layer, int inFrame, float finalOpacity = 1.f) {
            constexpr int kEntranceFrames = 18;
            layer.opacity(finalOpacity);
            layer.animateOpacity(inFrame, kEntranceFrames, 0.f, finalOpacity);
        }

        float scalePhotoToTarget(LayerHandle& photo, float targetWidth, float targetHeight) {
            const Vector2 measured = photo.layer().content.metrics.naturalSize;
            if (!std::isfinite(measured.x) || !std::isfinite(measured.y) ||
                measured.x <= 0.f || measured.y <= 0.f)
                throw std::invalid_argument("archive card: image measurement must have positive finite dimensions");
            // ImageRequest::targetSize controls the image treatment/crop, while
            // the motion layer still starts at the source's natural dimensions.
            // Scale the layer too so the photograph fits its paper/window.
            const float scale = std::max(targetWidth / measured.x, targetHeight / measured.y);
            photo.scale(scale);
            return scale;
        }

        LayerHandle& makeText(TemplateScene& scene, const std::string& name,
                              const std::string& text, const std::string& font,
                              float fontSize, const std::string& color,
                              float x, float y, int inFrame, int endFrame) {
            TextSpec spec{};
            spec.text = text;
            spec.font = font;
            spec.fontSize = fontSize;
            spec.color = color;
            spec.name = name;
            LayerHandle& handle = scene.text(spec);
            handle.layer().flat();
            handle.position(x - scene.canvas().x * 0.5f,
                            y - scene.canvas().y * 0.5f);
            handle.alive(inFrame, endFrame);
            handle.opacity(1.f);
            handle.animateOpacity(inFrame, 18, 0.f, 1.f);
            return handle;
        }

        void overlay(TemplateScene& scene, effects::EffectKind kind,
                     const ArchivalCardSpec& spec, int endFrame,
                     float intensity, float opacity, std::uint32_t seed) {
            effects::EffectSpec effect{};
            effect.intensity = intensity;
            effect.opacity = opacity;
            effect.seed = seed;
            effect.startFrame = spec.inFrame;
            effect.endFrame = endFrame;
            (void)effects::addEffect(scene, kind, effect);
        }

        LayerHandle& paperGround(TemplateScene& scene, const std::string& name,
                                 const std::string& color, float noise,
                                 std::uint32_t seed, int inFrame, int endFrame) {
            ShapeSpec ground{};
            ground.size = scene.canvas();
            ground.fillColor = color;
            ground.name = name;
            ground.noiseAmount = noise;
            ground.noiseSeed = seed;
            LayerHandle& handle = scene.shape(ground);
            handle.position(scene.canvas().x * 0.5f,
                            scene.canvas().y * 0.5f);
            handle.alive(inFrame, endFrame);
            handle.opacity(1.f);
            return handle;
        }

        void paperStain(TemplateScene& scene, const std::string& name,
                        float x, float y, float w, float h, const std::string& color,
                        float opacity, int inFrame, int endFrame) {
            ShapeRadialGradient gradient;
            gradient.center = Vector2(0.5f, 0.5f);
            gradient.radius = 0.5f;
            gradient.stops = {{0.f, color, opacity}, {1.f, color, 0.f}};
            ShapeSpec stain{};
            stain.size = Vector2(w, h);
            stain.fillColor = color;
            stain.name = name;
            stain.geometry = ShapeGeometry::Ellipse;
            stain.radialGradient = gradient;
            LayerHandle& handle = scene.shape(stain);
            positionScreenLayer(handle, x, y);
            handle.alive(inFrame, endFrame);
            handle.opacity(opacity);
        }

        std::vector<MotionLayerId> dustSpecks(TemplateScene& scene, const std::string& name,
                        std::uint32_t count, std::uint32_t seed,
                        float opacity, int inFrame, int endFrame, bool drifting = false) {
            const float w = scene.canvas().x;
            const float h = scene.canvas().y;
            std::vector<MotionLayerId> ids;
            ids.reserve(count);
            for (std::uint32_t i = 0; i < count; ++i) {
                const float size = 1.5f + hash01(i * 5 + 1, seed) * 3.5f;
                ShapeSpec dot{};
                dot.size = Vector2(size, size);
                dot.fillColor = "#F6F2E6";
                dot.name = name + "_" + std::to_string(i);
                dot.geometry = ShapeGeometry::Ellipse;
                LayerHandle& handle = scene.shape(dot);
                positionScreenLayer(handle,
                                    hash01(i * 5 + 2, seed) * w,
                                    hash01(i * 5 + 3, seed) * h);
                handle.alive(inFrame, endFrame);
                const float alpha = opacity * (0.35f + hash01(i * 5 + 4, seed) * 0.65f);
                handle.opacity(alpha);
                if (drifting) {
                    const float dx = (hash01(i * 5 + 5, seed) - 0.5f) * 18.f;
                    const float dy = (hash01(i * 5 + 6, seed) - 0.5f) * 12.f;
                    handle.animatePosition(inFrame, endFrame - inFrame, Vector3(dx, dy, 0.f));
                    ids.push_back(handle.id());
                }
            }
            return ids;
        }

        ArchivalCardLayers addTornPaperPortrait(TemplateScene& scene,
                                                const ArchivalCardSpec& spec,
                                                int endFrame, float cx, float cy) {
            ArchivalCardLayers out{};
            const float w = scene.canvas().x;
            const float h = scene.canvas().y;
            out.background = paperGround(scene, spec.name + "_bg_ground",
                                         "#E8DEC6", 0.006f, 1942, spec.inFrame, endFrame).id();

            ShapeSpec grid{};
            grid.size = scene.canvas();
            grid.fillColor = "#E8DEC6";
            grid.fillEnabled = false;
            grid.name = spec.name + "_bg_grid";
            grid.geometry = ShapeGeometry::Grid;
            grid.gridSpacing = 36.f;
            grid.strokeColor = "#B9AA8B";
            grid.strokeWidth = 1.1f;
            LayerHandle& gridLayer = scene.shape(grid);
            gridLayer.position(w * 0.5f, h * 0.5f);
            gridLayer.alive(spec.inFrame, endFrame);
            gridLayer.opacity(0.42f);

            // Keep this card on the GPU-native path. Radial-gradient circles
            // force a CPU fallback in the Vulkan renderer; the aged paper
            // layer, photo grain, and irregular frame already carry the look.

            const float photoY = cy - 18.f;
            const float matW = spec.primaryWidth + kMatPadX * 2.f;
            const float matH = spec.primaryHeight + kMatPadY * 2.f;

            LayerHandle& shadow = tornPaper(scene, spec.name + "_mat_shadow",
                                            matW, matH, "#2A2118", 7.f, 421,
                                            10.f, 14.f, cx, photoY,
                                            spec.inFrame, endFrame);
            shadow.opacity(0.26f);
            fadeEntrance(shadow, spec.inFrame, 0.26f);

            // A transparent frame asset gives the paper its real torn edge;
            // Chronon still composites it as an independent layer over photo.

            LayerHandle& photo = scene.image(ImageSpec{
                    .path = spec.primaryAsset, .name = spec.name + "_photo",
                    .frame = archivalCardFrameStyle(ArchivalCardLook::TornPaperPortrait),
                    .fit = ImageFitMode::Cover,
                    .targetSize = Vector2(spec.primaryWidth, spec.primaryHeight)});
            const float photoScale = scalePhotoToTarget(photo, spec.primaryWidth, spec.primaryHeight);
            photo.position(cx, photoY);
            animatePhoto(photo, spec.inFrame, endFrame, photoScale);
            out.primary = photo.id();

            LayerHandle& mat = scene.image(ImageSpec{
                    .path = kTornFrameAsset, .name = spec.name + "_torn_paper_frame",
                    .frame = {}, .fit = ImageFitMode::Stretch,
                    .targetSize = Vector2(matW, matH)});
            mat.position(cx, photoY);
            mat.alive(spec.inFrame, endFrame);
            fadeEntrance(mat, spec.inFrame);
            out.mat = mat.id();

            if (!spec.primaryLabel.empty()) {
                LayerHandle& caption = makeText(scene, spec.name + "_label", spec.primaryLabel,
                                                spec.font, 46.f, "#26231E",
                                                cx, photoY + spec.primaryHeight * 0.5f + 32.f,
                                                spec.inFrame, endFrame);
                out.caption = caption.id();
            }
            if (!spec.archiveLabel.empty()) {
                makeText(scene, spec.name + "_archive_label", spec.archiveLabel,
                         spec.font, 22.f, "#6B604E",
                         cx, photoY + spec.primaryHeight * 0.5f + 74.f,
                         spec.inFrame, endFrame);
            }

            return out;
        }

        ArchivalCardLayers addArchivePrint(TemplateScene& scene,
                                            const ArchivalCardSpec& spec,
                                            int endFrame, float cx, float cy) {
            ArchivalCardLayers out{};

            out.background = paperGround(scene, spec.name + "_bg_ground",
                                         "#8E8D89", 0.006f, 1951, spec.inFrame, endFrame).id();
            dustSpecks(scene, spec.name + "_bg_dust", 10, 1955, 0.22f,
                       spec.inFrame, endFrame);

            const float outerW = spec.primaryWidth + 28.f;
            const float outerH = spec.primaryHeight + 28.f;
            const float photoY = cy - 14.f;
            LayerHandle& outer = scene.shape(ShapeSpec{
                    .size = Vector2(outerW, outerH), .fillColor = "#111111",
                    .name = spec.name + "_border_outer"});
            positionScreenLayer(outer, cx, photoY);
            outer.alive(spec.inFrame, endFrame);
            fadeEntrance(outer, spec.inFrame);
            LayerHandle& inner = scene.shape(ShapeSpec{
                    .size = Vector2(spec.primaryWidth + 14.f, spec.primaryHeight + 14.f),
                    .fillColor = "#F1EFE8", .name = spec.name + "_border_inner",
                    .noiseAmount = 0.035f, .noiseSeed = 1952});
            positionScreenLayer(inner, cx, photoY);
            inner.alive(spec.inFrame, endFrame);
            fadeEntrance(inner, spec.inFrame);
            out.mat = inner.id();

            LayerHandle& photo = scene.image(ImageSpec{
                    .path = spec.primaryAsset, .name = spec.name + "_photo",
                    .frame = archivalCardFrameStyle(ArchivalCardLook::ArchivePrint),
                    .fit = ImageFitMode::Cover,
                    .targetSize = Vector2(spec.primaryWidth, spec.primaryHeight)});
            const float photoScale = scalePhotoToTarget(photo, spec.primaryWidth, spec.primaryHeight);
            photo.position(cx, photoY);
            animatePhoto(photo, spec.inFrame, endFrame, photoScale);
            out.primary = photo.id();

            return out;
        }

        ArchivalCardLayers addVintageFilmProjection(TemplateScene& scene,
                                                     const ArchivalCardSpec& spec,
                                                     int endFrame, float cx, float cy) {
            ArchivalCardLayers out{};
            const float w = scene.canvas().x;
            const float h = scene.canvas().y;

            ShapeSpec ground{};
            ground.size = scene.canvas();
            ground.fillColor = "#050505";
            ground.name = spec.name + "_bg_ground";
            LayerHandle& groundLayer = scene.shape(ground);
            groundLayer.position(w * 0.5f, h * 0.5f);
            groundLayer.alive(spec.inFrame, endFrame);
            groundLayer.opacity(1.f);
            out.background = groundLayer.id();

            const float windowW = spec.primaryWidth;
            const float windowH = spec.primaryHeight;
            LayerHandle& window = scene.shape(ShapeSpec{
                    .size = Vector2(windowW, windowH), .fillColor = "#E9E3D3",
                    .name = spec.name + "_window", .cornerRadius = 30.f,
                    .noiseAmount = 0.04f, .noiseSeed = 1963});
            positionScreenLayer(window, cx, cy);
            window.alive(spec.inFrame, endFrame);
            fadeEntrance(window, spec.inFrame);
            out.mat = window.id();

            LayerHandle& photo = scene.image(ImageSpec{
                    .path = spec.primaryAsset, .name = spec.name + "_photo",
                    .frame = archivalCardFrameStyle(ArchivalCardLook::VintageFilmProjection),
                    .fit = ImageFitMode::Cover,
                    .targetSize = Vector2(spec.primaryWidth, spec.primaryHeight)});
            const float photoScale = scalePhotoToTarget(photo, spec.primaryWidth, spec.primaryHeight);
            photo.position(cx, cy);
            // The container stays fixed: the movement belongs to the footage.
            animatePhoto(photo, spec.inFrame, endFrame, photoScale);
            out.primary = photo.id();

            if (!spec.primaryLabel.empty()) {
                out.caption = makeText(scene, spec.name + "_label", spec.primaryLabel,
                                       spec.font, 40.f, "#E7E1D2",
                                       cx, cy + windowH * 0.5f + kCaptionGap,
                                       spec.inFrame, endFrame).id();
            }
            if (!spec.archiveLabel.empty()) {
                makeText(scene, spec.name + "_archive_label", spec.archiveLabel,
                         spec.font, 20.f, "#8A867A",
                         cx, cy + windowH * 0.5f + kCaptionGap + 48.f,
                         spec.inFrame, endFrame);
            }

            // Moving overlay sprites intermittently invalidated the Vulkan
            // composite in encoded MP4s. Keep the film dust as a stable texture.
            out.animatedDust = dustSpecks(scene, spec.name + "_dust", 8, 1968, 0.30f,
                       spec.inFrame, endFrame, false);
            return out;
        }

        ArchivalCardLayers addDoublePortraitArchive(TemplateScene& scene,
                                                     const ArchivalCardSpec& spec,
                                                     int endFrame, float cx, float cy) {
            ArchivalCardLayers out{};
            const float w = scene.canvas().x;
            const float h = scene.canvas().y;
            const float offset = w * 0.18f;
            const float photoY = cy - 34.f;
            const float matW = spec.secondaryWidth + kMatPadX * 2.f;
            const float matH = spec.secondaryHeight + kMatPadY * 2.f;

            out.background = paperGround(scene, spec.name + "_bg_ground",
                                         "#D7C5A3", 0.006f, 1937, spec.inFrame, endFrame).id();
            paperStain(scene, spec.name + "_bg_stain_a", w * 0.22f, h * 0.24f,
                      w * 0.52f, h * 0.44f, "#A4834F", 0.20f, spec.inFrame, endFrame);
            paperStain(scene, spec.name + "_bg_stain_b", w * 0.78f, h * 0.70f,
                      w * 0.46f, h * 0.40f, "#8C6B3E", 0.16f, spec.inFrame, endFrame);

            const float leftX = cx - offset;
            const float rightX = cx + offset;

            // Two independent torn mats and pasted photographs.
            LayerHandle& shadowA = tornPaper(scene, spec.name + "_mat_shadow_a",
                                             matW, matH, "#2A2118", 6.f, 401,
                                             9.f, 12.f, leftX, photoY,
                                             spec.inFrame, endFrame);
            shadowA.opacity(0.24f);
            fadeEntrance(shadowA, spec.inFrame, 0.24f);
            LayerHandle& shadowB = tornPaper(scene, spec.name + "_mat_shadow_b",
                                             matW, matH, "#2A2118", 6.f, 409,
                                             9.f, 12.f, rightX, photoY,
                                             spec.inFrame, endFrame);
            shadowB.opacity(0.24f);
            fadeEntrance(shadowB, spec.inFrame, 0.24f);

            LayerHandle& matA = tornPaper(scene, spec.name + "_mat_a", matW, matH,
                                          "#F2EBD8", 6.f, 73, 0.f, 0.f, leftX, photoY,
                                          spec.inFrame, endFrame);
            fadeEntrance(matA, spec.inFrame);
            LayerHandle& matB = tornPaper(scene, spec.name + "_mat_b", matW, matH,
                                          "#F2EBD8", 6.f, 91, 0.f, 0.f, rightX, photoY,
                                          spec.inFrame, endFrame);
            fadeEntrance(matB, spec.inFrame + 8);
            out.mat = matA.id();

            ImageFrameStyle frameA = archivalCardFrameStyle(ArchivalCardLook::DoublePortraitArchive);
            frameA.tornEdgeSeed = 1937;
            ImageFrameStyle frameB = frameA;
            frameB.tornEdgeSeed = 1940;
            frameB.grainSeed = 1941;

            LayerHandle& photoA = scene.image(ImageSpec{
                    .path = spec.primaryAsset, .name = spec.name + "_photo_a",
                    .frame = frameA, .fit = ImageFitMode::Cover,
                    .targetSize = Vector2(spec.secondaryWidth, spec.secondaryHeight)});
            const float photoScaleA = scalePhotoToTarget(photoA, spec.secondaryWidth, spec.secondaryHeight);
            photoA.position(leftX, photoY);
            animatePhoto(photoA, spec.inFrame, endFrame, photoScaleA);
            out.primary = photoA.id();

            LayerHandle& photoB = scene.image(ImageSpec{
                    .path = spec.secondaryAsset, .name = spec.name + "_photo_b",
                    .frame = frameB, .fit = ImageFitMode::Cover,
                    .targetSize = Vector2(spec.secondaryWidth, spec.secondaryHeight)});
            const float photoScaleB = scalePhotoToTarget(photoB, spec.secondaryWidth, spec.secondaryHeight);
            photoB.position(rightX, photoY);
            animatePhoto(photoB, spec.inFrame + 12, endFrame, photoScaleB);
            out.secondary = photoB.id();

            const float labelY = photoY + matH * 0.5f + kCaptionGap;
            if (!spec.primaryLabel.empty()) {
                out.caption = makeText(scene, spec.name + "_label_a", spec.primaryLabel,
                                       spec.font, 38.f, "#2A241B",
                                       leftX, labelY, spec.inFrame, endFrame).id();
            }
            if (!spec.secondaryLabel.empty()) {
                makeText(scene, spec.name + "_label_b", spec.secondaryLabel,
                         spec.font, 38.f, "#2A241B",
                         rightX, labelY, spec.inFrame + 12, endFrame);
            }
            if (!spec.archiveLabel.empty()) {
                makeText(scene, spec.name + "_archive_label", spec.archiveLabel,
                         spec.font, 19.f, "#6E5A3E",
                         cx, labelY + 54.f, spec.inFrame, endFrame);
            }

            overlay(scene, effects::EffectKind::PaperGrain, spec, endFrame, 0.55f, 1.f, 31);
            overlay(scene, effects::EffectKind::CinematicVignette, spec, endFrame, 0.30f, 1.f, 37);
            return out;
        }

    } // namespace

    ImageFrameStyle archivalCardFrameStyle(ArchivalCardLook look) {
        ImageFrameStyle frame{};
        switch (look) {
            case ArchivalCardLook::TornPaperPortrait:
                frame.saturation = 0.55f;
                frame.contrast = 0.95f;
                frame.grain = 0.018f;
                frame.grainSeed = 1942;
                frame.vignette = 0.10f;
                frame.channelSplit = 1.2f;
                // The torn silhouette belongs to the mat, not the straight-edged photo.
                frame.tornEdgeAmount = 0.f;
                frame.tornEdgeScale = 8.f;
                frame.tornEdgeSeed = 0;
                return frame;
            case ArchivalCardLook::ArchivePrint:
                frame.cornerRadius = 2.f;
                frame.saturation = 0.f;
                frame.contrast = 1.08f;
                frame.grain = 0.035f;
                frame.grainSeed = 1951;
                frame.vignette = 0.18f;
                return frame;
            case ArchivalCardLook::VintageFilmProjection:
                frame.cornerRadius = 26.f;
                frame.saturation = 0.f;
                frame.contrast = 1.12f;
                frame.grain = 0.010f;
                frame.grainSeed = 1963;
                frame.vignette = 0.18f;
                frame.channelSplit = 0.f;
                frame.scanlineIntensity = 0.f;
                frame.scanlineSpacing = 0.035f;
                return frame;
            case ArchivalCardLook::DoublePortraitArchive:
                frame.saturation = 0.35f;
                frame.contrast = 1.02f;
                frame.grain = 0.025f;
                frame.grainSeed = 1937;
                frame.vignette = 0.16f;
                frame.tornEdgeAmount = 5.f;
                frame.tornEdgeScale = 7.f;
                frame.tornEdgeSeed = 1937;
                return frame;
            default:
                throw std::invalid_argument("archivalCardFrameStyle: unknown look");
        }
    }

    const char* archivalCardLookId(ArchivalCardLook look) noexcept {
        switch (look) {
            case ArchivalCardLook::TornPaperPortrait: return "archival_torn_paper_portrait";
            case ArchivalCardLook::ArchivePrint: return "archival_archive_print";
            case ArchivalCardLook::VintageFilmProjection: return "archival_vintage_film_projection";
            case ArchivalCardLook::DoublePortraitArchive: return "archival_double_portrait";
            default: return "archival_unknown";
        }
    }

    std::vector<std::string> archivalCardLookIds() {
        return {archivalCardLookId(ArchivalCardLook::TornPaperPortrait),
                archivalCardLookId(ArchivalCardLook::ArchivePrint),
                archivalCardLookId(ArchivalCardLook::VintageFilmProjection),
                archivalCardLookId(ArchivalCardLook::DoublePortraitArchive)};
    }

    ArchivalCardLayers addArchivalCard(TemplateScene& scene, ArchivalCardLook look,
                                        const ArchivalCardSpec& spec) {
        const float canvasW = scene.canvas().x;
        const float canvasH = scene.canvas().y;
        // `durationFrames` is the number of presented frames; the motion core
        // treats the authored out-frame as the last visible one, so the card
        // ends one frame before the exclusive boundary.
        const int endFrame = spec.inFrame + spec.durationFrames - 1;
        validateSpec(look, spec, canvasW, canvasH, endFrame);

        const float cx = spec.centerX < 0.f ? canvasW * 0.5f : spec.centerX;
        const float cy = spec.centerY < 0.f ? canvasH * 0.5f : canvasH - spec.centerY;
        if (cx < 0.f || cx > canvasW || cy < 0.f || cy > canvasH)
            throw std::invalid_argument("archive card: card centre must sit on the canvas");

        switch (look) {
            case ArchivalCardLook::TornPaperPortrait:
                return addTornPaperPortrait(scene, spec, endFrame, cx, cy);
            case ArchivalCardLook::ArchivePrint:
                return addArchivePrint(scene, spec, endFrame, cx, cy);
            case ArchivalCardLook::VintageFilmProjection:
                return addVintageFilmProjection(scene, spec, endFrame, cx, cy);
            case ArchivalCardLook::DoublePortraitArchive:
                return addDoublePortraitArchive(scene, spec, endFrame, cx, cy);
            default:
                throw std::invalid_argument("addArchivalCard: unknown look");
        }
    }

    const char* archivalCardPackId() noexcept {
        return "archival_card_v1";
    }

} // namespace chronontemplate
