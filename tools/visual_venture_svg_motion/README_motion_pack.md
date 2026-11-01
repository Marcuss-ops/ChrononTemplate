# Visual Venture motion pack

The pack contains ten documentary explainer scenes, eight reusable motion primitives, and three reference clips inspired by frames 0051–0065.

## 30-second story-led intro

`intro_10_real_secrets_30s.svg` is an editable 1920 × 1080 SVG with a timed SMIL storyboard. Its sequence is: Project Sunshine food-chain fallout and bone (0–5 s); a schematic San Francisco Bay map and dispersal cloud for Sea-Spray (5–10 s); the Goldsboro bomber, falling devices, and a safety-state dial (10–15 s); converging archival evidence sheets (15–21 s); a dominant centered title (21–26 s); and a line transition into the first story (26–30 s). No persistent upper-left heading.

The SVG includes a continuous path morph through isotope, bay, device, and dossier silhouettes. The 24 fps H.264 MP4 is rendered directly from the SVG timeline. The diagrams are illustrative, not archival reconstructions. The intro has no audio track. The standalone pack MP4 is `intro_10_real_secrets_narrative_final_30s.mp4`.

## Ten story scenes

`09_project_sunshine_food_chain`, `10_operation_sea_spray_dispersion`,
`11_project_shad_ship_scan`, `12_greenbrier_bunker_cutaway`,
`13_midnight_climax_surveillance`, `14_goldsboro_safety_sequence`,
`15_fernald_tracer_path`, `16_teapot_dome_money_flow`,
`17_operation_washtub_network`, and `18_soviet_alfa_cooling_loop`.

## Eight reusable primitives

`19_particle_flow`, `20_path_reveal`, `21_radar_scan`, `22_network_graph`,
`23_number_counter`, `24_shape_morph`, `25_document_reveal`, and
`26_signal_pulse`.

MP4s and matching SVGs are in `renders/` and
`assets/chronon_visual_venture_pack/`. See
`conspiracy_motion_pack_manifest.json` for the machine-readable asset list.

Run `python build_conspiracy_motion_pack.py` to rebuild the ten scenes and eight
primitives. Pass asset names as arguments to render selected clips. The three
reference clips can be rebuilt with `python render_svg_motion_mp4.py`.

## Drift placement

The intro is placed at 0 s on the top video track in `Cospirancy Theorie.drift`.
The ten story scenes start 10 seconds into their matching chapters; all eight
primitives follow in their corresponding topic sections.
