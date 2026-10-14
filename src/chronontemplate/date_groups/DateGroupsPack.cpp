#include "chronontemplate/date_groups/DateGroupsPack.hpp"

#include <cstddef>
#include <string>

namespace chronontemplate {

    namespace {

        constexpr float kDateFontSize = 200.f;
        constexpr float kLabelFontSize = 42.f;
        constexpr int kRiseFrames = 14;
        constexpr int kFadeOutFrames = 12;

        LayerHandle& addFontText(TemplateScene& scene, unsigned parentId, const DateGroupsSpec& spec,
                                 const std::string& name, const std::string& text, float fontSize,
                                 const std::string& color, float x, float y) {
            LayerHandle& label = scene.text(TextSpec{.text = text, .font = spec.font, .fontSize = fontSize,
                                                     .color = color, .name = name});
            label.parent(parentId);
            label.position(x, y);
            label.alive(0, 150);
            return label;
        }

        int framesPerDate(const DateGroupsSpec& spec) {
            return spec.secondsPerDate * static_cast<int>(spec.fps);
        }

        void validate(const DateGroupsSpec& spec) {
            elements::require(!spec.name.empty(), "addDateGroups: name is required");
            elements::require(spec.fps > 0.f, "addDateGroups: fps must be positive");
            elements::require(spec.secondsPerDate > 0, "addDateGroups: secondsPerDate must be positive");
            elements::require(framesPerDate(spec) > 0, "addDateGroups: a date must last at least one frame");
            elements::require(spec.width > 0.f && spec.height > 0.f,
                              "addDateGroups: canvas size must be positive");
            elements::require(!spec.animations.empty(), "addDateGroups: at least one animation is required");
            for (const DateAnimation& animation : spec.animations) {
                elements::require(!animation.name.empty(), "addDateGroups: every animation needs a name");
                elements::require(!animation.dates.empty(), "addDateGroups: every animation needs a date");
                for (const std::string& date : animation.dates) {
                    elements::require(!date.empty(), "addDateGroups: dates must be non-empty");
                }
            }
        }

    } // namespace

    int dateGroupsDurationFrames(const DateGroupsSpec& spec) {
        validate(spec);
        int total = 0;
        for (const DateAnimation& animation : spec.animations) {
            total += static_cast<int>(animation.dates.size()) * framesPerDate(spec);
        }
        return total;
    }

    LayerHandle& addDateGroups(TemplateScene& scene, const DateGroupsSpec& spec) {
        validate(spec);
        const elements::ElementPalette palette = elements::paletteFor(spec.style);
        const int perDate = framesPerDate(spec);
        const int total = dateGroupsDurationFrames(spec);

        // Children are authored relative to the canvas centre by the lowering,
        // so the root group stays at the origin (a centred root doubles the offset).
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, total);
        const unsigned rootId = root.id();

        LayerHandle& paper = elements::addBar(scene, rootId, spec.name + "_paper",
                                              spec.width, spec.height, 0.f, 0.f, palette.paper);
        paper.alive(0, total);

        int offset = 0;
        for (std::size_t a = 0; a < spec.animations.size(); ++a) {
            const DateAnimation& animation = spec.animations[a];
            const int animationEnd = offset + static_cast<int>(animation.dates.size()) * perDate;
            const std::string prefix = spec.name + "_" + std::to_string(a);

            LayerHandle& label = addFontText(scene, rootId, spec, prefix + "_label", animation.name,
                                             kLabelFontSize, palette.muted, 0.f, -230.f);
            label.alive(offset, animationEnd);

            for (std::size_t d = 0; d < animation.dates.size(); ++d) {
                const int start = offset + static_cast<int>(d) * perDate;
                const int end = start + perDate;
                const std::string stem = prefix + "_" + std::to_string(d);

                LayerHandle& date = addFontText(scene, rootId, spec, stem + "_date", animation.dates[d],
                                                kDateFontSize, palette.ink, 0.f, -40.f);
                date.alive(start, end);
                elements::applyElementMotion(date,
                        elements::ElementMotion{.preset = elements::ElementMotionPreset::Rise,
                                                .startFrame = start,
                                                .endFrame = start + kRiseFrames},
                        spec.fps);
                date.animate(FadeOut{.startFrame = end - kFadeOutFrames, .duration = kFadeOutFrames});

                LayerHandle& rule = elements::addBar(scene, rootId, stem + "_rule",
                                                     160.f, 4.f, 0.f, 110.f, palette.accent);
                rule.alive(start, end);
            }
            offset = animationEnd;
        }
        return root;
    }

} // namespace chronontemplate
