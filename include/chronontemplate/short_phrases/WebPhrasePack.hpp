// ChrononTemplate — web-phrase motion pack.
//
// Twenty web layer-motion presets projected from ChrononTemplate's native
// `web` and `web_rect_v1` families, plus ten entrance gestures in the
// typewriter / highlighting / geometric families.
//
// Every recipe is intentionally "virgin": it authors only the phrase's layer
// tracks and text animators. It never adds a page plate, marker, card, image,
// underline or decor layer, so the rendered MP4 is text on the runtime's
// default background and nothing else. The web recipes copy the source layer
// tracks verbatim (retimed to the phrase entrance); AdaptationNote names the
// source motion so the projection stays auditable.
//
// The same definitions feed both runtime catalogs:
//   * short_phrase_motion.v1.json  (Short Phrases style picker)
//   * chronontemplate_catalog.v1.json category "web_phrase_v1"
//     (the phrase_motion_pool used by long phrases and IMPORTANT_PHRASE)
//
// Every recipe declares both `short_phrase` and `important_phrase`: the same
// text-only entrance is valid for short copy and for long/IMPORTANT_PHRASE
// copy, so both pickers must offer it. The typewriter short/long families stay
// split because each declares only its own lane.
#ifndef CHRONONTEMPLATE_SHORT_PHRASES_WEB_PHRASE_PACK_HPP
#define CHRONONTEMPLATE_SHORT_PHRASES_WEB_PHRASE_PACK_HPP

#include "chronontemplate/short_phrases/ShortPhrasePack.hpp"

#include <string>
#include <vector>

namespace chronontemplate::web_phrase {

    /// One text-only web recipe plus the catalog metadata the two emitters need.
    struct WebPhraseRecipe {
        ShortPhraseDefinition definition{};
        std::string family{"web"};
        std::string subcategory{"web"};
        // `important_phrase` is the long-phrase picker target. Declaring both
        // targets is the explicit opt-in for a recipe shared by both lanes.
        std::vector<std::string> targets{"short_phrase", "caption", "important_phrase"};
    };

    /// The 30 recipes in stable catalog order. Returned by reference; callers
    /// must not mutate it.
    [[nodiscard]] const std::vector<WebPhraseRecipe>& webPhraseRecipes();

}// namespace chronontemplate::web_phrase

#endif//CHRONONTEMPLATE_SHORT_PHRASES_WEB_PHRASE_PACK_HPP
