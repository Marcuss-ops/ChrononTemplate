// ChrononTemplate web.WebShotsRebuildPack — port C++ fedele dei 28 shot Python.
//
// Origine: tools/web_shots/shots_group_{a,b,c,d,e}.py + web_shot_kit.py
// Ogni shot replica back()/front()/anim() come layer RenderPlan V3:
// shape, testo, marker seeded con profilo irregolare/core e timing smoothstep.
// Vulkan culla le shape 3D quando il piano ha una camera statica: il pack
// converte quindi i layer in screen-space 2D e omette la camera. Il movimento
// resta affidato ai track dei marker, non a un push ottico.
// Nessun Pillow, nessun browser, nessuno screenshot caricato.
// Gli helper arrivano da chronontemplate/web/WebShotJson.hpp (JSON puro).
#include "chronontemplate/web/WebShotsRebuildPack.hpp"
#include "chronontemplate/web/WebShotJson.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

namespace chronontemplate::web {

using shot::Json;

namespace {

using namespace shot;

// The native 3D text baseline sits below the author's top coordinate. These
// adapters place centered editorial copy at a requested visible screen Y.
float centeredTextTop(float screenTop, float size) {
    return screenTop - 0.375f * size;
}
float centeredRectTop(float screenTop, float height) {
    (void)height;
    return screenTop - 12.f;
}

Json staticHighlightRect(const std::string& id, float left, float top,
        float width, float height, const std::string& color, float alpha, int duration) {
    Json marker = rect(id,left,top,width,height,color,alpha,Json::array(),duration);
    marker.erase("_native_marker_core_alpha");
    marker["_v4_highlight"] = true;
    return marker;
}

[[noreturn]] void fail(const std::string& m) { throw std::invalid_argument("WebShotSpec: " + m); }

// Camera move per-shot: faithful port of each Python Shot's cam_from/cam_to
// (tools/web_shots/shots_group_*.py). The reference stills are rendered at
// still_t=1.0 with apply_camera() applied, so the GPU pack must reproduce the
// same (zoom, cx, cy) envelope frame by frame to land on the same composition.
// renderPlan() bakes this envelope into the layer tracks: the plan camera is
// inert for screen-space layers.
using CameraMove = std::array<double, 6>;
CameraMove cameraMove(WebShotId id) {
    switch (id) {
    case WebShotId::KumingaEspn:           return {1.02,.50,.50, 1.07,.47,.46};
    case WebShotId::AlCaponeTitle:         return {1.05,.52,.42, 1.00,.50,.50};
    case WebShotId::AlexisArquette:        return {1.00,.50,.50, 1.05,.52,.55};
    case WebShotId::CorllWarehouse:        return {1.02,.50,.50, 1.07,.46,.48};
    case WebShotId::TheyWereEconomy:       return {1.00,.50,.50, 1.06,.50,.50};
    case WebShotId::ThugTeacherQuote:      return {1.02,.50,.50, 1.06,.53,.52};
    case WebShotId::CrtAlcoholHeadline:    return {1.00,.50,.50, 1.045,.50,.42};
    case WebShotId::RainmakingNyt:         return {1.02,.50,.50, 1.00,.50,.52};
    case WebShotId::PintoHighlight:        return {1.00,.50,.50, 1.05,.52,.50};
    case WebShotId::TaxExemptNyt:          return {1.00,.50,.50, 1.00,.50,.50};
    case WebShotId::AcousticKitty:         return {1.05,.52,.50, 1.00,.50,.50};
    case WebShotId::SabotageManualGlow:    return {1.08,.38,.50, 1.02,.55,.50};
    case WebShotId::FoiaFinkelZoom:        return {1.00,.50,.50, 1.00,.50,.50};
    case WebShotId::Vw40Times:             return {1.00,.50,.50, 1.00,.50,.50};
    case WebShotId::CnbcSbfTilt:           return {1.00,.50,.50, 1.035,.50,.50};
    case WebShotId::NbcSwindled8b:         return {1.01,.50,.50, 1.05,.51,.48};
    case WebShotId::GuardianBiggestFrauds: return {1.01,.50,.50, 1.05,.48,.52};
    case WebShotId::FtxTweetCard:          return {1.02,.50,.52, 1.06,.50,.48};
    case WebShotId::NytLookCrazyZoom:      return {1.03,.50,.50, 1.09,.47,.51};
    case WebShotId::IndictmentSummary:     return {1.00,.50,.50, 1.04,.52,.47};
    case WebShotId::GuardianSeoulMissiles: return {1.00,.50,.50, 1.04,.51,.49};
    case WebShotId::IvieFacebook:          return {1.02,.50,.50, 1.07,.48,.52};
    case WebShotId::BlackVaultFoia:        return {1.03,.50,.50, 1.08,.47,.51};
    case WebShotId::BigFootPizza:          return {1.02,.50,.52, 1.06,.52,.50};
    case WebShotId::PizzaSauceCaption:     return {1.00,.50,.50, 1.05,.50,.50};
    case WebShotId::PizzaHutPerception:    return {1.02,.50,.50, 1.07,.48,.52};
    case WebShotId::TimesOfIndiaCoxon:     return {1.00,.50,.50, 1.045,.50,.48};
    case WebShotId::AmodeiPaceFrontier:    return {1.00,.50,.50, 1.04,.51,.49};
    }
    return {1.00,.50,.50, 1.035,.50,.50};
}

// ---- builders completi (nessuna eccezione) ----
void buildLayers(WebShotId id, Json& L, int D) {
    int b10 = D/9, s35 = D*4/9;
    switch (id) {
    // ============ GROUP A ============
    case WebShotId::KumingaEspn: {
        Json bg = rect("desk",0,0,1920,1080,"#15161A",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 7, 0.24f); L.push_back(std::move(bg));
        L.push_back(rect("paper",238,46,1468,1030,"#F4F2EE",1.f,Json::array(),D));
        L.push_back(rect("paper_edge",238,46,1470,18,"#FFFFFF",0.55f,Json::array(),D));
        L.push_back(textLayer("h1","Sources: Jonathan Kuminga",320,108,47,kBold,"#202124",D,0,0));
        L.push_back(textLayer("h2","demanding trade away from Warriors",320,172,47,kBold,"#202124",D));
        L.push_back(textLayer("by","Anthony Slater and Shams Charania",320,252,18,kMed,"#5F6368",D,0,1));
        L.push_back(textLayer("date","Jan 15, 2026, 08:58 PM",320,282,15,kRegular,"#80868B",D));
        L.push_back(textLayer("share","⬆ Share",320,330,19,kMed,"#3C4043",D));
        L.push_back(textLayer("like","♡ Like",490,330,19,kMed,"#3C4043",D));
        L.push_back(textLayer("react","❤️😭😢  4.0K",1345,330,17,kRegular,"#5F6368",D));
        L.push_back(rect("rule1",320,382,1300,2,"#DADCE0",1.f,Json::array(),D));
        L.push_back(textLayer("p1","SAN FRANCISCO -- On the first day he became eligible to be moved,",320,418,22,kRegular,"#202124",D));
        L.push_back(textLayer("p2a","fifth-year forward ",320,458,22,kRegular,"#202124",D));
        L.push_back(textLayer("p2b","Jonathan Kuminga",517,458,22,kRegular,"#1A73E8",D));
        L.push_back(textLayer("p2c"," demanded a trade away from the",720,458,22,kRegular,"#202124",D));
        L.push_back(textLayer("p3a","Golden State Warriors",320,498,22,kRegular,"#1A73E8",D));
        L.push_back(textLayer("p3b",", league sources told ESPN.",556,498,22,kRegular,"#202124",D));
        L.push_back(textLayer("p3","Kuminga could not be traded until Thursday, according to the terms",320,578,22,kRegular,"#202124",D));
        L.push_back(textLayer("p4","of the contract he signed this summer. The trade deadline is Feb. 5.",320,618,22,kRegular,"#202124",D));
        L.push_back(textLayer("p5","Kuminga's roller-coaster tenure with the Warriors is perhaps at its",320,668,22,kRegular,"#202124",D));
        L.push_back(textLayer("p6","lowest point. He started the first 12 games of the season -- with coach",320,708,22,kRegular,"#202124",D));
        L.push_back(textLayer("p7","Steve Kerr calling him a secure starter following a hot start -- but a",320,748,22,kRegular,"#202124",D));
        L.push_back(textLayer("p8","patch of struggles led to a demotion, landing poorly with the 23-year-old.",320,788,22,kRegular,"#202124",D));
        L.push_back(rect("picks",1050,812,570,260,"#FFFFFF",0.9f,Json::array(),D));
        L.push_back(textLayer("picks_h","EDITOR'S PICKS",1080,836,14,kBold,"#5F6368",D,0,-1,1.f,"la",1.2f));
        L.push_back(rect("pick_img1",1080,872,82,62,"#C9D1D9",1.f,Json::array(),D));
        L.push_back(textLayer("pick_t1","NBA trade buzz: All the moves that",1180,876,16,kMed,"#1A73E8",D));
        L.push_back(textLayer("pick_t1b","did and didn't happen on deadline day",1180,900,16,kMed,"#1A73E8",D));
        L.push_back(textLayer("pick_s1","ESPN",1180,930,13,kRegular,"#80868B",D));
        L.push_back(rect("pick_img2",1080,962,82,62,"#C9D1D9",1.f,Json::array(),D));
        L.push_back(textLayer("pick_t2","Six NBA trade proposals: How the",1180,966,16,kMed,"#1A73E8",D));
        L.push_back(textLayer("pick_t2b","Lakers, Bucks, Warriors and others",1180,990,16,kMed,"#1A73E8",D));
        break; }
    case WebShotId::AlCaponeTitle: {
        Json bg = rect("bg",0,0,1920,1080,"#0B0B0C",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.016f, 9, 0.34f); L.push_back(std::move(bg));
        // Full-canvas source images make Vulkan refuse the CPU fallback at frame 1.
        // A 1 px inset keeps the same composition and lets the encoder read the surface.
        L.push_back(image("capone","ChrononTemplate/assets/archival_refs_v2/al_capone_trio_source.png",1,1,1918,1078,D));
        L.push_back(rect("dim",0,0,1920,1080,"#08080A",0.30f,Json::array(),D));
        L.push_back(rect("grad_top",0,0,1920,360,"#08080A",0.55f,Json::array(),D));
        L.push_back(rect("grad_bot",0,620,1920,460,"#08080A",0.85f,Json::array(),D));
        L.push_back(textLayer("title","THE BRUTAL RISE AND FALL OF AL CAPONE",960,442,54,kOswaldBold,"#F2F2F0",D,0,0,1.f,"ma"));
        L.push_back(rect("rule",500,548,920,2,"#E8E5DE",0.85f,Json::array(),D));
        Json sub = textLayer("sub","AMERICAN HISTORY'S KINGPIN OF CRIME",960,584,30,kOswaldMed,"#E8E5DE",D,0,1,1.f,"ma",2.0f);
        L.push_back(std::move(sub));
        break; }
    case WebShotId::CrtAlcoholHeadline: {
        Json bg = rect("bg",0,0,1920,1080,"#080A0C",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.014f, 1984, 0.26f); L.push_back(std::move(bg));
        L.push_back(image("archival","ChrononTemplate/assets/archival_refs_v2/al_capone_trio_source.png",232,823,1440,257,D));
        L.push_back(rect("arch_dim",232,823,1440,257,"#080A0C",0.20f,Json::array(),D));
        const char* face = "ChrononTemplate/assets/fonts/PlayfairDisplay-Bold.ttf";
        // chroma fringe: yellow/cyan copies + main (come DocumentaryReferenceStills)
        L.push_back(textLayer("h1_y","GOVERNMENT TO DOUBLE",-140,-23,135,face,"#D5D000",D,0,-1,0.62f));
        L.push_back(textLayer("h1_c","GOVERNMENT TO DOUBLE",-130,-21,135,face,"#67B9D4",D,0,-1,0.42f));
        L.push_back(textLayer("h1","GOVERNMENT TO DOUBLE",-135,-22,135,face,"#DDE4E8",D));
        L.push_back(textLayer("h2_y","ALCOHOL POISON CONTENT",-68,135,135,face,"#D5D000",D,0,-1,0.62f));
        L.push_back(textLayer("h2_c","ALCOHOL POISON CONTENT",-58,137,135,face,"#67B9D4",D,0,-1,0.42f));
        L.push_back(textLayer("h2","ALCOHOL POISON CONTENT",-63,136,135,face,"#DDE4E8",D));
        L.push_back(textLayer("h3_y","AND ALSO ADD BENZINE",9,283,135,face,"#D5D000",D,0,-1,0.62f));
        L.push_back(textLayer("h3_c","AND ALSO ADD BENZINE",19,285,135,face,"#67B9D4",D,0,-1,0.42f));
        L.push_back(textLayer("h3","AND ALSO ADD BENZINE",14,284,135,face,"#DDE4E8",D));
        L.push_back(rect("rule",420,542,335,3,"#AEB7B3",0.62f,Json::array(),D));
        // per-letter reveal del reference (13 lettere riga1 + A di riga2): le box
        // adiacenti si sovrappongono (gx-4/gw+8), quindi allo still finale sono due
        // bande continue + la box della A; reveal sfalsato 13..48..58 come Python.
        L.push_back(modules::TextHighlight::layer("hl_word1", -139, -10, 981, 118, "#C9DC28", 0.85f, 13, 35, D));
        L.push_back(modules::TextHighlight::layer("hl_word2", 865, -10, 205, 118, "#C9DC28", 0.85f, 48, 10, D));
        L.push_back(modules::TextHighlight::layer("hl_la", -67, 148, 98, 118, "#C9DC28", 0.85f, 58, 3, D));
        L.push_back(textLayer("sub","SMELL WARNS DRINKERS",96,574,82,kOswald,"#DDE4E8",D,0,1));
        L.push_back(rect("track",910,535,4,205,"#8ED8E9",0.8f,Json::array(),D));
        break; }
    case WebShotId::RainmakingNyt: {
        Json bg = rect("paper",0,0,1920,1080,"#E9E8E6",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 912, 0.16f); L.push_back(std::move(bg));
        const float h1x = 244.f, h1y = 208.f, h1s = 95.f;
        const float h2x = 244.f, h2y = 308.f, h2s = 97.f;
        const float w1 = measuredTextWidth("Rainmaking Is Used As Weapon", h1s, kSerifBlkIt) + 16.f;
        const float w2 = measuredTextWidth("by U.S.", h2s, kSerifBlkIt) + 16.f;
        L.push_back(modules::TextHighlight::layer("m1", h1x, h1y + 6.f, w1, 101.f, "#E6E300", 0.97f, b10, s35, D));
        L.push_back(modules::TextHighlight::layer("m2", h2x, h2y + 8.f, w2, 99.f, "#E6E300", 0.97f, b10+8, s35, D));
        L.push_back(modules::HeadlineComposition::line("h1","Rainmaking Is Used As Weapon",h1x,h1y,h1s,kSerifBlkIt,"#10100F",D));
        L.push_back(modules::HeadlineComposition::line("h2","by U.S.",h2x,h2y,h2s,kSerifBlkIt,"#10100F",D));
        L.push_back(rect("rule",236,477,1484,2,"#D1D0CD",0.78f,Json::array(),D));
        L.push_back(rect("pill",258,598,352,75,"#F2F1EF",0.9f,Json::array(),D));
        L.push_back(textLayer("pill_t","▣  Share full article  ",278,611,24,kSemi,"#353432",D));
        L.push_back(ellipse("c1",651,594,84,84,"#F4F3F1",0.9f,D));
        L.push_back(textLayer("c1_t","↗",672,608,35,kDeja,"#353432",D));
        L.push_back(ellipse("c2",775,594,84,84,"#F4F3F1",0.9f,D));
        L.push_back(textLayer("c2_t","▯",794,605,35,kDeja,"#353432",D));
        L.push_back(textLayer("by","By Seymour M. Hersh  Special to The New York Times",-310,774,27,kSemi,"#454340",D));
        L.push_back(textLayer("date","July 3, 1972",-570,825,24,kMed,"#716E68",D));
        L.push_back(rect("rule2",236,920,1484,1,"#D5D4D1",0.82f,Json::array(),D));
        break; }
    case WebShotId::PintoHighlight: {
        L.push_back(image("plate","ChrononTemplate/assets/images/investigative_journalist_blurred_bg.png",0,0,1920,1080,D));
        Json tone = rect("tone",0,0,1920,1080,"#80685B",0.24f,Json::array(),D);
        shot::modules::DocumentLayer::finish(tone, 0.014f, 31, 0.18f); L.push_back(std::move(tone));
        L.push_back(textLayer("pre","Records later revealed that",-600,430,48,kRegular,"#F1EEE9",D));
        L.push_back(textLayer("pre2","before",1300,430,48,kRegular,"#F1EEE9",D));
        L.push_back(modules::TextHighlight::layer("m", 133, 453, 1554, 56, "#8F7313", 0.78f, 4, 36, D));
        L.push_back(textLayer("hl","Ford secretly crash-tested the Pinto more than forty times",-5,442,55,kRegular,"#F1D923",D));
        L.push_back(textLayer("post","the fuel tank ruptured in every test performed at speeds over twenty-five miles per hour.",-169,533,47,kRegular,"#EEEAE5",D));
        break; }
    case WebShotId::TaxExemptNyt: {
        Json bg = rect("paper",0,0,1920,1080,"#E9E8E6",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.012f, 731, 0.14f);
        L.push_back(std::move(bg));
        const char* lines[]={
            "Federal authorities ruled that the church's activities were",
            "and it lost its tax-exempt status.",
            "ordered to pay those taxes. Years of",
            "appeals followed and lawsuits flooded the IRS.",
            "From 1973-1977, something was"};
        const float xs[] = {-244.f, 0.f, -454.f, -262.f, -453.f};
        const float ys[] = {180.f, 367.f, 545.f, 718.f, 887.f};
        const float ss[] = {78.f, 79.f, 77.f, 77.f, 77.f};
        const float prew = measuredTextWidth("and it ", 79.f, kPlayfair);
        const float w = measuredTextWidth("lost its tax-exempt status.", 79.f, kPlayfair) + 20.f;
        L.push_back(staticHighlightRect("m", prew - 10.f, 382.f, w, 104.f, "#E9E600", 0.97f, D));
        for(int i=0;i<5;++i)
            L.push_back(textLayer("l"+std::to_string(i), lines[i], xs[i], ys[i], ss[i], kPlayfair,
                i==1?"#11100F":"#77736F", D));
        L.push_back(rect("activities_rule", 1137, 277, 714, 4, "#8191B1", 0.76f, Json::array(), D));
        break; }
    // ============ GROUP B ============
    case WebShotId::AlexisArquette: {
        Json bg = rect("paper",0,0,1920,1080,"#FAFAF8",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 11, 0.16f); L.push_back(std::move(bg));
        L.push_back(modules::TextHighlight::layer("m", 98, 172, 385, 108, "#F2E933", 0.95f, 7, 32, D));
        L.push_back(modules::HeadlineComposition::line("h1","Alexis Arquette was planning a tell-all",100,48,88,kBlack,"#14161A",D));
        L.push_back(modules::HeadlineComposition::line("h2","memoir before she died",100,172,88,kBlack,"#14161A",D));
        L.push_back(textLayer("src","news.com.au",100,372,32,kBold,"#17181B",D,0,1));
        L.push_back(textLayer("date","13 Sep, 2016 10:30 AM",100,430,26,kRegular,"#56595E",D));
        L.push_back(ellipse("clk",520,432,28,28,"#56595E",1.f,D));
        L.push_back(ellipse("clk_in",525,437,18,18,"#FAFAF8",1.f,D));
        L.push_back(textLayer("read","3 mins to read",566,430,26,kRegular,"#56595E",D));
        L.push_back(rect("rule",100,532,1800,2,"#D7D6D3",0.9f,Json::array(),D));
        L.push_back(textLayer("save","Save",1652,655,30,kMed,"#1A1A1A",D));
        L.push_back(textLayer("sh","Sh",1868,655,30,kMed,"#1A1A1A",D));
        L.push_back(rect("banner",100,808,1820,272,"#EDE23F",1.f,Json::array(),D));
        L.push_back(rect("cc",150,850,180,150,"#D7262E",1.f,Json::array(),D));
        L.push_back(textLayer("cc1","COMEDY",168,872,26,kBold,"#FFFFFF",D));
        L.push_back(textLayer("cc2","CENTRAL",168,908,26,kBold,"#FFFFFF",D));
        L.push_back(ellipse("bud",560,880,210,110,"#1B4F9B",1.f,D));
        L.push_back(textLayer("bud1","BUD",665,908,26,kBold,"#FFFFFF",D,0,-1,1.f,"ma"));
        L.push_back(textLayer("bud2","LIGHT",665,940,26,kBold,"#FFFFFF",D,0,-1,1.f,"ma"));
        L.push_back(rect("ride",990,828,190,200,"#E86FA0",1.f,Json::array(),D));
        L.push_back(textLayer("ride1","RIDE",1085,856,30,kBold,"#7E1B66",D,0,-1,1.f,"ma"));
        L.push_back(textLayer("ride2","OF",1085,896,30,kBold,"#7E1B66",D,0,-1,1.f,"ma"));
        L.push_back(textLayer("ride3","FAVOR",1085,936,30,kBold,"#7E1B66",D,0,-1,1.f,"ma"));
        L.push_back(rect("think",1440,855,210,140,"#7B6BD6",1.f,Json::array(),D));
        L.push_back(textLayer("think1","THINK",1545,878,24,kBold,"#FFFFFF",D,0,-1,1.f,"ma"));
        L.push_back(textLayer("think2","OUTSIDE",1545,910,24,kBold,"#FFFFFF",D,0,-1,1.f,"ma"));
        L.push_back(textLayer("think3","THE SUN",1545,942,24,kBold,"#FFFFFF",D,0,-1,1.f,"ma"));
        L.push_back(ellipse("hair",820,940,330,280,"#E8C87A",1.f,D));
        L.push_back(ellipse("face",890,980,190,220,"#E7C2A0",1.f,D));
        break; }
    case WebShotId::CorllWarehouse: {
        Json bg = rect("bg",0,0,1920,1080,"#0A0A0A",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.012f, 55, 0.30f); L.push_back(std::move(bg));
        L.push_back(textLayer("p1","hardcore child pornography; films depicting children in sexual bondage. In one of these",95,10,44,kSerif,"#D8D3C9",D));
        L.push_back(textLayer("p2","letters, Smith had written that a particular film would’ve been better if the producers",95,66,44,kSerif,"#D8D3C9",D));
        L.push_back(textLayer("p3","had, “tossed in a stiff 14-year old.”",95,122,44,kSerif,"#D8D3C9",D));
        L.push_back(textLayer("pg55","55",710,116,22,kSerif,"#C9A227",D));
        float wpre = 1067.9f;
        L.push_back(textLayer("p4","A little over a year later in February 1975 another warehouse belonging to Roy",215,178,44,kSerif,"#F2EEE6",D));
        L.push_back(modules::TextHighlight::layer("m", 205, 186, wpre+10, 52, "#B3121B", 0.88f, 11, 41, D));
        L.push_back(textLayer("p5","Ames was raided and two more tons of child pornography was seized.",95,234,44,kSerif,"#D8D3C9",D));
        L.push_back(textLayer("pg56","56",1321,228,22,kSerif,"#C9A227",D));
        L.push_back(textLayer("thistime","This time,",1353,234,44,kSerif,"#D8D3C9",D));
        L.push_back(textLayer("p6","Houston PD identified 11 of Dean Corll’s victims in the pornographic materials.",95,290,44,kSerif,"#D8D3C9",D));
        L.push_back(textLayer("pg57","57",1502,284,22,kSerif,"#C9A227",D));
        L.push_back(textLayer("p7","“Juvenile officers say 11 boys who were victims in the Houston mass murders case",95,346,42,kSerifIt,"#D8D3C9",D));
        L.push_back(textLayer("p8","are pictured in sex materials seized in what police called a homosexual ring.”",95,402,42,kSerifIt,"#D8D3C9",D));
        L.push_back(textLayer("pg58","58",1482,396,22,kSerif,"#C9A227",D));
        L.push_back(rect("rule",60,470,1800,2,"#39362F",0.9f,Json::array(),D));
        const char* qs[] = {
            "\u201cJuvenile Lt. H.A Contreras said Detective John St. John and a partner met",
            "with officers Wednesday about the case of photographer Roy Clifton Ames,",
            "convicted in 1975 for using the mails to distribute obscene material. Ames",
            "was sentenced to a Springfield Mo., federal prison after photographs of 11",
            "Houston area victims of the mass murders were seized following the arrests",
            "and murder convictions of Elmer Wayne Henley Jr. and David Owen Brooks."};
        for (int i = 0; i < 6; ++i)
            L.push_back(textLayer("q"+std::to_string(i),qs[i],140,560+56*i,44,kSerif,"#C9C4BA",D));
        break; }
    case WebShotId::TheyWereEconomy: {
        Json bg = rect("bg",0,0,1920,1080,"#191413",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.014f, 12, 0.36f); L.push_back(std::move(bg));
        // woven texture: due set diagonali (semplificati come overlay scuri)
        L.push_back(rect("weave1",0,0,1920,1080,"#2B2320",0.18f,Json::array(),D));
        L.push_back(modules::TextHighlight::layer("band", 170, 430, 1600, 210, "#7E1417", 0.92f, b10, s35, D));
        L.push_back(textLayer("cap","they were the economy",960,535,148,kSerif,"#F5E7C8",D,0,0,1.f,"mm"));
        break; }
    case WebShotId::ThugTeacherQuote: {
        L.push_back(image("plate","ChrononTemplate/assets/images/investigative_journalist_blurred_bg.png",0,0,1920,1080,D));
        Json tone = rect("tone",0,0,1920,1080,"#3A1F14",0.35f,Json::array(),D);
        shot::modules::DocumentLayer::finish(tone, 0.014f, 61, 0.30f); L.push_back(std::move(tone));
        const char* lines[] = {
            "…buying the cocaine, but when I got out I",
            "did what I wanted to do – fighting, all",
            "kinds of shit.\u201d A few years later, after a",
            "dispute over Thug\u2019s classroom antics",
            "turned physical, he got kicked out of",
            "middle school. \u201cI broke my teacher\u2019s",
            "arm,\u201d he says matter-of-factly. \u201cTook his",
            "ass out. Pussy-ass n***a.\u201d He spent the",
            "next four years in a harsh",
            "juvenile detention system. \u201cSeven in the"};
        for (int i = 0; i < 10; ++i)
            L.push_back(textLayer("l"+std::to_string(i),lines[i],300,40+72*i,52,kRegular,"#F2EFEA",D,i<2?2.6f:0.f,i==0?0:-1));
        float x6 = 300 + 399.0f;
        float w6 = 508.0f;
        float w7 = 132.0f;
        L.push_back(modules::TextHighlight::layer("m1", x6-8, 40+5*72+8, w6+16, 58, "#8A6A08", 0.92f, b10, s35, D));
        L.push_back(modules::TextHighlight::layer("m2", 300-8, 40+6*72+8, w7+16, 58, "#8A6A08", 0.92f, b10, s35, D));
        L.push_back(textLayer("hl1","I broke my teacher’s",x6,40+5*72,52,kRegular,"#F5B301",D));
        L.push_back(textLayer("hl2","arm,”",300,40+6*72,52,kRegular,"#F5B301",D));
        break; }
    case WebShotId::AcousticKitty: {
        // Port fedele di shots_group_b.py: i fogli sono poligoni (non rect),
        // la placca e' sfocata con GaussianBlur(9) e poi velata 0.16.
        Json bg = rect("bg",0,0,1920,1080,"#4E4640",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.016f, 71, 0.30f); L.push_back(std::move(bg));
        // NB: gaussian_blur sulle shape azzera il frame sul backend Vulkan
        // attuale (verificato isolando gli effetti), quindi la placca resta
        // nitida finche' il fix non arriva nel renderer.
        L.push_back(poly("p1",{{0,120},{760,40},{820,620},{60,700}},"#D6C7A8",0.95f,D));
        L.push_back(poly("p2",{{600,0},{1500,60},{1440,560},{560,520}},"#C9B896",0.9f,D));
        L.push_back(poly("p3",{{1150,260},{1920,180},{1920,900},{1100,860}},"#E2D3B0",0.92f,D));
        L.push_back(poly("p4",{{0,640},{900,560},{980,1080},{0,1080}},"#B3A184",0.9f,D));
        L.push_back(poly("scrap",{{0,0},{360,0},{230,300},{0,240}},"#2E3C5E",0.95f,D));
        for (int i = 0; i < 22; ++i) {
            const float lx = 120 + float((i * 173) % 1500);
            const float ly = 300 + float((i * 247) % 620);
            L.push_back(line("ink" + std::to_string(i), lx, ly,
                             lx + 130 + (i % 4) * 40, ly + (i % 3) * 6 - 6,
                             3, "#8A7A62", 0.55f, D));
        }
        L.push_back(textLayer("stamp","C-90",820,700,220,kSerifBold,"#2A211A",D,0,-1,0.7f));
        L.push_back(rect("veil",0,0,1920,1080,"#3A2E22",0.16f,Json::array(),D));
        float x0 = 270 + 1138.9f;
        float w = 248.0f;
        L.push_back(modules::TextHighlight::layer("m", x0-8, 486, w+16, 62, "#E8DC4A", 0.90f, 7, 32, D));
        L.push_back(textLayer("t","The First (and Last) Field Test",270,376,64,kSerifBold,"#F2EFE8",D,0,0));
        L.push_back(textLayer("b1","After years of development and an estimated cost of $20 million",270,478,54,kSerif,"#EDE8DF",D));
        L.push_back(textLayer("b2","(roughly $170 million today), Acoustic Kitty was ready for the real",270,556,54,kSerif,"#EDE8DF",D));
        L.push_back(textLayer("b3","world.",270,634,54,kSerif,"#EDE8DF",D));
        L.push_back(textLayer("b1hl","$20 million",x0,478,54,kSerif,"#B08A2E",D));
        break; }
    // ============ GROUP C ============
    case WebShotId::SabotageManualGlow: {
        Json bg = rect("bg",0,0,1920,1080,"#070706",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.014f, 1212, 0.30f); L.push_back(std::move(bg));
        L.push_back(textLayer("d1","was written during active wartime, the",-140,210,130,kPlayfair,"#6B6156",D));
        L.push_back(textLayer("d2","gestions for causing physical violence",-140,370,130,kPlayfair,"#4E4841",D));
        L.push_back(rect("halo",-140,530,1600,130,"#F2CD52",0.35f,Json::array(),D));
        L.push_back(textLayer("glow","ting fires, flooding warehouses, break",-140,530,130,kPlayfair,"#F5D24A",D,0,1));
        L.push_back(textLayer("d3","s many suggestions for how to just get",-140,690,130,kPlayfair,"#4E4841",D));
        L.push_back(textLayer("d4","ithin a bureaucracy or office setting.",-140,850,130,kPlayfair,"#6B6156",D));
        break; }
    case WebShotId::FoiaFinkelZoom: {
        Json bg = rect("paper",0,0,1920,1080,"#E9E8E6",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.012f, 13, 0.12f);
        L.push_back(std::move(bg));
        const float size = 112.f;
        const char* l1 = "filed a Freedom of Information Act request";
        const char* l2 = "n Post reporter David Finkel in his book '";
        const float mw = measuredTextWidth("filed a Freedom of Information Act", size, kHelvMed) + 16.f;
        L.push_back(modules::TextHighlight::layer("m", -95.f, 312.f, mw, 96.f, "#E6E32E", 0.95f, b10, s35, D));
        L.push_back(textLayer("l1", l1, -90.f, 300.f, size, kHelvMed, "#101010", D));
        L.push_back(textLayer("l2", l2, -70.f, 470.f, size, kHelvMed, "#101010", D));
        break; }
    case WebShotId::Vw40Times: {
        Json bg = rect("paper",0,0,1920,1080,"#E9E8E2",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 14, 0.14f);
        L.push_back(std::move(bg));
        const float size = 103.f, x = -120.f;
        const char* lines[] = {
            "sting in May 2014 that led the California Air R",
            "lkswagen was conducted by researchers at Wes",
            "missions from two VW models equipped with th",
            "sel engine. The researchers found that when tes"};
        for (int i = 0; i < 4; ++i)
            L.push_back(textLayer("l" + std::to_string(i), lines[i], x, 150.f + 150.f * i,
                size, kSerif, "#A6A39B", D));
        const float x5 = -140.f;
        const float xb = x5 + measuredTextWidth("most ", size, kSerif);
        const float xt = xb + measuredTextWidth("40 times", size, kSerifBold);
        const float mw = measuredTextWidth("40 times the permitted levels", size, kSerifBold) + 16.f;
        L.push_back(modules::TextHighlight::layer("m", xb - 8.f, 758.f, mw, 92.f, "#E6E32E", 0.95f, b10, s35, D));
        L.push_back(textLayer("l5a", "most ", x5, 750.f, size, kSerif, "#A6A39B", D));
        L.push_back(textLayer("l5b", "40 times", xb, 750.f, size, kSerifBold, "#2E2C28", D));
        L.push_back(textLayer("l5c", " the permitted levels of nitrogen", xt, 750.f, size, kSerif, "#A6A39B", D));
        break; }
    case WebShotId::CnbcSbfTilt: {
        Json bg = rect("paper",0,0,1920,1080,"#EDEBE7",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.012f, 15, 0.18f); L.push_back(std::move(bg));
        L.push_back(textLayer("home","Home",150,200,28,kHelv,"#55565A",D));
        L.push_back(textLayer("comp","Companies",320,200,28,kHelv,"#55565A",D));
        L.push_back(textLayer("mk","Markets",555,200,28,kHelv,"#55565A",D));
        L.push_back(textLayer("st","Street Talk",725,200,28,kHelv,"#55565A",D));
        L.push_back(textLayer("pol","Politics",950,200,28,kHelv,"#55565A",D));
        L.push_back(textLayer("pol2","Policy",1130,200,28,kHelv,"#55565A",D));
        L.push_back(textLayer("wld","World",1285,200,28,kHelv,"#55565A",D));
        L.push_back(textLayer("prop","Property",1425,200,28,kHelv,"#55565A",D));
        L.push_back(rect("u",552,244,112,3,"#2B6FD6",1.f,Json::array(),D));
        L.push_back(modules::HeadlineComposition::line("h1","Why this 30-year-old crypto",960,340,122,kPlayfair,"#1B1B1D",D,"ma"));
        L.push_back(modules::HeadlineComposition::line("h2","billionaire wants to give his",960,500,122,kPlayfair,"#1B1B1D",D,"ma"));
        L.push_back(modules::HeadlineComposition::line("h3","fortune away",960,660,122,kPlayfair,"#1B1B1D",D,"ma"));
        L.push_back(textLayer("deck","Sam Bankman-Fried is worth $26 billion, but he drives a Toyota Corolla, sleeps on a beanbag and has a Robin Hood-like philosophy.",960,900,40,kSerifIt,"#6C6B68",D,0,-1,1.f,"ma"));
        // Letterbox + chyron. The old transparent tilt frame carried a 3D
        // rotation after the 2D flatten and was rejected by the renderer.
        L.push_back(rect("bar_top",0,0,1920,128,"#080809",1.f,Json::array(),D));
        L.push_back(rect("bar_bot",0,984,1920,96,"#080809",1.f,Json::array(),D));
        L.push_back(textLayer("chy","HE DECIDED THAT",960,1030,42,kOswaldBold,"#E8871E",D,0,-1,1.f,"mm"));
        break; }
    case WebShotId::NbcSwindled8b: {
        Json bg = rect("paper",0,0,1920,1080,"#F4F3F0",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 16, 0.14f); L.push_back(std::move(bg));
        L.push_back(textLayer("k","TECH",140,150,26,kBold,"#6E6E6E",D,0,-1,1.f,"la",3.0f));
        float x0 = 120 + 922.0f;
        L.push_back(modules::TextHighlight::layer("m1", x0-6, 222, 417.0f+12, 88, "#E6E32E", 0.95f, b10, s35, D));
        L.push_back(modules::TextHighlight::layer("m2", 114, 334, 928.0f+12, 88, "#E6E32E", 0.95f, 27, 40, D));
        L.push_back(modules::HeadlineComposition::line("h1","How Sam Bankman-Fried swindled $8",120,210,74,kHelvBold,"#0E0E10",D));
        L.push_back(modules::HeadlineComposition::line("h2","billion in customer money, according",120,322,74,kHelvBold,"#0E0E10",D));
        L.push_back(modules::HeadlineComposition::line("h3","to federal prosecutors",120,434,74,kHelvBold,"#0E0E10",D));
        L.push_back(textLayer("pub","PUBLISHED SUN, DEC 18 2022·8:00 AM EST | UPDATED MON, DEC 19 2022·2:06 PM EST",125,575,22,kMed,"#6F7076",D,0,-1,1.f,"la",1.6f));
        L.push_back(ellipse("av1",130,655,80,80,"#9AA0A6",1.f,D));
        L.push_back(textLayer("n1","Rohan Goswami",235,650,27,kBold,"#1A1A1C",D));
        L.push_back(textLayer("h1a","@IN/ROHANGOSWAMINBC/",235,692,21,kSemi,"#2E6FD6",D));
        L.push_back(textLayer("h1b","@ROGOSWAMI",235,726,21,kSemi,"#2E6FD6",D));
        L.push_back(ellipse("av2",510,655,80,80,"#9AA0A6",1.f,D));
        L.push_back(textLayer("n2","MacKenzie Sigalos",615,650,27,kBold,"#1A1A1C",D));
        L.push_back(textLayer("h2a","@KENZIESIGALOS",615,692,21,kSemi,"#2E6FD6",D));
        L.push_back(rect("greenbar",0,1072,1920,8,"#2E7D32",1.f,Json::array(),D));
        break; }
    // ============ GROUP D ============
    case WebShotId::GuardianBiggestFrauds: {
        Json bg = rect("paper",0,0,1920,1080,"#EFECE5",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 17, 0.16f); L.push_back(std::move(bg));
        L.push_back(textLayer("kick","Sam Bankman-Fried",110,125,30,kBold,"#7A2231",D,0,0));
        float x0 = 100 + 1174.0f;
        L.push_back(modules::TextHighlight::layer("m1", x0-6, 212, 519.0f+12, 92, "#E6E32E", 0.95f, b10, s35, D));
        L.push_back(modules::TextHighlight::layer("m2", 94, 342, 1068.0f+12, 92, "#E6E32E", 0.95f, 27, 40, D));
        L.push_back(modules::HeadlineComposition::line("h1","Sam Bankman-Fried charged in one of 'biggest",100,195,78,kPlayfairBold,"#16161A",D));
        L.push_back(modules::HeadlineComposition::line("h2","financial frauds' in US history",100,325,78,kPlayfairBold,"#16161A",D));
        L.push_back(textLayer("b1","Indictment brings eight criminal counts against crypto entrepreneur arrested in the",110,520,34,kRegular,"#67645F",D));
        L.push_back(textLayer("b2","Bahamas",110,572,34,kRegular,"#67645F",D));
        break; }
    case WebShotId::FtxTweetCard: {
        Json bg = rect("bg",0,0,1920,1080,"#E8E7E3",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 18, 0.18f); L.push_back(std::move(bg));
        L.push_back(textLayer("back","←",398,205,42,kDeja,"#1B1B1D",D));
        L.push_back(textLayer("post","Post",470,200,42,kBold,"#1B1B1D",D,0,0));
        L.push_back(ellipse("av",372,268,96,96,"#9AA0A6",1.f,D));
        L.push_back(ellipse("av_in",397,293,46,46,"#7E848A",1.f,D));
        L.push_back(textLayer("name","Mario Gabriele",500,272,36,kBold,"#141416",D));
        L.push_back(ellipse("warn",862,282,26,26,"#E8842A",1.f,D));
        L.push_back(textLayer("handle","@mariogabriele",500,324,31,kRegular,"#6E7076",D));
        L.push_back(textLayer("dots","•••",1545,278,34,kDeja,"#6E7076",D));
        L.push_back(textLayer("t1","FTX is a wild company.",300,420,37,kRegular,"#17171A",D,0,1));
        L.push_back(textLayer("t2","•  Worth $18b",348,505,37,kRegular,"#17171A",D));
        L.push_back(textLayer("t3","•  Processing billions of dollars a day in trades",348,558,37,kRegular,"#17171A",D));
        L.push_back(textLayer("t4","•  Has 6 engineers",348,611,37,kRegular,"#17171A",D));
        L.push_back(textLayer("t5","No joke. Crypto's fastest-growing exchange has been powered by a tiny,",300,700,37,kRegular,"#17171A",D));
        L.push_back(textLayer("t6","hard-working team.",300,753,37,kRegular,"#17171A",D));
        L.push_back(rect("card",278,838,1372,360,"#D8D8D4",1.f,Json::array(),D));
        L.push_back(rect("card_in",281,841,1366,354,"#FCFCFB",1.f,Json::array(),D));
        L.push_back(rect("logo_b",348,890,72,72,"#2F7BF0",1.f,Json::array(),D));
        L.push_back(ellipse("logo_p",340,996,90,62,"#5B3FD6",1.f,D));
        L.push_back(rect("logo_r",470,1002,44,60,"#D63B2F",1.f,Json::array(),D));
        L.push_back(textLayer("ftx","FTX",1140,975,175,kPlayfairBold,"#17171A",D,0,2,1.f,"mm"));
        L.push_back(textLayer("ftx_sub","CRYPTO'S SPEEDRUNNER",1140,1098,33,kSemi,"#17171A",D,0,-1,1.f,"mm",5.0f));
        break; }
    case WebShotId::NytLookCrazyZoom: {
        Json bg = rect("paper",0,0,1920,1080,"#E9E7E1",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 1919, 0.16f); L.push_back(std::move(bg));
        L.push_back(textLayer("l0","$40 billion.",-20,-8,56,kPlayfairBold,"#2E2B27",D));
        L.push_back(textLayer("l1","As his business grew, Mr. Bankman-Fried began to establish a public",-45,78,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l2","profile, tweeting about his favorite video games and going on TV to explain",-45,154,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l3","crypto to the masses. But he refused to comport himself like a typical",-45,230,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l4","CNBC guest. Before one of his first TV appearances, Andy Croghan, a",-45,306,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l5","colleague at Alameda and FTX, urged him to clean up his look.",-45,382,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l6","“I was like, ‘Sam, you’ve got to cut your hair, dude — it looks ridiculous,’”",-45,458,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l7","Mr. Croghan said. “And he said, ‘I honestly think it’s negative EV for me to",-45,534,56,kPlayfair,"#57544F",D));
        float px = -45 + 317.0f;
        float w = 1377.0f;
        L.push_back(modules::TextHighlight::layer("m", px-8, 618, w+16, 66, "#E9E600", 0.92f, 11, 41, D));
        L.push_back(textLayer("pre","cut my hair. ",-45,610,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("hl","I think it’s important for people to think I look crazy.’”",px,610,56,kPlayfair,"#2E2B27",D,0,1));
        L.push_back(textLayer("l9","Mr. Croghan learned to embrace that strategy. Mr. Bankman-Fried often",-45,686,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l10","takes power naps on his beanbag between meetings. At the FTX office in",-45,762,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l11","Hong Kong, Mr. Croghan would arrange for high-profile visitors to arrive",-45,838,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l12","while Mr. Bankman-Fried was still sleeping, ushering them into a",-45,914,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l13","conference room with a view of the slumbering chief executive. Eventually",-45,990,56,kPlayfair,"#57544F",D));
        L.push_back(textLayer("l14","Bankman-Fried would rouse himself and walk into the meeting,",-45,1066,56,kPlayfair,"#57544F",D));
        break; }
    case WebShotId::IndictmentSummary: {
        Json bg = rect("paper",0,0,1920,1080,"#F3F2EF",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 20, 0.18f); L.push_back(std::move(bg));
        L.push_back(textLayer("title","SUMMARY",760,35,50,kSerifBold,"#232323",D,0,0,1.f,"la",4.0f));
        L.push_back(rect("u",755,97,302,3,"#232323",1.f,Json::array(),D));
        L.push_back(textLayer("n","1.",120,150,58,kSerif,"#232323",D));
        L.push_back(textLayer("b1","From at least May 2019 through November 2022, Bankman-Fried engaged in a",225,140,58,kSerif,"#232323",D));
        L.push_back(textLayer("b2","scheme to defraud equity investors in FTX Trading Ltd. (“FTX”), the crypto asset trading",225,258,58,kSerif,"#232323",D));
        L.push_back(textLayer("b3","platform of which he was CEO and co-founder, at the same time that he was also defrauding the",225,376,58,kSerif,"#232323",D));
        float px = 225 + 508.8f;
        L.push_back(modules::TextHighlight::layer("m", px-6, 502, 513.0f+12, 64, "#E8C84A", 0.95f, b10, s35, D));
        L.push_back(textLayer("pre","platform’s customers. ",225,494,58,kSerif,"#232323",D));
        L.push_back(textLayer("hl","Bankman-Fried raised",px,494,58,kSerif,"#232323",D));
        L.push_back(textLayer("post"," more than $1.8 billion from investors, including",px+513.0f,494,58,kSerif,"#232323",D));
        L.push_back(textLayer("b5","investors, who bought an equity stake in FTX believing that FTX had appropriate controls",225,612,58,kSerif,"#232323",D));
        L.push_back(textLayer("b6","and management measures.  Unbeknownst to those investors (and to FTX’s trading",225,730,58,kSerif,"#232323",D));
        L.push_back(textLayer("b7","customers), Bankman-Fried was orchestrating a massive, years-long fraud, diverting billions of",225,848,58,kSerif,"#232323",D));
        L.push_back(textLayer("b8","customer funds for his own personal benefit and to help grow",225,966,58,kSerif,"#232323",D,0,-1,0.55f));
        break; }
    case WebShotId::GuardianSeoulMissiles: {
        Json bg = rect("bg",0,0,1920,1080,"#202020",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.014f, 2121, 0.26f); L.push_back(std::move(bg));
        L.push_back(textLayer("brand","The Guardian",360,180,58,kPlayfairBold,"#E4572E",D,0,0));
        L.push_back(modules::TextHighlight::layer("hl", 350, 378, 1295, 100, "#E4572E", 0.95f, b10, s35, D));
        L.push_back(modules::HeadlineComposition::line("h1","Hasty redeployment of US missiles",355,262,76,kArialBold,"#F4F4F2",D));
        L.push_back(modules::HeadlineComposition::line("h2","from South Korea to Middle East",355,372,76,kArialBold,"#F4F4F2",D));
        L.push_back(modules::HeadlineComposition::line("h3","leaves Seoul rattled",355,482,76,kArialBold,"#F4F4F2",D));
        L.push_back(modules::EvidenceTimeline::rail("tl_h",129,805,578,4,"#C9C9C9",1.f,D));
        L.push_back(modules::EvidenceTimeline::rail("tl_v1",89,845,4,240,"#C9C9C9",1.f,D));
        L.push_back(modules::EvidenceTimeline::rail("tl_v2",747,573,4,192,"#C9C9C9",1.f,D));
        L.push_back(modules::EvidenceTimeline::rail("tl_h2",787,533,948,4,"#C9C9C9",1.f,D));
        L.push_back(modules::EvidenceTimeline::point("dot",1712,510,46,46,"#E4572E",1.f,D));
        L.push_back(textLayer("c1","South Korea's president has sought to reassure",818,575,30,kDeja,"#8E8E8E",D,0,-1,1.f,"la",1.2f));
        L.push_back(textLayer("c2","the public that the country is able to deter",818,614,30,kDeja,"#8E8E8E",D,0,-1,1.f,"la",1.2f));
        L.push_back(textLayer("c3","threats from the North.",818,653,30,kDeja,"#8E8E8E",D,0,-1,1.f,"la",1.2f));
        break; }
    // ============ GROUP E ============
    case WebShotId::IvieFacebook: {
        Json bg = rect("paper",0,0,1920,1080,"#E8E8E6",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 2222, 0.16f); L.push_back(std::move(bg));
        const float size = 52.f;
        const float pre = measuredTextWidth("Ivie said she ", size, kRegular);
        const float w = measuredTextWidth("immediately reached out on Facebook to mothers' groups in the", size, kRegular) + 14.f;
        L.push_back(modules::TextHighlight::layer("m", 150.f + pre - 7.f, 326.f, w, 64.f, "#E8E300", 0.92f, b10, s35, D));
        L.push_back(textLayer("l1","Ivie said she immediately reached out on Facebook to mothers' groups in the",150,320,size,kRegular,"#232323",D));
        L.push_back(textLayer("l2","area and the post started to share rapidly. Within hours, the post had reached",150,420,size,kRegular,"#232323",D));
        L.push_back(textLayer("l3","Jennifer's friend who got in touch with her.",150,520,size,kRegular,"#232323",D));
        break; }
    case WebShotId::BlackVaultFoia: {
        Json bg = rect("paper",0,0,1920,1080,"#EDECEA",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 2323, 0.18f); L.push_back(std::move(bg));
        L.push_back(textLayer("l0","searchable online database. The database is on the Black Vault, a website h",90,114,54,kSerif,"#262624",D));
        L.push_back(rect("u",90+1085.0f,172,252.9f,3,"#262624",0.9f,Json::array(),D));
        L.push_back(textLayer("l1","created in 1996 at the tender age of 15 to give the public access to",90,224,54,kSerif,"#262624",D));
        L.push_back(textLayer("l2","government secrets.",90,333,54,kSerif,"#262624",D));
        L.push_back(textLayer("l3","Since then, Greenewald has made over 5,000 Freedom of Information Act",90,406,54,kSerif,"#262624",D));
        L.push_back(textLayer("l4","(FOIA) requests and has shared over 1.4 million pages of declassified",90,497,54,kSerif,"#262624",D));
        L.push_back(textLayer("l5","documents on his website, shedding light on supposed government cover-",90,588,54,kSerif,"#262624",D));
        L.push_back(textLayer("l6","ups ranging from UFOs to CIA mind-control experiments to the Benghazi",90,679,54,kSerif,"#262624",D));
        L.push_back(textLayer("l7","embassy attacks in 2012.",90,770,54,kSerif,"#262624",D));
        L.push_back(modules::TextHighlight::layer("m1", 84, 231, 333.0f+12, 62, "#E8E300", 0.92f, b10, 36, D));
        float x2 = 90 + 693.0f;
        L.push_back(modules::TextHighlight::layer("m2", x2-6, 504, 804.9f+12, 62, "#E8E300", 0.92f, 31, 40, D));
        L.push_back(modules::TextHighlight::layer("m3", 84, 595, 549.9f+12, 62, "#E8E300", 0.92f, 31, 40, D));
        break; }
    case WebShotId::BigFootPizza: {
        Json bg = rect("paper",0,0,1920,1080,"#F0EFEC",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 2424, 0.16f); L.push_back(std::move(bg));
        L.push_back(textLayer("t","The Big Foot",130,390,50,kBold,"#141414",D,0,0));
        const char* l1 = "In 1993, Pizza Hut released The Big Foot, a massive, 2 feet long by 1-foot";
        const char* l2a = "wide square pizza creation.";
        const char* l2b = " This promotion helped lift Pizza Hut's";
        const char* l3a = "sales to $5.7 billion,";
        const char* l3b = " with The Big Foot accounting for 18%";
        const char* l4 = "of total sales.";
        float w1 = measuredTextWidth(l1, 40.f, kRegular);
        float w2a = measuredTextWidth(l2a, 40.f, kRegular);
        float w3b = measuredTextWidth(l3b, 40.f, kRegular);
        float w4 = measuredTextWidth(l4, 40.f, kRegular);
        float xL2b = 130 + w2a;
        float xL3b = 130 + measuredTextWidth(l3a, 40.f, kRegular);
        L.push_back(modules::TextHighlight::layer("m1", 124, 501, w1+12, 52, "#B9A916", 0.95f, b10, s35, D));
        L.push_back(modules::TextHighlight::layer("m2", 124, 562, w2a+12, 52, "#B9A916", 0.95f, b10, s35, D));
        L.push_back(modules::TextHighlight::layer("m3", xL3b-6, 623, w3b+12, 52, "#B9A916", 0.95f, 36, 40, D));
        L.push_back(modules::TextHighlight::layer("m4", 124, 684, w4+12, 52, "#B9A916", 0.95f, 36, 40, D));
        L.push_back(textLayer("l1",l1,130,495,40,kRegular,"#141414",D));
        L.push_back(textLayer("l2a",l2a,130,556,40,kRegular,"#141414",D));
        L.push_back(textLayer("l2b",l2b,xL2b,556,40,kRegular,"#8A8A8A",D));
        L.push_back(textLayer("l3a",l3a,130,617,40,kRegular,"#8A8A8A",D));
        L.push_back(textLayer("l3b",l3b,xL3b,617,40,kRegular,"#141414",D));
        L.push_back(textLayer("l4",l4,130,678,40,kRegular,"#141414",D));
        break; }
    case WebShotId::PizzaSauceCaption: {
        Json bg = rect("bg",0,0,1920,1080,"#131110",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.016f, 25, 0.34f); L.push_back(std::move(bg));
        L.push_back(ellipse("pizza1",240,-180,1520,1240,"#2B241E",1.f,D));
        L.push_back(ellipse("pizza2",360,-60,1290,1010,"#221C17",1.f,D));
        for (int i = 0; i < 5; ++i)
            L.push_back(ellipse("pep"+std::to_string(i),400+229*i%1050,20+317*i%760,130,100,"#3B322A",0.8f,D));
        L.push_back(modules::TextHighlight::layer("cap", 80, 492, 1760, 148, "#F7F7F5", 1.f, 11, 43, D));
        L.push_back(textLayer("hl","When they started changing the sauce, it went downhill.",960,566,52,kRegular,"#101010",D,0,0,1.f,"mm"));
        break; }
    case WebShotId::PizzaHutPerception: {
        Json bg = rect("paper",0,0,1920,1080,"#FDFCFA",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.008f, 2626, 0.12f); L.push_back(std::move(bg));
        L.push_back(textLayer("l0",") of Pizza Hut's U.S., speaking at Yum's investor day",150,15,48,kSerif,"#1A1A1A",D,2.5f,0));
        L.push_back(textLayer("l1","Wednesday, said he is “dissatisfied” with Pizza Hut's growth, telling investors",150,87,48,kSerif,"#1A1A1A",D));
        L.push_back(textLayer("l2","that the brand has “a lot of work to do.”",150,158,48,kSerif,"#1A1A1A",D));
        L.push_back(textLayer("hl1","The biggest problem that Pizza Hut is facing is perception, Starrs said,",150,345,48,kSerif,"#1A1A1A",D));
        L.push_back(textLayer("hl2","explaining that many of its customers don't associate Pizza Hut with delivery.",150,425,48,kSerif,"#1A1A1A",D));
        L.push_back(textLayer("l5","Most people think about ordering a pizza and carrying it out, or sitting down a",150,504,48,kSerif,"#1A1A1A",D));
        L.push_back(textLayer("l6","table and having a server bring a meal. Starrs said the facade of its locations",150,584,48,kSerif,"#1A1A1A",D));
        L.push_back(textLayer("l7","reinforces this idea and isn't helping to lure in diners.",150,663,48,kSerif,"#1A1A1A",D));
        L.push_back(textLayer("hl5","“When you drive by the location, it doesn't scream ‘we deliver.’” Starrs said.",150,792,48,kSerif,"#1A1A1A",D));
        L.push_back(textLayer("l9","Pizza Hut has only recently getting into the delivery game. Today, 55 percent",150,915,48,kSerif,"#1A1A1A",D));
        L.push_back(textLayer("l10","of Pizza Hut's sales in the U.S. come from digital orders and only 10 percent of",150,995,48,kSerif,"#1A1A1A",D));
        L.push_back(textLayer("l11","sales stem from diners coming into the chain and dining in. Going forward",150,1073,48,kSerif,"#1A1A1A",D));
        const float w1 = measuredTextWidth("The biggest problem that Pizza Hut is facing is perception, Starrs said,", 48.f, kSerif) + 12.f;
        const float w2 = measuredTextWidth("explaining that many of its customers don't associate Pizza Hut with delivery.", 48.f, kSerif) + 12.f;
        const float m3x = 150.f + measuredTextWidth("table and having a server bring a meal. Starrs said the ", 48.f, kSerif) - 6.f;
        const float w3 = measuredTextWidth("facade of its locations", 48.f, kSerif) + 12.f;
        const float w4 = measuredTextWidth("reinforces this idea and isn't helping to lure in diners.", 48.f, kSerif) + 12.f;
        const float w5 = measuredTextWidth("“When you drive by the location, it doesn't scream ‘we deliver.’” Starrs said.", 48.f, kSerif) + 12.f;
        L.push_back(modules::TextHighlight::layer("m1", 144, 352, w1, 62, "#F2C500", 0.95f, 7, 33, D));
        L.push_back(modules::TextHighlight::layer("m2", 144, 432, w2, 62, "#F2C500", 0.95f, 7, 33, D));
        L.push_back(modules::TextHighlight::layer("m3", m3x, 591, w3, 62, "#F2C500", 0.95f, 25, 33, D));
        L.push_back(modules::TextHighlight::layer("m4", 144, 670, w4, 62, "#F2C500", 0.95f, 25, 33, D));
        L.push_back(modules::TextHighlight::layer("m5", 144, 799, w5, 62, "#F2C500", 0.95f, 43, 34, D));
        break; }
    case WebShotId::TimesOfIndiaCoxon: {
        Json bg = rect("bg",0,0,1920,1080,"#0D0D0C",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.012f, 2727, 0.30f); L.push_back(std::move(bg));
        L.push_back(textLayer("mast_g1","THE TIMES OF INDIA",956,140,88,kPlayfairBold,"#C0708A",D,0,-1,0.55f,"ma"));
        L.push_back(textLayer("mast_g2","THE TIMES OF INDIA",964,144,88,kPlayfairBold,"#C0708A",D,0,-1,0.55f,"ma"));
        L.push_back(textLayer("mast_g3","THE TIMES OF INDIA",960,142,88,kPlayfairBold,"#C0708A",D,0,-1,0.35f,"ma"));
        L.push_back(textLayer("mast","THE TIMES OF INDIA",960,142,88,kPlayfairBold,"#F2E8EA",D,0,0,1.f,"ma"));
        L.push_back(textLayer("crumb","News  ·  Education News  ·  News",960,330,28,kMed,"#2E8B8B",D,0,-1,1.f,"ma",1.0f));
        L.push_back(rect("box1", 250, 398, 1680, 96, "#F5F0EE", 0.96f, Json::array(), D));
        L.back()["_v4_highlight"] = true;
        L.push_back(rect("box2", 650, 492, 650, 96, "#F5F0EE", 0.96f, Json::array(), D));
        L.back()["_v4_highlight"] = true;
        L.push_back(textLayer("who","Who is",48,415,62,kPlayfairBold,"#7A7A7A",D));
        L.push_back(textLayer("hl1","Jacob Coxon, the ex-Anthropic researcher warning",290,419,50,kPlayfairBold,"#5B1E2B",D));
        L.push_back(textLayer("hl2","AI could kill us all?",690,514,50,kPlayfairBold,"#5B1E2B",D));
        L.push_back(textLayer("p1","A young researcher named Jacob Coxon resigned from Anthropic after working at OpenAI. He warned that artificial",960,645,27,kRegular,"#6E6E6E",D,0,-1,1.f,"ma"));
        L.push_back(textLayer("p2","intelligence could end humanity by the decade's end. Coxon's concerns emerged after AI models demonstrated concerning",960,695,27,kRegular,"#6E6E6E",D,0,-1,1.f,"ma"));
        L.push_back(textLayer("p3","capabilities and escaped testing environments. His public declaration amplified private debates within leading AI",960,745,27,kRegular,"#6E6E6E",D,0,-1,1.f,"ma"));
        L.push_back(textLayer("src","TOI Education",30,795,26,kRegular,"#6E6E6E",D));
        L.push_back(textLayer("date","Sep 19, 2026, 15:11 IST",1890,795,26,kRegular,"#6E6E6E",D,0,-1,1.f,"ra"));
        L.push_back(rect("photo",202,937,1515,143,"#7C8794",1.f,Json::array(),D));
        L.push_back(ellipse("hill1",260,900,500,260,"#4E6B3A",0.9f,D));
        L.push_back(ellipse("hill2",900,890,620,280,"#587742",0.9f,D));
        L.push_back(rect("capbox",720,982,480,60,"#141414",0.92f,Json::array(),D));
        L.push_back(textLayer("cap","alarm bells across the country.",960,998,26,kRegular,"#F2F2F2",D,0,-1,1.f,"ma"));
        break; }
    case WebShotId::AmodeiPaceFrontier: {
        Json bg = rect("bg",0,0,1920,1080,"#0A0A09",1.f,Json::array(),D);
        shot::modules::DocumentLayer::finish(bg, 0.010f, 2828, 0.30f); L.push_back(std::move(bg));
        L.push_back(textLayer("back","←",142,55,40,kDeja,"#E7E9EA",D));
        L.push_back(textLayer("post","Post",225,52,44,kBold,"#E7E9EA",D,0,0));
        L.push_back(ellipse("av",127,187,115,115,"#8B8F94",1.f,D));
        L.push_back(ellipse("av_h",157,205,55,62,"#3A3D41",1.f,D));
        L.push_back(textLayer("name","Dario Amodei",270,192,40,kBold,"#E7E9EA",D));
        L.push_back(ellipse("ver",575,202,40,40,"#1D9BF0",1.f,D));
        L.push_back(rect("ai",638,200,46,42,"#E7E9EA",1.f,Json::array(),D));
        L.push_back(textLayer("ai_t","AI",661,210,22,kBold,"#0A0A09",D,0,-1,1.f,"ma"));
        L.push_back(textLayer("handle","@DarioAmodei",270,252,34,kRegular,"#71767B",D));
        L.push_back(textLayer("dots","•••",1770,200,34,kDeja,"#E7E9EA",D));
        float w1 = 1356.0f;
        float w2 = 1278.0f;
        L.push_back(modules::TextHighlight::layer("box1", 118, 352, w1+16, 62, "#F2F2F0", 0.96f, 11, 41, D));
        L.push_back(modules::TextHighlight::layer("box2", 118, 417, w2+16, 62, "#F2F2F0", 0.96f, 50, 35, D));
        L.push_back(textLayer("hl1","We Must Pace the Frontier: I’ve written a new essay on why the AI",125,360,44,kRegular,"#0E0F10",D));
        L.push_back(textLayer("hl2","industry should slow down, with a three-part plan for doing so.",125,425,44,kRegular,"#0E0F10",D));
        L.push_back(textLayer("b1","Anthropic is unilaterally committing to the first of these steps. We’ll",125,570,44,kRegular,"#E7E9EA",D));
        L.push_back(textLayer("b2","provide third-party evaluators with permanent, employee-level access",125,645,44,kRegular,"#E7E9EA",D));
        L.push_back(textLayer("b3","to our systems, so that they can verify adherence to our safety",125,720,44,kRegular,"#E7E9EA",D));
        L.push_back(textLayer("b4","measures, report on incidents, and assess models’ alignment during",125,795,44,kRegular,"#E7E9EA",D));
        L.push_back(textLayer("b5","training.",125,870,44,kRegular,"#E7E9EA",D));
        L.push_back(textLayer("foot","You can read the full post here:",125,1005,52,kRegular,"#E7E9EA",D));
        break; }
    }
}

} // namespace

const char* webShotName(WebShotId id) {
    switch (id) {
        case WebShotId::KumingaEspn: return "01_kuminga_espn_article";
        case WebShotId::AlCaponeTitle: return "02_al_capone_title";
        case WebShotId::AlexisArquette: return "03_alexis_arquette_article";
        case WebShotId::CorllWarehouse: return "04_corll_warehouse_excerpt";
        case WebShotId::TheyWereEconomy: return "05_they_were_the_economy";
        case WebShotId::ThugTeacherQuote: return "06_thug_teacher_quote";
        case WebShotId::CrtAlcoholHeadline: return "07_crt_alcohol_headline";
        case WebShotId::RainmakingNyt: return "08_rainmaking_nyt";
        case WebShotId::PintoHighlight: return "09_pinto_highlight";
        case WebShotId::TaxExemptNyt: return "10_tax_exempt_nyt";
        case WebShotId::AcousticKitty: return "11_acoustic_kitty_field_test";
        case WebShotId::SabotageManualGlow: return "12_sabotage_manual_glow";
        case WebShotId::FoiaFinkelZoom: return "13_foia_finkel_zoom";
        case WebShotId::Vw40Times: return "14_vw_40_times";
        case WebShotId::CnbcSbfTilt: return "15_cnbcsbf_profile_tilt";
        case WebShotId::NbcSwindled8b: return "16_nbc_swindled_8b";
        case WebShotId::GuardianBiggestFrauds: return "17_guardian_biggest_frauds";
        case WebShotId::FtxTweetCard: return "18_ftx_tweet_card";
        case WebShotId::NytLookCrazyZoom: return "19_nyt_look_crazy_zoom";
        case WebShotId::IndictmentSummary: return "20_indictment_summary";
        case WebShotId::GuardianSeoulMissiles: return "21_guardian_seoul_missiles";
        case WebShotId::IvieFacebook: return "22_ivie_facebook";
        case WebShotId::BlackVaultFoia: return "23_black_vault_foia";
        case WebShotId::BigFootPizza: return "24_big_foot_pizza";
        case WebShotId::PizzaSauceCaption: return "25_pizza_sauce_caption";
        case WebShotId::PizzaHutPerception: return "26_pizza_hut_perception";
        case WebShotId::TimesOfIndiaCoxon: return "27_times_of_india_coxon";
        case WebShotId::AmodeiPaceFrontier: return "28_amodei_pace_frontier";
    }
    return "unknown";
}
const char* webShotSource(WebShotId id) {
    switch (id) {
        case WebShotId::KumingaEspn: return "Screenshot 2026-10-09 090957.png";
        case WebShotId::AlCaponeTitle: return "Screenshot 2026-10-21 at 10-01-01 How Al Capone Took Over Chicago at 26 No AI - YouTube.png";
        case WebShotId::AlexisArquette: return "Screenshot 2026-10-25 200405.png";
        case WebShotId::CorllWarehouse: return "Screenshot 2026-10-25 200506.png";
        case WebShotId::TheyWereEconomy: return "Screenshot 2026-10-25 200835.png";
        case WebShotId::ThugTeacherQuote: return "Screenshot 2026-10-25 202808.png";
        case WebShotId::CrtAlcoholHeadline: return "Screenshot 2026-10-25 at 12-18-39 Unsettling Conspiracies That Turned Out True - YouTube.png";
        case WebShotId::RainmakingNyt: return "Screenshot 2026-10-25 at 12-23-00 Unsettling Conspiracies That Turned Out True - YouTube.png";
        case WebShotId::PintoHighlight: return "Screenshot 2026-10-25 at 12-25-51 Unsettling Conspiracies That Turned Out True - YouTube.png";
        case WebShotId::TaxExemptNyt: return "Screenshot 2026-10-25 at 12-28-56 Unsettling Conspiracies That Turned Out True - YouTube.png";
        case WebShotId::AcousticKitty: return "Screenshot 2026-10-25 at 12-39-03 Unsettling Conspiracies That Turned Out True - YouTube.png";
        case WebShotId::SabotageManualGlow: return "Screenshot 2026-10-25 at 12-44-37 Unsettling Conspiracies That Turned Out True - YouTube.png";
        case WebShotId::FoiaFinkelZoom: return "Screenshot 2026-10-25 at 12-47-03 Unsettling Conspiracies That Turned Out True - YouTube.png";
        case WebShotId::Vw40Times: return "Screenshot 2026-10-25 at 12-51-15 Unsettling Conspiracies That Turned Out True - YouTube.png";
        case WebShotId::CnbcSbfTilt: return "Screenshot 2026-10-26 085622.png";
        case WebShotId::NbcSwindled8b: return "Screenshot 2026-10-26 085659.png";
        case WebShotId::GuardianBiggestFrauds: return "Screenshot 2026-10-26 085706.png";
        case WebShotId::FtxTweetCard: return "Screenshot 2026-10-26 090129.png";
        case WebShotId::NytLookCrazyZoom: return "Screenshot 2026-10-26 090410.png";
        case WebShotId::IndictmentSummary: return "Screenshot 2026-10-26 090523.png";
        case WebShotId::GuardianSeoulMissiles: return "Screenshot 2026-10-26 at 11-13-55 America's deadly miscalculation in Iran - YouTube.png";
        case WebShotId::IvieFacebook: return "Screenshot 2026-10-27 140914.png";
        case WebShotId::BlackVaultFoia: return "Screenshot 2026-10-27 141145.png";
        case WebShotId::BigFootPizza: return "Screenshot 2026-10-27 171823.png";
        case WebShotId::PizzaSauceCaption: return "Screenshot 2026-10-27 171918.png";
        case WebShotId::PizzaHutPerception: return "Screenshot 2026-10-27 172102.png";
        case WebShotId::TimesOfIndiaCoxon: return "Screenshot 2026-10-28 at 08-42-33 Elon Musk & Dario's Final Warning - YouTube.png";
        case WebShotId::AmodeiPaceFrontier: return "Screenshot 2026-10-28 at 08-42-54 Elon Musk & Dario's Final Warning - YouTube.png";
    }
    return "";
}
const char* webShotDescription(WebShotId id) {
    switch (id) {
        case WebShotId::KumingaEspn: return "ESPN article plate on dark desk: Kuminga demanding trade";
        case WebShotId::AlCaponeTitle: return "Tight B&W Capone crop with THE BRUTAL RISE AND FALL title";
        case WebShotId::AlexisArquette: return "news.com.au article: Alexis Arquette tell-all memoir, memoir marked yellow";
        case WebShotId::CorllWarehouse: return "Dark document excerpt, red marker on 1975 warehouse raid line";
        case WebShotId::TheyWereEconomy: return "Cream serif caption 'they were the economy' on dark red band";
        case WebShotId::ThugTeacherQuote: return "Blurred quote plate, gold marker on the teacher quote";
        case WebShotId::CrtAlcoholHeadline: return "CRT-fringed headline: GOVERNMENT TO DOUBLE ALCOHOL POISON CONTENT";
        case WebShotId::RainmakingNyt: return "NYT page: Rainmaking Is Used As Weapon by U.S. with marker sweep";
        case WebShotId::PintoHighlight: return "Blurred plate: Ford Pinto crash-test claim highlighted gold";
        case WebShotId::TaxExemptNyt: return "Tight NYT excerpt: church lost its tax-exempt status, marker sweep";
        case WebShotId::AcousticKitty: return "Sepia archival documents with Acoustic Kitty caption, $20M marked";
        case WebShotId::SabotageManualGlow: return "Dark zoom of Sabotage Field Manual text, one line glowing yellow";
        case WebShotId::FoiaFinkelZoom: return "Tight FOIA-request zoom, marker over 'filed a Freedom of Information Act'";
        case WebShotId::Vw40Times: return "Serif zoom of VW story, '40 times the permitted levels' marked";
        case WebShotId::CnbcSbfTilt: return "Tilted CNBC profile: 30-year-old crypto billionaire, orange chyron";
        case WebShotId::NbcSwindled8b: return "NBC TECH headline on SBF $8B, two yellow markers, tilted page";
        case WebShotId::GuardianBiggestFrauds: return "Tilted Guardian page: SBF 'biggest financial frauds', two markers";
        case WebShotId::FtxTweetCard: return "Mario Gabriele tweet on FTX with link card";
        case WebShotId::NytLookCrazyZoom: return "NYT SBF zoom, marker over 'I think it's important ... look crazy'";
        case WebShotId::IndictmentSummary: return "Tilted DOJ indictment SUMMARY, marker over 'Bankman-Fried raised'";
        case WebShotId::GuardianSeoulMissiles: return "Guardian motion card: US missiles redeployed, timeline line";
        case WebShotId::IvieFacebook: return "Light excerpt: Ivie reached out to mothers' groups on Facebook";
        case WebShotId::BlackVaultFoia: return "Serif zoom: Black Vault 5,000+ FOIA requests, two marker sweeps";
        case WebShotId::BigFootPizza: return "Wide excerpt: Pizza Hut 'The Big Foot' promo 1993, olive markers";
        case WebShotId::PizzaSauceCaption: return "Dark blurred pizza close-up with white rough caption card";
        case WebShotId::PizzaHutPerception: return "Serif article: Pizza Hut perception problem, yellow markers";
        case WebShotId::TimesOfIndiaCoxon: return "TOI page on dark screen: Coxon AI warning in white boxes";
        case WebShotId::AmodeiPaceFrontier: return "Dark-mode Amodei post: 'We Must Pace the Frontier'";
    }
    return "";
}
std::vector<WebShotId> allWebShotIds() {
    return {WebShotId::KumingaEspn, WebShotId::AlCaponeTitle, WebShotId::AlexisArquette,
        WebShotId::CorllWarehouse, WebShotId::TheyWereEconomy, WebShotId::ThugTeacherQuote,
        WebShotId::CrtAlcoholHeadline, WebShotId::RainmakingNyt, WebShotId::PintoHighlight,
        WebShotId::TaxExemptNyt, WebShotId::AcousticKitty, WebShotId::SabotageManualGlow,
        WebShotId::FoiaFinkelZoom, WebShotId::Vw40Times, WebShotId::CnbcSbfTilt,
        WebShotId::NbcSwindled8b, WebShotId::GuardianBiggestFrauds, WebShotId::FtxTweetCard,
        WebShotId::NytLookCrazyZoom, WebShotId::IndictmentSummary, WebShotId::GuardianSeoulMissiles,
        WebShotId::IvieFacebook, WebShotId::BlackVaultFoia, WebShotId::BigFootPizza,
        WebShotId::PizzaSauceCaption, WebShotId::PizzaHutPerception,
        WebShotId::TimesOfIndiaCoxon, WebShotId::AmodeiPaceFrontier};
}

std::vector<std::string> webShotAnimationModules(WebShotId id) {
    using M = std::vector<std::string>;
    switch (id) {
    case WebShotId::AlexisArquette:       return M{"DocumentLayer","DocumentCamera","HeadlineComposition","TextHighlight"};
    case WebShotId::CorllWarehouse:       return M{"DocumentLayer","TextHighlight","FocusMask"};
    case WebShotId::TheyWereEconomy:      return M{"HeadlineComposition","TextHighlight"};
    case WebShotId::ThugTeacherQuote:     return M{"DocumentLayer","TextHighlight","FocusMask"};
    case WebShotId::RainmakingNyt:        return M{"DocumentLayer","TextHighlight","HeadlineComposition"};
    case WebShotId::PintoHighlight:       return M{"DocumentLayer","TextHighlight","FocusMask"};
    case WebShotId::TaxExemptNyt:         return M{"DocumentLayer","TextHighlight"};
    case WebShotId::AcousticKitty:        return M{"DocumentLayer","DocumentCamera"};
    case WebShotId::SabotageManualGlow:   return M{"DocumentLayer","DocumentCamera","TextHighlight","FocusMask"};
    case WebShotId::FoiaFinkelZoom:       return M{"DocumentLayer","TextHighlight"};
    case WebShotId::Vw40Times:            return M{"DocumentLayer","TextHighlight"};
    case WebShotId::CnbcSbfTilt:          return M{"DocumentLayer","DocumentCamera","HeadlineComposition"};
    case WebShotId::NbcSwindled8b:        return M{"DocumentLayer","DocumentCamera","HeadlineComposition","TextHighlight"};
    case WebShotId::GuardianBiggestFrauds:return M{"DocumentLayer","DocumentCamera","HeadlineComposition","TextHighlight"};
    case WebShotId::FtxTweetCard:         return M{"DocumentLayer"};
    case WebShotId::NytLookCrazyZoom:     return M{"DocumentLayer","DocumentCamera","TextHighlight","FocusMask"};
    case WebShotId::IndictmentSummary:    return M{"DocumentLayer","DocumentCamera","TextHighlight","FocusMask"};
    case WebShotId::GuardianSeoulMissiles:return M{"HeadlineComposition","EvidenceTimeline","TextHighlight"};
    case WebShotId::IvieFacebook:         return M{"DocumentLayer","TextHighlight"};
    case WebShotId::BlackVaultFoia:       return M{"DocumentLayer","DocumentCamera","TextHighlight","FocusMask"};
    default: return M{};
    }
}

void WebShotSpec::validate() const {
    if (durationFrames < 30 || durationFrames > 600) fail("durationFrames must be in [30,600]");
    if (fps != 30) fail("only 30fps is certified for the rebuild grammar");
}
std::string WebShotSpec::planName() const { return std::string(webShotName(id)) + "_native_v1"; }
std::string WebShotSpec::planNameV4() const { return std::string(webShotName(id)) + "_native_v4"; }
std::string WebShotSpec::outputStem() const {
    if (!outputName.empty()) return outputName;
    return std::string(webShotName(id)) + ".mp4";
}

// Vulkan drops every 3D shape layer as soon as the plan carries a camera
// (verified with an 8-colour probe: text survived, all shapes vanished). The
// native path that actually draws shapes is screen-space 2D. Convert the
// authored top-left/wire coordinates into the 2D renderer's centered,
// y-down space and drop the camera; marker/keyframe tracks stay untouched.
void flattenLayersTo2d(Json& layers) {
    constexpr float canvasW = 1920.f;
    constexpr float canvasH = 1080.f;
    for (Json& layer : layers) {
        if (!layer.contains("position") || !layer["position"].is_array() ||
            layer["position"].size() < 2) continue;
        const std::string type = layer.value("type", std::string{});
        const float x = layer["position"][0].get<float>();
        const float y = layer["position"][1].get<float>();
        if (type == "shape") {
            layer["position"] = Json::array({x - canvasW * 0.5f, canvasH * 0.5f - y});
            layer["enable_3d"] = false;
        } else if (type == "text") {
            layer["position"] = Json::array({x, canvasH - y});
            layer["enable_3d"] = false;
        } else if (type == "image") {
            layer["position"] = Json::array({x, y});
            layer["enable_3d"] = false;
        }
    }
}

// ── v4: runtime word reveal ───────────────────────────────────────────────
// v3 compone ogni riga come una run unica: al frame 0 e' gia' tutta li'. La
// v4 spezza le run in parole, ognuna con la propria opacity track, e le fa
// entrare in ordine di lettura con un fade breve. La posizione di ogni parola
// viene misurata dal font reale (prefix advance), quindi la composizione
// resta quella approvata in v3. I marker vengono ri-temporizzati e l'area
// evidenziata guida un drift di camera espresso come offset screen-space:
// i layer 2D non ricevono la camera prospettica del renderer.
struct V4WordSpan { std::size_t begin, end; };

std::vector<V4WordSpan> v4Words(const std::string& text) {
    std::vector<V4WordSpan> result;
    std::size_t i = 0;
    while (i < text.size()) {
        while (i < text.size() && std::isspace(static_cast<unsigned char>(text[i]))) ++i;
        if (i == text.size()) break;
        const std::size_t begin = i;
        while (i < text.size() && !std::isspace(static_cast<unsigned char>(text[i]))) ++i;
        result.push_back({begin, i});
    }
    return result;
}

bool v4HasTextProperty(const Json& layer, const char* property) {
    if (!layer.contains("text_animators") || !layer["text_animators"].is_array()) return false;
    for (const Json& animator : layer["text_animators"]) {
        if (!animator.contains("properties") || !animator["properties"].is_array()) continue;
        for (const Json& prop : animator["properties"])
            if (prop.value("property", std::string{}) == property) return true;
    }
    return false;
}

int v4StartForTop(float top) {
    const float t = std::clamp((top - 60.f) / 820.f, 0.f, 1.f);
    return 2 + static_cast<int>(std::lround(t * 14.f));
}

Json v4OpacityTrack(double target, int start, int fade, int duration) {
    Json keys = Json::array();
    keys.push_back(Json{{"frame", 0}, {"value", 0.0}});
    if (start > 0) keys.push_back(Json{{"frame", start}, {"value", 0.0}});
    const int end = std::min(duration - 1, start + fade);
    keys.push_back(Json{{"frame", end}, {"value", target}});
    if (end < duration - 1) keys.push_back(Json{{"frame", duration - 1}, {"value", target}});
    return Json{{"property", "opacity"}, {"easing", "out_cubic"}, {"keyframes", std::move(keys)}};
}

Json v4AnimatorFadeTrack(int start, int fade, int duration) {
    // Text animator property tracks only accept linear easing in the plan
    // schema, so bake the out-cubic curve into the keyframe values instead.
    Json keys = Json::array();
    keys.push_back(Json{{"frame", 0}, {"value", 0.0}});
    if (start > 0) keys.push_back(Json{{"frame", start}, {"value", 0.0}});
    const int end = std::min(duration - 1, start + fade);
    const int f1 = std::min(end, start + std::max(1, fade / 3));
    const int f2 = std::min(end, start + std::max(1, (2 * fade) / 3));
    if (f1 > start) keys.push_back(Json{{"frame", f1}, {"value", 0.7037}});
    if (f2 > f1) keys.push_back(Json{{"frame", f2}, {"value", 0.9630}});
    keys.push_back(Json{{"frame", end}, {"value", 1.0}});
    if (end < duration - 1) keys.push_back(Json{{"frame", duration - 1}, {"value", 1.0}});
    return Json{{"property", "opacity"}, {"easing", "linear"}, {"keyframes", std::move(keys)}};
}

void v4SetTrack(Json& layer, Json track) {
    Json tracks = Json::array();
    if (layer.contains("animation") && layer["animation"].is_object() &&
        layer["animation"].contains("tracks") && layer["animation"]["tracks"].is_array())
        tracks = layer["animation"]["tracks"];
    const std::string property = track.value("property", std::string{});
    Json kept = Json::array();
    for (const Json& existing : tracks)
        if (existing.value("property", std::string{}) != property) kept.push_back(existing);
    kept.push_back(std::move(track));
    layer["animation"] = Json{{"tracks", std::move(kept)}};
}

Json v4ExistingTrack(const Json& layer, const std::string& property) {
    if (!layer.contains("animation") || !layer["animation"].is_object() ||
        !layer["animation"].contains("tracks") || !layer["animation"]["tracks"].is_array())
        return Json();
    for (const Json& track : layer["animation"]["tracks"])
        if (track.value("property", std::string{}) == property) return track;
    return Json();
}

float v4Top(const Json& layer) {
    return float(kH) - layer["position"][1].get<float>() - layer["size"][1].get<float>() * 0.5f;
}

Json v4WordLayer(const Json& source, const std::string& word, float runLeft, float boxTop,
                 const std::string& id, double opacity, int start, int duration) {
    const std::string font = source["style"].value("font", std::string{});
    const float size = source["style"].value("font_size", 1.f);
    const float content = measuredTextWidth(word, size, font);
    const float w = std::max(60.f, content * 1.10f);
    const float h = source["size"][1].get<float>();
    const float pad = (w - content) * 0.5f;
    Json layer = source;
    layer["id"] = id;
    layer["text"] = word;
    layer["size"] = Json::array({w, h});
    layer["position"] = wirePos(runLeft - pad + w * 0.5f, boxTop + h * 0.5f);
    layer["start_frame"] = 0;
    layer["duration_frames"] = duration;
    layer.erase("opacity");
    layer.erase("animation");
    layer.erase("text_animators");
    v4SetTrack(layer, v4OpacityTrack(opacity, start, 7, duration));
    return layer;
}

struct V4MarkerTime { int begin{0}, span{1}; };

bool v4MarkerTime(const Json& layer, V4MarkerTime& out) {
    if (!layer.contains("animation") || !layer["animation"].is_object() ||
        !layer["animation"].contains("tracks") || !layer["animation"]["tracks"].is_array())
        return false;
    for (const Json& track : layer["animation"]["tracks"]) {
        if (track.value("property", std::string{}) != "scale_x") continue;
        if (!track.contains("keyframes") || !track["keyframes"].is_array() ||
            track["keyframes"].size() < 2) return false;
        const Json& keys = track["keyframes"];
        out.begin = keys[1].value("frame", 0);
        out.span = std::max(1, keys.back().value("frame", 0) - out.begin);
        return true;
    }
    return false;
}

void v4PanLayer(Json& layer, double dx, double dy, int duration) {
    if (!layer.contains("position") || !layer["position"].is_array() ||
        layer["position"].size() < 2) return;
    if (layer.value("type", std::string{}) == "color") return;
    if (layer.contains("size") && layer["size"].is_array() && layer["size"].size() >= 2 &&
        layer["size"][0].get<float>() >= 1900.f && layer["size"][1].get<float>() >= 1060.f)
        return;
    const int holdFrame = std::max(1, std::min(duration - 2,
        static_cast<int>(std::lround(double(duration - 1) * 0.72))));
    auto apply = [&](const char* property, double delta) {
        if (std::abs(delta) < 0.001) return;
        const Json existing = v4ExistingTrack(layer, property);
        if (existing.is_null()) {
            Json keys = Json::array();
            keys.push_back(Json{{"frame", 0}, {"value", 0.0}});
            keys.push_back(Json{{"frame", holdFrame}, {"value", delta}});
            if (holdFrame < duration - 1)
                keys.push_back(Json{{"frame", duration - 1}, {"value", delta}});
            v4SetTrack(layer, Json{{"property", property}, {"easing", "in_out_cubic"},
                                   {"keyframes", std::move(keys)}});
            return;
        }
        Json keys = Json::array();
        for (int frame = 0; frame < duration; ++frame) {
            const double t = std::min(1.0, double(frame) / double(holdFrame));
            keys.push_back(Json{{"frame", frame},
                {"value", trackValueAt(existing, frame) + delta * easingEval("in_out_cubic", t)}});
        }
        v4SetTrack(layer, Json{{"property", property}, {"easing", "linear"},
                               {"keyframes", std::move(keys)}});
    };
    apply("position_x", dx);
    apply("position_y", dy);
}

Json v4FullWindowSelector(const std::string& id) {
    return Json{
        {"id", id}, {"unit", "character"}, {"shape", "square"},
        {"order", "forward"}, {"combine", "replace"}, {"exclude_spaces", false},
        {"start", Json{{"keyframes", Json::array({Json{{"frame", 0}, {"value", 0.0}}})},
                        {"easing", "linear"}}},
        {"end", Json{{"keyframes", Json::array({Json{{"frame", 0}, {"value", 100.0}}})},
                      {"easing", "linear"}}}};
}

void applyV4Reveal(Json& layers, int duration) {
    bool foundFocus = false, anyMarker = false;
    float focusX = 0.f, focusY = 0.f, focusArea = 0.f;
    int minBegin = 0, maxBegin = 0;
    for (const Json& layer : layers) {
        if (!layer.value("_v4_highlight", false)) continue;
        const float w = layer["size"][0].get<float>();
        const float h = layer["size"][1].get<float>();
        const float cx = layer["position"][0].get<float>();
        const float cy = float(kH) - layer["position"][1].get<float>();
        if (w * h > focusArea) {
            focusArea = w * h; focusX = cx; focusY = cy; foundFocus = true;
        }
        V4MarkerTime timing;
        if (v4MarkerTime(layer, timing)) {
            if (!anyMarker) { minBegin = maxBegin = timing.begin; anyMarker = true; }
            else {
                minBegin = std::min(minBegin, timing.begin);
                maxBegin = std::max(maxBegin, timing.begin);
            }
        }
    }
    for (Json& layer : layers) {
        if (!layer.value("_v4_highlight", false)) continue;
        V4MarkerTime timing;
        if (v4MarkerTime(layer, timing)) {
            const int begin = anyMarker && maxBegin > minBegin
                ? 28 + static_cast<int>(std::lround(
                      18.0 * double(timing.begin - minBegin) / double(maxBegin - minBegin)))
                : 30;
            const int span = std::clamp(timing.span, 12, 22);
            const float width = layer["size"][0].get<float>();
            layer["animation"] = Json{{"tracks",
                modules::TextHighlight::tracks(width, begin, span)}};
        } else {
            v4SetTrack(layer, v4OpacityTrack(1.0, 28, 9, duration));
        }
    }
    if (foundFocus) {
        Json highlights = Json::array(), rest = Json::array();
        for (Json& layer : layers) {
            if (layer.value("_v4_highlight", false)) highlights.push_back(std::move(layer));
            else rest.push_back(std::move(layer));
        }
        std::size_t insertAt = rest.size();
        for (std::size_t i = 0; i < rest.size(); ++i)
            if (rest[i].value("type", std::string{}) == "text") { insertAt = i; break; }
        Json ordered = Json::array();
        for (std::size_t i = 0; i < insertAt; ++i) ordered.push_back(std::move(rest[i]));
        for (Json& layer : highlights) ordered.push_back(std::move(layer));
        for (std::size_t i = insertAt; i < rest.size(); ++i) ordered.push_back(std::move(rest[i]));
        layers = std::move(ordered);
    }
    for (Json& layer : layers) layer.erase("_v4_highlight");

    // One text layer per authored line; each word gets its own selector +
    // opacity animator. This keeps the renderer at v3's surface count while
    // still fading every word in at runtime.
    for (Json& layer : layers) {
        if (layer.value("type", std::string{}) != "text") continue;
        const float top = v4Top(layer);
        const int blockStart = v4StartForTop(top);
        const bool keepWhole = v4HasTextProperty(layer, "tracking") ||
                               v4HasTextProperty(layer, "blur");
        Json animators = layer.contains("text_animators") &&
                         layer["text_animators"].is_array()
            ? layer["text_animators"] : Json::array();
        const std::string id = layer.value("id", std::string{"text"});
        if (keepWhole) {
            // Tracking/blur: keep the authored font effect and add one
            // whole-line opacity property to its existing full-window
            // animator. Splitting these would lose spacing and duplicate the
            // blur across dozens of tiny surfaces.
            if (animators.empty()) {
                Json whole = Json::object();
                whole["id"] = id + "_v4whole";
                whole["selectors"] = Json::array({v4FullWindowSelector(id + "_v4whole_sel")});
                whole["properties"] = Json::array();
                animators.push_back(std::move(whole));
            }
            animators[0]["properties"].push_back(
                v4AnimatorFadeTrack(blockStart + 2, 8, duration));
            layer["text_animators"] = std::move(animators);
            continue;
        }
        const std::string text = layer.value("text", std::string{});
        const std::vector<V4WordSpan> spans = v4Words(text);
        if (spans.empty()) continue;
        const int count = static_cast<int>(spans.size());
        const float stagger = count > 1
            ? std::min(1.7f, 15.f / float(count - 1)) : 0.f;
        for (int i = 0; i < count; ++i) {
            const int start = blockStart + static_cast<int>(std::lround(float(i) * stagger));
            const double wordStart = 100.0 * double(i) / double(count);
            const double wordEnd = 100.0 * double(i + 1) / double(count);
            Json startTrack = Json::object();
            startTrack["easing"] = "linear";
            startTrack["keyframes"] = Json::array({
                Json{{"frame", 0}, {"value", wordStart}}});
            Json endTrack = Json::object();
            endTrack["easing"] = "linear";
            endTrack["keyframes"] = Json::array({
                Json{{"frame", 0}, {"value", wordEnd}}});
            Json selector = Json::object();
            selector["id"] = id + "_v4sel_" + std::to_string(i);
            selector["unit"] = "word";
            selector["shape"] = "square";
            selector["order"] = "forward";
            selector["combine"] = "replace";
            selector["exclude_spaces"] = false;
            selector["start"] = std::move(startTrack);
            selector["end"] = std::move(endTrack);
            Json animator = Json::object();
            animator["id"] = id + "_v4w_" + std::to_string(i);
            animator["selectors"] = Json::array({std::move(selector)});
            animator["properties"] = Json::array({
                v4AnimatorFadeTrack(start, 7, duration)});
            animators.push_back(std::move(animator));
        }
        layer["text_animators"] = std::move(animators);
    }

    if (foundFocus) {
        double dx = std::clamp((960.0 - double(focusX)) * 0.30, -64.0, 64.0);
        double dy = std::clamp((540.0 - double(focusY)) * 0.30, -40.0, 40.0);
        if (std::abs(dx) < 6.0) dx = 0.0;
        if (std::abs(dy) < 6.0) dy = 0.0;
        if (dx != 0.0 || dy != 0.0)
            for (Json& layer : layers) v4PanLayer(layer, dx, dy, duration);
    }
}

Json buildWebShotPlan(const WebShotSpec& spec) {
    spec.validate();
    Json layers = Json::array();
    buildLayers(spec.id, layers, spec.durationFrames);
    flattenLayersTo2d(layers);
    const auto authoredMove = cameraMove(spec.id);
    const double zoomDelta = std::clamp(std::abs(authoredMove[3]-authoredMove[0]) * 0.20, 0.0, 0.012);
    const double cxDelta = std::clamp((authoredMove[4]-authoredMove[1]) * 0.10, -0.003, 0.003);
    const double cyDelta = std::clamp((authoredMove[5]-authoredMove[2]) * 0.10, -0.003, 0.003);
    Json plan = shot::renderPlan(spec.planName(), spec.durationFrames, layers,
        shot::modules::DocumentCamera::samples(spec.durationFrames, 1.0, 0.5, 0.5,
                                    1.0 + zoomDelta, 0.5 + cxDelta, 0.5 + cyDelta));
    // The static camera is what makes Vulkan cull the shape layers. The 2D
    // conversions above already place every layer on screen, so no projection
    // is needed; keep the authored marker tracks as the only motion authority.
    plan.erase("camera");
    plan.erase("camera_samples");
    plan["output"] = Json{{"path", spec.outputStem()}, {"format","mp4"}, {"codec","h264"}};
    return plan;
}

Json buildWebShotPlanV4(const WebShotSpec& spec) {
    spec.validate();
    Json layers = Json::array();
    buildLayers(spec.id, layers, spec.durationFrames);
    applyV4Reveal(layers, spec.durationFrames);
    flattenLayersTo2d(layers);
    Json plan = shot::renderPlan(spec.planNameV4(), spec.durationFrames, layers, Json::array());
    plan.erase("camera");
    plan.erase("camera_samples");
    const std::string output = std::string(webShotName(spec.id)) + "_native_v4.mp4";
    plan["output"] = Json{{"path", output}, {"format","mp4"}, {"codec","h264"}};
    return plan;
}

} // namespace chronontemplate::web
