// Documentary title-to-snapshot recipes authored in ChrononTemplate.
#ifndef CHRONONTEMPLATE_DOCUMENTARY_SNAPSHOT_PACK_HPP
#define CHRONONTEMPLATE_DOCUMENTARY_SNAPSHOT_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// Scene-space target. The recipe owns the camera path; content layers stay put.
    struct ShotAnchor {
        chrononmotion::Vector3 center{0.f, 0.f, 0.f};
        float halfWidth{300.f};
        float halfHeight{120.f};
        chrononmotion::Quaternion orientation{};
    };

    enum class DocumentaryRecipe : std::uint8_t {
        SnapDown,
        PullbackReveal,
        PushThroughSnapshot,
        WhipToPhoto,
        FocusDrop,
        Reveal90,
        CornerTurn,
        ForegroundPhotoPass,
        PhotoStack,
        FilmstripHandoff,
        SplitDepth,
        ArchiveCraneReveal
    };

    enum class SnapshotStyle : std::uint8_t {
        Clean,
        Archive,
        Polaroid,
        Filmstrip,
        Evidence,
        Newspaper,
        BlackAndWhiteDocumentary
    };

    enum class SnapshotFit : std::uint8_t { Fit, Fill, Crop };

    struct SnapshotAsset {
        std::string path{};
        ShotAnchor anchor{};
        std::string caption{};
        SnapshotFit fit{SnapshotFit::Fit};
        ImageCrop crop{};
    };

    struct DocumentaryShot {
        ShotAnchor title{};
        std::vector<SnapshotAsset> snapshots{};
        DocumentaryRecipe recipe{DocumentaryRecipe::SnapDown};
        SnapshotStyle style{SnapshotStyle::Archive};
        int inFrame{0};
        int duration{100};
        int titleHoldFrames{45};
        int transitionFrames{8};
        float cameraDistance{1080.f};
    };

    /// Add the title and ordinary image layers, then author a camera handoff.
    /// The title and card transforms are invariant across camera recipes;
    /// ArchiveCrane settles on the full declared layout. Styling uses the
    /// existing ImageFrameStyle and ContentHost image path.
    void addDocumentarySnapshot(TemplateScene& scene, const TextSpec& title,
                                const DocumentaryShot& shot);

    [[nodiscard]] const char* documentaryRecipeId(DocumentaryRecipe recipe) noexcept;
    [[nodiscard]] const char* snapshotStyleId(SnapshotStyle style) noexcept;
    [[nodiscard]] std::vector<std::string> documentaryRecipeIds();
    [[nodiscard]] std::vector<std::string> snapshotStyleIds();

} // namespace chronontemplate

#endif // CHRONONTEMPLATE_DOCUMENTARY_SNAPSHOT_PACK_HPP
