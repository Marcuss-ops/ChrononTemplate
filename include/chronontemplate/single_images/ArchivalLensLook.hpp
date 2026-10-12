// ChrononTemplate — archival optical lens presets.
//
// Barrel distortion + chromatic aberration + soft blur + grain + vignette,
// lowered to Chronon's existing primitives (LensDistortion,
// ChromaticAberration, GaussianBlur, Noise, Vignette). No new renderer, no
// new effect kind, no CornerPin: the warp is radial and grows from the
// center outwards. Header-only: the three looks are pure ImageFrameStyle
// values, so no library source changes are needed to use them.
//
// The Q&A curved black border is not a separate mask: at curvature 0.17 /
// scale 1.10 the warp uncovers the frame edges and the renderer fills them
// black, which reads as the CRT bezel.

#ifndef CHRONONTEMPLATE_ARCHIVAL_LENS_LOOK_HPP
#define CHRONONTEMPLATE_ARCHIVAL_LENS_LOOK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

namespace chronontemplate {

    /// The three taratura starting points (1920x1080): press screenshots,
    /// the curved CRT screen, and the subtle documentary treatment.
    enum class ArchivalLensLook : std::uint8_t {
        WsjReddit,
        VintageCRT,
        DocumentarySubtle
    };

    [[nodiscard]] inline ImageFrameStyle archivalLensFrameStyle(ArchivalLensLook look) {
        ImageFrameStyle frame;
        switch (look) {
            case ArchivalLensLook::WsjReddit:
                frame.lensCurvature = 0.07f;
                frame.lensScale = 1.07f;
                frame.channelSplit = 1.5f;
                frame.softBlur = 0.8f;
                frame.grain = 0.02f;
                frame.vignette = 0.18f;
                return frame;
            case ArchivalLensLook::VintageCRT:
                frame.lensCurvature = 0.17f;
                frame.lensScale = 1.10f;
                frame.channelSplit = 2.0f;
                frame.softBlur = 1.5f;
                frame.grain = 0.03f;
                frame.vignette = 0.35f;
                return frame;
            case ArchivalLensLook::DocumentarySubtle:
                frame.lensCurvature = 0.035f;
                frame.lensScale = 1.04f;
                frame.channelSplit = 0.7f;
                frame.softBlur = 0.4f;
                frame.grain = 0.01f;
                frame.vignette = 0.10f;
                return frame;
            default:
                throw std::invalid_argument("archivalLensFrameStyle: unknown look");
        }
    }

    [[nodiscard]] inline const char* archivalLensLookId(ArchivalLensLook look) noexcept {
        switch (look) {
            case ArchivalLensLook::WsjReddit: return "archival_lens_wsj_reddit";
            case ArchivalLensLook::VintageCRT: return "archival_lens_vintage_crt";
            case ArchivalLensLook::DocumentarySubtle: return "archival_lens_documentary_subtle";
            default: return "archival_lens_unknown";
        }
    }

    [[nodiscard]] inline std::vector<std::string> archivalLensLookIds() {
        return {archivalLensLookId(ArchivalLensLook::WsjReddit),
                archivalLensLookId(ArchivalLensLook::VintageCRT),
                archivalLensLookId(ArchivalLensLook::DocumentarySubtle)};
    }

    /// Reel choreography backend: three 90-frame segments, lens static,
    /// content drifting behind it. The C++ side owns the validated spec and
    /// the exact viewport math (segment, zoom, pan); the pixel warp stays
    /// renderer-side, mirroring these samplers 1:1. Single source of truth:
    /// the Python reference renderer implements no motion of its own.
    struct ArchivalLensReel {
        int segmentFrames{90};
        float articleZoomFrom{1.06f};
        float articleZoomTo{1.11f};
        float articlePanPx{22.f};
        float crtDriftPx{3.f};
        float crtDriftYPx{2.f};
        float documentaryZoomFrom{1.0f};
        float documentaryZoomTo{1.05f};
    };

    /// Segment index for `frame`, clamped to [0,2].
    [[nodiscard]] inline int reelSegmentForFrame(const ArchivalLensReel& reel, int frame) {
        if (frame < 0) return 0;
        const int total = reel.segmentFrames * 3;
        if (frame >= total) return 2;
        return frame / reel.segmentFrames;
    }

