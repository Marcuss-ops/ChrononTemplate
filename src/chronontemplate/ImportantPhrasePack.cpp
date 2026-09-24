#include "chronontemplate/ImportantPhrasePack.hpp"

namespace chronontemplate {

    ClassicPhraseStyle classicPhraseStyle() {
        // The single important-phrase look, shared by every family. Consumers
        // render it through Chronon3D's one glow effect; nothing downstream
        // restates these values.
        return ClassicPhraseStyle{};
    }

}// namespace chronontemplate
