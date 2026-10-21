#ifndef CHRONONTEMPLATE_FAST_INTRO_PACK_HPP
#define CHRONONTEMPLATE_FAST_INTRO_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <string>
#include <vector>

namespace chronontemplate::fast_intro {

    struct FastIntroSpec {
        std::string name{"fast_intro_v1"};
        std::string kicker{"CHRONON TEMPLATE"};
        std::string title{"THE STORY SO FAR"};
        std::string subtitle{"A short line that sets up the story."};
        std::vector<std::string> topics{"CONTEXT", "EVIDENCE", "WHAT CHANGED"};
        std::string accent{"#363530"};
        std::string font{"ChrononTemplate/assets/fonts/Inter-Regular.ttf"};
        int durationFrames{72};
        float width{1920.f};
        float height{1080.f};
    };

    /// Author the opening plate, title/subtitle, topic chips, draw rail and
    /// moving marker. All copy and accent color are supplied by the caller.
    [[nodiscard]] LayerHandle& addFastIntro(TemplateScene& scene,
                                            const FastIntroSpec& spec);

} // namespace chronontemplate::fast_intro

#endif // CHRONONTEMPLATE_FAST_INTRO_PACK_HPP
