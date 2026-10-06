#ifndef CHRONONTEMPLATE_SHORT_PHRASE_RECIPE_SUPPORT_HPP
#define CHRONONTEMPLATE_SHORT_PHRASE_RECIPE_SUPPORT_HPP
#include "chronontemplate/short_phrases/ShortPhrasePack.hpp"
#include <utility>
namespace chronontemplate::modern_short_phrase::detail {
inline PhraseTrack t(const char* p, std::vector<PhraseKeyframe> k, const char* e="out_cubic") {
    return PhraseTrack{p,e,std::move(k)};
}
inline PhraseTextAnimator a(const char* unit, const char* window, std::vector<PhraseTrack> p) {
    return PhraseTextAnimator{PhraseSelector{unit,"forward",window},std::move(p)};
}
inline ShortPhraseDefinition make(const char* id,const char* title,const char* phrase,int enter,
        std::vector<PhraseTrack> tracks,std::vector<PhraseTextAnimator> animators={},float size=104.f,
        ShortPhraseExit exit=ShortPhraseExit::Reverse) {
    ShortPhraseDefinition d;
    d.id=id; d.title=title; d.phrase=phrase; d.enter=enter; d.tracks=std::move(tracks);
    d.textAnimators=std::move(animators); d.font_size=size; d.exit=exit; return d;
}
inline ShortPhraseDefinition::TextOverlay overlay(const char* id,std::string text,const char* fill,
        float x,float y,float opacity,std::vector<PhraseTrack> tracks={},
        std::vector<PhraseTextAnimator> animators={}) {
    return {id,std::move(text),fill,x,y,opacity,std::move(tracks),std::move(animators)};
}
}
#endif
