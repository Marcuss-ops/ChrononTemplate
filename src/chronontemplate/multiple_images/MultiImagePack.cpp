#include "chronontemplate/multiple_images/MultiImagePack.hpp"

#include "chrononmotion/math/MathUtils.hpp"
#include "chrononmotion/motion/Presets.hpp"

#include <algorithm>
#include <array>
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
            float softBlur{0.f};            ///< subtle optical softness on the print
            std::string haloColor{};        ///< soft glow frame behind each card; empty draws none
            float haloPadding{18.f};
            float haloGlowRadius{40.f};
            float haloGlowIntensity{0.8f};
            float haloOpacity{0.22f};
            bool dreamGlow{false};          ///< broad radial aura behind the whole board
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
                case MultiImageStyle::SoftDream:
                    // Deep indigo plate with a broad radial aura, feathered
                    // rounded prints and a soft accent rim behind every card.
                    look.plate = "#070A18";
                    look.plateNoise = 0.26f;
                    look.plateNoiseSize = 1.5f;
                    look.cornerRadius = 64.f;
                    look.captionFont = "Chronon3d/assets/fonts/Inter-Regular.ttf";
                    look.captionColor = "#EDE9FF";
                    look.captionSize = 30.f;
                    look.captionOffset = 30.f;
                    look.softBlur = 1.2f;
                    look.haloColor = "#7B6BFF";
                    look.haloPadding = 20.f;
                    look.haloGlowRadius = 44.f;
                    look.haloGlowIntensity = 0.9f;
                    look.haloOpacity = 0.24f;
                    look.dreamGlow = true;
                    return look;
            }
            return look;
        }

        /// How one tile enters: a slide along a direction, a pop, or a plain rise.
        enum class Enter : std::uint8_t { Slide, Pop, Rise, Fade, SoftZoom, SoftLift, SoftDrift, Settle };

        struct Beat {
            int start{0};        ///< frame offset from the board's inFrame
            int enter{1};        ///< frames the entrance takes
            Enter kind{Enter::Rise};
            Direction dir{Direction::Up};
            // Premium motions add one emphasis pass after the tile has entered:
            // the card eases forward in depth, takes a slight scale/tilt or
            // parallax emphasis, then settles back into its cell. Zero focusAt
            // keeps the classic entrance-only behaviour.
            int focusAt{0};             ///< frame offset from the board's inFrame
            int focusHold{0};           ///< frames the emphasis is held
            float focusScale{1.f};      ///< peak scale during the emphasis
            float focusDepth{0.f};      ///< peak z offset during the emphasis
            float focusDriftX{0.f};     ///< peak x offset during the emphasis
            float focusDriftY{0.f};     ///< peak y offset during the emphasis
            float focusTiltDegrees{0.f};///< peak rotation during the emphasis
        };

        /// One certification row per reusable group choreography. The public
        /// id list and the beat schedule both derive from this table; adding a
        /// motion here is what makes it reachable, and the catalog emitter
        /// fails if the row has no matching `image_group_v1` catalog entry.
        struct ReusableMotion {
            const char* id;
            Direction direction;
            Enter enter;
        };

        const std::array<ReusableMotion, 14>& reusableMotions() {
            static constexpr std::array<ReusableMotion, 14> motions{{
                    {"image_group_slide_right", Direction::Right, Enter::Slide},
                    {"image_group_slide_left", Direction::Left, Enter::Slide},
                    {"image_group_slide_in", Direction::Up, Enter::Pop},
                    {"image_group_slide_down", Direction::Down, Enter::Slide},
                    {"image_group_slide_up", Direction::Up, Enter::Slide},
                    {"image_group_soft_fade", Direction::Up, Enter::Fade},
                    {"image_group_gentle_zoom", Direction::Up, Enter::SoftZoom},
                    {"image_group_soft_lift", Direction::Up, Enter::SoftLift},
                    {"image_group_diagonal_drift", Direction::Up, Enter::SoftDrift},
                    {"image_group_depth_settle", Direction::Up, Enter::Settle},
                    {"image_group_camera_pan_right", Direction::Right, Enter::Slide},
                    {"image_group_camera_pan_left", Direction::Left, Enter::Slide},
                    {"image_group_camera_pan_down", Direction::Down, Enter::Slide},
                    {"image_group_camera_pan_up", Direction::Up, Enter::Slide},
            }};
            return motions;
        }

        /// The certified choreography of each layout as a per-tile beat schedule.
        /// `s` is the stagger step; every start stays inside the duration.
        std::vector<Beat> beatsFor(MultiImageLayout layout, const std::string& motionId,
                                   int count, int duration) {
            const int s = std::max(1, duration / (count + 1));
            const int half = std::max(1, s / 2);
            std::vector<Beat> beats(static_cast<std::size_t>(count));
            auto at = [&](std::size_t i) -> Beat& { return beats[i]; };
            auto focus = [&](std::size_t i, int atFrame, int hold, float scale, float depth,
                             float driftX, float driftY, float tilt) {
                Beat& beat = beats[i];
                beat.focusAt = atFrame;
                beat.focusHold = hold;
                beat.focusScale = scale;
                beat.focusDepth = depth;
                beat.focusDriftX = driftX;
                beat.focusDriftY = driftY;
                beat.focusTiltDegrees = tilt;
            };

            // Reusable transitions derive their stagger from the number of
            // tiles at render time. The motion itself stays the same for duo,
            // trio, quad and penta instead of maintaining per-count tracks.
            if (motionId.rfind("image_group_", 0) == 0) {
                const auto& motions = reusableMotions();
                const auto motion = std::find_if(
                        motions.begin(), motions.end(),
                        [&](const ReusableMotion& candidate) { return motionId == candidate.id; });
                if (motion == motions.end()) {
                    throw std::invalid_argument("beatsFor: uncertified reusable group motion");
                }
                const Direction direction = motion->direction;
                const Enter enter = motion->enter;
                const int move = std::max(12, std::min(24, duration / std::max(2, count)));
                const int step = std::max(1, (duration - move) / std::max(1, count));
                for (int i = 0; i < count; ++i) {
                    at(static_cast<std::size_t>(i)) = {i * step, move, enter, direction};
                }
                return beats;
            }

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
                    } else if (motionId == "duo_cinematic_parallax") {
                        // Cinematic two-shot: the cards settle in from opposite
                        // sides, then the focus travels left -> right with a
                        // gentle depth and parallax lift.
                        at(0) = {0, std::max(1, duration * 5 / 12), Enter::Rise, Direction::Up};
                        at(1) = {std::max(1, duration / 10),
                                 std::max(1, duration * 5 / 12), Enter::Slide, Direction::Left};
                        focus(0, duration / 2, std::max(1, duration / 5),
                              1.045f, 34.f, -8.f, 0.f, -1.8f);
                        focus(1, duration * 3 / 4, std::max(1, duration / 6),
                              1.045f, 34.f, 8.f, 0.f, 1.8f);
                    } else if (motionId == "duo_depth_handoff") {
                        // Depth handoff: both cards pop in, then each one takes
                        // the foreground in turn before the pair settles level.
                        at(0) = {0, std::max(1, duration / 3), Enter::Pop, Direction::Up};
                        at(1) = {std::max(1, duration / 8),
                                 std::max(1, duration / 3), Enter::Pop, Direction::Up};
                        focus(0, duration * 5 / 12, std::max(1, duration / 6),
                              1.04f, 46.f, 0.f, -4.f, -2.2f);
                        focus(1, duration * 7 / 10, std::max(1, duration / 7),
                              1.04f, 46.f, 0.f, -4.f, 2.2f);
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
                    } else if (motionId == "trio_orbit_focus") {
                        // Center-led orbit: the hero lands first, the side cards
                        // arc in, then the focus sweeps left -> center -> right.
                        at(1) = {0, std::max(1, duration / 4), Enter::Pop, Direction::Up};
                        at(0) = {std::max(1, duration / 12), std::max(1, duration / 4),
                                 Enter::Slide, Direction::Right};
                        at(2) = {std::max(1, duration / 6), std::max(1, duration / 4),
                                 Enter::Slide, Direction::Left};
                        focus(0, duration * 2 / 5, std::max(1, duration / 7),
                              1.055f, 36.f, -4.f, 0.f, -2.4f);
                        focus(1, duration * 11 / 20, std::max(1, duration / 6),
                              1.065f, 42.f, 0.f, 0.f, 0.f);
                        focus(2, duration * 7 / 10, std::max(1, duration / 7),
                              1.055f, 36.f, 4.f, 0.f, 2.4f);
                    } else if (motionId == "trio_prism_cascade") {
                        // Prism cascade: a diagonal ingress with alternating
                        // depth emphasis, so the row reads as a travelling light.
                        at(0) = {0, std::max(1, duration / 3), Enter::Slide, Direction::Right};
                        at(1) = {std::max(1, duration / 15), std::max(1, duration / 3),
                                 Enter::Rise, Direction::Up};
                        at(2) = {std::max(1, duration * 2 / 15), std::max(1, duration / 3),
                                 Enter::Slide, Direction::Left};
                        focus(0, duration * 7 / 20, std::max(1, duration / 8),
                              1.05f, 28.f, 0.f, -2.f, -3.f);
                        focus(1, duration / 2, std::max(1, duration / 7),
                              1.06f, 36.f, 0.f, 0.f, 0.f);
                        focus(2, duration * 13 / 20, std::max(1, duration / 8),
                              1.05f, 28.f, 0.f, -2.f, 3.f);
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
                    } else if (motionId == "quad_mosaic_wave") {
                        // Mosaic wave: a reading-order rise with a clockwise
                        // focus that gives each quadrant its own beat.
                        for (std::size_t i = 0; i < 4; ++i) {
                            at(i) = {static_cast<int>(i) * half,
                                     std::max(1, duration / 5), Enter::Rise, Direction::Up};
                        }
                        focus(0, duration * 2 / 5, std::max(1, duration / 10),
                              1.04f, 24.f, 0.f, -2.f, -1.5f);
                        focus(1, duration / 2, std::max(1, duration / 10),
                              1.04f, 24.f, 0.f, -2.f, 1.5f);
                        focus(2, duration * 3 / 5, std::max(1, duration / 10),
                              1.04f, 24.f, 0.f, -2.f, -1.5f);
                        focus(3, duration * 7 / 10, std::max(1, duration / 10),
                              1.04f, 24.f, 0.f, -2.f, 1.5f);
                    } else if (motionId == "quad_parallax_grid") {
                        // Parallax grid: columns arrive from opposite edges,
                        // then the top and bottom rows trade focus in depth.
                        at(0) = {0, std::max(1, duration / 4), Enter::Slide, Direction::Right};
                        at(2) = {std::max(1, duration / 15), std::max(1, duration / 4),
                                 Enter::Slide, Direction::Right};
                        at(1) = {std::max(1, duration / 8), std::max(1, duration / 4),
                                 Enter::Slide, Direction::Left};
                        at(3) = {std::max(1, duration * 3 / 20), std::max(1, duration / 4),
                                 Enter::Slide, Direction::Left};
                        focus(0, duration / 3, std::max(1, duration / 10),
                              1.045f, 32.f, 0.f, -2.f, -2.f);
                        focus(1, duration * 9 / 20, std::max(1, duration / 10),
                              1.045f, 32.f, 0.f, -2.f, 2.f);
                        focus(2, duration * 3 / 5, std::max(1, duration / 10),
                              1.04f, 28.f, 0.f, 2.f, 2.f);
                        focus(3, duration * 3 / 4, std::max(1, duration / 10),
                              1.04f, 28.f, 0.f, 2.f, -2.f);
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
                    } else if (motionId == "penta_carousel_orbit") {
                        // Carousel orbit: the five cards rise in a soft wave,
                        // then the focus travels across the strip one card at a
                        // time with a small alternating tilt.
                        for (std::size_t i = 0; i < 5; ++i) {
                            at(i) = {static_cast<int>(i) * half,
                                     std::max(1, duration / 5), Enter::Rise, Direction::Up};
                        }
                        const int focusStart = duration * 5 / 12;
                        const int focusStep = std::max(1, duration / 12);
                        for (std::size_t i = 0; i < 5; ++i) {
                            focus(i, focusStart + static_cast<int>(i) * focusStep,
                                  focusStep, 1.045f, 28.f,
                                  i % 2 == 0 ? -4.f : 4.f, 0.f,
                                  i % 2 == 0 ? -2.f : 2.f);
                        }
                    } else if (motionId == "penta_hero_cascade") {
                        // Hero cascade: the centre card lands first, the four
                        // satellites cascade in around it, then the hero takes
                        // a deeper foreground beat while the strip settles.
                        at(3) = {0, std::max(1, duration * 3 / 10), Enter::Pop, Direction::Up};
                        at(0) = {std::max(1, duration / 15), std::max(1, duration / 5),
                                 Enter::Rise, Direction::Up};
                        at(1) = {std::max(1, duration * 2 / 15), std::max(1, duration / 5),
                                 Enter::Rise, Direction::Up};
                        at(2) = {std::max(1, duration / 5), std::max(1, duration / 5),
                                 Enter::Rise, Direction::Up};
                        at(4) = {std::max(1, duration * 4 / 15), std::max(1, duration / 5),
                                 Enter::Rise, Direction::Up};
                        focus(3, duration * 7 / 15, std::max(1, duration / 5),
                              1.07f, 48.f, 0.f, 0.f, 0.f);
                        focus(0, duration * 8 / 15, std::max(1, duration / 15),
                              1.035f, 24.f, -3.f, 0.f, -2.f);
                        focus(1, duration * 3 / 5, std::max(1, duration / 15),
                              1.035f, 24.f, 0.f, -2.f, 2.f);
                        focus(2, duration * 2 / 3, std::max(1, duration / 15),
                              1.035f, 24.f, -3.f, 0.f, -2.f);
                        focus(4, duration * 11 / 15, std::max(1, duration / 15),
                              1.035f, 24.f, 3.f, 0.f, 2.f);
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
            // One reusable animation inventory for every group size. The
            // layout still chooses the image arrangement; it no longer
            // selects a separate animation family for duo/trio/quad/penta.
            static const std::vector<std::string> reusable = [] {
                std::vector<std::string> ids;
                ids.reserve(reusableMotions().size());
                for (const ReusableMotion& motion : reusableMotions()) {
                    ids.emplace_back(motion.id);
                }
                return ids;
            }();
            switch (layout) {
                case MultiImageLayout::Duo:
                case MultiImageLayout::Trio:
                case MultiImageLayout::Quad:
                case MultiImageLayout::Penta: return reusable;
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
            case MultiImageStyle::SoftDream: return "multi_image_soft_dream";
        }
        return "unknown";
    }

    const char* multiImageReelMoveId(MultiImageReelMove move) noexcept {
        switch (move) {
            case MultiImageReelMove::DreamPush: return "reel_dream_push";
            case MultiImageReelMove::SoftIris: return "reel_soft_iris";
            case MultiImageReelMove::LateralVeil: return "reel_lateral_veil";
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
        const bool storyReel = spec.presentation == MultiImagePresentation::StoryReel;
        if (storyReel &&
            spec.duration < static_cast<int>(expected) * 6) {
            throw std::invalid_argument(
                    "addMultiImageBoard: a story reel needs at least six frames per tile");
        }
        if (spec.headerLabel.size() > 64 || spec.headerSubtitle.size() > 96) {
            throw std::invalid_argument(
                    "addMultiImageBoard: header label (<= 64) or subtitle (<= 96) is too long");
        }
        std::string selectedMotion = spec.motionId;
        if (storyReel) {
            // A reel owns its own sequential timing; a board choreography would
            // only fight it. The resolved move is reported on the board instead.
            selectedMotion.clear();
        } else {
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
        }
        for (const MultiImageTile& tile : spec.tiles) {
            if (tile.path.empty()) {
                throw std::invalid_argument("addMultiImageBoard: every tile needs an asset path");
            }
        }

        std::vector<Vector2> cells = multiImageCells(spec.layout);
        if (storyReel) {
            // Every tile shares the center cell; the reel reveals them in turn.
            cells.assign(cells.size(), Vector2(0.5f, 0.5f));
        }
        const Vector2 canvas = scene.canvas();
        const int count = static_cast<int>(cells.size());
        const int stagger = std::max(1, spec.duration / (count + 1));
        const int endFrame = spec.inFrame + spec.duration + spec.holdFrames;
        const int exitFrames = exitFramesFor(spec);
        const int exitStart = endFrame - exitFrames;
        const float fps = scene.fps();

        // With no certified motion the shared entrance staggers the grid as before.
        const bool certified = !storyReel && !selectedMotion.empty();
        const std::vector<Beat> beats = certified
                ? beatsFor(spec.layout, selectedMotion, count, spec.duration)
                : std::vector<Beat>{};

        using chrononmotion::Vector3;
        using chrononmotion::motion::Easing;

        const StyleLook look = lookFor(spec.style, spec);
        const bool styled = spec.style != MultiImageStyle::Classic;

        MultiImageBoard board;
        board.motionId = selectedMotion;
        board.reelMoveId = storyReel ? multiImageReelMoveId(spec.reelMove) : std::string{};
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
            plate.position(0.f, 0.f);
            plate.alive(spec.inFrame, endFrame);
            plate.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
        }

        if (styled && look.dreamGlow) {
            // A broad, slowly breathing radial field under the cards. This is a
            // native shape gradient, not a second renderer or a screenshot.
            ShapeRadialGradient auraGradient;
            auraGradient.center = {0.5f, 0.5f};
            auraGradient.radius = 0.5f;
            auraGradient.stops = {
                    ShapeGradientStop{.position = 0.f, .color = "#5A3FA8", .opacity = 0.55f},
                    ShapeGradientStop{.position = 0.58f, .color = "#231846", .opacity = 0.32f},
                    ShapeGradientStop{.position = 1.f, .color = "#070A18", .opacity = 0.f}};
            LayerHandle& aura = scene.shape(ShapeSpec{
                    .size = {canvas.x * 1.45f, canvas.y * 1.45f},
                    .fillColor = "#FFFFFF",
                    .name = "dream_aura",
                    .geometry = ShapeGeometry::Ellipse,
                    .radialGradient = auraGradient});
            aura.position(0.f, 0.f);
            aura.alive(spec.inFrame, endFrame);
            aura.animateOpacity(spec.inFrame, 18, 0.f, 0.9f, Easing::easeOut());
            aura.animateOpacity(exitStart, exitFrames, 0.9f, 0.f, Easing::easeIn());
            aura.layer().tracks.scale.add(static_cast<float>(spec.inFrame) / fps,
                                          Vector3(1.f, 1.f, 1.f), Easing::inOutCubic());
            aura.layer().tracks.scale.add(static_cast<float>(endFrame) / fps,
                                          Vector3(1.08f, 1.08f, 1.f), Easing::inOutCubic());
        }

        if (styled && !look.headerInk.empty() &&
            (!spec.headerLabel.empty() || !spec.headerSubtitle.empty())) {
            const float hx = canvas.x * 0.055f - canvas.x * 0.5f;
            float hy = canvas.y * 0.105f - canvas.y * 0.5f;
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

        // One entrance vocabulary for the image and its soft halo: they move as
        // one card, so the rim cannot peel away from the print.
        const auto authorEnter = [&](LayerHandle& target, int startFrame, int enterFrames,
                                     int moveFrames, Enter kind, Direction dir) {
            if (certified) {
                switch (kind) {
                    case Enter::Slide:
                        target.animate(SlideIn{.direction = dir,
                                              .inFrame = startFrame,
                                              .duration = moveFrames,
                                              .distance = spec.tileWidth * 0.5f})
                                .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                        break;
                    case Enter::Pop:
                        target.animate(ScalePop{.inFrame = startFrame, .duration = moveFrames,
                                               .from = 0.72f, .to = 1.f})
                                .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                        break;
                    case Enter::Rise:
                        target.animate(SlideIn{.direction = Direction::Up,
                                              .inFrame = startFrame,
                                              .duration = moveFrames,
                                              .distance = spec.tileHeight * 0.5f})
                                .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                        break;
                    case Enter::Fade:
                        target.animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                        break;
                    case Enter::SoftZoom:
                        target.animate(ScalePop{.inFrame = startFrame, .duration = moveFrames,
                                               .from = 0.965f, .to = 1.f})
                                .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                        break;
                    case Enter::SoftLift:
                        target.animate(SlideIn{.direction = Direction::Up,
                                              .inFrame = startFrame,
                                              .duration = moveFrames,
                                              .distance = 28.f})
                                .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                        break;
                    case Enter::SoftDrift:
                        target.animate(SlideIn{.direction = Direction::Right,
                                              .inFrame = startFrame,
                                              .duration = moveFrames,
                                              .distance = 30.f})
                                .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                        break;
                    case Enter::Settle:
                        target.animate(ScalePop{.inFrame = startFrame, .duration = moveFrames,
                                               .from = 1.03f, .to = 1.f})
                                .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                        break;
                }
                return;
            }
            switch (spec.entrance) {
                case MultiImageEntrance::Fade:
                    target.animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                    break;
                case MultiImageEntrance::Rise:
                    target.animate(SlideIn{.direction = Direction::Up,
                                          .inFrame = startFrame,
                                          .duration = moveFrames,
                                          .distance = spec.tileHeight * 0.5f})
                            .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                    break;
                case MultiImageEntrance::ScalePop:
                    target.animate(ScalePop{.inFrame = startFrame, .duration = moveFrames,
                                           .from = 0.72f, .to = 1.f})
                            .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                    break;
                case MultiImageEntrance::SoftBloom:
                    target.animate(SlideIn{.direction = Direction::Up,
                                          .inFrame = startFrame,
                                          .duration = moveFrames,
                                          .distance = spec.tileHeight * 0.14f})
                            .animate(ScalePop{.inFrame = startFrame, .duration = moveFrames,
                                             .from = 0.92f, .to = 1.f})
                            .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                    break;
                case MultiImageEntrance::Drift:
                    target.animate(SlideIn{.direction = dir,
                                          .inFrame = startFrame,
                                          .duration = moveFrames,
                                          .distance = spec.tileWidth * 0.18f})
                            .animate(ScalePop{.inFrame = startFrame, .duration = moveFrames,
                                             .from = 0.97f, .to = 1.f})
                            .animate(FadeIn{.inFrame = startFrame, .duration = enterFrames});
                    break;
            }
        };

        // The reel keys each centered tile in and out inside its own slot. The
        // halo receives the identical keys; it only differs in resting opacity.
        const auto authorReel = [&](LayerHandle& target, std::size_t index,
                                    int startFrame, int enterFrames,
                                    int reelExitStart, int reelExitDuration) {
            const Vector3 rest = target.layer().transform.position;
            const float peakOpacity = target.layer().transform.opacity;
            const float baseZ = target.layer().transform.rotation.z;
            const auto keyPosition = [&](int frame, const Vector3& value, const Easing& easing) {
                target.layer().tracks.position.add(static_cast<float>(frame) / fps, value, easing);
            };
            const auto keyScale = [&](int frame, float value, const Easing& easing) {
                target.layer().tracks.scale.add(static_cast<float>(frame) / fps,
                                                Vector3(value, value, 1.f), easing);
            };
            const auto keyRotation = [&](int frame, float degrees, const Easing& easing) {
                target.layer().tracks.rotation.add(
                        static_cast<float>(frame) / fps,
                        Vector3(0.f, 0.f,
                                 baseZ + chrononmotion::math::degToRad(degrees)), easing);
            };

            target.animateOpacity(startFrame, std::max(2, enterFrames - 2),
                                  0.f, peakOpacity, Easing::easeOut());
            target.animateOpacity(reelExitStart, reelExitDuration,
                                  peakOpacity, 0.f, Easing::easeIn());

            switch (spec.reelMove) {
                case MultiImageReelMove::DreamPush:
                    target.animatePosition(startFrame, enterFrames,
                                           Vector3(0.f, 72.f, 0.f), Easing::easeOut());
                    keyScale(startFrame, 0.92f, Easing::easeOut());
                    keyScale(startFrame + enterFrames, 1.f, Easing::easeOut());
                    keyPosition(reelExitStart, rest, Easing::easeIn());
                    keyPosition(reelExitStart + reelExitDuration,
                                rest + Vector3(0.f, -42.f, 0.f), Easing::easeIn());
                    keyScale(reelExitStart, 1.f, Easing::easeIn());
                    keyScale(reelExitStart + reelExitDuration, 0.96f, Easing::easeIn());
                    break;
                case MultiImageReelMove::SoftIris:
                    target.animatePosition(startFrame, enterFrames,
                                           Vector3(0.f, 30.f, 0.f), Easing::easeOut());
                    keyScale(startFrame, 0.78f, Easing::overshoot());
                    keyScale(startFrame + enterFrames, 1.f, Easing::overshoot());
                    keyRotation(startFrame, -2.4f, Easing::easeOut());
                    keyRotation(startFrame + enterFrames, 0.f, Easing::easeOut());
                    keyPosition(reelExitStart, rest, Easing::easeIn());
                    keyPosition(reelExitStart + reelExitDuration,
                                rest + Vector3(0.f, 24.f, 0.f), Easing::easeIn());
                    keyScale(reelExitStart, 1.f, Easing::easeIn());
                    keyScale(reelExitStart + reelExitDuration, 1.05f, Easing::easeIn());
                    keyRotation(reelExitStart, 0.f, Easing::easeIn());
                    keyRotation(reelExitStart + reelExitDuration, 2.2f, Easing::easeIn());
                    break;
                case MultiImageReelMove::LateralVeil: {
                    const float side = index % 2 == 0 ? -1.f : 1.f;
                    target.animatePosition(startFrame, enterFrames,
                                           Vector3(side * spec.tileWidth * 0.22f, 0.f, 0.f),
                                           Easing::easeOut());
                    keyScale(startFrame, 0.96f, Easing::easeOut());
                    keyScale(startFrame + enterFrames, 1.f, Easing::easeOut());
                    keyRotation(startFrame, side * 1.6f, Easing::easeOut());
                    keyRotation(startFrame + enterFrames, 0.f, Easing::easeOut());
                    keyPosition(reelExitStart, rest, Easing::easeIn());
                    keyPosition(reelExitStart + reelExitDuration,
                                rest + Vector3(side * spec.tileWidth * 0.10f, -18.f, 0.f),
                                Easing::easeIn());
                    keyScale(reelExitStart, 1.f, Easing::easeIn());
                    keyScale(reelExitStart + reelExitDuration, 0.97f, Easing::easeIn());
                    keyRotation(reelExitStart, 0.f, Easing::easeIn());
                    keyRotation(reelExitStart + reelExitDuration, -side * 1.2f, Easing::easeIn());
                    break;
                }
            }
        };

        // The premium emphasis pass. It only reads the tile's resting transform,
        // so it can follow any entrance and rides the same keys on the image and
        // its soft halo. The pass is skipped if it would run into the exit.
        const auto authorFocus = [&](LayerHandle& target, const Beat& beat, float baseTilt) {
            if (beat.focusAt <= 0 || beat.focusHold <= 0) return;
            const int peakFrame = spec.inFrame + beat.focusAt;
            const int settleFrame = peakFrame + beat.focusHold;
            if (settleFrame >= exitStart) return;
            const Vector3 rest = target.layer().transform.position;
            const Vector3 restScale = target.layer().transform.scale;
            target.layer().tracks.position.add(
                    static_cast<float>(peakFrame) / fps,
                    rest + Vector3(beat.focusDriftX, beat.focusDriftY, beat.focusDepth),
                    Easing::inOutCubic());
            target.layer().tracks.position.add(
                    static_cast<float>(settleFrame) / fps, rest, Easing::inOutCubic());
            target.layer().tracks.scale.add(
                    static_cast<float>(peakFrame) / fps,
                    Vector3(beat.focusScale, beat.focusScale, 1.f), Easing::inOutCubic());
            target.layer().tracks.scale.add(
                    static_cast<float>(settleFrame) / fps, restScale, Easing::inOutCubic());
            if (beat.focusTiltDegrees != 0.f) {
                target.layer().tracks.rotation.add(
                        static_cast<float>(peakFrame) / fps,
                        Vector3(0.f, 0.f,
                                 baseTilt + chrononmotion::math::degToRad(beat.focusTiltDegrees)),
                        Easing::inOutCubic());
                target.layer().tracks.rotation.add(
                        static_cast<float>(settleFrame) / fps,
                        Vector3(0.f, 0.f, baseTilt), Easing::inOutCubic());
            }
        };

        for (std::size_t i = 0; i < cells.size(); ++i) {
            const MultiImageTile& tile = spec.tiles[i];
            const Vector2 cell = cells[i];
            const float x = canvas.x * (cell.x - 0.5f);
            const float y = canvas.y * (cell.y - 0.5f);

            // The fan look leans the outer tiles outward around an upright
            // center tile; every other style keeps the grid square.
            const float tiltDegrees = look.tiltStepDegrees == 0.f
                    ? 0.f
                    : (static_cast<float>(i) -
                       static_cast<float>(cells.size() - 1) * 0.5f) * look.tiltStepDegrees;
            const float tiltRadians = chrononmotion::math::degToRad(tiltDegrees);

            const int segment = storyReel ? std::max(1, spec.duration / count) : 0;
            const int overlap = storyReel ? std::max(2, std::min(10, segment / 4)) : 0;
            const bool lastTile = i + 1 == cells.size();
            int start = spec.inFrame + static_cast<int>(i) * stagger;
            int enterDuration = std::max(1, stagger);
            int moveDuration = std::max(2, stagger * 2);
            int tileExitStart = exitStart;
            int tileExitDuration = exitFrames;
            int tileAliveEnd = endFrame;
            Enter kind = Enter::Rise;
            Direction dir = Direction::Up;
            const Beat* beat = nullptr;
            if (storyReel) {
                start = spec.inFrame + static_cast<int>(i) * segment;
                enterDuration = std::max(3, std::min(16, segment / 3));
                moveDuration = std::max(enterDuration, segment / 2);
                // The previous print starts leaving before the next one arrives,
                // so the handoff is a crossfade rather than a hard cut.
                tileExitStart = lastTile ? exitStart : start + segment - overlap;
                tileExitDuration = lastTile ? exitFrames : std::max(2, overlap * 2);
                tileAliveEnd = lastTile
                        ? endFrame
                        : std::min(endFrame, tileExitStart + tileExitDuration);
                dir = (i % 2 == 0) ? Direction::Left : Direction::Right;
            } else if (certified) {
                beat = &beats[i];
                start = spec.inFrame + beat->start;
                enterDuration = beat->enter;
                moveDuration = std::max(2, beat->enter);
                kind = beat->kind;
                dir = beat->dir;
            } else if (spec.entrance == MultiImageEntrance::Drift) {
                dir = (i % 2 == 0) ? Direction::Left : Direction::Right;
            }

            ImageFrameStyle frame = tile.frame;
            if (styled) {
                frame.cornerRadius = look.cornerRadius;
                frame.tornEdgeAmount = look.tornEdge;
                if (look.softBlur > 0.f) frame.softBlur = look.softBlur;
                if (look.tornEdge > 0.f) {
                    frame.tornEdgeSeed = 1000u + static_cast<std::uint32_t>(i);
                }
            }

            LayerHandle* halo = nullptr;
            if (styled && !look.haloColor.empty()) {
                LayerHandle& glow = scene.shape(ShapeSpec{
                        .size = {spec.tileWidth + 2.f * look.haloPadding,
                                 spec.tileHeight + 2.f * look.haloPadding},
                        .fillColor = look.haloColor,
                        .name = "tile_halo_" + std::to_string(i),
                        .cornerRadius = look.cornerRadius + look.haloPadding,
                        .glowRadius = look.haloGlowRadius,
                        .glowIntensity = look.haloGlowIntensity,
                        .glowColor = look.haloColor});
                glow.position(x, y);
                glow.opacity(look.haloOpacity);
                glow.alive(storyReel ? start : spec.inFrame,
                           storyReel ? tileAliveEnd : endFrame);
                if (tiltDegrees != 0.f) {
                    glow.layer().tracks.rotation.add(
                            0.f, Vector3(0.f, 0.f, tiltRadians), Easing::easeOut());
                }
                halo = &glow;
            }

            if (styled && look.shadowOpacity > 0.f) {
                LayerHandle& shadow = scene.shape(ShapeSpec{
                        .size = {spec.tileWidth, spec.tileHeight},
                        .fillColor = "#000000",
                        .name = "tile_shadow_" + std::to_string(i),
                        .cornerRadius = look.cornerRadius});
                shadow.position(x + look.shadowOffset, y + look.shadowOffset);
                shadow.opacity(look.shadowOpacity);
                shadow.alive(storyReel ? start : spec.inFrame,
                             storyReel ? tileAliveEnd : endFrame);
                shadow.layer().tracks.rotation.add(
                        0.f, Vector3(0.f, 0.f, tiltRadians), Easing::easeOut());
                if (storyReel) {
                    shadow.animate(FadeIn{.inFrame = start, .duration = enterDuration});
                    shadow.animate(FadeOut{.startFrame = tileExitStart,
                                           .duration = tileExitDuration});
                } else {
                    shadow.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
                }
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
                card.alive(storyReel ? start : spec.inFrame,
                           storyReel ? tileAliveEnd : endFrame);
                card.layer().tracks.rotation.add(
                        0.f, Vector3(0.f, 0.f, tiltRadians), Easing::easeOut());
                if (storyReel) {
                    card.animate(FadeIn{.inFrame = start, .duration = enterDuration});
                    card.animate(FadeOut{.startFrame = tileExitStart,
                                         .duration = tileExitDuration});
                } else {
                    card.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
                }
            }

            LayerHandle& image = scene.image(ImageSpec{
                    .path = tile.path,
                    .name = "tile_" + std::to_string(i),
                    .frame = frame,
                    .targetSize = Vector2(spec.tileWidth, spec.tileHeight)});
            image.position(x, y);
            image.alive(storyReel ? start : spec.inFrame,
                        storyReel ? tileAliveEnd : endFrame);
            if (tiltDegrees != 0.f) {
                image.layer().tracks.rotation.add(
                        0.f, Vector3(0.f, 0.f, tiltRadians), Easing::easeOut());
            }

            if (storyReel) {
                authorReel(image, i, start, enterDuration, tileExitStart, tileExitDuration);
                if (halo != nullptr) {
                    authorReel(*halo, i, start, enterDuration, tileExitStart, tileExitDuration);
                }
            } else {
                authorEnter(image, start, enterDuration, moveDuration, kind, dir);
                image.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
                if (halo != nullptr) {
                    authorEnter(*halo, start, enterDuration, moveDuration, kind, dir);
                    halo->animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
                }
                if (beat != nullptr) {
                    authorFocus(image, *beat, tiltRadians);
                    if (halo != nullptr) authorFocus(*halo, *beat, tiltRadians);
                }
            }
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
                text.alive(storyReel ? start : spec.inFrame,
                           storyReel ? tileAliveEnd : endFrame);
                text.animate(FadeIn{.inFrame = start + std::max(1, enterDuration / 2),
                                    .duration = std::max(1, enterDuration)});
                text.animate(FadeOut{.startFrame = storyReel ? tileExitStart : exitStart,
                                     .duration = storyReel ? tileExitDuration : exitFrames});
                board.captions.push_back(&text);
            }
        }

        board.endFrame = endFrame;
        return board;
    }

}// namespace chronontemplate
