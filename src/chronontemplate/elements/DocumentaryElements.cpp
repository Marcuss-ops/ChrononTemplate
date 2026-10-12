#include "chronontemplate/elements/DocumentaryElements.hpp"

#include <algorithm>

namespace chronontemplate::elements {

    LayerHandle& addArchivePhotoFrame(TemplateScene& scene, const ArchivePhotoFrameSpec& spec) {
        require(!spec.assetPath.empty(), "addArchivePhotoFrame: an asset path is required");
        require(spec.width > 0.f && spec.height > 0.f,
                "addArchivePhotoFrame: positive dimensions are required");
        require(spec.variant == "clean" || spec.variant == "paper" || spec.variant == "film",
                "addArchivePhotoFrame: variant must be clean, paper or film");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        // Mount plate, then the photo, then editorial furniture.
        std::string mount = pal.paper;
        float radius = 6.f;
        if (spec.variant == "film") {
            mount = "#101014";
            radius = 2.f;
        }
        LayerHandle& plate = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width + 48.f, spec.height + 150.f),
                .fillColor = mount, .name = spec.name + "_mount", .cornerRadius = radius});
        plate.parent(root.id());
        plate.position(0.f, 20.f);
        plate.alive(0, 150);
        applyElementMotion(plate, spec.motion, scene.fps());
        ImageFrameStyle frame{.cornerRadius = radius};
        if (spec.variant == "film") {
            frame.grain = 0.6f;
            frame.vignette = 0.4f;
        } else if (spec.variant == "paper") {
            frame.contrast = 0.94f;
        }
        LayerHandle& photo = scene.image(ImageSpec{
                .path = spec.assetPath, .name = spec.name + "_photo", .frame = frame});
        photo.parent(root.id());
        photo.position(0.f, -35.f);
        photo.alive(0, 150);
        applyElementMotion(photo, spec.motion, scene.fps(), 1);
        int slot = 2;
        const auto line = [&](const std::string& tag, const std::string& text,
                              float size, const std::string& color, float y) {
            if (text.empty()) return;
            LayerHandle& label = addText(scene, root.id(), spec.name + "_" + tag,
                                         text, size, color, -spec.width * 0.5f, y);
            applyElementMotion(label, spec.motion, scene.fps(), slot++);
        };
        const std::string ink = spec.variant == "film" ? "#F2EFE6" : pal.ink;
        const float captionY = spec.height * 0.5f - 10.f;
        line("tag", spec.tag, 34.f, spec.variant == "film" ? pal.accent : pal.ink, captionY);
        line("date", spec.date, 30.f, spec.variant == "film" ? "#8A8F98" : pal.muted, captionY + 52.f);
        line("source", spec.source, 26.f, spec.variant == "film" ? "#8A8F98" : pal.muted,
             captionY + 96.f);
        return root;
    }

    LayerHandle& addEvidenceDocumentCard(TemplateScene& scene,
                                         const EvidenceDocumentCardSpec& spec) {
        require(!spec.header.empty(), "addEvidenceDocumentCard: a header is required");
        require(!spec.body.empty(), "addEvidenceDocumentCard: a body is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& sheet = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(820.f, 560.f),
                .fillColor = pal.paper, .name = spec.name + "_sheet", .cornerRadius = 8.f});
        sheet.parent(root.id());
        sheet.position(0.f, 0.f);
        sheet.alive(0, 150);
        applyElementMotion(sheet, spec.motion, scene.fps());
        int slot = 1;
        const auto line = [&](const std::string& tag, const std::string& text,
                              float size, const std::string& color, float y) {
            if (text.empty()) return;
            LayerHandle& label = addText(scene, root.id(), spec.name + "_" + tag,
                                         text, size, color, -360.f, y);
            applyElementMotion(label, spec.motion, scene.fps(), slot++);
        };
        line("header", spec.header, 36.f, pal.ink, -220.f);
        if (!spec.reference.empty()) line("reference", spec.reference, 28.f, pal.muted, -172.f);
        LayerHandle& rule = addBar(scene, root.id(), spec.name + "_rule",
                                   720.f, 3.f, 0.f, -130.f, pal.line, 1.f);
        applyElementMotion(rule, spec.motion, scene.fps(), slot++);
        line("body", spec.body, 32.f, pal.ink, -40.f);
        if (!spec.quote.empty()) {
            LayerHandle& bar = addBar(scene, root.id(), spec.name + "_quote_bar",
                                      8.f, 90.f, -360.f, 90.f, pal.accent, 4.f);
            applyElementMotion(bar, spec.motion, scene.fps(), slot++);
            line("quote", spec.quote, 32.f, pal.ink, 90.f);
        }
        if (!spec.stamp.empty()) {
            LayerHandle& stamp = addText(scene, root.id(), spec.name + "_stamp",
                                         spec.stamp, 44.f, "#E03B2F", 180.f, 200.f);
            applyElementMotion(stamp, spec.motion, scene.fps(), slot++);
        }
        return root;
    }

    LayerHandle& addQuoteAttributionBlock(TemplateScene& scene,
                                          const QuoteAttributionBlockSpec& spec) {
        require(!spec.quote.empty(), "addQuoteAttributionBlock: a quote is required");
        require(!spec.author.empty(), "addQuoteAttributionBlock: an author is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& rule = addBar(scene, root.id(), spec.name + "_rule",
                                   10.f, 300.f, -380.f, 0.f, pal.accent, 5.f);
        applyElementMotion(rule, spec.motion, scene.fps());
        LayerHandle& quote = addText(scene, root.id(), spec.name + "_quote",
                                     spec.quote, 64.f, pal.ink, -340.f, -60.f);
        applyElementMotion(quote, spec.motion, scene.fps(), 1);
        LayerHandle& author = addText(scene, root.id(), spec.name + "_author",
                                      spec.author, 38.f, pal.accent, -340.f, 110.f);
        applyElementMotion(author, spec.motion, scene.fps(), 2);
        if (!spec.role.empty()) {
            LayerHandle& role = addText(scene, root.id(), spec.name + "_role",
                                        spec.role, 30.f, pal.muted, -340.f, 162.f);
            applyElementMotion(role, spec.motion, scene.fps(), 3);
        }
        return root;
    }

    LayerHandle& addIdentityLowerThird(TemplateScene& scene, const IdentityLowerThirdSpec& spec) {
        require(!spec.person.empty(), "addIdentityLowerThird: a person name is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& person = addText(scene, root.id(), spec.name + "_person",
                                      spec.person, 64.f, pal.ink, -330.f, -30.f);
        applyElementMotion(person, spec.motion, scene.fps());
        LayerHandle& decor = addBar(scene, root.id(), spec.name + "_decor",
                                    90.f, 8.f, -330.f, 40.f, pal.accent, 4.f);
        applyElementMotion(decor, spec.motion, scene.fps(), 1);
        int slot = 2;
        if (!spec.profession.empty()) {
            LayerHandle& profession = addText(scene, root.id(), spec.name + "_profession",
                                              spec.profession, 34.f, pal.ink, -220.f, 40.f);
            applyElementMotion(profession, spec.motion, scene.fps(), slot++);
        }
        if (!spec.company.empty()) {
            LayerHandle& company = addText(scene, root.id(), spec.name + "_company",
                                           spec.company, 30.f, pal.muted, -330.f, 100.f);
            applyElementMotion(company, spec.motion, scene.fps(), slot++);
        }
        return root;
    }

    LayerHandle& addChapterDivider(TemplateScene& scene, const ChapterDividerSpec& spec) {
        require(!spec.chapter.empty(), "addChapterDivider: a chapter tag is required");
        require(!spec.title.empty(), "addChapterDivider: a title is required");
        require(spec.progress >= 0.f && spec.progress <= 1.f,
                "addChapterDivider: progress must sit in [0, 1]");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& chapter = addText(scene, root.id(), spec.name + "_chapter",
                                       spec.chapter, 40.f, pal.accent, 0.f, -160.f);
        applyElementMotion(chapter, spec.motion, scene.fps());
        LayerHandle& title = addText(scene, root.id(), spec.name + "_title",
                                     spec.title, 130.f, pal.ink, 0.f, -20.f);
        applyElementMotion(title, spec.motion, scene.fps(), 1);
        LayerHandle& track = addBar(scene, root.id(), spec.name + "_progress_track",
                                    560.f, 6.f, 0.f, 150.f, pal.line, 3.f);
        applyElementMotion(track, spec.motion, scene.fps(), 2);
        // Left-aligned fill; never degenerate at progress zero.
        const float fillW = std::max(560.f * spec.progress, 8.f);
        LayerHandle& fill = addBar(scene, root.id(), spec.name + "_progress_fill",
                                   fillW, 6.f, -280.f + fillW * 0.5f, 150.f,
                                   pal.accent, 3.f);
        applyElementMotion(fill, spec.motion, scene.fps(), 3);
        return root;
    }

    LayerHandle& addSourceCitationTag(TemplateScene& scene, const SourceCitationTagSpec& spec) {
        require(!spec.source.empty(), "addSourceCitationTag: a source is required");
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        // Pill plate + three short fields, readable at a glance.
        LayerHandle& pill = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(520.f, 64.f),
                .fillColor = "#101014", .name = spec.name + "_pill", .cornerRadius = 32.f});
        pill.parent(root.id());
        pill.position(0.f, 0.f);
        pill.alive(0, 150);
        applyElementMotion(pill, spec.motion, scene.fps());
        LayerHandle& dot = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(18.f, 18.f), .fillColor = "#E8B84A",
                .name = spec.name + "_dot", .cornerRadius = 9.f,
                .geometry = ShapeGeometry::Ellipse});
        dot.parent(root.id());
        dot.position(-230.f, 0.f);
        dot.alive(0, 150);
        applyElementMotion(dot, spec.motion, scene.fps(), 1);
        LayerHandle& source = addText(scene, root.id(), spec.name + "_source",
                                      spec.source, 28.f, "#F2EFE6", -200.f, -8.f);
        applyElementMotion(source, spec.motion, scene.fps(), 2);
        int slot = 3;
        if (!spec.date.empty()) {
            LayerHandle& date = addText(scene, root.id(), spec.name + "_date",
                                        spec.date, 28.f, "#8A8F98", 60.f, -8.f);
            applyElementMotion(date, spec.motion, scene.fps(), slot++);
        }
        if (!spec.material.empty()) {
            LayerHandle& material = addText(scene, root.id(), spec.name + "_material",
                                            spec.material, 28.f, "#8A8F98", 190.f, -8.f);
            applyElementMotion(material, spec.motion, scene.fps(), slot++);
        }
        return root;
    }

}// namespace chronontemplate::elements
