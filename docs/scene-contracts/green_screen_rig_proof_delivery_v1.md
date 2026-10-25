# Green Screen Rig Proof Delivery v1

## Scene contracts

- **Head and bust:** green background, keyed Keanu portrait; rotate the complete head relative to a fixed torso around the upper-neck pivot. Hair, face, ears and jaw share the skull joint; neck vertices blend into a fixed torso root. No global translation or vertical bob. Preview evidence is a five-frame contact sheet over the full four-second motion.
- **Hand:** green background and a close crop of an articulated hand; finger joints flex closed and reopen while the wrist/forearm remains visible. Must not split at the joints. Source is the project’s UAL1 articulated gesture GLB.
- **Wave:** green background and a connected, rigged figure raising its arm in a greeting motion. This is a technical rig preview from the available UAL1 mannequin, not a celebrity likeness. The local photogrammetry celebrity GLB has visible shoulder gaps when posed and is not used for this preview.

## Outputs

Destination: `OneDrive/Documenti/Chronomotion/MP4/Youtuberstle/`

- `keanu_head_bust_joint_rig_v3.mp4` and `keanu_head_bust_joint_rig_v3_contact.png`
- The legacy `keanu_head_bust_rig_fixed_v2.mp4` and `keanu_head_bust_rig_v1.mp4` plus their contact sheets are replaced with this joint-driven render.
- `green_screen_hand_fingers_v1.mp4` and `green_screen_hand_fingers_v1_contact.png`
- `connected_rig_wave_mannequin_v1_zoomed.mp4` and `connected_rig_wave_mannequin_v1_zoomed_contact.png`

All MP4s are 1920×1080, 30 fps, 121 frames (4.03 s), H.264, green-screen background. The head scene uses the canonical ChrononMotion `RigProgramEvaluator` and `MotionSceneBridge` in the existing headless C++/threepp render path; FFmpeg encoded the frames. The wave delivery is cropped and upscaled from the 1920×1080 GLB render to make the rig readable.

## Visual and temporal review

- Contact sheets use frames 0, 30/45, 60/90, and 120 (hand uses frames 0, 45, 90, 120; wave uses 13 samples across the clip).
- Head frames 0/30/60/90/120 show the skull rotating about the upper-neck pivot: up to 3° yaw plus 0.8° roll, with the neck transition blending to torso weights. No translation channel is animated; shoulder/chest regions have zero changed pixels in the decoded MP4 between frames 0 and 30. At summed RGB threshold 18, decoded frame 0→30 changes 17,875 eye-region pixels, 8,005 nose-region pixels, 30,608 head-top pixels, and 135,803 face-region pixels. The rig returns to the original pose at frame 120.
- Hand frames show a direct C++ flex of the five finger bone chains and a return toward the open pose. The available hand asset is a stylized orange mannequin hand with purple joint bands, not a photoreal cutout.
- Wave uses the available connected UAL1 mannequin and its `G_Wave` clip. It is a technical proof of the connected arm motion, not the requested famous-person render. A local MrBeast scan was inspected, but its posed shoulder shows green gaps.
- The head remains a 2.5D deformation of one front-facing photograph. Small yaw angles are intentionally limited because unseen face surfaces cannot be reconstructed from this image. The original RGBA texture/UVs are retained; its alpha is used for visibility.
- **RenderPlan gap:** C3D's inline-mesh animation currently transports baked positions but its renderer samples the base mesh. This scene therefore renders through ChrononMotion's existing MotionSceneBridge/GLRenderer path; no C3D RenderPlan animation support was added or claimed.

## Assets

- Head/bust: `assets/social_rig_keanu_v1/processed/keanu_keyed.png` (local generated/keyed portrait).
- Head rig source: `ChrononMotion3d/render/spike/head_neck_joint_rig.cpp`; canonical rig implementation via `RigProgramEvaluator` and `MotionSceneBridge`.
- Hand and wave: `models/output_mrbeast/ual1_seated_gestures.glb` (existing rigged UAL1 model and its embedded gesture clips).
- Celebrity inspection only: `models/output_mrbeast/rig/mrbeast_rigged.glb`; not delivered for waving due to shoulder artifacts.
