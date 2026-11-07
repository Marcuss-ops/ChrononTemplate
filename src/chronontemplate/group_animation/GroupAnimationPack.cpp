#include "chronontemplate/group_animation/GroupAnimationPack.hpp"

#include <algorithm>
#include <stdexcept>
#include <string>
#include <vector>

namespace chronontemplate {

    namespace {

        constexpr float kCanvasWidth = 1920.f;
        constexpr float kCanvasHeight = 1080.f;
        constexpr int kExitFrames = 22;
        constexpr int kExitDuration = 16;

        constexpr const char* kFontPlayfairBold = "assets/fonts/PlayfairDisplay-Bold.ttf";
        constexpr const char* kFontPlayfairItalic = "assets/fonts/PlayfairDisplay-Italic.ttf";
        constexpr const char* kFontInterMedium = "assets/fonts/Inter-Medium.ttf";
        constexpr const char* kFontInterRegular = "assets/fonts/Inter-Regular.ttf";
        constexpr const char* kFontInterDisplayBold = "assets/fonts/InterDisplay-Bold.ttf";

        constexpr const char* kInk = "#07090E";
        constexpr const char* kPaper = "#F7F1E6";
        constexpr const char* kMuted = "#8497AE";
        constexpr const char* kGold = "#C8A96B";
        constexpr const char* kCard = "#0E1726";
        constexpr const char* kCardStroke = "#2B3D57";
        constexpr const char* kImageCard = "#0D1522";
        constexpr const char* kImageStroke = "#405671";

        [[nodiscard]] bool hasRole(const std::vector<GroupMemberTiming>& members, GroupRole role) {
            return std::any_of(members.begin(), members.end(),
                               [&](const GroupMemberTiming& member) { return member.role == role; });
        }

        [[nodiscard]] const GroupMemberTiming& memberFor(
                const std::vector<GroupMemberTiming>& members, GroupRole role) {
            const auto found = std::find_if(members.begin(), members.end(),
                                            [&](const GroupMemberTiming& member) {
                                                return member.role == role;
                                            });
            if (found == members.end()) {
                throw std::invalid_argument("GroupAnimationPack: missing role in timeline");
            }
            return *found;
        }

        LayerHandle& addText(TemplateScene& scene, const TextSpec& spec, float x, float y,
                             int durationFrames, LayerHandle* parent = nullptr) {
            LayerHandle& layer = scene.text(spec);
            layer.position(x, y).alive(0, durationFrames - 1);
            if (parent != nullptr) layer.parent(parent->id());
            return layer;
        }

        LayerHandle& addShape(TemplateScene& scene, const ShapeSpec& spec, float x, float y,
                              int durationFrames, LayerHandle* parent = nullptr) {
            LayerHandle& layer = scene.shape(spec);
            layer.position(x, y).alive(0, durationFrames - 1);
            if (parent != nullptr) layer.parent(parent->id());
            return layer;
        }

        LayerHandle& addImage(TemplateScene& scene, const ImageSpec& spec, float x, float y,
                              int durationFrames, LayerHandle* parent = nullptr) {
            LayerHandle& layer = scene.image(spec);
            layer.position(x, y, 10.f).alive(0, durationFrames - 1);
            if (parent != nullptr) layer.parent(parent->id());
            return layer;
        }

        LayerHandle& addGroupController(TemplateScene& scene, const std::string& name,
                                        const GroupMemberTiming& member, int durationFrames) {
            LayerHandle& controller = scene.group(name);
            controller.alive(0, durationFrames - 1)
                    .animate(FadeIn{.inFrame = member.offsetFrames,
                                    .duration = member.enterFrames})
                    .animate(SlideIn{.direction = chrononmotion::motion::presets::Direction::Up,
                                     .inFrame = member.offsetFrames,
                                     .duration = member.enterFrames,
                                     .distance = 52.f})
                    .animate(FadeOut{.startFrame = durationFrames - kExitFrames,
                                     .duration = kExitDuration});
            return controller;
        }

        void addRoleTag(TemplateScene& scene, LayerHandle& parent, const std::string& text,
                        float x, float y, int durationFrames) {
            addText(scene,
                    TextSpec{.text = text,
                             .font = kFontInterMedium,
                             .fontSize = 16.f,
                             .color = kMuted},
                    x, y, durationFrames, &parent);
        }

