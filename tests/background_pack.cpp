#include "chronontemplate/backgrounds/BackgroundPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    void everyLookHasAStableId() {
        section("background looks have stable ids");
        const std::vector<BackgroundLook> looks = backgroundLooks();
        const std::vector<std::string> expectedIds{
                "bg_solid_tint", "bg_letterbox_bars", "bg_vertical_split", "bg_vignette_pulse",
                "bg_corner_glow", "bg_documentary_grid", "bg_radar_sweep", "bg_archive_dust",
                "bg_mesh_gradient", "bg_grid_pattern", "bg_particles", "bg_aurora",
                "bg_dark_veil", "bg_dot_grid", "bg_dot_field", "bg_gradient_waves",
                "bg_grainient", "bg_ripple_grid", "bg_shape_grid", "bg_silk"};
        check(looks.size() == expectedIds.size(),
              "the pack exposes twenty looks including all ten React-inspired backgrounds");
        if (looks.size() == expectedIds.size()) {
            for (std::size_t i = 0; i < looks.size(); ++i) {
                check(backgroundLookId(looks[i]) == expectedIds[i],
                      "each background has its exact append-only stable ID");
            }
        }
        for (const BackgroundLook look : looks) {
            const std::string id = backgroundLookId(look);
            check(id.rfind("bg_", 0) == 0, "every look id is namespaced with bg_");
        }
    }

    void everyLookBuildsAFullFrameBackground() {
        section("background looks build and submit");
        for (const BackgroundLook look : backgroundLooks()) {
            FakeContentHost host;
            TemplateScene scene(std::string("bg_") + backgroundLookId(look), 30.f, host,
                                1920.f, 1080.f);
            const BackgroundComposition built = addBackground(scene, BackgroundSpec{.look = look});

            check(built.ground != nullptr, "every look authors a ground layer");
            check(built.endFrame == 150, "every look ends at its authored in-frame plus duration");

            const FrameSubmission start = scene.submit(0);
            const FrameSubmission middle = scene.submit(75);
            const FrameSubmission end = scene.submit(150);
            const BoundLayer* ground = findLayer(middle, built.ground->id());
            check(ground && ground->draws(), "the ground draws at the middle of the clip");
            if (ground) {
                check(ground->content.isImage(), "the ground is a rasterized shape layer");
                check(std::isfinite(ground->transform.opacity) &&
                              ground->transform.opacity >= 0.f && ground->transform.opacity <= 1.f,
                      "the ground opacity stays finite and in range");
            }
            for (LayerHandle* accent : built.accents) {
                const BoundLayer* a = findLayer(start, accent->id());
                const BoundLayer* b = findLayer(middle, accent->id());
                const BoundLayer* c = findLayer(end, accent->id());
                check(a && b && c, "every accent layer submits across the clip");
                if (b) {
                    check(std::isfinite(b->transform.opacity),
                          "every accent opacity stays finite");
                }
            }
            check(scene.validate().empty(), "every background scene validates");
        }
    }

    void documentaryLooksHaveStableLayerIdsAndFadeAcrossTheirWindow() {
        section("documentary looks submit distinct animated layers");
        for (const BackgroundLook look : {BackgroundLook::DocumentaryGrid,
                                          BackgroundLook::RadarSweep,
                                          BackgroundLook::ArchiveDust,
                                          BackgroundLook::MeshGradient,
                                          BackgroundLook::GridPattern,
                                          BackgroundLook::Particles,
                                          BackgroundLook::Aurora,
                                          BackgroundLook::DarkVeil,
                                          BackgroundLook::DotGrid,
                                          BackgroundLook::DotField,
                                          BackgroundLook::GradientWaves,
                                          BackgroundLook::Grainient,
                                          BackgroundLook::RippleGrid,
                                          BackgroundLook::ShapeGrid,
                                          BackgroundLook::Silk}) {
            FakeContentHost host;
            TemplateScene scene(backgroundLookId(look), 30.f, host, 1920.f, 1080.f);
            BackgroundSpec spec;
            spec.look = look;
            spec.inFrame = 12;
            spec.duration = 150;
            const BackgroundComposition built = addBackground(scene, spec);
            const FrameSubmission start = scene.submit(spec.inFrame);
            const FrameSubmission middle = scene.submit(spec.inFrame + spec.duration / 2);
            const FrameSubmission end = scene.submit(built.endFrame);
            std::set<std::string> names;

            const std::size_t minimumLayers =
                look == BackgroundLook::DotGrid ? 1u :
                look == BackgroundLook::DotField ? 2u :
                look == BackgroundLook::RippleGrid ? 2u :
                look == BackgroundLook::Grainient ? 1u :
                look == BackgroundLook::Silk ? 1u :
                look == BackgroundLook::DarkVeil ? 1u :
                look == BackgroundLook::Aurora ? 2u :
                look == BackgroundLook::GradientWaves ? 1u :
                look == BackgroundLook::MeshGradient ? 4u : 9u;
            check(built.accents.size() >= minimumLayers,
                  "each procedural background authors the expected native layers");
            if (look == BackgroundLook::DotGrid) {
                const auto* dots = host.findShapeRequest("background_dots");
                check(dots && dots->geometry == ShapeGeometry::DotGrid && dots->gridSpacing >= 28.f,
                      "DotGrid uses a native regular dot primitive with bounded spacing");
            }
            if (look == BackgroundLook::Grainient || look == BackgroundLook::GradientWaves) {
                const auto* field = host.findShapeRequest(look == BackgroundLook::Grainient
                    ? "background_grainient" : "background_gradient_waves");
                check(field && field->field && field->noiseAmount > 0.f,
                      "field presets combine native field color and seeded grain on the same fill");
            }
            if (look == BackgroundLook::RippleGrid) {
                const auto ring = std::find_if(built.accents.begin(), built.accents.end(),
                    [](const LayerHandle* layer) { return layer->name() == "background_ripple_ring"; });
                check(ring != built.accents.end(), "RippleGrid authors its named ring layer");
                const auto* ringRequest = host.findShapeRequest("background_ripple_ring");
                check(ringRequest && ringRequest->geometry == ShapeGeometry::Ellipse &&
                          ringRequest->strokeColor == spec.rippleGrid.gridColor && !ringRequest->fillEnabled,
                      "RippleGrid uses a stroked native ring, not a filled halo");
            }
            if (look == BackgroundLook::DocumentaryGrid) {
                check(built.accents.size() == 38,
                      "1920x1080 grid creates 34 grid lines and four reticle ticks");
            }
            if (look == BackgroundLook::GridPattern) {
                check(built.accents.size() == 33,
                      "1920x1080 GridPattern creates its 21 vertical and 12 visible horizontal lines");
            }
            if (look == BackgroundLook::MeshGradient) {
                check(host.lastShapeRequest().geometry == ShapeGeometry::Ellipse &&
                              host.lastShapeRequest().radialGradient.has_value(),
                      "mesh fields lower as native radial-gradient ellipses");
            }
            if (look == BackgroundLook::Particles) {
                check(built.accents.size() == 100,
                      "Particles creates its default quantity of one hundred native dots");
            }
            if (look == BackgroundLook::Aurora || look == BackgroundLook::DarkVeil ||
                look == BackgroundLook::GradientWaves || look == BackgroundLook::Grainient ||
                look == BackgroundLook::Silk) {
                check(!built.accents.empty(), "field-based React looks author native render layers");
            }
            for (LayerHandle* accent : built.accents) {
                check(names.insert(accent->name()).second, "documentary layer names are unique");
                const BoundLayer* atStart = findLayer(start, accent->id());
                const BoundLayer* atMiddle = findLayer(middle, accent->id());
                const BoundLayer* atEnd = findLayer(end, accent->id());
                check(atStart && atMiddle && atEnd, "documentary layers submit at start, middle and end");
                if (atStart && atMiddle && atEnd) {
                    check(std::abs(atStart->transform.opacity) < 0.001f,
                          "documentary accents start hidden before their reveal");
                    check(std::isfinite(atMiddle->transform.opacity) &&
                                  atMiddle->transform.opacity > 0.f && atMiddle->transform.opacity <= 1.f,
                          "documentary accents become visible with bounded opacity");
                    check(std::abs(atEnd->transform.opacity) < 0.001f,
                          "documentary accents fade out by the end frame");
                }
            }
            check(scene.validate().empty(), "documentary background scene validates");
        }
    }

    void radarSweepUsesAProgressiveMotionTrack() {
        section("radar scan line moves across the full canvas");
        FakeContentHost host;
        TemplateScene scene("bg_radar_motion", 30.f, host, 1920.f, 1080.f);
        BackgroundSpec spec;
        spec.look = BackgroundLook::RadarSweep;
        spec.inFrame = 6;
        spec.duration = 120;
        const BackgroundComposition built = addBackground(scene, spec);
        const LayerHandle* scan = nullptr;
        for (LayerHandle* accent : built.accents) {
            if (accent->name() == "background_scan_line") scan = accent;
        }
        check(scan != nullptr, "radar look exposes its named scan line");
        if (scan) {
            const auto& keys = scan->layer().tracks.position.keys();
            check(keys.size() == 2, "scan line has a two-point deterministic motion track");
            if (keys.size() == 2) {
                checkNear(keys.front().value.x, 0.f, 0.001f, "scan line begins at the left canvas edge");
                checkNear(keys.back().value.x, 1920.f, 0.001f, "scan line ends at the right canvas edge");
                check(keys.back().time > keys.front().time, "scan line advances over time");
            }
            const int exitStart = built.endFrame - 15;
            const FrameSubmission leftFrame = scene.submit(spec.inFrame);
            const FrameSubmission rightFrame = scene.submit(exitStart);
            const BoundLayer* leftScan = findLayer(leftFrame, scan->id());
            const BoundLayer* rightScan = findLayer(rightFrame, scan->id());
            check(leftScan && rightScan, "scan line is submitted at both motion endpoints");
            if (leftScan && rightScan) {
                checkNear(leftScan->transform.world[12], 0.f, 0.001f,
                          "renderer submission places the scan line at the left edge");
                checkNear(rightScan->transform.world[12], 1920.f, 0.01f,
                          "renderer submission moves the scan line to the right edge");
            }
        }
    }

    void gridPatternFillsRequestedCells() {
        section("grid pattern supports filled square cells");
        FakeContentHost host;
        TemplateScene scene("bg_grid_squares", 30.f, host, 640.f, 360.f);
        BackgroundSpec spec;
        spec.look = BackgroundLook::GridPattern;
        spec.gridSpacing = 80.f;
        spec.gridSquares = {{{1, 1}}, {{4, 2}}};
        const BackgroundComposition built = addBackground(scene, spec);
        int filledSquares = 0;
        for (LayerHandle* layer : built.accents) {
            if (layer->name().find("_grid_square_") != std::string::npos) ++filledSquares;
        }
        check(filledSquares == 2, "GridPattern draws the requested in-bounds highlighted cells");
        check(scene.validate().empty(), "filled GridPattern scene validates");
        check(built.accents.size() == 16,
              "80-pixel spacing creates fourteen in-bounds grid lines plus the two requested cells");

        FakeContentHost particleHost;
        TemplateScene particleScene("bg_particles_motion", 30.f, particleHost, 640.f, 360.f);
        BackgroundSpec particleSpec;
        particleSpec.look = BackgroundLook::Particles;
        particleSpec.particleQuantity = 12;
        particleSpec.particleVx = 0.25f;
        particleSpec.particleColor = "#DDEEFF";
        const BackgroundComposition particles = addBackground(particleScene, particleSpec);
        check(particles.accents.size() == 12,
              "Particles quantity directly controls the authored dot count");
        check(!particles.accents.empty() &&
                      particles.accents.front()->layer().tracks.position.keys().size() == 2,
              "each particle gets a deterministic drift motion track");
        check(particleHost.lastShapeRequest().fillColor == "#DDEEFF",
              "Particles uses the caller-selected native shape color");
        check(particleScene.validate().empty(), "animated particle scene validates");
    }

    void archiveDustIsDeterministic() {
        section("archive dust is seeded by layer index");
        FakeContentHost firstHost;
        FakeContentHost secondHost;
        TemplateScene first("bg_dust_a", 30.f, firstHost, 1920.f, 1080.f);
        TemplateScene second("bg_dust_b", 30.f, secondHost, 1920.f, 1080.f);
        BackgroundSpec spec;
        spec.look = BackgroundLook::ArchiveDust;
        spec.particleCount = 18;
        const BackgroundComposition a = addBackground(first, spec);
        const BackgroundComposition b = addBackground(second, spec);
        check(a.accents.size() == 18 && b.accents.size() == 18,
              "particle count controls the exact number of dust layers");
        if (a.accents.size() == b.accents.size()) {
            for (std::size_t i = 0; i < a.accents.size(); ++i) {
                const auto& aKeys = a.accents[i]->layer().tracks.position.keys();
                const auto& bKeys = b.accents[i]->layer().tracks.position.keys();
                check(aKeys.size() == bKeys.size(), "same seed gives the same key count");
                if (aKeys.size() == bKeys.size() && !aKeys.empty()) {
                    check(std::abs(aKeys.front().value.x - bKeys.front().value.x) < 0.001f &&
                                  std::abs(aKeys.front().value.y - bKeys.front().value.y) < 0.001f,
                          "same seed gives identical dust start positions");
                    check(std::abs(aKeys.back().value.x - bKeys.back().value.x) < 0.001f &&
                                  std::abs(aKeys.back().value.y - bKeys.back().value.y) < 0.001f,
                          "same seed gives identical dust drift endpoints");
                }
            }
        }
    }

    void thePackRejectsInvalidSpecs() {
        section("background pack validates its spec");
        FakeContentHost host;
        TemplateScene scene("bg_bad", 30.f, host, 1920.f, 1080.f);

        bool threwBars = false;
        try {
            (void) addBackground(scene, BackgroundSpec{.look = BackgroundLook::LetterboxBars,
                                                       .barFraction = 0.75f});
        } catch (const std::invalid_argument&) {
            threwBars = true;
        }
        check(threwBars, "a bar fraction outside [0, 0.5) is rejected");

        bool threwDuration = false;
        try {
            (void) addBackground(scene, BackgroundSpec{.duration = 0});
        } catch (const std::invalid_argument&) {
            threwDuration = true;
        }
        check(threwDuration, "a non-positive duration is rejected");

        bool threwShortDocumentary = false;
        try {
            (void) addBackground(scene, BackgroundSpec{.look = BackgroundLook::RadarSweep,
                                                       .duration = 12});
        } catch (const std::invalid_argument&) {
            threwShortDocumentary = true;
        }
        check(threwShortDocumentary, "animated documentary looks reject windows shorter than 24 frames");

        bool threwGridSpacing = false;
        try {
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::DocumentaryGrid;
            invalid.gridSpacing = 0.f;
            (void) addBackground(scene, invalid);
        } catch (const std::invalid_argument&) {
            threwGridSpacing = true;
        }
        check(threwGridSpacing, "non-positive documentary grid spacing is rejected");

        bool threwGridNaN = false;
        try {
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::DocumentaryGrid;
            invalid.gridSpacing = std::numeric_limits<float>::quiet_NaN();
            (void) addBackground(scene, invalid);
        } catch (const std::invalid_argument&) {
            threwGridNaN = true;
        }
        check(threwGridNaN, "non-finite documentary grid spacing is rejected");

        bool threwOpacity = false;
        try {
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::RadarSweep;
            invalid.scanOpacity = 1.1f;
            (void) addBackground(scene, invalid);
        } catch (const std::invalid_argument&) {
            threwOpacity = true;
        }
        check(threwOpacity, "opacity outside [0, 1] is rejected");

        bool threwNegativeFrame = false;
        try {
            BackgroundSpec invalid;
            invalid.inFrame = -1;
            (void) addBackground(scene, invalid);
        } catch (const std::invalid_argument&) {
            threwNegativeFrame = true;
        }
        check(threwNegativeFrame, "negative start frames are rejected");

        bool threwGridBudget = false;
        try {
            TemplateScene denseScene("bg_dense", 30.f, host, 16384.f, 16384.f);
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::DocumentaryGrid;
            invalid.gridSpacing = 12.f;
            (void) addBackground(denseScene, invalid);
        } catch (const std::invalid_argument&) {
            threwGridBudget = true;
        }
        check(threwGridBudget, "extreme grid density is rejected before allocating hundreds of layers");

        bool threwGridPatternBudget = false;
        try {
            TemplateScene densePatternScene("bg_dense_pattern", 30.f, host, 640.f, 360.f);
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::GridPattern;
            invalid.gridSpacing = 12.f;
            invalid.gridSquares.resize(128, {0, 0});
            (void) addBackground(densePatternScene, invalid);
        } catch (const std::invalid_argument&) {
            threwGridPatternBudget = true;
        }
        check(threwGridPatternBudget,
              "GridPattern accounts for requested square layers before building an over-budget composition");

        bool threwMeshSpeed = false;
        try {
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::MeshGradient;
            invalid.meshSpeed = 9.f;
            (void) addBackground(scene, invalid);
        } catch (const std::invalid_argument&) {
            threwMeshSpeed = true;
        }
        check(threwMeshSpeed, "mesh-gradient speed outside its supported range is rejected");

        bool threwMeshColor = false;
        try {
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::MeshGradient;
            invalid.meshColors[0] = "not-a-color";
            (void) addBackground(scene, invalid);
        } catch (const std::invalid_argument&) {
            threwMeshColor = true;
        }
        check(threwMeshColor, "malformed mesh-gradient color is rejected");

        bool threwGridSquare = false;
        try {
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::GridPattern;
            invalid.gridSquares.push_back({-1, 0});
            (void) addBackground(scene, invalid);
        } catch (const std::invalid_argument&) {
            threwGridSquare = true;
        }
        check(threwGridSquare, "negative filled-grid coordinates are rejected");

        bool threwParticleCount = false;
        try {
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::ArchiveDust;
            invalid.particleCount = 300;
            (void) addBackground(scene, invalid);
        } catch (const std::invalid_argument&) {
            threwParticleCount = true;
        }
        check(threwParticleCount, "unbounded archive dust counts are rejected");

        bool threwParticleSize = false;
        try {
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::Particles;
            invalid.particleSize = 0.f;
            (void) addBackground(scene, invalid);
        } catch (const std::invalid_argument&) {
            threwParticleSize = true;
        }
        check(threwParticleSize, "non-positive particle size is rejected");

        bool threwDotBudget = false;
        try {
            TemplateScene denseDots("bg_dense_dots", 30.f, host, 1920.f, 1080.f);
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::DotField;
            invalid.dots.dotSpacing = 1.f;
            (void)addBackground(denseDots, invalid);
        } catch (const std::invalid_argument&) {
            threwDotBudget = true;
        }
        check(threwDotBudget, "DotField rejects spacing that would be silently changed to meet the renderer's dot cap");

        bool threwReactParticleCount = false;
        try {
            BackgroundSpec invalid;
            invalid.look = BackgroundLook::Particles;
            invalid.particleQuantity = 97;
            (void)addBackground(scene, invalid);
        } catch (const std::invalid_argument&) {
            threwReactParticleCount = true;
        }
        check(threwReactParticleCount, "React Particles enforces the 96-shape bounded budget");

    }

}// namespace

int main() {
    everyLookHasAStableId();
    everyLookBuildsAFullFrameBackground();
    documentaryLooksHaveStableLayerIdsAndFadeAcrossTheirWindow();
    radarSweepUsesAProgressiveMotionTrack();
    archiveDustIsDeterministic();
    gridPatternFillsRequestedCells();
    thePackRejectsInvalidSpecs();
    return chrononmotion_test::report();
}
