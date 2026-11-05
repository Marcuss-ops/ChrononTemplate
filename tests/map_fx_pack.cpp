// ChrononTemplate — the minimal map FX pack contract.
//
// These four ids are the shared vocabulary between the authoring pack and the
// RenderingGen `map_fx` runtime parameter. They intentionally stay out of the
// ChrononPlugin GPU catalog: this is the lightweight, primitive-only lane.
#include "chronontemplate/map/ModernMapPack.hpp"
#include "fake_content_host.hpp"

#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace chronontemplate;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

std::vector<chrononmotion::Vector2> anchorsFor(MapFxKind kind) {
    if (kind == MapFxKind::CityNetworkExpansion) {
        return {{420.f, 360.f}, {960.f, 540.f}, {1480.f, 700.f}};
    }
    return {{960.f, 540.f}};
}

MapFxSpec specFor(MapFxKind kind) {
    MapFxSpec spec;
    spec.kind = kind;
    spec.durationFrames = 120;
    spec.radius = 120.f;
    return spec;
}

} // namespace

int main() {
    try {
        require(mapFxKinds().size() == 4, "the minimal pack must expose exactly four effects");
        for (const MapFxKind kind : mapFxKinds()) {
            require(std::string(mapFxId(kind)) == mapFxId(mapFxKindFromId(mapFxId(kind))),
                    "map fx ids must round-trip");
            require(std::string(mapFxAnchorPolicy(kind)) ==
                        (kind == MapFxKind::CityNetworkExpansion ? "2..8" : "1"),
                    "anchor policy drifted");
        }

        chronontemplate_test::FakeContentHost host;
        for (const MapFxKind kind : mapFxKinds()) {
            TemplateScene scene("map_fx_" + std::string(mapFxId(kind)), 30.f, host, 1920.f, 1080.f);
            const auto anchors = anchorsFor(kind);
            const MapFxComposition built = addMapFx(scene, specFor(kind), anchors, 0, 150);
            require(!built.layers.empty(), std::string(mapFxId(kind)) + " emitted no layers");
            require(built.inFrame == 0 && built.endFrame == 120, "fx frame window drifted");
            require(scene.validate().empty(), std::string(mapFxId(kind)) + " produced an invalid scene");

            const auto frame = scene.submit(built.inFrame + 40);
            for (const LayerHandle* layer : built.layers) {
                require(layer != nullptr, "null fx layer");
                require(chronontemplate_test::findLayer(frame, layer->id()) != nullptr,
                        std::string(mapFxId(kind)) + " layer " + layer->name() + " is missing at mid-frame");
            }
        }

        // The network needs an edge to reveal; the focus effects need a place.
        {
            TemplateScene scene("map_fx_bad_anchor_count", 30.f, host, 1920.f, 1080.f);
            bool threw = false;
            try {
                (void)addMapFx(scene, specFor(MapFxKind::CityNetworkExpansion), {{960.f, 540.f}}, 0, 150);
            } catch (const std::invalid_argument&) {
                threw = true;
            }
            require(threw, "city_network_expansion must reject a single anchor");
        }
        {
            TemplateScene scene("map_fx_bad_color", 30.f, host, 1920.f, 1080.f);
            MapFxSpec spec = specFor(MapFxKind::AreaGlowPulse);
            spec.accent = "cyan";
            bool threw = false;
            try {
                (void)addMapFx(scene, spec, {{960.f, 540.f}}, 0, 150);
            } catch (const std::invalid_argument&) {
                threw = true;
            }
            require(threw, "invalid accent color must be rejected");
        }
        {
            TemplateScene scene("map_fx_bad_window", 30.f, host, 1920.f, 1080.f);
            MapFxSpec spec = specFor(MapFxKind::LightBeamDrop);
            spec.delayFrames = 150;
            bool threw = false;
            try {
                (void)addMapFx(scene, spec, {{960.f, 540.f}}, 0, 150);
            } catch (const std::invalid_argument&) {
                threw = true;
            }
            require(threw, "a delay outside the map window must be rejected");
        }

        std::cout << "minimal map fx pack: 4 effects, primitives-only, scene-valid\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "map_fx_pack test failed: " << error.what() << '\n';
        return 1;
    }
}
