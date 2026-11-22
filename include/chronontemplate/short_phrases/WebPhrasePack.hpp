// ChrononTemplate — web-phrase motion pack.
//
// Twenty web-motion recipes distilled to a single text layer, plus ten
// entrance gestures in the typewriter / highlighting / geometric families.
//
// Every recipe is intentionally "virgin": it authors only the phrase's layer
// tracks and text animators. It never adds a page plate, marker, card, image,
// underline or decor layer, so the rendered MP4 is text on the runtime's
// default background and nothing else.
//
// The same definitions feed both runtime catalogs:
//   * short_phrase_motion.v1.json  (Short Phrases style picker)
//   * chronontemplate_catalog.v1.json category "web_phrase_v1"
//     (the phrase_motion_pool used by long phrases and IMPORTANT_PHRASE)
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
        std::vector<std::string> targets{"short_phrase", "caption"};
    };

    /// The 30 recipes in stable catalog order. Returned by reference; callers
    /// must not mutate it.
    [[nodiscard]] const std::vector<WebPhraseRecipe>& webPhraseRecipes();

}// namespace chronontemplate::web_phrase

#endif//CHRONONTEMPLATE_SHORT_PHRASES_WEB_PHRASE_PACK_HPP
