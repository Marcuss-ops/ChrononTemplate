// ChrononTemplate — tactical territory fill contract.
//
// The pack must stay a primitive-only recipe: a dark grid, one fill plus two
// glows per already-projected ring, and a title that reveals late. No host
// request may carry a bitmap or a projection result from inside the pack.
#include "chronontemplate/map/TacticalFillPack.hpp"

#include "fake_content_host.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion::Vector2;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

TacticalFillSpec sampleSpec() {
    TacticalFillSpec spec;
    spec.title = "JERUSALEM";
    spec.subtitle = "Capital of Israel";
    spec.regions = {
        TacticalFillRegion{{
            {520.f, 360.f}, {860.f, 300.f}, {980.f, 520.f},
            {760.f, 700.f}, {480.f, 560.f}}},
        TacticalFillRegion{{
            {1180.f, 430.f}, {1320.f, 390.f}, {1400.f, 540.f},
            {1210.f, 610.f}}},
    };
    return spec;
}

void packDrawsGridTerritoryAndText() {
    FakeContentHost host;
    TemplateScene scene("tactical_fill", 30.f, host, 1920.f, 1080.f);
    const auto built = addTacticalFill(scene, sampleSpec());

    require(built.background != nullptr && built.minorGrid != nullptr && built.majorGrid != nullptr,
            "the tactical plate needs a background and two grid densities");
    require(built.territories.size() == 2, "every projected ring becomes one territory");
    for (const auto& territory : built.territories) {
        require(territory.outerGlow != nullptr &&
                    territory.innerGlow != nullptr && territory.fill != nullptr,
                "a territory needs both glows and its fill");
    }
    require(built.title != nullptr && built.subtitle != nullptr,
            "title and subtitle are separately addressable");

    const auto* fill = host.findShapeRequest("tactical_fill_territory_0_fill");
    require(fill != nullptr, "the fill shape must be requested from the host");
    require(fill->geometry == ShapeGeometry::Path && fill->path.size() == 6,
            "the closed five-point ring lowers to moveTo + four lineTo + close");
    require(fill->fillColor == "#24A62D" && fill->strokeColor == "#F6F9FC",
            "the fill and outline colours are the tactical palette");
    // Authored-origin shape layers clip to [0,size]: a point outside that box
    // reaches the renderer as a missing wedge, not a cropped glow.
    for (const auto& command : fill->path) {
        require(command.point.x >= 0.f && command.point.x <= fill->size.x &&
                    command.point.y >= 0.f && command.point.y <= fill->size.y,
                "territory path points stay inside the layer bounds");
    }
    const auto* minor = host.findShapeRequest("tactical_fill_grid_minor");
    require(minor != nullptr && minor->geometry == ShapeGeometry::Path,
            "the grid is authored as a path in local 0..size coordinates");
    for (const auto& command : minor->path) {
        require(command.point.x >= 0.f && command.point.x <= minor->size.x &&
                    command.point.y >= 0.f && command.point.y <= minor->size.y,
                "grid path points stay inside the layer bounds");
    }
    require(built.background->name() == "tactical_fill_background" &&
                built.background->layer().tracks.position.empty(),
            "the plate is a full-frame static background at the scene centre");

    const auto* outer = host.findShapeRequest("tactical_fill_territory_0_outer_glow");
    require(outer != nullptr && outer->glowRadius > 0.f && outer->glowIntensity > 0.f,
            "the outer glow is a native shape effect");
    require(outer->fillEnabled == false, "the glow layers do not paint their interior");

    const auto frame = scene.submit(60);
    for (const LayerHandle* layer : {built.background, built.minorGrid, built.majorGrid,
                                     built.territories[0].outerGlow,
                                     built.territories[0].innerGlow,
                                     built.territories[0].fill,
                                     built.title, built.subtitle}) {
        require(findLayer(frame, layer->id()) != nullptr,
                layer->name() + " must reach the submitted frame");
    }
    require(scene.validate().empty(), "the tactical fill scene validates");
}

