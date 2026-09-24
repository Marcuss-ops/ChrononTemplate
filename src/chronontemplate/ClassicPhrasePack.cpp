#include "chronontemplate/ClassicPhrasePack.hpp"

#include <stdexcept>
#include <utility>

namespace chronontemplate {

    namespace {

        PhraseTrack track(const std::string& property, std::vector<PhraseKeyframe> keys,
                          const std::string& easing = "out_cubic") {
            return PhraseTrack{property, easing, std::move(keys)};
        }

        /// Every Classic animation answers the same three beats over `enter`
        /// frames: start hidden, arrive, hold the resting value. The emitter
        /// synthesises the exit, so the definitions never author one.
        PhraseTrack fadeIn(int enter, int over) {
            return track("opacity", {{0, 0.f}, {over, 1.f}, {enter, 1.f}}, "linear");
        }

    }// namespace

    const char* name(ClassicPhraseAnimation animation) {
        switch (animation) {
            case ClassicPhraseAnimation::Fade: return "classic_fade";
            case ClassicPhraseAnimation::Rise: return "classic_rise";
            case ClassicPhraseAnimation::Drop: return "classic_drop";
            case ClassicPhraseAnimation::SlideFromLeft: return "classic_slide_from_left";
            case ClassicPhraseAnimation::SlideFromRight: return "classic_slide_from_right";
            case ClassicPhraseAnimation::ScalePop: return "classic_scale_pop";
            case ClassicPhraseAnimation::ZoomSettle: return "classic_zoom_settle";
            case ClassicPhraseAnimation::Typewriter: return "classic_typewriter";
            case ClassicPhraseAnimation::GlyphLift: return "classic_glyph_lift";
            case ClassicPhraseAnimation::GlyphTrackingIn: return "classic_glyph_tracking_in";
            case ClassicPhraseAnimation::TrackingTighten: return "classic_tracking_tighten";
            case ClassicPhraseAnimation::BlurFocus: return "classic_blur_focus";
            case ClassicPhraseAnimation::WordEmphasis: return "classic_word_emphasis";
            case ClassicPhraseAnimation::WordScaleIn: return "classic_word_scale_in";
        }
        throw std::invalid_argument("chronontemplate::name: unknown classic phrase animation");
    }

    std::vector<ClassicPhraseAnimation> classicPhraseAnimations() {
        return {ClassicPhraseAnimation::Fade,
                ClassicPhraseAnimation::Rise,
                ClassicPhraseAnimation::Drop,
                ClassicPhraseAnimation::SlideFromLeft,
                ClassicPhraseAnimation::SlideFromRight,
                ClassicPhraseAnimation::ScalePop,
                ClassicPhraseAnimation::ZoomSettle,
                ClassicPhraseAnimation::Typewriter,
                ClassicPhraseAnimation::GlyphLift,
                ClassicPhraseAnimation::GlyphTrackingIn,
                ClassicPhraseAnimation::TrackingTighten,
                ClassicPhraseAnimation::BlurFocus,
                ClassicPhraseAnimation::WordEmphasis,
                ClassicPhraseAnimation::WordScaleIn};
    }

