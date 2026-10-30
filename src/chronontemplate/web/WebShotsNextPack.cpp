// ChrononTemplate web.WebShotsNextPack — 6 nuove animazioni nello stile dei 28.
//
// Stessa grammatica dei rebuild (piastra + marker sweep + push centrale)
// con gesti nuovi: marker incrociati, glow pulsante, snap di scala,
// timeline che si disegna, caption pop, fringe CRT con flash.
// Helper condivisi da chronontemplate/web/WebShotJson.hpp (JSON puro).
#include "chronontemplate/web/WebShotsNextPack.hpp"
#include "chronontemplate/web/WebShotJson.hpp"

#include <stdexcept>

namespace chronontemplate::web {

using shot::Json;
using namespace shot;

namespace {

[[noreturn]] void fail(const std::string& m) { throw std::invalid_argument("WebNextSpec: " + m); }

} // namespace

const char* webNextName(WebNextRecipe r){
    switch(r){
        case WebNextRecipe::DualMarkerCross: return "next_dual_marker_cross";
        case WebNextRecipe::GlowLinePulse: return "next_glow_line_pulse";
        case WebNextRecipe::TiltSnapReveal: return "next_tilt_snap_reveal";
        case WebNextRecipe::TimelineDash: return "next_timeline_dash";
        case WebNextRecipe::CaptionPopCard: return "next_caption_pop_card";
        case WebNextRecipe::CrtFringeFlash: return "next_crt_fringe_flash";
    } return "unknown";
}
std::vector<WebNextRecipe> allWebNextRecipes(){
    return {WebNextRecipe::DualMarkerCross, WebNextRecipe::GlowLinePulse,
        WebNextRecipe::TiltSnapReveal, WebNextRecipe::TimelineDash,
        WebNextRecipe::CaptionPopCard, WebNextRecipe::CrtFringeFlash};
}
void WebNextSpec::validate() const{
    if(durationFrames<30||durationFrames>600) fail("durationFrames must be in [30,600]");
    if(headline.empty()||headline.size()>120) fail("headline must be 1..120 chars");
    if(highlight.empty()||highlight.size()>80) fail("highlight must be 1..80 chars");
    if(headline.find(highlight)==std::string::npos) fail("highlight must appear in headline (come i 28)");
    if(headline.find('\n')!=std::string::npos||highlight.find('\n')!=std::string::npos) fail("no newlines");
}
std::string WebNextSpec::planName() const{ return std::string(webNextName(recipe))+"_v1"; }
std::string WebNextSpec::outputStem() const{
    if(!outputName.empty()) return outputName;
    return planName()+".mp4";
}

Json buildWebNextPlan(const WebNextSpec& spec){
    spec.validate();
    int D=spec.durationFrames;
    Json L=Json::array();
    int b1=D/9, s1=D*4/9, b2=D*3/10, s2=D*4/10;
    std::string hl = spec.highlightColor.empty() ? "#E6E300" : spec.highlightColor;
    switch(spec.recipe){
    case WebNextRecipe::DualMarkerCross: {
        std::string paper = spec.paperColor.empty() ? "#EDECEA" : spec.paperColor;
        L.push_back(rect("paper",0,0,1920,1080,paper,1.f,Json::array(),D));
        float wH = estimateWidth(spec.highlight,72);
        // due sweep incrociati: primo da sinistra, secondo da destra ritardato
        L.push_back(rect("cross_a",200,400,wH+24,92,hl,0.95f,sweepTracks(wH,b1,s1),D));
        L.push_back(rect("cross_b",200,520,wH+24,72,"#E4572E",0.55f,sweepTracks(wH,b2,s2),D));
        L.push_back(textLayer("headline",spec.headline,200,400,72,"ChrononTemplate/assets/fonts/HelveticaNeue-Bold.otf","#141416",D,0.f,0));
        L.push_back(textLayer("sub",spec.subline,200,640,30,"ChrononTemplate/assets/fonts/Inter-Regular.ttf","#67645F",D,0.f,1));
        L.push_back(textLayer("body",spec.body,200,700,30,"ChrononTemplate/assets/fonts/Inter-Regular.ttf","#67645F",D,2.4f,2));
        break; }
    case WebNextRecipe::GlowLinePulse: {
        std::string paper = spec.paperColor.empty() ? "#0A0A0A" : spec.paperColor;
        L.push_back(rect("bg",0,0,1920,1080,paper,1.f,Json::array(),D));
        float wH = estimateWidth(spec.highlight,110);
        // glow: banda larga opaca + core stretto + pulse opacity 0.75->1
        L.push_back(rect("glow_halo",200,430,wH+40,120,"#F5D24A",0.35f,sweepTracks(wH,b1,s1),D));
        L.push_back(rect("glow_core",200,452,wH+16,76,"#F5D24A",0.95f,sweepTracks(wH,b1+6,s1),D));
        L.push_back(rect("underline",200,600,900,6,"#F5D24A",0.9f,sweepTracks(900,b2,s2),D));
        L.push_back(textLayer("headline",spec.headline,200,430,110,"ChrononTemplate/assets/fonts/PlayfairDisplay-Italic.ttf","#F5D24A",D,0.f,0));
        L.push_back(textLayer("sub",spec.subline,200,680,30,"ChrononTemplate/assets/fonts/Inter-Regular.ttf","#8A8578",D,2.6f,1));
        break; }
    case WebNextRecipe::TiltSnapReveal: {
        std::string paper = spec.paperColor.empty() ? "#F4F3F0" : spec.paperColor;
        L.push_back(rect("paper",0,0,1920,1080,paper,1.f,Json::array(),D));
        float wH = estimateWidth(spec.highlight,72);
        L.push_back(rect("snap_marker",140,330,wH+16,92,hl,0.95f,sweepTracks(wH,b1,s1),D));
        L.push_back(textLayer("headline",spec.headline,140,330,72,"ChrononTemplate/assets/fonts/HelveticaNeue-Bold.otf","#0E0E10",D,0.f,0));
        L.push_back(textLayer("body",spec.body,140,480,34,"ChrononTemplate/assets/fonts/Inter-Regular.ttf","#4A4844",D,2.4f,1));
        // Snap centrato senza rotazione: scala 0.94->1 con easing morbido.
        L.back()["animation"] = Json::object({{"tracks", Json::array({
            easedTrack("scale_x",0.94f,1.f,0,D/3,"out_cubic"),
            easedTrack("scale_y",0.94f,1.f,0,D/3,"out_cubic")})}});
        L.push_back(rect("chyron",0,984,1920,96,"#080809",1.f,Json::array(),D));
        L.push_back(textLayer("chy",spec.subline,760,1010,34,"ChrononTemplate/assets/fonts/Oswald-Bold.ttf","#E8871E",D,0.f,2));
        break; }
    case WebNextRecipe::TimelineDash: {
        std::string paper = spec.paperColor.empty() ? "#202020" : spec.paperColor;
        L.push_back(rect("bg",0,0,1920,1080,paper,1.f,Json::array(),D));
        L.push_back(textLayer("headline",spec.headline,355,262,64,"ChrononTemplate/assets/fonts/Arial-Bold.ttf","#F4F4F2",D,0.f,0));
        L.push_back(rect("rail",355,480,1200,4,"#8A8A8A",0.6f,Json::array(),D));
        // draw: la linea si allunga 0->1200, poi il dot pinga
        L.push_back(rect("draw",355,477,1200,10,"#E4572E",0.95f,sweepTracks(1200,b1,s1),D));
        L.push_back(ellipse("dot",355+1200-23,457,46,46,"#E4572E",1.f,D));
        L.back()["animation"] = Json::object({{"tracks", Json::array({
            easedTrack("opacity",0.f,1.f,b1+s1-6,10,"out_cubic"),
            easedTrack("scale_x",0.4f,1.f,b1+s1-6,14,"out_back"),
            easedTrack("scale_y",0.4f,1.f,b1+s1-6,14,"out_back")})}});
        L.push_back(textLayer("body",spec.body,355,540,30,"ChrononTemplate/assets/fonts/DejaVuSans.ttf","#8E8E8E",D,0.f,1));
        break; }
    case WebNextRecipe::CaptionPopCard: {
        std::string paper = spec.paperColor.empty() ? "#131110" : spec.paperColor;
        L.push_back(rect("bg",0,0,1920,1080,paper,1.f,Json::array(),D));
        L.push_back(ellipse("pizza",240,-180,1520,1240,"#2B241E",1.f,D));
        // card: pop con overshoot 0.9->1 + marker sweep dietro
        float wH = estimateWidth(spec.headline,52);
        L.push_back(rect("card",960-(wH/2)-60,492,wH+120,148,"#F7F7F5",1.f,sweepTracks(wH,b1,s1),D));
        Json card = textLayer("cap",spec.headline,960-wH/2,556,52,"ChrononTemplate/assets/fonts/Inter-Regular.ttf","#101010",D,0.f,0);
        card["animation"] = Json::object({{"tracks", Json::array({
            easedTrack("scale_x",0.9f,1.f,0,22,"out_back"),
            easedTrack("scale_y",0.9f,1.f,0,22,"out_back"),
            easedTrack("opacity",0.f,1.f,0,16,"out_cubic")})}});
        L.push_back(std::move(card));
        break; }
    case WebNextRecipe::CrtFringeFlash: {
        std::string paper = spec.paperColor.empty() ? "#080A0C" : spec.paperColor;
        L.push_back(rect("bg",0,0,1920,1080,paper,1.f,Json::array(),D));
        // fringe: due copie offset rosso/ciano sotto il bianco
        L.push_back(textLayer("fr_r",spec.headline,105,205,96,kSerifBold,"#D5D000",D,0.f,-1,0.55f));
        L.push_back(textLayer("fr_b",spec.headline,95,195,96,kSerifBold,"#67B9D4",D,0.f,-1,0.42f));
        float wH = estimateWidth(spec.highlight,96);
        L.push_back(rect("flash",100,210,wH+16,116,"#C9DC28",0.0f,Json::array(),D));
        // flash reveal: opacity 0->0.85 sul marker + testo bianco sopra
        L.back()["animation"] = Json::object({{"tracks", Json::array({
            easedTrack("opacity",0.f,0.85f,b1,s1,"in_out_cubic"),
            easedTrack("scale_x",0.f,1.f,b1,s1,"in_out_cubic")})}});
        L.push_back(textLayer("headline",spec.headline,100,200,96,kSerifBold,"#DDE4E8",D,0.f,0));
        L.push_back(textLayer("sub",spec.subline,100,560,34,kOswald,"#DDE4E8",D,0.f,1));
        break; }
    }
    Json plan = shot::renderPlan(spec.planName(), D, L, shot::cameraSamples(D));
    plan["output"] = {{"path",spec.outputStem()},{"format","mp4"},{"codec","h264"}};
    return plan;
}

} // namespace chronontemplate::web
