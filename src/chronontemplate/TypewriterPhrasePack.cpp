#include "chronontemplate/TypewriterPhrasePack.hpp"

#include <stdexcept>
#include <utility>

namespace chronontemplate {

    namespace {

        PhraseTrack track(const std::string& property, std::vector<PhraseKeyframe> keys,
                          const std::string& easing = "out_cubic") {
            return PhraseTrack{property, easing, std::move(keys)};
        }

        // ── The `_` cursor ──────────────────────────────────────────────────
        // Showcase glyphs measure ~57 px at the pack size, so a phrase of n
        // characters sweeps its cursor over n * 57 px, centred on the canvas.

        PhraseTrack cursorTrail(float half, int enter) {
            return track("position_x", {{0, -half}, {enter, half}}, "out_cubic");
        }

        /// Cursor always lit: fades in with the phrase and exits with it (the
        /// emitter returns the track to its first value across the exit).
        PhraseTrack cursorLit() {
            return track("opacity", {{0, 0.f}, {5, 1.f}, {96, 1.f}}, "linear");
        }

        /// Cursor lit until `from`, then blinking every `period` frames until
        /// `until`, always ending lit so the hold stays clean.
        PhraseTrack cursorBlink(int period, int from, int until) {
            std::vector<PhraseKeyframe> keys{{0, 0.f}, {5, 1.f}};
            if (from > 5) keys.push_back({from, 1.f});
            float value = 0.f;
            for (int frame = from + period / 2; frame < until; frame += period / 2) {
                keys.push_back({frame, value});
                value = 1.f - value;
            }
            keys.push_back({until, 1.f});
            return track("opacity", keys, "linear");
        }

        /// The canonical typed reveal: the window edge is the typing frontier
        /// and the properties hold their pre-typing state. An `opacity` held at
        /// 0 makes it true typing (hidden until typed); properties WITHOUT
        /// opacity leave the un-typed tail visible in its displaced state, so
        /// each glyph visibly settles as the edge passes.
        PhraseTextAnimator typedReveal(const std::string& window,
                                       std::vector<PhraseTrack> preTyping) {
            std::vector<PhraseTrack> properties;
            for (auto& property : preTyping) properties.push_back(std::move(property));
            return {PhraseSelector{"glyph", "forward", window}, std::move(properties)};
        }

    }// namespace

    const char* name(TypewriterPhraseAnimation animation) {
        switch (animation) {
            case TypewriterPhraseAnimation::Fade: return "typewriter_fade";
            case TypewriterPhraseAnimation::Cursor: return "typewriter_cursor";
            case TypewriterPhraseAnimation::CursorBlink: return "typewriter_cursor_blink";
            case TypewriterPhraseAnimation::CursorHold: return "typewriter_cursor_hold";
            case TypewriterPhraseAnimation::Lift: return "typewriter_lift";
            case TypewriterPhraseAnimation::SlideIn: return "typewriter_slide_in";
            case TypewriterPhraseAnimation::ScaleUp: return "typewriter_scale_up";
            case TypewriterPhraseAnimation::BlurFocus: return "typewriter_blur_focus";
            case TypewriterPhraseAnimation::Soft: return "typewriter_soft";
            case TypewriterPhraseAnimation::TrackingAssemble: return "typewriter_tracking_assemble";
            case TypewriterPhraseAnimation::Fast: return "typewriter_fast";
            case TypewriterPhraseAnimation::Slow: return "typewriter_slow";
            case TypewriterPhraseAnimation::DoubleBlink: return "typewriter_double_blink";
            case TypewriterPhraseAnimation::CursorLeads: return "typewriter_cursor_leads";
            case TypewriterPhraseAnimation::SoftLift: return "typewriter_soft_lift";
        }
        throw std::invalid_argument("chronontemplate::name: unknown typewriter phrase animation");
    }

    std::vector<TypewriterPhraseAnimation> typewriterPhraseAnimations() {
        return {TypewriterPhraseAnimation::Fade,
                TypewriterPhraseAnimation::Cursor,
                TypewriterPhraseAnimation::CursorBlink,
                TypewriterPhraseAnimation::CursorHold,
                TypewriterPhraseAnimation::Lift,
                TypewriterPhraseAnimation::SlideIn,
                TypewriterPhraseAnimation::ScaleUp,
                TypewriterPhraseAnimation::BlurFocus,
                TypewriterPhraseAnimation::Soft,
                TypewriterPhraseAnimation::TrackingAssemble,
                TypewriterPhraseAnimation::Fast,
                TypewriterPhraseAnimation::Slow,
                TypewriterPhraseAnimation::DoubleBlink,
                TypewriterPhraseAnimation::CursorLeads,
                TypewriterPhraseAnimation::SoftLift};
    }

