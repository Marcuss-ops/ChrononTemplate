// ChrononTemplate — authentic film leader countdown.
//
// Big numerals (5..1) slam in one per beat over a grainy gray field with
// crosshairs and a pulsing ring, then a PICTURE START card. Fully authored
// with existing primitives (text, shapes, animated grain): no
// renderer-side gap.

#ifndef CHRONONTEMPLATE_FILM_LEADER_PACK_HPP
#define CHRONONTEMPLATE_FILM_LEADER_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>

namespace chronontemplate::docfx {

    struct FilmLeaderSpec {
        int startNumber{5};       ///< first numeral, countdown runs down to 1
        int framesPerBeat{15};    ///< frames each numeral holds
        float numeralSize{420.f};
        std::string fieldColor{"#3A3A3C"};
        std::string numeralColor{"#F2EFE6"};
        std::string accentColor{"#C9A227"};
        std::uint32_t grainSeed{1968};
        int inFrame{0};
    };

    struct FilmLeaderLayers {
        MotionLayerId field{0};
        MotionLayerId startCard{0};
    };

    /// Author the grain field, crosshairs, ring, numerals and start card.
    /// Throws std::invalid_argument on any out-of-range spec value.
    [[nodiscard]] FilmLeaderLayers addFilmLeader(TemplateScene& scene,
                                                 const FilmLeaderSpec& spec);

    /// Total scene length in frames for the spec (beats + start card).
    [[nodiscard]] int filmLeaderFrames(const FilmLeaderSpec& spec);

    [[nodiscard]] const char* filmLeaderId() noexcept;

} // namespace chronontemplate::docfx

#endif // CHRONONTEMPLATE_FILM_LEADER_PACK_HPP
