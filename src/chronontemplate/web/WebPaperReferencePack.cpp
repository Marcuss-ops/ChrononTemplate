// ChrononTemplate web.WebPaperReferencePack — five supplied reference frames.
//
// The paper pages, torn strip and archive photograph are static content assets;
// the highlighter bands, page tilt, card entrance, shadows and watermarks are
// RenderPlan V3 layers. A flat lighting rig keeps raster and shape albedo at
// 100%; the highlighter is a normal-blend band and the text plate is lifted
// above it, so black ink stays black.
#include "chronontemplate/web/WebPaperReferencePack.hpp"

#include "chronontemplate/web/WebShotJson.hpp"

#include <algorithm>
#include <array>
#include <stdexcept>
#include <string>
#include <utility>

namespace chronontemplate::web {
namespace {

using Json = nlohmann::json;
using namespace shot;

constexpr const char* kAssetDir = "assets/web_reference_rebuild_20261114/";
constexpr const char* kInk = "#171614";
constexpr const char* kPaper = "#D9D8D3";
constexpr const char* kDesk = "#0E1012";
constexpr const char* kCharcoal = "#141414";

constexpr const char* kWatermark = "#8F8E8A";
// Resolved against the ChrononTemplate assets root, like the paper assets.
constexpr const char* kFontBold = "assets/fonts/Inter-Bold.ttf";
constexpr const char* kFontPlayfairBold = "assets/fonts/PlayfairDisplay-Bold.ttf";

[[noreturn]] void fail(const std::string& message) {
    throw std::invalid_argument("PaperReferenceSpec: " + message);
}

std::string asset(const char* name) {
    return std::string(kAssetDir) + name;
}

/// Two-key linear/eased channel, safe when the window starts at frame 0.
Json twoKeyTrack(const std::string& property, float from, float to, int duration,
                 const std::string& easing) {
    return Json{{"property", property}, {"easing", easing},
                {"keyframes", Json::array({
                    Json{{"frame", 0}, {"value", from}},
                    Json{{"frame", std::max(1, duration - 1)}, {"value", to}}})}};
}

/// Fade in and hold; no duplicate frame-0 key when start is 0.
Json fadeTrack(int duration, int start, int span, float peak = 1.f) {
    Json keys = Json::array();
    if (start > 0) keys.push_back(Json{{"frame", 0}, {"value", 0.0}});
    keys.push_back(Json{{"frame", start}, {"value", 0.0}});
    keys.push_back(Json{{"frame", start + span}, {"value", peak}});
    keys.push_back(Json{{"frame", std::max(1, duration - 1)}, {"value", peak}});
    return Json{{"property", "opacity"}, {"easing", "out_cubic"},
                {"keyframes", std::move(keys)}};
}

Json moveTrack(const std::string& property, float from, float to, int duration,
               int start, int span, const std::string& easing) {
    Json keys = Json::array();
    if (start > 0) keys.push_back(Json{{"frame", 0}, {"value", from}});
    keys.push_back(Json{{"frame", start}, {"value", from}});
    keys.push_back(Json{{"frame", start + span}, {"value", to}});
    keys.push_back(Json{{"frame", std::max(1, duration - 1)}, {"value", to}});
    return Json{{"property", property}, {"easing", easing},
                {"keyframes", std::move(keys)}};
}

void tracks(Json& layer, Json value) {
    layer["animation"] = Json{{"tracks", std::move(value)}};
}

/// Shape layers use a center relative to the canvas origin, exactly like image
/// layers. `rect`/`ellipse` build the absolute center with wirePos, so shift it
/// back; full-frame screen-space plates already sit at [0,0] and are left alone.
Json shiftShape(Json layer) {
    if (layer.value("screen_space", false)) return layer;
    if (layer.contains("position") && layer["position"].is_array() &&
        layer["position"].size() >= 2) {
        layer["position"][0] = layer["position"][0].get<float>() - 960.f;
        layer["position"][1] = layer["position"][1].get<float>() - 540.f;
    }
    return layer;
}

Json panel(const std::string& id, float left, float top, float width, float height,
           const std::string& color, float alpha, int duration) {
    return shiftShape(rect(id, left, top, width, height, color, alpha, Json::array(),
                           duration));
}

/// Native path fill is not rasterized by the Vulkan plan executor; the
/// referenced marker strokes are feathered textures, so the band is an image
/// swept with scale_x/position_x exactly like the native marker primitive.
Json marker(const std::string& id, const std::string& file, float left, float top,
            float width, float height, int begin, int span, int duration) {
    Json band = image(id, asset(file.c_str()), left, top, width, height, duration);
    tracks(band, sweepTracks(width, begin, span));
    return band;
}

/// The 2.5D pose is baked into the page plate: image-layer rotation is not
/// applied by the executor, while the transform still shows real perspective.
Json paperPage(int duration) {
    Json page = image("la_times_page", asset("la_times_page_tilted.png"), 0, 0,
                      1920, 1080, duration);
    // The baked plate is already full-bleed (its quad clears all four frame
    // edges), so a 1.0->1.05 push keeps coverage and the whole headline.
    tracks(page, Json::array({
        twoKeyTrack("scale", 1.f, 1.05f, duration, "in_out_cubic"),
        twoKeyTrack("position_x", -6.f, 10.f, duration, "in_out_cubic"),
        twoKeyTrack("position_y", 4.f, -4.f, duration, "in_out_cubic")}));
    return page;
}

/// Lift the sharp text plate clear of the marker depth range. At 0.05 steps the
/// Vulkan depth buffer resolves the 1 px marker/text contact unreliably.
Json liftAbove(Json plan, const std::string& id, float z = -0.8f) {
    for (Json& layer : plan["layers"]) {
        if (layer.value("id", std::string{}) == id && layer.contains("position") &&
            layer["position"].is_array() && layer["position"].size() >= 3) {
            layer["position"][2] = z;
        }
    }
    return plan;
}

Json sWatermark(int duration, float left = 1756.f, float top = 26.f) {
    Json box = panel("archive_watermark_box", left, top, 76, 76, kPaper, 0.40f,
                     duration);
    Json mark = textLayer("archive_watermark_s", "S", left + 38.f, top + 38.f, 30,
                          kFontBold, kWatermark, duration, 0.f, -1, 0.82f, "mm");
    return Json::array({box, mark});
}

// ── 1. LA Times page in 2.5D ────────────────────────────────────────────────
Json buildNewspaperTilt(int D) {
    Json layers = Json::array();
    Json bg = rect("desk", 0, 0, 1920, 1080, kDesk, 1.f, Json::array(), D);
    addNoiseVignette(bg, 0.012f, 7001, 0.56f);
    layers.push_back(std::move(bg));

    // A bare dark desk; the page edge and the paper texture carry the depth.
    layers.push_back(paperPage(D));
    return renderPlan("web_ref_newspaper_tilt_v1", D, layers, staticCamera());
}

// ── 2. Torn paper strip ─────────────────────────────────────────────────────
Json buildTornStrip(int D) {
    Json layers = Json::array();
    Json bg = image("charcoal", asset("torn_bg.png"), 0, 0, 1920, 1080, D);
    tracks(bg, Json::array({
        twoKeyTrack("scale", 1.025f, 1.f, D, "in_out_cubic"),
        twoKeyTrack("position_y", 5.f, 0.f, D, "in_out_cubic")}));
    layers.push_back(std::move(bg));

    Json strip = image("torn_strip", asset("torn_strip_base.png"), 70, 320, 1800, 460, D);
    layers.push_back(std::move(strip));

    // The strip text starts at x=70+120 and is 1578 px wide at 62 px, so the
    // strip fills the frame like the macro reference instead of floating small.
    // This stroke is a texture: its edges undulate like a real marker line.
    layers.push_back(marker("strip_marker", "marker_strip.png", 190, 430, 1586, 78,
                            38, 62, D));
    Json strip_text = image("torn_strip_text", asset("torn_strip_text.png"), 70, 320,
                            1800, 460, D);
    layers.push_back(std::move(strip_text));
    return liftAbove(renderPlan("web_ref_torn_strip_v1", D, layers, staticCamera()),
                     "torn_strip_text");
}

// ── 3. Sharp evidence over a defocused newspaper ────────────────────────────
Json buildBlurredEvidence(int D) {
    Json layers = Json::array();
    Json bg = image("blurred_newspaper", asset("evidence_bg.png"), 0, 0, 1920, 1080, D);
    tracks(bg, Json::array({
        twoKeyTrack("scale", 1.045f, 1.f, D, "in_out_cubic"),
        twoKeyTrack("position_y", 8.f, 0.f, D, "in_out_cubic")}));
    layers.push_back(std::move(bg));

    // No card, border or shadow: the sharp paragraph floats directly over the
    // defocused page, as in the supplied frame. Marker widths follow the text:
    // "whether a" at the end of line 4, full lines 5-6, "Arizona State" on 7.
    layers.push_back(marker("evidence_marker_3", "marker_evidence_3.png", 1209, 440,
                            251, 68, 42, 28, D));
    layers.push_back(marker("evidence_marker_4", "marker_evidence_4.png", 230, 515,
                            1400, 70, 54, 44, D));
    layers.push_back(marker("evidence_marker_5", "marker_evidence_5.png", 230, 595,
                            1300, 72, 66, 44, D));
    layers.push_back(marker("evidence_marker_6", "marker_evidence_6.png", 230, 675,
                            340, 72, 84, 26, D));

    Json text = image("evidence_text", asset("evidence_text.png"), 0, 0, 1920, 1080, D);
    layers.push_back(std::move(text));

    for (const Json& layer : sWatermark(D)) layers.push_back(layer);
    return liftAbove(renderPlan("web_ref_blurred_evidence_v1", D, layers, staticCamera()),
                     "evidence_text");
}

// ── 4. Archival collage with the Golden Gate photograph ─────────────────────
Json buildBridgeCollage(int D) {
    Json layers = Json::array();
    Json bg = image("collage_background", asset("collage_bg.png"), 0, 0, 1920, 1080, D);
    tracks(bg, Json::array({
        twoKeyTrack("scale", 1.035f, 1.f, D, "in_out_cubic"),
        twoKeyTrack("position_y", 6.f, 0.f, D, "in_out_cubic")}));
    layers.push_back(std::move(bg));

    // Narrative continuity: the previous shot's defocused paragraph survives
    // at the left edge, behind the title and the photo.
    Json left = image("collage_left_text", asset("collage_left_text.png"), 0, 260,
                      620, 520, D);
    tracks(left, Json::array({fadeTrack(D, 4, 14)}));
    layers.push_back(std::move(left));

    // Left-aligned with the photo's left edge, larger and darker than before.
    Json title_1 = textLayer("collage_title_1", "Giants drafted Barry Bonds", 496, 85,
                             76, kFontPlayfairBold, "#111111", D, 0.f, -1, 1.f, "la");
    tracks(title_1, Json::array({fadeTrack(D, 0, 18),
                                 moveTrack("position_y", 10.f, 0.f, D, 0, 18,
                                           "out_cubic")}));
    layers.push_back(std::move(title_1));
    Json title_2 = textLayer("collage_title_2", "but didn't sign him", 496, 169,
                             76, kFontPlayfairBold, "#111111", D, 0.f, -1, 1.f, "la");
    tracks(title_2, Json::array({fadeTrack(D, 3, 18),
                                 moveTrack("position_y", 10.f, 0.f, D, 3, 18,
                                           "out_cubic")}));
    layers.push_back(std::move(title_2));

    const Json rise = moveTrack("position_y", 24.f, 0.f, D, 10, 28, "out_cubic");
    const Json reveal = fadeTrack(D, 8, 20);

    Json shadow = panel("photo_shadow", 518, 350, 1024, 616, "#000000", 0.36f, D);
    tracks(shadow, Json::array({rise, reveal}));
    layers.push_back(std::move(shadow));

    Json border = panel("photo_border", 486, 318, 1044, 636, "#080808", 1.f, D);
    tracks(border, Json::array({rise, reveal}));
    layers.push_back(std::move(border));

    Json photo = image("golden_gate_photo", asset("bridge_bw.png"), 496, 328, 1024, 616, D);
    tracks(photo, Json::array({rise, reveal}));
    layers.push_back(std::move(photo));

    Json mlb_box = panel("mlb_box", 408, 371, 112, 58, "#080808", 1.f, D);
    tracks(mlb_box, Json::array({rise, reveal}));
    layers.push_back(std::move(mlb_box));
    Json mlb = textLayer("mlb_text", "MLB", 464, 400, 26, kFontBold, "#F4F3EF", D,
                         0.f, -1, 1.f, "mm");
    tracks(mlb, Json::array({rise, reveal}));
    layers.push_back(std::move(mlb));

    for (const Json& layer : sWatermark(D)) layers.push_back(layer);
    return renderPlan("web_ref_bridge_collage_v1", D, layers, staticCamera());
}

// ── 5. Book page with progressive highlighter ───────────────────────────────
Json buildBookHighlight(int D) {
    // Macro crop: page, marker and text share one 2.2x transform, so the
    // paragraph fills ~77% of the frame, the adjoining column's clipped
    // letters stay visible at the left edge, and the grey continuation shows
    // at the bottom. Offsets centre line 1 in the 1920 px frame.
    constexpr float S = 2.2f;
    constexpr float OX = -162.f;
    constexpr float OY = -96.f;
    const int pw = static_cast<int>(1920.f * S);
    const int ph = static_cast<int>(1080.f * S);

    Json layers = Json::array();
    Json page = image("book_page", asset("book_page_base.png"), OX, OY, pw, ph, D);
    layers.push_back(std::move(page));

    // FreeSerif 48: line 1 is 671.81 px, "wealth," is 135.12 px. Bands are
    // ~1.25x the scaled cap height and overhang the run slightly.
    constexpr float kBand = 39.f * S;
    layers.push_back(marker("book_marker_line_1", "marker_book_1.png",
                            OX + 168.f * S, OY + 177.f * S + 10.f,
                            671.81f * S + 30.f, kBand, 40, 66, D));
    layers.push_back(marker("book_marker_wealth", "marker_book_2.png",
                            OX + 168.f * S, OY + 247.f * S + 10.f,
                            135.12f * S + 25.f, kBand, 108, 26, D));

    // Active black paragraph above the bands: the highlighter cannot tint it.
    Json text = image("book_text", asset("book_text.png"), OX, OY, pw, ph, D);
    layers.push_back(std::move(text));
    return liftAbove(renderPlan("web_ref_book_highlight_v1", D, layers, staticCamera()),
                     "book_text");
}

}  // namespace

const char* paperReferenceName(PaperReferenceRecipe recipe) {
    switch (recipe) {
        case PaperReferenceRecipe::NewspaperTilt: return "web_ref_newspaper_tilt";
        case PaperReferenceRecipe::TornStrip: return "web_ref_torn_strip";
        case PaperReferenceRecipe::BlurredEvidence: return "web_ref_blurred_evidence";
        case PaperReferenceRecipe::BridgeCollage: return "web_ref_bridge_collage";
        case PaperReferenceRecipe::BookHighlight: return "web_ref_book_highlight";
    }
    return "unknown";
}

std::array<PaperReferenceRecipe, 5> allPaperReferenceRecipes() {
    return {PaperReferenceRecipe::NewspaperTilt, PaperReferenceRecipe::TornStrip,
            PaperReferenceRecipe::BlurredEvidence, PaperReferenceRecipe::BridgeCollage,
            PaperReferenceRecipe::BookHighlight};
}

void PaperReferenceSpec::validate() const {
    if (fps != 30) fail("fps must be 30");
    if (durationFrames < 30 || durationFrames > 300)
        fail("durationFrames must be in [30,300] (max 10 s at 30 fps)");
    if (outputName.find('\n') != std::string::npos)
        fail("outputName must be a single line");
}

std::string PaperReferenceSpec::planName() const {
    return std::string(paperReferenceName(recipe)) + "_v1";
}

std::string PaperReferenceSpec::outputStem() const {
    return outputName.empty() ? planName() + ".mp4" : outputName;
}

nlohmann::json buildPaperReferencePlan(const PaperReferenceSpec& spec) {
    spec.validate();
    const int duration = spec.durationFrames;
    Json plan;
    switch (spec.recipe) {
        case PaperReferenceRecipe::NewspaperTilt:
            plan = buildNewspaperTilt(duration);
            break;
        case PaperReferenceRecipe::TornStrip:
            plan = buildTornStrip(duration);
            break;
        case PaperReferenceRecipe::BlurredEvidence:
            plan = buildBlurredEvidence(duration);
            break;
        case PaperReferenceRecipe::BridgeCollage:
            plan = buildBridgeCollage(duration);
            break;
        case PaperReferenceRecipe::BookHighlight:
            plan = buildBookHighlight(duration);
            break;
    }
    // Image and shape albedo is lit by this rig. Without it the renderer's
    // default lighting multiplies paper and markers by roughly 0.48.
    plan["lighting_rig"] = Json{
        {"key_direction", Json::array({0.0f, 0.0f, 1.0f})},
        {"key_intensity", 0.0f},
        {"key_color", Json::array({1.0f, 1.0f, 1.0f, 1.0f})},
        {"ambient_intensity", 1.0f},
        {"ambient_color", Json::array({1.0f, 1.0f, 1.0f, 1.0f})},
        {"rim_enabled", false},
        {"rim_intensity", 0.0f},
        {"rim_power", 1.0f},
        {"rim_color", Json::array({1.0f, 1.0f, 1.0f, 1.0f})}};
    plan["job_id"] = spec.planName();
    plan["output"] = Json{{"path", spec.outputStem()}, {"format", "mp4"},
                          {"codec", "h264"}};
    return plan;
}

}  // namespace chronontemplate::web
