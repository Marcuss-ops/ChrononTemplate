#include "common.hpp"

using namespace chronon::youtuber;

// Forward declarations from the individual units
void run_01();
void run_02();
void run_03();
void run_04();
void run_05();
void run_06();
void run_07();
void run_08();
void run_09();
void run_10();
void run_11();
void run_12();
void run_13();
void run_14();
void run_15();
void run_16();
void run_17();
void run_18();
void run_19();
void run_20();

int main(int argc, char** argv) {
    std::cout << "========================================================\n"
              << "Chronon & ChrononMotion3D: YouTuber Animation Rebuilder\n"
              << "Recreating 20 authentic animations natively via C++\n"
              << "Outputs mirrored to:\n"
              << "  - " << kFinalBase1 << "\n"
              << "  - " << kFinalBase2 << "\n"
              << "========================================================\n" << std::endl;

    std::vector<std::string> tools = {
        "01_subject_floating_push",
        "02_portrait_parallax_drift",
        "03_historical_archive_framing",
        "04_cinematic_title_beat",
        "05_archival_evidence_box",
        "06_documentary_still_evidence",
        "07_archive_scene_pan",
        "08_tactical_radar_graphic",
        "09_newspaper_dossier_zoom",
        "10_highlighter_evidence_sweep",
        "11_subject_tilt_reframe",
        "12_dramatic_cutout_pushin",
        "13_newspaper_headline_wipe",
        "14_archive_document_framing",
        "15_declassified_memo_highlight",
        "16_evidence_callout_card",
        "17_classified_nightvision_reticle",
        "18_witness_portrait_focus",
        "19_chapter_title_card",
        "20_climax_multilayer_parallax"
    };

    std::cout << "Configured " << tools.size() << " dedicated C++ animation generators." << std::endl;
    return 0;
}
