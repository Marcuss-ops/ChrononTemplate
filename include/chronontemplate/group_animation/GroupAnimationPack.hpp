#ifndef CHRONONTEMPLATE_GROUP_ANIMATION_PACK_HPP
#define CHRONONTEMPLATE_GROUP_ANIMATION_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <string>
#include <vector>

namespace chronontemplate {

    /// The heterogeneous roles a group animation can own. The ids are the same
    /// wire vocabulary RenderingGen publishes in `animation_groups`, so a C++
    /// showcase and a semantic plan describe the same members.
    enum class GroupRole {
        Image,
        ImportantPhrase,
        Caption,
        Date,
        Metric
    };

    /// The first native group-animation showcase: one master with all five
    /// roles and four two-member clips that isolate a role next to the phrase.
    enum class GroupShowcaseMode {
        AllRoles,
        PhraseImage,
        PhraseCaption,
        PhraseDate,
        PhraseMetric
    };

    [[nodiscard]] const char* groupRoleId(GroupRole role) noexcept;
    [[nodiscard]] const char* groupShowcaseModeId(GroupShowcaseMode mode) noexcept;

    /// One member's place in the shared sequence. Offsets are relative to the
    /// group start, exactly like `animation_groups[].members[].offset_ms`.
    struct GroupMemberTiming {
        GroupRole role{GroupRole::ImportantPhrase};
        int offsetFrames{0};
        int enterFrames{24};
    };

    /// Authored data for one native group animation. The pack owns the layout
    /// and the sequence; the emitter only projects the resulting plans.
    struct GroupAnimationSpec {
        std::string id{};
        std::string title{};
        GroupShowcaseMode mode{GroupShowcaseMode::AllRoles};
        int fps{30};
        int durationFrames{300};
        int staggerFrames{12};
        int enterFrames{24};
        std::string phrase{"ONE GROUP. FIVE VOICES."};
        std::string kicker{"GROUP ANIMATION / SEQUENCE_V1"};
        std::string imageAsset{"assets/images/ada_lovelace_portrait.png"};
        std::string imageCaption{"ADA LOVELACE"};
        std::string dateValue{"1843"};
        std::string dateLabel{"THE NOTES"};
        std::string metricValue{"59.99"};
        std::string metricLabel{"SIGNAL / SEC"};
    };

    /// Roles in sequence order for one showcase mode.
    [[nodiscard]] std::vector<GroupRole> groupShowcaseRoles(GroupShowcaseMode mode);

    /// Validated member timeline. Offsets are index * staggerFrames.
    [[nodiscard]] std::vector<GroupMemberTiming> groupShowcaseTimeline(const GroupAnimationSpec& spec);

    /// Build the native scene. The group controllers are the only animation
    /// owners: each child lives in one controller, the controller carries the
    /// stagger/entrance/exit, and the existing text/image/shape lowering runs
    /// unchanged underneath it.
    void buildGroupAnimationShowcase(TemplateScene& scene, const GroupAnimationSpec& spec);

    /// The five first-party showcase specs. The master is 300 frames (10 s at
    /// 30 fps); the four role pairs are 210 frames (7 s).
    [[nodiscard]] std::vector<GroupAnimationSpec> groupAnimationShowcaseSpecs();

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_GROUP_ANIMATION_PACK_HPP
