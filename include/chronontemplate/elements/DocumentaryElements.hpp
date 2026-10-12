#ifndef CHRONONTEMPLATE_DOCUMENTARY_ELEMENTS_HPP
#define CHRONONTEMPLATE_DOCUMENTARY_ELEMENTS_HPP

// Graphics objects 19-24: documentary objects, photos and evidence.
// Strict visual hierarchy: one headline, one short description, few
// supporting marks. No microscopic text walls.

#include "chronontemplate/elements/ElementsCommon.hpp"

#include <string>

namespace chronontemplate::elements {

    /// 19 ArchivePhotoFrame: editorial photo mount with tag, date and
    /// source. Variants clean, paper and film.
    struct ArchivePhotoFrameSpec {
        std::string assetPath{};
        std::string tag{};
        std::string date{};
        std::string source{};
        std::string variant{"clean"};
        float width{620.f};
        float height{760.f};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"archive_photo_frame"};
    };
    [[nodiscard]] LayerHandle& addArchivePhotoFrame(TemplateScene& scene,
                                                    const ArchivePhotoFrameSpec& spec);

    /// 20 EvidenceDocumentCard: header, body blocks, quote marks, stamp.
    struct EvidenceDocumentCardSpec {
        std::string header{};
        std::string reference{};
        std::string body{};
        std::string quote{};
        std::string stamp{};
        ElementStyle style{ElementStyle::PaperLight};
        ElementMotion motion{};
        std::string name{"evidence_document_card"};
    };
    [[nodiscard]] LayerHandle& addEvidenceDocumentCard(TemplateScene& scene,
                                                       const EvidenceDocumentCardSpec& spec);

    /// 21 QuoteAttributionBlock: big quote, author, role, side rule.
    struct QuoteAttributionBlockSpec {
        std::string quote{};
        std::string author{};
        std::string role{};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"quote_attribution_block"};
    };
    [[nodiscard]] LayerHandle& addQuoteAttributionBlock(TemplateScene& scene,
                                                        const QuoteAttributionBlockSpec& spec);

    /// 22 IdentityLowerThird: name, profession, company, small decor.
    struct IdentityLowerThirdSpec {
        std::string person{};
        std::string profession{};
        std::string company{};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"identity_lower_third"};
    };
    [[nodiscard]] LayerHandle& addIdentityLowerThird(TemplateScene& scene,
                                                     const IdentityLowerThirdSpec& spec);

    /// 23 ChapterDivider: chapter number, giant title, progress rail.
    struct ChapterDividerSpec {
        std::string chapter{};
        std::string title{};
        float progress{0.5f};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"chapter_divider"};
    };
    [[nodiscard]] LayerHandle& addChapterDivider(TemplateScene& scene,
                                                 const ChapterDividerSpec& spec);

    /// 24 SourceCitationTag: persistent small source/date/material tag.
    struct SourceCitationTagSpec {
        std::string source{};
        std::string date{};
        std::string material{};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"source_citation_tag"};
    };
    [[nodiscard]] LayerHandle& addSourceCitationTag(TemplateScene& scene,
                                                    const SourceCitationTagSpec& spec);

}// namespace chronontemplate::elements

#endif//CHRONONTEMPLATE_DOCUMENTARY_ELEMENTS_HPP
