#include "chronontemplate/map/MapPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void everyMotionHasAStableId() {
        section("map motions have stable ids");
        const std::vector<MapMotion> motions = mapMotions();
        check(motions.size() == 5, "the pack exposes five camera motions");
        for (const MapMotion motion : motions) {
            const std::string id = mapMotionId(motion);
            check(id.rfind("map_", 0) == 0, "every motion id is namespaced with map_");
        }
    }

    void everyMotionAuthorsThePlateMarkersAndCamera() {
        section("map motions author the plate, markers, title and camera");
        for (const MapMotion motion : mapMotions()) {
            FakeContentHost host;
            TemplateScene scene(std::string("map_") + mapMotionId(motion), 30.f, host,
                                1920.f, 1080.f);
            MapSpec spec;
            spec.platePath = "catalog/maps/nasa_blue_marble_august.jpg";
            spec.title = "THE ROUTE";
            spec.motion = motion;
            spec.markers = {
                    MapMarker{.label = "ROME", .position = {1180.f, 470.f}},
                    MapMarker{.label = "PARIS", .position = {760.f, 380.f}}};
            const MapComposition built = addMapMotion(scene, spec);

            check(built.plate != nullptr, "every motion authors a plate");
            check(built.markers.size() == 2, "every marker becomes a layer");
            check(built.title != nullptr, "a title authors one text layer");
            check(built.endFrame == 150, "the composition ends at its authored duration");

            const FrameSubmission start = scene.submit(0);
            const FrameSubmission middle = scene.submit(75);
            const FrameSubmission end = scene.submit(150);
            const BoundLayer* plate = findLayer(middle, built.plate->id());
            check(plate && plate->draws() && plate->content.isImage(),
                  "the plate is a bound image at the middle of the clip");
            check(start.camera && middle.camera && end.camera,
                  "every map motion submits a camera pose");

            const bool cameraMoved =
                    std::abs(start.camera->position.x - middle.camera->position.x) > 0.01f ||
                    std::abs(start.camera->position.y - middle.camera->position.y) > 0.01f ||
                    std::abs(start.camera->position.z - middle.camera->position.z) > 0.01f;
            check(cameraMoved == (motion != MapMotion::HoldStatic),
                  "only the four moving recipes move the camera");
            check(scene.validate().empty(), "every map scene validates");
        }
    }

    void thePackRejectsInvalidSpecs() {
        section("map pack validates its spec");
        FakeContentHost host;
        TemplateScene scene("map_bad", 30.f, host, 1920.f, 1080.f);

        bool threwPath = false;
        try {
            MapSpec spec;
            (void) addMapMotion(scene, spec);
        } catch (const std::invalid_argument&) {
            threwPath = true;
        }
        check(threwPath, "an empty plate path is rejected");

        bool threwMarker = false;
        try {
            MapSpec spec;
            spec.platePath = "catalog/maps/nasa_blue_marble_august.jpg";
            spec.markers = {MapMarker{.label = "X", .position = {std::nanf(""), 0.f}}};
            (void) addMapMotion(scene, spec);
        } catch (const std::invalid_argument&) {
            threwMarker = true;
        }
        check(threwMarker, "a non-finite marker position is rejected");
    }

}// namespace

int main() {
    everyMotionHasAStableId();
    everyMotionAuthorsThePlateMarkersAndCamera();
    thePackRejectsInvalidSpecs();
    return chrononmotion_test::report();
}
