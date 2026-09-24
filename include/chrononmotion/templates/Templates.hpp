// ChrononMotion — compositional motion templates.
//
// Templates are scene authoring recipes, not a browser or a renderer. They create
// ordinary MotionScene layers with opaque text/image ContentRefs and keyframes.

#ifndef CHRONONMOTION_TEMPLATES_TEMPLATES_HPP
#define CHRONONMOTION_TEMPLATES_TEMPLATES_HPP

#include "chrononmotion/motion/MotionScene.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chrononmotion::templates {

    using motion::Layer;
    using motion::MotionScene;

    enum class TemplateId {
        YouTubeSubscribe,
        InstagramLike,
        FollowPrompt,
        LowerThird,
        QuoteCard,
        BreakingNews,
        EpisodeTag
    };

    /// Input shared by all catalog templates. Text and image identifiers remain
    /// opaque: Chronon owns their bytes, layout and rasterization.
    struct TemplateData {
        std::string primaryText{"ChrononMotion"};
        std::string secondaryText{"Motion graphics"};
        std::string authorText{"@chrononmotion"};
        std::string imageId{"image"};
        std::string iconId{"icon"};
        Vector2 canvas{1920.f, 1080.f};
        float fps{30.f};
        int startFrame{0};
        /// Catalog recipes require at least 48 frames for entrance, interaction
        /// and finite exit phases to fit without writing keys outside the lifetime.
        int duration{90};

        void validate() const;
    };

    /// Stable layer IDs make a generated template inspectable and bindable by a
    /// caller without exposing a renderer-specific node graph.
    struct TemplateLayers {
        Layer::Id root{1};
        Layer::Id primary{2};
        Layer::Id secondary{3};
        Layer::Id accent{4};
        Layer::Id icon{5};
        Layer::Id detail{6};
        Layer::Id particleStart{20};
    };

    [[nodiscard]] const char* name(TemplateId id);
    [[nodiscard]] std::vector<TemplateId> available();
    [[nodiscard]] MotionScene build(TemplateId id, const TemplateData& data = {});

}// namespace chrononmotion::templates

#endif//CHRONONMOTION_TEMPLATES_TEMPLATES_HPP
