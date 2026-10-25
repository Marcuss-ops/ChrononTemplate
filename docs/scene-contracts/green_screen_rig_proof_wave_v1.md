# Green-screen connected head and arm rig proof V1

## Scene contract

- **Subject and assets:** Synthetic Keanu Reeves likeness, chest-up, with a raised viewer-right arm and open palm on green screen. Source image `assets/social_rig_proof_v1/processed/keanu_wave_keyed.png` (1672×941 RGBA after chroma key).
- **Composition/camera:** Static orthographic front view; complete head, shoulder, elbow, wrist and fingertips stay in frame over pure #00FF00.
- **Motion/timing:** Four-second loop. Head sways slightly through neck/head joints. The raised arm waves through shoulder, elbow and wrist joints. Torso remains fixed.
- **Rig/layers:** C++ creates one dense textured plane with a real SkinnedMesh/Skeleton. Vertex weights connect torso, neck, head, shoulder, upper arm, forearm and hand; the head and arm are not cutout overlays.
- **Must not appear:** Head gaps at neck, floating arm, green wedges at shoulder/elbow/wrist, duplicated limbs, facial stretching, camera motion, text or extra scenery.
- **Review:** Compare neutral, both wave extremes, middle and loop end. Verify head remains attached at neck, arm at shoulder and the torso stays fixed.
