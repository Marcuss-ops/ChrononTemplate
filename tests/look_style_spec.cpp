// LookSpec / StyleSpec contract: closed look vocabulary, explicit backend
// capabilities and a strict `chronon.style.v1` reader.

#include "chronontemplate/core/LookSpec.hpp"
#include "chronontemplate/core/StyleSpec.hpp"

#include "motion_check.hpp"

#include <functional>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace chronontemplate;
using namespace chrononmotion_test;

namespace {

    bool throwsInvalid(const std::function<void()>& call) {
        try {
            call();
        } catch (const std::invalid_argument&) {
            return true;
        }
        return false;
    }

    std::string style(const std::string& id, const std::string& look, int fps) {
        return "{\"schema\":\"chronon.style.v1\",\"id\":\"" + id + "\",\"look\":\"" + look +
               "\",\"fps\":" + std::to_string(fps) + "}";
    }

}// namespace

int main() {
    chrononmotion_test::section("closed look vocabulary");

    for (const Look look : {Look::Pbr, Look::Glass, Look::Halftone, Look::Toon, Look::Pixelated}) {
        const std::string id(lookId(look));
        check(parseLook(id) == look, "every look id round-trips through parseLook");
    }
    check(throwsInvalid([] { (void) parseLook("volumetric-fog"); }),
          "an unknown look id is rejected, not approximated");

    check(lookCapabilities(Look::Glass).transmission,
          "glass requires the transmission capability");
    check(lookCapabilities(Look::Halftone).customFragmentShader,
          "halftone requires a custom fragment shader");
    check(lookCapabilities(Look::Toon).customFragmentShader,
          "toon requires a custom fragment shader");
    check(lookCapabilities(Look::Pixelated).reducedFramebuffer,
          "pixelated requires a reduced framebuffer");
    check(!lookCapabilities(Look::Pbr).transmission &&
                  !lookCapabilities(Look::Pbr).customFragmentShader &&
                  !lookCapabilities(Look::Pbr).reducedFramebuffer,
          "PBR needs no optional capability");

    LookSpec spec;
    spec.validate();
    spec.kind = Look::Glass;
    spec.intensity = 0.5f;
    spec.validate();
    check(lookFingerprint(spec) == "chronon.look.v1|glass|0.500000",
          "look fingerprints are stable and explicit");

    LookSpec bad = spec;
    bad.intensity = 1.5f;
    check(throwsInvalid([&] { bad.validate(); }), "look intensity above 1 is rejected");
    bad.intensity = -0.1f;
    check(throwsInvalid([&] { bad.validate(); }), "negative look intensity is rejected");

    chrononmotion_test::section("chronon.style.v1 reader");

    const StyleSpec glass = parseStyle(style("glass-launch", "glass", 30));
    check(glass.id == "glass-launch", "style id is preserved");
    check(glass.look.kind == Look::Glass, "style look resolves through the closed vocabulary");
    check(glass.fps == 30, "style fps is preserved");
    check(lookCapabilities(glass.look.kind).transmission,
          "the resolved style carries its backend requirement");

    std::istringstream stream(style("pbr-launch", "pbr", 24));
    const StyleSpec fromStream = readStyle(stream);
    check(fromStream.look.kind == Look::Pbr && fromStream.fps == 24,
          "readStyle consumes the same document from a stream");

    check(throwsInvalid([] { (void) parseStyle(style("x", "volumetric-fog", 30)); }),
          "an unknown look fails closed at the style boundary");
    check(throwsInvalid([] {
              (void) parseStyle("{\"schema\":\"chronon.style.v1\",\"id\":\"x\",\"look\":\"pbr\","
                                "\"fps\":30,\"unexpected\":true}");
          }),
          "an unknown style field fails closed");
    check(throwsInvalid([] {
              (void) parseStyle("{\"schema\":\"chronon.style.v2\",\"id\":\"x\",\"look\":\"pbr\",\"fps\":30}");
          }),
          "an unsupported schema version fails closed");
    check(throwsInvalid([] { (void) parseStyle(style("x", "pbr", 0)); }),
          "fps below 1 is rejected");
    check(throwsInvalid([] { (void) parseStyle(style("x", "pbr", 121)); }),
          "fps above 120 is rejected");
    check(throwsInvalid([] { (void) parseStyle(style("   ", "pbr", 30)); }),
          "a blank style id is rejected");
    check(throwsInvalid([] { (void) parseStyle("[]"); }), "a non-object document is rejected");
    check(throwsInvalid([] { (void) parseStyle("{\"schema\":\"chronon.style.v1\"}"); }),
          "missing fields are rejected");

    chrononmotion_test::section("style fingerprint");

    check(styleFingerprint(glass) == styleFingerprint(parseStyle(style("glass-launch", "glass", 30))),
          "the style fingerprint is stable across formatting");
    check(styleFingerprint(glass) != styleFingerprint(parseStyle(style("glass-launch", "glass", 24))),
          "the style fingerprint changes with fps");
    check(styleFingerprint(glass) != styleFingerprint(parseStyle(style("pbr-launch", "pbr", 30))),
          "the style fingerprint changes with the look");

    return chrononmotion_test::report();
}
