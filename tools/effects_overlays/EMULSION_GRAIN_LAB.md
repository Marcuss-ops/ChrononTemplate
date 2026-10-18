# Emulsion Grain Lab

## Scene contract

- Subject: an abstract archival signal aperture and editorial title card, authored from native Chronon shapes and text.
- Composition: title and labels on the left; concentric amber/teal aperture on the right; full-frame dark atmosphere and sparse dust.
- Motion: 5 seconds at 24 fps; seeded dust flecks drift across the aperture. The film grain is deterministic and static.
- Layers: separate base, coarse atmosphere grain, fine emulsion grain, aperture rings, signal, dust points, typography, and frame marks.
- Exclude: external footage, 3D geometry, AE plugin binaries, and additional renderer dependencies.
- Review: inspect decoded frame 0, frame 60, frame 119, plus contact sheet; title must remain legible and grain must visibly change over time.

## Effect mapping

The upstream Grain project inspired the controllable scale/intensity, tonal response, and accent-particle treatment. Its After Effects wrapper is not used. The scene combines Chronon's existing native Noise effect at coarse and fine scales with seeded, animated dust geometry; this is a reusable visual recipe, not a new engine effect implementation. Chronon's `NoiseParams.animated` path did not change decoded pixels across rendered frames in this experiment, so the demo uses explicit dust motion to ensure visible temporal change.

Upstream reference: [bryful/F-s-PluginsProjects, Grain](https://github.com/bryful/F-s-PluginsProjects/tree/master/Grain). The upstream repository is MIT licensed (copyright bryful, 2019); no upstream source files are copied into this experiment.

## Render facts

- Backend: Chronon software renderer; raw RGBA pre-encode output, then FFmpeg H.264 assembly.
- Canvas: 1920×1080, 24 fps, 120 frames / 5 seconds.
- Asset: `Chronon3dGPU/assets/fonts/Inter-Bold.ttf`.
- Outputs: `OneDrive/Documenti/Chronomotion/MP4/MP4/memoria_emulsion_grain_1920x1080.mp4` and `memoria_emulsion_grain_contact_sheet.png`; the source plan remains in `out/emulsion_grain_lab/emulsion_grain_lab.plan.json`. Raw RGBA is an intermediate that the script removes after encoding.
