// ChrononTemplate — the camera motion pack, implementation.
//
// Template-owned preset ids and selection metadata. Numeric recipe evaluation
// and CameraRig authoring are delegated to ChrononMotion3D.

#include "chronontemplate/camera_roll/CameraMotionPack.hpp"

#include <array>
#include <stdexcept>

namespace chronontemplate {


    namespace {

        // Template owns stable public enum IDs and editorial families. Numeric
        // recipe values are looked up from the CM3D registry by stable ID.
        struct AuthoredCameraMotionPreset {
            CameraMotionPreset preset;
            CameraMotionFamily family;
        };

        constexpr AuthoredCameraMotionPreset kAuthoredCameraMotionPresets[] = {
#define CAMERA_MOTION_PRESET(key, family) \
            {CameraMotionPreset::key, CameraMotionFamily::family},
#include "chronontemplate/camera_roll/CameraMotionPresets.def"
#undef CAMERA_MOTION_PRESET
        };

        constexpr std::size_t kCameraMotionPresetCount =
                sizeof(kAuthoredCameraMotionPresets) / sizeof(kAuthoredCameraMotionPresets[0]);

        [[nodiscard]] const AuthoredCameraMotionPreset* rosterEntry(CameraMotionPreset preset) noexcept {
            const auto ordinal = static_cast<std::size_t>(preset);
            if (ordinal >= kCameraMotionPresetCount || kAuthoredCameraMotionPresets[ordinal].preset != preset) return nullptr;
            return &kAuthoredCameraMotionPresets[ordinal];
        }

        [[nodiscard]] CameraMotionSpec specFor(const AuthoredCameraMotionPreset& row) {
            CameraMotionSpec spec;
            const auto recipes = chrononmotion::motion::camera::cameraMotionRecipeRegistry();
            const auto ordinal = static_cast<std::size_t>(row.preset);
            if (ordinal < recipes.size()) {
                static_cast<chrononmotion::motion::camera::CameraMotionRecipe&>(spec) =
                    recipes[ordinal].recipe;
                spec.id = recipes[ordinal].id.data();
            }
            spec.family = row.family;
            return spec;
        }

        [[nodiscard]] CameraMotionSpec specFor(CameraMotionPreset preset) {
            const auto* entry = rosterEntry(preset);
            return entry == nullptr ? CameraMotionSpec{} : specFor(*entry);
        }

    }// namespace

    // The canonical roster and fully-authored rows are above.


    std::vector<CameraMotionPreset> cameraMotionPresets() {
        std::vector<CameraMotionPreset> presets;
        presets.reserve(kCameraMotionPresetCount);
        for (const auto& entry : kAuthoredCameraMotionPresets) presets.push_back(entry.preset);
        return presets;
    }

    const char* cameraMotionPresetId(CameraMotionPreset preset) noexcept {
        const auto* entry = rosterEntry(preset);
        if (entry == nullptr) return nullptr;
        const auto recipes = chrononmotion::motion::camera::cameraMotionRecipeRegistry();
        const auto ordinal = static_cast<std::size_t>(preset);
        return ordinal < recipes.size() ? recipes[ordinal].id.data() : nullptr;
    }

    std::vector<std::string> cameraMotionPresetIds() {
        std::vector<std::string> ids;
        ids.reserve(kCameraMotionPresetCount);
        for (const auto& entry : kAuthoredCameraMotionPresets) {
            const char* id = cameraMotionPresetId(entry.preset);
            if (id != nullptr) ids.emplace_back(id);
        }
        return ids;
    }

    CameraMotionFamily cameraMotionFamily(CameraMotionPreset preset) {
        return specFor(preset).family;
    }

    int cameraMotionDuration(CameraMotionPreset preset) {
        return specFor(preset).durationFrames;
    }

    const CameraMotionSpec& cameraMotionSpecFor(CameraMotionPreset preset) {
        static const CameraMotionSpec kEmpty{};
        // Function-local static initialization is guaranteed thread-safe by
        // C++11. Numeric recipe rows are sourced from the CM3D registry.
        static const std::array<CameraMotionSpec, kCameraMotionPresetCount> table = [] {
            std::array<CameraMotionSpec, kCameraMotionPresetCount> rows{};
            for (std::size_t index = 0; index < kCameraMotionPresetCount; ++index) {
                rows[index] = specFor(kAuthoredCameraMotionPresets[index]);
            }
            return rows;
        }();
        const auto* entry = rosterEntry(preset);
        if (entry == nullptr) return kEmpty;
        return table[static_cast<std::size_t>(preset)];
    }