        void addPhrase(TemplateScene& scene, const GroupAnimationSpec& spec,
                       const std::vector<GroupMemberTiming>& members) {
            const GroupMemberTiming& phrase = memberFor(members, GroupRole::ImportantPhrase);
            LayerHandle& controller = addGroupController(scene, "group_phrase", phrase, spec.durationFrames);
            addText(scene,
                    TextSpec{.text = spec.kicker,
                             .font = kFontInterMedium,
                             .fontSize = 18.f,
                             .color = kMuted},
                    kCanvasWidth * 0.5f, 82.f, spec.durationFrames, &controller);
            addText(scene,
                    TextSpec{.text = spec.phrase,
                             .font = kFontPlayfairBold,
                             .fontSize = 84.f,
                             .color = kPaper,
                             .glow = TextGlowStyle{.color = kGold, .radius = 18.f, .intensity = 0.18f}},
                    kCanvasWidth * 0.5f, 164.f, spec.durationFrames, &controller);
            addRoleTag(scene, controller, "01 / IMPORTANT_PHRASE",
                       kCanvasWidth * 0.5f, 246.f, spec.durationFrames);
        }

        void addImageCardContent(TemplateScene& scene, const GroupAnimationSpec& spec,
                                 LayerHandle& parent, float x, float y, float size,
                                 float opacity, int durationFrames) {
            LayerHandle& card = addShape(scene,
                    ShapeSpec{.size = {size + 20.f, size + 20.f},
                              .fillColor = kImageCard,
                              .name = "ImageCard",
                              .cornerRadius = 30.f,
                              .strokeColor = kCardStroke,
                              .strokeWidth = 2.f},
                    x, y, durationFrames, &parent);
            card.opacity(opacity);
            LayerHandle& portrait = addImage(scene,
                    ImageSpec{.path = spec.imageAsset,
                              .name = "Portrait",
                              .frame = ImageFrameStyle{.cornerRadius = 22.f,
                                                       .borderColor = kImageStroke,
                                                       .borderWidth = 2.f},
                              .fit = ImageFitMode::Contain,
                              .targetSize = {size, size}},
                    x, y, durationFrames, &parent);
            portrait.opacity(opacity);
        }

        void addImageMember(TemplateScene& scene, const GroupAnimationSpec& spec,
                            const std::vector<GroupMemberTiming>& members, float x, float y,
                            float size) {
            const GroupMemberTiming& image = memberFor(members, GroupRole::Image);
            LayerHandle& controller = addGroupController(scene, "group_image", image, spec.durationFrames);
            addImageCardContent(scene, spec, controller, x, y, size, 1.f, spec.durationFrames);
            addRoleTag(scene, controller, "02 / IMAGE", x, y - size * 0.5f - 30.f,
                       spec.durationFrames);
        }

        void addStaticPortrait(TemplateScene& scene, const GroupAnimationSpec& spec,
                               float x, float y, float size) {
            // The caption clip keeps the portrait as editorial context, not as a
            // member: only the caption controller animates in that group.
            LayerHandle& card = addShape(scene,
                    ShapeSpec{.size = {size + 20.f, size + 20.f},
                              .fillColor = kImageCard,
                              .name = "ContextImageCard",
                              .cornerRadius = 30.f,
                              .strokeColor = kCardStroke,
                              .strokeWidth = 2.f},
                    x, y, spec.durationFrames);
            card.opacity(0.35f);
            LayerHandle& portrait = addImage(scene,
                    ImageSpec{.path = spec.imageAsset,
                              .name = "ContextPortrait",
                              .frame = ImageFrameStyle{.cornerRadius = 22.f,
                                                       .borderColor = kImageStroke,
                                                       .borderWidth = 2.f},
                              .fit = ImageFitMode::Contain,
                              .targetSize = {size, size}},
                    x, y, spec.durationFrames);
            portrait.opacity(0.35f);
        }

