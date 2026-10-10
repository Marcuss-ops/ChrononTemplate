#include "chronontemplate/composers/LayoutComposer.hpp"

#include <cmath>
#include <stdexcept>

namespace chronontemplate {

    namespace {

        using Vector2 = chrononmotion::Vector2;
        using Vector3 = chrononmotion::Vector3;
        using chrononmotion::motion::Easing;
        using chrononmotion::motion::Track;

        [[nodiscard]] inline float frameTime(const int frame, const float fps) {
            return chrononmotion::motion::frameToTime(frame, fps);
        }

    }// namespace

    const char* layoutDirectionId(LayoutDirection direction) noexcept {
        switch (direction) {
            case LayoutDirection::Row: return "composer_row";
            case LayoutDirection::Column: return "composer_column";
            case LayoutDirection::Grid: return "composer_grid";
        }
        return "unknown";
    }

    std::vector<LayoutCell> layoutCells(std::size_t count, float canvasW, float canvasH,
                                        float margin, float gap,
                                        LayoutDirection direction, int columns) {
        if (count == 0 || count > 9) {
            throw std::invalid_argument("layoutCells: expected between 1 and 9 tiles");
        }
        if (!(canvasW > 0.f) || !(canvasH > 0.f)) {
            throw std::invalid_argument("layoutCells: the canvas must be positive");
        }
        if (!(margin >= 0.f) || !(gap >= 0.f) || margin * 2.f >= canvasW || margin * 2.f >= canvasH) {
            throw std::invalid_argument("layoutCells: degenerate margin or gap");
        }
        int cols = 1;
        int rows = 1;
        switch (direction) {
            case LayoutDirection::Row:
                cols = static_cast<int>(count);
                rows = 1;
                break;
            case LayoutDirection::Column:
                cols = 1;
                rows = static_cast<int>(count);
                break;
            case LayoutDirection::Grid:
                if (columns > 0) {
                    cols = columns;
                } else {
                    cols = static_cast<int>(std::ceil(std::sqrt(static_cast<double>(count))));
                }
                if (cols <= 0) {
                    throw std::invalid_argument("layoutCells: the column count must be positive");
                }
                rows = static_cast<int>((count + static_cast<std::size_t>(cols) - 1) /
                                        static_cast<std::size_t>(cols));
                break;
        }
        const float innerW = canvasW - margin * 2.f;
        const float innerH = canvasH - margin * 2.f;
        const float cellW = (innerW - gap * static_cast<float>(cols - 1)) / static_cast<float>(cols);
        const float cellH = (innerH - gap * static_cast<float>(rows - 1)) / static_cast<float>(rows);
        if (!(cellW > 0.f) || !(cellH > 0.f)) {
            throw std::invalid_argument("layoutCells: the gap leaves no room for cells");
        }
        std::vector<LayoutCell> out;
        out.reserve(count);
        for (std::size_t i = 0; i < count; ++i) {
            const int col = static_cast<int>(i) % cols;
            const int row = static_cast<int>(i) / cols;
            out.push_back(LayoutCell{margin + static_cast<float>(col) * (cellW + gap),
                                     margin + static_cast<float>(row) * (cellH + gap),
                                     cellW, cellH});
        }
        return out;
    }

