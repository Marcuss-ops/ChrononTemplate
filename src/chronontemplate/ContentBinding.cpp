#include "chronontemplate/ContentBinding.hpp"

#include <stdexcept>
#include <utility>

namespace chronontemplate {

    void BindingRegistry::bind(MotionLayerId layer, ContentId content, std::uint64_t wireContent) {

        if (layer == chrononmotion::motion::Layer::kRoot) {
            throw std::invalid_argument("BindingRegistry::bind: the scene root carries no content");
        }
        if (content.empty()) {
            throw std::invalid_argument("BindingRegistry::bind: the content id is required");
        }

        const auto existing = m_byLayer.find(layer);
        if (existing != m_byLayer.end()) {
            // Retargeting while authoring: keep the row position, replace the asset.
            m_bindings[existing->second].content = std::move(content);
            m_bindings[existing->second].wireContent = wireContent;
            return;
        }

        m_byLayer.emplace(layer, m_bindings.size());
        m_bindings.push_back(ContentBinding{layer, std::move(content), wireContent});
    }

    bool BindingRegistry::bound(MotionLayerId layer) const {

        return m_byLayer.find(layer) != m_byLayer.end();
    }

    const ContentId& BindingRegistry::contentOf(MotionLayerId layer) const {

        const auto it = m_byLayer.find(layer);
        if (it == m_byLayer.end()) {
            throw std::invalid_argument("BindingRegistry::contentOf: the layer is not bound to any content");
        }
        return m_bindings[it->second].content;
    }

    std::uint64_t BindingRegistry::wireContentOf(MotionLayerId layer) const {

        const auto it = m_byLayer.find(layer);
        if (it == m_byLayer.end()) {
            throw std::invalid_argument("BindingRegistry::wireContentOf: the layer is not bound to any content");
        }
        return m_bindings[it->second].wireContent;
    }

    std::vector<MotionLayerId> BindingRegistry::layersOf(const ContentId& content) const {

        std::vector<MotionLayerId> result;
        for (const ContentBinding& binding : m_bindings) {
            if (binding.content == content) result.push_back(binding.layer);
        }
        return result;
    }

}// namespace chronontemplate