        void addCaption(TemplateScene& scene, const GroupAnimationSpec& spec,
                        const std::vector<GroupMemberTiming>& members, float x, float y,
                        bool large) {
            const GroupMemberTiming& caption = memberFor(members, GroupRole::Caption);
            LayerHandle& controller = addGroupController(scene, "group_caption", caption, spec.durationFrames);
            addShape(scene,
                    ShapeSpec{.size = {72.f, 3.f}, .fillColor = kGold, .name = "CaptionRule"},
                    x, y - 38.f, spec.durationFrames, &controller);
            addText(scene,
                    TextSpec{.text = spec.imageCaption,
                             .font = kFontPlayfairItalic,
                             .fontSize = large ? 58.f : 38.f,
                             .color = kPaper},
                    x, y, spec.durationFrames, &controller);
            addRoleTag(scene, controller, "03 / CAPTION", x, y + (large ? 70.f : 52.f),
                       spec.durationFrames);
        }

        void addDateCard(TemplateScene& scene, const GroupAnimationSpec& spec,
                         const std::vector<GroupMemberTiming>& members, float x, float y) {
            const GroupMemberTiming& date = memberFor(members, GroupRole::Date);
            LayerHandle& controller = addGroupController(scene, "group_date", date, spec.durationFrames);
            addShape(scene,
                    ShapeSpec{.size = {420.f, 200.f},
                              .fillColor = kCard,
                              .name = "DateCard",
                              .cornerRadius = 26.f,
                              .strokeColor = kCardStroke,
                              .strokeWidth = 2.f},
                    x, y, spec.durationFrames, &controller);
            addText(scene,
                    TextSpec{.text = spec.dateValue,
                             .font = kFontPlayfairBold,
                             .fontSize = 84.f,
                             .color = kPaper},
                    x, y - 18.f, spec.durationFrames, &controller);
            addText(scene,
                    TextSpec{.text = spec.dateLabel,
                             .font = kFontInterMedium,
                             .fontSize = 18.f,
                             .color = kMuted},
                    x, y + 62.f, spec.durationFrames, &controller);
            addShape(scene,
                    ShapeSpec{.size = {64.f, 3.f}, .fillColor = kGold, .name = "DateRule"},
                    x, y + 92.f, spec.durationFrames, &controller);
            addRoleTag(scene, controller, "04 / DATE", x, y - 132.f, spec.durationFrames);
        }

        void addMetricCard(TemplateScene& scene, const GroupAnimationSpec& spec,
                           const std::vector<GroupMemberTiming>& members, float x, float y) {
            const GroupMemberTiming& metric = memberFor(members, GroupRole::Metric);
            LayerHandle& controller = addGroupController(scene, "group_metric", metric, spec.durationFrames);
            addShape(scene,
                    ShapeSpec{.size = {420.f, 200.f},
                              .fillColor = kCard,
                              .name = "MetricCard",
                              .cornerRadius = 26.f,
                              .strokeColor = kCardStroke,
                              .strokeWidth = 2.f},
                    x, y, spec.durationFrames, &controller);
            addText(scene,
                    TextSpec{.text = spec.metricValue,
                             .font = kFontInterDisplayBold,
                             .fontSize = 84.f,
                             .color = kPaper},
                    x, y - 18.f, spec.durationFrames, &controller);
            addText(scene,
                    TextSpec{.text = spec.metricLabel,
                             .font = kFontInterMedium,
                             .fontSize = 18.f,
                             .color = kMuted},
                    x, y + 62.f, spec.durationFrames, &controller);
            addShape(scene,
                    ShapeSpec{.size = {220.f, 5.f}, .fillColor = kGold, .name = "MetricRule"},
                    x, y + 92.f, spec.durationFrames, &controller);
            addRoleTag(scene, controller, "05 / METRIC", x, y - 132.f, spec.durationFrames);
        }

        void addStage(TemplateScene& scene, const GroupAnimationSpec& spec) {
            addShape(scene,
                    ShapeSpec{.size = {kCanvasWidth, kCanvasHeight},
                              .fillColor = kInk,
                              .name = "Stage"},
                    kCanvasWidth * 0.5f, kCanvasHeight * 0.5f, spec.durationFrames);
            addShape(scene,
                    ShapeSpec{.size = {2200.f, 1400.f},
                              .fillColor = kInk,
                              .name = "Aura",
                              .geometry = ShapeGeometry::Ellipse,
                              .radialGradient = ShapeRadialGradient{
                                      .center = {0.5f, 0.5f},
                                      .radius = 0.5f,
                                      .stops = {{0.f, "#17304D", 0.9f},
                                                {0.62f, "#0B1422", 0.45f},
                                                {1.f, kInk, 0.f}}}},
                    kCanvasWidth * 0.5f, kCanvasHeight * 0.48f, spec.durationFrames);
            addShape(scene,
                    ShapeSpec{.size = {1600.f, 1.f}, .fillColor = "#223047", .name = "TopRule"},
                    kCanvasWidth * 0.5f, 300.f, spec.durationFrames);
            addShape(scene,
                    ShapeSpec{.size = {1600.f, 1.f}, .fillColor = "#1D2A3C", .name = "BottomRule"},
                    kCanvasWidth * 0.5f, 1000.f, spec.durationFrames);
            addText(scene,
                    TextSpec{.text = "CHRONONTEMPLATE / GROUP ANIMATION / 1920 x 1080 / 30 FPS",
                             .font = kFontInterRegular,
                             .fontSize = 15.f,
                             .color = "#50637C"},
                    kCanvasWidth * 0.5f, 1028.f, spec.durationFrames);
        }

