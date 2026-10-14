// Documentary date groups: each animation shows its dates one after another.
#ifndef CHRONONTEMPLATE_DATE_GROUPS_PACK_HPP
#define CHRONONTEMPLATE_DATE_GROUPS_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/elements/ElementsCommon.hpp"

#include <string>
#include <vector>

namespace chronontemplate {

    /// One named animation. Its dates are shown in order, each one for
    /// `DateGroupsSpec::secondsPerDate` seconds.
    struct DateAnimation {
        std::string name{};
        std::vector<std::string> dates{};
    };

    struct DateGroupsSpec {
        std::string name{"date_groups"};
        std::vector<DateAnimation> animations{};
        float fps{30.f};
        int secondsPerDate{3};
        float width{1920.f};
        float height{1080.f};
        elements::ElementStyle style{elements::ElementStyle::DocumentaryDark};
        /// Logical font asset resolved by the renderer (required for render plans).
        std::string font{"ChrononTemplate/assets/fonts/Inter-Bold.ttf"};
    };

    /// Total frames for every animation back to back.
    [[nodiscard]] int dateGroupsDurationFrames(const DateGroupsSpec& spec);

    /// Author the full date sequence on one root. Animations play one after
    /// another; inside an animation each date gets its own time window.
    /// Fail-closed: empty names/dates and a non-positive timing throw.
    LayerHandle& addDateGroups(TemplateScene& scene, const DateGroupsSpec& spec);

} // namespace chronontemplate

#endif // CHRONONTEMPLATE_DATE_GROUPS_PACK_HPP
