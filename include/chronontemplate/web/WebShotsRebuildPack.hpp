// ChrononTemplate — Web Shots Rebuild v1 (C++ base).
//
// Port nativo dei 28 shot Python in tools/web_shots/ (groups A-E +
// web_shot_kit.py) come dati RenderPlan V3 puri.
// Ogni shot e' una funzione pura dello spec: nessun Pillow, nessun browser,
// nessuno screenshot caricato come asset. Chronon3D rasterizza, questo pack
// possiede composizione, layout e timing.
//
// Grammatica comune (3.0s, 30fps, 90 frame): piastra -> marker seeded
// irregolare con core e sweep smoothstep -> camera centrata con push lieve.
// I dati di marker e le traiettorie restano deterministici per shot.
// I pannelli tilted (15,16,17,20) usano warp prospettico al render; qui e'
// dichiarato come tilt statico dei layer + nota nel piano (il renderer
// applica la prospettiva), cosi' il piano resta valido senza OpenCV.
//
// Mappa shot -> Python originale:
//   A: 01 kuminga, 02 capone, 07 crt, 08 rainmaking, 09 pinto, 10 tax
//   B: 03 alexis, 04 corll, 05 economy, 06 thug, 11 acoustic_kitty
//   C: 12 sabotage, 13 foia, 14 vw, 15 cnbc tilt, 16 nbc tilt
//   D: 17 guardian tilt, 18 ftx tweet, 19 nyt crazy, 20 indictment tilt, 21 seoul
//   E: 22 ivie, 23 blackvault, 24 bigfoot, 25 pizza sauce, 26 pizza hut, 27 toi, 28 amodei
#ifndef CHRONONTEMPLATE_WEB_SHOTS_REBUILD_PACK_HPP
#define CHRONONTEMPLATE_WEB_SHOTS_REBUILD_PACK_HPP

#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace chronontemplate::web {

enum class WebShotId : unsigned char {
    KumingaEspn = 0,      // 01
    AlCaponeTitle,         // 02
    AlexisArquette,        // 03
    CorllWarehouse,       // 04
    TheyWereEconomy,      // 05
    ThugTeacherQuote,     // 06
    CrtAlcoholHeadline,   // 07
    RainmakingNyt,         // 08
    PintoHighlight,        // 09
    TaxExemptNyt,          // 10
    AcousticKitty,         // 11
    SabotageManualGlow,   // 12
    FoiaFinkelZoom,       // 13
    Vw40Times,            // 14
    CnbcSbfTilt,          // 15
    NbcSwindled8b,        // 16
    GuardianBiggestFrauds,// 17
    FtxTweetCard,         // 18
    NytLookCrazyZoom,     // 19
    IndictmentSummary,    // 20
    GuardianSeoulMissiles,// 21
    IvieFacebook,         // 22
    BlackVaultFoia,       // 23
    BigFootPizza,         // 24
    PizzaSauceCaption,    // 25
    PizzaHutPerception,   // 26
    TimesOfIndiaCoxon,    // 27
    AmodeiPaceFrontier    // 28
};

[[nodiscard]] const char* webShotName(WebShotId id);
[[nodiscard]] const char* webShotSource(WebShotId id);
[[nodiscard]] const char* webShotDescription(WebShotId id);
[[nodiscard]] std::vector<std::string> webShotAnimationModules(WebShotId id);
[[nodiscard]] std::vector<WebShotId> allWebShotIds();

struct WebShotSpec {
    WebShotId id{WebShotId::KumingaEspn};
    int durationFrames{90}; // 3.0s @30fps come i Python
    int fps{30};
    std::string outputName{}; // vuoto -> <shot>.mp4

    void validate() const;
    [[nodiscard]] std::string planName() const;
    [[nodiscard]] std::string outputStem() const;
};

/// Funzione pura: stesso input -> stessi byte JSON (RenderPlan V3 completo).
[[nodiscard]] nlohmann::json buildWebShotPlan(const WebShotSpec& spec);

} // namespace chronontemplate::web

#endif