    PhraseAnimationDefinition definition(TypewriterPhraseAnimation animation) {
        // The typing frontier is the reveal window edge. True typing holds
        // opacity at 0 (hidden until typed); the settling variants drop the
        // opacity property and hold the displacement instead, so the un-typed
        // tail visibly settles glyph by glyph. The `_` cursor trails the edge.
        constexpr int enter = 60;// 2 s entrance @ 30 fps
        const std::vector<PhraseTrack> typing{track("opacity", {{0, 0.f}, {enter, 0.f}}, "linear")};
        switch (animation) {
            case TypewriterPhraseAnimation::Fade:
                return {"typewriter_fade", "Typewriter Fade",
                        "PAROLE A VIDEO", enter,
                        {},
                        {typedReveal("reveal", typing)},
                        {}};
            case TypewriterPhraseAnimation::Cursor:
                return {"typewriter_cursor", "Typewriter Cursor",
                        "SCRIVO QUINDI SONO", enter,
                        {},
                        {typedReveal("reveal", typing)},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(530.f, enter), cursorLit()}}};
            case TypewriterPhraseAnimation::CursorBlink:
                return {"typewriter_cursor_blink", "Typewriter Cursor Blink",
                        "TIC TAC SUL VIDEO", enter,
                        {},
                        {typedReveal("reveal", typing)},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(505.f, enter), cursorBlink(12, 6, 96)}}};
            case TypewriterPhraseAnimation::CursorHold:
                return {"typewriter_cursor_hold", "Typewriter Cursor Hold",
                        "FINE DELLA RIGA", enter,
                        {},
                        {typedReveal("reveal", typing)},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(450.f, enter), cursorBlink(12, 72, 132)}}};
            case TypewriterPhraseAnimation::Lift:
                return {"typewriter_lift", "Typewriter Lift",
                        "OGNI PAROLA SALE", enter,
                        {},
                        {typedReveal("reveal",
                                     {track("position_y", {{0, -34.f}, {enter, -34.f}}, "linear")})},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(475.f, enter), cursorLit()}}};
            case TypewriterPhraseAnimation::SlideIn:
                return {"typewriter_slide_in", "Typewriter Slide In",
                        "ENTRA IN SCENA", enter,
                        {},
                        {typedReveal("reveal",
                                     {track("position_x", {{0, 60.f}, {enter, 60.f}}, "linear")})},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(420.f, enter), cursorLit()}}};
            case TypewriterPhraseAnimation::ScaleUp:
                return {"typewriter_scale_up", "Typewriter Scale Up",
                        "CRESCONO LE IDEE", enter,
                        {},
                        {typedReveal("reveal",
                                     {track("scale", {{0, 0.6f}, {enter, 0.6f}}, "linear")})},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(475.f, enter), cursorLit()}}};
            case TypewriterPhraseAnimation::BlurFocus:
                return {"typewriter_blur_focus", "Typewriter Blur Focus",
                        "A FUOCO LENTO", enter,
                        {},
                        {typedReveal("reveal",
                                     {track("blur", {{0, 14.f}, {enter, 14.f}}, "linear")})},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(390.f, enter), cursorLit()}}};
            case TypewriterPhraseAnimation::Soft:
                return {"typewriter_soft", "Typewriter Soft",
                        "MORBIDO E LENTO", enter,
                        {},
                        {typedReveal("reveal_soft", typing)},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(450.f, enter), cursorLit()}}};
            case TypewriterPhraseAnimation::TrackingAssemble:
                return {"typewriter_tracking_assemble", "Typewriter Tracking Assemble",
                        "SI COME SIAMO", enter,
                        {},
                        {typedReveal("reveal",
                                     {track("tracking", {{0, 34.f}, {enter, 34.f}}, "linear")})},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(390.f, enter), cursorLit()}}};
            case TypewriterPhraseAnimation::Fast:
                return {"typewriter_fast", "Typewriter Fast",
                        "SUBITO VELOCE", 30,
                        {},
                        {typedReveal("reveal", {track("opacity", {{0, 0.f}, {30, 0.f}}, "linear")})},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(390.f, 30), cursorLit()}}};
            case TypewriterPhraseAnimation::Slow:
                return {"typewriter_slow", "Typewriter Slow",
                        "LENTO E SICURO", 90,
                        {},
                        {typedReveal("reveal", {track("opacity", {{0, 0.f}, {90, 0.f}}, "linear")})},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(420.f, 90), cursorLit()}}};
            case TypewriterPhraseAnimation::DoubleBlink:
                return {"typewriter_double_blink", "Typewriter Double Blink",
                        "TIC TAC TIC TAC", enter,
                        {},
                        {typedReveal("reveal", typing)},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {cursorTrail(420.f, enter), cursorBlink(6, 6, 110)}}};
            case TypewriterPhraseAnimation::CursorLeads:
                return {"typewriter_cursor_leads", "Typewriter Cursor Leads",
                        "IL CURSORE GUIDA", enter,
                        {},
                        {typedReveal("reveal", typing)},
                        PhraseCursor{"_", {140.f, 360.f}, {960.f, 540.f},
                                     {track("position_x", {{0, -475.f}, {14, 475.f}}, "out_cubic"),
                                      cursorLit()}}};
            case TypewriterPhraseAnimation::SoftLift:
                return {"typewriter_soft_lift", "Typewriter Soft Lift",
                        "PIANO COME NEVE", enter,
                        {},
                        {typedReveal("reveal_soft",
                                     {track("position_y", {{0, -24.f}, {enter, -24.f}}, "linear")})},
                        {}};
        }
        throw std::invalid_argument("chronontemplate::definition: unknown typewriter phrase animation");
    }

}// namespace chronontemplate
