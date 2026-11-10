// `chronon.style.v1`: the smallest style document a caller may hand
// ChrononTemplate. It carries editorial identity plus a look the closed
// vocabulary can resolve; anything else is rejected rather than guessed.

#ifndef CHRONONTEMPLATE_CORE_STYLESPEC_HPP
#define CHRONONTEMPLATE_CORE_STYLESPEC_HPP

#include "chronontemplate/core/LookSpec.hpp"

#include <istream>
#include <string>
#include <string_view>

namespace chronontemplate {

    struct StyleSpec {
        std::string id{};
        LookSpec look{};
        int fps{30};

        void validate() const;
    };

    /// Parse a complete `chronon.style.v1` document. Unknown schema versions,
    /// unknown fields and unknown looks fail closed.
    [[nodiscard]] StyleSpec parseStyle(std::string_view json);

    /// Same contract, reading from a stream (file or in-memory).
    [[nodiscard]] StyleSpec readStyle(std::istream& input);

    /// Stable identity of the resolved style, independent of JSON formatting.
    [[nodiscard]] std::string styleFingerprint(const StyleSpec& style);

}// namespace chronontemplate

#endif// CHRONONTEMPLATE_CORE_STYLESPEC_HPP