void revealAndTextTimingAreDeterministic() {
    FakeContentHost host;
    TemplateScene scene("tactical_fill_timing", 30.f, host, 1920.f, 1080.f);
    const auto built = addTacticalFill(scene, sampleSpec());

    const auto atStart = scene.submit(0);
    const auto atMiddle = scene.submit(60);
    const auto atEnd = scene.submit(119);
    const auto* startFill = findLayer(atStart, built.territories[0].fill->id());
    const auto* middleFill = findLayer(atMiddle, built.territories[0].fill->id());
    require(startFill != nullptr && middleFill != nullptr,
            "the fill must be alive across the reveal");

    const auto startScale = startFill->transform.world[0];
    const auto middleScale = middleFill->transform.world[0];
    require(startScale < middleScale, "the territory grows out of its centre");
    require(findLayer(atEnd, built.territories[0].fill->id()) != nullptr,
            "the territory stays on screen through the final frame");
    // The reveal must converge on the authored bbox origin, not on the
    // off-canvas scene coordinates that used to push the ring out of frame.
    const auto* endFill = findLayer(atEnd, built.territories[0].fill->id());
    require(endFill != nullptr && std::abs(endFill->transform.world.elements[12]) < 1200.f &&
                std::abs(endFill->transform.world.elements[13]) < 700.f,
            "the settled territory stays inside the canvas-centred scene");

    // The title has no visible content at frame zero (fade starts at 42%);
    // the motion layer still exists, but its opacity is already keyed low.
    const auto* title = findLayer(atStart, built.title->id());
    require(title != nullptr, "the title layer exists from the start");
    require(title->transform.opacity <= 0.01f,
            "the title is held until its late reveal");

    require(scene.validate().empty(), "the authored timing validates");
}

void malformedInputFailsClosed() {
    FakeContentHost host;

    {
        TemplateScene scene("tactical_fill_empty", 30.f, host);
        TacticalFillSpec spec;
        bool threw = false;
        try { (void)addTacticalFill(scene, spec); }
        catch (const std::invalid_argument&) { threw = true; }
        require(threw, "an empty territory list must be rejected");
    }
    {
        TemplateScene scene("tactical_fill_short", 30.f, host);
        TacticalFillSpec spec = sampleSpec();
        spec.regions[0].points = {{10.f, 10.f}, {20.f, 20.f}};
        bool threw = false;
        try { (void)addTacticalFill(scene, spec); }
        catch (const std::invalid_argument&) { threw = true; }
        require(threw, "a ring with fewer than three points must be rejected");
    }
    {
        TemplateScene scene("tactical_fill_nan", 30.f, host);
        TacticalFillSpec spec = sampleSpec();
        spec.regions[0].points[1].x = std::nanf("");
        bool threw = false;
        try { (void)addTacticalFill(scene, spec); }
        catch (const std::invalid_argument&) { threw = true; }
        require(threw, "non-finite points must be rejected");
    }
    {
        TemplateScene scene("tactical_fill_colour", 30.f, host);
        TacticalFillSpec spec = sampleSpec();
        spec.fill = "green";
        bool threw = false;
        try { (void)addTacticalFill(scene, spec); }
        catch (const std::invalid_argument&) { threw = true; }
        require(threw, "a non-hex fill colour must be rejected");
    }
    {
        TemplateScene scene("tactical_fill_duration", 30.f, host);
        TacticalFillSpec spec = sampleSpec();
        spec.duration = 12;
        bool threw = false;
        try { (void)addTacticalFill(scene, spec); }
        catch (const std::invalid_argument&) { threw = true; }
        require(threw, "a clip shorter than the FX floor must be rejected");
    }
}

} // namespace

int main() {
    try {
        require(std::string(tacticalFillId()) == "territory_tactical_fill",
                "the runtime id must stay aligned with the map renderer");
        packDrawsGridTerritoryAndText();
        revealAndTextTimingAreDeterministic();
        malformedInputFailsClosed();
        std::cout << "tactical fill pack: grid + territory + late text, primitives-only, scene-valid\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "tactical_fill_pack test failed: " << error.what() << '\n';
        return 1;
    }
}
