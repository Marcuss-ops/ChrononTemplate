#include "chronontemplate/web/WebTextLayout.hpp"
#include "chronontemplate/web/ArticleEvidenceReveal.hpp"
#include "chronontemplate/web/WebPageHighlightPack.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>

using namespace chronontemplate::web;

namespace {

std::optional<chronon3d::GlyphRun> mockShape(std::string_view text) {
    chronon3d::GlyphRun run;
    run.ascent = 9.f;
    run.descent = 3.f;
    run.line_height = 15.f;
    float x = 0.f;
    for (std::size_t i = 0; i < text.size();) {
        const auto lead = static_cast<unsigned char>(text[i]);
        const std::size_t bytes = lead < 0x80 ? 1 : (lead & 0xe0) == 0xc0 ? 2 :
                                  (lead & 0xf0) == 0xe0 ? 3 : 4;
        chronon3d::GlyphPosition glyph;
        glyph.glyph_id = 1;
        glyph.x = x;
        glyph.advance_x = 10.f;
        glyph.cluster = static_cast<chronon3d::u32>(i);
        glyph.is_cluster_start = true;
        run.glyphs.push_back(glyph);
        x += 10.f;
        i += bytes;
    }
    run.width = x;
    return run;
}

void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}

} // namespace

int main() {
    try {
        const std::string text = "Le caffè rivela che circa l'80% dei visitatori viene appositamente per vedere il dipinto.";
        const auto first = layoutWebText(text, 120.f, 300.f, 170.f, 19.f,
                                         "assets/fonts/Inter-Regular.ttf", 21.f, mockShape);
        const auto second = layoutWebText(text, 120.f, 300.f, 170.f, 19.f,
                                          "assets/fonts/Inter-Regular.ttf", 21.f, mockShape);
        require(first.lines.size() > 2, "long paragraph wraps into physical lines");
        require(first.lines.size() == second.lines.size(), "layout is deterministic");
        for (std::size_t i = 0; i < first.lines.size(); ++i) {
            require(first.lines[i].text == second.lines[i].text, "deterministic line text");
            require(first.lines[i].width <= 170.f, "exact shaped width stays within column");
        }

        const std::string phrase = "appositamente per vedere il dipinto";
        const auto start = text.find(phrase);
        const auto segments = resolveWebTextSpan(first, start, start + phrase.size());
        require(segments.size() >= 3, "wrapped phrase resolves to three distinct line segments");
        for (const auto& segment : segments) {
            require(segment.width > 0.f && segment.height == 12.f, "segments use shaped glyph geometry");
            require(segment.x >= 120.f && segment.x + segment.width <= 290.f,
                    "highlight geometry stays inside its text column");
        }

        const std::string accented = "caffè";
        const auto accentedStart = text.find(accented);
        const auto accentedSegments = resolveWebTextSpan(first, accentedStart,
                                                          accentedStart + accented.size());
        require(accentedSegments.size() == 1, "UTF-8 accent remains within its shaped cluster range");
        const auto oneLine = resolveWebTextSpan(first, accentedStart, accentedStart + accented.size());
        require(oneLine.size() == 1, "single-line highlight resolves to one segment");

        bool rejectsBadBoundary = false;
        try {
            (void)resolveWebTextSpan(first, accentedStart + 5, accentedStart + accented.size());
        } catch (const std::invalid_argument&) { rejectsBadBoundary = true; }
        require(rejectsBadBoundary, "invalid UTF-8 byte boundary fails closed");

        ArticleEvidenceSpec scene;
        scene.bodyText = "Le statistiche rivelano che circa l'80% dei visitatori viene appositamente per vedere il dipinto. "
                         "Il dato emerge dai registri e dalle interviste raccolte nell'archivio cittadino.";
        scene.highlightedPhrase = "viene appositamente per vedere il dipinto";
        scene.keyPoints = {"Il dato principale riguarda l'80% dei visitatori.",
                           "Le interviste confermano l'andamento osservato.",
                           "Il dipinto resta il motivo centrale della visita."};
        const auto sceneLayout = layoutWebText(scene.bodyText, 120.f, 300.f, 180.f, 19.f,
            "assets/fonts/Inter-Regular.ttf", 21.f, mockShape);
        const auto plan = buildArticleEvidenceRevealPlan(scene, sceneLayout);
        require(plan.at("canvas").at("width") == 1920 && plan.at("canvas").at("height") == 1080 &&
                    plan.at("canvas").at("fps_num") == 30 && plan.at("canvas").at("duration_frames") == 240,
                "article evidence scene has the requested 1080p eight-second format");
        require(plan.contains("camera") && plan.contains("camera_samples") &&
                    !plan.contains("camera_animation"),
                "camera push is present with the article composition");
        std::size_t markerCount = 0, pointCount = 0;
        for (const auto& layer : plan.at("layers")) {
            const std::string id = layer.at("id").get<std::string>();
            if (id.rfind("evidence_marker_", 0) == 0) ++markerCount;
            if (id.rfind("key_point_text_", 0) == 0) ++pointCount;
        }
        const auto phraseAt = scene.bodyText.find(scene.highlightedPhrase);
        const auto sceneSegments = resolveWebTextSpan(sceneLayout, phraseAt,
            phraseAt + scene.highlightedPhrase.size());
        require(markerCount == sceneSegments.size(), "each visual highlight line has an independent reveal layer");
        require(pointCount == 3, "three key points are emitted as separate native text layers");
        require(plan.at("layers").size() > sceneLayout.lines.size() + 10,
                "article, context blur, highlight, and three bullets compose in one plan");
        require(plan == buildArticleEvidenceRevealPlan(scene, sceneLayout), "the full plan is deterministic");

        WebPageHighlightSpec page;
        page.headlineLineOne = "Measured article layout";
        page.kicker = "EVIDENCE";
        page.bodyLines = {"legacy input replaced by shaped paragraph"};
        const auto exactPage = buildWebPageHighlightPlan(page, sceneLayout);
        const auto bodyLayer = std::find_if(exactPage.at("layers").begin(), exactPage.at("layers").end(),
            [](const auto& layer) { return layer.at("id") == "body_line_0"; });
        require(bodyLayer != exactPage.at("layers").end() &&
                    bodyLayer->at("text") == sceneLayout.lines[0].text &&
                    bodyLayer->at("position").at(0).get<float>() ==
                        sceneLayout.lines[0].x + (sceneLayout.lines[0].width + 2.f) * .5f,
                "existing web page pack consumes shared shaped text geometry");

        std::string longArticle;
        for (int i = 0; i < 400; ++i) {
            if (!longArticle.empty()) longArticle.push_back(' ');
            longArticle += (i % 2 == 0) ? "evidence" : "article";
        }
        const auto longLayout = layoutWebText(longArticle, 90.f, 300.f, 430.f, 20.f,
            "assets/fonts/Inter-Regular.ttf", 21.f, mockShape);
        std::string reconstructed;
        for (const auto& line : longLayout.lines) {
            if (!reconstructed.empty()) reconstructed.push_back(' ');
            reconstructed += line.text;
        }
        require(longLayout.lines.size() > 10 && reconstructed == longArticle,
                "400-word article wraps without dropping or duplicating text");
        std::cout << "web text layout tests passed\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
