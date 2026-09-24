// ChrononTemplate — the Chronon-side contract.
//
// This module never owns bytes, fonts, layout or rasterization: it asks Chronon
// to create content and to measure it, and Chronon answers with an identity plus
// a neutral rectangle. The interface is abstract so the module keeps compiling
// without the renderer, and so the host can be the real Chronon engine, the C
// ABI, or a test double.

#ifndef CHRONONTEMPLATE_CONTENT_HOST_HPP
#define CHRONONTEMPLATE_CONTENT_HOST_HPP

#include "chrononmotion/motion/Content.hpp"
#include "chrononmotion/math/Vector2.hpp"

#include "chronontemplate/ContentBinding.hpp"

#include <cstdint>
#include <string>

namespace chronontemplate {

    /// What the template wants written. The fields mirror Chronon's authoring
    /// vocabulary; the module keeps them as data and hands them over untouched.
    struct TextRequest {
        std::string text{};
        std::string font{};
        float fontSize{48.f};
        std::string color{"#FFFFFF"};
        chrononmotion::Vector2 canvas{1920.f, 1080.f};
    };

    struct ImageRequest {
        std::string path{};
        /// Chronon applies this frame mask to the content it creates. A zero
        /// radius is square; larger radii produce rounded corners. Border width
        /// is in px and zero disables the stroke.
        float cornerRadius{0.f};
        std::string borderColor{};
        float borderWidth{0.f};
    };

    struct VideoRequest {
        std::string path{};
    };

    /// Chronon's answer: the identity it minted plus the measurement it took.
    /// `metrics.fingerprint` is the digest of the exact bytes and style the
    /// rectangle came from — the motion side carries it and never interprets it.
    struct ContentHandle {
        ContentId id{};
        /// Numeric identity minted by Chronon for the ADR-032 C boundary.
        /// Zero means that this host is not connected to the ABI adapter.
        std::uint64_t wireId{0};
        chrononmotion::motion::ContentKind kind{chrononmotion::motion::ContentKind::None};
        chrononmotion::motion::ContentMetrics metrics{};

        [[nodiscard]] bool empty() const { return id.empty(); }
    };

    /// The Chronon surface this module depends on. Four calls, no more: creating
    /// content is Chronon's, measuring it is Chronon's, and the module only needs
    /// to know whether the numbers it holds are still the current ones.
    class ContentHost {
    public:
        virtual ~ContentHost() = default;

        [[nodiscard]] virtual ContentHandle createText(const TextRequest& request) = 0;
        [[nodiscard]] virtual ContentHandle createImage(const ImageRequest& request) = 0;
        [[nodiscard]] virtual ContentHandle createVideo(const VideoRequest& request) = 0;

        /// Digest of the content Chronon holds under `content` right now. A digest
        /// that differs from the one carried by a `ContentRef` is the only way a
        /// re-measured asset can be detected instead of silently mis-anchored.
        [[nodiscard]] virtual std::string currentFingerprint(const ContentId& content) const = 0;
    };

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_CONTENT_HOST_HPP
