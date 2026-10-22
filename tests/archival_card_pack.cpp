// Archival cards: the four reference looks carry their graded frame styles,
// compose the expected paper/mat/photo/caption layers, keep the photo visible
// through the settled window, and reject incomplete or out-of-range specs.
#include "chronontemplate/single_images/ArchivalCardPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <array>
#include <stdexcept>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    constexpr const char* kPrimary = "assets/test/archive_portrait.png";
    constexpr const char* kSecondary = "assets/test/archive_portrait_b.png";

    ArchivalCardSpec baseSpec(const std::string& name) {
        ArchivalCardSpec spec{};
        spec.primaryAsset = kPrimary;
        spec.secondaryAsset = kSecondary;
        spec.primaryLabel = "Ada Lovelace";
        spec.secondaryLabel = "Charles Babbage";
        spec.archiveLabel = "Archivio storico, 1843";
        spec.font = "EditorialSerif";
        spec.name = name;
        return spec;
    }

    void theFourPresetsCarryTheirTreatments() {
        section("archival card presets");
        const ImageFrameStyle torn = archivalCardFrameStyle(ArchivalCardLook::TornPaperPortrait);
        checkNear(torn.saturation, 0.72f, 1e-6f, "torn paper keeps the faded grade");
        checkNear(torn.tornEdgeAmount, 7.f, 1e-6f, "torn paper carries a 7px torn edge");
        checkNear(torn.tornEdgeScale, 9.f, 1e-6f, "torn paper carries a 9px edge scale");
        check(torn.tornEdgeSeed == 42, "torn paper keeps its deterministic edge seed");
        checkNear(torn.channelSplit, 1.2f, 1e-6f, "torn paper keeps the subtle RGB split");

        const ImageFrameStyle print = archivalCardFrameStyle(ArchivalCardLook::ArchivePrint);
        checkNear(print.saturation, 0.f, 1e-6f, "archive print is black and white");
        checkNear(print.grain, 0.035f, 1e-6f, "archive print carries photographic grain");
        checkNear(print.tornEdgeAmount, 0.f, 1e-6f, "archive print uses a clean rectangular border");

        const ImageFrameStyle film = archivalCardFrameStyle(ArchivalCardLook::VintageFilmProjection);
        checkNear(film.cornerRadius, 26.f, 1e-6f, "vintage film uses the rounded projection window");
        check(film.scanlineIntensity > 0.f, "vintage film keeps analog scanlines");
        checkNear(film.saturation, 0.f, 1e-6f, "vintage film is black and white");

        const ImageFrameStyle duo = archivalCardFrameStyle(ArchivalCardLook::DoublePortraitArchive);
        check(duo.saturation > 0.f && duo.saturation < 1.f, "double portrait keeps a sepia grade");
        checkNear(duo.tornEdgeAmount, 5.f, 1e-6f, "double portrait cuts keep irregular edges");

        const auto ids = archivalCardLookIds();
        check(ids.size() == 4 &&
              ids[0] == "archival_torn_paper_portrait" &&
              ids[1] == "archival_archive_print" &&
              ids[2] == "archival_vintage_film_projection" &&
              ids[3] == "archival_double_portrait",
              "the four look ids are stable and distinct");
        check(std::string(archivalCardPackId()) == "archival_card_v1",
              "the pack id is stable");
    }

    void eachLookSubmitsItsLayers() {
        section("archival card composition");
        struct Case {
            ArchivalCardLook look;
            const char* tag;
            const char* matShape;
            bool needsSecondPhoto;
        };
        const std::array<Case, 4> cases{{
                {ArchivalCardLook::TornPaperPortrait, "torn", "torn_mat", false},
                {ArchivalCardLook::ArchivePrint, "print", "print_paper", false},
                {ArchivalCardLook::VintageFilmProjection, "film", "film_window", false},
                {ArchivalCardLook::DoublePortraitArchive, "duo", "duo_mat_a", true},
        }};

        for (const Case& item : cases) {
            FakeContentHost host;
            TemplateScene scene(std::string("archive_") + item.tag, 30.f, host, 1920.f, 1080.f);
            ArchivalCardSpec spec = baseSpec(item.tag);
            const ArchivalCardLayers layers = addArchivalCard(scene, item.look, spec);
            const auto* mat = host.findShapeRequest(item.matShape);
            check(mat != nullptr, "each look authors its paper mat");
            check(scene.validate().empty(), "each archival card validates");

            const FrameSubmission settled = scene.submit(90);
            const FrameSubmission fading = scene.submit(140);
            const BoundLayer* primary = findLayer(settled, layers.primary);
            check(primary != nullptr && primary->draws() && primary->content.isImage(),
                  "each look submits its archival photograph");
            const BoundLayer* late = findLayer(fading, layers.primary);
            if (primary && late) {
                check(primary->transform.opacity > 0.f,
                      "the photograph is visible through the settled window");
                check(late->transform.opacity < primary->transform.opacity,
                      "the photograph fades out at the end of the card");
            }
            if (item.needsSecondPhoto) {
                const BoundLayer* secondary = findLayer(settled, layers.secondary);
                check(secondary != nullptr && secondary->draws() &&
                      secondary->content.isImage(),
                      "the double portrait submits its second photograph");
                check(layers.secondary != layers.primary,
                      "the double portrait photographs are distinct layers");
                check(host.findShapeRequest("duo_mat_b") != nullptr,
                      "the double portrait cuts two independent mats");
            }
            if (layers.caption != 0) {
                const BoundLayer* caption = findLayer(settled, layers.caption);
                check(caption != nullptr && caption->draws() && caption->content.isText(),
                      "each look submits its caption layer");
            }
            const ImageRequest& lastImage = host.lastImageRequest();
            if (item.look == ArchivalCardLook::TornPaperPortrait) {
                checkNear(lastImage.tornEdgeAmount, 7.f, 1e-6f,
                          "the torn portrait keeps its torn alpha edge on the image request");
            } else if (item.look == ArchivalCardLook::ArchivePrint) {
                checkNear(lastImage.saturation, 0.f, 1e-6f,
                          "the archive print keeps saturation zero on the image request");
            } else if (item.look == ArchivalCardLook::VintageFilmProjection) {
                checkNear(lastImage.cornerRadius, 26.f, 1e-6f,
                          "the projection window keeps its rounded mask");
            } else {
                check(lastImage.tornEdgeSeed == 1940,
                      "the second double portrait keeps its own torn-edge seed");
            }
        }
    }

    void incompleteSpecsFailClosed() {
        section("archival card validation");
        int throws = 0;
        FakeContentHost host;
        TemplateScene scene("invalid", 30.f, host, 1920.f, 1080.f);

        ArchivalCardSpec noAsset = baseSpec("no_asset");
        noAsset.primaryAsset.clear();
        try {
            (void) addArchivalCard(scene, ArchivalCardLook::TornPaperPortrait, noAsset);
        } catch (const std::invalid_argument&) { ++throws; }

        ArchivalCardSpec noSecond = baseSpec("no_second");
        noSecond.secondaryAsset.clear();
        try {
            (void) addArchivalCard(scene, ArchivalCardLook::DoublePortraitArchive, noSecond);
        } catch (const std::invalid_argument&) { ++throws; }

        ArchivalCardSpec emptyWindow = baseSpec("empty_window");
        emptyWindow.durationFrames = 0;
        try {
            (void) addArchivalCard(scene, ArchivalCardLook::ArchivePrint, emptyWindow);
        } catch (const std::invalid_argument&) { ++throws; }

        ArchivalCardSpec oversized = baseSpec("oversized");
        oversized.primaryWidth = 2400.f;
        try {
            (void) addArchivalCard(scene, ArchivalCardLook::VintageFilmProjection, oversized);
        } catch (const std::invalid_argument&) { ++throws; }

        check(throws == 4, "incomplete or out-of-range archive cards fail closed");
    }

} // namespace

int main() {
    theFourPresetsCarryTheirTreatments();
    eachLookSubmitsItsLayers();
    incompleteSpecsFailClosed();
    return chrononmotion_test::report();
}