    /// Local progress 0..1 inside the segment.
    [[nodiscard]] inline float reelLocalProgress(const ArchivalLensReel& reel, int frame) {
        const int seg = reelSegmentForFrame(reel, frame);
        const int local = frame - seg * reel.segmentFrames;
        const int denom = reel.segmentFrames - 1;
        if (denom <= 0) return 0.f;
        float p = static_cast<float>(local) / static_cast<float>(denom);
        return std::clamp(p, 0.f, 1.f);
    }

    /// Content zoom at `frame` (viewport scale, lens untouched).
    [[nodiscard]] inline float reelZoom(const ArchivalLensReel& reel, int frame) {
        const float p = reelLocalProgress(reel, frame);
        switch (reelSegmentForFrame(reel, frame)) {
            case 0: return reel.articleZoomFrom +
                           (reel.articleZoomTo - reel.articleZoomFrom) * p;
            case 2: return reel.documentaryZoomFrom +
                           (reel.documentaryZoomTo - reel.documentaryZoomFrom) * p;
            default: return 1.f;
        }
    }

    /// Centerpiece shot: a medium portrait card at canvas center (never
    /// fullscreen) under a strong edge-stretching lens. The C++ side owns
    /// the frame style, the card geometry and the slow push math; the
    /// Python renderer mirrors the same literals.
    struct CenterpieceStretched {
        float cardWidth{720.f};
        float cardHeight{900.f};
        float pushFrom{1.0f};
        float pushTo{1.02f};
        int durationFrames{150};
        float edgeStretch{0.18f}; ///< extra magnification growing outward
    };

    [[nodiscard]] inline ImageFrameStyle centerpieceStretchedStyle() {
        ImageFrameStyle frame;
        frame.lensCurvature = 0.20f;
        frame.lensScale = 1.14f;
        frame.channelSplit = 2.f;
        frame.softBlur = 1.0f;
        frame.grain = 0.015f;
        frame.vignette = 0.30f;
        return frame;
    }

    inline void validateCenterpiece(const CenterpieceStretched& shot) {
        if (!std::isfinite(shot.cardWidth) || shot.cardWidth <= 0.f ||
            shot.cardWidth > 1920.f ||
            !std::isfinite(shot.cardHeight) || shot.cardHeight <= 0.f ||
            shot.cardHeight > 1080.f ||
            !std::isfinite(shot.pushFrom) || !std::isfinite(shot.pushTo) ||
            shot.pushFrom < 1.f || shot.pushTo > 1.5f || shot.pushFrom > shot.pushTo ||
            shot.durationFrames < 1 || shot.durationFrames > 900 ||
            !std::isfinite(shot.edgeStretch) || shot.edgeStretch < 0.f ||
            shot.edgeStretch > 1.f)
            throw std::invalid_argument("centerpiece: geometry, push or stretch are outside supported ranges");
    }

    /// Slow push-in scale at `frame`: linear 0..1 eased smoothstep over the
    /// shot duration. Pure function of the spec.
    [[nodiscard]] inline float centerpiecePush(const CenterpieceStretched& shot, int frame) {
        if (frame <= 0) return shot.pushFrom;
        if (frame >= shot.durationFrames - 1) return shot.pushTo;
        float p = static_cast<float>(frame) / static_cast<float>(shot.durationFrames - 1);
        p = p * p * (3.f - 2.f * p);
        return shot.pushFrom + (shot.pushTo - shot.pushFrom) * p;
    }

    /// Content pan in px at `frame`: article sweeps laterally, CRT breathes
    /// on a slow sine, documentary holds center.
    [[nodiscard]] inline float reelPanX(const ArchivalLensReel& reel, int frame) {
        const float p = reelLocalProgress(reel, frame);
        switch (reelSegmentForFrame(reel, frame)) {
            case 0: return reel.articlePanPx * p;
            case 1: return reel.crtDriftPx * std::sin(2.f * 3.14159265f * p);
            default: return 0.f;
        }
    }

    [[nodiscard]] inline float reelPanY(const ArchivalLensReel& reel, int frame) {
        const float p = reelLocalProgress(reel, frame);
        if (reelSegmentForFrame(reel, frame) == 1)
            return reel.crtDriftYPx * std::sin(4.f * 3.14159265f * p);
        return 0.f;
    }

} // namespace chronontemplate

#endif // CHRONONTEMPLATE_ARCHIVAL_LENS_LOOK_HPP
