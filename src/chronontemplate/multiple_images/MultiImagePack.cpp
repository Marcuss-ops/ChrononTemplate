#include "chronontemplate/multiple_images/MultiImagePack.hpp"

#include "chrononmotion/math/MathUtils.hpp"
#include "chrononmotion/motion/Presets.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace chronontemplate {

    namespace {

        using chrononmotion::Vector2;
        using Direction = chrononmotion::motion::presets::Direction;

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

        /// Polaroid framing: white border on three sides, deeper bottom strip.
        constexpr float kPolaroidBorder = 18.f;
        constexpr float kPolaroidBottom = 58.f;

        /// The look each style gives the board: the plate, the tile frame and
        /// the caption typography. Colors follow the editorial reference
        /// boards (light archive plate, aged sepia paper, dark polaroid wall).
        struct StyleLook {
            std::string plate{};              ///< full-canvas backing color; empty draws none
            float plateNoise{0.f};
            float plateNoiseSize{1.f};
            float cornerRadius{24.f};
            float tornEdge{0.f};
            float captionSize{36.f};
            std::string captionFont{"Chronon3d/assets/fonts/Inter-Bold.ttf"};
            std::string captionColor{"#FFFFFF"};
            float captionOffset{26.f};
            float tiltStepDegrees{0.f};    ///< per-tile fan tilt; zero keeps tiles upright
            float shadowOffset{0.f};        ///< drop shadow distance; zero draws no shadow
            float shadowOpacity{0.f};
            std::string headerInk{};        ///< archival header ink; empty draws no header
        };

        [[nodiscard]] StyleLook lookFor(MultiImageStyle style, const MultiImageSpec& spec) {
            StyleLook look;
            look.captionFont = spec.captionFont;
            look.captionSize = spec.captionFontSize;
            look.captionColor = spec.captionColor;
            look.captionOffset = spec.captionOffset;
            switch (style) {
                case MultiImageStyle::Classic:
                    return look;
                case MultiImageStyle::ArchiveBoard:
                    look.plate = "#D9D9D6";
                    look.plateNoise = 0.22f;
                    look.plateNoiseSize = 1.6f;
                    look.cornerRadius = 28.f;
                    look.captionFont = "Chronon3d/assets/fonts/Inter-Bold.ttf";
                    look.captionColor = "#FFFFFF";
                    look.captionSize = 40.f;
                    look.shadowOffset = 16.f;
                    look.shadowOpacity = 0.32f;
                    look.headerInk = "#2A2A28";
                    return look;
                case MultiImageStyle::SepiaTorn:
                    look.plate = "#E4D2B4";
                    look.plateNoise = 0.38f;
                    look.plateNoiseSize = 1.2f;
                    look.cornerRadius = 0.f;
                    look.tornEdge = 7.f;
                    look.captionFont = "Chronon3d/assets/fonts/Georgia_Bold.ttf";
                    look.captionColor = "#2E2114";
                    look.captionSize = 42.f;
                    look.captionOffset = 30.f;
                    look.shadowOffset = 10.f;
                    look.shadowOpacity = 0.22f;
                    look.headerInk = "#3B2B1A";
                    return look;
                case MultiImageStyle::PolaroidFan:
                    look.plate = "#201F1D";
                    look.plateNoise = 0.45f;
                    look.plateNoiseSize = 2.2f;
                    look.cornerRadius = 2.f;
                    look.captionFont = "Chronon3d/assets/fonts/Inter-Regular.ttf";
                    look.captionColor = "#3A352C";
                    look.captionSize = 22.f;
                    look.tiltStepDegrees = 7.f;
                    look.shadowOffset = 12.f;
                    look.shadowOpacity = 0.38f;
                    return look;
            }
            return look;
        }

        /// How one tile enters: a slide along a direction, a pop, or a plain rise.
        enum class Enter : std::uint8_t { Slide, Pop, Rise };

        struct Beat {
            int start{0};        ///< frame offset from the board's inFrame
            int enter{1};        ///< frames the entrance takes
            Enter kind{Enter::Rise};
            Direction dir{Direction::Up};
        };

        /// The certified choreography of each layout as a per-tile beat schedule.
        /// `s` is the stagger step; every start stays inside the duration.
        std::vector<Beat> beatsFor(MultiImageLayout layout, const std::string& motionId,
                                   int count, int duration) {
            const int s = std::max(1, duration / (count + 1));
            const int half = std::max(1, s / 2);
            std::vector<Beat> beats(static_cast<std::size_t>(count));
            auto at = [&](std::size_t i) -> Beat& { return beats[i]; };

            switch (layout) {
                case MultiImageLayout::Duo:
                    if (motionId == "duo_split_reveal") {
                        // Both cards slide in from opposite edges at once.
                        at(0) = {0, std::max(1, duration / 2), Enter::Slide, Direction::Right};
                        at(1) = {0, std::max(1, duration / 2), Enter::Slide, Direction::Left};
                    } else if (motionId == "duo_soft_bloom_rise") {
                        // Soft bloom rise, left leads: both cards rise from below,
                        // the right card follows half a stagger step later.
                        at(0) = {0, std::max(1, duration / 2), Enter::Rise, Direction::Up};
                        at(1) = {half, std::max(1, duration / 2), Enter::Rise, Direction::Up};
                    } else if (motionId == "duo_soft_drift_settle") {
                        // Slow lateral drift inward: the cards settle from the
                        // outer edges, the right card a stagger step later.
                        at(0) = {0, std::max(1, duration / 2), Enter::Slide, Direction::Left};
                        at(1) = {s, s, Enter::Slide, Direction::Right};
                    } else if (motionId == "duo_soft_cross_bloom") {
                        // Simultaneous soft bloom: both cards bloom in place together.
                        at(0) = {0, std::max(1, duration / 2), Enter::Pop, Direction::Up};
                        at(1) = {0, std::max(1, duration / 2), Enter::Pop, Direction::Up};
                    } else if (motionId == "duo_soft_breathe_hold") {
                        // Joint fade with calm settle: both cards rise together
                        // over a long shared entrance.
                        at(0) = {0, 2 * s, Enter::Rise, Direction::Up};
                        at(1) = {0, 2 * s, Enter::Rise, Direction::Up};
                    } else if (motionId == "duo_soft_stagger_glow") {
                        // Staggered opacity-led entrances: the left card glows
                        // in first over a long entrance, the right card follows.
                        at(0) = {0, 2 * s, Enter::Pop, Direction::Up};
                        at(1) = {s, s, Enter::Pop, Direction::Up};
                    } else {  // duo_cross_focus: the first pops, then the second cross-focuses in
                        at(0) = {0, s, Enter::Pop, Direction::Up};
                        at(1) = {s, s, Enter::Pop, Direction::Up};
                    }
                    break;
                case MultiImageLayout::Trio:
                    if (motionId == "trio_fan_reveal") {
                        // The three cards fan up in reading order.
                        for (std::size_t i = 0; i < 3; ++i) {
                            at(i) = {static_cast<int>(i) * s, s, Enter::Slide, Direction::Up};
                        }
                    } else {  // trio_center_priority: the hero pops first, the sides follow
                        at(1) = {0, s, Enter::Pop, Direction::Up};
                        at(0) = {s, s, Enter::Slide, Direction::Right};
                        at(2) = {s, s, Enter::Slide, Direction::Left};
                    }
                    break;
                case MultiImageLayout::Quad:
                    if (motionId == "quad_grid_assemble") {
                        // Reading order cascade: each card rises into its cell.
                        for (std::size_t i = 0; i < 4; ++i) {
                            at(i) = {static_cast<int>(i) * s, s, Enter::Rise, Direction::Up};
                        }
                    } else {  // quad_corner_converge: the left column slides in, the right follows
                        at(0) = {0, s, Enter::Slide, Direction::Right};
                        at(2) = {0, s, Enter::Slide, Direction::Right};
                        at(1) = {s, s, Enter::Slide, Direction::Left};
                        at(3) = {s, s, Enter::Slide, Direction::Left};
                    }
                    break;
                case MultiImageLayout::Penta:
                    if (motionId == "penta_hero_plus_four") {
                        // The top-left hero pops first; the other four rise after it.
                        at(0) = {0, 2 * s, Enter::Pop, Direction::Up};
                        for (std::size_t i = 1; i < 5; ++i) {
                            at(i) = {2 * s + static_cast<int>(i - 1) * half, s, Enter::Rise, Direction::Up};
                        }
                    } else {  // penta_priority_cycle: each card pops in priority order
                        for (std::size_t i = 0; i < 5; ++i) {
                            at(i) = {static_cast<int>(i) * s, s, Enter::Pop, Direction::Up};
                        }
                    }
                    break;
            }
            return beats;
        }

        const std::vector<std::string>& motionIdsFor(MultiImageLayout layout) {
            static const std::vector<std::string> duo{"duo_split_reveal", "duo_cross_focus",
                                                      "duo_soft_bloom_rise", "duo_soft_drift_settle",
                                                      "duo_soft_cross_bloom", "duo_soft_breathe_hold",
                                                      "duo_soft_stagger_glow"};
            static const std::vector<std::string> trio{"trio_fan_reveal", "trio_center_priority"};
            static const std::vector<std::string> quad{"quad_grid_assemble", "quad_corner_converge"};
            static const std::vector<std::string> penta{"penta_hero_plus_four", "penta_priority_cycle"};
            switch (layout) {
                case MultiImageLayout::Duo: return duo;
                case MultiImageLayout::Trio: return trio;
                case MultiImageLayout::Quad: return quad;
                case MultiImageLayout::Penta: return penta;
            }
            throw std::invalid_argument("motionIdsFor: unknown layout");
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

    const char* multiImageStyleId(MultiImageStyle style) noexcept {
        switch (style) {
            case MultiImageStyle::Classic: return "multi_image_classic";
            case MultiImageStyle::ArchiveBoard: return "multi_image_archive_board";
            case MultiImageStyle::SepiaTorn: return "multi_image_sepia_torn";
            case MultiImageStyle::PolaroidFan: return "multi_image_polaroid_fan";
        }
        return "unknown";
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

    std::vector<std::string> multiImageMotionIds(MultiImageLayout layout) {
        return motionIdsFor(layout);
    }

    bool isMultiImageMotion(MultiImageLayout layout, const std::string& motionId) {
        const std::vector<std::string>& ids = motionIdsFor(layout);
        return std::find(ids.begin(), ids.end(), motionId) != ids.end();
    }

    std::string selectMultiImageMotion(MultiImageLayout layout, const std::string& seed,
                                       const std::string& previous) {
        const std::vector<std::string>& ids = motionIdsFor(layout);
        std::vector<const std::string*> candidates;
        candidates.reserve(ids.size());
        for (const std::string& id : ids) {
            if (id != previous) candidates.push_back(&id);
        }
        if (candidates.empty()) {
            for (const std::string& id : ids) candidates.push_back(&id);
        }
        // FNV-1a is used here instead of std::hash so a saved seed selects the
        // same choreography across processes, standard libraries and retries.
        std::uint64_t hash = 1469598103934665ULL;
        for (const unsigned char byte : seed) {
            hash ^= byte;
            hash *= 1099511628211ULL;
        }
        const std::string layoutName = multiImageLayoutId(layout);
        for (const unsigned char byte : layoutName) {
            hash ^= byte;
            hash *= 1099511628211ULL;
        }
        return *candidates[static_cast<std::size_t>(hash % candidates.size())];
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
        if (spec.headerLabel.size() > 64 || spec.headerSubtitle.size() > 96) {
            throw std::invalid_argument(
                    "addMultiImageBoard: header label (<= 64) or subtitle (<= 96) is too long");
        }
        std::string selectedMotion = spec.motionId;
        if (selectedMotion == "random") {
            std::string seed = spec.motionSeed;
            if (seed.empty()) {
                seed = scene.name();
                seed.push_back('\0');
                seed += multiImageLayoutId(spec.layout);
                for (const MultiImageTile& tile : spec.tiles) {
                    seed.push_back('\0');
                    seed += tile.path;
                }
            }
            selectedMotion = selectMultiImageMotion(spec.layout, seed);
        }
        if (!selectedMotion.empty() && !isMultiImageMotion(spec.layout, selectedMotion)) {
            throw std::invalid_argument(
                    "addMultiImageBoard: the motion is not certified for this layout");
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

        // With no certified motion the shared entrance staggers the grid as before.
        const bool certified = !selectedMotion.empty();
        const std::vector<Beat> beats = certified
                ? beatsFor(spec.layout, selectedMotion, count, spec.duration)
                : std::vector<Beat>{};

        using chrononmotion::Vector3;
        using chrononmotion::motion::Easing;

        const StyleLook look = lookFor(spec.style, spec);
        const bool styled = spec.style != MultiImageStyle::Classic;

        MultiImageBoard board;
        board.motionId = selectedMotion;
        board.inFrame = spec.inFrame;
        board.tiles.reserve(cells.size());
        board.captions.reserve(cells.size());

        if (styled && !look.plate.empty()) {
            LayerHandle& plate = scene.shape(ShapeSpec{.size = canvas,
                                                      .fillColor = look.plate,
                                                      .name = "board_plate",
                                                      .noiseAmount = look.plateNoise,
                                                      .noiseSeed = 7,
                                                      .noiseSize = look.plateNoiseSize});
            plate.position(canvas.x * 0.5f, canvas.y * 0.5f);
            plate.alive(spec.inFrame, endFrame);
            plate.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
        }

        if (styled && !look.headerInk.empty() &&
            (!spec.headerLabel.empty() || !spec.headerSubtitle.empty())) {
            const float hx = canvas.x * 0.055f;
            float hy = canvas.y * 0.105f;
            if (!spec.headerLabel.empty()) {
                LayerHandle& label = scene.text(TextSpec{.text = spec.headerLabel,
                                                        .font = "Chronon3d/assets/fonts/Inter-Bold.ttf",
                                                        .fontSize = 22.f,
                                                        .color = look.headerInk,
                                                        .name = "board_header_label"});
                label.position(hx + 60.f, hy);
                label.alive(spec.inFrame, endFrame);
                label.animate(FadeIn{.inFrame = spec.inFrame, .duration = 12});
                label.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
                hy += 22.f;
            }
            {
                LayerHandle& rule = scene.shape(ShapeSpec{.size = {150.f, 2.f},
                                                          .fillColor = look.headerInk,
                                                          .name = "board_header_rule"});
                rule.position(hx + 60.f, hy);
                rule.alive(spec.inFrame, endFrame);
                rule.animate(FadeIn{.inFrame = spec.inFrame, .duration = 12});
                rule.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
                hy += 24.f;
            }
            if (!spec.headerSubtitle.empty()) {
                LayerHandle& subtitle = scene.text(TextSpec{.text = spec.headerSubtitle,
                                                           .font = "Chronon3d/assets/fonts/Inter-Bold.ttf",
                                                           .fontSize = 18.f,
                                                           .color = look.headerInk,
                                                           .name = "board_header_subtitle"});
                subtitle.position(hx + 120.f, hy);
                subtitle.alive(spec.inFrame, endFrame);
                subtitle.animate(FadeIn{.inFrame = spec.inFrame, .duration = 12});
                subtitle.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
            }
        }

        for (std::size_t i = 0; i < cells.size(); ++i) {
            const MultiImageTile& tile = spec.tiles[i];
            const Vector2 cell = cells[i];
            const float x = canvas.x * cell.x;
            const float y = canvas.y * cell.y;

            // The fan look leans the outer tiles outward around an upright
            // center tile; every other style keeps the grid square.
            const float tiltDegrees = look.tiltStepDegrees == 0.f
                    ? 0.f
                    : (static_cast<float>(i) -
                       static_cast<float>(cells.size() - 1) * 0.5f) * look.tiltStepDegrees;
            const float tiltRadians = chrononmotion::math::degToRad(tiltDegrees);

            int start = spec.inFrame + static_cast<int>(i) * stagger;
            int enterDuration = std::max(1, stagger);
            int moveDuration = std::max(2, stagger * 2);
            Enter kind = Enter::Rise;
            Direction dir = Direction::Up;
            if (certified) {
                const Beat& beat = beats[i];
                start = spec.inFrame + beat.start;
                enterDuration = beat.enter;
                moveDuration = std::max(2, beat.enter);
                kind = beat.kind;
                dir = beat.dir;
            }

            ImageFrameStyle frame = tile.frame;
            if (styled) {
                frame.cornerRadius = look.cornerRadius;
                frame.tornEdgeAmount = look.tornEdge;
                if (look.tornEdge > 0.f) {
                    frame.tornEdgeSeed = 1000u + static_cast<std::uint32_t>(i);
                }
            }

            if (styled && look.shadowOpacity > 0.f) {
                LayerHandle& shadow = scene.shape(ShapeSpec{
                        .size = {spec.tileWidth, spec.tileHeight},
                        .fillColor = "#000000",
                        .name = "tile_shadow_" + std::to_string(i),
                        .cornerRadius = look.cornerRadius});
                shadow.position(x + look.shadowOffset, y + look.shadowOffset);
                shadow.opacity(look.shadowOpacity);
                shadow.alive(spec.inFrame, endFrame);
                shadow.layer().tracks.rotation.add(
                        0.f, Vector3(0.f, 0.f, tiltRadians), Easing::easeOut());
                shadow.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
            }
            if (styled && spec.style == MultiImageStyle::PolaroidFan) {
                // The polaroid card: white frame around the print with the
                // classic deeper bottom strip the caption sits on.
                LayerHandle& card = scene.shape(ShapeSpec{
                        .size = {spec.tileWidth + 2.f * kPolaroidBorder,
                                 spec.tileHeight + kPolaroidBorder + kPolaroidBottom},
                        .fillColor = "#F6F2E9",
                        .name = "polaroid_frame_" + std::to_string(i),
                        .cornerRadius = look.cornerRadius});
                card.position(x, y + (kPolaroidBottom - kPolaroidBorder) * 0.5f);
                card.alive(spec.inFrame, endFrame);
                card.layer().tracks.rotation.add(
                        0.f, Vector3(0.f, 0.f, tiltRadians), Easing::easeOut());
                card.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
            }

            LayerHandle& image = scene.image(ImageSpec{
                    .path = tile.path,
                    .name = "tile_" + std::to_string(i),
                    .frame = frame,
                    .targetSize = Vector2(spec.tileWidth, spec.tileHeight)});
            image.position(x, y);
            image.alive(spec.inFrame, endFrame);
            if (tiltDegrees != 0.f) {
                image.layer().tracks.rotation.add(
                        0.f, Vector3(0.f, 0.f, tiltRadians), Easing::easeOut());
            }

            if (certified) {
                switch (kind) {
                    case Enter::Slide:
                        image.animate(SlideIn{.direction = dir,
                                              .inFrame = start,
                                              .duration = moveDuration,
                                              .distance = spec.tileWidth * 0.5f})
                                .animate(FadeIn{.inFrame = start, .duration = enterDuration});
                        break;
                    case Enter::Pop:
                        image.animate(ScalePop{.inFrame = start, .duration = moveDuration,
                                               .from = 0.72f, .to = 1.f})
                                .animate(FadeIn{.inFrame = start, .duration = enterDuration});
                        break;
                    case Enter::Rise:
                        image.animate(SlideIn{.direction = Direction::Up,
                                              .inFrame = start,
                                              .duration = moveDuration,
                                              .distance = spec.tileHeight * 0.5f})
                                .animate(FadeIn{.inFrame = start, .duration = enterDuration});
                        break;
                }
            } else {
                switch (spec.entrance) {
                    case MultiImageEntrance::Fade:
                        image.animate(FadeIn{.inFrame = start, .duration = enterDuration});
                        break;
                    case MultiImageEntrance::Rise:
                        image.animate(SlideIn{
                                         .direction = Direction::Up,
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
            }
            image.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
            board.tiles.push_back(&image);

            const std::string caption =
                    tile.caption.empty() ? multiImageTileLabel(tile.path) : tile.caption;
            if (!caption.empty()) {
                LayerHandle& text = scene.text(TextSpec{.text = caption,
                                                        .font = look.captionFont,
                                                        .fontSize = look.captionSize,
                                                        .color = look.captionColor,
                                                        .name = "caption_" + std::to_string(i)});
                const bool onStrip = spec.style == MultiImageStyle::PolaroidFan;
                const float captionDrop = onStrip
                        ? spec.tileHeight * 0.5f + kPolaroidBottom * 0.5f
                        : spec.tileHeight * 0.5f + look.captionOffset;
                // The caption rides its card's tilt: the drop vector rotates
                // with the tile so the label stays on the bottom edge/strip.
                text.position(x - captionDrop * std::sin(tiltRadians),
                              y + captionDrop * std::cos(tiltRadians));
                if (tiltDegrees != 0.f) {
                    text.layer().tracks.rotation.add(
                            0.f, Vector3(0.f, 0.f, tiltRadians), Easing::easeOut());
                }
                text.alive(spec.inFrame, endFrame);
                text.animate(FadeIn{.inFrame = start + std::max(1, enterDuration / 2),
                                    .duration = std::max(1, enterDuration)});
                text.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
                board.captions.push_back(&text);
            }
        }

        board.endFrame = endFrame;
        return board;
    }

}// namespace chronontemplate
