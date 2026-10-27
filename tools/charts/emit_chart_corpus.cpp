#include "chronontemplate/charts/ChartsPack.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"
#include <nlohmann/json.hpp>

#include <filesystem>
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;

namespace {
    constexpr int kFrames = 120;
    constexpr float kFps = 30.f;

    struct AssetBackend {
        std::uint64_t nextWireId{1};
        std::unordered_map<ContentId, std::string> fingerprints;

        ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
            ContentHandle h;
            h.id = std::move(id);
            h.wireId = nextWireId++;
            h.kind = kind;
            h.metrics.naturalSize = size;
            h.metrics.anchor = {0.5f, 0.5f};
            h.metrics.fingerprint = "chronontemplate-charts-test-v1:" + h.id;
            fingerprints.emplace(h.id, h.metrics.fingerprint);
            return h;
        }
        ContentHandle text(const TextRequest& r) {
            return make("text/" + r.text, ContentKind::Text,
                        {r.fontSize * (static_cast<float>(r.text.size()) * 0.75f + 0.75f),
                         r.fontSize * 1.4f});
        }
        ContentHandle image(const ImageRequest& r) { return make(r.path, ContentKind::Image, {1920.f, 1080.f}); }
        ContentHandle video(const VideoRequest& r) { return make(r.path, ContentKind::Video, {1920.f, 1080.f}); }
        ContentHandle shape(const ShapeRequest& r) { return make("shape/" + r.name, ContentKind::Image, r.size); }
        std::string fingerprint(const ContentId& id) const {
            const auto it = fingerprints.find(id);
            return it == fingerprints.end() ? std::string{} : it->second;
        }
    };

    ChartDatum point(std::string label, double value, std::string period = {},
                     ChartQualifier qualifier = ChartQualifier::Exact,
                     std::string display = {}) {
        ChartDatum d;
        d.label = std::move(label);
        d.period = std::move(period);
        d.value = value;
        d.qualifier = qualifier;
        d.displayValue = std::move(display);
        return d;
    }

    struct Case {
        int id;
        std::string slug;
        std::string title;
        std::string decision;
        std::string note;
        std::optional<ChartSpec> chart;
        bool missingOriginalValues{false};
        std::string dataProvenance{"provided_by_test_spec"};
        std::vector<std::pair<std::string, std::string>> editorialFacts{};
    };

    ChartSpec chart(ChartStyle style, std::string title, std::string unit,
                    std::vector<ChartDatum> data) {
        ChartSpec spec;
        spec.style = style;
        spec.title = std::move(title);
        spec.unit = std::move(unit);
        spec.data = std::move(data);
        spec.duration = kFrames;
        return spec;
    }

    std::vector<Case> corpus() {
        using S = ChartStyle;
        using Q = ChartQualifier;
        std::vector<Case> c;
        auto addChart = [&](int id, std::string slug, std::string title, std::string decision,
                            std::string note, ChartSpec spec, bool missing = false,
                            std::string provenance = "provided_by_test_spec") {
            spec.name = "test_" + (id < 10 ? std::string("0") : std::string{}) + std::to_string(id);
            c.push_back({id, std::move(slug), std::move(title), std::move(decision),
                         std::move(note), std::move(spec), missing, std::move(provenance)});
        };
        auto addNo = [&](int id, std::string slug, std::string title, std::string note,
                         std::vector<std::pair<std::string, std::string>> facts = {},
                         std::string provenance = "provided_by_test_spec") {
            c.push_back({id, std::move(slug), std::move(title), "NO", std::move(note), std::nullopt,
                         false, std::move(provenance), std::move(facts)});
        };

        addChart(1, "technical-reports", "Segnalazioni dei tecnici", "CHART",
                 "Tecnici 42% · controllo 18%",
                 chart(S::DualComparisonBars, "Segnalazioni dei tecnici", "%",
                       {point("Tecnici", 42), point("Controllo", 18)}));
        c.back().chart->scaleMax = 100.;
        addChart(2, "technicians-control", "Tecnici contro controllo", "CHART",
                 "Confronto percentuale: 42% contro 18%",
                 chart(S::DualComparisonBars, "Tecnici contro controllo", "%",
                       {point("Tecnici", 42), point("Controllo", 18)}));
        c.back().chart->scaleMax = 100.;
        c.back().chart->comparisonCards = true;
        c.back().chart->comparisonCallout = "24 punti percentuali di differenza";
        addChart(3, "ford-toyota", "Ford contro Toyota", "CHART",
                 "Vendite di veicoli: confronto fra Ford e Toyota.",
                 chart(S::DualComparisonBars, "Vendite di veicoli", "veicoli",
                       {point("Ford", 800000), point("Toyota", 1200000)}));
        c.back().chart->scaleMax = 1200000.;

        addChart(4, "revenue-growth", "Crescita dei ricavi", "CHART",
                 "Ricavi annuali: 20, 27 e 35 M€ nel 2022–2024.",
                 chart(S::TimelineGrowth, "Ricavi · milioni di euro", "M€",
                       {point("Ricavi", 20, "2022"), point("Ricavi", 27, "2023"), point("Ricavi", 35, "2024")}));
        c.back().chart->scaleMax = 40.;
        addChart(5, "market-shares", "Quote di mercato", "CHART",
                 "Alfa 35%, Beta 25%, Gamma 15%: residuo non classificato 25%.",
                 chart(S::RankedBars, "Quote di mercato · resto non classificato", "%",
                       {point("Alfa", 35), point("Beta", 25), point("Gamma", 15)}));
        c.back().chart->scaleMax = 100.;
        c.back().chart->note = "Resto del mercato non classificato: 25%";
        addChart(6, "exports-country", "Esportazioni per paese", "CHART",
                 "Esportazioni per paese nel 2025, in miliardi di euro.",
                 chart(S::RankedBars, "Esportazioni per paese · 2025", "mld €",
                       {point("Germania", 15), point("Francia", 12), point("Spagna", 9)}));
        c.back().chart->scaleMax = 20.;
        addNo(7, "single-percent", "Avanzamento progetti", "Scheda percentuale singola.",
              {{"42%", "progetti completati"}}, "synthetic_context_for_user_provided_42_percent");
        addNo(8, "single-count", "Nuove assunzioni", "", {{"150", "ingegneri assunti"}});
        addNo(9, "clients-budget", "Due indicatori distinti", "",
              {{"42%", "clienti"}, {"18%", "budget"}});
        addNo(10, "percentage-amount", "Risultati e investimento", "",
              {{"12%", "tasso di conversione"}, {"250.000 €", "investimento"}},
              "synthetic_fixture_created_at_user_request");
        addNo(11, "flight-card", "Dettagli del volo", "",
              {{"AZ 421", "volo"}, {"Terminal 3", "partenza"}, {"18 SET 2025", "data · esempio"}},
              "synthetic_date_fixture_created_at_user_request");
        addNo(12, "artifact-timeline", "Il reperto nel tempo", "",
              {{"2007", "reperto acquisito"}, {"2026", "nuova valutazione"}});
        addNo(13, "event-timeline", "Due momenti della vicenda", "",
              {{"14 GIU 2019", "apertura del dossier"}, {"03 MAG 2024", "verifica sul campo"}},
              "synthetic_event_fixture_created_at_user_request");
        addNo(14, "editorial-top-five", "Cinque temi in classifica", "",
              {{"01", "Documentari"}, {"02", "Tecnologia"}, {"03", "Sport"},
               {"04", "Storia"}, {"05", "Scienza"}},
              "synthetic_list_fixture_created_at_user_request");
        addNo(15, "independent-populations", "Due popolazioni, due misure", "",
              {{"42%", "residenti che usano il servizio"}, {"18%", "imprese che investono"}},
              "synthetic_fixture_created_at_user_request");
        addNo(16, "retracted-claim", "Affermazione smentita", "",
              {{"500 contro 300", "confronto dichiarato · SMENTITO"}});

        auto optimistic = point("Ottimistico", 30, {}, Q::Hypothetical, "30 M€");
        auto prudent = point("Prudente", 18, {}, Q::Hypothetical, "18 M€");
        addChart(17, "scenario-split", "Due scenari ipotetici", "COND",
                 "Previsioni ipotetiche di ricavi per il 2027.",
                 chart(S::ScenarioSplit, "Previsioni ricavi 2027", "M€", {optimistic, prudent}));
        c.back().chart->note = "SCENARI IPOTETICI · non sono risultati osservati";
        addChart(18, "qualified-growth", "Crescita qualificata", "COND",
                 "2022 · circa 200 dipendenti; 2024 · oltre 350.",
                 chart(S::QualifiedGrowth, "Dipendenti", "dipendenti",
                       {point("Dipendenti", 200, "2022", Q::Approximate),
                        point("Dipendenti", 350, "2024", Q::GreaterThan)}));
        c.back().chart->note = "Crescita 2022–2024 · valori qualificati, senza incremento esatto";
        addChart(19, "unit-conversion", "Conversione delle unità", "COND",
                 "Percorso A: 2 km convertiti in 2.000 m; Percorso B: 1.500 m.",
                 chart(S::DualComparisonBars, "Confronto lunghezza percorsi", "m",
                       {point("Percorso A", 2000), point("Percorso B", 1500)}));
        c.back().chart->scaleMax = 2000.;
        c.back().chart->comparisonCallout = "500 m di differenza · derivato";
        c.back().chart->note = "A: 2 km convertiti in 2.000 m · scala comune in metri";
        c.back().chart->comparisonCallout = "500 m di differenza · derivato";

        ChartDatum missing;
        missing.label = "Dato non disponibile";
        missing.period = "2023";
        missing.qualifier = Q::Missing;
        addChart(21, "missing-period", "Dato mancante nel 2023", "COND",
                 "2022 = 100; 2023 = N/D; 2024 = 150. Nessuna linea attraversa il vuoto.",
                 chart(S::MissingDataTimeline, "Valori annuali", "unità",
                       {point("Unità", 100, "2022"), missing, point("Unità", 150, "2024")}));
        c.back().chart->scaleMax = 150.;
        c.back().chart->note = "2023 · dato non disponibile · nessuna interpolazione";
        addNo(20, "quantity-price", "Vendite e prezzo medio", "",
              {{"200", "prodotti venduti"}, {"35 €", "prezzo medio per prodotto"}});
        addNo(22, "not-chart-22", "Vendite", "", {{"+25%", "rispetto all’anno precedente"}});
        addNo(23, "not-chart-23", "La notizia è falsa", "",
              {{"Confronto Alfa/Beta", "affermazione smentita · nessun valore confermato"}});

        addChart(24, "energy-timeline", "Produzione energetica", "CHART",
                 "Valori indicati: 100, 125 e 140 GWh.",
                 chart(S::TimelineGrowth, "Produzione energetica", "GWh",
                       {point("Produzione", 100, "2022"), point("Produzione", 125, "2023"), point("Produzione", 140, "2024")}));
        c.back().chart->scaleMax = 150.;
        c.back().chart->note = "GWh · scala da zero · 2022–2024";
        ChartSpec preference = chart(S::DualComparisonBars, "Preferenze", "%",
                                     {point("Opzione A", 48), point("Opzione B", 32)});
        preference.scaleMax = 100.;
        preference.note = "Nel medesimo sondaggio · scala 0–100%";
        addChart(25, "preferences", "Preferenze", "CHART", "48% contro 32%.", std::move(preference));
        addNo(26, "different-currencies", "Importi citati in valute diverse", "",
              {{"10 M$", "Alfa · dollari"}, {"9 M€", "Beta · euro"}},
              "synthetic_currency_fixture_created_at_user_request");
        addChart(27, "unspecified-remainder", "Confronto con residuo ignoto", "COND",
                 "A = 40%; B = 35%. Resto delle risposte non specificato.",
                 chart(S::DualComparisonBars, "Risposte: A e B", "%",
                       {point("A", 40), point("B", 35)}));
        c.back().chart->scaleMax = 100.;
        c.back().chart->note = "Altre risposte non specificate";
        ChartDatum bounded;
        bounded.label = "Costo previsto";
        bounded.lower = 10.;
        bounded.upper = 15.;
        bounded.qualifier = Q::Range;
        ChartSpec range = chart(S::BoundedRangeComparison, "Costo previsto e budget", "M€",
                                {bounded, point("Budget iniziale", 8)});
        range.scaleMax = 20.;
        addChart(28, "bounded-range", "Intervallo previsto contro budget", "COND",
                 "Previsione 10–15 M€; budget iniziale 8 M€.",
                 std::move(range));
        addChart(29, "before-after-40-55", "Vendite", "CHART",
                 "40 → 55; +37,5% è un valore derivato dai dati e resta distinto.",
                 chart(S::BeforeAfterMetric, "Vendite · unità", "unità vendute",
                       {point("Vendite", 40, "2023"), point("Vendite", 55, "2024")}));
        addNo(30, "documents-population", "Due informazioni distinte", "",
              {{"Documenti", "conteggio di un archivio"}, {"Popolazione", "numero di persone · metrica separata"}});
        addChart(31, "incidents-zero", "Incidenti per periodo", "CHART",
                 "Sequenza esatta: 0, 3, 1 incidenti. Lo zero resta a zero.",
                 chart(S::TimelineGrowth, "Incidenti per anno", "incidenti",
                       {point("Incidenti", 0, "2022"), point("Incidenti", 3, "2023"), point("Incidenti", 1, "2024")}));
        c.back().chart->scaleMax = 3.;
        c.back().chart->timelineBars = true;
        ChartSpec segmented = chart(S::SegmentedTotalBar, "Esito di 200 richieste", "richieste",
                                    {point("Approvate", 120), point("Respinte", 80)});
        segmented.total = 200.;
        addChart(32, "segmented-total", "Esito di 200 richieste", "CHART", "120 approvate e 80 respinte.",
                 std::move(segmented));
        addChart(33, "annual-cost", "Costo annuale", "COND",
                 "A: 20 €/mese → 240 €/anno · valori annualizzati sulla stessa scala.",
                 chart(S::DualComparisonBars, "Costo annuale", "€/anno",
                       {point("A", 240), point("B", 150)}));
        c.back().chart->note = "A: 20 €/mese → 240 €/anno · poi confronto sulla stessa scala";
        c.back().chart->comparisonCallout = "90 €/anno di differenza · derivato";
        c.back().chart->sequentialComparison = true;
        addChart(34, "before-after-80-95", "Ricavi", "CHART",
                 "Ricavi: 80 → 95 milioni di euro.",
                 chart(S::BeforeAfterMetric, "Ricavi · milioni di euro", "M€",
                       {point("Ricavi", 80, "2023"), point("Ricavi", 95, "2024")}));
        addChart(35, "before-after-units", "Pezzi prodotti", "CHART",
                 "2023 → 2024 · 100.000 → 120.000 pezzi.",
                 chart(S::DualComparisonBars, "Produzione · pezzi", "pezzi",
                       {point("2023", 100000), point("2024", 120000)}));
        c.back().chart->scaleMax = 120000.;
        c.back().chart->comparisonCallout = "+20% · incremento derivato";
        addNo(36, "unverified-data", "Valori citati nel rapporto", "",
              {{"“Vendite raddoppiate”", "citazione riportata · dati non verificati"}},
              "synthetic_claim_fixture_created_at_user_request");

        std::sort(c.begin(), c.end(), [](const Case& a, const Case& b) { return a.id < b.id; });
        if (c.size() != 36) throw std::logic_error("chart corpus must contain exactly 36 cases");
        return c;
    }

    const char* chartStyleName(ChartStyle style) {
        switch (style) {
            case ChartStyle::DualComparisonBars: return "dual_comparison_bars";
            case ChartStyle::TimelineGrowth: return "timeline_growth";
            case ChartStyle::RankedBars: return "ranked_bars";
            case ChartStyle::ScenarioSplit: return "scenario_split";
            case ChartStyle::BoundedRangeComparison: return "bounded_range_comparison";
            case ChartStyle::QualifiedGrowth: return "qualified_growth";
            case ChartStyle::MissingDataTimeline: return "missing_data_timeline";
            case ChartStyle::SegmentedTotalBar: return "segmented_total_bar";
            case ChartStyle::BeforeAfterMetric: return "before_after_metric";
        }
        return "unknown";
    }

    const char* qualifierName(ChartQualifier qualifier) {
        switch (qualifier) {
            case ChartQualifier::Exact: return "exact";
            case ChartQualifier::Approximate: return "approximate";
            case ChartQualifier::GreaterThan: return "greater_than";
            case ChartQualifier::Forecast: return "forecast";
            case ChartQualifier::Hypothetical: return "hypothetical";
            case ChartQualifier::Range: return "range";
            case ChartQualifier::Missing: return "missing";
        }
        return "unknown";
    }

    void writeDataManifest(const std::vector<Case>& cases, const std::filesystem::path& dir) {
        nlohmann::json manifest = {
                {"schema", "chronontemplate.charts.test-data.v1"},
                {"notice", "Synthetic values are labeled per test; they are fixtures, not observed facts."},
                {"tests", nlohmann::json::array()}};
        for (const Case& item : cases) {
            nlohmann::json entry = {
                    {"id", item.id}, {"title", item.title}, {"decision", item.decision},
                    {"data_provenance", item.dataProvenance}, {"note", item.note}};
            if (item.chart) {
                const ChartSpec& spec = *item.chart;
                nlohmann::json chartData = {
                        {"style", chartStyleName(spec.style)}, {"title", spec.title},
                        {"timeline_bars", spec.timelineBars}, {"sequential_comparison", spec.sequentialComparison},
                        {"unit", spec.unit}, {"scale_min", spec.scaleMin ? nlohmann::json(*spec.scaleMin) : nlohmann::json(nullptr)},
                        {"scale_max", spec.scaleMax ? nlohmann::json(*spec.scaleMax) : nlohmann::json(nullptr)},
                        {"total", spec.total ? nlohmann::json(*spec.total) : nlohmann::json(nullptr)},
                        {"note", spec.note}, {"comparison_cards", spec.comparisonCards},
                        {"comparison_callout", spec.comparisonCallout}, {"data", nlohmann::json::array()}};
                for (const ChartDatum& datum : spec.data) {
                    chartData["data"].push_back({
                            {"label", datum.label}, {"period", datum.period}, {"unit", datum.unit},
                            {"value", datum.value ? nlohmann::json(*datum.value) : nlohmann::json(nullptr)},
                            {"lower", datum.lower ? nlohmann::json(*datum.lower) : nlohmann::json(nullptr)},
                            {"upper", datum.upper ? nlohmann::json(*datum.upper) : nlohmann::json(nullptr)},
                            {"qualifier", qualifierName(datum.qualifier)},
                            {"display_value", datum.displayValue}, {"source", datum.source}});
                }
                entry["chart"] = std::move(chartData);
            } else {
                entry["chart"] = nullptr;
            }
            entry["editorial_facts"] = nlohmann::json::array();
            for (const auto& fact : item.editorialFacts)
                entry["editorial_facts"].push_back({{"value_or_date", fact.first}, {"description", fact.second}});
            manifest["tests"].push_back(std::move(entry));
        }
        const auto output = dir / "test_data.json";
        std::ofstream file(output, std::ios::binary | std::ios::trunc);
        if (!file || !(file << manifest.dump(2) << '\n'))
            throw std::runtime_error("could not write " + output.string());
    }

    void addNonChartScene(TemplateScene& scene, const Case& item, int frames) {
        const Vector2 canvas(1920.f, 1080.f);
        auto& bg = scene.shape(ShapeSpec{.size = canvas, .fillColor = "#0B1220", .name = "editorial-background"});
        bg.position(960.f, 540.f).alive(0, frames - 1);
        auto addText = [&](std::string content, float x, float y, float size,
                           std::string color, std::string name, int at) {
            auto& layer = scene.text(TextSpec{.text = std::move(content), .font = "assets/fonts/Inter-SemiBold.ttf",
                                               .fontSize = size, .color = std::move(color), .name = std::move(name)});
            layer.position(x, canvas.y - y, 0.f).alive(0, frames - 1).animate(FadeIn{at, 18});
        };
        auto addPanel = [&](float x, float y, float w, float h, std::string name, std::string color = "#17233A") {
            auto& panel = scene.shape(ShapeSpec{.size = Vector2(w, h), .fillColor = std::move(color),
                                                .name = std::move(name), .cornerRadius = std::min(w, h) * 0.06f});
            panel.position(x, canvas.y - y, 0.f).alive(0, frames - 1).animate(FadeIn{8, 18});
        };
        addText(item.title, 960.f, 135.f, 58.f, "#F4F7FC", "editorial-title", 0);
        if (item.dataProvenance.find("synthetic") != std::string::npos) {
            addPanel(1630.f, 135.f, 205.f, 64.f, "synthetic-badge", "#4B351E");
            addText("ESEMPIO", 1630.f, 145.f, 25.f, "#FFD59B", "synthetic-label", 8);
        }

        auto addFactCard = [&](std::size_t index, float x, float y, float w, float h,
                               float valueSize, float labelSize, std::string name) {
            const auto& fact = item.editorialFacts[index];
            addPanel(x, y, w, h, name + "-panel", index % 2 == 0 ? "#162544" : "#1B2940");
            addText(fact.first, x, y - h * 0.13f, valueSize, "#FFFFFF", name + "-value", 14 + static_cast<int>(index) * 5);
            addText(fact.second, x, y + h * 0.18f, labelSize, "#B9C9E2", name + "-label", 24 + static_cast<int>(index) * 5);
        };

        if (item.id == 20 && item.editorialFacts.size() == 2) {
            const auto& first = item.editorialFacts[0];
            const auto& second = item.editorialFacts[1];
            addText(first.first, 960.f, 465.f, 170.f, "#FFFFFF", "products-sold-value", 10);
            addText(first.second, 960.f, 595.f, 46.f, "#B9C9E2", "products-sold-label", 25);
            addText(second.first, 960.f, 760.f, 115.f, "#F2A56B", "average-price-value", 42);
            addText(second.second, 960.f, 875.f, 42.f, "#B9C9E2", "average-price-label", 54);
            return;
        }
        if (item.id == 11 && item.editorialFacts.size() == 3) {
            addFactCard(0, 350.f, 560.f, 500.f, 430.f, 69.f, 36.f, "flight-code");
            addFactCard(1, 960.f, 560.f, 500.f, 430.f, 66.f, 36.f, "flight-terminal");
            addFactCard(2, 1570.f, 560.f, 500.f, 430.f, 60.f, 34.f, "flight-date");
            return;
        }
        if ((item.id == 12 || item.id == 13) && item.editorialFacts.size() == 2) {
            auto& timeline = scene.shape(ShapeSpec{.size = Vector2(1160.f, 8.f), .fillColor = "#536B99",
                                                    .name = "event-timeline"});
            timeline.position(960.f, canvas.y - 555.f, 0.f).alive(0, frames - 1).animate(FadeIn{12, 20});
            for (std::size_t i = 0; i < 2; ++i) {
                const float x = i == 0 ? 550.f : 1370.f;
                auto& node = scene.shape(ShapeSpec{.size = Vector2(34.f, 34.f), .fillColor = i == 0 ? "#73A2FF" : "#F2A56B",
                                                   .name = "event-node-" + std::to_string(i),
                                                   .geometry = ShapeGeometry::Ellipse});
                node.position(x, canvas.y - 555.f, 0.f).alive(0, frames - 1).animate(FadeIn{18 + static_cast<int>(i) * 24, 14});
                addText(item.editorialFacts[i].first, x, 425.f, 48.f, "#FFFFFF", "event-date-" + std::to_string(i),
                        24 + static_cast<int>(i) * 24);
                addPanel(x, 720.f, 600.f, 190.f, "event-card-" + std::to_string(i), "#17233A");
                addText(item.editorialFacts[i].second, x, 725.f, 31.f, "#D7E3F4", "event-description-" + std::to_string(i),
                        32 + static_cast<int>(i) * 24);
            }
            return;
        }
        if (item.id == 14 && item.editorialFacts.size() == 5) {
            for (std::size_t i = 0; i < item.editorialFacts.size(); ++i) {
                const float y = 280.f + static_cast<float>(i) * 150.f;
                addPanel(960.f, y, 1260.f, 112.f, "ranked-row-" + std::to_string(i),
                         i == 0 ? "#233C68" : "#17233A");
                addText(item.editorialFacts[i].first, 460.f, y, 38.f, "#F2A56B", "rank-" + std::to_string(i), 12 + static_cast<int>(i) * 9);
                addText(item.editorialFacts[i].second, 1010.f, y, 39.f, "#FFFFFF", "rank-item-" + std::to_string(i), 18 + static_cast<int>(i) * 9);
            }
            return;
        }
        if (item.id == 16 || item.id == 23 || item.id == 36) {
            addPanel(960.f, 565.f, 1500.f, 480.f, "fact-check-card", "#17233A");
            addText(item.editorialFacts.front().first, 960.f, 490.f, 59.f, "#FFFFFF", "fact-check-claim", 16);
            const std::string status = item.editorialFacts.front().second;
            addText(status, 960.f, 665.f, 42.f, "#FFB36B", "fact-check-status", 34);
            return;
        }
        if (item.editorialFacts.size() == 1) {
            addFactCard(0, 960.f, 565.f, 1320.f, 500.f, 180.f, 49.f, "hero-stat");
            return;
        }
        if (item.id == 30 && item.editorialFacts.size() == 2) {
            for (std::size_t i = 0; i < 2; ++i) {
                const float y = i == 0 ? 460.f : 690.f;
                addText(item.editorialFacts[i].first, 480.f, y, 54.f, i == 0 ? "#73A2FF" : "#F2A56B",
                        "separate-topic-" + std::to_string(i), 14 + static_cast<int>(i) * 28);
                addText(item.editorialFacts[i].second, 1080.f, y, 43.f, "#FFFFFF",
                        "separate-description-" + std::to_string(i), 22 + static_cast<int>(i) * 28);
            }
            return;
        }
        if (item.editorialFacts.size() == 2) {
            const float w = 700.f;
            addFactCard(0, 600.f, 570.f, w, 440.f, 106.f, 37.f, "fact-a");
            addFactCard(1, 1320.f, 570.f, w, 440.f, 106.f, 37.f, "fact-b");
            return;
        }
        addText(item.note, 960.f, 600.f, 40.f, "#D7E3F4", "editorial-copy", 18);
    }

    void emit(const Case& item, const std::filesystem::path& dir) {
        AssetBackend assets;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& r) { return assets.text(r); },
            .createImage = [&](const ImageRequest& r) { return assets.image(r); },
            .createVideo = [&](const VideoRequest& r) { return assets.video(r); },
            .createShape = [&](const ShapeRequest& r) { return assets.shape(r); },
            .currentFingerprint = [&](const ContentId& id) { return assets.fingerprint(id); }});
        const std::string id = "test_" + (item.id < 10 ? std::string("0") : std::string{}) +
                               std::to_string(item.id) + "_" + item.slug;
        TemplateScene scene(id, kFps, host, 1920.f, 1080.f);
        // Fit the 1920×1080 pixel-space composition into Chronon's perspective
        // camera at the default 1080-unit depth.
        scene.camera().setFov(55.f);
        if (item.chart && !item.missingOriginalValues) {
            ChartSpec spec = *item.chart;
            spec.inFrame = 0;
            spec.duration = kFrames;
            (void)addChart(scene, spec);
        } else {
            addNonChartScene(scene, item, kFrames);
        }
        if (!scene.validate().empty())
            throw std::runtime_error(id + ": " + scene.validate().front());
        auto plan = lowerToRenderPlan(scene, host, id, id + ".mp4");
        auto document = nlohmann::json::parse(renderPlanToJson(plan));
        // The C++ emitter bakes the camera statically for these flat 2D charts.
        // The legacy Motion lowering serializes redundant per-frame camera
        // tracks; Chronon now consumes resolved camera_samples instead.
        document.erase("camera_animation");
        // lowerToRenderPlan defaults to PNG even when outputPath has an MP4
        // extension. State the video contract explicitly so Chronon builds
        // the compatibility export view and takes its real video render lane.
        document["output"]["format"] = "mp4";
        document["output"]["codec"] = "h264";
        const auto output = dir / (id + ".plan.json");
        std::ofstream file(output, std::ios::binary | std::ios::trunc);
        if (!file || !(file << document.dump(2) << '\n'))
            throw std::runtime_error("could not write " + output.string());
        std::cout << "emitted " << id << (item.missingOriginalValues ? " (source values missing)" : "") << '\n';
    }
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_emit_chart_corpus <plans-directory>\n";
        return 2;
    }
    try {
        const std::filesystem::path output(argv[1]);
        std::filesystem::create_directories(output);
        const auto cases = corpus();
        writeDataManifest(cases, output);
        for (const auto& item : cases) emit(item, output);
    } catch (const std::exception& e) {
        std::cerr << "chart corpus emission failed: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
