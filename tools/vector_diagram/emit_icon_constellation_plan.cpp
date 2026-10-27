// emit_icon_constellation_plan.cpp
// Generates chronon.render-plan.v3 for the 2.5D Icon Constellation video-essay animation.

#include <iostream>
#include <fstream>
#include <string>
#include <vector>

int main() {
    std::string out_path = "C:/Users/pater/Pyt/ChrononTemplate/out/svg_parity/icon_constellation_25d.plan.json";

    std::ofstream f(out_path);
    if (!f.is_open()) {
        std::cerr << "Failed to open " << out_path << " for writing\n";
        return 1;
    }

    f << "{\n"
      << "  \"version\": \"chronon.render-plan.v3\",\n"
      << "  \"sequence_id\": \"tech_space_icon_constellation_25d\",\n"
      << "  \"target_specs\": {\n"
      << "    \"width\": 1920,\n"
      << "    \"height\": 1080,\n"
      << "    \"frame_rate\": 60,\n"
      << "    \"duration_seconds\": 6.0,\n"
      << "    \"total_frames\": 360,\n"
      << "    \"color_space\": \"sRGB\",\n"
      << "    \"background_color\": \"#030508\"\n"
      << "  },\n"
      << "  \"camera\": {\n"
      << "    \"type\": \"perspective_2.5D\",\n"
      << "    \"focal_length\": 800.0,\n"
      << "    \"depth_of_field\": {\n"
      << "      \"enabled\": true,\n"
      << "      \"focus_distance\": 750.0,\n"
      << "      \"aperture\": 2.8,\n"
      << "      \"bokeh_shape\": \"circular\"\n"
      << "    },\n"
      << "    \"keyframe_path\": [\n"
      << "      { \"time\": 0.0, \"pos\": [960.0, 540.0, -420.0], \"look_at\": [960.0, 540.0, 0.0] },\n"
      << "      { \"time\": 2.2, \"pos\": [960.0, 540.0, -450.0], \"look_at\": [960.0, 540.0, 0.0] },\n"
      << "      { \"time\": 4.5, \"pos\": [1020.0, 510.0, -960.0], \"look_at\": [960.0, 540.0, 0.0] },\n"
      << "      { \"time\": 6.0, \"pos\": [1020.0, 510.0, -980.0], \"look_at\": [960.0, 540.0, 0.0] }\n"
      << "    ]\n"
      << "  },\n"
      << "  \"asset_catalog\": {\n"
      << "    \"icons_svg_base\": \"assets/icons/svg/\",\n"
      << "    \"icons_png_neon_base\": \"assets/icons/png_neon/\",\n"
      << "    \"icons_png_white_base\": \"assets/icons/png_white/\",\n"
      << "    \"nodes\": [\n"
      << "      { \"id\": \"core_cpu\", \"icon\": \"cpu\", \"layer\": \"core\", \"world_pos\": [960, 540, 0] },\n"
      << "      { \"id\": \"core_brain\", \"icon\": \"brain\", \"layer\": \"core\", \"world_pos\": [960, 540, -40] },\n"
      << "      { \"id\": \"tech_vulkan\", \"icon\": \"vulkan\", \"layer\": \"inner_ring\", \"world_pos\": [660, 360, 80] },\n"
      << "      { \"id\": \"tech_cpp\", \"icon\": \"cplusplus\", \"layer\": \"inner_ring\", \"world_pos\": [1260, 360, 80] },\n"
      << "      { \"id\": \"tech_db\", \"icon\": \"database\", \"layer\": \"inner_ring\", \"world_pos\": [680, 720, 50] },\n"
      << "      { \"id\": \"tech_shield\", \"icon\": \"shield\", \"layer\": \"inner_ring\", \"world_pos\": [1240, 720, 50] },\n"
      << "      { \"id\": \"space_globe\", \"icon\": \"globe\", \"layer\": \"outer_cosmos\", \"world_pos\": [1450, 480, 220] },\n"
      << "      { \"id\": \"space_satellite\", \"icon\": \"satellite\", \"layer\": \"orbit\", \"world_pos\": [1550, 280, 220] },\n"
      << "      { \"id\": \"space_rocket\", \"icon\": \"rocket\", \"layer\": \"deep_space\", \"world_pos\": [450, 220, 350] },\n"
      << "      { \"id\": \"sci_atom\", \"icon\": \"atom\", \"layer\": \"micro_cosmos\", \"world_pos\": [420, 800, 180] },\n"
      << "      { \"id\": \"sci_dna\", \"icon\": \"dna\", \"layer\": \"micro_cosmos\", \"world_pos\": [1480, 820, 150] },\n"
      << "      { \"id\": \"energy_zap\", \"icon\": \"zap\", \"layer\": \"energy\", \"world_pos\": [960, 220, 100] }\n"
      << "    ]\n"
      << "  },\n"
      << "  \"motion_tracks\": [\n"
      << "    { \"target\": \"core_cpu\", \"type\": \"scale_spring\", \"time_span\": [0.0, 1.2], \"from\": 0.0, \"to\": 0.38 },\n"
      << "    { \"target\": \"hud_rings\", \"type\": \"continuous_rotation\", \"speed_deg_per_sec\": 35.0 },\n"
      << "    { \"target\": \"axons\", \"type\": \"trim_path_laser\", \"time_span\": [0.8, 2.8], \"draw_fraction\": [0.0, 1.0] },\n"
      << "    { \"target\": \"space_rocket\", \"type\": \"bezier_trajectory\", \"time_span\": [2.0, 6.0] },\n"
      << "    { \"target\": \"space_satellite\", \"type\": \"elliptical_orbit\", \"speed\": 0.8 },\n"
      << "    { \"target\": \"camera_dolly\", \"type\": \"dolly_out_with_dof\", \"time_span\": [2.2, 5.0] }\n"
      << "  ],\n"
      << "  \"post_processing\": {\n"
      << "    \"multi_pass_bloom\": { \"enabled\": true, \"intensity\": 1.25, \"threshold\": 0.65 },\n"
      << "    \"analog_film_grain\": { \"enabled\": true, \"grain_opacity\": 0.04, \"dust_specks_count\": 80 },\n"
      << "    \"vignette\": { \"enabled\": true, \"radius\": 0.85, \"softness\": 0.45 }\n"
      << "  }\n"
      << "}\n";

    f.close();
    std::cout << "[SUCCESS] Emitted Icon Constellation Plan: " << out_path << "\n";
    return 0;
}
