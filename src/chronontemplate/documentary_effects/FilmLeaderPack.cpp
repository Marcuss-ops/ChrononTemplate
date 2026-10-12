#include "chronontemplate/documentary_effects/FilmLeaderPack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <cmath>
#include <stdexcept>
#include <string>

namespace chronontemplate::docfx {

    namespace {

        void validate(const FilmLeaderSpec& spec, float canvasW, float canvasH) {
            if (!std::isfinite(spec.numeralSize))
                throw std::invalid_argument("leader: numeralSize must be finite");
            if (spec.startNumber < 1 || spec.startNumber > 9 ||
                spec.framesPerBeat < 6 || spec.framesPerBeat > 60 ||
                spec.numeralSize <= 0.f || spec.numeralSize > std::min(canvasW, canvasH) ||
                spec.inFrame < 0)
                throw std::invalid_argument("leader: spec is outside supported ranges");
            if (!chronon3d::render_plan::parse_hex_color(spec.fieldColor) ||
                !chronon3d::render_plan::parse_hex_color(spec.numeralColor) ||
                !chronon3d::render_plan::parse_hex_color(spec.accentColor))
                throw std::invalid_argument("leader: colors must be #RRGGBB");
        }

    } // namespace

    int filmLeaderFrames(const FilmLeaderSpec& spec) {
        return spec.startNumber * spec.framesPerBeat + 30;
    }

    FilmLeaderLayers addFilmLeader(TemplateScene& scene, const FilmLeaderSpec& spec) {
        validate(spec, scene.canvas().x, scene.canvas().y);
        const float canvasW = scene.canvas().x;
        const float canvasH = scene.canvas().y;
        const int beats = spec.startNumber * spec.framesPerBeat;
        const int endFrame = spec.inFrame + filmLeaderFrames(spec);
        FilmLeaderLayers out{};

        // Grainy gray field with animated grain baked in the request.
        LayerHandle& field = scene.shape(ShapeSpec{
                .size = scene.canvas(), .fillColor = spec.fieldColor,
                .name = "leader_field", .noiseAmount = 0.22f,
                .noiseSeed = spec.grainSeed, .animatedNoise = true, .noiseSize = 2.f});
        field.position(canvasW * 0.5f, canvasH * 0.5f);
        field.alive(spec.inFrame, endFrame);
        out.field = field.id();

        // Crosshairs + pulsing ring behind the numerals.
        LayerHandle& hBar = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(canvasW, 6.f),
                .fillColor = spec.accentColor, .name = "leader_cross_h"});
        hBar.position(canvasW * 0.5f, canvasH * 0.5f);
        hBar.opacity(0.5f);
        hBar.alive(spec.inFrame, spec.inFrame + beats);
        LayerHandle& vBar = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(6.f, canvasH),
                .fillColor = spec.accentColor, .name = "leader_cross_v"});
        vBar.position(canvasW * 0.5f, canvasH * 0.5f);
        vBar.opacity(0.5f);
        vBar.alive(spec.inFrame, spec.inFrame + beats);
        LayerHandle& ring = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.numeralSize * 1.9f,
                                               spec.numeralSize * 1.9f),
                .fillColor = "#FFFFFF", .name = "leader_ring",
                .fillEnabled = false, .geometry = ShapeGeometry::Ellipse,
                .strokeColor = spec.numeralColor, .strokeWidth = 5.f});
        ring.position(canvasW * 0.5f, canvasH * 0.5f);
        ring.alive(spec.inFrame, spec.inFrame + beats);
        ring.animate(ScalePop{.inFrame = spec.inFrame, .duration = beats,
                              .from = 1.06f, .to = 0.94f});

        // One numeral per beat, slamming in with a settle pop.
        for (int n = 0; n < spec.startNumber; ++n) {
            const int onset = spec.inFrame + n * spec.framesPerBeat;
            const int value = spec.startNumber - n;
            LayerHandle& numeral = scene.text(TextSpec{
                    .text = std::to_string(value), .fontSize = spec.numeralSize,
                    .color = spec.numeralColor,
                    .name = "leader_" + std::to_string(value)});
            numeral.position(canvasW * 0.5f, canvasH * 0.5f);
            numeral.alive(onset, onset + spec.framesPerBeat);
            numeral.animate(ScalePop{.inFrame = onset, .duration = 8,
                                     .from = 1.6f, .to = 1.f});
            numeral.animate(FadeIn{.inFrame = onset, .duration = 4});
        }

        LayerHandle& start = scene.text(TextSpec{
                .text = "PICTURE START", .fontSize = spec.numeralSize * 0.28f,
                .color = spec.numeralColor, .name = "leader_start"});
        start.position(canvasW * 0.5f, canvasH * 0.5f);
        start.alive(spec.inFrame + beats, endFrame);
        start.animate(FadeIn{.inFrame = spec.inFrame + beats, .duration = 10});
        out.startCard = start.id();
        return out;
    }

    const char* filmLeaderId() noexcept {
        return "docfx_film_leader_v1";
    }

} // namespace chronontemplate::docfx
