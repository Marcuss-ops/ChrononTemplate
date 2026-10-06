// ChrononTemplate — the binding table.
//
// The one thing neither engine can own: which Chronon content a given Motion
// layer draws. Chronon owns the bytes, ChrononMotion owns the matrix, and this
// module keeps the row that ties them together.

#ifndef CHRONONTEMPLATE_CONTENT_BINDING_HPP
#define CHRONONTEMPLATE_CONTENT_BINDING_HPP

#include "chrononmotion/motion/Layer.hpp"

#include <cstdint>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace chronontemplate {

    /// Motion layer identity. Chronon never sees this type.
    using MotionLayerId = chrononmotion::motion::Layer::Id;

    /// Chronon content identity. Opaque here: Chronon owns how it is minted.
    using ContentId = std::string;

    struct ContentBinding {
        MotionLayerId layer{0};
        ContentId content{};
        /// Opaque numeric Chronon identity for the C boundary; zero when absent.
        std::uint64_t wireContent{0};
    };

    /// Layer -> content, one row per content layer.
    ///
    /// A layer that carries no content (a null/controller) needs no row; a layer
    /// that carries content without a row is a template defect, and the bridge
    /// refuses to submit the frame instead of drawing the wrong asset silently.
    class BindingRegistry {
    public:
        /// Bind `layer` to `content`. Rebinding a layer replaces its row, so a
        /// template can retarget a layer while it is being authored.
        void bind(MotionLayerId layer, ContentId content, std::uint64_t wireContent = 0);

        [[nodiscard]] bool bound(MotionLayerId layer) const;
        [[nodiscard]] const ContentId& contentOf(MotionLayerId layer) const;
        [[nodiscard]] std::uint64_t wireContentOf(MotionLayerId layer) const;

        /// Every layer currently drawing `content` (a shared asset may drive more
        /// than one layer).
        [[nodiscard]] std::vector<MotionLayerId> layersOf(const ContentId& content) const;

        [[nodiscard]] std::size_t size() const { return m_bindings.size(); }
        [[nodiscard]] const std::vector<ContentBinding>& bindings() const { return m_bindings; }

    private:
        std::vector<ContentBinding> m_bindings{};
        std::unordered_map<MotionLayerId, std::size_t> m_byLayer{};
    };

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_CONTENT_BINDING_HPP
