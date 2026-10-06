#include "chronontemplate/core/ChrononMotionContract.hpp"
#include "chronontemplate/core/TemplateScene.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
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

    section("runtime handshake preserves compiled transforms and inherited state");
    chronontemplate_test::FakeContentHost host;
    TemplateScene scene("handshake_parity", 30.f, host, 640.f, 360.f);
    LayerHandle& parent = scene.group("controller");
    parent.position(340.f, 170.f).opacity(0.5f);
    LayerHandle& child = scene.text(TextSpec{.text = "PARITY", .fontSize = 48.f});
    child.parent(parent.id()).position(40.f, 30.f, 2.f).opacity(0.6f);
    child.animate(FadeIn{.inFrame = 0, .duration = 4});
    scene.camera().framing(320.f, 180.f, 900.f).orbit(0.2f, -0.1f).between(0, 12);

    constexpr std::array<int, 5> frames{0, 3, 8, 12, 3};
    std::array<std::array<float, 16>, frames.size()> expectedMatrices{};
    std::array<float, frames.size()> expectedOpacity{};
    std::array<std::uint8_t, frames.size()> expectedVisibility{};
    for (std::size_t index = 0; index < frames.size(); ++index) {
        const FrameSubmission frame = scene.submit(frames[index]);
        const BoundLayer* expected = nullptr;
        const BoundLayer* controller = nullptr;
        for (const BoundLayer& candidate : frame.layers) {
            if (candidate.transform.id == child.id()) expected = &candidate;
            if (candidate.transform.id == parent.id()) controller = &candidate;
        }
        check(expected != nullptr && controller != nullptr,
              "runtime frame includes the content and controller layer");
        if (expected == nullptr || controller == nullptr) continue;
        check(!controller->draws(), "the controller is sampled but omitted from the render handshake");
        check(expected->draws() && expected->wireContentId != 0,
              "the content-bearing layer keeps its opaque wire identity");
        check(expected->transform.visible,
              "layer visibility survives the compiled-scene boundary");
        check(std::isfinite(expected->transform.opacity) &&
                  expected->transform.opacity >= 0.f && expected->transform.opacity <= 1.f,
              "inherited world opacity is finite and clamped before ABI packing");

        const auto packed = makeChrononLayerStates(frame);
        const auto packedLayer = std::find_if(packed.begin(), packed.end(), [&](const auto& state) {
            return state.layer == child.id();
        });
        check(packedLayer != packed.end(), "content state is present in the runtime ABI records");
        if (packedLayer == packed.end()) continue;
        check(packedLayer->visible == (expected->transform.visible ? 1u : 0u),
              "ABI visibility equals the evaluated Motion visibility");
        chrononmotion_test::checkNear(packedLayer->opacity, expected->transform.opacity, 1e-6f,
                  "ABI opacity equals the evaluated inherited Motion opacity");
        check(packedLayer->layer == expected->transform.id &&
                  packedLayer->content == expected->wireContentId,
              "ABI identities exactly preserve evaluated layer and content identities");
        for (unsigned int element = 0; element < 16; ++element) {
            const float columnMajor = expected->clipFromLocal[element];
            const unsigned int row = element % 4;
            const unsigned int column = element / 4;
            const float rowMajor = packedLayer->clip_from_local[row * 4 + column];
            chrononmotion_test::checkNear(rowMajor, columnMajor, 1e-6f,
                      "ABI matrix equals the Template projection·view·world matrix after layout transpose");
            expectedMatrices[index][row * 4 + column] = rowMajor;
        }
        expectedOpacity[index] = packedLayer->opacity;
        expectedVisibility[index] = packedLayer->visible;
    }
    check(std::memcmp(expectedMatrices[1].data(), expectedMatrices[4].data(), sizeof(expectedMatrices[1])) == 0,
          "random-access revisit emits a bit-identical packed camera/world transform");
    check(expectedOpacity[1] == expectedOpacity[4] && expectedVisibility[1] == expectedVisibility[4],
          "random-access revisit emits bit-identical opacity and visibility");

    return chrononmotion_test::report();
}