    ComposerBoard addComposerBoard(TemplateScene& scene, const ComposerSpec& spec) {
        if (spec.tiles.empty() || spec.tiles.size() > 9) {
            throw std::invalid_argument("addComposerBoard: expected between 1 and 9 tiles");
        }
        if (spec.duration <= 0 || spec.holdFrames < 0) {
            throw std::invalid_argument("addComposerBoard: positive duration is required");
        }
        for (const ComposerTile& tile : spec.tiles) {
            if (tile.path.empty()) {
                throw std::invalid_argument("addComposerBoard: every tile needs an asset path");
            }
        }
        const Vector2 canvas = scene.canvas();
        const std::vector<LayoutCell> cells = layoutCells(spec.tiles.size(), canvas.x, canvas.y,
                                                          spec.margin, spec.gap,
                                                          spec.direction, spec.columns);
        const int count = static_cast<int>(cells.size());
        const int stagger = std::max(1, spec.duration / (count + 1));
        const int endFrame = spec.inFrame + spec.duration + spec.holdFrames;

        ComposerBoard board;
        board.inFrame = spec.inFrame;
        board.endFrame = endFrame;
        board.cells = cells;
        board.captionOffset = spec.captionFontSize * 0.6f;
        board.tiles.reserve(cells.size());

        for (std::size_t i = 0; i < cells.size(); ++i) {
            const LayoutCell& cell = cells[i];
            const int start = spec.inFrame + static_cast<int>(i) * stagger;
            LayerHandle& image = scene.image(ImageSpec{.path = spec.tiles[i].path,
                                                       .name = spec.name + "_tile_" + std::to_string(i),
                                                       .frame = {.cornerRadius = spec.tileCornerRadius},
                                                       .targetSize = Vector2(cell.w, cell.h)});
            image.position(cell.x + cell.w * 0.5f, cell.y + cell.h * 0.5f)
                 .alive(spec.inFrame, endFrame);
            image.animate(SlideIn{.direction = chrononmotion::motion::presets::Direction::Up,
                                  .inFrame = start,
                                  .duration = std::max(2, stagger * 2),
                                  .distance = cell.h * 0.25f})
                 .animate(FadeIn{.inFrame = start, .duration = std::max(1, stagger)});
            board.tiles.push_back(&image);

            const std::string& caption = spec.tiles[i].caption;
            if (!caption.empty()) {
                LayerHandle& text = scene.text(TextSpec{.text = caption,
                                                        .font = spec.captionFont,
                                                        .fontSize = spec.captionFontSize,
                                                        .color = spec.captionColor,
                                                        .name = spec.name + "_caption_" + std::to_string(i)});
                text.position(cell.x + cell.w * 0.5f, cell.y + cell.h + spec.captionFontSize * 0.6f)
                    .alive(spec.inFrame, endFrame);
                text.animate(FadeIn{.inFrame = start + stagger / 2, .duration = std::max(1, stagger)});
                board.captions.push_back(&text);
            }
        }
        return board;
    }

    void morphComposerBoard(TemplateScene& scene, ComposerBoard& board,
                            const std::vector<LayoutCell>& newCells,
                            int inFrame, int duration) {
        if (newCells.size() != board.tiles.size()) {
            throw std::invalid_argument("morphComposerBoard: the cell count must match the board");
        }
        if (duration < 2 || inFrame < 0) {
            throw std::invalid_argument("morphComposerBoard: the morph needs at least 2 frames");
        }
        const float fps = scene.fps();
        for (std::size_t i = 0; i < board.tiles.size(); ++i) {
            const LayoutCell& from = board.cells[i];
            const LayoutCell& to = newCells[i];
            const Vector3 a(from.x + from.w * 0.5f, from.y + from.h * 0.5f, 0.f);
            const Vector3 b(to.x + to.w * 0.5f, to.y + to.h * 0.5f, 0.f);
            Track<Vector3>& pos = board.tiles[i]->layer().tracks.position;
            pos.add(frameTime(inFrame, fps), a, Easing::easeInOut());
            pos.add(frameTime(inFrame + duration, fps), b, Easing::easeInOut());
            if (i < board.captions.size()) {
                const float ay = from.y + from.h + board.captionOffset;
                const float by = to.y + to.h + board.captionOffset;
                Track<Vector3>& cap = board.captions[i]->layer().tracks.position;
                cap.add(frameTime(inFrame, fps), Vector3(a.x, ay, 0.f), Easing::easeInOut());
                cap.add(frameTime(inFrame + duration, fps), Vector3(b.x, by, 0.f), Easing::easeInOut());
            }
        }
        board.cells = newCells;
    }

}// namespace chronontemplate
