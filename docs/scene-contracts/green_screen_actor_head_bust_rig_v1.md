# Green-screen actor head and bust rig V1

## Scene contract

- **Subject and source:** AI-generated photorealistic Keanu Reeves portrait, 1672×941 landscape, front-facing, originally RGB on a uniform green background. Keyed texture: `assets/social_rig_keanu_v1/processed/keanu_keyed.png`.
- **Composition:** 1920×1080, centered head and shoulders, full green-screen output. Fixed front camera; keep all hair and shoulders in frame.
- **Motion and timing:** Four seconds, 121 frames at 30 fps. The complete head makes a small yaw and tilt around the upper-neck pivot. Torso and shoulders remain still; no global translation or vertical bob.
- **Rig/layers:** C++ dense textured plane deformed by ChrononMotion's `RigProgramEvaluator` and applied through `MotionSceneBridge`. Skull vertices include hair, face, ears and jaw; weights blend through the neck into the torso root. Original UV and RGBA texture are retained; alpha controls visibility.
- **Must not appear:** Green gaps at the neck, detached head, key fringes, cropping, face replacement, text or extra props.
- **Review:** Inspect frames 0/30/60/90/120. Confirm whole-skull motion, continuous neck, stable shoulder/chest pixels, and neutral start/end poses. The delivered contact sheet is `keanu_head_bust_joint_rig_v3_contact.png`.

## Render path and verification

The scene now uses the C3D RenderPlan V3 inline-mesh animation path. ChrononMotion bakes the canonical rig deformation into textured mesh samples; Chronon3D interpolates the vertex positions at the requested frame and renders the original UV/RGBA texture through its software mesh backend. Mesh texture assets are supported alongside inline geometry. The background and portrait are independent mesh layers.

The delivered C3D proof is `keanu_head_neck_joint_rig_c3d.mp4`; its contact sheet is `keanu_head_neck_joint_rig_c3d_contact.png`. Verified output: H.264, 1920×1080, 30 fps, 121 frames (4.03 s), green-screen background. Frames 0/30/60/90/120 were inspected. The whole head visibly changes between frames 0 and 30/90, while sampled shoulder/chest regions remain visually stable apart from small raster/compression differences. Frame 120 returns close to the neutral pose. Encoding used FFmpeg because this C3D build does not include its native FFmpeg video sink; C3D rendered the raw frame stream.
