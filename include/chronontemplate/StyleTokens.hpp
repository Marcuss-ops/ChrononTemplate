// ChrononTemplate — shared web-style design tokens.
#ifndef CHRONONTEMPLATE_STYLE_TOKENS_HPP
#define CHRONONTEMPLATE_STYLE_TOKENS_HPP

#include "chronontemplate/UiPrimitives.hpp"

#include <stdexcept>
#include <string>

namespace chronontemplate::style {

    struct Tokens {
        std::string background{"#101522"};
        std::string surface{"#1A2233"};
        std::string foreground{"#F8FAFC"};
        std::string muted{"#AAB4C6"};
        std::string accent{"#FF3045"};
        float radiusSmall{8.f};
        float radiusLarge{24.f};
        ui::Gap gapSmall{.value = 8.f};
        ui::Gap gapMedium{.value = 16.f};
        ui::Gap gapLarge{.value = 24.f};
        ui::Padding safePadding{.top = 48.f, .right = 48.f, .bottom = 48.f, .left = 48.f};
        ui::Shadow cardShadow{.blur = 24.f, .offsetY = 8.f, .opacity = 0.28f};

        void validate() const {
            if (background.empty() || surface.empty() || foreground.empty() || muted.empty() || accent.empty()) {
                throw std::invalid_argument("Tokens: colors are required");
            }
            if (!(radiusSmall >= 0.f) || !(radiusLarge >= radiusSmall)) {
                throw std::invalid_argument("Tokens: radii must be ordered and non-negative");
            }
            gapSmall.validate();
            gapMedium.validate();
            gapLarge.validate();
            safePadding.validate();
            cardShadow.validate();
        }
    };

    inline Tokens WebLight() {
        Tokens tokens;
        tokens.background = "#F7F8FA";
        tokens.surface = "#FFFFFF";
        tokens.foreground = "#111827";
        tokens.muted = "#667085";
        tokens.accent = "#FF3045";
        return tokens;
    }

    inline Tokens WebDark() { return Tokens{}; }

    inline Tokens YouTubeBrand() {
        Tokens tokens = WebLight();
        tokens.accent = "#FF0000";
        return tokens;
    }

    inline Tokens InstagramBrand() {
        Tokens tokens = WebLight();
        tokens.accent = "#E1306C";
        return tokens;
    }

    inline Tokens BreakingNewsBrand() {
        Tokens tokens = WebDark();
        tokens.accent = "#FF3045";
        return tokens;
    }

}// namespace chronontemplate::style

#endif//CHRONONTEMPLATE_STYLE_TOKENS_HPP
