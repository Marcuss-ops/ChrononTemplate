#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition decryptedText() {
    using namespace detail;
    auto d = make("short_phrase_product_decrypted_text", "Decrypted Text",
                  "DECODE THE SIGNAL", 90, {}, {}, 108.f);
    d.drawMainPhrase = false;
    const std::string target = "DECODE THE SIGNAL";
    constexpr char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+?<>";
    constexpr int stages = 9;
    for (int stage = 0; stage < stages; ++stage) {
        std::string encoded = target;
        for (std::size_t i = static_cast<std::size_t>(stage); i < target.size(); ++i) {
            if (target[i] == ' ') continue;
            const std::size_t pick = (static_cast<std::size_t>(stage) * 19U + i * 31U + 7U) % (sizeof(alphabet) - 1U);
            encoded[i] = alphabet[pick];
        }
        const int start = stage * 8;
        const int peak = start + 2;
        const int finish = start + 4;
        auto frames = stage == 0
            ? std::vector<PhraseKeyframe>{{0, 0.f}, {peak, 1.f}, {finish, 0.f}, {194, 0.f}, {209, 0.f}}
            : std::vector<PhraseKeyframe>{{0, 0.f}, {start, 0.f}, {peak, 1.f}, {finish, 0.f}, {194, 0.f}, {209, 0.f}};
        d.textOverlays.push_back(overlay(("decrypt_stage_" + std::to_string(stage)).c_str(),
                                         std::move(encoded), "#35C8D9", 0.f, 0.f, 1.f,
                                         {t("opacity", std::move(frames), "linear")}));
    }
    d.textOverlays.push_back(overlay("decrypt_resolved", target, "#F7F8FA", 0.f, 0.f, 1.f,
                                      {t("opacity", {{0, 0.f}, {74, 0.f}, {76, 1.f},
                                                       {194, 1.f}, {209, 0.f}}, "linear")}));
    d.adaptation_note = "Pre-baked deterministic encoded-character stages resolve left-to-right; React hover/click/view triggers and per-frame randomness are not represented.";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