    PhraseAnimationDefinition definition(ClassicPhraseAnimation animation) {
        // Local-time entrance keyframes (frames at the pack's 30 fps), authored
        // per animation. Layer tracks move the phrase as one piece; text
        // animators reveal it through its units the way Chronon3D owns them.
        constexpr int enter = 60;// 2 s entrance @ 30 fps
        switch (animation) {
            // ── Layer entrances: the phrase moves as one piece ──────────────
            case ClassicPhraseAnimation::Fade:
                return {"classic_fade", "Fade",
                        "OGNI DETTAGLIO CONTA", enter,
                        {fadeIn(enter, 55)},
                        {}};
            case ClassicPhraseAnimation::Rise:
                return {"classic_rise", "Rise",
                        "QUESTO CAMBIA TUTTO", enter,
                        {track("position_y", {{0, 60.f}, {enter, 0.f}}),
                         track("scale", {{0, 0.96f}, {enter, 1.f}}),
                         fadeIn(enter, 24)},
                        {}};
            case ClassicPhraseAnimation::Drop:
                return {"classic_drop", "Drop",
                        "LA STORIA INIZIA QUI", enter,
                        {track("position_y", {{0, -60.f}, {enter, 0.f}}),
                         fadeIn(enter, 24)},
                        {}};
            case ClassicPhraseAnimation::SlideFromLeft:
                return {"classic_slide_from_left", "Slide From Left",
                        "UN PASSO AVANTI", enter,
                        {track("position_x", {{0, -260.f}, {enter, 0.f}}),
                         fadeIn(enter, 22)},
                        {}};
            case ClassicPhraseAnimation::SlideFromRight:
                return {"classic_slide_from_right", "Slide From Right",
                        "IL FUTURO È QUI", enter,
                        {track("position_x", {{0, 260.f}, {enter, 0.f}}),
                         fadeIn(enter, 22)},
                        {}};
            case ClassicPhraseAnimation::ScalePop:
                return {"classic_scale_pop", "Scale Pop",
                        "FORZA E CORAGGIO", enter,
                        {track("scale", {{0, 0.8f}, {36, 1.04f}, {enter, 1.f}}, "out_back"),
                         fadeIn(enter, 20)},
                        {}};
            case ClassicPhraseAnimation::ZoomSettle:
                return {"classic_zoom_settle", "Zoom Settle",
                        "ORA O MAI PIÙ", enter,
                        {track("scale", {{0, 1.12f}, {enter, 1.f}}),
                         fadeIn(enter, 22)},
                        {}};

            // ── Glyph staging: the staggered windows carry the ramp ─────────
            // The GPU lane samples properties per run, so a "reveal" animator
            // holds its property at the hidden value and lets the window edge
            // do the per-glyph ramp; a "band" animator sweeps a narrow window
            // so the held value pulses through the run. The properties settle
            // the moment the window completes or closes.
            case ClassicPhraseAnimation::Typewriter:
                // Reveal frontier + opacity held at 0: glyphs flip visible one
                // by one as the edge passes — the true typewriter.
                return {"classic_typewriter", "Typewriter",
                        "PAROLA DOPO PAROLA", enter,
                        {},
                        {{PhraseSelector{"glyph", "forward", "reveal"},
                          {track("opacity", {{0, 0.f}, {enter, 0.f}}, "linear")}}}};
            case ClassicPhraseAnimation::GlyphLift:
                // A band of lift travels through the run: each glyph rises and
                // settles as the pulse crosses it.
                return {"classic_glyph_lift", "Glyph Lift",
                        "OGNI LETTERA SALE", enter,
                        {},
                        {{PhraseSelector{"glyph", "forward", "band"},
                          {track("position_y", {{0, 0.f}, {12, -34.f}, {enter + 10, -34.f},
                                                {enter + 18, 0.f}},
                                 "in_out_sine")}}}};
            case ClassicPhraseAnimation::GlyphTrackingIn:
                // Reveal frontier + tracking held open: the tail keeps its
                // wide spacing and slides into place glyph by glyph.
                return {"classic_glyph_tracking_in", "Glyph Tracking In",
                        "AVANTI", enter,
                        {},
                        {{PhraseSelector{"glyph", "forward", "reveal"},
                          {track("tracking", {{0, 34.f}, {enter, 34.f}}, "linear")}}}};

            // ── Whole-run focus: one static window over every glyph ─────────
            case ClassicPhraseAnimation::TrackingTighten:
                return {"classic_tracking_tighten", "Tracking Tighten",
                        "LO SPAZIO TRA LE PAROLE", enter,
                        {},
                        {{PhraseSelector{"glyph", "forward", "full"},
                          {track("tracking", {{0, 22.f}, {enter, 0.f}}),
                           track("opacity", {{0, 0.f}, {24, 1.f}, {enter, 1.f}}, "linear")}}}};
            case ClassicPhraseAnimation::BlurFocus:
                return {"classic_blur_focus", "Blur Focus",
                        "METTI A FUOCO L'IDEA", enter,
                        {},
                        {{PhraseSelector{"glyph", "forward", "full"},
                          {track("blur", {{0, 18.f}, {enter, 0.f}}),
                           track("opacity", {{0, 0.f}, {24, 1.f}, {enter, 1.f}}, "linear")}}}};

            // ── Full-run word emphasis (the run-level GPU profile) ──────────
            // The run-level contract keys on a single-word run, so these two
            // showcase one strong word each.
            case ClassicPhraseAnimation::WordEmphasis:
                return {"classic_word_emphasis", "Word Emphasis",
                        "IMPATTO", enter,
                        {},
                        {{PhraseSelector{"word", "forward", "full"},
                          {track("position_y", {{0, 24.f}, {enter, 0.f}}),
                           fadeIn(enter, 24)}}}};
            case ClassicPhraseAnimation::WordScaleIn:
                return {"classic_word_scale_in", "Word Scale In",
                        "FUTURO", enter,
                        {},
                        {{PhraseSelector{"word", "forward", "full"},
                          {track("scale", {{0, 0.9f}, {enter, 1.f}}),
                           fadeIn(enter, 24)}}}};
        }
        throw std::invalid_argument("chronontemplate::definition: unknown classic phrase animation");
    }

}// namespace chronontemplate
