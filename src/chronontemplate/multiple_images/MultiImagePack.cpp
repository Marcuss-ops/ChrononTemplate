#include "chronontemplate/multiple_images/MultiImagePack.hpp"

#include "chrononmotion/motion/Presets.hpp"

#include <algorithm>
#include <cctype>
#include <stdexcept>

namespace chronontemplate {

    namespace {

        using chrononmotion::Vector2;

        /// `assets/card_trio_1.png` -> `CARD TRIO 1` (no directory, no extension).
        std::string labelFromPath(const std::string& assetPath) {
            std::string stem = assetPath;
            const std::size_t slash = stem.find_last_of("/\\");
            if (slash != std::string::npos) stem = stem.substr(slash + 1);
            const std::size_t dot = stem.find_last_of('.');
            if (dot != std::string::npos) stem = stem.substr(0, dot);

            std::string out;
            out.reserve(stem.size());
            bool pendingSpace = false;
            for (const char c : stem) {
                if (c == '_' || c == '-' || c == ' ') {
                    pendingSpace = !out.empty();
                    continue;
                }
                if (pendingSpace) {
                    out.push_back(' ');
                    pendingSpace = false;
                }
                out.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(c))));
            }
            return out;
        }

        [[nodiscard]] int exitFramesFor(const MultiImageSpec& spec) {
            return std::max(1, std::min(18, spec.holdFrames + 1));
        }

    }// namespace

    std::size_t multiImageTileCount(MultiImageLayout layout) {
        switch (layout) {
            case MultiImageLayout::Duo: return 2;
            case MultiImageLayout::Trio: return 3;
            case MultiImageLayout::Quad: return 4;
            case MultiImageLayout::Penta: return 5;
        }
        throw std::invalid_argument("multiImageTileCount: unknown layout");
    }

    std::vector<Vector2> multiImageCells(MultiImageLayout layout) {
        switch (layout) {
            case MultiImageLayout::Duo:
                return {{0.30f, 0.50f}, {0.70f, 0.50f}};
            case MultiImageLayout::Trio:
                return {{0.20f, 0.50f}, {0.50f, 0.50f}, {0.80f, 0.50f}};
            case MultiImageLayout::Quad:
                return {{0.28f, 0.30f}, {0.72f, 0.30f}, {0.28f, 0.70f}, {0.72f, 0.70f}};
            case MultiImageLayout::Penta:
                return {{0.30f, 0.28f}, {0.70f, 0.28f}, {0.16f, 0.72f}, {0.50f, 0.72f}, {0.84f, 0.72f}};
        }
        throw std::invalid_argument("multiImageCells: unknown layout");
    }

    const char* multiImageLayoutId(MultiImageLayout layout) noexcept {
        switch (layout) {
            case MultiImageLayout::Duo: return "multi_image_duo";
            case MultiImageLayout::Trio: return "multi_image_trio";
            case MultiImageLayout::Quad: return "multi_image_quad";
            case MultiImageLayout::Penta: return "multi_image_penta";
        }
        return "unknown";
    }

    std::string multiImageTileLabel(const std::string& assetPath) {
        return labelFromPath(assetPath);
    }

    MultiImageBoard addMultiImageBoard(TemplateScene& scene, const MultiImageSpec& spec) {
        const std::size_t expected = multiImageTileCount(spec.layout);
        if (spec.tiles.size() != expected) {
            throw std::invalid_argument(
                    "addMultiImageBoard: the tile count does not match the layout");
        }
        if (!(spec.tileWidth > 0.f) || !(spec.tileHeight > 0.f) || !(spec.gap >= 0.f) ||
            spec.duration <= 0 || spec.holdFrames < 0) {
            throw std::invalid_argument(
                    "addMultiImageBoard: positive tile size and duration are required");
        }
        for (const MultiImageTile& tile : spec.tiles) {
            if (tile.path.empty()) {
                throw std::invalid_argument("addMultiImageBoard: every tile needs an asset path");
            }
        }

        const std::vector<Vector2> cells = multiImageCells(spec.layout);
        const Vector2 canvas = scene.canvas();
        const int count = static_cast<int>(cells.size());
        const int stagger = std::max(1, spec.duration / (count + 1));
        const int endFrame = spec.inFrame + spec.duration + spec.holdFrames;
        const int exitFrames = exitFramesFor(spec);
        const int exitStart = endFrame - exitFrames;

        MultiImageBoard board;
        board.inFrame = spec.inFrame;
        board.tiles.reserve(cells.size());
        board.captions.reserve(cells.size());

        for (std::size_t i = 0; i < cells.size(); ++i) {
            const MultiImageTile& tile = spec.tiles[i];
            const Vector2 cell = cells[i];
            const float x = canvas.x * cell.x;
            const float y = canvas.y * cell.y;
            const int start = spec.inFrame + static_cast<int>(i) * stagger;
            const int enterDuration = std::max(1, stagger);
            const int moveDuration = std::max(2, stagger * 2);

            LayerHandle& image = scene.image(ImageSpec{
                    .path = tile.path,
                    .name = "tile_" + std::to_string(i),
                    .frame = tile.frame,
                    .targetSize = Vector2(spec.tileWidth, spec.tileHeight)});
            image.position(x, y);
            image.alive(spec.inFrame, endFrame);
            switch (spec.entrance) {
                case MultiImageEntrance::Fade:
                    image.animate(FadeIn{.inFrame = start, .duration = enterDuration});
                    break;
                case MultiImageEntrance::Rise:
                    image.animate(SlideIn{
                                     .direction = chrononmotion::motion::presets::Direction::Up,
                                     .inFrame = start,
                                     .duration = moveDuration,
                                     .distance = spec.tileHeight * 0.5f})
                            .animate(FadeIn{.inFrame = start, .duration = enterDuration});
                    break;
                case MultiImageEntrance::ScalePop:
                    image.animate(ScalePop{.inFrame = start, .duration = moveDuration,
                                           .from = 0.72f, .to = 1.f})
                            .animate(FadeIn{.inFrame = start, .duration = enterDuration});
                    break;
            }
            image.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
            board.tiles.push_back(&image);

            const std::string caption =
                    tile.caption.empty() ? multiImageTileLabel(tile.path) : tile.caption;
            if (!caption.empty()) {
                LayerHandle& text = scene.text(TextSpec{.text = caption,
                                                        .font = spec.captionFont,
                                                        .fontSize = spec.captionFontSize,
                                                        .color = spec.captionColor,
                                                        .name = "caption_" + std::to_string(i)});
                text.position(x, y + spec.tileHeight * 0.5f + spec.captionOffset);
                text.alive(spec.inFrame, endFrame);
                text.animate(FadeIn{.inFrame = start + std::max(1, stagger / 2),
                                    .duration = enterDuration});
                text.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
                board.captions.push_back(&text);
            }
        }

        board.endFrame = endFrame;
        return board;
    }

}// namespace chronontemplate
