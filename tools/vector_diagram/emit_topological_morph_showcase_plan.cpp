// emit_topological_morph_showcase_plan.cpp
// Generates chronon.render-plan.v3 for the Topological Morphing Showcase (Van -> Thermometer -> Sun -> Rocket)

#include <iostream>
#include <fstream>
#include <string>

int main() {
    std::string out_path = "C:/Users/pater/Pyt/ChrononTemplate/out/svg_parity/topological_morph_showcase.plan.json";

    std::ofstream f(out_path);
    if (!f.is_open()) {
        std::cerr << "Failed to open " << out_path << " for writing\n";
        return 1;
    }

    f << "{\n"
      << "  \"version\": \"chronon.render-plan.v3\",\n"
      << "  \"sequence_id\": \"topological_morphing_parity_showcase\",\n"
      << "  \"target_specs\": {\n"
      << "    \"width\": 1920,\n"
      << "    \"height\": 1080,\n"
      << "    \"frame_rate\": 60,\n"
      << "    \"duration_seconds\": 7.5,\n"
      << "    \"total_frames\": 450,\n"
      << "    \"color_space\": \"sRGB\",\n"
      << "    \"background_color\": \"#020408\"\n"
      << "  },\n"
      << "  \"topological_morpher\": {\n"
      << "    \"resampling_algorithm\": \"uniform_arc_length_lut\",\n"
      << "    \"common_topology_nodes\": 256,\n"
      << "    \"energy_solver\": \"euclidean_deformation_minimization_l2\",\n"
      << "    \"rotational_phase_alignment\": true,\n"
      << "    \"winding_rectification\": true\n"
      << "  },\n"
      << "  \"metamorphosis_stages\": [\n"
      << "    {\n"
      << "      \"stage\": 1,\n"
      << "      \"from\": { \"name\": \"delivery_van\", \"raw_vertices\": 26 },\n"
      << "      \"to\": { \"name\": \"clinical_thermometer\", \"raw_vertices\": 18 },\n"
      << "      \"time_span\": [0.5, 2.0],\n"
      << "      \"color_transition\": [\"#00F0FF\", \"#FF4D6D\"]\n"
      << "    },\n"
      << "    {\n"
      << "      \"stage\": 2,\n"
      << "      \"from\": { \"name\": \"clinical_thermometer\", \"raw_vertices\": 18 },\n"
      << "      \"to\": { \"name\": \"radiating_sun\", \"raw_vertices\": 32 },\n"
      << "      \"time_span\": [2.6, 4.1],\n"
      << "      \"color_transition\": [\"#FF4D6D\", \"#FFB703\"]\n"
      << "    },\n"
      << "    {\n"
      << "      \"stage\": 3,\n"
      << "      \"from\": { \"name\": \"radiating_sun\", \"raw_vertices\": 32 },\n"
      << "      \"to\": { \"name\": \"space_rocket\", \"raw_vertices\": 20 },\n"
      << "      \"time_span\": [4.7, 6.2],\n"
      << "      \"color_transition\": [\"#FFB703\", \"#7209B7\"]\n"
      << "    }\n"
      << "  ],\n"
      << "  \"visual_layers\": {\n"
      << "    \"inner_glow_sdf\": { \"enabled\": true, \"fill_opacity\": 0.15 },\n"
      << "    \"neon_rim\": { \"enabled\": true, \"stroke_width\": 3.5, \"bloom_intensity\": 1.4 },\n"
      << "    \"morph_vector_lattice\": { \"enabled\": true, \"sample_step\": 8, \"opacity\": 0.35 },\n"
      << "    \"telemetry_hud\": { \"enabled\": true, \"font\": \"monospace\", \"show_energy_metrics\": true }\n"
      << "  }\n"
      << "}\n";

    f.close();
    std::cout << "[SUCCESS] Emitted Topological Morph Plan: " << out_path << "\n";
    return 0;
}