        void validateSpec(const GroupAnimationSpec& spec) {
            if (spec.id.empty() || spec.title.empty()) {
                throw std::invalid_argument("GroupAnimationPack: id and title are required");
            }
            if (spec.fps < 1 || spec.fps > 120) {
                throw std::invalid_argument("GroupAnimationPack: fps must be in 1..120");
            }
            if (spec.durationFrames < spec.fps ||
                spec.durationFrames > spec.fps * 10) {
                throw std::invalid_argument("GroupAnimationPack: duration must be between one second and ten seconds");
            }
            if (spec.staggerFrames < 0 || spec.staggerFrames > 240) {
                throw std::invalid_argument("GroupAnimationPack: staggerFrames must be in 0..240");
            }
            if (spec.enterFrames < 1 || spec.enterFrames >= spec.durationFrames) {
                throw std::invalid_argument("GroupAnimationPack: enterFrames must fit inside the duration");
            }
            if (spec.phrase.empty() || spec.imageAsset.empty()) {
                throw std::invalid_argument("GroupAnimationPack: phrase and imageAsset are required");
            }
            const std::vector<GroupMemberTiming> timeline = groupShowcaseTimeline(spec);
            if (timeline.size() < 2 || timeline.size() > 8) {
                throw std::invalid_argument("GroupAnimationPack: a group requires 2..8 members");
            }
            for (std::size_t index = 0; index < timeline.size(); ++index) {
                if (timeline[index].offsetFrames < 0 ||
                    timeline[index].offsetFrames + spec.enterFrames >= spec.durationFrames - kExitFrames) {
                    throw std::invalid_argument("GroupAnimationPack: member entrance collides with the group exit");
                }
                for (std::size_t other = 0; other < index; ++other) {
                    if (timeline[index].role == timeline[other].role) {
                        throw std::invalid_argument("GroupAnimationPack: duplicate role in group");
                    }
                }
            }
        }

    }// namespace

    const char* groupRoleId(GroupRole role) noexcept {
        switch (role) {
            case GroupRole::Image: return "image";
            case GroupRole::ImportantPhrase: return "important_phrase";
            case GroupRole::Caption: return "caption";
            case GroupRole::Date: return "date";
            case GroupRole::Metric: return "metric";
        }
        return "unknown";
    }

    const char* groupShowcaseModeId(GroupShowcaseMode mode) noexcept {
        switch (mode) {
            case GroupShowcaseMode::AllRoles: return "all_roles";
            case GroupShowcaseMode::PhraseImage: return "phrase_image";
            case GroupShowcaseMode::PhraseCaption: return "phrase_caption";
            case GroupShowcaseMode::PhraseDate: return "phrase_date";
            case GroupShowcaseMode::PhraseMetric: return "phrase_metric";
        }
        return "unknown";
    }

    std::vector<GroupRole> groupShowcaseRoles(GroupShowcaseMode mode) {
        switch (mode) {
            case GroupShowcaseMode::AllRoles:
                return {GroupRole::ImportantPhrase, GroupRole::Image, GroupRole::Caption,
                        GroupRole::Date, GroupRole::Metric};
            case GroupShowcaseMode::PhraseImage:
                return {GroupRole::ImportantPhrase, GroupRole::Image};
            case GroupShowcaseMode::PhraseCaption:
                return {GroupRole::ImportantPhrase, GroupRole::Caption};
            case GroupShowcaseMode::PhraseDate:
                return {GroupRole::ImportantPhrase, GroupRole::Date};
            case GroupShowcaseMode::PhraseMetric:
                return {GroupRole::ImportantPhrase, GroupRole::Metric};
        }
        return {};
    }

