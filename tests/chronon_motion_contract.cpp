#include "chronontemplate/ChrononMotionContract.hpp"

#include "motion_check.hpp"

#include <stdexcept>

using namespace chronontemplate;
using namespace chrononmotion::motion;
using chrononmotion_test::check;
using chrononmotion_test::section;

int main() {
    section("Chronon ABI motion contract");

    FrameSubmission submission;
    BoundLayer layer;
    layer.transform.id = 101;
    layer.transform.visible = true;
    layer.transform.opacity = 1.4f;
    layer.content = ContentRef::text("chronon", chrononmotion::Vector2(120.f, 40.f));
    layer.wireContentId = 42;
    layer.clipFromLocal[0] = 2.f;
    submission.layers.push_back(layer);

    const auto states = makeChrononLayerStates(submission);
    check(states.size() == 1, "one content layer becomes one ABI state");
    check(states[0].struct_size == sizeof(chronon_layer_state), "ABI struct size is populated");
    check(states[0].layer == 101 && states[0].content == 42, "opaque layer/content identities are preserved");
    check(states[0].opacity == 1.f, "opacity is clamped at the boundary");
    check(states[0].clip_from_local[0] == 2.f, "final clip matrix is copied without reinterpretation");

    layer.wireContentId = 0;
    submission.layers.clear();
    submission.layers.push_back(layer);
    bool rejected = false;
    try {
        (void)makeChrononLayerStates(submission);
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    check(rejected, "an unconnected content identity fails closed instead of hashing an id");

    return chrononmotion_test::report();
}
