#include "chronontemplate/investigation_board/InvestigationBoardPack.hpp"

#include "chrononmotion/math/MathUtils.hpp"
#include "chrononmotion/motion/Presets.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace chronontemplate {

    namespace {
        using chrononmotion::Vector3;
        using chrononmotion::motion::Easing;

        void validate(const InvestigationBoardSpec& spec) {
            if (spec.items.empty())
                throw std::invalid_argument("addInvestigationBoard: at least one item is required");
            if (spec.duration <= 0 || spec.inFrame < 0 || spec.staggerFrames < 0)
                throw std::invalid_argument("addInvestigationBoard: timing must be non-negative and duration positive");
            if (!std::isfinite(spec.panYaw) || !std::isfinite(spec.pinSize) || spec.pinSize <= 0.f ||
                !std::isfinite(spec.stringWidth) || spec.stringWidth <= 0.f)
                throw std::invalid_argument("addInvestigationBoard: pin size, string width and pan must be finite and positive");
            for (const auto& item : spec.items) {
                if (item.path.empty() || !(item.width > 0.f) || !(item.height > 0.f) ||
                    !std::isfinite(item.x) || !std::isfinite(item.y) || !std::isfinite(item.rotationDegrees))
                    throw std::invalid_argument("addInvestigationBoard: each item needs a path and positive finite size");
            }
            for (const auto& c : spec.connections) {
                if (c.from >= spec.items.size() || c.to >= spec.items.size() || c.from == c.to)
                    throw std::invalid_argument("addInvestigationBoard: connection must join two different existing items");
            }
        }

        float seconds(int frame, float fps) { return static_cast<float>(frame) / fps; }

        // Pin sits at the top-centre of its card.
        Vector3 pinCentre(const InvestigationBoardItem& item, float pinSize) {
            return Vector3(item.x, item.y - item.height * 0.5f + pinSize * 0.5f, 0.f);
        }
    }

    InvestigationBoardLayers addInvestigationBoard(TemplateScene& scene,
                                                   const InvestigationBoardSpec& spec) {
        validate(spec);
        const float fps = scene.fps();
        const float canvasW = scene.canvas().x;
        const float canvasH = scene.canvas().y;
        InvestigationBoardLayers out{};
        out.endFrame = spec.inFrame + spec.duration;

        // Cork plate fills the canvas and stays for the whole board.
        scene.image(ImageSpec{.path = spec.corkPath, .name = "Cork",
                              .fit = ImageFitMode::Cover,
                              .targetSize = chrononmotion::Vector2(canvasW, canvasH)})
             .position(canvasW * 0.5f, canvasH * 0.5f, 0.f)
             .alive(0, out.endFrame);

        // Cards: a drop shadow, then the paper card, each entering in turn.
        for (std::size_t i = 0; i < spec.items.size(); ++i) {
            const auto& item = spec.items[i];
            const int start = spec.inFrame + static_cast<int>(i) * spec.staggerFrames;

            LayerHandle& shadow = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(item.width, item.height),
                    .fillColor = "#000000", .name = "Shadow"});
            shadow.position(item.x + spec.shadowOffset, item.y + spec.shadowOffset, 0.f)
                  .opacity(spec.shadowOpacity)
                  .animate(FadeIn{.inFrame = start, .duration = 12});
            shadow.layer().tracks.rotation.add(0.f, Vector3(0.f, 0.f,
                    chrononmotion::math::degToRad(item.rotationDegrees)), Easing::easeOut());

            LayerHandle& card = scene.image(ImageSpec{
                    .path = item.path, .name = "Card",
                    .frame = ImageFrameStyle{.borderColor = item.borderColor,
                                             .borderWidth = item.borderWidth},
                    .fit = ImageFitMode::Cover,
                    .targetSize = chrononmotion::Vector2(item.width, item.height)});
            card.position(item.x, item.y, 0.f)
                .animate(FadeIn{.inFrame = start, .duration = 12});
            card.layer().tracks.rotation.add(0.f, Vector3(0.f, 0.f,
                    chrononmotion::math::degToRad(item.rotationDegrees)), Easing::easeOut());
            out.cards.push_back(&card);
        }

        // Pins and strings are authored after the cards so they sit on top.
        for (const auto& c : spec.connections) {
            const Vector3 a = pinCentre(spec.items[c.from], spec.pinSize);
            const Vector3 b = pinCentre(spec.items[c.to], spec.pinSize);
            const float dx = b.x - a.x;
            const float dy = b.y - a.y;
            const float length = std::sqrt(dx * dx + dy * dy);
            const int start = spec.inFrame + static_cast<int>(std::max(c.from, c.to)) * spec.staggerFrames;

            LayerHandle& string = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(length, spec.stringWidth),
                    .fillColor = "#B0141C", .name = "String"});
            string.position((a.x + b.x) * 0.5f, (a.y + b.y) * 0.5f, 0.f)
                  .animate(FadeIn{.inFrame = start, .duration = 10});
            string.layer().tracks.rotation.add(0.f, Vector3(0.f, 0.f, std::atan2(dy, dx)),
                                               Easing::easeOut());
            out.strings.push_back(&string);
        }

        for (const auto& item : spec.items) {
            const Vector3 p = pinCentre(item, spec.pinSize);
            LayerHandle& pin = scene.image(ImageSpec{
                    .path = spec.pinPath, .name = "Pin",
                    .fit = ImageFitMode::Contain,
                    .targetSize = chrononmotion::Vector2(spec.pinSize, spec.pinSize)});
            pin.position(p.x, p.y, 0.f);
            out.pins.push_back(&pin);
        }

        // One slow pan over the whole board.
        scene.camera().orbit(spec.panYaw, 0.f).between(spec.inFrame, out.endFrame);
        return out;
    }

}// namespace chronontemplate