    std::vector<GroupMemberTiming> groupShowcaseTimeline(const GroupAnimationSpec& spec) {
        const std::vector<GroupRole> roles = groupShowcaseRoles(spec.mode);
        if (roles.empty()) {
            throw std::invalid_argument("GroupAnimationPack: unknown showcase mode");
        }
        if (spec.staggerFrames < 0) {
            throw std::invalid_argument("GroupAnimationPack: staggerFrames must not be negative");
        }
        if (spec.enterFrames < 1) {
            throw std::invalid_argument("GroupAnimationPack: enterFrames must be positive");
        }
        std::vector<GroupMemberTiming> timeline;
        timeline.reserve(roles.size());
        for (std::size_t index = 0; index < roles.size(); ++index) {
            timeline.push_back(GroupMemberTiming{
                    .role = roles[index],
                    .offsetFrames = static_cast<int>(index) * spec.staggerFrames,
                    .enterFrames = spec.enterFrames});
        }
        return timeline;
    }

    void buildGroupAnimationShowcase(TemplateScene& scene, const GroupAnimationSpec& spec) {
        validateSpec(spec);
        const std::vector<GroupMemberTiming> timeline = groupShowcaseTimeline(spec);
        addStage(scene, spec);
        addPhrase(scene, spec, timeline);

        switch (spec.mode) {
            case GroupShowcaseMode::AllRoles:
                addImageMember(scene, spec, timeline, 430.f, 585.f, 380.f);
                addCaption(scene, spec, timeline, 430.f, 855.f, false);
                addDateCard(scene, spec, timeline, 960.f, 585.f);
                addMetricCard(scene, spec, timeline, 1430.f, 585.f);
                break;
            case GroupShowcaseMode::PhraseImage:
                addImageMember(scene, spec, timeline, 960.f, 620.f, 560.f);
                break;
            case GroupShowcaseMode::PhraseCaption:
                addStaticPortrait(scene, spec, 960.f, 540.f, 400.f);
                addCaption(scene, spec, timeline, 960.f, 860.f, true);
                break;
            case GroupShowcaseMode::PhraseDate:
                addDateCard(scene, spec, timeline, 960.f, 620.f);
                break;
            case GroupShowcaseMode::PhraseMetric:
                addMetricCard(scene, spec, timeline, 960.f, 620.f);
                break;
        }

        if (!hasRole(timeline, GroupRole::ImportantPhrase)) {
            throw std::invalid_argument("GroupAnimationPack: every group needs the phrase anchor");
        }
    }

    std::vector<GroupAnimationSpec> groupAnimationShowcaseSpecs() {
        return {
                GroupAnimationSpec{.id = "group_sequence_all_roles",
                                   .title = "Group Sequence - All Five Roles",
                                   .mode = GroupShowcaseMode::AllRoles,
                                   .durationFrames = 300,
                                   .staggerFrames = 14,
                                   .enterFrames = 24},
                GroupAnimationSpec{.id = "group_sequence_phrase_image",
                                   .title = "Group Sequence - Phrase + Image",
                                   .mode = GroupShowcaseMode::PhraseImage,
                                   .durationFrames = 210,
                                   .staggerFrames = 16,
                                   .enterFrames = 24},
                GroupAnimationSpec{.id = "group_sequence_phrase_caption",
                                   .title = "Group Sequence - Phrase + Caption",
                                   .mode = GroupShowcaseMode::PhraseCaption,
                                   .durationFrames = 210,
                                   .staggerFrames = 16,
                                   .enterFrames = 24},
                GroupAnimationSpec{.id = "group_sequence_phrase_date",
                                   .title = "Group Sequence - Phrase + Date",
                                   .mode = GroupShowcaseMode::PhraseDate,
                                   .durationFrames = 210,
                                   .staggerFrames = 16,
                                   .enterFrames = 24},
                GroupAnimationSpec{.id = "group_sequence_phrase_metric",
                                   .title = "Group Sequence - Phrase + Metric",
                                   .mode = GroupShowcaseMode::PhraseMetric,
                                   .durationFrames = 210,
                                   .staggerFrames = 16,
                                   .enterFrames = 24}};
    }

}// namespace chronontemplate
