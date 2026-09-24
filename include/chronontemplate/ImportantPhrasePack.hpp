// ChrononTemplate — the important-phrase shared look and plan data types.
//
// RenderingGen names the editorial kind (IMPORTANT_PHRASE); this module owns
// how such a phrase LOOKS and the motion vocabulary every family animates it
// with. One file per family from here on:
//
//   ClassicPhrasePack.hpp   — the fourteen "normal" phrase animations
//   TypewriterPhrasePack.hpp— the fifteen typed animations with the `_` cursor
//
// The packs are data, not rendering: tools/emit_important_phrase_classic.cpp
// lowers the family definitions to the Chronon3D render-plan contract and
// Chronon3D shapes the run and draws the glow.
//
// Every animation stays inside Chronon3D's canonical GPU text contract (see
// can_lower_gpu_text_animation): one text animator, one selector — either a
// forward glyph window (properties opacity / position / scale / tracking /
// blur) or a full-run word emphasis (properties opacity / position / scale).
// That is what lets the whole pack render on the Vulkan lane with
// require_gpu_native instead of falling back to software text.
//
// The GPU lane samples animator properties per RUN, so unit-level staging is
// never property keyframes: it is the selector weight. Per-glyph effect is
// always `property(t) * weight(glyph, t)`, which gives the packs their
// staggered windows: `reveal` holds the property at its pre-typing value and
// sweeps the window edge as the typing frontier, `band` sweeps a narrow
// window through the run so the held value pulses unit by unit and settles
// when the band closes.

#ifndef CHRONONTEMPLATE_IMPORTANT_PHRASE_PACK_HPP
#define CHRONONTEMPLATE_IMPORTANT_PHRASE_PACK_HPP

#include <array>
#include <string>
#include <vector>

namespace chronontemplate {

    /// The important-phrase look every family shares: a white Montserrat Bold
    /// face with a *soft white* glow and a *slight black* stroke on the black
    /// canvas — the stroke keeps every letter crisp, the glow gives it
    /// presence. (The first revision haloed in black, which on the black
    /// canvas is invisible by construction.) Motion recipes animate the phrase
    /// layer; they never restyle it. The name dates from the Classic family,
    /// which introduced it.
    struct ClassicPhraseStyle {
        std::string font{"assets/fonts/Montserrat-Bold.ttf"};
        float font_size{130.f};
        std::array<float, 2> box{1700.f, 360.f};
        std::array<float, 2> position{960.f, 540.f};
        std::array<float, 4> background{0.f, 0.f, 0.f, 1.f};
        std::string fill{"#FFFFFF"};
        std::string stroke{"#000000"};
        float stroke_width{4.f};
        std::string glow{"#FFFFFF"};
        float glow_radius{30.f};
        float glow_intensity{0.4f};
    };

    [[nodiscard]] ClassicPhraseStyle classicPhraseStyle();

    // ── Motion data ─────────────────────────────────────────────────────────
    //
    // One dimension per keyframe: every property the packs animate
    // (position_x/y, scale, opacity, tracking, blur) is scalar on the plan
    // contract, so a keyframe carries one number and the emitter never has to
    // guess an arity.

    struct PhraseKeyframe {
        int frame{0};
        float value{0.f};
    };

    struct PhraseTrack {
        std::string property{};
        std::string easing{"out_cubic"};
        std::vector<PhraseKeyframe> keyframes{};
    };

    /// The text-unit window an animator applies its properties to. Because the
    /// GPU lane folds `property(t) * weight(glyph, t)`, all unit-level staging
    /// lives in the window:
    ///   "reveal"      — the window edge sweeps forward as the typing frontier
    ///                   while properties hold their pre-typing value
    ///                   (typewriter, assembly).
    ///   "reveal_soft" — the same frontier with the smooth shape, so each
    ///                   glyph ramps instead of flipping.
    ///   "band"        — a narrow window travels across the run, pulsing the
    ///                   held value through unit by unit (lift, wave).
    ///   "full"        — a static full window; properties act on the whole run
    ///                   at once (emphasis, tracking, blur).
    struct PhraseSelector {
        std::string unit{"glyph"};// glyph | word
        std::string order{"forward"};
        std::string window{"full"};// full | reveal | reveal_soft | band
    };

    struct PhraseTextAnimator {
        PhraseSelector selector{};
        std::vector<PhraseTrack> properties{};
    };

    /// The `_` underscore cursor of the Typewriter family: a second text layer
    /// that trails the typing edge (or holds and blinks after it). Its motion
    /// lives on the layer tracks — `position_x` for the sweep, `opacity` for
    /// the blink — the same plan contract the phrase layer uses.
    struct PhraseCursor {
        std::string text{"_"};
        std::array<float, 2> box{140.f, 360.f};
        std::array<float, 2> position{960.f, 540.f};
        std::vector<PhraseTrack> tracks{};
    };

    /// One animation of any family: entrance keyframes in `enter` frames of
    /// local time (60 — a two-second entrance at the pack fps — so the motion
    /// and the glow read on camera), on the layer and/or on text units. The
    /// emitter holds the resting value and synthesises the exit. A non-empty
    /// `cursor` adds the underscore layer the Typewriter family types with.
    struct PhraseAnimationDefinition {
        std::string id{};    ///< stable wire id, e.g. "classic_typewriter"
        std::string title{}; ///< human name, e.g. "Typewriter"
        std::string phrase{};///< showcase phrase rendered with the animation
        int enter{48};       ///< entrance length in frames @ the pack fps
        std::vector<PhraseTrack> tracks{};              ///< layer-level motion
        std::vector<PhraseTextAnimator> textAnimators{};///< per-unit motion
        PhraseCursor cursor{};                          ///< the `_` cursor layer
    };

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_IMPORTANT_PHRASE_PACK_HPP