    float cameraMotionIntensityFactor(CameraMotionIntensity intensity) noexcept {
        return chrononmotion::motion::camera::intensityFactor(intensity);
    }

    float cameraMotionReferenceDistance(const CameraMotionSubject& subject, float fovDegrees,
                                        const chrononmotion::Vector2& viewport, float frameFill) {
        return chrononmotion::motion::camera::referenceDistance(subject, fovDegrees, viewport, frameFill);
    }

    chrononmotion::motion::Easing cameraMotionEasingFor(const std::string& name) {
        return chrononmotion::motion::camera::easingFor(name);
    }

    std::vector<CameraMotionPreset> cameraMotionSuggestions(CameraContentKind kind) {
        using P = CameraMotionPreset;
        switch (kind) {
            case CameraContentKind::TitleOnWhite:
                return {P::TitleSlowPush, P::TitleLateralDrift, P::TitleRiseSettle};
            case CameraContentKind::ImpactWord:
                return {P::TitleSlowPush, P::TitleRiseSettle};
            case CameraContentKind::SinglePortrait:
                return {P::PortraitArc, P::RackFocusPortrait};
            case CameraContentKind::PortraitBuildingText:
                return {P::PortraitArc, P::RackFocusPortrait};
            case CameraContentKind::ArchivePhoto:
                return {P::ArchiveReveal, P::RackFocusPortrait};
            case CameraContentKind::MapCountry:
                return {P::MapRegionPush, P::MapCountryTilt};
            case CameraContentKind::MapTwoCountries:
                return {P::MapRouteTrack, P::MapRegionPush};
            case CameraContentKind::MapRoute:
                return {P::MapRouteTrack};
            case CameraContentKind::DashboardChart:
                return {P::UiPanelPush, P::UiCardParallax};
            case CameraContentKind::PremiumUI3D:
                return {P::UiCardParallax, P::UiMicroFloat, P::Web3DProductPush,
                        P::Web3DOrbit, P::Web3DSlowDrift};
            case CameraContentKind::Web3DObject:
                return {P::Web3DProductPush, P::Web3DOrbit, P::Web3DArcLeft,
                        P::Web3DArcRight, P::Web3DRiseReveal, P::Web3DTopDown,
                        P::Web3DLateralSlide, P::Web3DDollyArc, P::Web3DCraneDown,
                        P::Web3DSlowDrift};
            case CameraContentKind::FastCut:
                return {P::WhipPanLeft, P::WhipPanRight};
            case CameraContentKind::ObjectPass:
                return {P::DollyHandoff};
            case CameraContentKind::BlurPass:
                return {P::RackFocusPortrait};
        }
        return {};
    }

    std::vector<CameraContentKind> cameraContentKinds() {
        return {CameraContentKind::TitleOnWhite, CameraContentKind::ImpactWord,
                CameraContentKind::SinglePortrait, CameraContentKind::PortraitBuildingText,
                CameraContentKind::ArchivePhoto, CameraContentKind::MapCountry,
                CameraContentKind::MapTwoCountries, CameraContentKind::MapRoute,
                CameraContentKind::DashboardChart, CameraContentKind::PremiumUI3D,
                CameraContentKind::FastCut, CameraContentKind::ObjectPass,
                CameraContentKind::BlurPass, CameraContentKind::Web3DObject};
    }

    void applyCameraMotionShot(TemplateScene& scene, CameraMotionPreset preset,
                               const CameraMotionShot& shot) {
        const CameraMotionSpec& spec = cameraMotionSpecFor(preset);
        if (spec.id == nullptr) throw std::invalid_argument("applyCameraMotionShot: unknown preset");
        chrononmotion::motion::presets::author(scene.motion(), spec.id, [&] {
            chrononmotion::motion::camera::applyRecipe(
                    scene.camera().rig(), spec, shot, scene.fps(), scene.canvas());
        });
    }

}// namespace chronontemplate
