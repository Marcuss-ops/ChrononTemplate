#include "chronontemplate/single_images/PixelGridPack.hpp"

#include "chronontemplate/single_images/ImageAnimationPack.hpp"

#include "chrononmotion/motion/Presets.hpp"

#include <stdexcept>

namespace chronontemplate {

    namespace {
        using chrononmotion::Vector2;
        using chrononmotion::Vector3;
        using chrononmotion::motion::Easing;
        using chrononmotion::motion::Layer;

        float at(int frame, float fps) { return static_cast<float>(frame) / fps; }
    }

    LayerHandle& addImagePixelGrid(TemplateScene& scene, ImagePixelGrid animation,
                                   const std::string& assetPath, const std::string& name,
                                   ImageFrameStyle frame, ImageCameraMove cameraMove) {
        switch (animation) {
            case ImagePixelGrid::GridReveal:
            case ImagePixelGrid::PixelStepIn:
            case ImagePixelGrid::GridZoomOut:
            case ImagePixelGrid::GridSlideTiles:
            case ImagePixelGrid::GridBreathe:
                break;
            default:
                throw std::invalid_argument("addImagePixelGrid: unknown animation");
        }

        // Backdrop plate first so it draws behind the hero card: same asset,
        // dimmed to 0.55 (the renderer adds blur + pixelation + grid mask).
        LayerHandle& backdrop = scene.image(ImageSpec{
                .path = assetPath, .name = name + "_backdrop",
                .frame = ImageFrameStyle{.cornerRadius = 32.f}});
        backdrop.alive(0, 150);
        backdrop.animateOpacity(0, 30, 0.f, 0.55f);
        backdrop.animateOpacity(132, 18, 0.55f, 0.f);

        LayerHandle& image = scene.image(ImageSpec{
                .path = assetPath, .name = name, .frame = std::move(frame)});
        backdrop.parent(image.id());
        backdrop.position(0.f, 0.f);

        // Lattice bars on top of the hero, riding its entrance.
        struct Bar { const char* tag; float w; float h; float x; float y; };
        const Bar bars[] = {
            {"h0", 900.f, 4.f, 0.f, -110.f}, {"h1", 900.f, 4.f, 0.f, 110.f},
            {"v0", 4.f, 620.f, -160.f, 0.f}, {"v1", 4.f, 620.f, 160.f, 0.f},
        };
        const float fps = scene.fps();
        decltype(image.id()) barIds[4];
        int barCount = 0;
        for (const Bar& bar : bars) {
            LayerHandle& lattice = scene.shape(ShapeSpec{
                    .size = Vector2(bar.w, bar.h), .fillColor = "#8A8F98",
                    .name = name + "_grid_" + bar.tag, .cornerRadius = 2.f});
            lattice.parent(image.id());
            lattice.position(bar.x, bar.y);
            lattice.alive(0, 150);
            lattice.animateOpacity(0, 24, 0.f, 1.f);
            lattice.animateOpacity(132, 18, 1.f, 0.f);
            barIds[barCount++] = lattice.id();
        }

        Layer& hero = *scene.motion().findLayer(image.id());
        using chrononmotion::motion::presets::Direction;
        switch (animation) {
            case ImagePixelGrid::GridReveal:
                image.animate(ScalePop{.inFrame = 0, .duration = 88, .from = 0.90f, .to = 1.02f})
                     .animate(FadeIn{.inFrame = 0, .duration = 20});
                break;
            case ImagePixelGrid::PixelStepIn: {
                // Hard stepped scale: the renderer swaps in coarser pixel
                // blocks on each step for the pixel-reveal feel.
                auto& s = hero.tracks.scale;
                const Easing step = Easing::linear();
                s.add(at(0, fps), Vector3(0.60f, 0.60f, 0.60f), step);
                s.add(at(12, fps), Vector3(0.72f, 0.72f, 0.72f), step);
                s.add(at(24, fps), Vector3(0.84f, 0.84f, 0.84f), step);
                s.add(at(36, fps), Vector3(0.94f, 0.94f, 0.94f), step);
                s.add(at(48, fps), Vector3(1.f, 1.f, 1.f), Easing::easeOut());
                image.animate(FadeIn{.inFrame = 0, .duration = 16});
                break;
            }
            case ImagePixelGrid::GridZoomOut:
                image.animate(ScalePop{.inFrame = 0, .duration = 96, .from = 1.12f, .to = 1.0f})
                     .animate(FadeIn{.inFrame = 0, .duration = 20});
                break;
            case ImagePixelGrid::GridSlideTiles: {
                image.animate(SlideIn{.direction = Direction::Left, .inFrame = 0,
                                      .duration = 72, .distance = 260.f})
                     .animate(FadeIn{.inFrame = 0, .duration = 18});
                // Staggered lattice slide: each bar flies in from its side.
                for (int slot = 0; slot < 4; ++slot) {
                    Layer& barLayer = *scene.motion().findLayer(barIds[slot]);
                    const Bar& bar = bars[slot];
                    const int start = slot * 8;
                    const bool horizontal = slot < 2;
                    const float fromX = horizontal ? (slot == 0 ? -600.f : 600.f) : bar.x;
                    const float fromY = horizontal ? bar.y : (slot == 2 ? -400.f : 400.f);
                    barLayer.tracks.position.add(at(start, fps), Vector3(fromX, fromY, 0.f),
                                                 Easing::easeOut());
                    barLayer.tracks.position.add(at(start + 30, fps), Vector3(bar.x, bar.y, 0.f),
                                                 Easing::easeOut());
                }
                break;
            }
            case ImagePixelGrid::GridBreathe:
                image.animate(FadeIn{.inFrame = 0, .duration = 24});
                chrononmotion::motion::presets::floatHover(hero, 36, 96, 22.f, fps);
                break;
        }

        switch (cameraMove) {
            case ImageCameraMove::None:
                break;
            case ImageCameraMove::Dolly:
                scene.camera().push(3.f).between(8, 126);
                break;
            case ImageCameraMove::Orbit:
                scene.camera().orbit(0.22f, 0.045f).between(8, 126);
                break;
            case ImageCameraMove::DollyOrbit:
                scene.camera().push(3.f).between(8, 66);
                scene.camera().orbit(0.22f, 0.045f).between(66, 126);
                break;
            default:
                throw std::invalid_argument("addImagePixelGrid: unknown camera move");
        }
        image.animate(FadeOut{.startFrame = 132, .duration = 18});
        return image;
    }

}// namespace chronontemplate
