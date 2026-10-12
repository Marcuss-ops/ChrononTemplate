#include "chronontemplate/elements/DocumentaryElements.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

using namespace chronontemplate;
using namespace chronontemplate::elements;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void submitsThrough(const char* what, TemplateScene& scene, LayerHandle& root) {
        check(findLayer(scene.submit(0), root.id()) &&
                      findLayer(scene.submit(48), root.id()) &&
                      findLayer(scene.submit(149), root.id()),
              what);
        check(scene.validate().empty(), "each documentary scene validates");
    }

    void archivePhotoFrameComposes() {
        section("19 archive photo frame");
        FakeContentHost host;
        TemplateScene scene("el_archive", 30.f, host, 1920.f, 1080.f);
        ArchivePhotoFrameSpec spec;
        spec.assetPath = "assets/test/square_bottle_test.png";
        spec.tag = "ARCHIVE NO. 018";
        spec.date = "CALIFORNIA, 1980s";
        spec.source = "AppleInsider";
        spec.variant = "paper";
        LayerHandle& root = addArchivePhotoFrame(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the frame root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 6, "mount, photo and three captions compose six layers");
        check(host.lastImageRequest().path == "assets/test/square_bottle_test.png",
              "the photo asset reaches Chronon unchanged");
        bool threw = false;
        try {
            ArchivePhotoFrameSpec bad;
            bad.assetPath = "assets/test/square_bottle_test.png";
            bad.variant = "polaroid";
            addArchivePhotoFrame(scene, bad);
        } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "an unknown frame variant fails closed");
    }

    void evidenceDocumentCardComposes() {
        section("20 evidence document card");
        FakeContentHost host;
        TemplateScene scene("el_evidence", 30.f, host, 1920.f, 1080.f);
        EvidenceDocumentCardSpec spec;
        spec.header = "EXHIBIT A";
        spec.reference = "CASE 2011-0847";
        spec.body = "The email thread confirms the meeting";
        spec.quote = "Stay hungry, stay foolish";
        spec.stamp = "SEALED";
        LayerHandle& root = addEvidenceDocumentCard(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the document root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 9, "sheet, rule, fields, bar and stamp compose nine layers");
    }

    void quoteAttributionBlockComposes() {
        section("21 quote attribution block");
        FakeContentHost host;
        TemplateScene scene("el_quote", 30.f, host, 1920.f, 1080.f);
        QuoteAttributionBlockSpec spec;
        spec.quote = "Design is how it works";
        spec.author = "Steve Jobs";
        spec.role = "Co-founder, Apple";
        LayerHandle& root = addQuoteAttributionBlock(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the quote root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 5, "rule, quote, author and role compose five layers");
    }

    void identityLowerThirdComposes() {
        section("22 identity lower third");
        FakeContentHost host;
        TemplateScene scene("el_identity", 30.f, host, 1920.f, 1080.f);
        IdentityLowerThirdSpec spec;
        spec.person = "Steve Jobs";
        spec.profession = "Co-founder";
        spec.company = "Apple Inc.";
        LayerHandle& root = addIdentityLowerThird(scene, spec);
        root.position(960.f, 860.f);
        submitsThrough("the lower third submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 5, "person, decor, profession and company compose five layers");
    }

    void chapterDividerComposes() {
        section("23 chapter divider");
        FakeContentHost host;
        TemplateScene scene("el_chapter", 30.f, host, 1920.f, 1080.f);
        ChapterDividerSpec spec;
        spec.chapter = "CHAPTER 03";
        spec.title = "THE TURNING POINT";
        spec.progress = 0.5f;
        LayerHandle& root = addChapterDivider(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the divider root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 5, "chapter, title and progress compose five layers");
        const auto* fill = host.findShapeRequest("chapter_divider_progress_fill");
        check(fill != nullptr, "the progress fill exists");
        bool threw = false;
        try {
            ChapterDividerSpec bad;
            bad.chapter = "C";
            bad.title = "T";
            bad.progress = 1.5f;
            addChapterDivider(scene, bad);
        } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "out-of-range progress fails closed");
    }

    void sourceCitationTagComposes() {
        section("24 source citation tag");
        FakeContentHost host;
        TemplateScene scene("el_source", 30.f, host, 1920.f, 1080.f);
        SourceCitationTagSpec spec;
        spec.source = "NASA Archive";
        spec.date = "1969";
        spec.material = "16mm";
        LayerHandle& root = addSourceCitationTag(scene, spec);
        root.position(300.f, 1000.f);
        submitsThrough("the citation tag submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 6, "pill, dot and three fields compose six layers");
    }

}// namespace

int main() {
    archivePhotoFrameComposes();
    evidenceDocumentCardComposes();
    quoteAttributionBlockComposes();
    identityLowerThirdComposes();
    chapterDividerComposes();
    sourceCitationTagComposes();
    return chrononmotion_test::report();
}
